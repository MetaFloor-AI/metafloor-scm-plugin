---
name: netsuite
description: "Oracle NetSuite - safe operation of the mid-market cloud ERP: records and posting vs non-posting transactions (sales order, purchase order, item receipt, item fulfillment, vendor bill, invoice, journal entry, intercompany JE), SuiteFlow approval routing, accounting periods (open, locked, closed) and the period-close checklist, OneWorld subsidiaries and intercompany elimination, inventory costing and lot/serial, and saved searches vs mass-update and inline edits. Use when the connected ERP is NetSuite and the work approves or transmits a PO, receives or bills it, fulfills or invoices an SO, posts a journal, edits or voids or deletes a posted transaction, hits a locked or closed period, touches received-not-billed or three-way match, or runs a saved search, CSV import, or mass update. Not for Oracle Fusion or EBS (oracle-erp) or SAP (sap-mm, sap-fi)."
---

# NetSuite - operating it safely

NetSuite runs finance, inventory, and order management as the system of record for a mid-market business,
often across many legal entities (OneWorld). The thing that makes NetSuite dangerous is specific to it:
**writes fall into two very different buckets, and the platform lets you do things other ERPs forbid.** A
sales order and a purchase order post nothing to the ledger, so they feel safe - yet approving a PO
transmits a real commitment to a vendor. Meanwhile a posted invoice, bill, or journal can be opened and
edited in place, or deleted outright, restating or erasing the general ledger with only a System Note as
evidence. This skill gives the judgment to classify NetSuite actions so the harness can gate them, plus
the period, subsidiary, and costing edge states that decide whether a mistake is fixable.

## Contents
- When this applies / when NOT
- Object & state model
- Vocabulary that bites
- Operations: read / write / destructive
- Gotchas that bite
- Edge states & special cases
- Recovery patterns
- Guardrails
- References

## When this applies / when NOT
Connector is NetSuite and the work touches its records, transactions, periods, subsidiaries, or inventory.
When NOT:
- The ERP is Oracle Fusion Cloud ERP or E-Business Suite (EBS), not NetSuite -> `oracle-erp`.
- The ERP is SAP: materials/inventory/procurement -> `sap-mm`; ledger, period close from the
  finance side, account determination -> `sap-fi`.
- Physical warehouse execution (waves, tasks, advanced bin/WMS mechanics) beyond the item receipt /
  fulfillment record that posts inventory -> the WMS skill for the connected warehouse system.

## Object & state model (reason about state, not nouns)
NetSuite's core split is **posting vs non-posting** transactions. Non-posting records commit or promise but
touch no GL; posting records move the ledger. Reason about which bucket you are in first.
- **Item** - inventory / non-inventory / assembly (BOM) / kit / service, optionally lot- or serial-numbered.
  Carries a **costing method** (Average / FIFO / LIFO / Standard) that is frozen once transactions exist.
- **Sales Order (SO)** - *non-posting* commitment to a customer. States: Pending Approval -> Pending
  Fulfillment -> Partially Fulfilled -> Pending Billing -> Billed -> Closed. No GL until fulfillment/invoice.
- **Purchase Order (PO)** - *non-posting* commitment to a vendor. States: Pending Approval -> Pending
  Receipt -> Partially Received -> Pending Billing -> Fully Billed -> Closed. Approval + transmit makes it contractual.
- **Item Receipt** - *posting*: debits Inventory Asset, credits Accrued Purchases (Received Not Billed). The physical-receipt leg of procure-to-pay.
- **Item Fulfillment** - *posting*: cuts stock and, with the default "Post COGS on Shipment" preference, debits COGS and credits Inventory Asset. If that preference is set to post COGS at billing, fulfillment only reduces inventory and COGS posts on the invoice. The inventory leg of order-to-cash.
- **Vendor Bill** - *posting*: debits Accrued Purchases / expense, credits Accounts Payable. Clears the receipt accrual.
- **Invoice** - *posting*: debits Accounts Receivable, credits Revenue. The AR/revenue leg of order-to-cash.
- **Journal Entry** - posts directly to the GL. An **Intercompany JE** posts across two subsidiaries at once.
- **Accounting Period** - states: Open / Locked (A/R, A/P, Payroll, or All can each be locked) / Closed. A
  posting whose date lands in a locked (for that subledger) or closed period is refused. See `references/periods-and-close.md`.
- **Subsidiary (OneWorld)** - the legal-entity dimension on every transaction, with its own base currency;
  consolidation and intercompany elimination roll up the subsidiary hierarchy. Fixed at creation.

