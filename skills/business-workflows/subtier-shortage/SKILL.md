---
name: subtier-shortage
description: "Trace a supply shortage that starts N tiers up (a tier-3 sub-supplier or raw-material event) down your multi-level BOM to the affected parts, finished SKUs, and customer commits; size the exposure by week and revenue-at-risk; and assemble priced mitigation options (pre-buy or buffer, qualify an alternate sub-source, dual-source, expedite, reallocate) for a human to approve. Advise-only, no autonomous action. Use when a tier-N risk feed (Everstream, Resilinc, Interos) flags a sub-tier fire, force majeure, allocation, or shutdown that no tier-1 has confirmed and it is not yet in the PO book; when someone asks which of our products depend on this node, how much revenue is at risk, or whether to pre-empt now or wait for tier-1 confirmation; or mentions tier-3 shortage, sub-tier pegging, multi-level BOM where-used, n-tier exposure, uc-net-subtier-shortage, revenue-at-risk, penalty commit, or pre-buy vs wait."
---

# Sub-tier shortage: trace it up the BOM before it hits the PO book

Use case `uc-net-subtier-shortage`. A tier-N feed flags an event two or three hops up the supply chain, at a
sub-tier plant or a raw material no buyer's PO touches. It is already inside your BOM, but nothing links it to
your finished products until the shortage surfaces in the PO book weeks later, when the cheap mitigation window
(pre-buy, qualify an alternate) is half gone. This skill runs the three-hop trace no one does by hand, sizes
the exposure, and prices the options, so a human can pre-empt on the unconfirmed signal.

**Egress rule (do not skip):** on an unconfirmed signal, keep every notification internal. No outreach to
tier-1, the sub-tier, or the market until the event confirms or the named approver authorizes it - a leaked
"we are short" is what starts the allocation.

## When this fires
A tier-N feed flags a tier-3 sub-supplier or raw-material event (fire, force majeure, allocation, shutdown)
that no tier-1 has acknowledged. The shortage is three hops up the BOM and invisible in the PO book. The
window between the feed alert and the tier-1 confirmation is the whole opportunity - days, not weeks.

## Autonomy
Recommended dial for the write: **gated (L2)**. The agent traces the shortage up the BOM and builds the priced mitigation options unattended, but takes no action - a human decides. Every committing write (the risk-register exposure entry and the plan exposure flags on affected parts) holds for human approval each time. Any outbound (the notifications to planning, category, and affected buyers, and, on escalation, the incident bridge - n-tier supplier shortage data is sensitive, carrying supplier identity and sub-tier exposure, and an unconfirmed tier-N signal must not leak to tier-1 or the market before it confirms or the approver authorizes it, or premature outreach triggers the allocation you were trying to get ahead of) gates by the outbound floor at every level below yolo. Suggested approver: supply-risk lead / commodity manager (e.g. D. Kaur) - advisory only; v1 does not enforce approver identity, so approval is a real human click through the prompt, not a name check. The customer's `.scm/autonomy.yaml` dial is what the harness actually enforces; this is only the recommended default.

## Systems
| Read | Purpose | Vendor HOW |
|---|---|---|
| Risk & tier-N feed | the event; resolve the flagged node to entities you buy from (directly or via sub-tier) | `everstream` / `resilinc` / `interos` (tier-N risk map) |
| PLM / BOM (multi-level) | where-used explosion: which parts and SKUs contain the node | PLM BOM |
| SAP / ERP | on-hand, in-transit, firmed inbound, valuation for each affected part | `sap-mm` (BOM / coverage) |
| Planning | time-phased demand and supply, weeks of cover | `kinaxis` |
| Supplier portal / EDI, commodity feed | corroborate the signal; approved-vendor-list (AVL) source of the part | portal / market feed |

| Write (all gated, advise-only) | Class | On approval |
|---|---|---|
| Risk register: exposure entry | write, consequential (treat as effectively irreversible) - the entry itself can be edited, but its numbers propagate to planning and can trigger real cash commitments downstream, so a wrong size is not cleanly undone | opened after the approver signs off |
| Plan: exposure flags on affected parts | write, reversible (flag can be cleared) | written to planning, then handed to `kinaxis` for the reschedule |
| Notification: planning + category + affected buyers | write, irreversible egress (cannot un-send) | internal only until confirmed (egress high) |
| Incident bridge (on escalation) | write, irreversible egress | opened only if the approver escalates |
| Recommended pre-buy / qualify-alt | not written here - it is a downstream procurement commit; once the human executes it, the cash is committed and not cleanly reversible | staged as a recommendation only; procurement executes it |

