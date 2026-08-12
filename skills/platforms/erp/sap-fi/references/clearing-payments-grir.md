# SAP FI - clearing, payments, GR/IR

How open items become cleared, how payments post and reverse, and how the MM/FI GR/IR bridge is resolved.
Read when a workflow clears items, runs or reverses a payment, or reconciles GR/IR.

## Contents
- Open items and clearing (F-32 / F-44 / F-03)
- Partial vs residual clearing
- Reset clearing (FBRA)
- Manual payments
- The F110 payment run
- Payment and dunning blocks
- GR/IR clearing and MR11

## Open items and clearing
- Sub-ledger accounts (AP/AR) and open-item-managed G/L accounts (GR/IR, bank clearing) carry **open items** -
  lines awaiting an offset. "Open" means unmatched, not overdue.
- **Clearing** matches debits and credits that net to zero and writes a **clearing document** with a clearing
  date. The matched items become **cleared**; they are not deleted.
- Transactions: **F-32** clear customer, **F-44** clear vendor, **F-03** clear G/L, **F-30** post with
  clearing (post a new item and clear in one step). **F.13** is automatic clearing by rule.
- An item clears only against the **same account** and a compatible currency; a mismatch stays open.

## Partial vs residual clearing (they are not the same)
- **Partial payment** - the original open item stays **open** at its full amount; the partial payment posts as
  its **own** open item linked to it. Both remain open. The original **baseline date** is unchanged.
- **Residual payment** - the original item is **cleared** and a **new** open item is created for the remaining
  balance, with a **new baseline date**. That resets payment-term and dunning timing, and can drop an earned
  cash discount.
- Choosing residual when you meant partial silently restarts the due-date/dunning clock on the remainder.

## Reset clearing (FBRA)
- **FBRA** reverses a clearing: it reopens the previously cleared items. It can optionally also reverse the
  clearing/payment document.
- Required **before** you can reverse a payment that cleared invoices - you cannot FB08 a cleared document
  directly. Sequence: FBRA (reopen) -> then reverse the payment if needed.
- FBRA reopens the ledger items; it does **not** un-send money that already left the bank.

## Manual payments
- **F-53** post outgoing payment, **F-58** payment with printout, **F-28** incoming payment, **F-26** incoming
  fast entry. Each posts a payment document and clears the target open items.
- A manual payment is a committing ledger event: it moves the sub-ledger balance and (via the bank/clearing
  account) real cash.

## The F110 payment run (automatic payment program)
Two phases, different blast radius:
1. **Proposal** - the program proposes which open items to pay by due date, payment method, and block status.
   The proposal is **editable and deletable** - a reversible draft. Reviewing/editing it is safe.
2. **Payment run** - carrying it out **posts the payment documents, clears the invoices, and generates the
   payment medium** (bank file / checks / ACH). This is committing, and once the bank file is transmitted it
   is effectively irreversible.
- To undo a run: FBRA to reset the clearing and reverse the payment documents, **and** recall the bank file
  manually at the bank. If the file already went out, the money may be unrecoverable.
- Config lives in **FBZP**. Treat "run F110" as destructive; treat "edit the proposal" as reversible.

## Payment and dunning blocks
- A **payment block** (field ZLSPR) on a line item or on the vendor master stops that item from being paid by
  F110. Blocks are set for disputes, holds, missing goods, or compliance.
- Lifting a block to force a payment through is an authority/compliance violation, not a fix - it belongs to
  the person who set it. A block means stop.
- A **dunning block** similarly stops AR reminders; lifting it re-exposes the customer to dunning.

## GR/IR clearing and MR11
- The **GR/IR clearing account** is an open-item-managed G/L account that bridges the MM goods receipt and the
  invoice. GR (MIGO 101) debits stock/expense and credits GR/IR; IR (MIRO) debits GR/IR and credits the vendor.
  When quantity and price match, GR/IR nets to zero and the items clear.
- A **quantity or price mismatch leaves a residual open item** on GR/IR - the classic 3-way-match exception.
- **MR11** (GR/IR account maintenance) clears residual balances by **writing the difference to a P&L account**.
  It is a destructive adjustment with expense impact, not routine housekeeping - it needs review, not a reflex.
- FI owns the GR/IR reconciliation and MR11 write-off from the ledger side; MM owns the goods movement side.
