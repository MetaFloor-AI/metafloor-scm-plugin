---
name: infor
description: "Infor ERP - safe operation of the CloudSuite family and its product lines M3 (process/distribution), LN (ex-Baan, discrete/project), and SyteLine / CloudSuite Industrial (CSI): purchase orders and receiving, AP supplier invoices and three-way matching, general ledger, inventory, valuation and costing, ION approvals, and accounting periods. The lines name objects and address screens differently (M3 programs like PPS200/MMS060, LN sessions like tdpur/tfacp/whinh, SyteLine named forms) but share the same posting, period, and approval invariants. Use when the connected ERP is Infor and the work touches a purchase order, goods receipt, supplier invoice or voucher, a three-way match or hold, an integration transaction, a journal or GL posting, an open or closed period, item cost, an ION workflow, or mentions Infor M3, LN, Baan, SyteLine, CloudSuite, Infor OS, or a BOD. Not for SAP (sap-mm/sap-fi), Oracle (oracle-erp), or Infor EAM (infor-eam)."
---

# Infor ERP - operating it safely

Infor is not one ERP - it is a **family**. The CloudSuite editions are packaged, multi-tenant deployments
built on one of three distinct product lines: **M3** (process and distribution - food, fashion, chemicals,
wholesale), **LN** (the ex-Baan engine - discrete and project manufacturing, aerospace, industrial), and
**SyteLine / CloudSuite Industrial (CSI)** (mid-market discrete manufacturing). They share the posting,
period, and approval invariants of any real ERP - a goods receipt or supplier invoice hits inventory and the
general ledger, a closed period is a wall, an approval enforces authority - but they name the objects
differently and address their screens differently. The danger is twofold: each write is an audited financial
event, **and** acting with the wrong product line's assumptions targets the wrong screen or field. This skill
gives the judgment to identify the line, classify each action so the harness can gate it, and know which
mistakes are fixable.

## Contents
- When this applies
- Identify the product line first
- Object & state model
- Vocabulary that bites
- Operations: read / write / destructive
- Gotchas that bite
- Edge states & special cases
- Reconciliation & freshness
- Recovery patterns
- Guardrails
- References

## When this applies
Connector is Infor ERP and the work is procurement, receiving, payables, GL, or inventory in M3, LN, or
SyteLine/CSI (including the CloudSuite editions built on them). When NOT:
- SAP materials/inventory/procurement -> `sap-mm`; SAP ledger/finance -> `sap-fi`.
- Oracle Fusion / EBS -> `oracle-erp`; Coupa -> `coupa`.
- **Infor EAM** (enterprise asset management / maintenance) -> `infor-eam`. Different product,
  work orders and assets, not P2P/GL - do not extrapolate this skill's postings onto it.
- Deep warehouse execution in a standalone **Infor WMS** (ex-HighJump) -> its own WMS skill. M3/LN's own
  inventory and receiving stay in scope here.
- **Out of scope here:** sales orders / customer invoicing / AR, and manufacturing execution (work orders,
  shop floor). They share the period and posting mechanics but have their own objects and rules - do not
  extrapolate this skill's P2P, receiving, and GL patterns onto them.

## Identify the product line first (this is step zero, and it is not optional)
The same task uses different objects and addressing depending on the line. Establish which one before acting:

| Line | Industry fit | How screens are addressed | AP invoice object | Stock model |
|---|---|---|---|---|
| **M3** (ex-Movex) | process, distribution, F&B, fashion | **program codes** - PPS (purchasing), MMS (item/stock), OIS (sales), APS (payables), GLS (GL), CRS (common) | Supplier invoice (APS100), matched in APS360 | balance identity (warehouse / location / lot / status) |
| **LN** (ex-Baan) | discrete, project, A&D, industrial | **session codes** `td`/`tf`/`wh…` - tdpur (purchase), whinh (warehouse inbound), tfacp (AP), tfgld (GL) | Purchase invoice (tfacp), matched to receipt | warehouse inventory + **integration transactions** to finance |
| **SyteLine / CSI** | mid-market discrete mfg | **named forms** + IDOs (Mongoose) - "Purchase Orders", "PO Receiving", "Voucher Builder", "A/P Vouchers", "Journal Entries" | **Voucher** (built + matched, then posted) | on-hand by item/warehouse/location; Unposted -> Posted |