This skill (advise mode) writes nothing on its own. The reads above are all safe. The riskiest thing it
produces is the pre-buy recommendation: once a human acts on it, the cash is committed, so the sizing that
justifies it must be re-read fresh at the gate.

## Flow: detect, assemble, options, gate, act
1. **Detect** - match the tier-N alert against your BOM the hour it posts. Read the event, then resolve the
   named node (a plant, a company, a commodity) to entities you can peg. Freshness rule: re-read on-hand,
   in-transit, and firmed supply at execute (stock drifts daily) and re-check the event status
   (escalated or downgraded) before any write. Tie staleness to the clock: coverage must be under 24 hours
   old when `T_window` <= 2 weeks, under 72 hours otherwise - a tight window cannot ride on stale on-hand.
2. **Assemble** - run the trace + sizing method below: peg the node up the multi-level BOM to the finished
   SKUs, then size the exposure by week and by revenue-at-risk. This is the stage no one runs by hand.
3. **Options** - construct and price each mitigation (pre-buy, qualify alt, dual-source, expedite,
   reallocate, absorb). Rank by expected value with a downside-protection tie-breaker.
4. **Gate** - present to the named risk lead the sized exposure, the ranked options, and precedent (prior
   sub-tier calls scored against your own history). Approve / adjust / decline. Nothing writes before this.
5. **Act (on approval only)** - stage the risk-register entry and plan exposure flags, notify planning and
   affected buyers internally, and hand the downstream reschedule to `kinaxis` (`uc-resched-subtier`).
   Record why. Advise mode never fires these on its own.

## The trace + sizing method
The record gives the skeleton; this is the computation. State moves in one direction:
`detected -> pegged -> sized -> options-priced -> gated -> approved (acting) | watching`. Report which state
you are in so the work can be resumed after an interruption; never jump to `sized` on an unresolved peg.

**1. Resolve the node.** The feed names a sub-tier node. Resolve it to a purchased material or commodity and
the supplier(s) that feed it. The tier-N risk system owns this n-tier map; your PLM/AVL is authoritative for
which parts you actually buy from that node. One event can hit several materials at once (one plant fire ->
three resin grades): fan out per affected material, run the trace for each, then aggregate at the end-item
level so a SKU that depends on two of them is counted once. Classify each peg:
- **Confirmed** - node resolves to a real entity in your AVL and the BOM path is complete.
- **Inferred** - partial sub-tier links; you know the commodity but not the exact supplier hop.
- **Speculative** - the node does not resolve to anything you buy; downgrade, do not size.

**2. Peg up the BOM (where-used).** From the sub-tier material, run a multi-level where-used explosion:
raw material -> component -> sub-assembly -> finished SKU. Collect every end item on a path with no ready
BOM-approved substitute. Aggregate at the end-item level so a shared node feeding two components is not
double-counted (a shared-node / concentration case Interos surfaces).

**3. Size coverage by week.** For each affected part compute time-phased cover:
`available[week] = on-hand + in-transit + firmed inbound within lead time`. The `exposure_week` is the first
week where cumulative demand > cumulative available. `weeks_of_cover = available / weekly_demand`. Read
on-hand/in-transit from `sap-mm`, time-phased demand/supply from `kinaxis`.

**4. Size revenue-at-risk.** For each finished SKU, `units_short[week] = demand - available`, and
`revenue_at_risk = sum over exposed weeks (units_short * ASP)`. Flag any penalty-bearing commit separately:
`penalty_exposure = penalty_rate * commit_value`. Report a point number only on a **confirmed** peg; on an
**inferred** peg report a range and label the gap - never report "no exposure" when the trace has gaps.

**Signal confidence.** `P_real = source_reliability x corroboration`, where `source_reliability` is the feed's
own confidence on the event (0-1; the tier-N system supplies it) and `corroboration = min(1, 0.5 +
0.25 x independent_confirming_sources)` (a market/commodity feed, a portal note, a second risk system each
count as one). Size and recommend a pre-buy only when the peg is confirmed, or inferred with `P_real` above
your watch threshold (a sensible default is 0.5). A speculative node, or `P_real` below threshold, stays
watch-only - no sizing, no recommendation. **Lone-feed guard:** when `independent_confirming_sources = 0`,
corroboration is only 0.5, so a single uncorroborated feed cannot clear the threshold on `source_reliability`
alone - do not recommend a pre-buy on it without the named approver's explicit sign-off.

**Edge cases the data does not list**, each breaks naive "one part, one price, one plant" sizing:
- **Multi-site BOM** - the same part is built at two plants with different on-hand; size coverage per plant, do not pool.
- **Contract-tier ASP** - revenue-at-risk uses the committed price per customer tier, not a blended list price, when a commit is tier-priced.
- **Partial substitute** - a BOM-approved alternate covers some SKUs but not others; exclude the covered paths from exposure, size only the uncovered ones.
- **Dual-sourced component** - if the affected part already has a qualified alternate in the AVL, size only the single-sourced share of demand.

