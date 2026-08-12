---
name: dc-stock-split
description: "Split scarce DC stock across stores and direct-customer orders under an outbound wave clock - size the shortfall against available-to-deploy, rank nodes by days-of-supply, promo/planogram priority, lost-sale risk and SLA exposure, price three deployment splits, and on approval write the allocation to the WMS wave and update the deployment plan (use-case uc-inv-deploy-allocation). Use when overnight replenishment shows DC on-hand covering less than the network pull for a fast-mover, stores plus open customer orders exceed available-to-deploy, a promo or planogram store risks going short on a flat fair-share split, or the user mentions scarce stock allocation, deployment split, DC-to-store allocation, days-of-supply, protect the promo node, demand-weighted vs fair-share, outbound wave cut-off, or which stores get the units before the trucks load."
---

# DC stock split - scarce units across the network before the wave loads

The DC holds less of a fast-mover than stores and open orders are pulling. Someone decides which nodes get
the scarce units before the outbound wave cuts. Fair-share splits it flat and the promo store that would
actually sell it goes short; decide by volume alone and the sale walks; decide too slow and the wave loads
without you. What is really being set is where the day's lost-sale risk lands. This skill is the method:
size the shortfall, rank the nodes, price the splits, hold the gate, deploy. Use-case `uc-inv-deploy-allocation`.

## Autonomy
Recommended dial for the write: **gated (L2)**. One audited exception: if the gate cannot clear before the wave cut, a protect-tier-only fallback auto-writes (protect tier filled to need, general tier untouched) with a mandatory logged reason. The method runs on its own - it sizes the shortfall, ranks the nodes, prices the splits, and re-prices live - but nothing loads to the wave until approved. Every committing write (the wave allocation to the WMS, the direct-order allocation in OMS, and the deployment-plan commit) holds for human approval each time. Any outbound (the single transport + store notification, sent once after the write - low sensitivity, no cross-org exposure) gates by the outbound floor at every level below yolo. Suggested approver: inventory/deployment analyst (e.g. M. Chen) - advisory only; v1 does not enforce approver identity, so approval is a real human click through the prompt, not a name check. The customer's `.scm/autonomy.yaml` dial is what the harness actually enforces; this is only the recommended default. The fallback's audit entry records the vector, reason, and timestamp and is flagged for review; roll it back by de-allocating the un-picked lines before pick-start (`manhattan-wms`), after which de-allocation is costly, so the fallback stays conservative.

## Systems
| System (record) | Read / write | Vendor HOW deferred to |
|---|---|---|
| Inventory / depot + WMS | read DC on-hand, held, allocated; **write** outbound wave allocation | `manhattan-wms` (available-to-deploy, wave release, allocation) |
| Order management / OMS | read open store + direct-customer orders, SLA flags; **write** direct-order allocation | `manhattan-oms` |
| Demand forecast + Planning | read velocity, promo/planogram flags; **write** deployment plan | `kinaxis` (deployment plan, commit/publish) |
| Notifications | write once: transport + store teams | (message only) |

The workflow owns the **cross-system split**. Each write's mechanics (how a wave allocates and what
de-allocation costs, how the deployment plan is committed) belong to the named `expertise-*` skill, not here.

**Action class - not every write is equal (the gate reads this):**
| Kind of action | Class | Reversible? |
|---|---|---|
| Read ATD, need, velocity, SLA, promo flags | read | n/a - re-read at execute, on-hand drifts |
| Write the wave allocation **before pick-start** | write (committing) | yes, by de-allocating - stock is reserved, not yet moved |
| Write the wave allocation **after pick-start** | **destructive** | de-allocation now unwinds physical work (`manhattan-wms`) - a real cost, not a clean undo |
| Allocate a direct-customer order in OMS | write (committing) | reversible before fulfilment; on an SLA order a late de-allocation may trip a penalty (`manhattan-oms`) - treat as destructive once the order is confirmed to the customer |
| Commit / publish the deployment plan | write (committing) -> **destructive after publish** | committing while it stays in the plan; once it publishes / releases downstream there is no clean uncommit - gate it like a destructive write (`kinaxis`) |
| Notify transport + store teams | write (egress) | send once - a re-send is noise, not a rollback |

