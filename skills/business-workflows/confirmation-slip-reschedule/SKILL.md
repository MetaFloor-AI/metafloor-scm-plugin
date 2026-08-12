---
name: confirmation-slip-reschedule
description: "Take a single supplier confirmation slip (an EDI 855 order acknowledgment) on a PO, peg it forward through MRP to the affected production / work orders and customer commitments, size the downstream impact by week and by customer, and price the reschedule options (accept the slip and re-time the build, expedite or dual-source an alternate, split, escalate a pull-in, or hold and absorb) for a buyer to approve. Use when an EDI 855 or supplier-portal acknowledgment confirms a PO date later than promised (a lead-time slip), when a confirmed date lands past its committed need date, when someone asks which work orders or customer commits move, whether to dual-source or re-time or absorb, or mentions uc-resched-slip, confirmation slip, PO date change, schedule-line confirmation, MRP pegging, reschedule-in / reschedule-out, expedite spend, over-expediting, penalty commit, or a slipped critical component."
---

# Confirmation slip -> downstream reschedule: peg it before it becomes a line-down

Use case `uc-resched-slip`. A supplier's order acknowledgment (EDI 855) confirms a PO three weeks late - 11
weeks against an 8-week lead time on a critical component - and it lands quietly in a mailbox during a demand
uptick. The build plan and the customer commitment still assume the old date, so the shortage is invisible
until it is a line-down six weeks out. This skill runs the forward peg no one runs by hand the day the slip
lands, sizes the exposure by week and by customer, and prices the reschedule options, so the cheap-options
window is used instead of missed.

## Read this first
Two opposite mistakes cost the money here, and the method exists to avoid both:
- **Over-reacting to a soft date.** Expediting or dual-sourcing a slip that existing buffer plus internal
  build slack would have absorbed on its own burns premium for nothing. This is the #1 leak - do not price an
  expedite until the peg proves a HARD commit is actually breached.
- **Missing a hard customer commit.** Letting a penalty-bearing or contractual commit slip silently because
  no one traced the slip forward. A hard commit that goes short must surface with its penalty priced at the
  gate, never buried.
The revised PO is **staged for release, not released** - the commit boundary is the release, and the outbound
supplier notification is gated. Nothing binds money or reaches the supplier before the buyer approves.

## Autonomy
Recommended dial for the write: **gated (L2)**. Detection and pegging run unattended across every open PO - that is what lets it catch the slip the day it lands instead of at shortage time. Every committing write (the revised PO staged in SAP, the build-sequence change in the plan) holds for human approval each time. Any outbound (the supplier + planning notification, and any supplier pull-in outreach) gates by the outbound floor at every level below yolo - the outbound touches the supplier, and a premature "we need to pull this in" or a silent dual-source-away can strain the relationship or trigger a re-quote. Suggested approver: buyer (e.g. J. Rivera) - advisory only; v1 does not enforce approver identity, so approval is a real human click through the prompt, not a name check. The customer's `.scm/autonomy.yaml` dial is what the harness actually enforces; this is only the recommended default.

## Systems
| Role | System | Authoritative for | Expertise skill |
|---|---|---|---|
| read | Supplier portal / EDI 855 | the confirmed date, the slip, the ACK line status | portal / EDI feed |
| read | SAP / ERP (PO) | the PO commitment, the posted confirmation, on-hand, firmed inbound, the forward peg | `sap-mm` (PO / MRP pegging) |
| read | Planning | time-phased net demand/supply, weeks of cover, CTP on an alternate | `kinaxis` (replan) |
| read | MES | the real line schedule + WIP state (can the build actually re-sequence?) | `siemens-opcenter` (line schedule) |
| read | Outlook | where the 855 landed | mailbox |
| write | SAP - revised PO staged for release | the commit | `sap-mm` |
| write | Plan - build sequence | the re-time | `kinaxis` |
| write | Notification - supplier + planning (once) | - | - |

### Action classes (what the harness gates)
- **Read** - the 855, the PO + posted confirmation, on-hand + firmed inbound, the forward peg, time-phased
  demand/commit, WIP state. Always pass; re-read the drifting ones (stock, WIP, live commit, latest 855) at execute.
