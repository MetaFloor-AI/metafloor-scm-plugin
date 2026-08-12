# RFx scoring rubric - the full anchor bands and variant methods

Loaded on demand from `rfx-scoring`. The SKILL.md carries the method and the short anchors; this file
holds the full per-criterion bands, the normalization formulas in detail, and the variant sourcing methods
(reverse auction, should-cost, multi-line award). One place only - if a band is here, it is not restated in SKILL.md.

## Contents
- Normalization formulas (the exact math)
- Per-criterion anchor bands (Quality, Delivery, Risk, Sustainability)
- Price scoring options (ratio vs min-max)
- Split-award and award-shape math
- Variant methods (reverse auction, should-cost, multi-line optimization)

## Normalization formulas (the exact math)
All bids reduce to one `Normalized TCO/unit`. Compute per unit at the award volume.

- **Currency:** `price_base = price_bid x FX_locked`. Lock one FX rate for the whole event, taken at RFx close
  from a single published source (e.g. the close-date ECB / central-bank reference rate), so a currency swing
  during evaluation does not re-rank bids. Flag FX exposure separately for a multi-year award.
- **Landed (incoterm):** bring every bid to the same delivery point. `landed = price_base + inbound_freight +
  duty + insurance` for anything not already delivered (EXW, FCA, FOB); a DDP/DDU quote already includes most of
  this. Read the Incoterm before adding, or you double-count or under-count freight.
- **Payment-terms cost of cash:** `terms_adj = landed x WACC x (baseline_days - terms_days) / 365`, added to
  TCO. Longer terms (`terms_days > baseline`) make `baseline_days - terms_days` negative, so the adjustment
  reduces TCO (cheaper to you, you hold the cash longer); shorter terms add cost. Baseline is the category's
  standard term (commonly Net-30).
- **Expected cost of poor quality:** `copq_unit = (PPM / 1,000,000) x COPQ_per_defect`. `COPQ_per_defect` bundles
  containment, sort, rework/scrap, return freight, and the expected line-down / warranty exposure - size it from
  the part's position in the line, not a flat number. A safety-critical machined part carries a far higher
  `COPQ_per_defect` than a low-consequence commodity.
- **Priceable risk-mitigation (quantifiable only):** e.g. `safety_stock_carry = extra_days_cover x daily_demand x
  unit_cost x carrying_rate / units`, plus amortized dual-tooling/PPAP and switching/NRE. Only costs you can
  contract or compute go here. The residual solvency/disruption risk is the scorecard Risk criterion - do not
  price it twice (see the anti-double-count rule in SKILL.md).
- **Amortized one-time cost:** `one_time_unit = (tooling + NRE + qualification + MOQ_penalty) / award_volume`.

`Normalized TCO/unit = landed + terms_adj + copq_unit + risk_mitigation_unit + one_time_unit`.

## Per-criterion anchor bands
Score 0-100. Anchors are defaults for an industrial machined-component category; tune per category, but lock the
mapping before bids open, the same discipline as the weights.

### Quality (weight 25% default)
Primary signal is defect history (PPM); modify by system maturity.
| PPM defective (trailing) | Score |
|---|---|
| < 50 | 100 |
| 50 - 200 | 85 |
| 200 - 500 | 70 |
| 500 - 1,000 | 55 |
| 1,000 - 5,000 | 35 |
| > 5,000 | 15 |

Modifiers (apply +/- up to 10, do not exceed 100 or drop below 0): IATF 16949 / ISO 9001 current (+), PPAP
approved for this part (+), open corrective actions or a recent recall (-), no auditable quality system (- and a
risk flag). No history at all is not a middle score - it is a data gap; request it or score conservatively.

### Delivery (weight 15% default)
Blend on-time-in-full history with quoted lead time vs required.
| OTIF (trailing) | Score |
|---|---|
| >= 98% | 100 |
| 95 - 98% | 85 |
| 90 - 95% | 65 |
| < 90% | 40 |
Then cap by lead time: a quoted lead time longer than the required window caps Delivery at 60 regardless of
OTIF, because reliable-but-too-slow still misses. A shorter, buffered lead time can lift a marginal score.

