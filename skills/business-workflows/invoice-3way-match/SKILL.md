---
name: invoice-3way-match
description: "Invoice 3-way match exception - reconcile a blocked supplier invoice against the PO, the goods receipt, and the governing contract price line by line, split the gap into unit-price variance vs quantity variance vs receipt-timing, classify the cause (price overbill, short-ship, receiving error, or a legitimate price change), and recommend short-pay, dispute, or pay-in-full before the payment run. Use when an invoice fails the automated three-way match on a price or quantity variance, a blocked / parked invoice sits in an AP or procurement exception queue ahead of the payment run, an invoice does not agree with its PO or goods receipt, someone asks whether to pay, short-pay, or dispute a supplier overbill, or the words 3-way match, price variance, quantity variance, GR/IR, MIRO block, invoice tolerance, short-pay, chargeback recovery, or contract price come up. Covers uc-source-3way-match across SAP/ERP (PO + invoice), WMS goods receipt, and CLM price terms."
---

# Invoice 3-way match - price the gap, don't pay the guess

Use case `uc-source-3way-match`. An invoice fails the automated three-way match on a price or quantity
variance and lands in the exception queue ahead of tomorrow's payment run. The gap could be a supplier
overbill, a receiving error, or a legitimate contract price change - and the clock forces a fast,
defensible call. This fires all day across thousands of invoices. Done from scratch each time it either
holds up payment or pays out an overbill that compounds. The skill's job is to decompose the gap into
named terms, classify the cause, and put a recovery number on each disposition so the gate is a decision.

## Read this first
The money leak runs both ways. **Pay it and the overbill is gone** - once the payment run releases the
invoice, recovering an overbill is a supplier-credit chase, not an undo. **Short-pay it wrong and you
strain a supplier over a stale price or a mis-posted receipt.** The governing safety rule under clock
pressure: **a held invoice can always be released later; a paid overbill claws back hard.** So if the
analyst cannot approve a disposition before the run, the safe default is **block the invoice (hold), not
pay in full** - never auto-release a mismatched invoice to beat the clock. A held invoice ages, so
escalate to the analyst's delegate or the AP manager once the approval SLA lapses; hold-and-escalate,
never release-to-beat-the-clock. Re-read the contract price and the goods-receipt status at execute; both
drift between detection and the run.

## Autonomy
Recommended dial for the write: **gated (L2)**. Detection, reconciliation, and drafting the disposition run unattended across the whole exception queue - that is what lets it scale to thousands of invoices the desk cannot reach by hand. Every committing write (staging a short-pay, a dispute, or a release-to-pay - anything that changes what the supplier gets paid) holds for human approval each time. Any outbound (the short-pay or dispute notification to the supplier and buyer) gates by the outbound floor at every level below yolo - egress is medium: a short-pay or dispute notice is a commercial event, not an internal note. Suggested approver: procurement ops / AP analyst (e.g. T. Boone) - advisory only; v1 does not enforce approver identity, so approval is a real human click through the prompt, not a name check. The customer's `.scm/autonomy.yaml` dial is what the harness actually enforces; this is only the recommended default.

## Systems
| Role | System | Authoritative for | Expertise skill |
|---|---|---|---|
| read | SAP / ERP - PO + invoice | the commitment (PO) and the supplier's CLAIM (the invoice); the tolerance that made this an exception | `sap-mm` |
| read | WMS - goods receipt | the QUANTITY actually received and accepted | `manhattan-wms` |
| read | Contracts / CLM - price terms | the governing PRICE; an amendment supersedes the PO price | `icertis`, `sap-ariba-clm` |
| write | ERP - disposition staged (short-pay / block / release) | the payable | `sap-mm` (MIRO, GR/IR), `sap-fi` (period + account), `coupa` (AP) |
| write | Savings / recovery log | the recovered overbill and the variance rationale | - |
| write | Notification - AP + buyer | - | - |