A **CloudSuite** name (e.g. CloudSuite Distribution, CloudSuite Aerospace & Defense, CloudSuite Industrial)
tells you the industry edition, not the mechanics - look under it for M3, LN, or SyteLine and apply that
line's object model. **If you cannot determine the line, stop and ask - do not guess:** acting on the wrong
line targets the wrong screen and field (gotcha 1). Deep per-line object/screen map: `references/product-lines.md`.

## Object & state model (reason about state, not nouns)
Names differ by line; the states and transitions are common. See `references/product-lines.md` for the
per-line object names.
- **Purchase Order** - the commitment to the supplier. States: entered -> **approved** (routes ION workflow
  or native approval above a threshold) -> issued/sent -> (partially) received -> (partially) invoiced ->
  closed. Not a real obligation until approved and issued.
- **Goods receipt** - receiving against a PO creates an inventory transaction that increases stock **and**
  drives a GL posting (via M3 accounting rules, LN integration transactions, or a SyteLine posted
  transaction). In LN and SyteLine the finance side is decoupled and lands only after posting/processing.
- **Supplier invoice / voucher** - the AP liability. Recorded, then **matched** three-way to the PO and
  receipt; a variance beyond tolerance raises a **matching hold** that blocks payment until cleared. In
  SyteLine the object is a **voucher** (built from the receipt), which is then posted.
- **Inventory balance** - stock is not one number: it carries a warehouse/location, a **status** (available,
  quality/inspection, blocked), lot/serial, and allocations. On hand is not available.
- **GL journal / voucher** - the ledger entry. Unposted (editable) -> **Posted** (balances updated) ->
  corrected only by a new reversing entry, never un-posted.
- **Accounting period** - per finance calendar, with a status. LN keeps **separate fiscal, tax, and
  reporting period statuses**, each opened/closed independently, plus a terminal **Finally Closed**. Posting
  lands only in an open period.

## Vocabulary that bites
- **CloudSuite** - the packaged, usually multi-tenant cloud edition. Multi-tenant means you cannot modify
  core code; changes go through the **extensibility framework** (extensions, ION scripts, Mongoose for CSI),
  and the upgrade cadence is vendor-controlled. A "just patch it" assumption is wrong on CloudSuite.
- **Infor OS / ION** - the integration and workflow fabric across the family. **ION Workflow** runs
  approvals, monitors, and alerts, so a PO or invoice approval state can live **outside** the ERP screen you
  are looking at. **ION** also moves data between apps asynchronously.
- **BOD** (Business Object Document) - the canonical XML message Infor apps exchange over ION (e.g.
  SyncPurchaseOrder, ProcessReceiveDelivery). A change in one app propagates by BOD, so a replicated copy or
  the Data Lake can **lag** the source-of-record app.
- **Integration transactions / mapping scheme** (LN) - LN keeps logistics and finance **decoupled**: a
  warehouse or purchase transaction creates a logistic record, and the GL entry exists only once integration
  transactions are **mapped and posted**. Until then, logistics and finance disagree.
- **Accounting rules** (M3) - the configuration that derives which GL accounts a logistics event posts to. A
  mis-set rule posts to the wrong account silently; the error shows in the GL, not on the logistics screen.
- **Voucher** (SyteLine) - the AP invoice concept; built from receipts (Voucher Builder), matched, then
  posted. An **unvouchered receipt** sits as an accrued liability until a voucher is built.
