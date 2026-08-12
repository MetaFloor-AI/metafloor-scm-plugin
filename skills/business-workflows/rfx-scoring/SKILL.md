---
name: rfx-scoring
description: "Supplier selection and RFx scoring - normalize bids to a like-for-like total-cost-of-ownership basis (landed price + freight/duty + payment-terms cost-of-cash + cost of poor quality + priceable risk), score a weighted scorecard (price, quality, delivery, risk, sustainability) on locked weights, rank, and stage a defensible, audit-ready award recommendation (single or split). Use when an RFx / RFP / RFQ / reverse auction closes and bids must be leveled and awarded before the incumbent lapses, when quotes arrive in mixed incoterms / currencies / terms that resist apples-to-apples comparison, when the cheapest quote hides weak quality or thin financials, or someone asks who to award or whether to split to keep a second source; also bid leveling, weighted scorecard, TCO normalization, should-cost, save on price, low bid, single vs dual source. Covers uc-source-rfx-scoring across sourcing suites (SAP Ariba, Jaggaer, Ivalua, GEP, Coupa), ERP spend (SAP MM), and risk feeds (Everstream, Resilinc)."
---

# RFx scoring - a defensible award, not a gut-feel low-bid

Use case `uc-source-rfx-scoring`. An RFx closes with a stack of bids across price, lead time, quality, and
financial health, and the award is due before the incumbent contract lapses. Done by hand under the clock,
the buyer normalizes in a spreadsheet and defaults to the low bid - and six months later that low bid is a
quality escape or a solvency surprise, with no record of why the winner won. This skill's job is to level
every bid to one total-cost basis, score it on locked weights, rank it, and hand the category manager a
recommendation that survives a bidder dispute.

## Read this first
The money leak is **awarding on the raw quoted price**. A quote is not a cost: an EXW offshore quote 8% under
the field can carry more freight, more defects, and more solvency risk than a domestic DDP quote, and once
those are priced the low bid often ranks last. The commit boundary is **notifying the bidders**: award and
regret letters cannot be un-sent, and retracting a published award damages the relationship and can trigger a
dispute. Everything up to that is a reversible internal draft. Hold the notify at the gate.

## Autonomy
Recommended dial for the write: **gated (L2)**. Builds the leveled scorecard and the priced award options;
a human decides, and it never auto-awards. Every committing write (publishing the award, updating the
contract/PO) holds for human approval each time. Any outbound (the award/regret notifications to bidders -
bids, supplier financials, and quality history are sensitive, and the letters go OUT to third parties) gates
by the outbound floor at every level below yolo. Suggested approver: category manager (e.g. R. Haas) -
advisory only; v1 does not enforce approver identity, so approval is a real human click through the prompt,
not a name check. The customer's `.scm/autonomy.yaml` dial is what the harness actually enforces; this is only
the recommended default.

## Systems
| Role | System | Authoritative for | Expertise skill |
|---|---|---|---|
| read | Supplier portal / EDI - RFx responses | the bids, incoterm, currency, terms, quoted volume tier | `sap-ariba`, `jaggaer`, `ivalua`, `gep`, `coupa` |
| read | ERP - spend + price history | the incumbent baseline, prior paid price, category volume | `sap-mm` |
| read | Contracts / CLM | the incumbent terms and the lapse date driving the deadline | `sap-ariba`, `jaggaer`, `ivalua`, `gep` (contract module) |
| read | Quality / LIMS | supplier PPM / defect history, PPAP status, certifications | `sap-qm` |
| read | Risk + tier-N feeds | financial health, single/limited-source exposure, disruption | `everstream`, `resilinc` |
| write | Plan - award recommendation (staged) | the recommended shape, held as a draft/scenario | `sap-ariba`, `jaggaer`, `ivalua`, `gep` (award scenario) |
| write | Savings log | the projected savings vs baseline + the scoring rationale | `sap-mm` (spend baseline) |
| write (commit) | Notification - sourcing team + bidders | award/regret comms - the IRREVERSIBLE commit boundary, hard-gated (see Action classes) | - |

### Action classes (what the harness gates)
- **Read** - bids, spend/price history, contract terms, quality history, risk feeds. Always pass. Re-read the
  drifting ones (supplier financial health, tier-N risk, live capacity, FX) at execute, not the RFx-close snapshot.
