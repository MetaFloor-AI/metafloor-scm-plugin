# Dynamics 365 F&O - vendor invoices and invoice matching

How a vendor bill posts, which checks fire, and how a mismatch holds it. Read when posting or troubleshooting
a vendor invoice, a matching discrepancy, or an accrual that will not clear.

## Contents
- Invoice paths (how the bill enters)
- Matching policies (two-way / three-way)
- Tolerances and matching status
- Posting with discrepancies (the override)
- Accrual clearing (received-not-invoiced)
- Correcting an invoice (credit note / cancel)

## Invoice paths (how the bill enters)
- **From the PO (matched)** - the *Invoice* function on the confirmed/received PO pulls the ordered/received
  lines. This is the path where matching applies against the PO and product receipts.
- **Pending vendor invoice** - an invoice entered and routed through **invoice workflow** for review/approval
  before posting; it holds a saved state and matching results until posted.
- **Invoice register / approval journal** - a two-step path: register the invoice (accrue to a holding account
  for early liability recognition), then post the **invoice approval journal** to move it to the vendor and
  final accounts. Used where invoices are booked before full detail/approval.
Only **posting** commits the AP liability and the ledger voucher. Everything before that is a saved draft.

## Matching policies (two-way / three-way)
- The **matching policy** default is set in Accounts payable parameters and overridden on the released product
  (and vendor); the most specific applies:
  - **Two-way** - matches invoice **price** against the PO (net unit price); **price-totals** matching (line
    net) is a separate toggle that can be on or off within two-way.
  - **Three-way** - two-way plus **quantity** matching against posted **product receipts**.
  - **Not required** - no line matching (still subject to totals/charge checks if configured).
- A three-way item invoiced **before** its product receipt is posted fails quantity matching (nothing received
  to match) and holds. The fix is to post the receipt, not to drop the policy.
- **Charges matching** (if on) compares invoice charges to PO charges within tolerance.

## Tolerances and matching status
- **Matching discrepancy tolerances** (percentage and/or amount) are set for price and charges at company,
  item, vendor, or item-group level. Within tolerance = pass with no hold; beyond = a discrepancy.
- **Matching status** on the invoice line/header: **Passed**, **Failed**, or a warning/within-tolerance state
  flagged for review. Failed lines are held from clean posting.
- The status is computed at match time and can go stale - re-run/re-read matching at execute if receipts or the
  PO changed after the invoice was entered.

## Posting with discrepancies (the override)
- Posting an invoice whose matching status is **Failed** requires the **post-invoice-with-matching-discrepancies**
  security privilege. It is an **override**, not a resolution: it pays a bill that does not agree with the PO or
  the receipt.
- Loosening a tolerance, changing the matching policy to a weaker one, or overriding to clear a hold all bypass
  the control rather than fixing the price/quantity gap. Route a real discrepancy to a person: correct the PO,
  post the missing receipt, or get a credit from the vendor. Treat the override as a destructive action needing
  a named approver.

## Accrual clearing (received-not-invoiced)
- Posting the product receipt accrued the received value to a **product-receipt / purchase-accrual** account
  (see `procurement-receiving.md`). Posting the matched vendor invoice **reverses that accrual** and posts:
  debit purchase-expenditure-for-product (or inventory), credit the **vendor** (AP), plus any price variance.
- Received-not-invoiced is the accrual balance still open: receipts posted without a matching invoice. It is a
  real liability that must be reconciled at period end, not left to grow. A quantity/price mismatch that holds
  the invoice keeps the accrual open until resolved.
- Under **Standard cost**, an invoice price different from standard posts a **purchase price variance**; under
  Weighted/Moving average or FIFO it moves the item's running cost. Same invoice, different accounting - see
  `ledger-periods-costing.md`.

## Correcting an invoice (credit note / cancel)
- A **posted** vendor invoice is never deleted. To reverse it you post a **credit note** (a negative invoice
  that reverses distributions) or cancel it where allowed - both only land in an **open** period.
- A fully **settled** (paid) invoice needs the settlement reversed (un-settle) or a credit note; you cannot
  cancel a paid invoice outright.
- Reduce a vendor balance with a credit note, not by editing a posted voucher. Every correction is its own dated
  voucher in the trail.
