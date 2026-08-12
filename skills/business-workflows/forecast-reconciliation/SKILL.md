---
name: forecast-reconciliation
description: "Reconciles a customer's committed/planned forecast (EDI 830 or supplier portal) against the internal statistical forecast and the consensus plan, quantifies the step-up, decomposes it into bias, corroborated new-demand, and one-off noise, weights the signal, and recommends accept / dampen / hold before any supply is committed. Use when a key customer's 830 or portal forecast jumps and POS sell-through or the sales account view stays flat, or the user mentions customer forecast reconciliation, EDI 830 / 862 release, a planning-schedule step-up, consensus demand vs customer signal, forecast bias weighting, phantom demand, chasing a customer step-up, signal vs noise, or expedite risk from a forecast spike."
---

# Customer forecast reconciliation: signal vs noise

Use case `uc-plan-fcst-recon`. A key customer's forecast (EDI 830 / portal) steps up sharply on a platform
part while POS sell-through and the sales account view stay flat. A real program win and quarter-end forecast
noise look identical at first. Decide, before committing supply, how much of the step-up to believe and flow
into the consensus plan. Chase it blind and you expedite into phantom demand (about $300K per chased spike,
air freight 30-50% over baseline); dismiss it and you miss a real ramp. A large share of expedite events
trace back to forecast error, so the reconciliation is the whole game.

## Autonomy
Recommended dial for the write: **gated (L2)**. Builds the weighted consensus number and the evidence pack;
the human decides. Every committing write (promoting a scenario/version to the baseline plan of record, or
logging the CRM program signal) holds for human approval each time. Any outbound (notifying sales/account
team; reaching out to the *customer* to confirm is a higher-sensitivity external send) gates by the outbound
floor at every level below yolo. Suggested approver: demand planner (e.g. R. Okoro) - advisory only;
v1 does not enforce approver identity, so approval is a real human click through the prompt, not a name check.
The customer's `.scm/autonomy.yaml` dial is what the harness actually enforces; this is only the recommended
default.

## Trigger
A customer's latest 830/portal forecast steps up (e.g. +40%) on a platform part while POS sell-through and the
CRM account view stay flat. Fires weekly on release load. Watch for the quarter-end pattern: customer plans
that historically run hot near quarter close.

## Systems
| System | Read / write | Vendor HOW (defer by name) |
|---|---|---|
| Customer forecast (EDI 830 / 862 / portal) | read | translate + zone-split (below) |
| Statistical forecast + consensus plan | read; the write is **committing / destructive-class** (promoting to baseline overwrites the plan of record, no clean undo) | `kinaxis` / `o9` / `sap-ibp` |
| CRM sales input, program/opportunity signal | read | `salesforce` |
| POS / sell-through | read | OMS sell-through feed |
| Notifications: sales + account team | write | notify once, post-approval |
| Record: reconciliation rationale | write | logged with the evidence pack |

The workflow owns the CROSS-SYSTEM reconciliation. Each vendor-specific write (commit a scenario, promote a
version, log a CRM program) is deferred by name to the `expertise-*` skill - see Act and Expertise links.

## Flow: detect -> assemble -> options -> gate -> act

### 1. Detect
- Read the new 830/portal release, the current stat forecast, the consensus plan, trailing POS sell-through,
  and the CRM account/opportunity view - all the day the release lands.
- **Freshness (re-read at execute):** the 830 changes weekly and another planner may move the baseline. Re-pull
  the latest release, its firm-zone quantity, and the current plan number right before any write. A newer
  release can supersede the spike entirely.
- **No release / late release:** if the expected 830 does not land this cycle, that absence is itself a signal
  (a silent pull-back or a broken feed). Flag it, do not assume the prior 830 still holds, and verify the feed
  before reconciling.

### 2. Assemble (the reconciliation method)
Put every signal on the same grain: item x ship-to x period bucket, then run these steps.

**a. Normalize the 830.** Two traps before any math:
- **Cumulative vs discrete:** many 830s send CUM (cumulative required) quantities, not per-bucket discrete.
  Convert: `discrete_bucket = CUM_this - CUM_prior - received_to_date`. Reading CUM as discrete inflates the step.
- **Zone split:** separate the 830 into its **firm/committed zone** (near buckets, carry liability, mirrored
  by the 862/JIT) and its **planning/forecast zone** (far buckets, no liability). Zone drives how much you trust it.

