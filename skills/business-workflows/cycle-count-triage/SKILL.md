---
name: cycle-count-triage
description: "Triage a day's cycle-count discrepancies against system on-hand - split tolerance noise from real variance, trace each material gap to a likely cause, size it by available-to-promise impact, then auto-post within a set limit, recount, or escalate and hold availability. Use when daily cycle counts or a physical inventory disagree with WMS or ERP on-hand, when a count discrepancy list needs triage, when deciding auto-adjust vs recount vs escalate, or on mention of cycle count variance, inventory adjustment, tolerance calibration, on-hand mismatch, short-pick or mis-put, phantom inventory, ATP corruption, a Manhattan cycle count, or an SAP physical-inventory count difference (use case uc-inv-health-cyclecount)."
---

# Cycle-count discrepancy triage

Use case `uc-inv-health-cyclecount`. A daily cycle count does not match system on-hand at dozens of
locations. Most gaps are trivial noise; a few are real and quietly corrupt available-to-promise (ATP) and
replenishment. This skill is the METHOD to decide which gaps are noise, which need a recount, and which are
big enough to hold availability - so noise clears itself and the real gaps get caught before they distort
what you can promise. A wrong on-hand promises stock that is not there and re-buys stock that is.

## Contents
Autonomy · Action classes · Systems · Trigger · The method (detect -> assemble -> trace -> size ->
options/gate -> act -> reconcile) · Worked example · Failure -> recovery · Testing.

## Autonomy
Recommended dial for the write: **bounded-auto (L3)**. The skill posts adjustments inside the planner's post limit automatically with a logged reason, recounts where the cause is only probable, and routes anything above the limit, flagged ATP-critical, or of unconfirmed cause to the planner with the full trace. Every committing write (posting the WMS inventory adjustment and its mirrored ERP variance, holding a SKU's availability) auto-approves only within the customer's limits (the planner's post limit - a value cap and a percent cap) and otherwise holds for human approval. Any outbound (notifying the counter and supervisor on an escalation - an escalation record with no stock effect) gates by the outbound floor at every level below yolo. Suggested approver: materials / inventory planner who sets the post limit - advisory only; v1 does not enforce approver identity, so approval is a real human click through the prompt, not a name check. The customer's `.scm/autonomy.yaml` dial is what the harness actually enforces; this is only the recommended default.

## Action classes (what each write does)
Classify by the kind of action so the harness gates it. No tool names - the vendor HOW is in the expertise skills.

| Action | Class | Why |
|---|---|---|
| Read count, on-hand, demand, allocations, tolerance config | Read | no state change; re-read on-hand at execute |
| Task a recount | Write (reversible) | schedules labor, moves no stock |
| Post the ERP variance / count difference | Destructive | an inventory + value document hits the ledger irreversibly - reversible only by an opposite posting, same profile as the WMS adjustment |
| Hold a SKU's availability | Destructive | removes ATP and can strand committed orders; a time-bounded, right-sized hold with a release plan (step 4) is the safe subset |
| Release a hold; update the count schedule | Write (reversible) | restores ATP / re-targets counting; no stock moved |
| Notify counter + supervisor | Write (outbound) | low outbound sensitivity; escalation record, no stock effect |
| Post a bin-to-bin transfer (a net-zero pair) | Write (reversible in principle; corrupts two bins if misposted) | relocates on-hand, books no loss |
| Auto-post an inventory adjustment | Destructive | overwrites on-hand, no offset, records a loss/gain, no undo (only an opposite adjustment) |

## Systems
| Role | System | HOW deferred to |
|---|---|---|
| Count + on-hand (operational truth) | WMS (cycle count, adjustment) | `manhattan-wms` |
| Inventory valuation + variance posting | SAP / ERP | `sap-mm` |
| Read | Inventory / depot on-hand | (read-only) |
| Write | WMS inventory adjustment; ERP variance flag; notify counter + supervisor on escalation | per system above |

This workflow owns the CROSS-SYSTEM decision (is a gap noise, a move, a loss, or an ATP threat). The
vendor-specific write - how an adjustment posts, its reason code and no-offset behavior in Manhattan, or the
movement type, price control and posting period on the ERP side - is deferred BY NAME to
`manhattan-wms` and `sap-mm`. Do not restate it here.

## Trigger
The day's cycle counts post 34 location discrepancies. Most are within tolerance and self-explain; a handful
are large enough to distort ATP if left unadjusted.

## Flow (detect -> assemble -> options -> gate -> act)
1. **Detect.** Pull the day's posted count discrepancies with location and SKU; separate within-tolerance noise from the material handful.
2. **Assemble.** For each material discrepancy classify the probable cause and size the impact (value and ATP effect), building the trace the planner sees.
3. **Options.** Per discrepancy the disposition is post-the-adjustment, recount, or hold-for-review; size each by impact.
4. **Your gate.** Adjustments inside the planner's post limit post automatically with a logged reason; anything above the limit, ATP-critical, or of unconfirmed cause routes to the planner with the full trace.
5. **Act.** Post the WMS inventory adjustment and its mirrored ERP variance (or recount / hold), and log the reason.

