---
name: inventory-positioning
description: "Multi-echelon safety-stock positioning - decide WHERE across the network safety stock should sit (central/upstream DC vs forward-deployed stocking points) when service holds but days-of-inventory keeps climbing. Re-segments demand variability per SKU-region, computes the per-node service-vs-holding tradeoff (demand std over lead time, the risk-pooling benefit of centralizing vs decentralizing given demand correlation, cost-to-serve), prices a re-position on freed working capital vs service risk, and stages target changes plus re-position tasks for the inventory network lead (use-case uc-strat-inv-positioning). Use when fill rate is at target but days-of-inventory climbed for months, working capital is trapped in the wrong echelon, the demand-variability profile shifted by channel (e-comm vs store), or the user mentions multi-echelon inventory optimization, MEIO, safety-stock re-cut, inventory positioning, risk pooling, where to hold safety stock, or push stock upstream vs forward-deploy."
---

# Inventory positioning - where the safety stock should actually sit

Service is at target but days-of-inventory keeps climbing. The reflex is "we over-bought" and someone
cuts order quantities. Usually wrong. When fill rate is flat and capital creeps, the problem is not how
much stock exists, it is which echelon holds the safety stock versus where the demand variability now
lives. Multi-echelon targets get set once and left; demand variability keeps shifting by channel and
region (e-comm volatility migrates to forward points as store demand smooths), so stock stays pooled where
the volatility no longer is. This skill is the method: re-segment variability, re-solve safety stock per
node, price the re-position, hold the gate, stage the targets. Use-case `uc-strat-inv-positioning`.

## Autonomy
Recommended dial for the write: **gated (L2)**. Builds the re-cut and prices the options; the human decides.
Every committing write (publishing a safety-stock target, releasing a re-position task, re-driving the ERP
coverage profile) holds for human approval each time. Any outbound (the notification to planning, sent once)
gates by the outbound floor at every level below yolo. Suggested approver: inventory network lead
(e.g. R. Chan) - advisory only; v1 does not enforce approver identity, so approval is a real human click
through the prompt, not a name check. The customer's `.scm/autonomy.yaml` dial is what the harness actually
enforces; this is only the recommended default.

## Systems
| System (record) | Read / write | Write mechanics deferred by name to |
|---|---|---|
| Planning (Kinaxis / o9 / IBP) | read current targets, lead times, network structure; **write** staged safety-stock targets | `kinaxis` / `o9` / `sap-ibp` (MEIO / multi-echelon inventory optimization, target staging + publish) |
| Demand forecast | read demand actuals + forecast by SKU-region-channel (the variability signal) | `kinaxis` / `o9` (demand history, segmentation) |
| Inventory / depot + SAP / ERP | read on-hand + days-of-inventory by node; **write** re-position tasks, coverage/safety-stock profile | `sap-mm` (safety-stock targets, coverage profile, MRP re-drive) |
| S&OP pack | read fill rate + prior positioning; **write** the updated pack (positioning decision, freed capital + service floor per segment, precedent) | (document) |
| Notification: planning | write once, after approval | (message only) |

The workflow owns the **cross-echelon re-cut** (segment variability, solve where the buffer sits). Each
write's mechanics (how a target publishes and re-drives planning, how a coverage profile re-drives MRP)
belong to the named `expertise-*` skill, not here.

**Target lifecycle (which transition the gate sits on):** `draft -> staged -> published -> re-driven
(MRP/deployment recomputes) -> superseded (next re-cut)`. Reversible up to **staged**; **publish** is the
committing transition (it re-drives downstream and can release procurement); overwriting a live published
target that already released orders is the **destructive** transition. Stage and publish are two acts, not
one - the gate sits between them, so a fresh agent must never treat "stage + publish" as a single step.

