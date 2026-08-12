---
name: oracle-erp
description: "Oracle ERP (Fusion Cloud ERP and E-Business Suite / EBS) - safe operation of Procurement, Receiving, Payables, General Ledger, and Inventory: requisitions and purchase orders, approval hierarchies (AME / approval rules), receipts, corrections and returns, AP invoices, invoice holds, 2-/3-/4-way matching, Subledger Accounting (SLA), GL journals, accounting periods, encumbrance / budgetary control, on-hand and item cost. Use when the connected ERP is Oracle Fusion or EBS and the work touches a purchase order, requisition, receipt, AP invoice, an invoice hold, a 3-way match, Create Accounting, a GL journal, an open or closed accounting period, an approval hierarchy, funds reservation, on-hand or item cost, or the user mentions Oracle Payables, Purchasing, iProcurement / Self-Service Procurement, Receiving, Cost Management, or Subledger Accounting."
---

# Oracle ERP - operating it safely

Oracle Fusion Cloud ERP (and the older E-Business Suite / EBS) is the book of record for procure-to-pay,
the general ledger, and inventory. What makes it dangerous is the same thing that makes it useful: the
subledgers (Payables, Purchasing, Cost Management) and the General Ledger are wired together through
**Subledger Accounting (SLA)**, so a single act like validating an invoice or accounting it can create
journal entries, consume budget, and move cash. You are not editing a form - you are posting to an audited
ledger with real money and stock behind it. This skill gives the judgment to classify each action so the
harness can gate it, plus the Oracle-specific edge states and recovery paths that decide whether a mistake
is fixable.

## Contents
- When this applies
- Object & state model
- Vocabulary that bites
- Operations: read / write / destructive
- Gotchas that bite
- Edge states & special cases
- Recovery patterns
- Guardrails
- References

## When this applies
Connector is Oracle Fusion ERP or EBS and the work is procurement, receiving, payables, GL, or inventory.
When NOT:
- SAP materials/inventory/procurement -> `sap-mm`; SAP ledger/finance -> `sap-fi`.
- Coupa as the procurement/S2P system of record -> `coupa`.
- NetSuite (Oracle's mid-market ERP, a different product and data model) -> `netsuite`.
- Oracle Transportation Management (OTM/GTM) -> `oracle-otm`.
- Out of scope here: Receivables (AR), Fixed Assets, and Projects. They share SLA and period-close mechanics
  but have their own objects and rules - do not extrapolate P2P matching/hold logic onto them.

## Object & state model (reason about state, not nouns)
- **Requisition** - a *request* to buy. States: Incomplete -> Pending Approval -> Approved -> Processed (a PO
  or agreement release is created). Editable/withdrawable while Incomplete; reversible until it becomes a PO.
- **Purchase Order** - the *commitment* to the supplier. Types: Standard PO, Blanket Purchase Agreement (BPA)
  with releases, Contract Purchase Agreement (CPA), Planned PO. Statuses: Incomplete -> Pending Approval ->
  Open (Approved) -> receiving/invoicing -> Closed for Receiving / Closed for Invoicing -> Closed ->
  **Finally Closed**. Also Cancelled, On Hold. Open = a real obligation; Finally Closed is a one-way door.
- **Receipt** - a receiving transaction against a PO. Routing decides the path: Direct Delivery (straight to
  stock), Standard Receipt (receive -> deliver), or Inspection Required (receive -> inspect -> deliver).
  Follow-on transactions: Correction, Return to Receiving, Return to Vendor (RTV).
- **AP Invoice** - the supplier bill. Types: Standard, Credit Memo, Debit Memo, Prepayment. Independent state
  axes: Validation (Never Validated / Needs Revalidation / Validated), Holds (any number applied), Accounted
  (No / Partial / Yes), Paid (No / Partial / Yes). A validated, accounted, paid invoice is fully committed.
  Editing a validated invoice, or a change to its matched PO/receipt, flips it to Needs Revalidation.
- **Payment** - the disbursement a Payment Process Request creates. States: Formatted -> Printed/Issued ->
  Remitted (sent to the bank) -> Cleared -> Reconciled. Void is clean while un-cleared; voiding a Cleared or
  Reconciled payment has bank-reconciliation consequences. Read the payment state before deciding a void is safe.
- **Subledger Accounting (SLA)** - the engine that derives journal entries for AP/Purchasing/Cost from the
  transaction. **Create Accounting** in Draft previews; in **Final** it creates and transfers entries to GL.
- **GL Journal** - the ledger entry. States: Unposted (editable) -> Posted (balances updated) -> can only be
  **Reversed** by a new reversing journal. Never un-posted.
- **Accounting period** - per ledger, statuses: Never Opened, Future Enterable, **Open**, **Closed**,
  **Permanently Closed**. Accounting and posting only land in an Open period; Permanently Closed cannot reopen.

## Vocabulary that bites
- **Validation** (AP) - Oracle's term for readying an invoice: it recalculates tax and amounts, runs
  matching, and **applies or releases holds**. It is *not* accounting and *not* payment. (Historical note:
  EBS 11i called this step "Invoice Approval" - same idea, distinct from the approval hierarchy; Fusion says
  Validation.)
- **Create Accounting** - the act that turns a subledger transaction into journal entries. Draft = safe
  preview; **Final = the point of no clean undo** (entries exist in SLA and GL).
- **Hold** (AP) - a stop flag on an invoice. System holds (matching, tax variance, distribution variance) are
  placed automatically at validation; manual holds are placed by a person. A hold blocks accounting and
  payment until released. Release the *cause*, not just the flag.
- **Matching** (2-/3-/4-way) - comparing the invoice to the PO (2-way), plus the receipt (3-way), plus
  inspection (4-way). The **Invoice Match Option** and Receipt/Inspection Required flags on the PO shipment
  set the level. A 3-way item invoiced before receipt sits on a "Qty Received" hold.
- **Tolerance** - the allowed price/quantity variance before matching auto-places a hold. Set at supplier
  site or system. Loosening it or releasing the hold bypasses the control, it does not resolve the mismatch.
- **Encumbrance / Budgetary Control** - funds reservation. A requisition creates a **commitment**, an
  approved PO an **obligation**, an invoice the **actual/expenditure**; each consumes budget via a funds
  check. Cancel or Finally Close **liquidates** the reservation.
- **Finally Close** - a terminal PO/line status that liquidates remaining encumbrance and permanently blocks
  further receiving, invoicing, or matching. Unlike Close (soft, reopens on new activity), it cannot be undone.
- **Ledger** - a book of record defined by its 4 C's (Chart of accounts, accounting Calendar, Currency,
  accounting Convention/method). A secondary ledger or reporting currency gets its own SLA entries.