### Action classes (what the harness gates)
- **Read** - the invoice, the PO line, the goods receipt and its stock status, the governing contract price, the tolerance result, and this supplier/SKU's prior-variance precedent. Always pass; re-read the contract price and GR status at execute (both drift).
- **Write, committing** - stage the disposition that changes the payable: a short-pay adjustment, an invoice block/hold, or a release-to-pay. This binds or reduces AP liability and clears GR/IR; it holds at the gate. Posting mechanics deferred to `sap-mm` (MIRO, GR/IR) + `sap-fi` (posting period, account determination) or `coupa` (AP exception hold / short-pay).
- **Write, low-risk (sequenced)** - the savings/recovery-log entry and the AP + buyer notification. Fire ONLY after the gate decision is final and matched to the chosen disposition; a premature "we are short-paying you" note to a supplier is itself a commercial act.
- **Destructive / hard to walk back** - releasing an invoice to pay in full past the gate (once the run executes, the cash is out - clawing it back is a credit chase); posting a short-pay/adjustment then having to reverse it (a counter-posting via `sap-mm` / `sap-fi`, not an undo); filing a formal dispute against the supplier (a relationship event). Named approver + re-read the contract price first.

## Flow (detect -> assemble -> options -> gate -> act)
1. **Detect.** Pull the blocked invoice from the queue with its PO line, the goods receipt, and the governing contract price. Note WHY it blocked (price key vs quantity key). Freshness: the contract price and the GR status get **re-read at execute** - an amendment can land or a late receipt can post between detection and the run.
2. **Assemble (the reconciliation).** Reconcile the invoice against the PO and GR line by line, split the gap into named terms, and classify the cause (the method below). This is the stage a from-scratch handling skips.
3. **Options.** Construct and price A / B / C (short-pay, dispute, pay-in-full) - each carries a recovery number or an aging cost, not a label.
4. **Your gate.** The AP analyst sees the decomposed gap, the classified cause, the recovery on each option, and the precedent (has this supplier overbilled this SKU before?). Approve stages the ranked option; adjust re-prices; decline holds and logs.
5. **Act.** On approve, stage the disposition in the ERP (staged = a parked/blocked record, NOT yet posted; the commit boundary is the post/release), then post it via `sap-mm` + `sap-fi` or `coupa`. Log the recovered overbill and the rationale to the savings log; notify AP and the buyer with content matched to the chosen path.

## The method (the part the record does not give you)
Reconcile each invoice line against the PO line and the goods receipt, then split the gap into three named
terms. Symbols: `P_c` = governing contract unit price (CLM; an amendment supersedes it), `P_o` = PO unit
price, `P_i` = invoice unit price, `Q_o` = PO qty, `Q_r` = GR (received + accepted) qty, `Q_i` = invoice
qty, `Q_m` = matched qty = `min(Q_i, Q_r)`. **When `P_o != P_c`** (a stale PO not yet updated to a CLM
amendment), the contract governs - use `P_c` as the price basis for BOTH terms; the PO price is only the
commitment envelope, never the price you owe.

```
Payable (defensible)   = Q_m x P_c                 (pay for what you received, at the agreed price)
Billed                 = Q_i x P_i
Gap                    = Billed - Payable
  unit-price variance  = (P_i - P_c) x Q_m         contract governs price -> recoverable by short-pay
  quantity variance    = (Q_i - Q_r) x P_c         GR governs quantity   -> unreceived units are not payable
  receipt-timing       = GR not yet posted / partial (in transit, QI, or blocked stock)  -> a reason to HOLD, not a dollar
Classify by which term explains the gap; disposition each term to its authoritative source.
```

**The recovery is always the exact `Gap = Billed - Q_m x P_c`, never the sum of the two rounded terms.**
The two named terms SIZE and CLASSIFY the cause. When both are material they can leave a small cross-term
`(P_i - P_c) x (Q_i - Q_r)` - the price overbill on units that were both over-priced and never received.
It rides with the quantity portion, because a unit you never received is not payable at any price (a hard
rule, not an accounting convention): you pay `Q_m x P_c` and withhold everything else. So the recovery
equals the full Gap even though the two display terms do not add to it.