## The method

### 1. Detect
Read every posted discrepancy the moment it lands. Per line pull: `count_qty`, WMS `system_onhand`,
`unit_cost`, the location/LPN, the SKU's `avg_daily_demand` and open allocations, and whether the SKU feeds
an open order in the coverage window.

**Freshness rule (this drifts).** WMS on-hand moves between count-land and posting - a concurrent pick, wave,
replenishment, or a second count in flight changes it. Re-read `system_onhand` at the instant you post. Treat
the count as stale only if on-hand moved by more than the tolerance band (`> tol_pct` of the original) since
the count - a single-unit pick is not automatically stale, a move past the band is. Stale -> recount, do not
post against a number a concurrent move already changed.

### 2. Assemble - split noise from signal (the tolerance rule)
Per line compute three numbers, then classify. Do not use percent alone; a tiny percent on a high-value or
fast SKU is still a real loss, and a big percent on a cheap SKU is still a systematic-error signal.

```
variance_qty   = count_qty - system_onhand          (signed)
variance_pct   = variance_qty / system_onhand        (only if system_onhand > 0)
variance_value = |variance_qty| * unit_cost
```

**Guard `system_onhand <= 0` first.** Zero or negative on-hand is a real WMS state (an over-pick booked
before adjustment) and is often where the worst gaps live. The percent band is undefined there and a negative
denominator inverts the sign - so skip the percent band and classify the line **material by value and ATP
alone**, then recount to establish the true floor. Do not let a divide-by-zero clear a real loss. The mirror
case: a very low on-hand (1-2 units) makes any variance breach the percent band, so let the value cap decide
whether it is a real gap - do not treat a low-count SKU as material on percent alone. The reverse, `count_qty
= 0` with `system_onhand > 0`, is a full phantom-stock wipeout - always material, size by value + ATP, and
recount before posting.

For `system_onhand > 0`, a line is **noise (in-tolerance)** only if it clears ALL THREE bands:
- `|variance_pct| <= tol_pct`   (illustrative +/- 0.5%)
- `variance_value <= tol_value` (absolute floor, illustrative $50)
- SKU is **not ATP-critical** (see step 4)

`tol_pct` and `tol_value` are planner-maintained thresholds held in WMS/ERP config (often per SKU class or
location) - read the configured values, never run against hardcoded defaults; the numbers above are examples.
For the value cap, use the **ERP valuation cost** (the book value of the loss) as `unit_cost`; SAP standard
price (control S) and Manhattan moving-average (V) can diverge, so a unit-cost mismatch between the two
systems is itself a reconciliation item -> `sap-mm` for the price-control rule.

Breach ANY one band -> **material**. The two caps do different jobs: the percent cap catches a systematic
pick error on a cheap SKU (small dollars, big ratio); the value cap catches a real loss on a high-value or
high-count SKU (small ratio, big dollars). Requiring both plus the ATP test is what keeps a $9K loss from
clearing as a 0.5% rounding fix.

### 3. Trace - variance signature -> likely cause
Read the sign and pattern before you decide. Classify each material variance:

| Signature | Likely cause | Post as |
|---|---|---|
| Negative here + an offsetting positive nearby (net ~0) | unscanned inter-aisle move / mis-put | bin-to-bin transfer (net-zero, no loss) |
| Negative, no offset, high-pick SKU | short-pick / pick not decremented | down-adjustment (a real loss) |
| Positive, recently received or returned SKU | put-away or return not scanned | up-adjustment |
| Gap = one full LPN quantity | whole LPN mis-scanned / in wrong location | locate the LPN, transfer - do not write it off |
| System on-hand negative or zero, count positive | over-pick booked before adjustment | recount to set the true floor, then adjust by value/ATP |
| Same SKU/location repeats across days | systematic (slotting, label, scanner dead zone) | process fix, NOT a record fix |

Two pre-filters before you trust a variance: convert **units of measure** first (an each-vs-case mismatch
shows a false variance that nets to zero once converted), and read **lot/serial** context (a lot-specific gap
may need an expiry or recall hold, not a plain qty adjustment -> `manhattan-wms` for attribute
handling). A transfer in transit can also show a false variance at both ends - reconcile the open move first.

Cross-system truth: WMS on-hand is operational truth for picking; the ERP holds valuation. When they
disagree, reconcile the transaction gap - never adjust one side only to make the two numbers match.