- **Business Unit / Operating Unit + MOAC** - Fusion partitions data by Business Unit, EBS by Operating Unit;
  Multi-Org Access Control (data access set) decides which org's requisitions, POs, invoices you can see or post.
- **Item cost** - Standard vs Average (also FIFO/Actual). Under Standard, a price difference posts a variance
  (PPV/IPV); under Average, the transaction moves the item's average cost. Same move, different accounting.
- **Consigned inventory** - supplier-owned stock in your subinventory; ownership and the payable transfer only
  at **consumption** (creating a consumption transaction / self-billed invoice), not at physical receipt.

## Operations: read / write / destructive
Classify every operation family by what it does to state. No tool/op names - kinds of action.

| Class | Oracle ERP operation families | Gate | Why |
|---|---|---|---|
| **Read** | view/query a requisition, PO, agreement, receipt, invoice, payment, journal, supplier; on-hand and available inquiry; item cost inquiry; ledger/account balance, trial balance, aging, account analysis; period status; hold detail; approval history; **funds available inquiry**; **Create Accounting in Draft mode** (preview, no posting) | always pass | no state change; read before every write, re-read at execute |
| **Write (reversible)** | create/edit a requisition while Incomplete; build a PO in Incomplete before submit; enter an AP invoice while Never Validated (unaccounted, unpaid) - editable/deletable; create an **Unposted** GL journal - editable/deletable before post | gate one at a time | still a request/draft; no ledger or supplier commitment yet |
| **Write (committing)** | submit/approve a requisition or PO (routes the approval hierarchy, reserves encumbrance); approve a BPA/Planned release; process a receipt (Receive/Deliver - updates on-hand, accrues); **Validate** an invoice (applies/releases holds, makes it accountable); **Create Accounting (Final)**; **Post** a GL journal; reserve funds; miscellaneous/subinventory/inter-org inventory transactions; apply a prepayment to an invoice; period-end FX revaluation/translation (finance-owned); run a **Payment Process Request** (cash out) | gate + human approve | binds money, moves stock, or writes the ledger; each is an audited posting |
| **Destructive / irreversible** | reverse/correct a receipt; **Return to Vendor**; cancel a PO or line that has receipts/invoices; **Finally Close** a PO/line; cancel an AP invoice; **Void a payment**; **release an AP hold** without fixing its cause; reverse a posted GL journal; post into or reopen a **prior/closed period**; standard-cost update / cost adjustment; physical-inventory or cycle-count adjustment; a manual/top-side journal that overrides subledger; changing an approved PO past tolerance (re-triggers approval) | hard gate + named approver + re-read | permanent trail; re-values or liquidates; disburses or claws back cash; crosses a compliance/close boundary |

