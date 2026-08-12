# Infor - periods, posting to GL, and approvals

The three control mechanisms that decide whether a write lands, how logistics reaches the ledger, and who
must approve. Read when a task posts (period), moves a logistics event to finance (accounting rules /
integration transactions / posting), or crosses an approval threshold.

## Contents
- Accounting periods - the wall (per line)
- How logistics reaches the GL (per line)
- Approvals - ION Workflow vs native
- Period-end order of operations

## Accounting periods - the wall (per line)
- **Common invariant:** a posting lands only in an **open** period. Posting into a closed period is refused,
  or (mis-configured) shoved into a different open period and misdated. Reopening is a finance-close decision,
  not an agent workaround.
- **LN** keeps **separate period statuses by type - fiscal, tax, reporting** - each opened and closed
  independently. A period can be open for tax and closed for fiscal. Statuses include Open, Closed, and
  **Finally Closed** (terminal - it can never reopen). Check the status of the specific period type your
  posting touches. A **tax-period close is as hard a wall as a fiscal close** - a tax posting into a closed
  tax period is refused, even if the fiscal period is open.
- **M3** controls the GL period status per company/division; postings outside the open period are rejected.
- **SyteLine** holds status on the "Accounting Periods" form; a period must be open for "Post Transactions"
  to land.
- Practical rule: at execute, confirm the posting/accounting date falls in an open period **of the right
  type** before staging any receipt, invoice, or journal.

## How logistics reaches the GL (per line)
The lines differ sharply here - this is where finance and logistics can silently disagree.
- **M3 - accounting rules, interactive or batch.** Logistics events (receipt, issue, invoice) generate GL
  postings through configured **accounting rules** that derive the account string. Whether the posting lands
  **immediately (interactive update) or waits for a batch update job** depends on configuration - in batch
  mode the GL lags the logistics event, so a just-recorded receipt may not yet be in the ledger. A mis-set
  rule posts to the wrong account **silently** - the logistics screen looks correct; the error only shows in
  the GL. Verify the accounting result, not just the logistics confirmation.
- **LN - integration transactions + mapping scheme (decoupled).** A logistic event creates an **integration
  transaction**; a **mapping scheme** derives its GL accounts; then you **post** the integration transactions
  to the ledger. Until they are posted, the subledger/logistics and GL disagree. Reading GL before processing
  shows stale finance. An unprocessed integration transaction stuck at period close leaves the period out of
  balance.
- **SyteLine - Unposted -> Posted.** Receipts accrue as **unvouchered receipts** (a liability) until a voucher
  is built and matched; journals and vouchers are **Unposted** (editable) until "Post Transactions" updates
  the GL. Posting cannot be un-posted; correct with a reversing entry.

## Approvals - ION Workflow vs native
- **ION Workflow** (Infor OS) runs approvals, monitors, and alerts across the family. On CloudSuite,
  approvals are commonly **ION-driven**, so a PO or invoice's approval state can live **outside** the ERP
  form you are viewing. Always check the workflow status before pushing a document; do not act on a document
  ION has not released.
- **Native approval** also exists per line (e.g. LN's approve-purchase-order step, M3 order status controls).
  Either way, a PO above a configured threshold is **not an obligation until approved and issued**.
- **Never bypass an approval**, and **never split or lower a PO to drop under a threshold** - that is the same
  authority violation with extra steps, and it is auditable.
- **Reclassification:** editing an already-approved PO above the approval or matching tolerance re-triggers
  approval; treat it as a committing action routed to the named approver, not a benign edit.

## Period-end order of operations
Getting the sequence wrong leaves the ledger unbalanced for the period.
1. Stop or drain in-flight logistics (receipts, issues) for the period.
2. **LN only:** process **all** outstanding integration transactions so every logistic event has reached the
   GL. A stuck integration transaction blocks a clean close.
3. Match and post outstanding supplier invoices/vouchers; resolve matching holds (fix the cause, do not
   release the flag).
4. Post remaining journals/vouchers dated in the open period.
5. Finance closes the period. A correction for a closed period is a finance-close decision made in the
   current open period - not a reopen.