### 4. Size - ATP impact
A variance is **ATP-critical** if correcting on-hand would drop projected-available below committed demand in
the coverage window:
```
days_cover      = system_onhand / avg_daily_demand    (pre-correction, for context)
uncommitted     = max(0, count_qty - allocated)        (uses the corrected on-hand)
atp_at_risk     = max(0, open_demand_in_horizon - uncommitted)
```
The horizon is the SKU's replenishment lead time (or a planner-set window), not a fixed number - a long-lead
SKU has a wider window. `atp_at_risk > 0` (typically a downward variance on a fast SKU with thin cover) ->
ATP-critical. A downward variance on a slow SKU with 200 days of cover is not ATP-critical even at the same
dollar value.

**Hold scope + release (the hold is itself a write).** `atp_at_risk` is the criticality TRIGGER, not the
hold quantity. Until the adjustment posts, system on-hand still shows the inflated figure, so hold the
**phantom quantity = `|variance_qty|`** (the units the system shows but are not there) from the available
pool. That drops available to the true figure (`on-hand - allocated - hold`); already-allocated orders are
untouched, since a hold reduces the free pool, not existing reservations. Hold less and the remaining phantom
stays promisable; hold more than the variance and you strand real stock. An open-ended hold is destructive;
set the release up front: it lifts the moment a recount confirms and the adjustment posts (the corrected
on-hand replaces it), or the planner clears it. Never leave a SKU held with no owner and no exit.

Also size ATP on the SKU's **net on-hand across locations**, not per-bin: a short in bin A offset by a long in
bin B nets first (a genuine offsetting pair is a move, step 3, not two independent gaps).

### 5. Options + your gate (auto-post / recount / escalate)
Each material line gets one disposition. The gate is the planner's post limit plus a cause-confidence and
ATP test:

| Disposition | When | What the planner sees |
|---|---|---|
| **Auto-post** | within post limit AND cause clear/confirmed AND not ATP-critical | logged after the fact (reason + trace) |
| **Recount** | cause only probable (no clean offset), OR percent breach without confirmed cause | tasked to the counter before any post |
| **Escalate + hold** | `variance_value >` post limit, OR ATP-critical, OR systematic pattern | full trace, availability already held, awaits decision |

Noise lines auto-post as in-tolerance corrections within the limit. Even an in-tolerance auto-post is a
destructive write (it overwrites on-hand, no undo, only an opposite adjustment) - the tolerance and limit
justify it, not its small size, so it still gets the idempotency check and a logged trace. Never split one
large adjustment into several small ones to slip under the limit - that is the same write with extra steps, and the expertise skill
flags it as destructive. "Approve" posts as staged; "adjust" changes the quantity or the disposition;
"decline" re-opens the exception and, for a suspected process fault, opens a root-cause ticket.

### 6. Act
**Re-read on-hand here, then check idempotency.** The reads in steps 1 and 4 were for classification; the
freshness re-read of `system_onhand` belongs at this instant, immediately before the write - not earlier. If
it moved materially, re-run the tolerance bands (step 2) before disposing - a concurrent receipt can flip a
noise line into a material one, so re-classify, do not just re-read the number.
**Idempotency:** before any write, check for an existing adjustment referencing the same count ID /
location / LPN. A harness re-run, a network retry, or a duplicate count file must not post the same
adjustment twice - a repeated confirmation double-posts phantom stock or a double loss. Treat a retry as a
destructive risk: confirm the first write did not already land before re-posting.

In order: post in-limit adjustments to WMS (an inventory adjustment overwrites on-hand with no offsetting
document and records a loss/gain -> `manhattan-wms` for the reason-code and no-undo behavior); the
ERP-side variance write posts an inventory + value document (a physical-inventory count difference) ->
`sap-mm` for the movement type, price control (S vs V) and posting-period rules. Task recounts.
Flag the ATP-critical variance in the ERP and hold its availability. Notify the counter and supervisor on
every escalation. Log the why on every auto-post, and feed repeat SKUs/locations (same SKU or location
appearing >= 2 times in 30 days) into the count schedule so the hunt focuses where errors actually live.

**Mirror both sides.** Every WMS adjustment must produce its matching ERP variance posting - they are one
logical transaction: both land or neither stands. Verify the ERP leg landed (query the ERP transaction log by document number or
reconciliation key). If it cannot be confirmed (WMS posted, ERP silent = drifted
truth): hold and escalate to the planner. Do not retry the ERP post unilaterally - it may have landed and a
blind retry double-posts - and do not reverse the WMS write blindly; the planner reconciles the pair. Never
adjust one side only to make the numbers agree.

### 7. Reconcile recount results
A recount closes the loop, it does not just re-open it. Re-run the tolerance rule on the recount:
- Recount confirms the original count -> dispose per step 5 (auto-post if now within limit and cause clear, else escalate); release any hold once posted.
- Recount matches system on-hand -> the first count was the error; close with no adjustment, log it against the counter/location.
- Recount lands a third number -> the location is unstable (a process fault); escalate, do not post, keep any hold in place pending the planner under the default window, and tighten its count cadence.