**Reclassification rule:** editing an *already-approved* requisition or PO above the matching/approval
tolerance is not a benign edit - it re-triggers the approval hierarchy and becomes a committing action needing
approval. Splitting a requisition to stay under an approval limit is the same authority violation with steps.

Universal rules to teach: read the document's validation + hold + accounted + period + funds state before any
write, and **re-read at execute** (state drifts, holds appear at validation); never release a hold, loosen a
tolerance, or split a value to bypass a control; a hold or a closed period means **stop**; Draft accounting is
safe, **Final accounting and posting are not**.

## Gotchas that bite (the real set - causal chains)
1. **Validation is not accounting.** Validating an invoice recalculates it, runs matching, and applies or
   releases holds; it creates no GL entry. Treating a validated invoice as "in the books" is wrong - it still
   needs Create Accounting. `references/payables-matching.md`.
2. **Create Accounting in Final mode is the point of no clean undo.** It creates SLA journal entries and
   transfers them to GL. To reverse accounted entries you post an offsetting/reversing entry; you cannot
   un-account. `references/subledger-gl-periods.md`.
3. **A closed accounting period is a wall.** Create Accounting or a journal post into a Closed period is
   refused (or, mis-set, reassigned to the next Open period and misdated). Reopening a Closed period is a
   finance-close action; a **Permanently Closed** period can never reopen.
4. **A hold means stop - clear the cause, do not just release the flag.** A matching hold (Qty Received,
   Price, Qty Ordered) or a manual hold was placed for a reason. Fixing the cause and **re-validating**
   auto-clears a *system* hold - that is a normal committing write. **Manually releasing a hold without fixing
   the cause** pays a disputed or mismatched invoice - the destructive path, needing a named approver.
5. **Matching tolerances place holds silently at validation.** A 3-way match compares invoice to PO and
   receipt; a quantity/price variance beyond tolerance auto-places a hold. Loosening the tolerance or
   releasing the hold skips the control rather than resolving the exception.
6. **The match level lives on the PO shipment.** Invoice Match Option and Receipt/Inspection Required set 2-,
   3-, or 4-way. A 3-way item invoiced before the receipt is posted sits on a "Qty Received" hold - the fix is
   to receive, not to release.
7. **Reversing or correcting a receipt is not an undo.** A Correction adjusts received quantity and reverses
   receipt accrual; a Return to Vendor reverses the receipt and can reopen PO quantity and downstream accrual.
   Both leave a permanent trail and cannot restore a quantity already delivered and consumed.
8. **Finally Close is irreversible.** It liquidates remaining encumbrance and permanently blocks further
   receiving, invoicing, and matching. Unlike a soft Close (which reopens on new activity), it cannot be undone.
9. **Cancelling a PO with receipts or invoices strands them.** Cancel reduces the ordered quantity, but
   existing receipts, accruals, and invoices remain; the accrual can be left open and downstream matching
   breaks. Recover by matching existing invoices to the reduced quantity and issuing a return/debit memo for
   the excess before cancelling, not by cancelling first.
10. **Budgetary control reserves funds at every stage.** With encumbrance on, a requisition reserves a
    commitment, an approved PO an obligation, an invoice the actual; a failed funds check blocks approval, and
    Cancel/Finally Close liquidates the reservation. Acting without a successful funds check silently fails.
11. **SLA is the only correct source of subledger GL entries.** AP/Purchasing/Cost transactions are accounted
    by Create Accounting, not posted to GL by hand. Editing the GL journal that came from a subledger breaks
    reconciliation between the subledger and the ledger.
12. **A posted GL journal cannot be un-posted.** Correcting it means a reversing journal - a new, dated entry
    that shows both sides in the audit trail. The reversal date must fall in an Open period.