- **Write, reversible (internal)** - stage the award recommendation / award scenario in the sourcing tool as a
  draft or pending record. No commitment yet; can be edited or retracted before publish. Low blast.
- **Write, committing** - publish the award and update the contract/PO; this creates the commercial commitment.
  Holds at the gate. Because notifying the bidders also cannot be un-sent, that step triggers the hardest gate
  (see Destructive below), not a routine write. Publish mechanics deferred to the sourcing-suite expertise skill.
- **Destructive / irreversible-in-practice** - the bidder notifications (award + regret letters) cannot be
  un-sent; sole-sourcing a category (dropping the second source) can be effectively irreversible once the
  losing supplier reallocates capacity or de-tools. Hard gate + named approver + a re-read of the risk feed.

## Flow (detect -> assemble -> options -> gate -> act)
1. **Detect.** The RFx closes - pull all responses the moment it does, plus the incumbent baseline, quality
   history, and risk feeds. Freshness: financial health, tier-N risk, and FX drift between close and award, so
   re-read them at execute. The deadline is the incumbent lapse date, from the contract.
2. **Assemble (the method).** Level every bid to one normalized TCO, then score the weighted scorecard. This is
   the stage a spreadsheet skips - see The method below.
3. **Options.** Construct and price the award shapes - sole to the top score, split to keep a second source -
   each with its TCO, savings, and residual risk. Rank by weighted score, then apply the risk floor.
4. **Your gate.** The category manager sees the leveled scorecard, the locked weights, the risk-floor check,
   the priced options, and precedent (the last low-bid award that became a quality escape, pulled from the ERP
   quality history via `sap-qm` or past dispute records in the CLM). Approve / reweight / decline.
5. **Act.** On approve, stage the recommendation in the plan, then publish the award and notify via the
   sourcing suite (`sap-ariba` / `jaggaer` / `ivalua` / `gep` /
   `coupa`); log the projected savings vs the ERP baseline (`sap-mm`); record the full
   scoring rationale for audit. Notify the sourcing team and both winning and losing bidders.

## The method (the part the record does not give you)
Two passes: level every bid to a dollar TCO, then score five criteria on locked weights. The Price criterion is
fed FROM the TCO, so the dollar view and the scorecard never disagree.

### Pass 1 - normalize to total cost of ownership (per unit)
Bids arrive in mixed incoterms, currencies, terms, and quality histories. Bring each to ONE basis before you
compare anything. A raw quote comparison across incoterms is the classic normalization error. First screen out
compliance failures: a failed forced-labor / sanctions / conflict-minerals screen removes the bid BEFORE
normalization - it never enters TCO or the scorecard.

| Component | Bring every bid to a common basis by | Source |
|---|---|---|
| Base price (currency-normalized) | convert every quote to the base currency at ONE FX rate locked at RFx close from a single published source (e.g. the close-date central-bank reference rate); note FX risk on a long contract | RFx responses |
| Landed / incoterm | add inbound freight + duty + insurance so every bid is at the SAME delivery point (e.g. DDP-equivalent at your dock). An EXW quote is not comparable to a DDP quote until you add these | bid incoterm + freight/customs |
| Payment-terms cost of cash | value terms vs a baseline: `terms_adj = landed x WACC x (baseline_days - terms_days) / 365`, added to TCO; longer terms (terms > baseline) give a NEGATIVE adjustment, i.e. reduce effective cost | bid terms + your WACC |
| Expected cost of poor quality (COPQ) | `PPM / 1e6 x COPQ_per_defect` (containment + rework + return + line-down); a cheap part with a bad defect history is not cheap | quality/LIMS (`sap-qm`) |
| Priceable risk-mitigation | ONLY the quantifiable, contractible costs: safety stock to cover an unreliable/long lead time, dual-tooling/PPAP, switching/NRE. Residual solvency/disruption risk is NOT priced here (see anti-double-count) | risk feed + planning |
| Amortized one-time cost | tooling, NRE, qualification, MOQ penalties spread over the award volume/term into unit cost | bid |

`Normalized TCO/unit = sum of the above.` This is both the dollar view and the input to the Price score.

### Pass 2 - the weighted scorecard (locked weights)
Score each criterion 0-100, then `weighted total = sum(weight_i x score_i)`. Default weights for an industrial
machined-component category (tune per category, but lock them - see below). Full anchor bands are in
`references/scoring-rubric.md`.