**Allocation lifecycle:** `draft -> priced -> approved -> released (allocated) -> picked -> shipped`. Reversal
is free up to **released**, cheap until **pick-start**, then costly (de-allocation unwinds work), then gone once
**shipped**. Know which state a line is in before you touch it.

## Flow (detect -> assemble -> options -> gate -> act)

**1. Detect - size the real gap, not the headline gap.**
Read at the replenishment run. The number that matters is **available-to-deploy (ATD)**, not raw on-hand:
`ATD = DC on-hand - already-allocated - on-hold/QA - damaged - reserved safety`. Manhattan WMS is the system
of record for on-hand (`manhattan-wms`). Then per node: store need (replen pull + open store lines),
direct-order need + SLA flag (OMS), velocity and promo/planogram flags (Planning). `shortfall = network pull - ATD`.
**Freshness rule:** ATD drifts (picks, cycle counts, adjustments post all morning). Re-read ATD at execute,
right before the write. Threshold: if the ATD delta is `> 2%` of network pull, re-size and re-price; if `<= 2%`,
proceed and note the variance in the audit log. Deploying on a stale on-hand is failure mode 1.

**2. Assemble - rank every node, cut nothing on volume alone.** This is the core (see Method below). Score
each node on days-of-supply, promo/planogram priority, and lost-sale risk; check direct orders for SLA/penalty.
Split the nodes into a **protect tier** (fill first) and a **general tier** (rank, then greedily fill).

**3. Options - price three splits with real dollars.** Each split is a full allocation vector priced on
lost-sale dollars and stockout risk. Construct A/B/C by the pricing method below; rank by total lost-sale $.

**4. Your gate - the analyst decides on evidence.** Show the three priced splits, which stores get cut, and
**precedent from the deployment record** - the retained memory of prior scarce-day cuts on this SKU / these
stores and how they then sold, so the next call starts from what happened, not a fresh guess. Approve writes the
chosen vector; **adjust** moves a node's line and the rest re-price live; decline holds and escalates. Every
override is kept with its reason in the same record.

**5. Act - deploy in order, before the cut.** Writes, in sequence: (a) allocation to the WMS outbound wave
(`manhattan-wms` - wave release allocates on-hand and generates work; committed stock leaves the
available pool, and de-allocation after picking starts has a cost); (b) direct-order allocation in OMS
(`manhattan-oms`), skipping any order on hold; (c) update the deployment plan so the next run
starts from what was deployed (`kinaxis`); (d) notify transport + store teams once; log the why.

## Method - how to size the shortfall and rank the nodes

**Per-node inputs**
- `need` - units the node is pulling today (store replen + open lines, or the direct-order quantity).
- `DOS` (days-of-supply) `= node on-hand / daily forecast velocity`. Low DOS = stocks out today; high DOS = can wait.
- `promo/planogram` - live promo, feature, or a planogram reset that must show full facing.
- `lost-sale risk per unit` `= unit margin x P(stockout if short)`. Use **margin**, not revenue - the sale that
  walks costs margin. If margin is unavailable, use price as a proxy and say so.
- `P(stockout if short)` - read it off the DOS band when a node's own stockout curve is not available:
  `P ~ 1.0` when DOS `< 1`, `P ~ 0.5` when DOS `1.0 - 3.0`, `P ~ 0.1` when DOS `> 3`. A live promo overrides the
  band to `P ~ 1.0` (promo demand outruns the shelf). These bands are fallback approximations - a live demand
  model, historical stockout frequency, or a service-level target overrides them when available. The band value
  is the **fully-short** case; scale it down for a shallow cut (a node shorted 10% stocks out far less than one
  shorted 100%), so partial cuts in the general tier are not over-priced.
- `SLA` - a direct order with a contractual service level or late penalty.