## Vocabulary that bites
- **Posting vs non-posting transaction** - the single most important NetSuite distinction. SO, PO, quote,
  and opportunity are non-posting (no GL); item receipt, fulfillment, invoice, bill, and journal post. "The order booked revenue" is false - the invoice did.
- **Item Receipt vs Vendor Bill** - two separate records and posts in P2P. The receipt books the asset plus
  the accrual; the bill books AP and clears the accrual. Billing without receiving (or the reverse) breaks the three-way match.
- **Item Fulfillment vs Invoice** - two separate records and posts in O2C. Fulfillment books COGS and cuts
  stock; the invoice books AR and revenue. A fulfilled-but-uninvoiced order has already moved COGS.
- **Received Not Billed (Accrued Purchases)** - the clearing account a receipt credits and a bill debits;
  NetSuite's GR/IR analog. A quantity or price mismatch leaves it open as a standing accrual.
- **Void vs Delete** - void keeps the record and, with the reversing-journal preference on, posts an
  offsetting entry; delete removes the transaction and its GL lines entirely, leaving only a System Note. Delete is the high-blast path.
- **Locked vs Closed period** - a locked period blocks one subledger (A/R, A/P, or Payroll) or "All"; a
  closed period blocks all posting. **Allow Non-G/L Changes** frees only non-financial fields on a closed-period record, never amounts.
- **SuiteFlow / approval routing** - NetSuite's workflow engine plus the native "Require Approvals"
  preferences and employee purchase/approval limits. It sets records to Pending Approval, routes by amount, and can lock fields. Pending Approval is not yet effective.
- **Saved Search vs Mass Update vs Inline Edit** - a saved search reads; a Mass Update, or inline editing a
  list, writes to every matching record at once. Same list view, opposite blast radius.
- **Costing method** - Average / FIFO / LIFO / Standard, set on the item and frozen once transactions exist.
  "The cost" depends on the method and cannot be re-chosen (see `references/oneworld-costing-inventory.md`).
- **Subsidiary (OneWorld)** - the legal-entity dimension; fixed at creation, drives base currency,
  intercompany, and elimination. A wrong subsidiary is not an editable field after the transaction posts.
- **Intercompany JE / elimination** - a journal posting in two subsidiaries; the period-close elimination
  subsidiary nets intercompany balances out of the consolidated view.
- **System Notes** - the field-level audit trail. Often the only evidence left after a delete or an in-place edit of a posted transaction.

## Operations: read / write / destructive
Classify every operation family by what it does to the ledger, to a commitment, and to state. Kinds of
action, not tool names.

| Class | NetSuite operation families | Gate | Why |
|---|---|---|---|
| **Read** | view any record/transaction (SO/PO/receipt/fulfillment/bill/invoice/journal/item/subsidiary); run a saved search or report; check period status, approval status, on-hand, or accrual balances; export search results; read System Notes | always pass | no state change; read before every write and re-read at execute |
| **Write (reversible)** | create/edit an SO or PO **before approval** (non-posting); save a draft or Pending Approval transaction; edit a non-GL field (memo, custom field) on an open-period record; create a quote/estimate | gate one at a time | uncommitted, non-posting, or non-financial; low blast, cleanly undone |
| **Write (committing)** | approve + transmit a PO (vendor commitment); edit an approved/transmitted PO or SO (changes a live commitment); create/post an item receipt (asset + accrual); post a vendor bill (AP, clears accrual); fulfill an SO (COGS + inventory); post an invoice (AR + revenue); post a journal or intercompany JE; apply a customer/vendor payment; post an inventory adjustment/transfer/count; build/unbuild an assembly; edit a posted transaction (re-posts the GL in place); inline-edit, Mass Update, or a CSV import in **update** mode on a posting field; **void** with the reversing-journal preference **on** (posts an audit-safe reversing JE in the current period) | gate + human approve | posts to the GL, binds money, moves stock, or re-states a period; each is a ledger event |
| **Destructive / irreversible** | delete any posted transaction (removes GL lines, System Note only); **void** with the reversing-journal preference **off** (reverses inside the original period); CSV import in **delete** mode; Mass Delete; lock or close an accounting period; reopen a closed period; override/skip a SuiteFlow approval | hard gate + named approver + re-read | erases or restates the ledger, bypasses a control, or crosses a period / legal-entity wall that cannot be cleanly undone |