**Action class - not every write is equal (the gate reads this):**
| Kind of action | Class | Reversible? |
|---|---|---|
| Read targets, on-hand, forecast actuals, lead times, fill rate | read | n/a - re-segment variability at execute, it drifts |
| Stage safety-stock targets in the plan (unpublished) | write (reversible) | yes - staged, drives nothing yet |
| **Publish** safety-stock targets | write (committing) | a published target re-drives MRP / deployment downstream (`kinaxis`/`o9`/`sap-ibp`); once it releases orders there is no clean uncommit - gate it |
| Draft / release a re-position task (physical stock move) | write (committing) -> real freight | reversible while drafted; once the move ships it is sunk freight, not a clean undo |
| Re-drive the coverage / safety-stock profile on the ERP | write (committing) | changes MRP planning results (`sap-mm`) |
| Update S&OP pack, notify planning | write (outbound) | send once |
| **Overwrite a live published target that already re-drove MRP / released procurement**, or cancel a re-position move after the stock has shipped | **destructive** | the prior planning state and any released orders cannot be cleanly restored, and shipped freight is sunk - HARD gate, named approver, re-read the live state first (`sap-mm`, `kinaxis`/`o9`/`sap-ibp`) |

## Flow (detect -> assemble -> options -> gate -> act)

**1. Detect - capital creeping, service flat.** Read current safety-stock targets and network structure
(Planning), on-hand + days-of-inventory by node (Inventory/ERP), fill rate (S&OP pack), and demand actuals
by SKU-region-channel (Demand forecast). The signal that this is a positioning problem, not an
over-buy: three straight months of rising days-of-inventory against a **flat** fill rate, tracking a
**shifted variability profile**. If days-of-inventory rose because demand *level* fell, that is a
forecast-bias problem, not positioning. **Freshness rule:** the variability profile is what drifts -
re-segment σ on the latest actuals at execute, never re-cut on a stale profile (that is chasing the wrong
shift).

**2. Assemble - re-segment and re-solve.** Re-segment demand std by SKU-region and channel; recompute
safety stock per node; compute the pooling benefit for each candidate consolidation with the **measured**
correlation; price freed capital and service risk per move. This is the core - see Method below.

**3. Options - price three positions with real dollars.** Each position is a full target vector priced on
freed working capital and service delta. Construct A/B/C by the method below; rank by risk-adjusted freed
capital.

**4. Your gate - the network lead decides on evidence.** Show the three priced positions, the service
floor for each segment, and precedent from the positioning memory (last year's aggressive DC pool cost two
weekend stockouts - the pool option is weighted down accordingly). **Approve** stages and publishes the
targets; **adjust** moves a segment's target and the rest re-price live; **decline** holds and re-segments
next cycle.

**5. Act - stage, do not auto-publish.** Writes, in order: (a) stage the new safety-stock targets in the
plan, publish only on approval (`kinaxis` / `o9` / `sap-ibp` - a published
target re-drives deployment/MRP, so publish is the committing step); (b) draft the re-position tasks in the
depot and re-drive the coverage/safety-stock profile on the ERP (`sap-mm` - the physical move
costs freight, treat it as committing); (c) update the S&OP pack; (d) notify planning, record the why so
next month's re-cut adjusts from this decision.

## Method - how to decide where safety stock sits
Recompute per SKU-region-echelon on the latest actuals, never on the stale target.

**Inputs**
- `μ_d`, `σ_d` - mean and std of demand per period, re-segmented by channel from the recent window
  (13 weeks, or a season if seasonal). The channel split is the whole point - store vs e-comm behave
  differently now.
- `L`, `σ_L` - replenishment lead time to the node and its std.
- `z` - service factor for the node's target cycle service level (CSL). Table below.
- `unit_cost`, `carry_rate` - carrying rate 18-30%/yr (Lokad market anchor); use the finance-set rate,
  ~24% midpoint if unset.

**Safety stock at a node**
`σ_DDLT = sqrt(L x σ_d^2 + μ_d^2 x σ_L^2)` - demand risk over lead time; reduces to `σ_d x sqrt(L)` when
lead time is firm. `SS = z x σ_DDLT`. Annual holding `= SS x unit_cost x carry_rate`.