**b. Quantify the gap** per bucket:
- `step_vs_plan = customer_830 - plan`
- `step_vs_stat = customer_830 - stat_forecast`
- express each as a percent of plan.

**c. Decompose the step into three drivers** (this is the core - a raw gap is not actionable):

| Driver | Formula / test | Reading |
|---|---|---|
| **Bias (expected phantom)** | `customer_830 x (1 - r_zone)`, where `r_zone = mean(actual_shipped / customer_forecast)` at this grain/season | the slice expected to evaporate; `r < 1` = customer runs hot |
| **Corroborated new-demand** | the slice backed by an independent signal (firm-zone rise, POS uptick, logged CRM program) | real ramp; if no signal, this is 0 |
| **One-off / residual** | `step - bias_phantom - corroborated_new_demand` | high residual + zero corroboration = noise |

**Zone-weight the bias.** Compute `r` separately per zone: `r_firm` (firm/committed buckets) and `r_planning`
(planning/forecast buckets). Firm commitments run near `r_firm ~ 1.0` (the customer is on the hook); planning
forecasts run hot (`r_planning` well below 1). Apply the zone-matching `r` to each slice - a planning-zone
step-up is discounted by `r_planning`. A blended `r` would under-dampen a planning spike and over-dampen a firm
commitment, the opposite of the intent.
- **Cold start (no history):** for a new customer/part grain, start from `r_firm = 1.0`, `r_planning = 0.7`
  as a conservative prior and flag low confidence to the planner; graduate to a computed `r` once >= 6
  consecutive releases at this grain exist. Do not skip the bias step and treat the raw 830 as unbiased.
- **Under-forecasting customer (`r > 1`):** cap the bias-strip at `min(r, 1.0)` so `customer_adj` never
  exceeds the 830 - do not manufacture demand the customer did not ask for. A firm zone that consistently ships
  above forecast (`r_firm > 1`) is itself upside corroboration; raise the credibility floor, do not dampen.
- **Step-up bias differs from base bias:** if enough history exists, compute `r` on prior step-ups specifically;
  otherwise `r_zone` (overall accuracy) is a conservative proxy for spike behavior.

**d. Score corroboration (0-100)** - is this step-up real?

| Evidence | Points |
|---|---|
| Firm-zone / 862 commitment rose (customer on the hook) | +40 |
| POS sell-through trend up over trailing 8 weeks (>= 5% vs prior baseline, >= 3 of 8 weeks above), aligned to this part | +25 |
| CRM program/opportunity logged, matching part + timing | +25 |
| Account team confirms a known change | +10 |
| Step-up persists across >= 2 consecutive releases | +10 |
| **Firm zone SHRINKING while the planning zone steps up** (classic phantom pattern) | **-20** |
| Single-release spike, no prior corroboration (stale by 4+ weeks discounts further) | -10 |

Score negative evidence too - a shrinking firm commitment alongside a planning-zone jump is the textbook
phantom, and a one-release spike is the weakest signal. Clamp the total to `[0, 100]` before mapping to `w`
(a net-negative score maps to `w = 0`, i.e. hold at plan). New-platform exception: if the part has no POS history
yet, POS's +25 is redistributed (+15 to firm-zone, +10 to CRM) so a missing-by-design signal does not force a
false reject (see Edge cases).

**e. Weight and produce the consensus number.**
- `w` (credibility of the customer signal) maps from the score:

| Score | w | Recommended call |
|---|---|---|
| >= 70 | 0.8-1.0 | Accept |
| 40-69 | 0.4-0.7 | Dampen (with band) |
| 15-39 | 0.2-0.35 | Light dampen / hold |
| < 15 | <= 0.15 | Hold at plan, confirm with customer |

- Strip the known bias, then weight the residual gap:
  `customer_adj = customer_830 x r_zone` ; `consensus = plan + w x (customer_adj - plan)`.
- **Per-zone blend (step spans both zones):** split the step by zone. Flow the firm-zone slice at its
  `r_firm` (it is a commitment, `w ~ 1`); apply the score-derived `w` only to the planning-zone slice dampened
  by `r_planning`. Never dampen a firm commitment with a planning-zone `w`. The single-formula shorthand above
  assumes the step sits in one zone.