- **Balance identity** (M3) - the key under which stock is tracked (warehouse, location, lot, container,
  status). "Stock on hand" is per balance identity, not a single company figure.
- **Valuation method** - per item: **standard cost** (off-price posts a purchase price variance), **average
  / MAUC** (LN moving-average, a receipt moves the average), **FTP** (LN Fixed Transfer Price), or
  FIFO/LIFO/Lot. Same receipt, different accounting.
- **Matching hold / tolerance** - the block a three-way match sets when price or quantity varies beyond the
  configured tolerance. Loosening the tolerance or releasing the hold bypasses the control, it does not
  resolve the mismatch.
- **Finally Closed** (LN period) - a terminal period status that cannot reopen, distinct from a soft Close.
- **Update method (M3)** - M3 derives GL postings from accounting rules, but whether they hit the ledger
  **immediately (interactive) or only when a batch update job runs** depends on configuration. In batch mode
  the GL lags the logistics event - a receipt is not necessarily "in the books" the instant it is recorded.

## Operations: read / write / destructive
Classify every operation family by what it does to state. No tool/op names - kinds of action. Examples name
the line where they differ.

| Class | Infor operation families | Gate | Why |
|---|---|---|---|
| **Read** | display/query a PO, receipt, supplier invoice/voucher, journal, supplier, item; stock/balance inquiry (M3 MMS060, LN inventory, SyteLine on-hand); item cost / valuation inquiry; GL balance, trial balance, aging; period status; matching-hold detail; approval/workflow status in ION; integration-transaction status (LN) | always pass | no state change; read before every write, re-read at execute |
| **Write (reversible)** | create/edit a PO before approval; enter a requisition; delete an unapproved PO/requisition or cancel a PO line that has no receipts; record a supplier invoice before matching/posting; build an **Unposted** journal (SyteLine) or an unposted M3 voucher; stage a voucher before posting; a payment proposal / selection before it is confirmed (a deletable draft) - all still editable/deletable and not yet committed | gate one at a time | still a request/draft; no supplier or ledger commitment yet |
| **Write (committing)** | approve a PO (routes ION/native approval, becomes an obligation); issue/send a PO; **post a goods receipt** (stock + GL via accounting rules / integration / posting); **match** a supplier invoice/voucher three-way; **post** a journal or voucher (updates GL); **process/post LN integration transactions** to GL (intercompany flows post them in two companies - double the failure surface); an inventory transfer that changes stock **status** (available <-> quality/blocked); a **confirmed** AP payment run (cash out, writes the payment file + bank reconciliation) | gate + human approve | binds money, moves stock, or writes the ledger; each is an audited posting |
| **Destructive / irreversible** | reverse/cancel a posted goods receipt; return to supplier; cancel a PO or line that has receipts/invoices; reverse or void a posted supplier invoice/voucher; **void/reverse an AP payment**; reverse a posted GL journal; scrap/write-off stock; reopen a **closed period** to force a posting (the post into a closed period is otherwise refused; a **Finally Closed** LN period cannot reopen at all); release a matching hold or loosen a tolerance without fixing the cause; standard-cost/valuation revaluation; physical-inventory or cycle-count adjustment | hard gate + named approver + re-read | permanent trail; re-values or frees stock; disburses or claws back cash; crosses a period/compliance boundary |

**Reclassification rule:** editing an *already-approved* PO above the approval or matching tolerance is not a
benign edit - it re-triggers the ION/native approval and becomes a committing action needing approval.
Splitting a PO to stay under an approval threshold is the same authority violation with extra steps.

**Inventory movement is committed, not a draft:** even a same-status location-to-location transfer moves real
stock and leaves an audit trail - its undo is a reverse transfer, not a delete. It is lower-risk than a status
change or a ledger posting, but gate it as a committing write, never as an editable draft.

