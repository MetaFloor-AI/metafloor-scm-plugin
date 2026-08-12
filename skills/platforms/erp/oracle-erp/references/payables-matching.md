# Oracle ERP - Payables, matching, holds

The pay side: how an AP invoice is entered, matched to the PO and receipt, held when it disagrees, accounted,
and paid. Read when a workflow enters or validates an invoice, works a hold, runs a match, or issues a payment.

## Contents
- Invoice types
- Validation (what it does)
- Matching: 2-/3-/4-way and the Invoice Match Option
- Holds: system vs manual, and how to clear them
- Tolerances
- Variances (IPV / ERV)
- Withholding tax
- Prepayments
- Payment, void, and cancel
- Credit and debit memos

## Invoice types
- **Standard** - the ordinary supplier bill; matched to a PO/receipt or entered **unmatched**. An unmatched
  Standard invoice has no matching holds - only tax/distribution checks - so the 2-/3-/4-way controls never
  fire; an expense that belonged on a PO can be paid with no receipt or price check.
- **Credit Memo / Debit Memo** - reduce what is owed (a return, a negotiated credit). A new document with its
  own accounting - the correct way to lower a balance, not cancelling the original invoice.
- **Prepayment** - pays the supplier in advance; only offsets a later Standard invoice when **applied**.

## Validation (what it does)
- Validation recalculates tax and amounts, runs **matching**, checks the period and distributions, and
  **applies or releases holds**. Its outputs: Validated / Needs Revalidation, plus any holds.
- Validation is **not** accounting and **not** payment. A Validated invoice with no holds is eligible to be
  accounted (Create Accounting) and then paid - but nothing has posted to GL yet.
- (EBS 11i named this step "Invoice Approval", which is distinct from the approval *hierarchy* - do not conflate.)

## Matching: 2-/3-/4-way and the Invoice Match Option
- **2-way** - invoice vs PO (price and quantity billed vs ordered).
- **3-way** - invoice vs PO vs **receipt** (adds quantity received).
- **4-way** - invoice vs PO vs receipt vs **inspection** (adds quantity accepted).
- The level is set on the PO shipment by **Receipt Required** and **Inspection Required**. The **Invoice Match
  Option** (Purchase Order vs Receipt) decides whether the invoice matches to the PO or to specific receipts.
- Consequence: a 3-way item invoiced before its receipt is posted validates onto a **Qty Received** hold - the
  fix is to post the receipt, not to release the hold.

## Holds: system vs manual, and how to clear them
- **System (matching) holds** are placed automatically at validation when the invoice breaks a rule:
  Qty Ordered, Qty Received, Price, Amount, Maximum Ordered/Received, tax variance, distribution variance,
  no-rate (currency). They clear when the **cause** is fixed and the invoice is re-validated (receive the
  goods, correct the price, fix the distribution).
- **Manual holds** are placed by a person (dispute, pending credit, compliance). They clear only by manual
  **release** with a reason.
- A hold blocks **both accounting and payment**. **Releasing a hold to force a payment through, without fixing
  the underlying mismatch, pays a wrong or disputed invoice** - that is a destructive action needing a named
  approver, not a reflex. Prefer to clear system holds by correcting the cause.

## Tolerances
- **Matching tolerances** (price %, quantity %, amount, shipment/total) are defined at the supplier site or
  system level and decide how much variance is allowed before a matching hold is placed at validation.
- Loosening a tolerance or raising a limit to avoid a hold **bypasses the control** - it does not resolve the
  variance and it is auditable. Treat a tolerance change as a controlled configuration action, not a fix.

## Variances (IPV / ERV)
- **Invoice Price Variance (IPV)** - when the invoice unit price differs from the PO price, validation/matching
  posts the difference to an IPV account. The invoice can pass the match yet still post a variance to the P&L.
- **Exchange Rate Variance (ERV)** - for a foreign-currency invoice, a rate difference between PO/receipt and
  invoice posts to an ERV account.
- Under **standard costing**, receipt-side differences post **Purchase Price Variance (PPV)**; under average
  costing they move the item's average. See `inventory-costing.md`.

## Withholding tax
- **Automatic withholding tax (AWT)** computes tax to withhold from a supplier at validation or payment. It
  can place a **system hold** until the withheld tax is accounted, and it pays the supplier **net** of the
  withheld amount (Oracle books a withholding invoice to the tax authority).
- This is a distinct mechanism from matching holds - do not clear a withholding hold by manual release; it
  resolves when the withholding is accounted per the setup.

## Prepayments
- A **Prepayment** invoice pays in advance and sits available to apply. It reduces a later Standard invoice
  only when explicitly **applied** to it. An unapplied prepayment overstates the open payable to the supplier.

## Payment, void, and cancel
- A **Payment Process Request (PPR)** selects validated, accounted, unheld invoices and disburses cash. This is
  a committing cash event.
- **Void a payment** - reverses the payment accounting and reopens the invoice for payment. If the payment was
  already cleared/reconciled at the bank, voiding has bank-reconciliation consequences.
- **Cancel an invoice** - reverses its distributions and (if accounted) posts reversing entries in an Open
  period. Cancel is possible only when the invoice is **unpaid**; a paid invoice must have its payment voided
  first. A fully paid, accounted invoice cannot simply be cancelled.
- Gating note: PPR = committing; Void, Cancel, and hold-release = destructive (cash claw-back or reversing
  postings), each needing a named approver and a re-read of current state.

## Credit and debit memos
- To reduce a supplier balance (return, overbilling, negotiated credit), issue a **Credit Memo** or **Debit
  Memo** matched to the PO/invoice. It is a new AP document with its own accounting and audit trail - the
  correct mechanism, versus cancelling or editing the original invoice.
