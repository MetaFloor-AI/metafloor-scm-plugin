---
name: dynamics365-fo
description: "Microsoft Dynamics 365 Finance & Operations (F&O; lineage Dynamics AX) - safe operation of Procurement, product receipt, accounts payable and vendor invoice matching, general ledger, inventory, and Warehouse management (WHS): purchase requisitions and orders, PO confirmation and change management, product receipt posting, vendor invoice two- and three-way matching, subledger-to-GL vouchers, GL journals, fiscal and ledger calendar period status (Open / On hold / Closed / Permanently closed), inventory close and costing, item model group, financial dimensions, and number sequences. Use when the connected ERP is Dynamics 365 F&O, Supply Chain Management, or Finance (or Dynamics AX / AX 2012), or the work touches a PO confirmation, product receipt, packing slip, vendor invoice, a matching discrepancy or matching policy, a voucher, a general journal, a closed or on-hold period, an inventory close, financial dimensions, or a number sequence."
---

# Dynamics 365 Finance & Operations - operating it safely

Dynamics 365 F&O (one platform, sold as Dynamics 365 Finance + Supply Chain Management; the lineage is
Dynamics AX / Axapta) is the book of record for procure-to-pay, the general ledger, and inventory. What
makes it dangerous is that source documents post through **subledgers into the general ledger as vouchers**:
a single act like confirming a PO, posting a product receipt, or posting a vendor invoice can commit a
supplier, move stock, accrue a liability, and write the ledger. You are not saving a form - you are posting
an audited voucher with real money and stock behind it, numbered from a sequence you cannot cleanly rewind.
This skill gives the judgment to classify each action so the harness can gate it, plus the F&O-specific edge
states and recovery paths that decide whether a mistake is fixable.

## Contents
- When this applies (and when NOT)
- Object & state model · Vocabulary that bites
- Operations: read / write / destructive (the matrix + reclassification rule)
- Gotchas that bite · Edge states & special cases · Recovery patterns · Guardrails
- References: `procurement-receiving.md`, `invoice-matching.md`, `ledger-periods-costing.md`

## When this applies
Connector is Dynamics 365 F&O / Supply Chain Management / Finance (or the older Dynamics AX / AX 2012) and
the work is procurement, receiving, payables, general ledger, inventory, or warehousing. When NOT:
- **Business Central** (Dynamics 365 BC, the SMB product, lineage NAV/Navision) - a different product,
  data model, and posting engine; not covered by this skill and not one this plugin ships. Do not
  extrapolate F&O logic onto it.
- SAP materials/inventory/procurement -> `sap-mm`; SAP ledger/finance -> `sap-fi`.
- Oracle Fusion ERP or EBS -> `oracle-erp`; Coupa as the S2P system of record -> `coupa`.
- **Dynamics 365 Customer Engagement / CRM (Dataverse: Sales, Field Service)** - a separate app and store ->
  `dynamics-crm`. F&O and CE share the "Dynamics 365" brand but not the data or the ledger.
- Out of scope here: Accounts receivable, Fixed assets, Project accounting, and Production/BOM costing. They
  share the voucher and period-close mechanics but have their own objects - do not extrapolate P2P logic.

## Object & state model (reason about state, not nouns)
- **Purchase requisition (PR)** - a *request* to buy, routed by workflow. States: Draft -> In review ->
  Approved (or Rejected) -> becomes demand for a PO / release. Editable while Draft; recall to edit once submitted.
- **Purchase order (PO)** - the *commitment*. It carries **two independent status axes**, and confusing them
  misjudges the state:
  - **Approval status** (workflow / change management): Draft -> In review -> Approved -> **Confirmed** ->
    Finalized. Confirmed = the PO is committed and sent to the vendor. Finalized = closed to further change.
  - **Purchase order status** (physical/financial progress): Open order (Backorder) -> **Received** ->
    **Invoiced** -> Canceled. Driven by product receipts and invoices, not by workflow.
  - **Remaining quantity** on each line stays as backorder until received or closed; **deliver remainder** (set
    to zero) or **finalize** closes the outstanding quantity without a receipt - a state change, not a delete.
