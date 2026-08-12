# Oracle OTM - freight payment and settlement

Settlement is money out: it pays the carrier. The core risk is approving a charge that was not earned, or
letting auto-pay pay from a wrong shipment cost. Read when a workflow matches, audits, approves, vouchers,
or allocates a freight invoice.

## Contents
- The three steps: match -> approve/voucher -> allocate
- Invoice and voucher statuses
- Match-and-pay vs auto-pay / self-billing
- Accessorials and tolerance
- Recovery: credits and adjustments

## The three steps: match -> approve/voucher -> allocate
1. **Match** - the carrier's freight invoice (often EDI 210) is matched to its buy shipment. OTM validates
   the invoice cost lines against the planned shipment cost. A clean match means the carrier billed what was
   agreed.
2. **Approve + issue voucher** - approving the matched invoice creates a **voucher**: the payment record
   authorized to AP. The voucher is issued to the ERP/AP via the Send Voucher Interface action. Approval is
   the money-out commit.
3. **Allocate** - a voucher allocation rule spreads the freight cost back to the orders/lines (by weight or
   volume) so cost lands on the right business object. Until allocated, the cost is unassigned.

## Invoice and voucher statuses
- Invoice: NEW -> MATCHED -> APPROVED (then a voucher exists). A mismatch holds it as an exception.
- Voucher allocation status starts NOT ALLOCATED; it becomes allocated only after the allocation step runs.
- An **approved but un-issued** voucher is not yet money in AP; an **issued but un-allocated** voucher has
  paid the carrier but not yet assigned cost. Both are half-done settlement, not "done".

## Match-and-pay vs auto-pay / self-billing
- **Match-and-pay** - the carrier submits an invoice; OTM matches it to the shipment, and you approve. There
  is a document to check against.
- **Auto-pay / self-billing (evaluated receipt)** - OTM *generates* the invoice from the shipment cost with
  no carrier invoice. There is nothing to match against, so if the shipment cost is wrong (bad rate, missing
  accessorial, wrong weight) OTM pays the wrong amount automatically and nothing flags it. Verify the
  shipment cost before relying on auto-pay.

## Accessorials and tolerance
- Accessorial costs (detention, fuel, liftgate, reweigh) are extra charges beyond the base rate; a carrier
  invoice often adds them. They are the common source of an invoice exceeding the planned cost.
- A tolerance defines how far an invoice may exceed the plan and still auto-match. Approving *over tolerance*
  without resolving the variance overpays and buries the exception - review the accessorial, do not wave it through.

## Recovery: credits and adjustments
- An overpaid or wrongly approved invoice is NOT corrected by un-approving; the approval and voucher stay in
  the trail. Correct it with a **credit or adjustment invoice** or an offsetting voucher - a new document.
- **Voiding/reversing an issued voucher** after it reached AP is a downstream financial reversal; coordinate
  with AP/ERP rather than treating it as a delete inside OTM.

Gating note: matching and rating are reads; approving an invoice + issuing its voucher is committing (money
out); voiding/reversing an issued voucher is destructive (a financial reversal, not an undo); auto-pay makes
the shipment cost itself the payment basis, so verifying that cost is the control point.