- **Write, committing** - releasing the revised PO. Crossing a release threshold on the change re-triggers the
  release strategy (see `sap-mm`); the mechanics are deferred there. Holds at the gate.
- **Write, reversible (conditionally)** - staging the revised PO in SAP as a draft (not released) and editing
  the build sequence in a Kinaxis scenario. Reversible only while it stays a draft / scenario edit: to roll
  back, delete the draft PO before release and revert the scenario edit before publish. **This is reversible
  ONLY if plant config suppresses supplier output and the MRP planning-file update on a draft change; otherwise
  a draft change can fire output to the supplier or re-trigger MRP and is a committing write.** Check config
  before treating a staged change as safe to roll back; hold the draft so it does not reach the supplier or feed
  MRP until release (mechanics deferred to `sap-mm`). Still gated - they feed the decision.
- **Write, committing (plan)** - **publishing** the build-sequence change promotes it into the shared baseline
  and can release dependent orders to ERP; downstream engines consume it once published. That is a committing
  action, not a reversible flag - it holds at the gate, mechanics deferred to `kinaxis`.
- **Write, irreversible egress** - the supplier + planning notification, and any supplier pull-in outreach
  (option C). Cannot un-send; fires once, after the gate, on the approved option only - never off a draft in flight.

## Flow (detect -> assemble -> options -> gate -> act)
1. **Detect.** Fire event-driven on each inbound 855 (with a periodic sweep of open POs as a backstop for
   confirmations the mailbox never surfaced), cross-check the confirmed date against the live plan, and validate
   it before trusting it (below). Freshness: time passes between detect and act, so re-read on-hand, firmed
   inbound, WIP state, the live commit, and the latest 855 at execute - a slip decided on a stale peg over-buys or misses.
2. **Assemble.** Run the validate -> peg-forward -> size -> classify method below. This is the stage no one
   runs by hand: peg the slipped receipt forward to the work orders and customer commits it feeds, and size the
   shortage by week and by customer.
3. **Options.** Construct and price each path (accept + re-time, expedite/dual-source the covering slice, split,
   escalate a pull-in, hold + absorb) - each carries a number, not a label. Rank by lowest cost that still
   protects every hard commit.
4. **Your gate.** The buyer sees the sized exposure, the priced options, and precedent (prior recorded reschedule
   calls for this part / supplier, pulled from the decision log this skill writes in step 5). Approve fires the
   ranked option; adjust re-prices; decline holds and logs the absorb with its penalty.
5. **Act (on approval).** Stage the revised PO in SAP for release (`sap-mm`), flag the build-sequence
   change (`kinaxis`), and notify supplier + planning once. Record the rejected options and the chosen
   one with a name and timestamp so next quarter's squeeze starts from this call, not from scratch.

**When the gate is closing and the buyer is unreachable (a hard commit cannot age out).** Time-box the gate to
the hours left in the cheap-options window (`weeks to shortage - alternate lead time`). If a **hard** commit is
breached and the named buyer does not respond, route to the backup approver and escalate to the planning
manager - a penalty-bearing breach must not sit unowned at the gate until it is a line-down. the gated dial
never fires a committing write on its own, so if no one approves before the window closes, hold, log the missed
window as the outcome, and keep the cheap options priced for the escalation. A missed cheap window is
recoverable at higher cost later; an unapproved commit or a silent hard-commit slip is not.

## The method (the part the record does not give you)
State moves one way; report which state you are in so the work resumes after an interruption, and never jump to
`sized` on an unvalidated slip.

| State | Trigger | Go to |
|---|---|---|
| detected | 855 validated (fresh, real change, slips past need date) | pegged |
| detected | validation fails (stale / duplicate / no real change) | **terminate** - log, no reschedule |
| pegged | exposure sized by week + customer | sized |
| sized | options priced AND every hard commit verified | options-priced |
| options-priced | buyer approves | approved (acting) |
| options-priced | buyer declines / cheap window closes | watching (logged with its penalty) |
| watching | net demand rises and re-breaches a hard commit (re-checked each sweep) | detected (re-peg, re-price) |
| any state | a later 855 supersedes | detected (re-peg on the latest) |