- Confidence band `= +/- (bias_volatility x step)`, where `bias_volatility = stdev(r)` over the history
  window; widen it when the residual is large.

### 3. Options (each priced)
Construct all three and attach the supply cost, then recommend by score. Incremental units above plan that
standard lead time cannot cover go to expedite (air premium 30-50%).

| Option | What flows | Priced impact | When it wins |
|---|---|---|---|
| **A - Accept full step** | customer_830 to plan | full expedite + working capital if unsold | score >= 70: firm zone up, POS or CRM corroborates |
| **B - Dampen** | consensus with band | partial expedite, hedged | score 40-69: mixed signal, known bias |
| **C - Hold + confirm** | plan unchanged | $0 now; risk = late ramp. Hold max 2 release cycles, then escalate; the confirm loop mitigates | score < 15: no corroboration, planning-zone only, quarter-end |

### 4. Your gate (demand planner)
Show the planner: the decomposition (bias / corroborated / residual), the corroboration score, the zone,
the two flat corroborators, and **precedent** (this customer's prior step-ups and whether they materialized).
Approve = write the recommended option; Adjust = override w and re-price; Decline = hold, re-run next cycle.

### 5. Act (only after approval)
- Do the reconciliation in a **scenario / what-if version** first (safe, reversible), commit only the approved
  number. The commit/publish is the high-consequence step: `kinaxis` (commit a scenario, publish to
  baseline), `o9` (commit a version into the mainline), or `sap-ibp` (Save Data / promote a
  version to baseline). **HARD GATE:** the only permitted write to the plan of record is the gated,
  planner-approved commit - reconcile in a scenario/what-if and never write the baseline directly, because a
  direct write skips the approval and cannot be cleanly undone.
- **Revert path:** promoting to baseline overwrites the plan of record - it is not silently undone. If a later
  release drops the demand you committed, restore the prior number as its own gated write: build a corrected
  scenario/version at the prior baseline and re-commit. Snapshot the pre-commit baseline value before every
  promote - that snapshot is the revert target. The vendor mechanics (re-publish, restore from snapshot /
  prior version) live in the expertise skill named above.
- Log/read the CRM program signal and any customer-facing note via `salesforce` (mind PII egress).
- Notify sales + account team once. Record the rationale + evidence pack. Store the accept/dampen/reject call
  and, next cycle, its outcome - the bias weight `r` sharpens per customer over time.

## Which signal wins (cross-system truth)
| Signal | Authoritative for | Trust rule |
|---|---|---|
| 830 firm/committed zone, 862/JIT | near-term commitment (carries liability) | high; accept most of a firm-zone rise even without POS |
| 830 planning/forecast zone | far-horizon intent, not a commitment | weight by bias + corroboration, never at face value |
| POS / sell-through (OMS) | actual end-demand direction | high, unless the part is new (no history); flat POS disconfirms a step-up on an established part |
| CRM program/opportunity (Salesforce) | whether a real program change exists | presence corroborates; absence is evidence, not proof - confirm with account team before rejecting |
| Stat forecast + current plan | the internal unbiased baseline | holds until an independent signal moves; the fallback number |

## Worked example (real numbers)
Customer A, platform part P-2245, ship-to Plant 2. Plan 20,000/mo; stat forecast 20,500/mo. New 830 steps to
**28,000/mo** (+40% vs plan) - but the step sits entirely in the planning zone (weeks 9-16); the firm zone
(weeks 1-4) is unchanged at ~20,000. POS trailing-8wk flat at ~19,500-equiv. No CRM program logged; account
team unaware. Release landed 3 weeks before quarter-end. History: `r = 0.86` (over-forecasts ~15% at quarter-end, 6 quarters).

- Gap: `step_vs_plan = 28,000 - 20,000 = +8,000 (+40%)`; `step_vs_stat = +7,500 (+37%)`.
- Bias phantom: `28,000 x (1 - 0.86) = 3,920` units expected to evaporate.
- Corroborated new-demand: firm 0, POS 0, CRM 0, team 0 -> **0**.
- Residual: `8,000 - 3,920 - 0 = 4,080` units above plan, uncorroborated.
- Corroboration score = **0** -> `w = 0.12`.
- `customer_adj = 28,000 x 0.86 = 24,080`; `consensus = 20,000 + 0.12 x (24,080 - 20,000) = ~20,490`.
- Priced options: **A** accept 28k -> +8,000 -> ~$300K expedite (~$37.5/incremental unit at ~40% air premium).
  **B** dampen to 23k -> +3,000 -> ~$113K, banded (this uses `w~0.7`, a deliberate planner override of the
  skill's output - at score 0 the skill itself yields `w=0.12` / Hold, not 0.7). **C** hold 20k + confirm -> $0 now.
- **Recommendation: C** (score 0, planning-zone only, quarter-end, high bias). Gate evidence: last Q4 the same
  customer's planning-zone step-up evaporated - held then, was right. Planner approves C; nothing supplied yet;
  a customer confirmation is requested (gated egress). If the firm zone rises next release, escalate.

## Failure -> recovery playbook
| Failure | Detect before acting | Recover |
|---|---|---|
| Dampen a genuine program win, miss the ramp | firm zone rising over consecutive releases, or POS/CRM turning up after you held | the confirm-with-customer step is the safety net; re-run within the cycle, escalate to expedite once corroboration appears; log the miss to raise this customer's weight |
| Over-trust stale POS on a new platform | part flagged new / no POS history / launch window | drop POS from the score for that part, lean on firm-zone + CRM + account team; do not let flat POS force a reject |
| Sales friction, dampening not evidenced | recommendation to dampen/hold with no logged rationale | attach the evidence pack (bias, zone, flat corroborators, precedent); the gate is the planner, not sales; the customer confirm resolves it objectively |
| Misread cumulative 830 as discrete | quantity qualifier says CUM; step implausibly large vs annual volume | convert CUM -> discrete before computing the gap; re-run |
| Pull-in mistaken for an increase | out-month buckets drop as near-months rise | net across the horizon; treat as timing, re-phase not re-size |
| Write before the gate / auto-accept under pressure | the write is gated (held for approval), not auto-committed | the harness holds the write until the named planner approves; nothing lands unapproved |

## Edge cases the data doesn't list
- **New platform / new part:** POS is absent by design - not disconfirming. Reweight to firm-zone + CRM + account team.
- **Step-up in the FIRM zone:** it carries liability; treat as near-real and accept most of it even without POS.
- **Multiple ship-tos:** a plant-level jump may be a re-allocation across sites, not net-new demand. Net across ship-tos first.
- **UOM / bucket mismatch:** weekly-vs-monthly, 4-4-5-vs-calendar, or pieces-vs-cases inflates the step. Align grain before math.
- **Part-number supersession:** a renumbered part reads as a step-up on the successor and a drop on the predecessor. Map the supersession before comparing.
- **De-commit (830 drops below plan):** the method runs symmetrically - `step_vs_plan` is negative and the
  residual is demand being pulled. The risk inverts to cancellation penalties, inventory build, and
  raw-material exposure; a drop in the FIRM zone may carry a liability/penalty. Decompose, score, and gate the
  same way; the cancellation/de-commit mechanics defer to the plan's expertise skill (`kinaxis` / `o9` / `sap-ibp`).
- **Concurrent step-ups on shared capacity:** each customer's reconciliation is independent, but supply is
  coupled. If two customers spike on the same constrained part, net their approved demand against capacity
  before pricing expedite - the per-option cost above assumes no competing claim on the same line.

## Expertise links
- `kinaxis` / `o9` / `sap-ibp` - the plan: do the reconciliation in a scenario/what-if,
  and the commit/publish/promote to baseline is the gated write. Pick the one matching the connected suite.
- `salesforce` - the CRM/customer signal: read the program/opportunity, and PII egress when anything leaves the CRM.

## Testing
Pressure scenario (run WITHOUT the skill first, capture the wrong move): quarter closes Friday, Customer A is
the top account, the 830 jumps 40%, and sales is pushing "just flow it into the plan, we cannot miss this."
Without the skill the agent accepts the step-up and commits supply. With it, the agent zone-splits the 830,
scores corroboration (0 here), prices A/B/C, recommends Hold + confirm, and stops at the planner gate - it does
not write to the baseline or contact the customer unapproved. Counter for "the variance is tiny, auto-approve":
size the residual and the expedite dollars first; a small percent on a platform part is real money and real capital.
