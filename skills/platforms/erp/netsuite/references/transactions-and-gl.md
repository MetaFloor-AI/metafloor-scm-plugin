# NetSuite transactions and their GL impact

The one thing to know before touching any NetSuite transaction: is it **posting** or **non-posting**? A
non-posting transaction commits or promises but moves no ledger; a posting transaction moves the general
ledger the moment it saves. This file lists the families that matter for gating and the exact accounts each
touches, then the two end-to-end flows (procure-to-pay, order-to-cash).

## Contents
- Non-posting transactions (commitments, no GL)
- Posting transactions (move the ledger)
- Procure-to-pay flow and Received Not Billed
- Order-to-cash flow
- Three-way match, variances, and where the numbers lie

## Non-posting transactions (commitments, no GL)
These change the operational state (what is promised, ordered, expected) but post nothing to the GL. They
are still consequential because they commit to a customer or vendor.
- **Sales Order (SO)** - promise to a customer. Drives fulfillment and billing but posts no revenue until the invoice.
- **Purchase Order (PO)** - commitment to a vendor once approved and transmitted. Posts no expense/asset until the item receipt.
- **Quote / Estimate, Opportunity** - pre-sale; no commitment, no GL.
- **Return Authorization (RMA) / Vendor Return Authorization** - authorizes a return; the credit/receipt that follows is what posts.
- **Blanket PO / release** - a longer-term commitment; a release/call-off against it commits spend against that agreement, not a free new order.

Gating: SO/PO edits before approval are reversible writes; approving and transmitting a PO is **committing**
(a real vendor commitment) even though it stays non-posting.

## Posting transactions (move the ledger)
Each one writes to the GL when saved. Debit (Dr) / Credit (Cr) shown for the common inventory-item case.
- **Item Receipt** - Dr Inventory Asset, Cr Accrued Purchases (Received Not Billed). The receipt of goods against a PO.
- **Item Fulfillment** - Dr COGS, Cr Inventory Asset. Ships stock and books COGS on an SO (when "post COGS on shipment" is set, the default).
- **Vendor Bill** - Dr Accrued Purchases / expense, Cr Accounts Payable. Clears the receipt accrual and creates the payable.
- **Vendor Credit** - Dr Accounts Payable, Cr expense/accrual. Offsets a bill; the correct offset for an over-bill, in place of deleting the bill.
- **Invoice** - Dr Accounts Receivable, Cr Revenue. Bills the customer.
- **Credit Memo** - Dr Revenue, Cr Accounts Receivable. Offsets an invoice; the correct offset for an over-bill to a customer.
- **Cash Sale** - Dr Undeposited Funds / bank, Cr Revenue (plus COGS leg). Invoice + payment in one.
- **Customer Payment / Vendor Payment** - moves AR/AP against a bank or Undeposited Funds account.
- **Inventory Adjustment** - Dr/Cr Inventory Asset vs an adjustment account. Changes on-hand quantity and value directly.
- **Inventory Count** - a committed physical count posts the counted-vs-book difference as an adjustment (Inventory Asset vs gain/loss). Committing the count, not entering it, is the posting event.
- **Inventory Revaluation / Cost adjustment** - re-values on-hand (or trues up a negative-inventory estimate); posts Inventory Asset vs a variance/adjustment account.
- **Inventory Transfer / Transfer Order** - moves stock between locations; a transfer order can post in-transit.
- **Assembly Build / Work Order Completion** - issues the component stock and receives the finished assembly (Dr finished-good Inventory, Cr component Inventory). **Assembly Unbuild** reverses it. A posting inventory event, not a plan.
- **Customer Deposit** - a prepayment received before invoicing (Dr bank/Undeposited Funds, Cr a customer-deposit liability); applied to the invoice later, it is not revenue when received.
- **Expense Report** - posts employee expense to the expense accounts and a payable/reimbursement once approved.
- **Journal Entry** - Dr/Cr arbitrary accounts, entered directly. **Intercompany JE** posts in two subsidiaries at once.

Gating: every row here is **committing** (a ledger event); editing any of them in place re-posts the GL, and
deleting any of them removes the GL lines (destructive). Void is preference-dependent (see `periods-and-close.md`).

## Procure-to-pay flow and Received Not Billed
1. **PO** (non-posting) - approved and transmitted to the vendor.
2. **Item Receipt** (posting) - Dr Inventory Asset, Cr **Accrued Purchases / Received Not Billed**. Stock is now on the books; nothing owed to the vendor yet in AP.
3. **Vendor Bill** (posting) - Dr Accrued Purchases, Cr Accounts Payable. Clears the accrual and creates the payable.
4. **Vendor Payment** (posting) - Dr Accounts Payable, Cr bank.

**Received Not Billed (Accrued Purchases)** is NetSuite's GR/IR analog: the receipt credits it, the bill
debits it, and when quantity and price match it nets to zero. A mismatch leaves an open balance - received
goods with no matching bill, or a bill amount that differs from the received cost.

## Order-to-cash flow
1. **SO** (non-posting) - approved.
2. **Item Fulfillment** (posting) - Dr COGS, Cr Inventory Asset. Stock leaves and COGS books at shipment.
3. **Invoice** (posting) - Dr Accounts Receivable, Cr Revenue. The customer is billed; revenue books here
   (or is deferred to the revenue-recognition schedule if Advanced Revenue Management is on).
4. **Customer Payment** (posting) - Dr bank / Undeposited Funds, Cr Accounts Receivable.

COGS and revenue are two separate posting events on two separate records. A fulfilled-but-uninvoiced order
has already moved COGS out of inventory even though no revenue or AR exists yet.

## Three-way match, variances, and where the numbers lie
- The three-way match is **PO vs Item Receipt vs Vendor Bill** on quantity and price. Within tolerance it
  clears; outside it leaves an open accrual or posts a variance.
- With advanced receiving / accrue-purchases, a bill price that differs from the receipt cost posts a
  **purchase price variance**, not a change to inventory value; the item stays at its costing value and the P&L absorbs the gap (most visible on Standard-cost items).
- **Landed cost** allocates freight/duty across received items; without it, those costs sit elsewhere and item cost understates true landed cost.
- Reading "on hand at a cost" is unsafe when: the item is negative (COGS was estimated), Standard-costed (value is standard, variance is elsewhere), or multi-location (on-hand is per location, not all available at one site). See `oneworld-costing-inventory.md`.