## Mitigation options (priced)
Each option carries a number and a feasibility test, not a label.

| Option | Construction | Cost | Exposure closed | Feasible when |
|---|---|---|---|---|
| **A Pre-buy buffer + qualify alt** | buy a material buffer from a second source now (fast) and start qualifying a new alternate sub-source (slow) | buffer + expedite + qualification | the full exposed window incl. penalty commit | buffer pre-buy lead time < weeks to `exposure_week` |
| **B Wait + expedite on confirm** | hold, watch tier-1, expedite only if the event confirms | expedite premium (only if confirmed) | the tail after confirmation | tier-1 confirmation expected before the window closes |
| **C Reallocate** | steer existing supply to the penalty-bearing commit first | no cash out, opportunity cost of the de-prioritized SKUs | only the prioritized commit; adds no supply | total supply >= prioritized demand |
| **D Absorb** | do nothing | expected loss = `P_real * revenue_at_risk` | nothing | exposure is small vs mitigation cost |

Pre-buy delivery (existing buffer material from a second source) and qualifying a brand-new alternate
sub-source are two different clocks: the first can arrive in days, the second takes weeks of PPAP / first-article
approval. Option A leans on the fast buffer to cover the near weeks and the slow qualification to cover the tail.

**Ranking.** Score each by `EV = P_real * exposure_avoided - mitigation_cost`, rank high to low. Tie-breaker
on a penalty-bearing commit is downside protection (minimize worst case), not EV - a low-probability $4M
penalty still dominates when the mitigation is cheap relative to it. Recommend one default plus one escape
hatch, not a menu. **Portfolio rule:** when several tier-N signals fire in the same window, rank pre-buys
across events by EV per dollar of buffer and cap aggregate pre-buy at the portfolio cash limit - do not buffer
every weak signal. Option C (reallocate) can also steer across customers or regions, not only SKUs, when their
penalty tiers differ; prioritize the highest-penalty commit first.

## Pre-empt now vs wait (the threshold)
The core decision the record names. Two clocks:
- `T_window` = weeks until you must commit the cheap mitigation to beat the exposure = `exposure_week - alt_lead_time`.
- `T_confirm` = expected weeks to tier-1 confirmation.

If `T_window < T_confirm` you cannot wait - the cheap window closes before confirmation, so the call must be
made on the unconfirmed signal. **Pre-empt when** `P_real * (revenue_at_risk + penalty_exposure) > mitigation_cost`
**and** the alternate's qualification/pre-buy lead time is shorter than weeks to `exposure_week`. Otherwise
hold and watch (option B). Use strict inequalities: `P_real` must be strictly greater than the watch threshold
(default > 0.5), and the pre-empt test must clear, not tie.

**When the gate is closing and the approver is unreachable:** time-box the gate to the hours left in
`T_window`, route to the named backup approver, and page the risk chain / incident bridge. If no one responds
before the window closes, hold - advise mode never authorizes an unapproved pre-buy - and log the missed
window as the outcome. A missed cheap window is recoverable (expedite later at higher cost); an unauthorized
cash commit is not.

## Worked example (real numbers)
A tier-3 specialty-resin plant halts on force majeure. Everstream flags it at hour 0; no tier-1 PO shows it.
- **Peg**: resin grade R-9 -> tier-2 compound C-4 -> connector part P-2207 -> where-used -> 3 finished SKUs
  (SKU-A, SKU-B, SKU-C), one connector per finished unit. Peg is **confirmed** (P-2207 in AVL, path complete).
- **Coverage** (P-2207, read at execute): on-hand 4,000 + in-transit 2,000 + firmed inbound 3,000 = 9,000
  available. Weekly demand = SKU-A 1,200 + SKU-B 800 + SKU-C 500 = 2,500/wk. Weeks of cover = 9,000 / 2,500 =
  3.6, so supply runs dry in week 4. Plant down + rebuild = 5 weeks -> exposed weeks 4-8.
- **Revenue-at-risk**: units short weeks 4-8 = 5 x 2,500 = 12,500 finished units. SKU-A 6,000 x $900 = $5.4M;
  SKU-B 4,000 x $500 = $2.0M; SKU-C 2,500 x $400 = $1.0M -> **$8.4M** revenue-at-risk. SKU-A carries a $4M
  quarter commit with an 8% penalty = **$320K** penalty if missed.
