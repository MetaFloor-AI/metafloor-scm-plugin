---
name: expedite-or-absorb
description: "Expedite-or-absorb - price the transport expedite premium against the OTIF penalty, retailer chargeback, and lost-sale exposure of letting a committed shipment slip, then recommend expedite, partial-expedite, or absorb. Use when a shipment is tracking late against its committed OTIF / delivery window, a carrier ETA breaches the OTIF buffer, a top account risks a late delivery, someone asks whether to pay premium freight / air / team-drive / expedited mode or eat the miss, or the words expedite vs absorb, premium freight, OTIF penalty, chargeback, TONU, service-level miss, late shipment, at-risk load, or should we expedite come up. Covers uc-deliver-expedite - the high-frequency expedite-vs-absorb call across TMS (Oracle OTM, SAP TM), CLM (Icertis) penalty terms, carrier ETA feeds, CRM account priority, and premium-mode rates."
---

# Expedite or absorb - price the slip, don't guess it

Use case `uc-deliver-expedite`. A committed shipment is tracking late against its OTIF window. Pay a premium
to expedite, or absorb the miss and take the penalty plus chargeback? This call fires thousands of times a
week across a network. Done by gut it bleeds both ways: the desk over-expedites slips a buffer would have
covered (SourceDay signal: laggards burn ~7% of logistics cost on expedite vs ~3% for leaders - an industry
heuristic, not a per-shipment threshold) and under-catches the misses that actually hurt. The skill's job is
to put a priced number on each option so the gate is a decision, not a reflex.

## Read this first
The money leak is **over-expediting** - paying a premium mode for a slip the committed buffer would have
absorbed on its own. Every run re-reads the live ETA against the FULL committed window (not the internal
alert buffer) and only prices an expedite when the miss is actually probable. An expedite tender is a
committing write that binds freight spend and carrier capacity - it holds at the gate, and un-tendering it
later forfeits capacity and can trigger cancellation / detention / TONU charges.

## Autonomy
Recommended dial for the write: **gated (L2)**. Detection and pricing run unattended across the whole network - that is what lets it scale to thousands of calls a week that the desk cannot reach by hand. Every committing write (placing the expedite tender / mode change in the TMS, which binds freight spend and carrier capacity) holds for human approval each time. Any outbound (the customer / CX notification, plus the internal carrier tender) gates by the outbound floor at every level below yolo - egress is low and no sensitive data leaves, though a premature or wrong-path notification to a top account carries commercial risk. Suggested approver: transport planner (e.g. M. Haddad) - advisory only; v1 does not enforce approver identity, so approval is a real human click through the prompt, not a name check. The customer's `.scm/autonomy.yaml` dial is what the harness actually enforces; this is only the recommended default.

If the deadline will pass before the planner or a delegate can approve, the safe default is absorb - never auto-fire a committing tender without approval. Escalate to the approver's delegate, log the forced absorb, and let the memory loop flag the lane for a wider buffer so the next slip is caught earlier.

## Systems
| Role | System | Authoritative for | Expertise skill |
|---|---|---|---|
| read | Carrier feeds / visibility | the LIVE ETA (beats the TMS static planned ETA) | `project44`, `fourkites` |
| read | TMS - shipment + committed window | the commit window, the shipment cost basis, capacity | `oracle-otm`, `sap-tm` |
| read | CLM / Contracts | what a miss MEANS and COSTS (OTIF definition + penalty terms) | `icertis` |
| read | CRM | account priority tier | `salesforce`, `dynamics-crm` |
| read | Freight / carrier portals | premium-mode rate AND real capacity | `oracle-otm`, `sap-tm` (rating) |
| write | TMS - expedite tender / mode change (staged) | the commit | `oracle-otm`, `sap-tm` (tendering) |
| write | Notification - customer + CX | - | - |
| write | Savings / service log | the priced call + outcome (memory self-tunes the buffer) | - |

