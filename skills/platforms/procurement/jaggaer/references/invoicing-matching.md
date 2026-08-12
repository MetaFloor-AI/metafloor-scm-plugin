# JAGGAER invoicing, receipts, and matching

Read when a task posts a receipt, reconciles an invoice, releases a hold, or touches a tolerance/credit memo.
The rule under all of it: approving/releasing the invoice is the money event, and a hold exists because
something did not reconcile.

## Contents
- Receipts: quantity vs cost
- Invoice sources and types
- Matching (2-way / 3-way)
- Exceptions and holds
- Tolerances
- Credit memos and duplicate detection
- e-invoicing compliance

## Receipts: quantity vs cost
- **Quantity receipt** - counts units received against a goods line. The physical-control leg for a goods PO.
- **Cost receipt** - records an amount/effort delivered against a service or amount line.
Crossing them (a quantity receipt on a cost line, or the reverse) breaks the match and can overpay. Match the
receipt type to the line type. A PO confirmation or ASN is a supplier *claim*, not a receipt - only a posted
receipt lets a matched invoice pass.

## Invoice sources and types
- Sources: supplier PO-flip over the JSN, cXML/EDI, or paper converted (OCR/AP entry).
- Types: **PO-based** (matches a PO), **contract-based** (matches contract terms, no PO), **non-PO** (no PO to
  match - reconciles against a contract or nothing; highest risk, extra scrutiny).
A supplier-submitted invoice is the supplier's **legal e-document**: dispute/reject it back, do not silently
edit its amounts or tax.

## Matching (2-way / 3-way)
- **2-way** - invoice vs PO (price, quantity, terms).
- **3-way** - invoice vs PO vs receipt. The receipt is what confirms goods actually arrived.
A wrong or over-receipt can clear a 3-way match and auto-pay for goods not received - receipt is a financial control.

## Exceptions and holds
A mismatch (price, quantity, receipt, tax, PO-amount, sub-total) raises an **exception** that puts an **AP hold**
on the invoice so it cannot pay.
- **Within tolerance** -> auto-clears as a **system action**, no human sees it (see tolerances).
- **Out of tolerance** -> parks on hold. Releasing the hold / accepting the exception **authorizes pay despite
  the mismatch** - destructive; route to the named approver, do not clear it to move on.
- A **non-blocking informational** exception flagged for manual acknowledgment (not auto-cleared) is a
  committing acknowledgment, one step below the out-of-tolerance override.

## Tolerances
The variance band under which a match auto-clears with no reviewer. Raising a tolerance is not a one-off - it
**pre-authorizes every future invoice** up to that gap, silently. Treat a tolerance change as destructive.

## Credit memos and duplicate detection
- A **credit memo** reduces the payable only if it references the correct invoice/PO; a wrong reference mis-nets.
- **Duplicate detection** keys on **supplier + invoice number**. Resubmitting the same bill under a tweaked
  number can slip past the check and double-pay - never renumber to get an invoice through.

## e-invoicing compliance
In countries with e-invoicing/tax mandates, an invoice carries a compliance status. A non-compliant invoice
cannot be legally processed there; editing tax to force it through can break the compliance record. Read the
status; have the supplier reissue a compliant invoice rather than editing it. The ERP still posts and pays the
approved invoice (`sap-fi`) - JAGGAER approval != paid; check export status.
