# Dynamics 365 F&O - ledger, periods, dimensions, and inventory cost

The controls that decide whether a posting is allowed, which accounts it hits, and what it costs. Read when
the task touches the general ledger, fiscal periods, financial dimensions, number sequences, or inventory cost.

## Contents
- Subledger to general ledger (vouchers and transfer)
- General journals and reversal
- Fiscal / ledger calendar and period status
- Inventory close and cost adjustment
- Costing methods and the item model group
- Standard cost versions
- Financial dimensions and combinations
- Number sequences

## Subledger to general ledger (vouchers and transfer)
- Every posting creates a **voucher**: a balanced set of ledger entries with a date and a number. Source
  documents (vendor invoices, product receipts, inventory transactions) post a **subledger journal** that
  transfers to the **general ledger**.
- **Transfer to general ledger** can run **synchronous** (immediate), **asynchronous**, or **scheduled batch**.
  When it is batched, GL balances **trail** the subledger until the batch runs - reading the GL before transfer
  under-reports what is actually posted. Reconcile subledger to GL, and check the transfer mode before trusting
  a GL balance for a same-day posting.

## General journals and reversal
- A **general journal** (journal name + voucher lines) is editable until **posted**. A posted voucher is never
  un-posted.
- To correct a posted voucher, post a **Reverse transaction (storno)** - a new reversing voucher dated in an
  **open** period. Both the original and the reversal remain in the trail. Set a reversal date that falls in an
  open period; a reversal into a closed period is refused.
- Recurring/periodic journals and ledger settlement post the same way - each is a voucher, not a scratch edit.

## Fiscal / ledger calendar and period status
- A **fiscal calendar** defines fiscal years split into periods. The **ledger calendar** (per legal entity)
  sets each period's status, **per module**: **Open**, **On hold**, **Closed**, **Permanently closed**. Module
  access can further restrict which user groups may post in a period.
- Postings land only in **Open**. **On hold** blocks postings for the affected module(s). **Closed** must be
  reopened (a finance-close action) before any posting; **Permanently closed** can **never** reopen.
- A voucher posts to the period of its **transaction/accounting date**, not today's date. Letting the date
  default when the current period is closed silently misposts to another open period - set the date into the
  intended open period.
- **Year-end close** rolls balances to retained earnings and opens the new year; opening transactions are
  generated. Reopening a prior year to post is a controlled finance action.

## Inventory close and cost adjustment
- **Inventory close** is the period settlement: it matches **issues to receipts** by the item's costing method
  and posts cost **adjustments** so the running (estimated) cost is trued up to the settled cost. A **stop/close
  date** bounds it.
- Once a period is closed for inventory, posting a **back-dated** transaction into it requires **cancelling the
  close** and re-running it, which recomputes cost across the period - a heavy, revaluing action.
- **Recalculation** is a non-settling estimate (does not fix the settlement); **close** is the settling run.
  Correct a single wrong cost with a targeted **cost adjustment** where possible, rather than cancelling close.
- Physical cost (at product receipt) is estimated; financial cost settles at invoice and at close. Margin and
  valuation are only final after the invoice and the inventory close.

## Costing methods and the item model group
- The **item model group** sets the **costing method**: **Standard**, **Weighted average**, **Moving average**,
  **FIFO**, **LIFO**. It also controls whether **physical** and **financial negative inventory** are allowed.
- Under **Standard**, a receipt/invoice at an off-standard price posts a **purchase price variance** to a
  variance account; stock stays at standard. Under the moving/average/FIFO methods the transaction **moves the
  running value**; a small-quantity receipt at an outlier price shifts the average.
- **Negative inventory**: if allowed, issues can drive on-hand negative and produce an unreliable running cost
  until close; if not allowed, the issue posting is **blocked**.

## Standard cost versions
- Standard costs live in **cost versions** with a status: a **pending** version does nothing until it is
  **activated**. Activating a version **revalues** on-hand at the new standard and posts a revaluation voucher.
- Do not activate a cost version mid-period without expecting the revaluation posting; it is a committing,
  revaluing action, not a price edit.

## Financial dimensions and combinations
- **Financial dimensions** (Department, Cost center, Business unit, and custom) combine with the **main account**
  to form the **ledger account** (a ledger dimension). Values **default** onto a voucher from the account,
  vendor, item, or a defaulting rule.
- A **wrong default dimension** posts to the wrong cost center/department silently. **Account structures** and
  **advanced rules** validate which main-account + dimension combinations are legal; an invalid combination
  **blocks** a posting that otherwise looks fine. Read the derived dimensions before posting.

## Number sequences
- Every document (PO, confirmation, product receipt, invoice, voucher, journal) draws a number from a **number
  sequence**. **Continuous** sequences guarantee **no gaps** (used where invoices/vouchers must be sequential)
  and serialize postings; a **failed** post can leave a **reserved** number that needs **number-sequence
  cleanup**. **Non-continuous** sequences allow gaps and avoid the bottleneck.
- Confirming a PO or posting a document **consumes** a number; you cannot cleanly reuse or rewind a consumed
  continuous number without cleanup. A stuck continuous sequence can block posting until cleaned up.