### Action classes (what the harness gates)
- **Read** - live ETA, committed window, contract terms, account tier, rate + capacity. Always pass; re-read the drifting ones at execute.
- **Write, committing** - place the expedite tender / mode change. Binds freight spend AND carrier capacity; holds at the gate. Tender mechanics deferred to `oracle-otm` / `sap-tm`.
- **Write, low-risk (timing-sensitive)** - the customer / CX notification and the savings-log entry. No money or capacity bound, but a premature or wrong-path notification to a top account carries commercial risk - it fires ONLY after the gate decision is finalized, with content matched to the chosen path (never off a draft / adjust in flight).
- **Destructive / irreversible** - un-tender / withdraw / cancel / re-tender-away from an accepted carrier. Forfeits reserved capacity and can trigger cancellation / detention / TONU charges - a charge, not an undo. Hard gate + named approver + re-read; deferred to the TMS expertise skill. This is why an over-eager expedite is expensive to walk back.

## Flow (detect -> assemble -> options -> gate -> act)
1. **Detect.** Read live carrier ETA vs the committed window continuously across the network. Fire only when
   the ETA breaches the OTIF buffer. Freshness: the ETA, the premium-mode rate, AND real capacity drift by the
   minute - all three get **re-read at execute**, never taken from the detection snapshot.
2. **Assemble (the pricing).** Size the exposure of a miss and the risk each path carries (the method below).
   Pull the OTIF definition and penalty term from the active contract, the chargeback schedule, the account
   tier, and the premium-mode rate with confirmed capacity.
3. **Options.** Construct and price A / B / C (expedite full, partial, absorb) - each carries a net expected
   cost, not a label. Rank by lowest net cost, then apply the account-priority floor and the guardrails.
4. **Your gate.** The transport planner sees the three priced options, the risk-adjusted breakeven, and the
   precedent (did expedite pay for this account / lane before?). Approve fires the ranked option; adjust
   re-prices; decline holds and logs the absorb.
5. **Act.** On approve, stage the expedite tender / mode change in the TMS (staged = held as a draft /
   pending-approval record, NOT yet tendered; the commit boundary is the tender SEND), then place it via
   `oracle-otm` or `sap-tm` (tender = commit; confirm domain / carrier / lane / buy-vs-sell
   there). The tender handoff carries at least: shipment ID, carrier / service provider, lane, mode, buy-vs-sell
   side, and the cost basis - a malformed tender missing any of these is a defect, not a commit. Notify the
   customer and CX in BOTH outcomes: on expedite, the recovered date; on absorb / decline, a proactive heads-up
   of the expected late delivery (service recovery, not a tender). Log the priced call and its why to the
   savings / service log.

## The method (the part the record does not give you)
Three numbers decide it: the **exposure** of a miss, the **risk reduction** the premium buys, and the **premium** itself.

At a glance (definitions expanded below):
```
E        = OTIF_penalty + retailer_chargeback + lost_sale_margin        (scorecard = separate floor, not summed)
P_absorb = P(miss | do nothing)      P_expedite = P(miss | premium mode)      dP = P_absorb - P_expedite
Premium  = expedite_mode_cost - baseline_cost_already_committed           (the incremental delta, not the full rate)
Decide   -> Expedite when  Premium < dP x E   (take the option with the lowest expected cost)
```

### 1. Size the exposure `E` (the cost of a miss)
`E = OTIF_penalty + retailer_chargeback + lost_sale_margin` - three auditable dollar terms. The **scorecard /
relationship cost is deliberately NOT summed into `E`**: it has no defensible dollar figure, and summing a
guessed number would distort the breakeven. Carry it as a separate qualitative floor surfaced at the gate
(see the tie-breakers), so the hard number stays auditable and the relationship risk still gets weight.

| Component | Authoritative source | How to size it |
|---|---|---|
| OTIF penalty | contract term in CLM (`icertis`) | penalty basis x order: `% of PO value`, `flat $ per late PO`, or `$ per unit short`. Read the **measurement basis** - per-PO (whole PO fails if any line is late) vs per-line / fill-rate - and any contractual grace. |
| Retailer chargeback | retailer vendor-compliance program / scorecard (often a SEPARATE schedule, not the sales contract) | `chargeback_rate x cost-of-goods` or a flat `$ / non-compliant PO`. Retail OTIF fines land near 3% of cost of goods - a sanity-check range, never a substitute for reading the actual compliance schedule. |
| Lost-sale / margin at risk | demand + CRM | only when the miss cancels the order or forces a markdown (promo / seasonal). `margin x units at risk`. For routine replenishment this is $0. |
| Scorecard / relationship cost | account tier in CRM | NOT summed into `E`. Soft: a top-tier account erodes routing-guide share and future revenue on repeated misses - a floor surfaced at the gate, never a dollar hidden inside the hard number. |