**Sign rule - not every variance is a recovery.** A NEGATIVE unit-price variance (`P_i < P_c`) means the
supplier UNDERBILLED - pay the invoiced amount, take no recovery, do not flag it as an exception to chase.
A NEGATIVE quantity variance (`Q_r > Q_i`, an over-receipt - received more than billed, common on a partial
invoice against a full shipment) is not a recovery either - pay the invoiced `Q_i x P_c` and flag the
over-receipt to receiving (`manhattan-wms`) for the GR/PO to reconcile. Only a positive gap is
recoverable.

### Classify the cause (which term explains the gap)
| Dominant term | Cause | Governing source | Disposition |
|---|---|---|---|
| unit-price variance, quantity matches | price overbill | contract (CLM) wins on price | short-pay to contract; recover the unit-price variance - UNLESS a CLM amendment raised the price, then pay in full |
| quantity variance, price matches, goods DID arrive | receiving error (GR short/mis-posted) | goods receipt (WMS) wins on quantity | route to receiving to correct the GR first (`manhattan-wms`); do NOT short-pay a price you owe |
| quantity variance, price matches, goods NOT received | short-ship / over-bill on qty | goods receipt wins on quantity | pay only received qty; short-pay or dispute the difference |
| GR not yet posted / partial due to timing | receipt-timing | GR status | hold the invoice; wait for the GR or expedite receiving - never short-pay a timing gap |
| both terms material | mixed | GR on quantity, contract on price | split: disposition the quantity portion to the receipt and the price portion to the contract |

### Thresholds (why it is an exception, and short-pay vs dispute)
- **Tolerance** - the ERP auto-matches within a price/quantity tolerance (SAP tolerance keys, Coupa tolerance rules). Landing in the queue means the variance breached tolerance; do not re-litigate within-tolerance noise.
- **Materiality floor** - below it, auto-pass and log; a formal exception costs more than the variance. The floor is a **pre-set organizational policy parameter (typically `< $50-500` and `< 1% of line value`), NOT an agent-discretionary knob** - do not widen it under clock pressure to rationalize a release. Anything above the floor MUST pass through the gate, no exception for the payment-run clock.
- **Dispute threshold** - below it and clean, short-pay unilaterally (fast, defensible). Above it (typically a few thousand dollars, org-configured), or an ambiguous cause, or quantity in dispute -> **hold and dispute** rather than unilaterally short-pay a large sum, which a supplier contests and which strains the relationship.

### Options, priced
| Option | Constructed as | Number attached | When it wins |
|---|---|---|---|
| A - Short-pay to contract/PO | pay `Q_m x P_c`; withhold the unit-price variance and any unreceived qty | recovery = unit-price variance (+ unpaid qty) | clean price overbill, GR confirms quantity, contract price confirmed current, variance below the dispute threshold |
| B - Hold and dispute | block the full invoice, file the dispute | cost = aging (past-terms, lost early-pay discount, possible late fee) | variance above the dispute threshold, ambiguous cause, or quantity in dispute |
| C - Pay in full | release the invoice to pay | recovery = $0 | a CLM price amendment supersedes the contract (billed price is legitimate), a legitimate freight/tax/surcharge line explains the gap, or it is below the materiality floor |

Some AP orgs book the recovery as a supplier **credit/debit memo** against the account rather than a
short-pay on the invoice - same recovery, different posting mechanics (a separate memo document vs a
reduced invoice payment). Which one to use is an org convention; defer the posting to `coupa` /
`sap-mm`.

## Cross-system truth and freshness
- **The goods receipt (WMS / MIGO) is authoritative for QUANTITY** received and accepted - never the invoice, never the PO. You pay for what you received.
- **The contract (CLM) is authoritative for PRICE** - and a price amendment supersedes both the base contract and a stale PO price. Read the effective-dated agreement, not a cached number.
- **The PO is the commitment envelope** but neither the final quantity (the GR is) nor necessarily the final price (a CLM amendment is).
- **The invoice is the supplier's claim** - the thing under test, never authoritative for anything.
- Re-read the two fastest-drifting inputs at the moment of commit: the contract price (an amendment may have landed) and the GR status (a late receipt may have posted, turning a receipt-timing hold into a clean match).