**Thresholds**
| Signal | Band | Action |
|---|---|---|
| DOS | `< 1.0 day` critical | protect - it stocks out today |
| DOS | `1.0 - 3.0` tight | general tier, high rank |
| DOS | `> 3.0` comfortable | general tier, **cut first** - it can wait a wave |
| Promo/planogram | live | protect - fill to promo forecast or planogram min, use promo velocity not baseline |
| SLA / penalty | present | protect - fill to need; short = a cash penalty, not a soft miss |
| DC safety hold | `0 - 5%` of ATD | hold higher when the on-hand read is shaky or inbound is late; hold 0 when replen lands before the next wave |

**Ranking**
1. **Protect tier, filled to need first:** nodes with DOS `< 1.0` and live demand; live promo/planogram nodes;
   direct orders with an SLA. No haircut here.
2. **General tier, greedy by lost-sale risk per unit:** allocate the remaining ATD to the highest lost-sale-risk
   nodes first until it runs out. The shortfall lands on the lowest-risk, highest-DOS nodes (they wait a day).
   Tie-break on lower DOS.

**When the protect tier alone exceeds ATD** (two live promos plus an SLA order pull more than you hold): do not
fill flat inside the tier. Fill each node to its planogram min or promo floor first, then pro-rate the residual
by lost-sale risk per unit, and escalate - a starved promo is a gate decision, not a silent haircut. Example:
protect need 1,200 + 900 + 1,000 = 3,100 against ATD 2,800 leaves 300 short inside the tier; cover the two
planogram mins (say 400 + 300), then split the remaining 300 shortfall by risk per unit and flag it to the analyst.

**Cross-system truth (who wins on a disagreement):** WMS is authoritative for DC on-hand / ATD; Planning owns
velocity and promo flags; OMS owns open direct orders and their SLA. Never override a fresh WMS on-hand with a
stale planning number - re-read WMS at execute.

## Options - construct and price the three splits
| Split | Construction | What it costs |
|---|---|---|
| **A - Demand-weighted** | every node filled at `fill ratio = ATD / network pull`, promo included | promo/high-velocity nodes take the same haircut -> largest lost sales |
| **B - Protect promo + SLA** | protect tier to need; rank general tier by lost-sale risk per unit and greedily fill | cut lands on high-DOS slow stores (they wait a day); SLA penalty avoided - lowest lost sales |
| **C - Hold 4% safety cover** | B, minus a 4% ATD buffer against a stale on-hand or a late priority order | B's lost sales + small held-unit opportunity cost; lowest DC execution risk |

Default recommendation: **B**. Switch to **C** when the on-hand read is shaky (a cycle count is pending or an
adjustment just posted) - the buffer absorbs the surprise. **A** is the anti-pattern the fair-share replen
system produces on its own; price it only to show the analyst the dollars a flat split gives away.

## Worked example (SKU 4471, numbers)
Setup: WMS on-hand **9,200**; 0 held, 0 pre-allocated -> **ATD = 9,200**. Network pull **11,800** = stores 9,300
+ six direct orders 2,500. `shortfall = 11,800 - 9,200 = 2,600`. Wave cuts in 3 hours.
(If 150 were on QA-hold, ATD = 9,050 and the shortfall is 2,750 - sizing on raw on-hand under-sizes the gap.)

| Node | need | on-hand | velocity/day | DOS | flag | tier |
|---|---|---|---|---|---|---|
| Store 12 | 1,200 | 300 | 900 | 0.33 | promo/feature | protect |
| Store 45 | 900 | 200 | 600 | 0.33 | promo/planogram reset | protect |
| DO-991 | 1,000 | - | - | - | SLA, $3,000/day late | protect |
| Store 03 | 1,500 | 1,000 | 800 | 1.25 | high velocity | general (high) |
| Store 88 | 700 | 2,800 | 200 | 14 | slow | general (cut first) |
| Store 51 | 500 | 1,900 | 180 | 10.5 | slow | general (cut first) |
| 18 other stores | 4,500 | - | mixed | - | - | general |
| DO-992..996 | 1,500 | - | - | - | no SLA | general |

Protect tier = 1,200 + 900 + 1,000 = **3,100**, filled to need. Remaining ATD = 9,200 - 3,100 = **6,100** for a
general-tier need of 8,700 -> the full 2,600 shortfall lands on the general tier.

