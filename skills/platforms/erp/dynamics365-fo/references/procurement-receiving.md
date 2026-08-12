# Dynamics 365 F&O - procurement, confirmation, and receiving

The path from a request to received stock, and where each step commits. Read when the task touches
requisitions, purchase orders, PO confirmation, change management, product receipts, WHS inbound work, or
closing remaining PO quantity.

## Contents
- The two PO status axes (do not confuse them)
- Purchase requisition and workflow
- Change management and PO confirmation
- Product receipt posting and its accrual
- WHS (advanced warehouse) inbound - different from basic
- Deliver remainder, cancel, and finalize
- Charges (misc. charges)

## The two PO status axes (do not confuse them)
A purchase order carries two independent status fields. Reading one for the other misjudges the state.
- **Approval status** (workflow / change management): Draft -> In review -> Approved -> **Confirmed** ->
  Finalized. Tracks who has authorized the order. Confirmed = committed to the vendor; Finalized = closed to change.
- **Purchase order status** (physical/financial progress): **Open order** (Backorder) -> **Received** ->
  **Invoiced** -> **Canceled**. Driven by product receipts and invoices posted against the lines, line by line.
A PO can be Confirmed (approval) but still Open order (nothing received). It can be partially Received and
partially Invoiced at once. Judge "is it committed" from Approval status and "how far has it progressed" from
Purchase order status.

## Purchase requisition and workflow
- A **purchase requisition (PR)** is a request routed by workflow: Draft -> In review -> Approved / Rejected.
  Approved demand is turned into a PO or an agreement release (manually or by the release process).
- Submitting a PR (or PO, invoice, journal) to workflow **locks** it; edit it only by **Recall**, which pulls
  it back to Draft. The approval hierarchy routes by amount, category, and financial dimension.
- Splitting a PR into smaller documents to stay under an approval limit is the same authority violation with
  extra steps, and it is auditable. Route the real amount to the real approver.

## Change management and PO confirmation
- **Change management** (activated at company, or per vendor) forces a PO through workflow approval before it
  can be confirmed. With it on, you cannot confirm a PO in Draft/In review - it must be Approved first.
- **Confirm** is the commitment. Confirming:
  - generates a **purchase order confirmation** (a versioned document) and sends the order to the vendor,
  - consumes a number sequence,
  - sets Approval status to Confirmed.
  It is a committing action, not a save.
- **Editing a confirmed PO** (price, quantity, dimension, delivery) re-triggers change-management approval and
  produces a **new confirmation version**; the version history is retained. Deactivating change management to
  skip this, or editing then quietly re-confirming to route around an approver, is a control bypass.
- Vendor collaboration: a vendor can confirm/propose changes through the vendor portal; those still flow back
  through the same confirmation and change-management path.

## Product receipt posting and its accrual
- A **product receipt** (called a *packing slip* in AX) records the **physical** receipt against the PO. It
  requires a **product receipt number** (the vendor's packing-slip reference) and updates:
  - on-hand inventory (physical) with an **estimated** cost (running average / physical cost), and
  - if the item model group posts physical inventory and the posting profile is set, a ledger **accrual**:
    debit purchase-expenditure-un-invoiced, credit a **product-receipt / purchase-accrual** account.
- It does **not** post accounts payable. The vendor liability appears only when the invoice posts.
- The accrual account is the **received-not-invoiced** balance (the D365 analog of SAP GR/IR). It clears when
  the vendor invoice posts against the same receipt. Receipts posted without invoices leave accrued purchases
  that must be reconciled.
- **Correcting / cancelling** a posted product receipt posts a new corrective document; the original and the
  correction both remain in the trail; it re-values the accrual and cannot restore a quantity already consumed.

## WHS (advanced warehouse) inbound - different from basic
- A warehouse with **"Use warehouse management processes"** enabled (the WHS / advanced warehousing module)
  does **not** take a direct product receipt on the PO. Inbound flows through **warehouse work**:
  - arrival / registration of the incoming quantity (mobile device or arrival overview / load),
  - system-generated **put-away work** directed by location directives to a location,
  - the **product receipt** posts against the completed work (or automatically per configuration).
- Loads and shipments group the inbound; license plates track handling units; waves and work templates drive
  the work. Posting a plain product receipt on a WHS-enabled warehouse, or reasoning about on-hand without the
  work and location, mis-states where stock is and whether it is put away and available.
- Basic (non-WHS) warehouses use the direct product receipt described above. Know which mode the warehouse is
  in before receiving.

## Deliver remainder, cancel, and finalize
- **Over/under delivery**: the remaining ordered quantity stays as backorder on the line. To close it without a
  receipt, reduce the **deliver remainder** to zero (or use the finalize/close function), which stops further
  receipt against that quantity.
- **Cancelling a PO line** is clean only when it has **no** posted receipts or invoices. Cancelling a line that
  already has a posted product receipt leaves the receipt, its accrual, and any invoice in place - it strands
  the accrual and breaks matching. Recover by reversing or invoicing the receipt first, then closing the
  remaining quantity; do not cancel first.
- **Finalizing** an order closes it to further change and settles remaining delivery; it is a one-way step for
  that order.

## Charges (misc. charges)
- **Misc. charges** (freight, handling, duty) attach to a PO header or line and post to their own ledger
  accounts per the charges setup. They can be automatic (charges groups) or manual.
- When **charge matching** is enabled, an invoice charge that does not match the PO charge (or exceeds
  tolerance) holds the invoice like a price discrepancy - see `invoice-matching.md`. A charge posted at receipt
  vs at invoice hits different timing; reconcile both.