- **Confidence**: Everstream `source_reliability` = 0.8, one corroborating commodity/market feed -> corroboration
  = 0.5 + 0.25 x 1 = 0.75 -> `P_real` = 0.8 x 0.75 = **0.60**, above the 0.5 watch threshold, so size and price it.
- **Clocks**: alt-compounder pre-buy deliverable in 2 weeks, `exposure_week` = 4, so `T_window` = 4 - 2 = 2.
  `T_confirm` ~ 3 weeks. `T_window (2) < T_confirm (3)` -> cannot wait; decide on the signal.
- **Options**: A pre-buy buffer + qualify alt ~$280K ($180K resin + $40K expedite + $60K qualification),
  closes ~$8.4M incl the penalty commit, feasible (2 < 4). B wait + expedite ~$150K but qual 5 wk leaves weeks
  4-7 exposed (~$6.7M). C reallocate to SKU-A: protects the $4M/$320K, concedes ~$3.0M of SKU-B/C, no cash.
  D absorb: expected loss = 0.6 x $8.4M ~ $5.0M.
- **Pre-empt test**: `0.6 x ($8.4M + $0.32M) = $5.2M > $0.28M` -> pre-empt. **Recommend A** (mitigation is 3%
  of exposure and the 2-week pre-buy beats the 4-week window). Hold at the risk lead's gate; precedent: a
  prior substrate-halt case in the risk register where pre-empting on the signal saved the quarter.

(Timeline note: the 2-week clock is buffer delivery from a second compounder; the 5-week clock in option B is
full qualification of a new alternate sub-source. Different actions, different clocks.)

## Failure -> recovery
| Failure | Detect before acting | Recover |
|---|---|---|
| Acting hard on a tier-N signal that is noise | score the signal (source reliability, corroboration, does the node resolve to something you buy?); require a confirmed/inferred peg before sizing | advise mode means nothing auto-fired; downgrade to watch-only, reverse the pre-buy recommendation before the human commits, keep the scored miss in memory for the next alert |
| Feed is factually wrong (not noise, but a false or duplicate event - plant never shut, mis-tagged event ID) | cross-reference a second feed or direct supplier attestation (via `resilinc`) before sizing; a confirmed peg on a false event is still wrong | downgrade to watch-only, log the feed miss to recalibrate that source's reliability, and do not let a clean BOM peg substitute for confirming the event itself |
| BOM sub-tier links incomplete, real exposure missed | measure where-used coverage; flag gaps where sub-tier links are partial | widen the peg to the commodity / AVL class, size a range not a point, escalate to fill the link (supplier attestation via `resilinc`); report "unknown, links incomplete", never "no exposure" |
| Over-buffering every weak signal, tying up cash | portfolio view of open pre-buy recommendations vs cash; require `EV(mitigation) > cost` and confidence above threshold | net the buffer against existing on-hand and in-transit first, cap aggregate pre-buy, release buffers when signals clear |
| Stale coverage read | on-hand read age vs execute time | re-read on-hand / in-transit / firmed supply at execute (it drifts daily) via `sap-mm` before sizing |
| Premature egress leak to tier-1 or market | egress classification of any outbound on an unconfirmed signal | hold all outbound to internal only until the event confirms or the approver authorizes (egress high) |
| Shared node double-counted | same node pegs multiple components on multiple paths | aggregate exposure at the end-item level, not per path |
| Alternate fails qualification mid-pre-buy | track the qualification milestone (first-article / PPAP) against the exposure clock | keep the fast buffer running to cover the near weeks, re-price the tail exposure without the alt, escalate to a third source |
| Event downgraded after a pre-buy is committed | re-check event status before and at the gate; the pre-buy commits cash and is not cleanly reversible | you cannot un-commit the cash; net the surplus buffer against future demand and record the scored miss - do not stack more buffer on the same weakening signal |
| Demand or commit shifts between sizing and gate | re-read time-phased demand from `kinaxis` at the gate | re-size revenue-at-risk on the fresh demand before the approver decides; a stale size can over- or under-buy |
| Multi-site coverage pooled by mistake | check whether the part builds at more than one plant | size cover per plant, not pooled; one plant can be short while another is long |

## Cross-system truth + freshness
The workflow owns the cross-system trace; each vendor HOW is deferred by name. Authoritative sources: the
tier-N risk system (`everstream` / `resilinc` / `interos`) for the event and the
sub-tier map, but NOT for your BOM or coverage; PLM/AVL for which parts you buy from the node and the
where-used explosion; `sap-mm` for on-hand, in-transit, and valuation; `kinaxis` for
time-phased demand/supply and the downstream reschedule. When the feed's supplier-to-part mapping disagrees
with your AVL, your AVL wins for what you actually buy. Re-read coverage and event status at execute.