Universal rules to teach: identify the product line, then read the PO/invoice/receipt's approval + match +
period + status + (LN) integration-transaction state before any write, and **re-read at execute** because
ION replication lags and periods close underneath you; never release a matching hold, loosen a tolerance, or
split a value to bypass a control; a hold or a closed period means **stop**; an Unposted journal/voucher is
safe, posting it is not.

## Gotchas that bite (the real set - causal chains)
1. **Wrong product line targets the wrong screen.** M3 (PPS/MMS programs), LN (tdpur/tfacp/whinh sessions),
   and SyteLine (named forms + IDOs) name the same object differently. Applying one line's field/screen logic
   to another acts on the wrong thing. Identify the line first. `references/product-lines.md`.
2. **A goods receipt is a financial event, not a note.** It increases inventory and drives a GL posting - in
   M3 via accounting rules (immediately if the update method is interactive, or deferred until a batch update
   job runs), in LN only once integration transactions are posted, in SyteLine once the transaction is posted.
   Treating it as a stock-only update, or assuming the GL is written the instant stock moves, misses the ledger side.
3. **In LN, logistics and finance are decoupled.** A warehouse receipt creates a logistic transaction; the GL
   entry exists only after **integration transactions are mapped and posted**. Reading GL before they are
   processed shows stale finance - logistics and the ledger disagree until you process them.
   `references/posting-periods-approvals.md`.
4. **Reversing a receipt is not an undo.** It posts a counter-transaction; both stay in the trail; it
   re-values stock; and it cannot restore a quantity already issued or consumed.
5. **A closed accounting period is a wall.** Posting into a closed period is refused or misdated. LN keeps
   **separate fiscal, tax, and reporting period statuses** - a period can be open for one type and closed for
   another - and a **Finally Closed** period can never reopen. A **tax posting into a closed tax period is
   refused even when the fiscal period is open** - the tax period is its own wall. Reopening is a finance-close
   decision, not a workaround.
6. **Approval state can live in ION, outside the ERP screen.** A PO or invoice may look actionable on the
   form while an ION Workflow still holds it for approval. Check the workflow status; do not push a document
   that ION has not released.
7. **A matching hold means stop - clear the cause, not the flag.** A three-way match (PO, receipt,
   invoice/voucher) holds on a price or quantity variance beyond tolerance. Tax and charges on the invoice are
   part of the matched amount, so a tax variance is a match discrepancy too. Fixing the cause and re-matching
   clears a system hold normally; **releasing the hold or loosening the tolerance** pays a disputed or
   mismatched invoice - the destructive path, needing a named approver.
8. **Valuation method changes what a receipt posts.** Under standard cost an off-price receipt posts a
   purchase price variance; under **MAUC / average** (LN) the receipt moves the item's average; under **FTP**
   (LN Fixed Transfer Price) it values at the fixed price and books the difference elsewhere. Reason about
   cost only after you know the method. `references/receiving-matching-costing.md`.
9. **A small receipt at an outlier price moves the whole average.** Under MAUC/average, a few units at a bad
   price shift the on-hand valuation for everything - e.g. 1000 units at a $10 average plus 10 units at $100
   moves the average to about $10.89 across all 1010 units, a costing distortion, not just a line effect.
10. **CloudSuite is multi-tenant - you cannot patch core code.** Behaviour changes go through the
    extensibility framework (extensions, ION scripts, Mongoose for CSI), and upgrades are vendor-scheduled.
    Assuming you can hotfix core logic, or that behaviour is frozen, is wrong.
11. **BOD replication lags.** Because apps exchange Business Object Documents over ION asynchronously, a copy
    in another Infor app or the Data Lake can be behind the source-of-record app. Re-read the authoritative
    app at execute, not the replicated view.
12. **On hand is not available.** Stock carries a status (available / quality / blocked), lot/serial, and
    allocations; quality-held, blocked, or allocated stock is on the books but not usable. In M3 this is per
    **balance identity**, so a company-level "on hand" hides where and in what status the stock is.