The committing/destructive rows name the families that bite; `references/transactions-and-gl.md` has the
full posting-transaction list (payments, cash sales, customer deposits, assembly builds, counts).

**Hard stops (the platform refuses these - there is no named-approver override):** changing an item's
**costing method** once transactions exist, and changing a posted transaction's **subsidiary** in OneWorld.
Do not attempt them; the fix is a new item, or a void-and-re-enter. Splitting or lowering a PO to slip under
an approval limit is not an operation at all - see Prohibited circumvention below.

**Reclassification (read this):**
- **Creating a posting transaction from scratch is committing**, exactly like the families above - a new
  invoice, bill, receipt, fulfillment, or journal posts to the GL on save, not only edits of existing ones.
- **An in-place edit of a posted transaction is committing, and destructive if it restates a reported
  period.** NetSuite lets you open a posted bill, invoice, or journal and change amounts; saving re-posts
  the GL with no reversing document. A save whose date lands in a closed/locked period is blocked; a save that restates an already-reported open period should be treated as destructive.
- **Void is preference-dependent.** With "Void Transactions Using Reversing Journals" **on**, a void posts an
  offsetting entry in the current open period - committing and audit-safe. With it **off**, the void reverses inside the original period, restating a possibly-reported month - destructive. Check the preference before calling a void safe.
- **Non-posting is not the same as safe.** Approving or transmitting an SO or PO posts nothing, yet commits
  to a customer or vendor. Classify by commitment, not only by GL impact.
- **A bulk tool inherits the class of the field it writes.** A saved search is read; the same search driving
  a Mass Update or an inline edit on a posting field, or a CSV import in **add/create** mode (bulk-creates posting records) or **update** mode, is committing; a CSV import in **delete** mode or a Mass Delete is destructive.

**Prohibited circumvention (patterns to block, not operations to perform):** splitting or lowering a PO to
drop under an employee purchase / approval limit; back-dating a transaction into an open period to dodge a
closed one; renumbering to slip past duplicate detection; deleting a posted transaction to "clean up"
instead of voiding or issuing an offsetting credit. If a request amounts to one of these, stop and route to the real approver.

Universal rules to teach: read before every write and **re-read at execute** (period status, approval
state, on-hand, and accrual all drift); never post into a locked/closed period or reopen one to force a
posting through; never bypass SuiteFlow approval or split under a limit; a lock, a hold, or Pending Approval
means **stop**; prefer void or an offsetting credit/journal over delete so the audit trail survives.

## Gotchas that bite (the real set, as causal chains)
1. **Posting vs non-posting is the whole game.** A sales order and a purchase order hit no GL account. The
   books move at item receipt, item fulfillment, invoice, and vendor bill. Reasoning that "the SO changed the ledger" is wrong; the fulfillment/invoice did.
2. **Deleting a posted transaction erases its GL lines.** NetSuite lets you delete an invoice, bill, or
   journal outright; the ledger balance changes with only a System Note as evidence. High blast - prefer void or an offsetting credit.
3. **Void behavior depends on a hidden preference.** "Void Transactions Using Reversing Journals": on -> a
   void posts a reversing journal in the current open period (audit-safe); off -> the void reverses inside the original period, silently restating a possibly-reported month.
4. **Editing a posted transaction re-posts the GL in place.** Unlike ERPs that force a reversal, NetSuite
   lets you open a posted bill or invoice and change amounts; saving re-posts the ledger and restates the period with no reversing document.
5. **Changing a transaction's date can move it into another period.** Editing the date re-posts to the new
   period; if it is open, you have silently shifted the month. If the target period is closed or locked the save is blocked - do not reopen it; void/offset in the original period and re-enter in the correct open one.
6. **A closed period is a wall; a locked period is a selective wall.** Locking A/P blocks bills, vendor
   credits, and vendor payments; locking A/R blocks invoices and customer payments; "Lock All" blocks nearly everything; "Closed" blocks all posting. Do not reopen to force a posting.
7. **"Allow Non-G/L Changes" only unlocks non-financial fields.** With it on you can edit a memo or custom
   field on a closed-period transaction, but not amounts or accounts. Do not read a successful save as "the period accepted a financial change."
8. **Item receipt posts before the bill.** Receiving debits Inventory Asset and credits Accrued Purchases /
   Received Not Billed; the vendor bill later clears that accrual. A quantity or price gap leaves a standing accrual or a bill variance, not a clean match.