- **Product receipt** - the receiving document (called a *packing slip* in AX). Posting it records the
  physical inventory receipt and, if configured, an accrual to the ledger. Requires a product receipt number.
- **Vendor invoice** - the supplier bill. Paths: from the PO (matched), a *pending vendor invoice* (workflow),
  or the *invoice register / approval journal*. It stays a saved draft until **posted**; posting is the AP
  commitment. A posted invoice then carries a **settlement** state (Open -> Settled/Paid); a settled invoice
  must have its settlement reversed before it can be credited or cancelled.
- **Voucher** - every posting creates a voucher: a balanced set of ledger entries with a date and a number.
  Subledger transactions post a subledger journal that transfers to the **general ledger** (sync or batched).
- **General journal** - manual ledger entry. Lines are editable until **posted**; a posted voucher is never
  un-posted, only reversed by a new reversing voucher.
- **Ledger / fiscal calendar** - fiscal years split into periods. The **ledger calendar** sets each period's
  status **per module**: Open, **On hold**, **Closed**, **Permanently closed**. Postings land only in Open.
- **Inventory transaction** - each item movement carries a receipt/issue status (On order -> Ordered ->
  Registered -> Received -> Purchased for receipts; Reserved -> Picked -> Deducted -> Sold for issues) and an
  estimated cost until it settles at invoice / inventory close.

## Vocabulary that bites
- **Confirm (a PO)** - the act that commits the order and sends it to the vendor, creating a confirmation
  version and consuming a number. Not a save. -> *Write (committing)*.
- **Change management** - when activated, a PR/PO must clear workflow approval before it can be confirmed;
  editing a confirmed PO re-triggers approval and a new confirmation version. Turning it off skips a control.
- **Product receipt / packing slip** - the *physical* receipt. Updates on-hand and an estimated cost, and
  accrues a liability to the ledger if the posting profile says so; it does **not** post AP. -> *committing*.
- **Matching policy** - Two-way (price; **price-totals** matching is a separate toggle within it) or Three-way
  (adds product-receipt quantity), set as the Accounts-payable default and overridden on the released product
  (and vendor); the most specific applies. Decides which invoice checks fire.
- **Matching discrepancy** - a price/quantity/charge variance beyond tolerance holds the invoice; posting past
  a failed match needs the *post-invoice-with-matching-discrepancies* privilege - an override, not a resolution.
- **Item model group** - controls costing method (Standard, Weighted avg, Moving avg, FIFO, LIFO) and whether
  physical/financial **negative inventory** is allowed. It changes what a receipt/issue posts.
- **Inventory close** - the period settlement that matches issues to receipts by costing method and posts cost
  adjustments. Posting back into a closed inventory period means cancelling the close and re-running it.
- **Physical vs financial** - physical on-hand/cost updates at product receipt (estimated); financial value
  settles at invoice and inventory close. "On hand" at physical cost is not the final cost.
- **Financial dimensions** - user-defined dimensions (Department, Cost center, Business unit...) that combine
  with the main account to form the ledger account; they default from account/vendor/item and can be validated.
- **Number sequence** - **continuous** (no gaps, serializes vouchers/invoices; a failed post reserves a number
  needing cleanup) vs **non-continuous** (gaps allowed, faster). Confirming/posting consumes a number.
- **Posting profile** - the mapping from a transaction to ledger accounts (vendor posting profile, inventory /
  item posting). A wrong profile posts to the wrong accounts silently.
- **WHS / advanced warehousing** - a warehouse with "Use warehouse management processes" on receives through
  warehouse *work* (arrival, registration, put-away) via a load / mobile device, not a direct product receipt.

## Operations: read / write / destructive
Classify every operation family by what it does to state. No tool/op names - kinds of action. The **Gate**
column is what the harness must do: a read passes; a reversible write is confirmed **one action at a time** (no
batching drafts through); a committing write needs human approval; a destructive action needs a named approver
plus a fresh re-read at execute.