13. **Consignment and subcontract stock are not free own-stock.** Supplier-owned consignment (ownership
    transfers only at consumption) and components provided to a subcontractor are not yours to net or deploy;
    counting them overstates inventory. `references/receiving-matching-costing.md`.
14. **Lot/serial-controlled items cannot move without their lot/serial.** A move that omits it fails; a wrong
    lot mis-assigns shelf-life or quality (heavily used in M3 food/pharma) and can ship expired stock.
15. **A PO is not a commitment until approved.** Changing an approved PO past tolerance re-triggers approval;
    an unapproved PO is not an obligation. Do not treat a draft as sent or a sent PO as still editable freely.
16. **SyteLine "Post" is the point of no clean undo.** Journals and vouchers are Unposted (editable) until
    posted; posting updates the GL and cannot be un-posted - you reverse with a new entry. An **unvouchered
    receipt** sits as an accrued liability until a voucher is built and matched.
17. **An AP payment run is cash out the door.** Voiding or reversing a posted payment reopens the invoice and
    has bank-reconciliation impact; it is not a clean cancel.
18. **A mis-set M3 accounting rule posts to the wrong account silently.** The logistics screen looks correct
    while the GL is wrong; the error surfaces only in finance. Verify the accounting result, not just the
    logistics confirmation.
19. **Canceling a PO line that already has receipts strands them.** The receipt, accrual, and any invoice
    remain; matching breaks and the accrual can be left open. Resolve the receipts and invoices first, then
    cancel - not the reverse.
20. **Period-end in LN needs all integration transactions processed before finance close.** An unprocessed
    integration transaction stuck at close leaves the subledger and GL out of balance for that period - the
    close reconciliation depends on it.
21. **A receipt booked against the wrong PO line puts the cost on the wrong account/cost object.** The value
    follows that line's account assignment; you cannot move it in place - you reverse the receipt and
    re-receive against the correct line. Check the line before confirming.
22. **Multi-currency rate differences create their own matching variance.** When the exchange rate differs
    across the PO, receipt, and invoice dates, the converted amounts diverge and can raise a matching hold (and
    post an exchange-rate variance) even when quantity and unit price agree in the document currency.

(Deeper per-topic detail: `references/product-lines.md`, `references/posting-periods-approvals.md`,
`references/receiving-matching-costing.md`.)

## Edge states & special cases
Each breaks naive "one screen, one number" logic. Key rule inline; full behavior in the reference noted.
- **Product-line identity** - M3 vs LN vs SyteLine changes objects and addressing; a CloudSuite name only
  tells you the industry edition. `references/product-lines.md`.
- **LN integration transactions** - logistics and finance are two ledgers reconciled by a mapping scheme;
  unposted integration transactions mean they disagree. `references/posting-periods-approvals.md`.
- **Separate period types (LN)** - fiscal, tax, and reporting periods close independently; check the one your
  posting touches.
- **Valuation method (FTP / standard / MAUC / FIFO/LIFO/Lot)** - decides what a receipt posts and what a
  transfer re-values. `references/receiving-matching-costing.md`.
- **Consignment / subcontract stock** - not free own-stock; exclude from owned value and deployable quantity.
- **Lot / serial control** - a controlled item cannot transact without its lot/serial; a wrong lot
  mis-assigns quality/shelf-life.
- **CloudSuite multi-tenant** - no core-code changes; extensibility framework only; vendor-scheduled upgrades.
- **ION / BOD async replication** - the source-of-record app is authoritative; replicated copies lag.
- **Partial receipt then backorder** - a partly received PO whose remainder the supplier backorders keeps its
  commitment open; the line is not closed, so re-planning must account for the open remainder.
- **Invoice before quality release** - if a receipt sits in quality/blocked status when the invoice arrives,
  the three-way match's received quantity is effectively zero until the hold clears; matching before release
  under-matches. Release quality first, then match.