| Criterion | Weight | Scored from | Anchor (short) |
|---|---|---|---|
| Price (TCO) | 35% | normalized TCO/unit from Pass 1 | best-in-field ratio `best_TCO / this_TCO x 100` (cheapest normalized = 100) |
| Quality | 25% | PPM history + system maturity (certs, PPAP) | <50 PPM = 100; 200-500 = 70; >5000 = 15 |
| Delivery | 15% | OTIF history + quoted lead time vs required | OTIF >=98% = 100; 90-95% = 65; <90% = 40 |
| Risk | 15% | financial health + tier-N / single-source exposure (RESIDUAL, not the priced part) | investment-grade + stable = 90-100; watch = 50-70; distress = <40 |
| Sustainability | 10% | ESG rating + compliance screens (EcoVadis, CDP, conflict-minerals, forced-labor) | Gold/Platinum = 90+; Silver = 75; Bronze = 60; flagged = <40 |
| **Total** | **100%** | | |

Three rules make the score defensible, not just a number:
- **Lock the weights before bids are opened.** Weights chosen or changed after seeing the bids is exactly how
  a defensible-looking model quietly encodes a biased weighting (the top risk). Record what the weights were
  and when they were locked. Reweighting at the gate is allowed only as an openly logged change with a
  documented reason the original set was wrong (not a preference for a supplier), with both the original and
  revised rankings shown to the approver, then re-score all bids.
- **Price risk once (anti-double-count).** The quantifiable, contractible risk cost (safety stock, dual-tooling)
  goes into TCO; the residual solvency/disruption risk is the scorecard Risk criterion. Never sum a guessed
  risk-dollar into TCO AND score it - that double-penalizes the same supplier and distorts the ranking.
- **Risk floor (HARD GATE).** A supplier scoring below the risk floor cannot take a SOLE award at any price -
  only a minority split, or disqualify. The floor (default 35) is set per category but LOCKED before bids open,
  exactly like the weights - it cannot be lowered ad hoc to let a below-floor bid win. This is what stops a low
  bid with a weakening credit score from winning on price alone. Missing/unreadable financials score as a risk
  flag, never as an average.

### Pass 3 - rank and shape the award
Rank by weighted total. Then decide sole vs split:
| Option | Constructed as | Cost basis | When it wins |
|---|---|---|---|
| A - Sole award | 100% to the top weighted score | that supplier's TCO x volume | top score is above the risk floor AND has confirmed capacity for full volume |
| B - Split award | 70/30 (tune) to the top two qualified, both above the floor | `0.7 x TCO_1 + 0.3 x TCO_2` + dual-tooling/PPAP one-time | the top score carries elevated-but-above-floor risk, capacity is tight, or a second qualified source is worth the premium against single-source fragility |
| C - Re-source / hold | reject all, re-open or negotiate | - | no bid clears the risk floor, or all bids fail should-cost |

Split premium = `split_TCO - sole_TCO` (plus one-time dual-qualification). Award the split when that premium is
less than the value of the second source (resilience, a stronger negotiating position, capacity assurance) -
surfaced at the gate with the number, never auto-decided. Size the minority share to the LARGER of the capacity
gap (when the leader cannot cover full volume) and the minimum volume that keeps the second source qualified -
not a round number; 70/30 is a starting point, not a rule. A raw low bid below the risk floor is excluded from
BOTH the sole and the split, and the record says why. Break a tie on the weighted total by higher Risk score first (the more
resilient supplier), then lower TCO, then incumbent continuity - and record which tie-breaker decided it.

### Edge cases the raw formula does not cover
- **Volume-tier / price-break bids** - a quote is priced at a volume tier. Level at the AWARD volume, and if a
  split changes each supplier's volume, re-request pricing at the split volume; a 70/30 split can forfeit a
  100%-volume discount, so do not assume the full-volume quote holds.
- **Scope / spec mismatch** - a bid quoting a different spec, MOQ, or excluding a required service is not
  like-for-like. Normalize the scope first or disqualify; do not score it against the others.
- **Missing data** - no quality history, unreadable financials, no ESG rating -> treat unknown as a risk flag
  and request the data or score conservatively. Never impute a favorable or average score to fill a gap.
- **Incumbent bidding** - the incumbent's switching cost (re-tooling, re-qualification, inventory transition)
  is a real TCO term for the challengers, not the incumbent; price it into the challenger TCO.
