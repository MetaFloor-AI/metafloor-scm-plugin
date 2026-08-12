# NetSuite accounting periods, close, and void vs delete

The controls that decide whether a posting is allowed, and how a correction is made without destroying the
audit trail. Read when a workflow posts near a period boundary, corrects a posted transaction, or hits a
locked or closed period.

## Contents
- Period states: open / locked / closed
- The period-close checklist (in order)
- Allow Non-G/L Changes
- Void vs delete vs offsetting document
- Reversing journals

## Period states: open / locked / closed
A NetSuite accounting period is not a simple open/closed flag. It has selective locks:
- **Open** - postings allowed.
- **Locked A/R** - blocks AR-side postings (invoices, credit memos, customer payments) into that period; other postings still allowed.
- **Locked A/P** - blocks AP-side postings (vendor bills, vendor credits, vendor payments).
- **Locked Payroll** - blocks payroll postings.
- **Locked All** - blocks nearly all postings while leaving the period technically not-yet-closed (used mid-close).
- **Closed** - blocks all posting into the period. The hard monthly/quarterly wall.

A save whose posting date lands in a period locked for that subledger, or closed, is **refused**. Do not
reopen or re-lock to force a posting through - locks are set deliberately during close.

## The period-close checklist (in order)
NetSuite drives close through an ordered, gated checklist. Later steps will not complete until earlier ones
do. The typical sequence (OneWorld adds the intercompany and currency steps):
1. **Lock A/P** - stop new payables postings.
2. **Lock A/R** - stop new receivables postings.
3. **Review Negative Inventory** - resolve items posted below zero (their COGS was estimated).
4. **Review Inventory Cost Accounting** - confirm costing is complete and consistent.
5. **Resolve Date/Exchange-Rate issues** - fix transactions with bad dates or missing rates.
6. **Create Intercompany Adjustments** / **Eliminate Intercompany Transactions** (OneWorld) - balance and eliminate intercompany.
7. **Calculate Consolidated Exchange Rates** (OneWorld) - set the rates for consolidation.
8. **Revalue Open Foreign Currency Balances** - post currency revaluation on open FX balances.
9. **Set Closing Period Adjustments** - final adjusting entries.
10. **Lock All**, then **Close Period** - the terminal step; the period becomes a wall.

Consequence: you cannot Close a period with unbalanced intercompany, unresolved negative inventory, or
incomplete costing - the checklist blocks the Close step until each prior step is cleared.

Steps are conditional on enabled features: the intercompany, consolidated-rate, and FX-revaluation steps
appear only in OneWorld; the negative-inventory and cost-accounting steps only with inventory features on. A
non-OneWorld, non-inventory account will not show them - do not wait on a step the account never has.

Diagnosing a blocked close: each checklist step names its own exceptions. If Close will not complete, work
the earliest incomplete step, not the Close button - a red "Review Negative Inventory" step means specific
items are negative (drill into that step's list to find them); an unbalanced intercompany step names the
subsidiaries and amounts that do not net. Resolve the source, re-run the step, then advance.

## Allow Non-G/L Changes
An accounting preference. With it enabled, a transaction dated in a **closed** period can still have its
**non-financial** fields edited (memo, custom fields, some classifications) without reopening the period. It
never allows changing amounts, accounts, or the posting date into the closed period. Do not read a
successful save under this preference as "the period accepted a financial change" - it did not.

## Void vs delete vs offsetting document
Three ways to unwind a posted transaction, with very different blast radius:
- **Offsetting document (safest)** - a **credit memo** offsets an invoice, a **vendor credit** offsets a
  bill, a **reversing/offsetting journal** offsets a journal. The original stays; the correction is its own dated, auditable posting. Use this to correct a reported period.
- **Void** - keeps the record but zeroes its effect. Behavior is governed by the **"Void Transactions Using
  Reversing Journals"** accounting preference:
  - **On** - voiding posts a reversing journal in the **current open period**, preserving the original period's reported numbers. Audit-safe.
  - **Off** - the void reverses **inside the original period**, silently restating a month that may already be reported.
  Void is available on payment-type and certain transactions; not every transaction exposes a void.
- **Delete (highest blast)** - removes the transaction and its GL lines entirely. Only a **System Note**
  records that it existed. The ledger balance changes with no offsetting document. A delete is blocked or cascades if a downstream transaction (a bill against a receipt, an invoice against a fulfillment) references it.

Rule: prefer an offsetting document or an audit-safe void over delete. Delete only a genuinely erroneous,
same-period, downstream-free transaction, and never to "clean up" a reported period.

## Reversing journals
- A journal entry can be flagged to **auto-reverse**, which posts its reversal in the **following** period
  (used for accruals). It does not reverse in the current period.
- A same-period correction needs a **manual offsetting journal** dated in the current period, not the auto-reverse flag.
- A reversing journal is itself a posting transaction - it is committing, and gate it like any journal.