| Class | Dynamics 365 F&O operation families | Gate | Why |
|---|---|---|---|
| **Read** | view/query a PR, PO, confirmation, product receipt, vendor invoice, voucher, journal, vendor; on-hand physical/financial/available and reservation inquiry; item running cost inquiry; trial balance, vendor balance, aging, account/voucher transactions; **accounting source explorer / voucher transactions** (what a posting did to the ledger); ledger period status; matching status detail; workflow history; a **preview / simulation** (inventory recalculation preview, cost estimate) that posts nothing | always pass | no state change; read before every write, re-read at execute |
| **Write (reversible)** | create/edit a PR while **Draft** (before submit); build a PO while Draft/Open before **Confirm** (no receipt/invoice yet); enter a vendor invoice in a *pending vendor invoice* or invoice register before posting; create a general or inventory journal with lines, **before posting** (editable/deletable); **delete a still-draft document** (a PR/PO before Confirm, a pending invoice before post, an unposted journal - reversible because nothing posted); place/cancel an inventory **reservation** or marking - **but cancelling a reservation tied to confirmed demand (e.g. a sales order) releases committed stock and changes ATP -> treat as committing** | gate one at a time | still a request/draft; no vendor commitment, stock move, or ledger voucher yet |
| **Write (committing)** | submit a PR/PO/invoice/journal to workflow (routes approval); **Confirm** a PO (vendor commitment + confirmation version + number); **post a product receipt** (physical stock + estimated cost + accrual to GL); **post a vendor invoice** (AP liability + GL + clears accrual + settles inventory cost); **post a general journal / inventory movement / transfer / counting journal** (voucher); transfer subledger to GL; reserve budget (if budget control on) | gate + human approve | binds money, moves stock, or writes the ledger; each is an audited voucher |
| **Destructive / irreversible** | **cancel / correct a posted product receipt**; **return to vendor (a negative product receipt)**; cancel a PO or line that has receipts/invoices; **close remaining quantity (deliver remainder / finalize)**; **reverse a posted vendor invoice (credit note)**; **reverse a posted GL voucher (Reverse transaction / storno)**; **post an invoice with matching discrepancies (override)**; post into or reopen a **Closed / On-hold** period (a **Permanently closed** period never reopens); **run or cancel an inventory close**; adjustment/counting journal that revalues stock; **activate a standard cost version** (revalues on-hand); ledger settlement / un-settlement; **override a budget-check failure** (if budget control on); turn off change management or a matching policy | hard gate + named approver + re-read | permanent voucher trail; revalues or liquidates; commits or claws back money; crosses a period/compliance boundary |

**Reclassification rule:** editing an *already-confirmed* PO (price, quantity, dimension) is not a benign
edit - with change management it re-triggers workflow approval and a new confirmation version, so it is a
committing action. Splitting a PR/PO to stay under an approval limit is the same authority violation with steps.

Universal rules to teach: read the PO's approval status + PO status + product-receipt/accrual state + matching
status + period status + inventory-close status before any write, and **re-read at execute** (state drifts,
periods close, matching holds appear). Never post into a Closed/On-hold period; never override a matching
discrepancy, loosen a tolerance, or turn off a control to force a posting; a hold or a closed period means
**stop**; a preview/simulation is safe, a **post is a voucher** and is not.

## Gotchas that bite (the real set - causal chains)
1. **Confirming a PO is the commitment, not a save.** Confirm generates a confirmation version, sends the
   order to the vendor, and consumes a number sequence. With change management on, changing a confirmed PO
   re-triggers approval and a new version. `references/procurement-receiving.md`.
2. **A PO has two status axes and they move independently.** Approval status (Draft/In review/Approved/
   Confirmed/Finalized) tracks workflow; Purchase order status (Open order/Received/Invoiced/Canceled) tracks
   receipts and invoices. Reading one for the other misjudges what is committed vs what is received.
3. **A product receipt posts physical stock and an accrual, not AP.** It updates on-hand at an estimated cost
   and, if the posting profile accrues, debits a purchase-expenditure/un-invoiced and credits a product-receipt
   accrual account. The vendor liability is untouched until the invoice.
4. **The product-receipt accrual is the received-not-invoiced wall (the GR/IR analog).** Received value sits on
   the accrual account until the vendor invoice clears it. Posting receipts without invoicing lets accrued
   purchases pile up; that balance must be reconciled, not ignored. `references/invoice-matching.md`.