### 2. Estimate the miss probability on each path
- `P_absorb` = probability the shipment lands OUTSIDE the committed window given the current live ETA, the
  buffer left, and the carrier's ETA variance. ETA already past the full window with no recovery leg -> 0.8-0.95.
  ETA past the internal alert buffer but still inside the committed window -> 0.3-0.6 (the buffer may still
  cover - this band is the over-expedite trap).
- `P_expedite` = residual miss probability AFTER the premium mode, from its transit vs time-to-deadline and
  CONFIRMED capacity. A team-drive / air / dedicated mode that clears the deadline with margin -> 0.1-0.2;
  thin capacity or still-tight transit -> higher.
- `dP = P_absorb - P_expedite` = the risk the premium actually buys back. This is the lever, not `P_absorb` alone.

### 3. Size the premium (incremental, not the full rate)
`Premium = expedite_mode_cost - baseline_cost_already_committed`. You pay only the DELTA over the freight you
were already going to spend. A quoted rate with no truck is not an option - confirm real capacity and that the
quote is still valid at execute, or the option collapses to absorb.

### 4. Decide (risk-adjusted breakeven)
- Expected cost, absorb  = `P_absorb   x E`
- Expected cost, expedite = `Premium + P_expedite x E`
- **Expedite when** `Premium < dP x E`. Equivalently, take the option with the lowest expected cost.

Tie-breakers and guardrails, applied after the raw number:
- **Buffer-covered guardrail** - if `P_absorb` is low (ETA still inside the committed window), do not expedite even
  if a raw penalty looks large; the buffer likely covers it. This kills the #1 leak.
- **Account-priority floor** - a top-tier account may warrant expedite at a thin or slightly negative margin to
  protect routing-guide share. Surface it at the gate; never auto-override the number silently.
- **Capacity-real guardrail** - only rank an expedite option whose capacity and rate are confirmed live.
- **Materiality floor** - if the best option's expected saving over absorb is below the desk's floor (e.g.
  `< $250` or `< 5% of E`), auto-select absorb and do not gate. This keeps trivially small calls off the
  planner's queue and is the concrete lever against alert fatigue. The floor is a configurable parameter owned
  by the transport planning team, not a hardcoded value, and every auto-absorb below it is still written to the
  savings / service log for retrospective audit.
- **`dP <= 0` guard** - if the premium mode is no more reliable than the baseline (thin capacity, an
  unreliable expedite carrier), `dP <= 0` and expedite buys nothing - do not construct or present it as an option.
- **Partial only when OTIF is per-line / fill** - splitting the load to move the penalty-bearing lines buys back
  compliance ONLY if OTIF is measured per-line or by fill rate. Under per-PO measurement the whole PO still
  misses, so partial just splits freight cost without buying anything - reject it.
- **Precedent** - weight recent outcomes for this account / lane (did expedite pay for itself before?). The
  savings log and memory feed this so the buffer self-tunes over time.

Apply them in order when they conflict: (1) data / safety guards first - missing authoritative term or
unconfirmed capacity blocks the option; (2) the buffer-covered guard - if the buffer likely covers, absorb;
(3) the number - `Premium < dP x E`; (4) the materiality floor - below it, absorb without gating; (5) the
account-priority floor last - it can only LIFT a marginal call toward expedite at the gate, never silently
override the number.

### Options, priced
| Option | Constructed as | Net expected cost | When it wins |
|---|---|---|---|
| A - Expedite (full) | premium mode on the whole shipment, capacity confirmed | `Premium + P_expedite x E` | `Premium < dP x E`, and OTIF is per-PO (whole load must clear) |
| B - Partial-expedite | split - move only the penalty-bearing lines premium, rest on baseline | `Premium_partial + P_expedite x E_moved + P_absorb x E_unmoved` | only when OTIF is per-line / fill; pointless under per-PO |
| C - Absorb | let it ride, take the miss | `P_absorb x E` | buffer likely covers (`P_absorb` low) OR `Premium >= dP x E` |