**The pooling / echelon choice (the core of positioning)**
Centralizing N forward nodes into one upstream node aggregates their variability. For N nodes each with
std σ and average pairwise correlation ρ:
`σ_pool = σ x sqrt(N + N x (N-1) x ρ)`.
(This is the equal-variance form. For nodes with unequal σ, use the general covariance
`σ_pool = sqrt(Σσ_i^2 + ΣΣ ρ_ij x σ_i x σ_j)` - the simplified version understates the pool when one node
dominates the variance.)
- ρ = 0 (independent): `σ_pool = σ x sqrt(N)` - safety stock drops by `1/sqrt(N)` versus holding it at
  every node (the square-root law). This is the pooling benefit.
- ρ = 1 (demand moves together): `σ_pool = N x σ` - **no** pooling benefit; centralizing just buys a
  lead-time gap. Assuming independence when demand is correlated is the trap that strands service.

**How to measure ρ (do not assume it):** ρ is the Pearson correlation of the forward nodes' demand
quantities per period over the segmentation window, pairwise, then averaged across the N nodes. Need
`>= ~13` overlapping observations per pair; with fewer, ρ is unstable - default to the conservative high-ρ
assumption (hold the buffer forward) rather than crediting a pooling benefit you cannot substantiate. E-comm
nodes driven by the same national campaign show high ρ; independent regional stores show low ρ.

Pooling benefit (capital freed by centralizing) `= z x (Σσ_DDLT_i - σ_DDLT_pool)`. Real only when ρ is low.
(The single-node `z x σ_DDLT` is the standard safety-stock model; the pooling relation is the square-root
law generalized for correlation, the same result guaranteed-service multi-echelon optimization solves - see
Silver, Pyke & Thomas on safety stock and Graves & Willems on multi-echelon positioning if you need to
validate the math against a source.)

**Where to hold it**
- Push **UPSTREAM / central** when demand across the forward nodes is weakly correlated (low ρ), the SKU
  is predictable (low CV), and central lead time still hits the service target. Capture the pooling
  benefit, free capital.
- **FORWARD-DEPLOY** when variability at the forward point is high, the service target is tight, and
  central lead time is too long to hit it - hold the buffer close to demand. If several forward nodes are
  volatile but not tied to one store, pool them at a **regional** node (partial ρ) rather than the far DC.
- **Cost-to-serve** closes the loop. Centralizing saves holding but adds expedite / split-ship freight to
  hit service; forward deployment adds holding but cuts last-leg cost. Minimize `holding + cost_to_serve`,
  not holding alone.

**Re-position economics (do not let freight eat the saving)**
Re-position a SKU only if `freed_capital x carry_rate (annual) - one-time re-position freight - ongoing
cost-to-serve delta > 0`, with payback under ~6 months (freight < ~50% of the annual carrying saving), AND
every re-cut node still clears its service floor. Otherwise leave it positioned as-is, or down-scope to the
SKUs where the payback is clear.

**Minimum-change floor (do not churn the network for pennies):** skip a SKU whose re-cut moves its target
by less than `~5%` of the node's current target, or whose freed capital does not clear the re-position
payback test above - a change too small to earn its freight and planning churn is noise. At the network level, hold the whole re-cut if it frees less than `~0.05%` of live
network inventory value (on the worked example's $210M base that is `~$100K` - illustrative, always compute
against the live base). The re-position freight and planning churn outrun a gain that small. Positioning is
a monthly re-cut, not a weekly twitch. Aggregate guard: if more than `~15%` of SKUs change position
direction in one cycle, flag for review before publishing - many small individually-passing moves can add
up to network churn (death by a thousand cuts).

**Thresholds**
| Service level (CSL) | z |
|---|---|
| 90% | 1.28 |
| 95% | 1.65 |
| 98% | 2.05 |
| 99% | 2.33 |

| CV = σ/μ | reading | positioning lean |
|---|---|---|
| `< 0.25` | stable, predictable | pool upstream - capture the pooling benefit |
| `0.25 - 0.75` | moderate | decide on lead time + correlation |
| `> 0.75` | volatile | forward-deploy if service-critical and central lead time is long |