13. **A Payment Process Request is cash out the door.** To undo you Void the payment, which reverses its
    accounting and reopens the invoice; voiding a payment already cleared/reconciled at the bank has
    reconciliation consequences.
14. **Cancelling an AP invoice reverses its distributions and accounting.** You can cancel only if it is
    unpaid (else Void the payment first); if it was accounted, cancellation posts reversing entries in an Open
    period. A fully paid invoice cannot simply be cancelled.
15. **A prepayment does nothing until applied.** A Prepayment invoice pays the supplier in advance and only
    reduces a later Standard invoice when explicitly applied; an unapplied prepayment overstates what is owed.
16. **On-hand is not available.** Reservations, consigned stock, and stock in an inspection/hold subinventory
    reduce what is actually available to promise; available-to-transact and ATP differ from on-hand quantity.
17. **Consigned inventory is supplier-owned until consumed.** It sits in your subinventory but ownership and
    the payable transfer only at consumption; counting it as owned overstates inventory value and the balance sheet.
18. **Costing method changes what a move posts.** Under Standard cost, a receipt/invoice at an off-standard
    price posts a purchase/invoice price variance (PPV/IPV) to a variance account; under Average cost the
    transaction moves the item's average. A small-quantity receipt at an outlier price can shift the average.
19. **Invoice Price Variance posts even on a clean match.** When invoice price differs from PO price, a 3-way
    match can still pass yet post an IPV (and, in foreign currency, an exchange-rate variance) to the P&L.
20. **Multi-org partitions everything.** A requisition, PO, receipt, and invoice each live in one Business
    Unit / inventory org; querying or posting in the wrong org shows nothing or posts to the wrong books. The
    data access set (MOAC) bounds what you can see and touch.
21. **Receipt routing decides when stock is usable.** With Standard or Inspection-Required routing, stock sits
    in receiving/inspection and is not in the usable subinventory until delivered (and accepted). Direct
    Delivery makes it usable at receipt.
22. **Approval hierarchy exists on purpose.** Requisitions and POs route by amount, account, and category
    through AME (EBS) or approval rules (Fusion). Changing an approved document past tolerance re-triggers
    approval; do not engineer around it.
23. **Reduce a supplier balance with a credit/debit memo, not a cancel.** To lower what you owe, the usual
    path is a Credit or Debit Memo (a new AP document with its own accounting), not cancelling the original invoice.
24. **Foreign-currency documents carry rate risk.** A rate difference across PO/receipt/invoice posts exchange-
    rate variance, and period-end revaluation/translation restates open balances in the ledger currency.
25. **The accounting date, not today, picks the period.** A transaction posts to the period of its
    accounting/GL date, not the system date. Letting the date default when the current period is closed
    silently misposts to the next Open period; set the accounting date into the intended Open period.
26. **Batch operations commit many documents at once.** Batch Validate, mass Create Accounting, and a Payment
    Process Request each act on a *set* of documents; read the selection scope before running, because one
    action can move dozens of invoices into an accounted or paid state, or raise many holds together.
27. **An unmatched invoice skips matching entirely.** A Standard invoice entered without a PO reference has no
    matching holds - only tax and distribution checks - so the 2-/3-/4-way controls never fire. An expense
    that should have sat on a PO can be paid with no receipt or price check.
28. **Accrual timing depends on the accrual method.** Expense items accrue either at receipt (perpetual) or at
    period end; the method decides when the receipt accrual hits GL and how a receipt reversal or period close
    treats it. Reasoning about open liabilities at close needs the method. `references/procurement-receiving.md`.
29. **A PO change order matches against the current revision.** Editing an approved PO past tolerance opens a
    change order, runs its own approval, and increments the revision; receipts and invoices then match the
    current revision. Editing without tracking the revision strands downstream documents against a stale one.
30. **Withholding tax places its own holds and reduces the payment.** Automatic withholding computes tax at
    validation/payment, can hold the invoice until the tax is accounted, and pays the supplier net of the
    withheld amount - a distinct mechanism from matching holds. `references/payables-matching.md`.

(Deeper per-topic detail: `references/procurement-receiving.md`, `references/payables-matching.md`,
`references/subledger-gl-periods.md`, `references/inventory-costing.md`.)