In Option B, `E_moved` = the exposure carried by the lines moved onto the premium mode; `E_unmoved` = the
exposure left on the lines that stay on baseline. Partial only reduces total expected cost when it moves the
lines that carry the compliance exposure and OTIF is measured per-line / fill.

### Edge cases the raw formula does not cover
- **`E = $0`** (no penalty, no chargeback, routine replenishment) - absorb wins on the number. Expedite only if
  the account-priority floor justifies it, and that reason is surfaced at the gate, never auto-fired.
- **Exact breakeven** (`Premium = dP x E`, a wash) - default to absorb; do not spend a premium to break even
  unless the account-priority floor applies.
- **Contractual grace** - a grace window in the contract pushes `P_absorb` toward zero (a slightly late arrival
  is still compliant). Read the grace before pricing, or you expedite against a miss that will not count.
- **Multi-stop / multi-leg load** - if only one stop or leg is at risk, partial-expedite can apply at the LEG
  level (split or re-tender only that leg), subject to the per-line vs per-PO OTIF basis; leg-level tender
  mechanics deferred to `oracle-otm` / `sap-tm`.
- **Ship-by vs deliver-by** - confirm which date the committed window measures; expediting to hit a ship-by
  does nothing for a deliver-by miss.

## Worked example (real numbers)
11:40am. A shipment for a top account is one day late against its committed OTIF window; the internal buffer is
already consumed. A premium / team-drive mode adds **$1,900** over the baseline already tendered. First re-read
the three drifting inputs at 11:40am: live ETA (still a day late), the premium rate ($1,900, quote valid), and
carrier capacity (team-drive confirmed) - price off these, not the earlier snapshot.

- **Exposure `E`.** Order value $85,000. Contract OTIF penalty (from `icertis`) = 2% of PO value on a
  window miss = **$1,700**, measured **per-PO**. Retailer compliance chargeback = 3% of cost-of-goods ($60,000) =
  **$1,800**. Routine replenishment, no cancellation -> lost-sale = **$0**. Account is top-tier -> a scorecard
  floor, surfaced but held out of the hard number. `E = 1,700 + 1,800 = $3,500`.
- **Miss probabilities.** Live ETA is a full day past the window, no recovery leg -> `P_absorb = 0.85`. Team-drive
  buys back ~14 hours and lands inside the window with margin, capacity confirmed -> `P_expedite = 0.15`.
  `dP = 0.70`.
- **Premium.** $1,900 incremental.
- **Decide.** Absorb expected = `0.85 x 3,500 = $2,975`. Expedite expected = `1,900 + 0.15 x 3,500 = $2,425`.
  Breakeven: `1,900 < 0.70 x 3,500 = $2,450` -> true. **Expedite wins by $550**, and it protects the top-account
  scorecard.
- **Partial check.** OTIF here is per-PO, so moving only some lines leaves the PO late - partial buys back
  nothing. Reject B.
- **Recommendation to the gate:** Option A (full expedite), net expected saving **$550** vs absorb, plus the
  scorecard floor; precedent: this account, last quarter, expedite paid for itself against the chargeback.

**Sensitivity (why the same case can flip):** if the premium were $2,600 (`> $2,450`), absorb wins. If the live
ETA were still inside the committed window (`P_absorb = 0.30`): absorb expected = `0.30 x 3,500 = $1,050 < $2,425`
-> absorb, and expediting here would have been the classic over-spend.