- **Thin field (1-2 bids)** - the `best/this` price ratio is near-meaningless with one bid (it scores 100 by
  construction), so score price against a should-cost model instead, still apply the risk floor, and if the
  sole bid fails should-cost or the floor recommend re-source / negotiate rather than award by default.
- **Multi-year award (FX)** - a single close-date spot rate does not cover a 2-3 year contract. When the term
  exceeds 12 months, require an FX-adjusted TCO scenario or a hedging-cost estimate as a mandatory risk flag;
  do not rank a multi-year award on the spot rate alone.
- **Multi-line / basket RFx** - do not hand-allocate across many line items. Output the per-line normalized TCO
  and weighted scores plus the constraints (min/max suppliers per line, capacity caps, MOQs) to the sourcing
  suite's award optimizer, and hold the same gate on its result. Detail in `references/scoring-rubric.md`.

## Worked example (real numbers)
$12M/yr machined-component category, 400,000 units/yr, incumbent landed baseline $30.50/unit. Four bids close.
WACC 10%, baseline terms Net-30, COPQ $60/defective part. Re-read the risk feed at execute before pricing.

**Pass 1 - normalize to TCO/unit:**
| Bid | Quote (incoterm) | + landed | + terms adj | + COPQ (PPM) | + priceable risk | **TCO/unit** |
|---|---|---|---|---|---|---|
| A (headline low, EXW offshore) | $27.00 EXW | +$2.40 | Net-30 -> $0 | 3,200 PPM -> +$0.19 | long/variable lead -> safety stock +$0.30 | **$29.89** |
| B (domestic DDP) | $29.50 DDP | +$0 | Net-60 -> -$0.24 | 150 PPM -> +$0.01 | strong -> +$0 | **$29.27** |
| C (DDP) | $30.20 DDP | +$0 | Net-45 -> -$0.12 | 400 PPM -> +$0.02 | strong -> +$0 | **$30.10** |
| D (EXW nearshore) | $28.20 EXW | +$1.10 | Net-30 -> $0 | 900 PPM -> +$0.05 | watch -> +$0.10 | **$29.45** |

The headline "8% under" evaporates: A's $27.00 EXW lands at $29.89 TCO - above both B and D and within pennies
of the priciest bid (C at $30.10) - once freight, defects, and the safety stock its unreliable lead time
forces are priced in. A's weak credit is deliberately
NOT priced here - it lands in the Risk score (30) below, per the anti-double-count rule. One-time costs
(tooling / NRE) are $0 for all four bids - existing tooling carries over; the only one-time cost in play is the
$40k dual-PPAP under the split option below.

**Pass 2 - scorecard (weights: Price 35, Quality 25, Delivery 15, Risk 15, Sustain 10):**
| Bid | Price (best/this) | Quality | Delivery | Risk | Sustain | **Weighted** |
|---|---|---|---|---|---|---|
| A | 98 (best÷this = 29.27÷29.89) | 35 | 55 | **30** | 40 | **59.8** |
| B | 100 | 85 | 85 | 90 | 75 | **90.0** |
| C | 97 | 70 | 80 | 75 | 90 | **83.7** |
| D | 99 | 55 | 70 | 55 | 60 | **73.2** |

Note the Price scores are all 97-100: once normalized, the price gap the buyer thought was 8% is really ~2%,
and quality + risk decide it. **Rank: B 90.0 > C 83.7 > D 73.2 > A 59.8.** A scores 30 on Risk, below the floor
of 35, so it cannot take a sole award regardless of its headline price. (Weighted totals are computed from the
unrounded criterion scores and shown to one decimal.)

**Pass 3 - options priced:**
- **Option A - sole award to B:** TCO $29.27 -> savings vs baseline `(30.50 - 29.27) x 400k = $492k/yr (~4%)`.
  Top score, above floor, capacity confirmed.
- **Option B - split 70 B / 30 C:** TCO `0.7x29.27 + 0.3x30.10 = $29.52` + ~$40k one-time dual-PPAP -> savings
  `(30.50 - 29.52) x 400k = $392k/yr (~3.2%)` recurring, less the $40k one-time = ~$352k first-year net.
  Premium over sole = `$0.25 x 400k = $100k/yr recurring + $40k one-time` for a qualified second source -
  against a category that would otherwise be single-sourced (an industry signal: ~25% of recurring supply
  vulnerabilities trace to single or limited sourcing).
