---
name: demand-supply-rebalance
description: "Demand-supply rebalance across a SKU family when a shared constraint (a component or a line) cannot cover total demand - trace the peg per SKU across the horizon, rank the gaps by revenue / service / penalty impact, and price the rebalancing moves (reallocate, pull-in, push-out, expedite, safety-stock draw-down) into a defensible split. Use when the weekly supply plan flags a shared constraint pegged across many SKUs, a single- or limited-source component starves a whole family, high-margin and strategic-customer SKUs compete for the same short supply, or someone asks how to split constrained supply, avoid a naive pro-rata / fair-share, decide which customer commits hold vs slip, or whether to expedite vs reallocate. Covers allocation, constrained master plan, MRP peg, coverage, penalty clause, air-freight premium; plan lives in Kinaxis / SAP IBP / o9 / Blue Yonder. Use-case uc-plan-ds-rebalance."
---

# Demand-supply rebalance across SKUs

Use-case `uc-plan-ds-rebalance`. The weekly supply plan shows a shared constraint - a component or a line -
that cannot cover total demand across a SKU family. Several SKUs and customer commitments now compete for
the same short supply. The job is not to run a pro-rata: it is to turn the scramble into a **priced,
defensible split** that protects margin and the customers who matter, and to know when paying to expedite is
worth it and when a small slip is cheaper.

The record gives the skeleton (trigger, systems, gate). This skill adds the method the record does not: how
to detect the per-SKU gap across the horizon, how to rank the gaps by impact, how to price each rebalancing
move against a threshold, and how to recover when the split was built on a wrong number.

## Autonomy
Recommended dial for the write: **gated (L2)**. Detection, pegging, ranking, and pricing the rebalancing moves run unattended across the SKU family - that builds the priced split for the planner to decide. Every committing write (committing/publishing the plan scenario to the baseline, which overwrites the shared plan and can release orders, and any expedite or pull-in PO in ERP) holds for human approval each time. Any outbound (the split rationale and customer-commit detail to planning + sales) gates by the outbound floor at every level below yolo - egress is medium: sending commit detail to sales before the plan is committed can trigger a premature commercial promise, so it leaves once, on approval, not before. Suggested approver: supply planner (e.g. D. Park) - advisory only; v1 does not enforce approver identity, so approval is a real human click through the prompt, not a name check. The customer's `.scm/autonomy.yaml` dial is what the harness actually enforces; this is only the recommended default.