**1. Validate the slip (before pegging anything).** A confirmation you act on wrongly is worse than one you
missed. Three checks:
- **Fresh + not duplicate** - dedupe on `PO + line + release + transaction control number`; compare the 855
  timestamp against the last posted confirmation on that schedule line. A re-transmitted or superseded 855 is
  not a new slip.
- **A real schedule change** - read the ACK line status: `IC` (accepted with changes) or `IB` (backordered)
  with a later date is a genuine slip; `IA` (accepted, no change) is not. The confirmed date is `ACK` /
  schedule-date, not the PO's requested date.
- **Slip magnitude** - `slip = confirmed_date - committed_need_date` (the need date the PO was placed to hit,
  not the requested date if they differ), in the PO's planning-calendar unit (days or weeks - hold one unit
  through the whole run; a 3-day slip and a 3-week slip have very different mitigation paths). No slip past the
  need date -> stop, log, no reschedule.

**2. Peg forward.** From the PO's component, run the forward peg (SAP `MD04` pegged stock/requirements list,
via `sap-mm`) to every dependent work / production order and, through the finished SKU, to the
customer commitments (sales orders) they feed. Classify each pegged demand:
- **Hard** - a penalty-bearing or contractual customer commit, or a firm-pegged MTO/allocation order. Its date
  cannot move without cost.
- **Soft** - internal build sequence, anonymous replenishment, make-to-stock. Its date can flex within downstream slack.

If the forward peg returns **no dependent demand** (no work orders, no commits), the slip is absorbed by
inventory build - log it and terminate, no reschedule. Do not price an expedite on a component no one is waiting on.

**Verify the hard/soft call before pricing (highest-consequence judgment).** Misreading a hard commit as soft
is how a penalty commit goes short silently. Confirm each hard classification against the actual contract term /
sales-order commitment type, not the due date alone, before the `options-priced` state - and surface every
hard commit and its penalty at the buyer gate for confirmation. A demand you cannot verify defaults to hard.

**3. Size the exposure.** For the slipped component compute time-phased cover:
`available[week] = on-hand + in-transit + firmed inbound (net of the slipped PO at its NEW date)`. The
`shortage_week` is the first week cumulative demand > cumulative available. For each affected commit,
`units_short = demand - available` over the exposed weeks; `revenue_at_risk = units_short x ASP`;
`penalty_exposure = penalty_rate x commit_value` for each hard commit breached.

**4. Net against buffer + slack (the over-reaction guard).** Subtract what absorbs the slip for free: safety
stock, and the downstream slack that lets soft dates move.
`net_exposure = max(0, hard_commit_demand[exposed weeks] - (safety_stock_absorption + soft_date_flex))`.
**If `net_exposure = 0`, no hard commit is breached - the answer is accept + re-time; do not price an
expedite.** Only a non-zero net exposure justifies spending premium. If a partial receipt was already posted
against the PO, only the **open (un-received) quantity** moves to the confirmed date - net the received units
out before sizing, or the shortage is overstated.

**5. Price the options and decide.** Rank by lowest total cost **subject to: every hard commit is covered on
time, or its penalty is explicitly accepted at the gate.** The over-reaction guard and the alternate-feasibility
test are applied before the raw number, in that order.

## Options, priced
| Option | Constructed as | Cost | When it wins |
|---|---|---|---|
| A - Dual-source the whole qty | expedite the full PO quantity from an alternate, widen the ETA | premium x full qty | rarely - only if the slip breaches many hard commits and the primary cannot recover; usually over-buys |
| B - Accept slip + re-time + partial-expedite the covering slice | take the slip on the bulk, flex the soft build dates into slack, expedite from an alternate ONLY the units needed to cover the hard commit | premium x covering qty + re-sequence cost | the common winner - protects the hard commit at the lowest premium |
| S - Split the PO line | leave the bulk on the primary at the slipped date, divert only the covering slice to a separate source / PO line | premium x covering qty + dual receipt + dual invoice-match overhead | when the covering slice must come on a separate source line, not the same PO - carries the extra 3-way-match overhead B avoids |
| C - Escalate a pull-in | negotiate the confirmed date back with the supplier before moving volume | ~$0, uncertain | run as a parallel track; never the sole plan for a hard commit |
| D - Hold + absorb | accept the slip everywhere, let the commit slip | `P(shortage) x (penalty + lost_margin)` | net exposure small vs any mitigation cost; surface the penalty explicitly |