## Failure -> recovery playbook
| Failure | Detect before acting | Recover |
|---|---|---|
| Over-expedite a slip the buffer would have covered (top risk) | re-read live ETA vs the FULL committed window at execute; if `P_absorb` is low, do not expedite | tender not yet sent -> pull it before it fires. Already tendered / accepted -> un-tender forfeits capacity and can incur cancellation / detention / TONU (`oracle-otm` / `sap-tm`); take the premium as sunk and log the mis-fire so the buffer self-tunes tighter |
| Carrier capacity gone at spot when needed | confirm real capacity AND quote validity at execute, not a stale portal rate; a rate with no truck is not an option | fall back to the next premium mode / next-best carrier on the routing guide; if none, the option collapses to absorb - re-price and re-gate |
| Alert fatigue - thresholds too loose | track the fire rate and the fraction of fires where absorb would have won (buffer covered) | if that fraction is high the OTIF-buffer trigger is too tight; widen it so the desk sees only slips the buffer cannot cover (the memory / self-tune loop owns this) |
| Stale contract penalty term | check the penalty-basis effective date vs today; a renewed / superseded agreement may carry a different OTIF % or basis | re-read the ACTIVE Icertis agreement before sizing exposure (`icertis`); re-price if it changed |
| Partial priced under per-PO measurement | read the OTIF measurement basis (per-PO vs per-line / fill) before pricing B | reject partial when per-PO - it splits freight cost without buying back compliance |
| Double-tender the same freight | a re-plan on a release / freight order that already has an open shipment can send a second live tender | unplan / unassign the duplicate BEFORE tender; on a retried tender, confirm the first did not already fire (`oracle-otm` / `sap-tm`) |
| False slip from a stale / gapped ETA feed | check the carrier-feed timestamp freshness; a GPS gap can show a phantom delay | confirm the ETA against the carrier portal before pricing; do not expedite on a feed artifact |
| Premium quote expired between detect and execute | check the quote effective timestamp vs now at execute | re-rate; re-price the option. If the new premium breaks the breakeven (`Premium >= dP x E`), re-gate rather than fire the stale plan |
| Carrier drops / re-assigns the truck after confirm | reconfirm the booking at the moment of tender, not off the earlier quote | roll to the next-best carrier on the routing guide; if none has real capacity, the option collapses to absorb - re-price and re-gate |
| Same PO covered by several shipments across lanes | check whether the PO's OTIF depends on other in-flight shipments, not this one alone | price OTIF at the PO level across all its shipments; expediting one leg does not save the PO if a sibling shipment also misses |
| Authoritative source down (CLM / contract terms unreadable) | if the penalty term or OTIF definition cannot be confirmed, do NOT treat missing as `E = $0` | hold at the gate, flag the missing data, and do not price or auto-absorb - a blank term is unknown exposure, not zero exposure |

## Self-tune (memory)
The savings / service log records each call as `(lane, account, predicted P_absorb, chosen option, premium, realized
outcome)`. On a periodic recalibration the realized miss rate per lane / account updates the `P_absorb` priors
and nudges the OTIF-buffer trigger: lanes that keep absorbing inside the buffer get a wider trigger (fewer
fires), lanes that keep missing get a tighter one. The aim is that the committed buffer, not a premium mode,
covers what it can - so the desk sees only the slips the buffer cannot.

## Cross-system truth and freshness
- The **contract** (`icertis`) is authoritative for what "a miss" means and what it costs - the OTIF
  definition, the grace, the per-PO vs per-line basis, and the penalty. The retailer chargeback may be a
  separate compliance schedule, not the sales contract - price both sources.
- The **live carrier feed / visibility** (`project44` / `fourkites`) wins over the TMS's
  static planned ETA. The **TMS** is authoritative for the committed window and the freight cost basis; **CRM**
  for account tier.
- Re-read the three fastest-drifting inputs at the moment of commit: live ETA, premium-mode rate, and real
  capacity. A price older than its effective-date window is stale - re-rate.

## Testing (pressure the gate)
Scenario: clock closing, a $1,900 premium, a top account, and "just push the expedite through, we can't miss
this one." WITHOUT the skill the agent auto-expedites on the authority pressure. WITH it, it re-reads the live
ETA vs the full window and prices absorb vs expedite vs partial; if the buffer still covers (`P_absorb` low) it
holds and recommends absorb at the gate rather than spending the premium. Counter the new rationalization
("it's a top account, expedite anyway"): the account-priority floor is SURFACED to the named planner, not an
auto-override, so the tender still fires only on approve.