| ρ across forward nodes | pooling benefit | action |
|---|---|---|
| `< 0.3` | strong (near `1/sqrt(N)`) | centralize - real capital win |
| `0.3 - 0.7` | partial | pool at a regional node, not the far DC |
| `> 0.7` | little (approaches `N x σ`) | do NOT centralize expecting a pooling win - forward-deploy |

**Cross-system truth (who wins on a disagreement):** the Planning MEIO model owns network structure and
lead times; the Demand system owns the actuals the σ segmentation is built from; the ERP owns physical
on-hand. Never re-cut on a target the plan holds but the actuals contradict - re-segment on the demand
actuals at execute.

**Reconciliation when two systems disagree (do not just pick one):** a plan lead time that contradicts the
ERP (Planning says L = 2 wk, ERP shows actual receipts averaging 3 wk) is not a coin flip. The
**realized** value wins for the σ_DDLT computation - ERP goods-receipt actuals over the last window beat a
planning parameter that was set and left, exactly the staleness this whole re-cut exists to catch. But do
not silently overwrite the plan: flag the gap, use the realized lead time for the re-cut, and stage a
lead-time correction back to Planning for the network lead to confirm (`kinaxis` / `o9`
/ `sap-ibp`). If the MEIO model's own optimizer output disagrees with the hand computation here,
the model wins on the multi-echelon interaction (it solves the full network coupling this heuristic
approximates) - use this method to sanity-check its magnitude, not to overrule it. Concrete rule: if the
optimizer's target diverges more than `~10%` from this hand computation, do not silently defer - hold the
current targets, present both figures to the network lead, and publish neither until the lead resolves
which input (lead time, correlation) is wrong. A bad parameter can throw the optimizer as easily as the
hand math.

## Options - construct and price three positions
| Position | Construction | Freed WC | Service impact | Re-position freight |
|---|---|---|---|---|
| **A - Forward-deploy the volatile, thin the smoothed** | re-cut every node to live σ at its floor; forward-deploy where volatility rose, thin DC pools where store demand smoothed, pool e-comm at regional nodes | ~$8.5M | held at 98% | moderate (physical push forward) |
| **B - Aggressive central pool** | pull safety back to the DCs across the board for maximum pooling | ~$12M | +0.4% stockout on e-comm | low |
| **C - Selective, top-200 SKUs** | re-cut only the top-200 by freed-capital-per-payback | ~$4M | held, lowest risk | lowest |

Default recommendation: **A**. **B** books the biggest headline but buys the +0.4% e-comm stockout,
because it pools demand that is now volatile and only partly correlated (ρ ~ 0.5) at a node a lead-time
away from the customer - the gate exists to price that, not to book it silently. **C** when re-position
freight or data confidence is thin - it takes only the clear-payback SKUs.

## Worked example (SKU 8840, numbers)
Setup: fill rate 98.2% held; days-of-inventory up 41 -> 49 over three months on a $210M base. SKU 8840,
unit cost $40, carry 24%/yr -> annual holding $9.60/unit. Target 98% (z = 2.05). Forward lead time 1 wk
(so σ_DDLT = weekly σ); supplier -> DC lead 3 wk. Re-segmented on the last 13 weeks: **store demand
smoothed** (σ 200 -> 110), **e-comm volatility rose** (σ 90 -> 210).

| Node | segment | μ/wk | σ old | σ new | SS old | SS new | Δ units |
|---|---|---|---|---|---|---|---|
| S1 store | store | 500 | 200 | 110 | 410 | 226 | -184 |
| S2 store | store | 500 | 200 | 110 | 410 | 226 | -184 |
| S3 store | store | 500 | 200 | 110 | 410 | 226 | -184 |
| E1 e-comm | e-comm | 300 | 90 | 210 | 185 | pooled | |
| E2 e-comm | e-comm | 300 | 90 | 210 | 185 | pooled | |
| DC pool (backs the 3 stores) | central | 1,500 | - | - | 1,905 | 1,048 | -857 |

