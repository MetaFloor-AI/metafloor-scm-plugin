# Oracle ERP - procurement and receiving

The buy side: how a requisition becomes a commitment, who has to approve it, and how goods land in stock.
Read when a workflow raises or changes a requisition/PO, routes an approval, or receives, corrects, or
returns against a PO.

## Contents
- Document types (what commits spend)
- Requisition and PO lifecycle
- Approval hierarchy (AME / approval rules)
- Change orders and re-approval
- Receipt routing (when stock is usable)
- Corrections, returns, RTV
- Receipt accrual method (on-receipt vs period-end)
- Encumbrance / budgetary control

## Document types (what commits spend)
- **Standard Purchase Order** - a one-time commitment for specific items, quantities, price, and need-by date.
- **Blanket Purchase Agreement (BPA)** - a negotiated agreement (price/terms). The agreement itself does not
  commit spend; a **BPA release** against it does. Treat a release as committing.
- **Contract Purchase Agreement (CPA)** - terms only, no lines; referenced by later Standard POs.
- **Planned PO** - a long-term estimate with a delivery schedule; **scheduled releases** commit spend.
- Rule: an agreement is not a commitment; the **release/PO against it is**. Do not treat a release as a free edit.

## Requisition and PO lifecycle
- **Requisition** states: Incomplete -> Pending Approval -> Approved -> Processed (a PO/release is created).
  Incomplete is editable and withdrawable; once Approved and turned into a PO it is a commitment path.
- **PO** statuses: Incomplete -> Pending Approval -> **Open** (Approved) -> Closed for Receiving / Closed for
  Invoicing (informational soft closes that reopen on new activity) -> **Closed** -> **Finally Closed**. Also
  Cancelled and On Hold.
- **Open** = a live obligation to the supplier and (with encumbrance) a reserved obligation. **Finally Closed**
  liquidates remaining encumbrance and blocks all further receiving/invoicing/matching - a one-way door.
- Cancel vs Finally Close: Cancel reduces open quantity but leaves prior receipts/invoices in place; Finally
  Close terminates the line for good. Neither restores anything already received or invoiced.

## Approval hierarchy (AME / approval rules)
- EBS routes approvals through the **Approvals Management Engine (AME)**; Fusion uses **approval rules /
  workflow** (BPM). Both route by amount, account/cost center, item category, and the employee-supervisor or
  position hierarchy, against **approval limits / approval groups**.
- A requisition or PO above a limit routes to the next approver; it is not a commitment until fully approved.
- **Do not bypass the hierarchy**, and **do not split a requisition or lower a PO to drop under an approval
  limit** - it is the same authority violation with extra steps and it is auditable.

## Change orders and re-approval
- Editing an **already-approved** requisition or PO is not a benign write. A change to price, quantity, or
  account that crosses the approval/matching tolerance **re-triggers approval** (a change order / PO revision).
- A PO revision increments the revision number and, in Fusion, may need supplier acknowledgement. Downstream
  receipts and invoices match against the current revision.
- Treat any post-approval change that crosses tolerance as a committing action routing to the named approver.

## Receipt routing (when stock is usable)
- **Direct Delivery** - received straight into the destination subinventory; usable immediately.
- **Standard Receipt** - a two-step receive then deliver; stock sits in receiving until delivered.
- **Inspection Required** - receive -> inspect (Accept/Reject) -> deliver; rejected quantity does not become
  usable stock and may route to RTV.
- Consequence: stock in receiving or inspection is on the record but **not in the usable subinventory** and not
  available to promise until delivered (and accepted). A deploy read that ignores routing over-promises.
- A 3-way match needs the **Deliver** (receipt) posted before the invoice can pass; a 4-way match also needs
  inspection Accept.

## Corrections, returns, RTV
- **Correction** - adjusts the received quantity of an existing receipt (up or down) and reverses/adjusts the
  receipt accrual. It is a new transaction, not an edit of the original.
- **Return to Receiving** - moves delivered stock back to the receiving step.
- **Return to Vendor (RTV)** - sends received stock back to the supplier; reverses the receipt, can reopen PO
  quantity, and drives a downstream debit memo / accrual reversal.
- None of these restore a quantity already issued or consumed; each leaves a permanent transaction trail.

## Receipt accrual method (on-receipt vs period-end)
- Expense-destination items accrue either **at receipt** (perpetual - the receipt posts a receipt-accrual
  liability to GL immediately) or **at period end** (a period-end accrual run books the uninvoiced-receipt
  liability, then reverses next period). Inventory-destination receipts always accrue on receipt.
- Consequence: the method decides *when* a receipt hits the ledger, how a **receipt correction/RTV** reverses
  the accrual, and what the uninvoiced-receipt liability looks like at close. Reasoning about open liabilities
  at period end needs the method. The receipt-accrual balance clears against the invoice at match (the Oracle
  analog of GR/IR reconciliation).

## Encumbrance / budgetary control
- With budgetary control on, funds are **reserved** at each stage: a requisition creates a **commitment**, an
  approved PO an **obligation**, and an AP invoice the **actual/expenditure**. Each stage relieves the prior
  (a PO liquidates the requisition commitment; the invoice liquidates the PO obligation).
- A **funds check** must pass to reserve; a failed check (insufficient budget) blocks approval.
- **Cancel** and **Finally Close** liquidate the remaining reservation and return budget. Reopening is not
  automatic - a Finally Closed line does not give the encumbrance back on new activity.
- Gating note: reserving funds and approving an encumbered document are committing; Finally Close is destructive
  (it liquidates and terminates). Never force a funds check or override a budget failure without the budget owner.