- **Failed integration transaction (LN)** - an integration transaction in a *failed* status (not merely
  unprocessed) blocks the period close and needs the mapping/data corrected, not a re-run of a clean batch.
- **Intercompany / multi-company (LN)** - intercompany POs/receipts post their own integration transactions
  with a distinct sequence and period implications; an intercompany flow can fail at the integration step
  where a single-company flow would not. Treat it as a special case, not the default path.

## Reconciliation & freshness
- The **source-of-record app** (M3, LN, or SyteLine) is authoritative for its objects. ION-replicated copies,
  portal views, and the Data Lake can lag - re-read the authoritative app at execute.
- In LN, **finance can lag logistics** until integration transactions are posted. A GL read during a
  logistics-heavy window may be behind; check whether integration transactions are outstanding before trusting
  the ledger for a decision.
- Re-read approval/workflow status in **ION** at execute - a document released for approval a moment ago may
  now be held, and vice versa.
- Stock read at plan time drifts by execute; confirm status, allocation, and balance identity (M3) before
  acting on a quantity.

## Recovery patterns (can it be undone, and what can't)
- **Goods receipt reversal** - a counter-transaction with a permanent trail; re-values stock; cannot restore
  a consumed quantity. The mechanism differs by line (M3 a reversal/return against the receipt program, LN a
  warehouse-receipt reversal/return, SyteLine a return on the receiving form) - see
  `references/receiving-matching-costing.md`.
- **Supplier invoice / voucher** - after matching or posting, corrected by a reversal or a credit/debit memo
  (a new document with its own accounting), not by deletion. A paid invoice cannot simply be deleted.
- **Posted journal / voucher** - reversed only by a new reversing entry, dated in an open period; you cannot
  un-post.
- **AP payment** - void/reverse reopens the invoice and carries bank-reconciliation impact; not a clean undo.
- **Period reopen** - finance-close owned; an LN **Finally Closed** period never reopens. Correct in the
  current open period instead.
- **Wrong valuation / average** - corrected by a cost revaluation (itself a committing financial posting),
  not an undo.
- **LN unprocessed integration transactions** - process and reconcile them; do not force a finance close over
  the gap.

## Guardrails
- Identify the product line, then read the document's approval + match + period + status + (LN) integration
  state before acting; re-read at execute, because ION replication lags and periods close underneath you. In
  LN, check fiscal, tax, and reporting period status independently; in M3/SyteLine, check the single
  GL/accounting period status.
- Never release a matching hold without fixing its cause (if business necessity truly demands it, that is a
  destructive action needing a named approver, not a routine release), never loosen a tolerance or split a
  value to dodge a control, and never reopen a closed period to force a posting. If a closed period needs a
  correction, it is a finance-close decision made in the current open period.
- Treat every goods receipt, three-way match, posting, integration-transaction process, and payment run as a
  committing ledger/stock/cash event. An Unposted journal/voucher is the safe preview.
- For anything in the destructive row (reverse, cancel, void, hold release, revaluation, period reopen):
  named approver, re-read, and log the reason. It re-values, frees stock, or moves cash - it is not a correction.

## References (load on demand)
- `references/product-lines.md` - **load when you need screen/program/session/form names or object
  addressing.** M3 vs LN vs SyteLine/CSI object and screen map; the CloudSuite editions and which line each
  sits on; where the same task diverges.
- `references/posting-periods-approvals.md` - **load when the task posts, closes/checks a period, or crosses
  an approval.** Period types and statuses per line; M3 accounting rules, LN integration transactions and the
  mapping scheme, SyteLine posting; ION Workflow vs native approval and how a threshold routes.
- `references/receiving-matching-costing.md` - **load when receiving, matching an invoice/voucher, or
  reasoning about cost.** Goods-receipt families; three-way match per line and tolerances (with worked
  examples); valuation methods (FTP / standard / MAUC / FIFO/LIFO/Lot) and variances; consignment,
  subcontract, lot/serial stock.