### Risk (weight 15% default) - RESIDUAL only
The quantifiable part (safety stock, dual-tooling) is already in TCO; this criterion scores what is left:
financial solvency and supply concentration.
| Financial + supply signal | Score |
|---|---|
| Investment-grade / strong Altman Z (> 3) / stable, no single-source concentration | 90 - 100 |
| Stable, mid credit, some concentration | 70 - 89 |
| Watch: deteriorating credit, Z 1.8 - 3, or a tier-N concentration flag | 50 - 69 |
| Distress: Z < 1.8, recent downgrade, negative news, or a critical single-source dependency | < 40 |

`Risk floor = 35` (HARD GATE): below it a supplier cannot take a sole award at any price - minority split or
disqualify only. Missing/unreadable financials do not score as average - they score as a flag near the floor
until the data is produced. Pull the signal from `everstream` / `resilinc` and re-read it at execute.

### Sustainability (weight 10% default)
ESG rating plus mandatory compliance screens.
| Signal | Score |
|---|---|
| EcoVadis Gold/Platinum, CDP A/B, all screens clean | 90 - 100 |
| EcoVadis Silver, screens clean | 75 - 89 |
| EcoVadis Bronze or self-declared, screens clean | 55 - 74 |
| No rating | 40 - 54 |
| Conflict-minerals / forced-labor / sanctions screen FLAGGED | 0 (disqualifying, not a low score) |
A failed forced-labor or sanctions screen is a compliance wall, not a weighted deduction - it removes the bid.

## Price scoring options
- **Best-in-field ratio (default):** `score = best_TCO / this_TCO x 100`. Cheapest normalized bid = 100; others
  scale down. Simple, monotonic, hard to game.
- **Min-max (wider spread):** `score = 100 x (worst_TCO - this_TCO) / (worst_TCO - best_TCO)`. Use when TCOs are
  clustered and you want price to differentiate more; be aware it exaggerates small dollar gaps, so only use it
  when the category manager agrees price spread should dominate. Pick one method and lock it before bids open.

## Split-award and award-shape math
- **Split TCO:** `split_TCO = share_1 x TCO_1 + share_2 x TCO_2 + one_time_dual_qualification / award_volume`.
- **Split premium:** `split_TCO - sole_TCO`. Award the split when this premium is less than the priced value of a
  second source: avoided single-source disruption exposure, a stronger hand on the next event, and capacity
  assurance. That value is often qualitative - surface the premium as a number at the gate and let the category
  manager weigh it; do not auto-decide.
- **Capacity constraint:** if the top supplier cannot cover full volume reliably, a split is not optional - it is
  required, and the second share is sized to the capacity gap, not to a round 30%.
- **Re-source / hold:** if no bid clears the risk floor, or all fail should-cost, recommend re-opening,
  negotiating, or re-scoping rather than awarding the least-bad option.

## Variant methods
- **Reverse auction:** the live-auction low is still a raw price - normalize the winning bid to TCO before you
  treat the auction result as the award. An auction compresses price but does not level quality, risk, or
  incoterm. Auction mechanics are deferred to the sourcing suite (`sap-ariba`, `jaggaer`
  Advanced Sourcing Optimizer, `ivalua`, `gep`).
- **Should-cost / cost breakdown:** where suppliers submit a cost breakdown (material, labor, overhead, margin),
  build a should-cost model and score price against the model, not only against the other bids - it catches a
  field that is uniformly overpriced. A bid far below should-cost is a risk flag (unsustainable, or a scope gap).
- **Multi-line / basket award:** for an RFx spanning many line items, a supplier may be best on some lines and
  not others. The optimal award can be a per-line or bundled allocation subject to constraints. This is an
  optimization the sourcing suite's award-scenario / optimizer runs (`jaggaer` ASO,
  `ivalua` Sourcing Decision Center, `gep` award scenarios); the workflow supplies the
  normalized per-line TCO and the weighted scores as inputs, plus the constraints to feed the optimizer -
  min/max suppliers per line, per-supplier capacity caps, MOQs, and any incumbent-retention or business-share
  floor - and holds the same gate (weights locked, risk floor, named approver) on the optimizer's result.