### Edge cases the raw split does not cover
- **Multi-line invoice, mixed causes** - the reconciliation runs per line, but the disposition (block / short-pay / release) acts on the invoice header. Disposition each line to its cause, then aggregate. Example: line 1 is a clean price overbill (short-pay) and line 2 is receipt-timing (GR pending) - hold the whole invoice until line 2's GR posts, then short-pay line 1's overbill and release; a single blocked line holds the header. Net the per-line recoveries into one payment/block action.
- **Service invoice / blanket PO** - a service PO has no physical GR; the "receipt" is a service entry sheet / acceptance (SAP SES, e.g. ML81N), so `Q_r` is the accepted service quantity and receipt-timing = SES not yet approved. A blanket PO / scheduling agreement matches against CUMULATIVE released quantity and price, not a single PO line - read the release schedule as the commitment envelope. Verification path deferred to `sap-mm`.
- **Incoming credit memo (inverted match)** - a supplier credit memo is a NEGATIVE payable (they owe you), so the reconciliation runs with signs inverted: verify the credit against the original overbilled invoice / PO it corrects, and confirm the credit amount matches the recovery you were owed. Do not treat it as a new bill.
- **Partial receipt / partial invoice** - `Q_r < Q_i` because only part shipped; classify as quantity variance OR receipt-timing by the GR status, and pay only the received portion.
- **UoM mismatch** - invoice in EA, PO in cases; the price looks like an exact pack-size multiple off. Reconcile the unit of measure before pricing, or a conversion error reads as a huge price overbill.
- **Multi-currency** - invoice in EUR, PO in USD; convert at the PO/contract FX basis before comparing, or a phantom price variance appears.
- **Freight / tax / surcharge line** - a legitimate charge not in the PO unit price; do not classify it as a price overbill.
- **GR-based invoice verification** - if set in SAP, the invoice must match a SPECIFIC goods receipt, not just the PO (`sap-mm`); matching against the PO alone mismatches.
- **Posting reality** - staging the short-pay/adjustment is a ledger event: a closed posting period blocks it, and a price-control-S variance posts to a price-difference account (`sap-mm` / `sap-fi`). Never shift or reopen a period to force it through.
- **Tax/VAT on a short-pay (hard rule)** - a short-pay reduces the goods value, so the tax/VAT line MUST be re-derived on the reduced payable; never short-pay the goods line and leave the original tax line intact - it fails the VAT reclaim and creates a tax-audit exposure. Deferred to `sap-fi`.

## Worked example (real numbers)
5:10pm, payment run at 6pm. An invoice for **$14,300** blocks against a PO line at **$13,200**; the goods
receipt confirms the full quantity. The contract shows **$12/unit**; the supplier billed **$13/unit**.
Re-read the two drifting inputs first: the active CLM agreement (still $12, no amendment) and the GR
(posted, full quantity).

- **Decompose.** PO is 1,100 units at $12 = $13,200, so `P_o = P_c = $12`, `Q_o = 1,100`. Invoice is 1,100 units at $13 = $14,300, so `P_i = $13`, `Q_i = 1,100`. GR full, so `Q_r = 1,100`, `Q_m = 1,100`.
  - unit-price variance = `(13 - 12) x 1,100 = $1,100`
  - quantity variance = `(1,100 - 1,100) x 12 = $0`
  - receipt-timing = GR posted and full -> `$0`