9. **Fulfilling an SO cuts inventory and (by default) books COGS before any invoice.** With "Post COGS on
   Shipment" on (the default), fulfillment is the inventory/COGS event and the invoice is the AR/revenue event; a fulfilled-but-uninvoiced order has already moved COGS out of stock. If COGS is set to post at billing, it waits for the invoice - so know the preference before reading margin.
10. **Negative inventory posts at an estimate.** NetSuite lets quantity go below zero; it books COGS at the
    last/average cost, then when a receipt lands it creates cost-adjustment postings to true up. That period's COGS was an estimate, not actual.
11. **Costing method is set once and frozen.** Average / FIFO / LIFO / Standard is chosen on the item and
    cannot change once transactions exist. The wrong choice is permanent, corrected only by creating a new item.
12. **Approving a PO is the commitment, and transmitting sends it to the vendor.** A PO in Pending Approval
    is not an order; approval plus email/EDI transmit makes it contractual even though it stays non-posting.
13. **A saved search is read-only, but inline edit and Mass Update are not.** Turning on inline editing in a
    list, or running a Mass Update built on a search, writes directly to every matching record with no approval - a bulk write that is hard to reverse.
14. **CSV import can create, update, or delete in bulk.** An import in "update" mode overwrites fields on
    matched records and in "delete" mode removes them; a wrong mapping or key restates or erases hundreds of records at once.
15. **Intercompany transactions must net to zero across subsidiaries.** An intercompany JE posts in two
    subsidiaries; if the legs do not balance and eliminate, consolidated statements are wrong until the period-close elimination runs.
16. **You generally cannot change a transaction's subsidiary after it posts.** Subsidiary is fixed at
    creation in OneWorld; a wrong subsidiary means void/delete and re-enter, not an edit.
17. **Foreign-currency balances need revaluation at close.** A transaction posts at its transaction-date
    rate; open FX balances are revalued and consolidated exchange rates applied during the period-close checklist. Skipping it misstates consolidated results.
18. **Closing a PO line is not deleting it.** "Close" on a PO line stops further receipt and billing while
    keeping the record and trail; delete removes it. Use close to stop activity, not delete.
19. **A three-way match break parks the bill, it does not fix it.** A PO vs item receipt vs vendor bill
    mismatch (quantity or price) creates a variance/exception; paying it authorizes the mismatch. Fix the receipt or price, do not override to move on.
20. **Auto-reversing journals reverse next period, not now.** Flagging a journal to auto-reverse posts the
    reversal in the following period; a same-period correction needs a manual offsetting entry, not the auto-reverse flag.
21. **Period-close checklist steps are gated and ordered.** You cannot Close a period with unbalanced
    intercompany, unresolved negative inventory, or incomplete inventory costing; the checklist blocks the final Close step until each prior step is done.
22. **Deleting an item fulfillment or receipt cascades.** Removing it reverses COGS/inventory or the
    accrual, but if a downstream invoice or bill already references it, the delete is blocked or orphans the dependent document.
23. **An assembly build consumes components and posts.** A work-order completion / assembly build issues the
    component stock and receives the finished good - a posting inventory event; unbuild reverses it. Treating a build as a planning step misses the COGS/inventory move.
24. **A committed inventory count or revaluation posts an adjustment.** Approving a physical count or an
    inventory revaluation writes an adjustment to Inventory Asset and a gain/loss account. It is a posting correction, not a data refresh.
25. **Approving a PO may auto-transmit it to the vendor.** Depending on the email/EDI and SuiteFlow
    configuration, approval can send the order the same second - turning an "internal" approval into an irrevocable vendor commitment. Check the transmit setup before treating approval as internal-only.
26. **A customer deposit is a liability, not revenue.** Cash received as a customer deposit posts to a
    deposit liability; revenue recognizes only when the deposit is applied to an invoice. Reading a deposit as booked revenue overstates the top line.
27. **An invoice under Advanced Revenue Management posts AR now but defers revenue.** With rev-rec on, the
    invoice books Accounts Receivable immediately while revenue spreads across a recognition schedule; reading AR as earned revenue for the period is wrong.
28. **A save can fire SuiteScript / SuiteFlow triggers that cascade.** beforeSubmit/afterSubmit user-event
    scripts and workflow actions can create dependent transactions, email a vendor or customer, or block the save - so a committing write may reach beyond the target record. Re-read after saving to catch side effects you did not classify.
29. **Your role scopes and gates everything.** A restricted integration role may have an operation silently
    refused, may not see a subsidiary or record, or may lack the approval permission SuiteFlow expects. Treat a permission refusal as a hard stop to diagnose, not an error to retry.