- **A - demand-weighted:** fill ratio 9,200 / 11,800 = **0.780**, applied to every node. Row by row
  (`units short = need x 0.220`, then `x margin x P`):
  - Store 12: short 264 x $8 x 1.0 = **$2,112**
  - Store 45: short 198 x $8 x 1.0 = **$1,584**
  - Store 03: short 330 x $8 x 0.5 = **$1,320**
  - the 18-store + direct-order buckets short ~1,800 units at a blended ~$7 x ~0.6 -> **~$9K** (blend =
    weighted-average margin ~$7 and blended P ~0.6 across the DOS 1-3 nodes in those buckets)

  Network total **~$14K lost sales**, with ~$3.7K of it on the two promo stores a flat split gives away first.
- **B - protect promo + SLA:** 12, 45, DO-991 filled whole (0 lost). The 2,600 cut is ranked onto the high-DOS
  slow nodes: Store 88 cut 700 x $6 x 0.1 = **$420**, Store 51 cut 500 x $6 x 0.1 = **$300**, remaining ~1,400
  cut across other DOS `> 3` stores at ~$6 x 0.15 blended -> **~$2.8K**. Total **~$3.5K**, SLA penalty avoided;
  every cut node has DOS 10-14, so it covers for a day.
- **C - hold 4%:** buffer 9,200 x 4% = **368** units; deployable 8,832; cut grows to ~2,968 onto the same slow
  nodes. Lost sales **~$4K** plus ~$0.5K held opportunity - lowest risk if the on-hand is uncertain.

Recommend **B** (saves ~$10.5K vs A and avoids the SLA penalty). If a cycle count is pending on SKU 4471, recommend **C**.

## Failure -> recovery playbook
| Failure (risk) | Detect before acting | Recover |
|---|---|---|
| Deploying on a **stale on-hand** the WMS has not reconciled | compare WMS on-hand timestamp / last cycle-count / adjustment vs the replen read; re-read ATD at execute | before release: re-size and re-price. After release on the bad number: over-allocation surfaces as short-picks - de-allocate the un-picked lines (`manhattan-wms`) and re-run the split on corrected ATD |
| **Fair-share bias** starving the store that would have sold it | any promo/planogram or DOS `< 1` node getting a fill ratio `< 1` while a DOS `> 3` node got units | move that node into the protect tier and re-price at the gate (adjust); the memory record shows which cut stores later sold |
| **Missing the outbound cut-off** so the call is moot | time-to-cut vs time-to-decide; the wave clock | fire the clock fallback - deploy the protect-tier-only default (bounded auto), log it, flag for review; never hold the whole wave chasing a perfect split |

**Edge cases the record does not list:** inbound in-transit that lands before the wave (adds to ATD - include
only if it arrives before the cut); a direct order on hold in OMS (do not allocate to it); a partial/short pick
mid-wave (re-check remaining ATD before topping up); another DC that could cover the gap (out of scope here -
flag for a multi-DC re-source, do not silently pull from it); **cross-SKU contention** - several short SKUs pull
on the same ATD constraint (dock, truck cube, pick labor), so sequence them by aggregate lost-sale risk rather
than solving each SKU in isolation; **stale velocity** - a planning refresh lag means
DOS is computed on old velocity; check the forecast timestamp and treat a promo node's baseline velocity as
suspect (use the promo forecast); a node in **both** promo and a planogram reset (take the larger fill target,
promo forecast or planogram min); a **cycle count that locks the SKU mid-wave** in the WMS (the ATD you sized on
is frozen - re-read after the count clears, do not allocate against a locked balance).

## Testing (pressure scenario)
Clock closing (wave cuts in 20 min) + a tiny shortfall (only 4% short) + authority ("just fair-share it and
push the wave, we do not have time"). WITHOUT this skill the agent flat-splits and loads - the promo store goes
short and the sale walks. WITH it, it sizes ATD, ranks the nodes, prices A/B/C, holds at the analyst's gate, and if
the clock truly runs out fires the protect-tier fallback rather than a blind flat split. Counter to add if it
recurs: "the shortfall is tiny, fair-share is fine" - a 4% shortfall landed entirely on one promo store is the
whole lost sale, not a rounding error.