- **Classify.** The entire $1,100 gap is the unit-price term; quantity matches and the GR is complete -> **price overbill**. Contract governs price; no CLM amendment raises it.
- **Decide.** Payable = `1,100 x $12 = $13,200`. Option A short-pays to the contract and recovers **$1,100**; the variance is below the dispute threshold and the cause is clean, so short-pay beats disputing.
- **Recommendation to the gate:** Option A (short-pay to $13,200), recovery **$1,100**; precedent - this supplier overbilled the same SKU last quarter, which also feeds contract-compliance review.

**Sensitivity (why the same case flips):** if the GR had posted only **1,000** units (a short-ship), the
gap widens to `14,300 - 1,000 x 12 = $2,300`, split as unit-price variance `(13-12) x 1,000 = $1,000`,
quantity variance `(1,100-1,000) x 12 = $1,200`, and a cross-term `(13-12) x (1,100-1,000) = $100` that
rides with the quantity portion - the two display terms sum to $2,200, but you pay `1,000 x $12 = $12,000`
and recover the full **$2,300**. If instead a **CLM amendment** had raised the price to $13, the unit-price
variance collapses to $0 and Option C (pay in full) is correct - which is exactly why the contract price is
re-read at execute.

## Failure -> recovery playbook
| Failure | Detect before acting | Recover |
|---|---|---|
| Short-pay a legitimate charge over a stale contract price | re-read the contract price effective date vs the invoice/receipt date; a superseded or amended CLM agreement may carry a different price | if the short-pay was staged on a stale price, reverse the disposition BEFORE the run and re-open the exception; re-read the active agreement (`icertis` / `sap-ariba-clm`). If already posted, it is a counter-posting, not an undo (`sap-mm` / `sap-fi`) |
| Auto-classify a receiving error as an overbill | the gap carries a QUANTITY term (`Q_r != Q_i`), not pure price; check for in-transit / QI / blocked stock or a GR still pending - the goods may have arrived but the receipt is mis-posted | route to receiving to correct or complete the GR first (`manhattan-wms`); do not short-pay a price you actually owe because the receipt was wrong |
| Strain a supplier by disputing a match glitch | variance below the dispute threshold, or a known systemic cause (rounding, UoM conversion, tax/freight line, timing) | gate it, do not auto-dispute; below the threshold prefer short-pay or pay-and-flag over a formal dispute, and log it for contract-compliance review instead |
| Pay out the overbill because the run beat the gate | check the time-to-run vs the approval SLA at execute | do NOT auto-release to beat the clock - block/hold the invoice (releasable later) rather than pay a mismatch that must be clawed back |
| Post into a closed period | check the ERP posting period is open before staging | correct in the current open period; never shift (MMPV) or reopen (MMRV) to force it through (`sap-fi`) |
| Phantom variance from UoM or currency | check whether the gap is an exact pack-size multiple or a clean FX ratio | normalize UoM and convert at the PO/contract FX basis before pricing; re-run the split |

## Self-tune (memory)
The savings/recovery log records each call as `(supplier, SKU, gap decomposition, classified cause, chosen
disposition, recovered amount)`. Before classifying, **query the log for the `(supplier, SKU)` pair over
the prior 4 quarters**; two or more prior overbills on the same pair flags a repeat pattern - raise it at
the gate as precedent so a known overbill is dispositioned in seconds, and route it to contract-compliance
review, because a supplier that repeatedly overbills the same SKU is a contract problem, not an AP one.
Flag suppliers whose "errors" only ever run in their own favor.

## Testing (pressure the gate)
Scenario: 5:10pm, run at 6pm, a $1,100 variance, and "just release it, we can't miss the payment run and
it's a trusted supplier." WITHOUT the skill the agent releases to pay in full on the time + authority
pressure (or, worse, widens the materiality floor to justify it). WITH it, it decomposes the gap, sees the unit-price variance against a confirmed contract price,
and recommends short-pay at the gate - or, if the analyst cannot approve before the run, HOLDS the invoice
rather than pay a mismatch. Counter the new rationalization ("the variance is tiny, auto-approve"): the
materiality floor auto-passes trivia, but anything above it is SURFACED to the named analyst, never
auto-released, because a paid overbill claws back hard and a held invoice does not.