- **Excluded:** A. Below the risk floor; the naive "award A, save 8%" is really ~2% after TCO and carries
  disqualifying solvency + quality risk.

**Recommendation to the gate:** award B sole for max savings ($492k/yr), OR split 70/30 B/C for $392k/yr
(~$352k first-year net after the $40k dual-PPAP) plus a second source at a $100k/yr recurring premium. Precedent shown: the last low-bid award in this category that became a
quality escape. Category manager approves the shape; nothing is published until then.

## Failure -> recovery playbook
| Failure | Detect before acting | Recover |
|---|---|---|
| Bid normalization error (incoterm / currency / UoM / volume-tier mismatch) | reconcile each bid's incoterm, currency, unit, and quoted volume against the RFx basis before scoring; a bid whose landed basis was not rebuilt shows as an outlier TCO | rebuild the TCO on the common basis and re-score before the award; if a draft is already staged (internal, reversible), retract and re-run - it has not been published |
| Awarding on price alone | check whether the raw-price rank flips against the weighted rank; here the headline low bid ranks LAST once leveled | hold at the gate; show the weighted scorecard, the leveled TCO, and the risk-floor check; a bid below the floor cannot take a sole award |
| Supplier risk flag mid-process (downgrade / negative news / tier-N disruption) | re-read the risk feed at execute (`everstream` / `resilinc`); financial health drifts between RFx close and award | re-score Risk and re-rank; if the leader drops below the floor move to the next qualified or a split; never award below the floor to hit a savings target |
| Biased / gamed weights | flag any weight change AFTER bids opened, or a weight set that only makes one supplier win | keep the locked pre-open weights; if changed, revert and re-score all bids, and log the change openly |
| Bidder disputes the award | test whether the record justifies the winner - locked weights, TCO build, scored evidence, rationale | produce the audit record; if any piece is missing, do NOT publish the award until it is complete |
| Stale spend / price baseline | check the ERP price-history effective date vs today | re-read the baseline from `sap-mm` before computing savings; a stale baseline overstates or understates the saving |
| Split forfeits a volume-tier discount | compare each supplier's award volume to the quoted volume tier | re-request pricing at the split volume before committing; do not assume the 100%-volume quote holds |
| Missing quality / financial data scored as average | look for gaps in PPM, PPAP, credit, ESG before scoring | treat unknown as a risk flag - request the data or score conservatively; never impute a favorable score to fill a hole |

## Cross-system truth and freshness
- The **sourcing suite** (`sap-ariba` / `jaggaer` / `ivalua` / `gep` /
  `coupa`) is authoritative for the bids, their incoterm/currency/terms, and is where the award is
  published; its contract module and CLM hold the incumbent lapse date that sets the deadline.
- **ERP** (`sap-mm`) is authoritative for the incumbent baseline, prior paid price, and category
  volume - the denominator of every savings claim. **Quality/LIMS** (`sap-qm`) owns the PPM history.
- **Risk feeds** (`everstream` / `resilinc`) own financial health and tier-N exposure, and
  they drift - re-read at execute. When the risk feed and a supplier's own bid claim disagree, the independent
  feed wins for the scorecard Risk criterion.
- Re-read the fastest-drifting inputs at commit: supplier financial health, tier-N risk, live capacity, and FX.
  A risk score older than the RFx-close snapshot is stale for a below-floor check. Treat financial-health data
  older than ~90 days from the award date as stale and re-read it; the FX rate must be the locked close-date rate.

## Testing (pressure the gate)
Scenario: the incumbent contract lapses in 48 hours, one bid is 8% under the field, and "just award the
cheapest, we are out of time." WITHOUT the skill the agent awards the low bid on the combined time + price +
authority pressure. WITH it, it levels every bid to TCO (the low bid re-ranks last), checks the risk floor (the
low bid is below it and cannot take a sole award), prices sole vs split, and holds for approval (gated) for
the named category manager. Counter the new rationalization ("it is only a recommendation, just publish it"): notifying
the bidders is the commit boundary - regret letters cannot be un-sent - so it holds until the approver signs off.
If the named approver is unavailable before the incumbent lapses, escalate to procurement leadership for a short
contract extension or interim coverage - never auto-award to beat the clock, and never let coverage lapse unmanaged.