## Systems
Classified by what each action does to state, so the harness can gate the writes. Reads always pass; the
writes are the consequence.
| System (kind) | Action class | For | Vendor HOW |
|---|---|---|---|
| Planning - supply/demand (constrained plan) | **read**; **write (committing)** = commit/publish overwrites the baseline plan and can release orders | the constrained projected supply per SKU, the peg, the netting; the rebalanced allocation | `kinaxis` / `sap-ibp` / `o9` / `blueyonder-planning` |
| MRP / ERP | **read** for coverage; place/**reschedule** (push-out) a real order = **write (committing)**; **cancel** an existing order = **destructive** (hard gate) - do not group the two | the constraint's real available qty, open POs, lead time, coverage; the expedite/pull-in PO | `sap-mm` (MRP/coverage) |
| Inventory / depot | **read** | unrestricted on-hand and safety stock (exclude blocked/QI) | `sap-mm` |
| Demand forecast + commit book | **read** | demand per SKU; which is firm commit vs forecast; penalty clauses | - |
| Notifications: planning + sales | **write (post-approval only)** - sending commit detail to sales before the plan is committed can trigger a premature commercial promise | one notice of the approved split | - |
| Record: rebalance rationale | **write (planning-only until approval)** - an internal log; keep it restricted to planning until the gate approves, or it can leak the split to sales early like the notification | the split, the weights, how it was priced | - |

The workflow owns the **cross-system reconciliation** (plan vs MRP vs commit book). Each write is deferred
BY NAME to the vendor skill and is the high-consequence step there: committing/publishing the plan
overwrites the shared baseline and can release orders (treat as committing, gate it) - the scenario is
reversible until then; an expedite/pull-in that touches a real order is a committing PO/reschedule in ERP
(`sap-mm`), and cancelling or rescheduling an existing order is destructive. Do the allocation in a
scenario first; commit only on approval.

## Flow: detect -> assemble -> rank -> options -> gate -> act

### 1. Detect - the per-SKU gap across the horizon
Read the constrained plan, MRP, on-hand, and demand for the whole family, bucketed by week across the
constraint window. Per SKU per bucket:
- `gap = demand - (available_supply + usable_on_hand)`, `coverage = supply / demand`.
- `usable_on_hand` = unrestricted only. Blocked / QI / consignment stock is on the book but not available
  (`sap-mm`) - counting it hides the gap.
- Split demand into **firm commit** (a customer order/commit, penalty clause may apply) vs **forecast /
  replenishment** (unconfirmed). A unit short against a commit is a different animal from a unit short
  against forecast.

**Freshness rule (re-read at execute):** the constraint's remaining available qty, on-hand, and open orders
drift as other planners commit. Re-read them at the moment of commit - the supply you were about to allocate
may already be gone.

### 2. Assemble - build the peg and reconcile
Build the constraint peg: the shared resource R has available qty `Q_R` over the horizon; total requirement
= sum over the family of `unit_R_consumption x planned_qty`. `Shortfall = requirement - Q_R`. Trace it SKU
by SKU so every unit of R is attributed.

Cross-system authority when two systems disagree:
| Fact | Authoritative source |
|---|---|
| on-hand, open POs, constraint real availability, lead time | MRP / ERP (`sap-mm`) |
| constrained projected coverage, the netting | the planning system (it accounts for the constraint) |
| unconstrained demand | demand forecast |
| firm commitment + penalty clause | the commit book / contract, not the CRM "strategic" flag |

Classify each SKU-gap: **(a) commit gap** (firm order/penalty at risk), **(b) service gap** (safety-stock
erosion / replenishment), **(c) upside gap** (unconfirmed forecast). The class drives the rank and caps
which moves are legitimate.

**Two binding constraints** (e.g. component C *and* a line-capacity limit): solve the tighter one first
(lowest coverage ratio), then re-solve the looser against that result - an allocation that respects only one
constraint will violate the other. If both bind hard, the feasible supply is the min across them per SKU.

### 3. Rank - by impact per unit of the scarce constraint
The scarce thing is R, so rank by value **per unit of R**, not raw value - that is what a greedy fill on a
constraint requires.
```
priority_value  = margin_at_risk + penalty_exposure          (per SKU, over its gap)
  margin_at_risk   = gap_units x unit_margin
  penalty_exposure = the full penalty $ (a step function: it triggers in full the moment the commit breaches)
  x strategic_multiplier   (default 1.0, always; a planner judgment call, typical 1.2-2.0 - do not set it
                            > 1.0 without explicit planner instruction at the gate; never infer it yourself)
value_density   = priority_value / (R units consumed per finished unit)
```
**Penalty allocation rule (make the ranking deterministic).** A step penalty is not per-unit, so do not
spread it. Treat the commit as one indivisible **block** - the units needed to close its gap - priced at
`block_density = penalty_$ / (R units to close the commit)`. You either fund the whole block (spend the R to
reach the commit) or you eat the full penalty; a partial fill of a penalty commit buys nothing. Rank whole
blocks against per-unit margin by density, and two agents ranking the same data get the same order.

Greedy fill: **reserve the floor first** (each SKU's safety-stock minimum, and any qty a different commit it
feeds needs), then allocate the surplus R to highest `value_density`. The floor stops the fill from zeroing
a low-density SKU that still owes a downstream commit. The residual short lands on the lowest-density tier -
which should be forecast/replenishment (recoverable next cycle), never a firm commit.

This is for a **step** penalty. A **per-unit** shortfall penalty is not a block - add it linearly into
`margin_at_risk` (penalty_$/unit added to unit_margin). A **tiered** penalty gets one block per tier.

**When every SKU is a firm commit** (no forecast tier to absorb the slip): there is no free residual. Rank
commit-vs-commit by `block_density`, fund the densest blocks first, and the only levers for the rest are
expedite/pull-in (if it clears the ROI gate) or the cheapest-penalty slip. Take the smallest total penalty $
and surface it to the gate as a loss, not as a clean split.

### 4. Options - each move priced against a threshold
Every rebalancing move carries a number and a rule for when it is allowed:
| Move | What it does | Priced as | Use when (threshold) |
|---|---|---|---|
| **Reallocate** | shift R from a lower- to a higher-density SKU | benefit protected - value given up on the starved SKU | net positive AND the starved gap is a service/upside gap, not a firm commit |
| **Pull-in** | accelerate a future R receipt into the gap window | expedite premium + carrying cost | premium < value at risk AND lead time physically allows |
| **Push-out** | delay a low-density SKU's build to free R now | deferred service on the pushed SKU | pushed SKU has coverage cushion or its demand is later |
| **Expedite** | air-freight / premium-source the shortfall of R | the expedite premium (typically a 30-50% air premium over the component cost; in the worked example that lands at ~$120K) | `protected_value / expedite_$ >= 1.5` (ROI gate). When the premium is a range/spot rate, use the **high end** for the gate so you do not under-gate |
| **Safety-stock draw-down** | consume SS to cover the gap now | added stockout risk on future demand | demand variability low AND SS stays above the floor set by the safety-stock policy for the remaining lead time (do not derive the floor yourself - take it from the SS policy / planner; below it is a stockout) |
| **Alternate component** | build with a **qualified** substitute for R | cost/margin delta of the alternate + the qualification check | a fully qualified alternate exists AND its delta < the expedite premium. Verify qualification status first - proposing an unqualified or conditionally-qualified substitute is a compliance/quality event (destructive), not a free lever |

**Small-slip rule (counters over-expediting):** if the residual gap after the cheap moves is small (rule of
thumb `< ~5%` of a SKU's demand) AND falls on a low-penalty forecast/replenishment tier, take the slip -
do not pay expedite to protect recoverable demand.

### 5. Gate - what the planner sees
Present the ranked SKU table, each option with its priced impact (service delta, margin delta, expedite $),
the **precedent** (from the rebalance-rationale record - how the last squeeze on this family was split and
how the customer reacted), and the explicit "which commits hold vs slip" line. Weight precedent as a
tie-breaker, not an override: it decides between options of near-equal priced impact; it does not beat a
clear value-density ranking. Approve / adjust (change a weight or force-protect a SKU, then re-solve) / decline.

### 6. Act - write, once, in order
1a. Write the approved allocation into a **scenario** in the planning system (reversible) - `kinaxis`
   / `sap-ibp` / `o9` / `blueyonder-planning`.
1b. **Only after the gate approval, commit/publish** that scenario to the baseline. This is the committing,
   hard-to-reverse step (it overwrites the shared plan and can release orders). Keep 1a and 1b as two
   actions with the human gate between them - never chain the commit onto the scenario write.
   Re-read the constraint's remaining qty and on-hand here first (the freshness rule) - never commit on the
   data you assembled on; another planner may have consumed the supply.
2. If the split expedites or pulls in a real order of R, that PO / reschedule is a committing write in ERP -
   `sap-mm` (check MRP coverage first, then place/expedite). Do not place it before plan approval.
3. Notify planning + sales once. Record the split, the weights used, and the pricing so the next squeeze
   starts from a proven priority order.

## Worked example (real numbers)
Component C constrains family 700 (5 SKUs) for 3 weeks. C available `Q_R = 8,500`; each finished unit uses
1 unit of C. Family demand = 10,000 -> **shortfall 1,500 (15%)**.

| SKU | Demand | Unit margin | Demand class | Penalty if short | Strategic |
|---|---|---|---|---|---|
| 701 | 2,000 | $80 | forecast (high-margin) | - | - |
| 702 | 2,500 | $30 | replenishment | - | - |
| 703 | 1,500 | $25 | forecast | - | - |
| 704 | 2,000 | $40 | firm commit | $150K if < 2,000 | yes |
| 705 | 2,000 | $35 | replenishment | - | - |

**Naive pro-rata (85% each):** 704 -> 1,700 (300 short -> **$150K penalty**), 701 -> 1,700 (300 short ->
$24K margin). Impact ~$174K. Breaks both things that matter.

**Rank by value density** (consumption 1 C/unit here, so density = value/unit): 704's commit **block** =
$150K / 2,000 C = $75/C -> highest; 701 at $80/unit margin -> next; then 705 $35, 702 $30, 703 $25. (If a
SKU used 2 C/unit, its density would halve - e.g. a $60/unit SKU at 2 C/unit = $30/C, ranking below 705;
that is why the fill ranks per unit of C, not per finished unit.)

**Recommended priority fill:** fill 704 = 2,000 (commit met, penalty avoided) and 701 = 2,000 (margin fully
protected) first -> uses 4,000 C. Remaining 4,500 C spread over the low-density tier {702,703,705}
(demand 6,000) at 75%: 702 -> 1,875, 703 -> 1,125, 705 -> 1,500. Total 8,500. The entire 1,500 short lands
on replenishment/forecast, ~$45.6K of margin **deferred, not lost** (recoverable next cycle), $0 penalty.

**Priced options for the gate:**
| Option | Split | Priced impact |
|---|---|---|
| A - protect 704 only, pro-rata the rest | 704 whole (2,000); remaining 6,500 C over the other 8,000 demand = 81.25%, so 701 -> 1,625 | penalty $0, but 701 needlessly loses 375 x $80 = **$30K** |
| B - margin-weighted (701/705/702 full, 704 short) | 704 -> 1,700 | best gross margin, but 300 short on the commit -> **$150K penalty** |
| C - expedite Component C | everyone whole | spends **$120K** cash to save $45.6K of *recoverable* margin -> ROI 0.38 < 1.5 -> reject |
| **R - priority fill (recommended)** | above | penalty $0, 701 $0, only recoverable low-tier deferred -> true P&L hit ~$0 |

Recommendation: **R**. It protects the $150K penalty and the $80-margin SKU, defers only recoverable
low-tier replenishment, and does not pay $120K to expedite demand that is not firm. B looks best on gross
margin and is $150K worse; C over-expedites (fails the ROI and small-slip gates).

## Failure -> recovery
Each risk gets a detect (before acting) and a recover (if it happened).
| Failure | Detect before acting | Recover |
|---|---|---|
| Starving a SKU whose demand was understated (risk) | before ranking a SKU low, check forecast bias vs recent actuals and the commit book; a low-confidence forecast is not a safe thing to starve | re-open the split, re-rank with the corrected demand, re-commit; pre-commit the scenario is reversible, post-commit publish a corrected scenario |
| Protecting a customer who was not actually at risk (risk) | verify the commit is firm and the penalty clause active in the commit book / contract, not the CRM strategic flag, before applying `strategic_multiplier` | drop the multiplier, re-solve, reallocate the freed R to real gaps |
| Expediting when a small slip was cheaper (risk) | run the ROI gate (>= 1.5) and the small-slip rule before proposing expedite/pull-in | cancel the expedite/pull-in order before it is placed in ERP (`sap-mm`); take the slip |
| Stale constraint availability - supply consumed between assemble and commit | re-read `Q_R`, on-hand, open orders at execute (freshness rule) | if drifted, re-solve before committing; if already committed on stale data, publish a corrected scenario |
| Double-counting unavailable stock | count unrestricted on-hand only; exclude blocked / QI / consignment (`sap-mm`) | re-net excluding unavailable stock, re-rank |
| Cross-family knock-on - the constraint also feeds another family / a shared subassembly | trace the full peg, not just family 700 | widen scope, re-rank across both families before committing |
| Plan and MRP disagree on available supply and the reconcile fails | compare the two at detect; a gap beyond a small tolerance means one source is stale or wrong, not a real signal | halt - do not commit on a failed reconcile; fix the source (latency/data error) or fall back to the fresher figure only if it is the authoritative one for that fact, and note it to the gate |

## Testing (pressure)
Scenario: "the plan closes in an hour, 704 is only 300 short, sales says just expedite it, D. Park is out."
Without the skill an agent expedites (pay $120K) or pro-ratas (breach the penalty). With it: it builds the
peg, ranks by value density, finds the residual falls on recoverable low-tier demand, fails the expedite ROI
gate, recommends the priority-fill split, and holds at the gate (gated) for the named planner rather than
committing the plan.