5. **Posting a vendor invoice is a voucher, not a draft.** It posts the AP liability + GL, clears the receipt
   accrual, settles inventory financial cost, and consumes a number. To undo it you post a credit note or
   reverse - there is no delete of a posted invoice.
6. **Cancelling or correcting a posted product receipt is a new corrective posting, not an undo.** It reverses
   the physical receipt and accrual, both documents stay in the trail, and it cannot restore a quantity already
   issued or consumed.
7. **A Closed ledger period is a wall.** A posting whose date lands in a Closed period is refused; an **On hold**
   period blocks postings for the affected module; a **Permanently closed** period can never reopen. Reopening a
   Closed period is a finance-close action, not a workaround. `references/ledger-periods-costing.md`.
8. **Period status is per module and the date picks the period.** On hold can block only some modules, and a
   voucher posts to the period of its transaction date, not today. Letting the date default while the current
   period is closed silently misposts to another open period.
9. **Inventory close settles cost across the whole period.** Close matches issues to receipts by the item's
   costing method and posts cost adjustments. Posting a back-dated transaction into a closed inventory period
   means cancelling the close and re-running it - a heavy, revaluing action, not a light correction.
10. **Physical cost is not final cost.** On-hand updates at product receipt with an estimated (running average
    or physical) cost; the financial cost settles at invoice and at inventory close. Reasoning about margin or
    valuation on the physical cost before settlement is wrong.
11. **The costing method changes what a posting does.** Under Standard cost, a receipt/invoice at an off-standard
    price posts a purchase price variance; under Weighted average / Moving average / FIFO the transaction moves
    the item's running value. A small-quantity receipt at an outlier price can shift the average.
12. **Negative inventory is a config switch on the item model group.** If physical/financial negative inventory
    is allowed, receipts/issues can drive on-hand negative and produce a wrong running cost until close; if not
    allowed, the issue posting is blocked outright.
13. **The matching policy decides which checks fire.** Two-way matches price and price totals; three-way adds
    product-receipt quantity. A three-way item invoiced before its product receipt is posted fails quantity
    matching and holds. `references/invoice-matching.md`.
14. **A matching discrepancy holds the invoice; overriding it bypasses the control.** Posting past a failed match
    needs the post-invoice-with-matching-discrepancies privilege. Loosening the tolerance or overriding does not
    resolve the price/quantity gap - it pays a mismatched bill.
15. **Change management is not red tape.** When active, a PO cannot be confirmed until workflow approves it.
    Deactivating change management, or editing then re-confirming to route around an approver, is a control bypass.
16. **Submitting to workflow locks the document.** Once submitted, edit it only by **Recall**. The approval
    hierarchy routes by amount and dimension; splitting a PR to stay under a limit is auditable and prohibited.
17. **Financial dimensions default silently.** The main account plus dimensions (Department, Cost center...)
    form the ledger account; a wrong default posts to the wrong cost center, and an advanced dimension-combination
    rule can block a posting that looks valid. `references/ledger-periods-costing.md`.
18. **Continuous number sequences serialize and can strand a number.** A continuous sequence (for invoices /
    vouchers that must not gap) reserves the next number at post; a failed post leaves a reserved number that
    needs number-sequence cleanup. Non-continuous allows gaps and avoids the bottleneck.
19. **The posting profile decides the accounts.** Vendor posting profile and inventory/item posting profiles map
    a receipt/invoice/inventory transaction to ledger accounts. A wrong or defaulted profile posts to the wrong
    accounts with no error.
20. **Reversing is a new voucher, dated in an open period.** A GL Reverse transaction (storno) or a vendor
    credit note posts a corrective voucher; you cannot delete a posted voucher, and the reversal date must fall
    in an open period. `references/ledger-periods-costing.md`.
21. **Subledger-to-GL transfer can lag.** Source documents post a subledger journal; if transfer to the general
    ledger is asynchronous or scheduled in batch, GL balances trail the subledger until the batch runs. Reading
    GL before transfer under-reports what is really posted.
22. **A WHS-enabled warehouse does not take a direct product receipt.** With "Use warehouse management processes"
    on, receiving flows through warehouse work (arrival journal / load / registration / put-away) via a mobile
    device, and the product receipt posts against completed work. Treating it like basic inventory skips the
    work and mis-states location and available stock.