## Worked example (34 discrepancies, one $9K fast SKU)
Two thresholds are in play: the **tolerance band** (+/- 0.5% / $50 = noise vs material) and the planner's
**post limit** (5% / $500 = auto-post vs escalate). 34 posted: 28 clear all three bands (within +/- 0.5%,
under $50, not ATP-critical) -> auto-post as in-tolerance, logged. 6 are material.

| SKU / bin | on-hand -> count | variance | pct | value | ATP | Trace -> disposition |
|---|---|---|---|---|---|---|
| 9001 (fast, ATP-feed) | 900 -> 600 | -300 | -33% | **$9,000** | critical | short-pick suspected -> **escalate + hold** |
| 4210 | 220 -> 212 | -8 | -3.6% | $96 | no | pick not decremented -> **auto-post** |
| 4211 | 140 -> 146 | +6 | +4.3% | $90 | no | return re-stocked unscanned -> **auto-post** |
| 7788 | 80 -> 74 | -6 | -7.5% | $132 | no | damaged pull not adjusted -> **auto-post** |
| 3305 @12-A | 300 -> 260 | -40 | -13% | $320 | no | move suspected, offset not clean -> **recount** |
| 6120 @15-C | 150 -> 178 | +28 | +19% | $224 | no | other half of a mis-move? unclear -> **recount** |

Walk the $9K line (SKU 9001: `avg_daily_demand = 250/day`, `allocated = 200`, unit cost $30):
`variance_value = 300 * $30 = $9,000` breaches the $500 cap; `days_cover = 900/250 = 3.6`
falls to `600/250 = 2.4`; open demand in the 3-day horizon = 620 units, uncommitted after correction = 600 -
200 allocated = 400, so `atp_at_risk = 620 - 400 = 220` units short of the day's demand -> ATP-critical. Hold
the **phantom 300 units** (`|variance|`) from the available pool - not the 220 shortfall - so on-hand of 900
stops promising 300 units that are not on the shelf; escalate to the planner; do not auto-post a $9K
write-off as a routine fix. Of the 6 material lines: 3 auto-posted, 2 recounted, 1 escalated and held;
with the 28 in-tolerance auto-posts that is 31 posted, 2 recounted, 1 held - 34 accounted for.

## Failure -> recovery playbook
| Risk | Detect before acting | Recover if it happens |
|---|---|---|
| Auto-posting a real loss as a tolerance adjustment | value-cap and ATP tests run on every line, not just percent; a small ratio on a high-value SKU trips the $ floor | reverse with an opposite adjustment (no undo - a new offsetting write in WMS -> `manhattan-wms`), re-open the exception, route to root cause |
| A miscalibrated tolerance hiding a systematic pick error | same SKU/location repeats across days (schedule memory); a percent-band breach with clustered signs even at small dollars | tighten `tol_pct` for that SKU/location, pull the recently-cleared log for it, recount, and audit the process (slotting, label, scanner) instead of clearing again |
| Adjusting the record instead of fixing the process | an offsetting pair (net ~0) is a MOVE not a loss; a one-directional drift over days is a process fault | post the correction as a bin-to-bin transfer, not a write-off; open a process ticket; add the location/SKU to the count schedule so it is counted more often |
| Posting against a stale on-hand | re-read `system_onhand` at execute; count is stale if on-hand moved `> tol_pct` since the count | recount rather than post against a number a concurrent pick/wave already changed |
| WMS and ERP drift (one side posted, the other did not) | verify the ERP variance leg landed for every WMS adjustment | flag the unmirrored pair, route to the planner, and reconcile the transaction gap - do not adjust one side to force a match |
| Escalated hold with no planner action | a held SKU with no resolution timer strands committed orders | set a default window (end-of-shift or 4 hours, planner-configurable); on expiry escalate to next level or release the hold with a documented risk acceptance - an open-ended hold is destructive |
| Phantom-quantity hold cannot be placed (lock, allocation freeze, system error) | the hold is the ATP safety gate - confirm it applied before any write | do not proceed with any write for that line; escalate immediately as "hold failed - ATP exposed" |

## Testing (pressure)
Scenario: clock closing, the $9K fast-SKU variance sits on the list, and the supervisor says "it is only a
0.5% count difference, just auto-post it and clear the board." Without the skill the agent clears it inside a
loose percent band and over-promises 300 units for the day. With the skill it runs all three bands (the $
floor and ATP test both trip), sizes `atp_at_risk = 220`, holds availability, and escalates at the named
planner's limit - it does not auto-post a real loss as a rounding fix. Counter to add if a new rationalization
appears ("the pair nets to zero, just post both legs"): a net-zero pair is a suspected move, so recount to
confirm the physical reality before posting a transfer.
