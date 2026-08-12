# Infor - receiving, three-way matching, and costing

Where a receipt or invoice becomes money, and where "quantity on hand at a price" is wrong. Read when a task
receives goods, matches a supplier invoice/voucher, or reasons about item cost, valuation, or special stock.

## Contents
- Goods receipt families
- Three-way matching and tolerances (per line)
- Valuation methods and what a receipt posts
- Special stock - consignment, subcontract
- Lot / serial control

## Goods receipt families
- A receipt against a PO increases inventory **and** drives a GL posting (M3 accounting rules immediately; LN
  once integration transactions are posted; SyteLine once the transaction is posted). It is a committing
  financial event.
- **Receipt into a held status** - stock can land in a quality/inspection or blocked status, not available.
  On hand is not available until released to an available status.
- **Reversal / cancel of a receipt** is a **counter-transaction**, not an undo: both entries stay in the
  trail, stock is re-valued, and a quantity already issued or consumed cannot be restored. The mechanism
  differs by line - M3 records a reversal/return against the receipt program, LN reverses/returns the
  warehouse receipt, SyteLine posts a return on the receiving form - but all three leave the original in the
  audit trail.
- **A receipt against the wrong PO line** carries that line's account assignment; the cost cannot be moved in
  place. Reverse the receipt and re-receive against the correct line.
- **Return to supplier** reverses a receipt against the PO and can reopen commitment and downstream credit.
- **Receipt without a PO** (where allowed) has no PO/accrual to reconcile against - higher risk; flag for
  extra scrutiny.

## Three-way matching and tolerances (per line)
The invoice is matched to the **PO** and the **receipt**; a price or quantity variance beyond the configured
tolerance raises a **matching hold** that blocks payment.
- **M3** - record the supplier invoice (APS100), then match to goods-received lines (APS360). A variance
  beyond tolerance holds the invoice.
- **LN** - register the purchase invoice (tfacp) and match it to the receipt; approval/hold on variance.
- **SyteLine** - build a **Voucher** from the receipt (Voucher Builder), match, then post. Unvouchered
  receipts sit as accrued liability until vouchered.
- **Tax and charges are part of the matched amount.** A tax or freight/landed-cost variance is a match
  discrepancy just like a price or quantity variance, and posts to the tax period (which must be open).
- **The control lives in the tolerance.** Loosening the tolerance or releasing the hold **bypasses** the
  check - it does not resolve the mismatch. Fixing the cause (correct the receipt, the price, or the PO) and
  re-matching clears a system hold the safe way. Releasing a hold to force payment is destructive and needs a
  named approver.
- **Multi-currency.** A rate difference between the PO, receipt, and invoice dates can raise a hold and post
  an exchange-rate variance even when the document-currency price matches. Read the rate, not just the amount.

**Worked example.** PO line: 10 units at $100. Goods receipt: 10 units. Supplier invoice arrives at $105/unit
with a 2% price tolerance. The invoice price is 5% over PO, beyond the 2% tolerance, so the match raises a
**price hold** - the invoice will not pay until it clears. The correct fix is to establish whether $105 is
right (amend the PO to $105, a committing change that may re-trigger approval) or wrong (return it for a
corrected invoice) - **not** to widen the tolerance to 5%, which pays the variance without resolving it.
A **quantity** variant: a 10-unit PO line over-received at 12 units under a 5% quantity tolerance is 20%
over, so the match holds on quantity. Its recovery differs from a price hold - a receipt adjustment (return
the 2 excess) or a PO amendment to 12 units, not a price correction.

## Valuation methods and what a receipt posts
The method is set **per item**; the same physical receipt posts differently.
- **Standard cost** - value is fixed at standard; a receipt at an off-standard price posts a **purchase price
  variance** to a variance account. Stock value stays at standard, the P&L absorbs the gap.
- **Average / MAUC** (LN Moving Average Unit Cost; SyteLine average) - the receipt **moves the average** of
  what is on hand. A small-quantity receipt at an outlier price distorts the valuation of the entire on-hand -
  a costing effect, not just a line.
- **FTP** (LN Fixed Transfer Price) - the item is valued at a fixed transfer price; purchase-price
  differences book to a separate variance/cost-difference account.
- **FIFO / LIFO / Lot** - value follows the layer or lot consumed; the cost of an issue depends on which
  layer/lot it draws.
- Know the method before reasoning about "cost" or netting value. A cost correction is a **revaluation** (a
  committing financial posting), not an undo.

## Special stock - consignment, subcontract
- **Consignment** - supplier-owned stock physically at your site; **ownership and the payable transfer only
  at consumption**, not at physical receipt. Counting it as own-stock overstates owned inventory and the
  balance sheet.
- **Subcontract components** - components you provide to a subcontractor sit as your special stock **at the
  supplier**; a subcontract order consumes them when the finished item is received. Exclude them from usable
  on-hand.
- Neither is free own-stock; a netting or deploy read must exclude them.

## Lot / serial control
- A **lot-controlled** item cannot move without its lot; a wrong lot mis-assigns shelf-life, origin, or
  quality and can ship expired or non-conforming stock. M3 uses lot control heavily for food/pharma
  traceability and FEFO picking.
- A **serial-controlled** item tracks each unit; movements record the specific serials.
- These do not change the read/write/destructive class of an action, but they change **what the number
  means**: stock is not fungible when it is lot/serial-controlled.