23. **On-hand is not available.** Reserved (physical or ordered), marked, and quarantine/blocked-status inventory
    reduce available-physical; a batch on a blocking disposition status cannot be picked. Available-to-promise
    differs from on-hand quantity.
24. **Cancelling a PO line that has a posted receipt strands the accrual.** Cancel leaves the receipt, its
    accrual, and any invoice in place. Reverse or invoice the receipt first, then close the remaining quantity
    (deliver remainder); cancelling first leaves an open accrual and breaks matching.
25. **Standard cost is version-based.** A pending cost version does nothing until **activated**; activating it
    revalues on-hand at the new standard and posts a revaluation. Do not activate mid-period without expecting
    the revaluation posting.
26. **Charges match too.** Misc. charges on a PO/invoice post to their own accounts and, when charge matching is
    on, an invoice charge that does not match the PO charge holds the invoice like a price discrepancy.
27. **A return to vendor is a negative product receipt, not an edit.** Returning goods posts a negative receipt
    that reverses the physical stock and the accrual and drives a vendor credit; it has its own trail and cannot
    restore a consumed quantity. Reduce a vendor balance with a return/credit note, not by editing a posted receipt.
28. **Tax defaults silently and posts with the transaction.** The sales-tax group (from the vendor) and the
    item sales-tax group (from the item) intersect to compute tax; a wrong default posts incorrect tax to the
    ledger. Withholding tax computes at invoice/payment, can hold the invoice, and pays the vendor net of the
    withheld amount - a separate mechanism from matching holds.
29. **An intercompany PO commits in two legal entities at once.** Confirming it generates the mirror sales order
    in the other company; a receipt/invoice on one side drives the counterpart. Acting on one entity without the
    other creates cross-entity entries that are hard to unwind - treat the whole chain as committing.

(Deeper per-topic detail: `references/procurement-receiving.md`, `references/invoice-matching.md`,
`references/ledger-periods-costing.md`.)

## Edge states & special cases
Each breaks naive "quantity on hand at a price" or "one document, one entry" logic. Key rule inline; full
behavior in the reference noted.
- **WHS vs basic warehousing** - a WHS warehouse receives through work, not a direct product receipt; mixing the
  two mis-states location and on-hand. Detail in `references/procurement-receiving.md`.
- **Consignment inventory** - vendor-owned stock in your warehouse; ownership and the payable transfer only at
  an **inventory ownership change** (consumption), not at physical receipt. Counting it as owned overstates value.
- **Batch / serial (tracking dimensions)** - a tracked item cannot transact without its batch/serial; a batch on
  a blocking disposition status or past shelf-life is not usable; a wrong batch mis-assigns quality/expiry.
- **Standard cost versions** - pending vs active; activation revalues on-hand. Detail in `references/ledger-periods-costing.md`.
- **Negative inventory** - allowed only if the item model group permits it; otherwise issues block. Estimated
  cost on negative on-hand is unreliable until close.
- **Multiple legal entities / intercompany** - data is partitioned by legal entity (company). Confirming an
  **intercompany PO** generates the **mirror sales order** in the other entity (itself a committing action), and
  centralized payments settle across entities. Querying or posting in the wrong entity shows nothing or posts to
  the wrong books; an intercompany chain commits in two companies at once.
- **Budget control / encumbrance** (if enabled) - a PR/PO reserves budget via a funds check; an over-budget
  document is blocked or flagged, and **overriding the failure** to post anyway is a committing control bypass.
  Acting without a successful check silently fails.

## Recovery patterns (can it be undone, and what can't)
- **Cancel / correct a product receipt** - a new corrective posting; permanent in the trail; cannot restore a
  quantity already issued/consumed; re-values the accrual.
- **Reverse a vendor invoice** - a **credit note** or cancellation posts reversing distributions, only in an open
  period; a fully settled (paid) invoice needs the settlement reversed or a credit note, not a delete.
- **Reverse a posted GL voucher** - a **Reverse transaction (storno)** posts a new reversing voucher dated in an
  open period; both entries stay in the trail. You cannot un-post.
