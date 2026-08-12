# Oracle ERP - Subledger Accounting, GL, and periods

How a subledger transaction becomes a general-ledger balance, and the period boundaries that decide whether a
posting is even allowed. Read when a workflow accounts a transaction, posts or reverses a journal, or touches
an accounting period, ledger, or budgetary-control entry.

## Contents
- Subledger Accounting (SLA)
- Create Accounting: Draft vs Final
- Transfer and post to GL
- GL journal states and reversal
- Accounting period statuses (the wall)
- Ledgers, secondary ledgers, reporting currency
- Budgetary-control accounting
- Foreign-currency revaluation and translation

## Subledger Accounting (SLA)
- SLA is the engine that derives **journal entries** for the subledgers (Payables, Purchasing/Receiving, Cost
  Management, Receivables) from their transactions, using the ledger's accounting method (rules that map a
  transaction to accounts). It is the **only** correct path from a subledger event to the GL.
- Editing the resulting GL journal by hand breaks reconciliation between the subledger and the ledger. Correct
  the subledger transaction and re-account instead.

## Create Accounting: Draft vs Final
- **Create Accounting** turns a subledger transaction into SLA journal entries.
  - **Draft** - derives and shows the entries for review; **posts nothing**. Safe preview.
  - **Final** - creates the entries and (with the transfer/post options) sends them to GL. This is the **point
    of no clean undo**: the entries now exist in SLA and, once posted, in GL balances.
- To reverse Final accounting you post a **reversing or offsetting entry**, not a deletion.

## Transfer and post to GL
- Final accounting can **Transfer to General Ledger** and **Post in General Ledger** in one run, or transfer as
  unposted for GL to import and post. Posting updates **account balances**.
- Journal Import brings subledger and interface entries into GL as journal batches.

## GL journal states and reversal
- Journal states: **Unposted** (editable/deletable) -> **Posted** (balances updated). A posted journal cannot
  be un-posted.
- **Reversal** creates a *new* reversing journal (swapped debits/credits), dated in an **Open** period - by an
  assigned reversal method/period or on demand. Both the original and the reversal remain in the audit trail.
- Rule: to fix a posted entry, reverse and re-enter; never expect an in-place undo.

## Accounting period statuses (the wall)
Per ledger, an accounting period is in one of:
- **Never Opened** - not yet available.
- **Future Enterable** - entries may be *entered* but not posted (a limited forward window).
- **Open** - the only status where accounting and posting land.
- **Closed** - no posting; can be **reopened** by the finance close if needed.
- **Permanently Closed** - no posting and **cannot be reopened**, ever.

Consequences:
- Create Accounting or a post into a **Closed** period is refused, or (mis-set) reassigned to the next Open
  period and misdated. A reversal or correction must be dated into an Open period.
- Reopening a Closed period is a **finance-close decision**, not an agent workaround. If a closed month needs a
  correction, make it in the current Open period.

## Ledgers, secondary ledgers, reporting currency
- A **ledger** is defined by its 4 C's: **Chart of accounts, accounting Calendar, Currency, accounting
  Convention** (subledger accounting method).
- A **secondary ledger** or a **reporting currency** gets its **own** SLA accounting from the same
  transactions. A manual journal entered only in the primary ledger does **not** flow to them automatically.

## Budgetary-control accounting
- With encumbrance on, reservations post as encumbrance journals: **commitment** (requisition), **obligation**
  (PO), then the **actual** at invoice. Each stage relieves the prior; **Cancel/Finally Close** liquidates the
  remainder. Encumbrance entries also respect period status.

## Foreign-currency revaluation and translation
- Foreign-currency transactions convert at a rate per stage; rate differences post **Invoice/Exchange Rate
  Variance** (see `payables-matching.md`).
- At period end, **revaluation** restates open foreign-currency balances at the period rate (unrealized
  gain/loss), and **translation** restates the whole ledger into a reporting currency. Both are period-close
  postings owned by finance, not routine writes.