## Edge states & special cases
Each breaks naive "quantity on hand at a cost" or "posted means settled" logic. Deep mechanics in
`references/oneworld-costing-inventory.md` and `references/periods-and-close.md`.

| Edge state | Naive assumption | Actual behavior | Correct action |
|---|---|---|---|
| **Negative inventory** | cannot go below zero | NetSuite posts COGS at an estimated cost, then trues up when a receipt lands | do not trust COGS/margin on a negative-on-hand item until the receipt posts |
| **Partial receipt / partial bill** | PO fully open or fully done | remaining quantity is open; the accrual reflects only what is received; a later receipt changes what the bill matches | re-read the receipt/accrual before billing a partial PO |
| **Multi-location inventory** | one on-hand number | quantity is per location/bin; total on-hand is not all available at one site | net on the location-level Available quantity, not company-wide On Hand, before promising stock |
| **Lot / serial item** | fungible quantity | each move must name the lot/serial number; a move without it fails or misassigns | supply the lot/serial on every fulfillment and adjustment |
| **Intercompany transaction** | a normal posting | posts in two subsidiaries and must eliminate at close | confirm both legs balance and elimination is configured |
| **Foreign-currency transaction** | face value is the number | posts at the transaction-date rate; consolidated and revalued at close | check the applied rate before treating a variance as an error |
| **Closed-period record + Allow Non-G/L Changes** | the period accepted an edit | only non-financial fields changed; amounts stayed | do not infer the GL was editable from a successful save |
| **Standard-cost item** | value is actual cost | value is standard; the PO/bill gap posts to a purchase price variance | read the variance account, not the item value, for the real cost |

## Recovery patterns (can it be undone, and what cannot)

| Action | Undoable? | How / what cannot be restored |
|---|---|---|
| **Non-posting SO/PO edit (pre-approval)** | yes | edit or delete cleanly; there is no GL to unwind |
| **Approved / transmitted PO** | no clean undo | Close the PO or cancel it; the vendor was notified, receipts/bills may exist, the trail stays |
| **Posted item receipt** | via delete/reverse, with cascade | deleting reverses the asset + accrual, but a downstream bill referencing it blocks the delete |
| **Posted vendor bill / invoice** | offset, not undo | if a payment is linked, unapply it first (itself a committing action), then void (preference-dependent) or issue a vendor credit / credit memo; delete removes the GL lines and destroys the trail |
| **Posted journal** | offset | a reversing / offsetting journal dated in an open period (a flagged auto-reverse posts *next* period, not now); delete erases it (System Note only) |
| **Deleted transaction** | no | gone from the ledger, only System Notes remain; re-creating it will not match the original date or document number |
| **Closed period** | admin reopen only | reopening re-exposes the month; corrections belong in the current open period, not a reopen |
| **Costing method** | no | frozen once transactions exist; only fixable via a new item |

## Guardrails
- Read the transaction and its posting status, period lock, approval state, subsidiary, and on-hand before acting; re-read at execute, since state drifts.
- Never post into a locked or closed period, and never reopen one to force a posting through; a correction for a closed month goes in the current open period.
- Prefer void or an offsetting credit/journal over delete. Delete removes the GL lines and leaves only a System Note - it destroys the audit trail.
- Never bypass SuiteFlow or native approval, and never split or lower a PO under an employee purchase limit. Pending Approval means not yet effective.
- Treat every item receipt, fulfillment, bill, invoice, and journal as a ledger event, and every in-place edit of a posted transaction as a re-post that restates the period.
- Confirm the account/environment (production vs sandbox) and your role's permissions before any committing or destructive action - a write to the wrong account is its own incident class, and a permission refusal is a hard stop to diagnose, not an error to retry.
- For anything in the destructive row: named approver, re-read of live state, and a logged reason. In OneWorld, confirm the subsidiary before posting - it cannot be changed after.

## References (load on demand)
- `references/transactions-and-gl.md` - the posting vs non-posting map, the GL each transaction type posts,
  the procure-to-pay and order-to-cash flows, and Received Not Billed / three-way match with variances.
- `references/periods-and-close.md` - period states (open / A-R, A-P, Payroll, All lock / closed), the
  period-close checklist steps in order, Allow Non-G/L Changes, and void vs delete vs reversing-journal mechanics.
- `references/oneworld-costing-inventory.md` - OneWorld subsidiaries, base and consolidated currency and
  intercompany elimination, costing methods and the negative-inventory true-up, and locations, bins, lot and serial.