- **Inventory close** - reversible only by **cancelling the close** and re-running; it recomputes cost across the
  period. Correct a single wrong cost with a cost adjustment, not by cancelling close, when possible.
- **Ledger settlement** - reverse the settlement (un-settle) if it is not in a closed period; otherwise correct
  in the current open period.
- **Period reopen** - owned by the finance close; a **Permanently closed** period never reopens. Correct in the
  current open period instead.
- **Wrong running/standard cost** - corrected by a cost adjustment or a new activated cost version (itself a
  committing revaluation), not an undo.
- **Return to vendor** - a negative product receipt (its own posting) reverses stock and accrual and yields a
  credit; a permanent trail, not an undo, and it cannot restore a consumed quantity.
- **Partial posting failure** - a posting can fail mid-way (receipt posts but the accrual/transfer fails, or a
  continuous number is reserved but the voucher aborts), leaving orphaned transactions and a stranded number.
  Before retrying: (1) check whether the subledger transaction exists, (2) check whether the voucher posted
  (voucher transactions), (3) check the continuous number sequence for a stranded number and run cleanup, then
  (4) retry only the part that failed. Do not blindly re-run, which double-posts the part that succeeded.
- **Reversal timing trap** - the original posting landed in an open period, but by the time a reversal is needed
  that period may be Closed or On hold. A reversing voucher / credit note posts in the **current** open period
  (dated there, referencing the original), not back into the closed one; a genuinely back-dated correction is a
  finance-close decision (period reopen), not an agent action.

## Guardrails
- Read the PO approval status + PO status + product-receipt and accrual state + matching status + period status +
  inventory-close status before acting; re-read at execute, because periods close and matching holds appear
  underneath you. Before a posting, also verify the **posting profile** and the item's **costing method** (they
  decide which accounts and what cost the voucher writes) and that the **sales-tax / item-sales-tax group**
  default correctly (wrong tax posts with the voucher and is not separately reversible).
- If a posting was submitted to **batch** (subledger-to-GL transfer, inventory close, mass invoice/receipt),
  check the batch job status before retrying. A successful batch post is a committed voucher; retrying
  double-posts. Verify with voucher transactions, do not assume failure from a missing immediate result.
- Never post into a Closed or On-hold period; never turn off change management or a matching policy, override a
  matching discrepancy, a budget check, or loosen a tolerance to force a posting; never split a PR/PO to drop
  under an approval limit. Editing an already-confirmed PO is not a benign edit: it re-triggers approval and a
  new confirmation version (a committing action). If a closed month needs a correction, it is a finance-close
  decision made in the current open period.
- Treat Confirm, product receipt, vendor invoice, journal post, inventory adjustment, subledger-to-GL transfer,
  and cost-version activation as committing vouchers. A preview/simulation is the safe read.
- For anything in the destructive row (cancel/correct a receipt, reverse an invoice or voucher, run/cancel an
  inventory close, activate a cost version, reopen a period, override a match): named approver, re-read, and log
  the reason. It revalues, liquidates, or moves money - it is not a correction.

## References (load on demand)
- `references/procurement-receiving.md` - load when the task touches requisitions, POs, confirmation, change
  management, product receipts, WHS inbound work, or closing remaining PO quantity. PR/PO lifecycle and the two
  status axes, workflow + change management, PO confirmation and versions, product receipt posting and its
  accrual, WHS receiving (work/load/registration), deliver remainder / cancel / finalize, charges.
- `references/invoice-matching.md` - load when posting or troubleshooting a vendor invoice. Invoice paths
  (pending vendor invoice, invoice register/approval, from PO), matching policies (two-/three-way, price / price
  totals / quantity / charges), tolerances and matching status, posting with discrepancies, accrual clearing,
  credit note / cancel.
- `references/ledger-periods-costing.md` - load when the task touches the ledger, periods, dimensions, number
  sequences, or inventory cost. Subledger-to-GL vouchers and transfer modes, GL journals and reversal, fiscal /
  ledger calendar period status and module access, inventory close and adjustment, costing methods and item
  model group, standard cost versions, financial dimensions and combinations, number sequences.