An expedite/dual-source option is only real if the alternate is **qualified (on the AVL), has capacity, and its
own lead time clears the hard date**. Fail any of those and the option collapses toward C or D - re-price, do
not present a source that cannot deliver. Relationship strain in D is a qualitative floor surfaced at the gate,
never summed into the dollar figure.

**Option C is human-initiated.** The agent surfaces the pull-in as an option and can draft the ask, but it
never contacts the supplier itself - a pull-in negotiation is egress and fires only after the named buyer
approves it (egress high). "Parallel track" means the buyer runs the conversation while the priced options
stand, not that the agent opens it autonomously.

## Worked example (real numbers)
PO-44821, component X, 5,000 units. Placed to a week-8 need date; EDI 855 confirms week 11. Validated: `IC`,
fresh, control number new -> genuine 3-week slip.

- **Peg forward.** X feeds work orders that build finished SKU-Y. Two demands peg off it: customer commit Y =
  1,200 units due **week 9**, contractual with an 8% penalty on a $2.5M commit; plus internal make-to-stock
  replenishment across weeks 6-11. Commit Y is **hard**; the replenishment is **soft**.
- **Size.** Weeks counted from today (week 0). Cover: on-hand 2,000 + firmed inbound 1,000 = 3,000 units of X.
  Baseline consumption 500/wk -> the on-hand + inbound runs dry in **week 6**. With PO-44821 slipped to week 11, weeks 6-10 have no fresh X. Commit
  Y draws 1,200 units of X at **week 9**, inside that gap -> 1,200 short before any netting. `revenue_at_risk`
  on Y = the $2.5M commit; `penalty_exposure` = 8% x $2.5M = **$200K**.
- **Net against buffer + slack.** `net_exposure = max(0, 1,200 - (safety_stock + soft_date_flex))`. Safety stock
  holds 300 units of X above the reorder point. The soft make-to-stock replenishment has ~2 weeks of
  finished-goods slack, so it re-times to the week-11 arrival and stops competing for the scarce X in weeks 6-9.
  Net shortage on the hard commit Y = `1,200 - 300 = 900 units` of X against its week-9 date. Non-zero -> a hard
  commit is breached, so an expedite is justified for the 900-unit covering slice only.
- **Price the options.**
  - A - dual-source all 5,000 from alternate #1, widen ETA: premium ~$36/unit x 5,000 = **+$180K**. Protects Y
    but pays premium on ~4,100 units the buffer + slack already cover. Over-buys.
  - B - accept the slip on the bulk, re-time the soft build into slack, partial-expedite the 900-unit covering
    slice from qualified alternate #2 (lead time clears week 9, capacity confirmed): premium ~$105/unit x 900 =
    ~$95K, re-sequence ~$0 (soft dates move into existing downstream slack, no overtime or setup penalty) ->
    **+$95K**. Covers Y at the lowest premium.
  - C - escalate a pull-in with the primary: $0, but no firm commit back yet - run in parallel, not as the plan.
  - D - hold + absorb: expected = P(shortage ~0.9) x ($200K penalty + lost margin) ~ **>$180K** and it burns the
    customer relationship.
- **Recommend B, +$95K**, against an avoided stockout worth multiples. Precedent shown at the gate: the last
  comparable squeeze on record, where the buyer chose the re-time + partial-expedite and it held. Reschedule
  and resequence become one decision, not two handoffs.

**Sensitivity (why the same case flips):**
| Change to the case | Result |
|---|---|
| Commit Y reclassifies hard -> soft (not penalty-bearing) AND it has ~3 weeks of slack (both together) | `net_exposure = 0` -> accept + re-time, spend $0; expediting here is the classic over-spend |
| Alternate #2 not qualified / no capacity | B collapses -> re-price to A (full dual-source) or escalate the pull-in harder |
| A second 855 slips another component feeding SKU-Y | re-peg on the combined shortage before pricing; the two slips can compound past the buffer |