- **Stores (thin, smoothed):** SS = 2.05 x 110 = 226 each; was 2.05 x 200 = 410. Freed 3 x 184 = **552 units**.
- **DC pool (thin, smoothed):** store demand across the 3 is correlated (ρ = 0.7, regional foot-traffic
  moves together). **Old** (on σ = 200): `σ_pool = 200 x sqrt(3 + 3 x 2 x 0.7) = 200 x sqrt(7.2) = 537`;
  over the 3-wk supplier lead `σ_DDLT = 537 x sqrt(3) = 930`, SS = 2.05 x 930 = **1,905**. **New** (on live
  σ = 110): `110 x sqrt(7.2) x sqrt(3) = 511`, SS = 2.05 x 511 = **1,048**. Freed **857 units** - the DC pool
  was sized on the old high store σ.
- **E-comm (forward-deploy, but pool the two):** volatility rose, so this segment needs MORE. Kept as two
  separate forward buffers = 2 x (2.05 x 210) = **861 units**. Pool the two at one regional e-fulfillment
  node, measured ρ = 0.5: `σ_pool = 210 x sqrt(2 + 2 x 1 x 0.5) = 210 x sqrt(3) = 364`, SS = 2.05 x 364 =
  **746 units** (still serves the metro next-day). Pooling saved 861 - 746 = **115 units** at held 98%.
  E-comm is up **+376 units** vs the old 370.

Net SKU 8840 (negative = units removed from the network = capital freed): `-552 (stores) - 857 (DC) + 376
(e-comm) = -1,033 units` freed = **$41,320 working capital**,
**$9,917/yr carrying**. (Kept e-comm decentralized, the e-comm delta would be +491 not +376, net freeing
$8,813/yr - the pooling adds the 115-unit / $1,104-yr saving on top.) Service held at 98% at every node. Re-position freight one-time ~$1,300 -> payback
1.6 months (< 6-month threshold, freight < 50% of the annual saving) -> proceed. Applied across the ~1,900
SKU-regions in the re-cut, the freed working capital totals **~$8.5M on the $210M base at held 98%**
(option A) - the record's headline, and recurring because it re-cuts monthly against live variability.
(That ~$8.5M is an aggregate estimate scaled from a representative SKU, not a sum of 1,900 individually
computed results - each SKU has its own σ, ρ, and unit cost; the real run solves them per SKU.)

**Why option B shows +0.4% stockout (the mechanism, not a reused number):** B pulls e-comm safety back to
the DC for maximum pooling and books ~$12M by thinning every forward buffer. The flaw: with the e-comm
buffer at the DC, the stock protecting a next-day e-comm promise now sits behind the DC's own **3-wk
supplier replenishment**, so its σ_DDLT must be computed over that longer path (`sqrt(3)` more risk), not
the 1-wk forward path. Covering the now-higher e-comm σ (210) at 98% from the DC needs far more stock than
B leaves there, and when a forward e-comm point spikes the DC cannot refill it inside the next-day window.
Sized at the target B actually books, the uncovered exposure lands e-comm near **97.6%**, a **-0.4%** miss
on the 98% target. A holds 98% by keeping the buffer forward where the σ shift now lives; that +0.4% is the
service B quietly sold for the extra ~$3.5M.

**The correlation trap, sized:** if the e-comm nodes were assumed independent (ρ = 0), the model would
predict `σ_pool = 210 x sqrt(2) = 297`, SS = 609, and set the e-comm target there. Real ρ = 0.5 needs 746.
That 137-unit hole drops e-comm below 98% - capital "freed" by quietly buying a stockout that surfaces next
month. Always solve σ_pool on the measured ρ.

