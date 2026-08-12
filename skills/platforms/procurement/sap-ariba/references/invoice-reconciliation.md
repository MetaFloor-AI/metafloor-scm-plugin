# SAP Ariba - invoice reconciliation and exceptions

The downstream money leg: how an arriving invoice becomes an **Invoice Reconciliation (IR)** approvable, what
the exceptions mean, and why accepting one is the act that authorizes payment despite a mismatch. Read when a
workflow touches an invoice, an IR, a match exception, a tolerance, a service entry sheet, or a credit memo.
The one rule: approving the IR is the money event; accepting an exception overrides the control that flagged it.

## Contents
- The IR document and its states
- Matching kinds (PO-based / contract-based / non-PO)
- Exception types and tolerances
- Service entry sheets (services procurement)
- Credit memos
- E-invoicing compliance
- Gating summary

## The IR document and its states
When an invoice arrives (Network PO-flip, cXML/EDI, or converted paper), Ariba creates an **Invoice
Reconciliation** document that runs matching against the PO, the receipt(s), the contract, and tax/charge
rules. States: **reconciling** (exceptions open) -> **reconciled** (exceptions cleared or accepted) ->
**approved** (runs the IR approval flow) -> **exported / paid** (handed to the ERP). Approving the IR creates
the accounts-payable liability and authorizes payment/export - it is not a review step. The ERP posts and pays
(`sap-fi`); Ariba's control ends at export. **Approved != paid:** the export can still be rejected by
the ERP (closed period, invalid cost object, blocked vendor), leaving an IR that reads "approved" in Ariba with
no payable created - check export status, do not assume approval means the money moved.

## Matching kinds (PO-based / contract-based / non-PO)
- **PO-based** - the invoice references a PO; matched 2-way (PO + invoice), 3-way (PO + receipt + invoice), or
  4-way (adds inspection). The receipt leg is a posted goods receipt or service entry sheet, not an ASN or
  order confirmation.
- **Contract-based** - no PO; the invoice reconciles against a contract's terms and accumulators. Consumes the
  contract's committed amount.
- **Non-PO** - no PO and no contract behind it; nothing committed to reconcile against. Highest risk - flag for
  extra scrutiny, because the usual PO+receipt controls do not apply.

## Exception types and tolerances
The IR raises an **exception** for each thing that does not reconcile. Common families:
- **Price variance** - unit price above the PO/contract price beyond tolerance.
- **Quantity variance** - invoiced qty above received/ordered qty.
- **PO-amount / sub-total variance** - line or header total over the PO amount.
- **Tax / charge variance** - tax, freight, or other charges outside the expected rule.
- **Receipt exception** - invoiced without a sufficient posted receipt (a 3-way gap).

**Tolerance** is the variance band under which an exception **auto-accepts** with no human. Two consequences:
- An invoice fully within tolerance can pass with no reviewer ever seeing it.
- **Raising a tolerance pre-authorizes** every future invoice up to that gap - it is not a one-time waiver, it
  changes the auto-pass band going forward. Treat a tolerance change as a committing control change.

**One invoice, many exceptions:** an IR can carry several exceptions at once. Accepting one clears only that
one; the invoice pays only when **every** exception is cleared or accepted **and** the IR is approved. A single
exception acceptance is not by itself an authorization to pay - but on an IR with only that exception open, it is.

**Accepting an out-of-tolerance exception** overrides the specific mismatch and lets the invoice pay despite it.
The exception exists because a control caught something; accepting it is a destructive override - route it to
the named approver, do not clear it to move on. Fixing the *source* (post the missing receipt, correct the
price, have the supplier reissue) is the non-override path and is preferred.

## Service entry sheets (services procurement)
A **service** is confirmed not by a quantity goods-receipt but by a **service entry sheet** recording the effort
or amount performed, approved on its own flow. It is the physical-control leg for a service line. A service
invoice reconciles against approved service entry sheets, not a quantity receipt - do not force a goods-receipt
match on a service line, and do not treat an unapproved service sheet as a cleared match leg.

## Credit memos
A **credit memo** is a negative invoice that reduces a payable. It nets correctly only if it references the
right invoice/PO/contract; a credit memo pointed at the wrong document mis-nets the balance. Applying a credit
memo is a committing write (it changes what is owed) - apply it against the specific referenced document.

## E-invoicing compliance
A supplier invoice submitted over the Network is the supplier's **legal e-document**. In countries with tax
mandates, Ariba carries a compliance status per the legal framework configured for the supplier's country. A
non-compliant invoice cannot be legally processed in a mandated country, and **editing tax on it can break the
compliance record**. Read the compliance status; have the supplier reissue a compliant invoice rather than
editing tax to force it through. The buyer disputes/rejects a bad supplier invoice back - it does not silently
edit the supplier's amounts.

## Gating summary
- Read: view the IR, its exceptions, tolerances, matched PO/receipt/contract, and compliance status.
- Write (committing): post a receipt / approve a service entry sheet; approve an IR (creates the payable);
  accept a within-tolerance exception; apply a credit memo against the correct document.
- Destructive: accept an out-of-tolerance exception; raise a tolerance; dispute/void past controls; edit tax on
  a compliant invoice. Each authorizes payment despite a flag or breaks the compliance trail - hard gate + named approver.