## Failure -> recovery playbook
| Failure | Detect before acting | Recover |
|---|---|---|
| Acting on a stale or duplicate 855 the mailbox never surfaced | dedupe on PO+line+release+control number; compare the 855 timestamp vs the last posted confirmation | if superseded, discard and re-peg on the latest 855; nothing staged yet, so no write to reverse |
| Over-expediting when the buffer would have covered it (top leak) | compute net_exposure after buffer + soft-date flex; if 0, no hard commit is breached | do not stage the expedite - the re-time is the answer. Staged but not released -> pull it before release |
| Straining the supplier by rescheduling without a conversation | is this a pull-in or a dual-source-away that cuts the supplier's volume? | negotiate the pull-in first (option C, parallel), send ONE notification, never fire a silent dual-source-away |
| Alternate source not actually available / qualified | check AVL qualification + capacity + the alternate's own lead time vs the hard date | if it cannot clear the hard date the expedite/split option collapses -> re-price toward escalate or absorb-with-penalty |
| Peg misclassifies a soft date as a hard commit (or vice versa) | classify each pegged demand hard vs soft from the contract / commit terms, not from the due date alone | re-classify before pricing; a soft date treated as hard triggers a needless expedite |
| Revised PO release re-triggers the release strategy | does the changed value / date cross a release threshold? | it becomes a committing action -> route through the release strategy; mechanics deferred to `sap-mm` |
| Build cannot actually re-sequence on the floor | check the WO / WIP state in MES before assuming the re-time is feasible | if the WO is already in-process or past line clearance, the re-time is constrained (`siemens-opcenter`) -> re-price |
| Demand or commit shifts between sizing and the gate | re-read live demand + the commit at the gate | re-size revenue-at-risk and penalty_exposure on the fresh numbers before the buyer decides |
| A later 855 supersedes mid-flow | re-check the 855 status at execute | re-peg on the latest confirmation before staging anything |
| Several 855s slip the same component at once | aggregate every open confirmation on the component before pegging | net all confirmed dates into one time-phased supply picture and peg once on the combined shortage - do not price each slip in isolation, they can compound |
| Partial receipt already posted against the PO before the 855 | check received qty vs PO qty | only the open (un-received) balance moves to the confirmed date - net out the received units, or the shortage is overstated |
| Peg crosses into another plant / company code (STO, intra-company) | does the forward peg leave the plant? | size cover per plant, do not pool; the revised PO release may hit a different release strategy per company code (`sap-mm`) |
| Alternate's lead time / capacity shifts after the expedite is staged | re-confirm the alternate's promise date + capacity at execute, not off the earlier quote | if the alternate now misses the hard date the covering option collapses -> re-price and re-gate before release |

## Cross-system truth + freshness
The workflow owns the cross-system peg; each vendor HOW is deferred by name. `sap-mm` is
authoritative for the PO commitment, the posted confirmation, on-hand / firmed inbound, and the forward peg
(MD04, reschedule-in / reschedule-out exception messages). `kinaxis` is authoritative for the
time-phased net plan, the net-change replan, and CTP when re-timing the build or checking an alternate.
`siemens-opcenter` is authoritative for the real line schedule and WIP state - whether a production
order can actually be re-sequenced. When the plan and the ERP disagree on a date, the ERP PO confirmation is
the commitment; the plan is the consequence. Re-read stock, WIP, the live commit, and the latest 855 at execute.
If an authoritative read system is unreachable, hold at `detected` and do not proceed on stale data - a peg
sized against a system you could not read is a guess, not an exposure.

## Testing (pressure the gate)
Scenario: the slip is on a critical part, a top customer is on the line, and "just dual-source the whole PO and
move on, we can't be short." WITHOUT the skill the agent expedites the full quantity on the authority pressure.
WITH it, it validates the 855, pegs forward, nets the slip against buffer + soft-date slack, and finds only the
900-unit covering slice is truly exposed - so it prices the partial-expedite at +$95K against the +$180K
full dual-source and holds at the buyer's gate. Counter the new rationalization ("it's critical, expedite it
all"): criticality sets which commit is hard, not whether the buffer already covers the soft demand - the
number, not the adjective, decides the quantity to expedite.

## Related
- A **single** confirmation slip on one PO: this skill.
- **Two or more suppliers slipping the same commodity within days (a market squeeze):** `correlated-supplier-slip` - it sizes the category exposure across suppliers and prices a forward-buy.
- A shortage that originates several tiers upstream: `subtier-shortage`.