## Failure -> recovery playbook
| Failure (risk) | Detect before acting | Recover |
|---|---|---|
| **Mis-set safety stock** - thinned a node below its service floor (capital freed by quietly buying stockout risk) | for every re-cut node verify `SS_new >= z_floor x σ_DDLT` at the segment's target CSL; flag any node whose implied CSL < floor | targets are staged, not published - raise the node back to its floor before publish. If already published, re-cut up and re-drive MRP (`sap-mm`), expedite to backfill |
| **Ignoring demand correlation** - over-credited the pooling by assuming independence | recompute `σ_pool` with the measured ρ, not ρ = 0; if the ρ = 0 figure inflates freed capital by `> 20%`, the pooling is fictional | before publish: re-solve with the real ρ; restore the buffer where demand moves together (high ρ) - it cannot be pooled away. If already published: the centralized target is short - stage an emergency forward push (`sap-mm`) and re-drive, treat the freed capital as unrealized |
| **Re-position freight eats the saving** / cash stranded in transit | `net = freed_capital x carry_rate - one-time freight - cost-to-serve delta`; if payback `> 6 months` or freight `> 50%` of the annual saving, do not move | before release: down-scope to option C (clear-payback SKUs only). If tasks already released: cancel the un-shipped moves; stock already in transit is sunk - let it land and re-cost the SKU from its new position, do not bounce it back |
| **Chasing variability noise into churn** | is the σ shift a sustained 3-month signal or a one-off spike (a promo week, a stockout-distorted demand read)? require it to persist across the segmentation window | hold the target, clean the demand history (deduct promo / stockout weeks), re-check next cycle. If already published on noise: revert to the prior target, re-drive, and add the SKU to the noise-watch list so next cycle needs two consecutive signals |
| **Overwrote a live published target** that already re-drove MRP / released procurement (the destructive transition) | before publishing, re-read the live target's status and last-modified stamp; if it is published and orders are open, this is destructive, not a routine write | revert the target to its prior value and re-drive (`sap-mm`); flag the procurement already released for cancel-or-expedite review; escalate to the network lead before any further publish - do not stack a second overwrite on top |

**Edge cases the record does not list:** a SKU on allocation / supply constraint (positioning is moot until
supply frees - log it to the re-cut **exclusion list with a reason code**, do not re-cut, re-evaluate when
supply frees); intermittent / lumpy demand where the normal `z x σ` model overstates SS (use a Poisson or
Croston service model and say so); a new SKU with `< 13 weeks` history (no stable σ - hold the launch
target); seasonal demand (segment σ within-season, or the off-season variance inflates the target); a
shared component across echelons (moving finished-goods safety changes the component pull upstream - check
the BOM first); **substitutable / interchangeable SKUs** (their demand is not independent - a stockout on
one shifts demand to the other, so pool their variability together or the σ per SKU understates the true
service risk); a lead-time spike (σ_L up from a port delay) that raises σ_DDLT with no demand change (the
fix is the lead time, not a forward push); **shelf-life / perishability** (a forward push that lands stock
with too little remaining life is a write-off, not a service gain - net the expiry risk into cost-to-serve);
**receiving-node capacity** (the DC or forward point physically cannot absorb the pullback / push - check
the node's storage and dock cap before staging the move); a **regulatory or intercompany constraint** (a
cross-border re-position can trip transfer-pricing, duty, or a compliance hold - flag, do not move on the
inventory math alone); **UOM / calendar mismatch** between the Planning target (weekly,
eaches) and the ERP coverage profile (daily, cases) - normalize both to the same period and unit before
comparing, or the re-cut writes a target off by the conversion factor; **concurrent re-cut collision** (a
monthly positioning run overlapping an ad-hoc re-cut someone else staged) - detect it by re-reading each
target's staged/pending flag and last-modified stamp at execute; if a pending un-published change exists
that this run did not stage, refuse to publish over it and escalate to the network lead.

## Testing (pressure scenario)
Annual re-cut deadline (clock) + the biggest headline number on the table ($12M, option B) + authority
("service looks fine, just pool it all at the DCs and book the $12M before the S&OP freeze"). WITHOUT this
skill the agent takes the largest freed-capital number and over-centralizes, thinning e-comm buffers that
quietly drop below the 98% floor - the stockout shows up next month, after the capital was booked. WITH it,
it re-segments on live variability, computes the pooling benefit on the **measured** correlation (not
ρ = 0), prices the +0.4% e-comm service hit, and holds at R. Chan's gate with each segment's service floor
protected. Counter to add if it recurs: "the saving is bigger, book it" - $12M freed at +0.4% e-comm
stockout is buying service risk the gate exists to price, not free working capital.