## Edge states & special cases
Each breaks naive "quantity on hand at a price" or "one invoice, one entry" logic. Key rule inline; full
behavior in the reference noted.
- **Encumbrance / budgetary control** - commitment -> obligation -> actual, each a funds reservation; a failed
  funds check blocks the document; Cancel/Finally Close liquidates. Detail in `references/procurement-receiving.md`.
- **Multi-org / MOAC** - Business Unit (Fusion) or Operating Unit (EBS) plus data access set bound visibility
  and posting; wrong org = wrong books.
- **Foreign currency** - conversion rate at each stage; IPV/ERV on variance; GL revaluation and translation at
  period end. Detail in `references/subledger-gl-periods.md`.
- **Consigned inventory** - supplier-owned until consumption; exclude from owned value until the consumption
  transaction. Detail in `references/inventory-costing.md`.
- **Lot / serial / revision control** - a controlled item cannot transact without its lot/serial; a wrong lot
  mis-assigns shelf-life or quality.
- **Secondary ledger / reporting currency** - gets its own SLA accounting; a manual GL entry in the primary
  does not flow there automatically.
- **Partial failure** - Create Accounting (Final) and a Payment Process Request can succeed for some documents
  and fail for others, leaving the subledger and GL (or a pay run) partly done. Reconcile the exceptions; do
  not blindly retry the whole set.

## Recovery patterns (can it be undone, and what can't)
- **Reverse a posted GL journal** - a new reversing journal, dated in an Open period; both entries stay in the
  trail. You cannot un-post.
- **Un-account** - Final accounting is reversed only by a GL reversal or an offsetting subledger entry, not by
  deletion; Draft accounting can be re-run.
- **Void a payment** - reverses the disbursement; the invoice returns to Validated/Unpaid; bank-reconciliation
  impact if the payment was already cleared.
- **Cancel an AP invoice** - posts reversing distributions; only when unpaid, and the reversal lands in an Open period.
- **Receipt Correction / Return to Vendor** - each is a new transaction with a permanent trail; neither
  restores a consumed quantity.
- **Finally Close** - not reversible. Use soft Close if any further activity is possible.
- **Period reopen** - owned by the finance close; a Permanently Closed period never reopens. Correct in the
  current Open period instead.
- **Wrong item cost** - corrected by a cost update/adjustment (itself a committing revaluation), not an undo.
- **Batch partial failure** - read the exception report and fix each failed document on its own; do not blindly
  retry the batch, since retrying can double-post the subset that already succeeded.

## Guardrails
- Read the document's validation + hold + accounted + paid + period + funds state before acting; re-read at
  execute, because holds appear at validation and periods close underneath you.
- Never release a hold to force payment, never loosen a tolerance or split a value to dodge a control, and
  never post into or reopen a closed period from a subledger. If a closed month needs a correction, it is a
  finance-close decision made in the current Open period.
- Treat Validate, Create Accounting (Final), Post, a receipt, an inventory transaction, and a Payment Process
  Request as committing ledger/stock/cash events. Draft accounting is the safe preview.
- For anything in the destructive row (reverse, cancel, Finally Close, void, hold release, cost adjustment,
  period reopen): named approver, re-read, and log the reason. It liquidates, revalues, or moves cash - it is
  not a correction.

Never, under any pressure: edit a GL journal that came from a subledger (correct the subledger and re-account);
release a hold or loosen a tolerance to force a payment; override a funds-check failure without the budget
owner; change a period status to force a posting; split a document to drop under an approval limit; enter an
unmatched Standard invoice for an expense that should sit on a PO (it skips every matching control); or Finally
Close a line that may still see activity.

## References (load on demand)
- `references/procurement-receiving.md` - requisition/PO lifecycle, document types and releases, approval
  hierarchy (AME / approval rules), change orders and re-approval, receipt routing, corrections/RTV, encumbrance.
- `references/payables-matching.md` - invoice types, validation, 2-/3-/4-way match and Invoice Match Option,
  hold families (system vs manual) and tolerances, IPV/ERV, prepayments, payment/void, cancel, credit/debit memo.
- `references/subledger-gl-periods.md` - Subledger Accounting, Create Accounting Draft vs Final, transfer/post
  to GL, journal states and reversal, period statuses, budgetary control accounting, secondary ledger/currency.
- `references/inventory-costing.md` - on-hand vs available, material transaction families, reservations,
  consigned stock, Standard vs Average costing and variances, multi-org / MOAC.
