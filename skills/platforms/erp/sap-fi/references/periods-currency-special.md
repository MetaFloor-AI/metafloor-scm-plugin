# SAP FI - periods, close, currency, special G/L, tax

The controls and edge states that decide whether a posting is allowed, in which period and ledger it lands,
and what its balance really means. Read when a workflow posts near period close, in foreign currency, across
company codes, or with special G/L or tax.

## Contents
- Fiscal year variant and periods
- Posting periods and close (OB52)
- Year-end balance carryforward
- Foreign currency and valuation
- Parallel ledgers and document splitting
- Special G/L (down payments, bills of exchange, guarantees)
- Cross-company postings
- Tax codes

## Fiscal year variant and periods
- The **fiscal year variant** (OB29) defines the periods: typically 12 normal periods plus up to 4 **special
  periods** (13-16) used for year-end adjustments and audit entries. It may be calendar-based or shifted (e.g.
  a fiscal year that starts in April), or non-calendar (4-4-5 retail).
- Every posting date maps to a period through this variant.

## Posting periods and close (OB52)
- The **posting period variant** (assigned per company code) plus **OB52** control which periods are open for
  posting. OB52 has rows **per account type**: **+** (valid for all), **S** (G/L), **D** (customers), **K**
  (vendors), **A** (assets), **M** (materials).
- Each row has **two intervals**: interval 1 for normal postings and interval 2 usually for special periods /
  privileged users; an **authorization group** on interval 1 restricts who may post.
- Posting into a **closed** period is refused. Opening a period is a finance close decision. Because rows are
  per account type, opening G/L (S) but leaving vendors (K) closed lets a pure-G/L entry post while blocking
  the AP side - a document touching both cannot post.
- The MM posting period (MMPV, `sap-mm`) is separate but must be kept in sync with FI, or a
  goods-movement-driven FI posting is refused on one side.

## Year-end balance carryforward
- At year-end, **FAGLGVTR** (New G/L; classic F.16) carries balance-sheet account balances into the new fiscal
  year and rolls P&L accounts into **retained earnings**. New-year periods must be opened first.
- Posting into a prior year **after** carryforward requires re-running the carryforward so opening balances
  stay correct - the carried-forward figure does not update itself.

## Foreign currency and valuation
- A document posts in **document currency**, translated to **local (company code) currency** at the exchange
  rate (table TCURR), and optionally to parallel currencies (group, hard). Rate type M (average), B (buying),
  G (selling).
- **Realized** exchange differences post at **clearing/payment** - the actual gain/loss when the item settles.
- **Unrealized** differences post at period-end **valuation** (F.05 / FAGL_FCV): open items are revalued at the
  period-end rate, an unrealized gain/loss is posted, and - by the delta/reset method - it **reverses on day
  one of the next period**. Treating unrealized as realized double-counts FX.

## Parallel ledgers and document splitting
- A **leading ledger** (0L) plus optional **non-leading ledgers** support parallel accounting (IFRS vs local
  GAAP). A **ledger-group-specific** posting affects only the ledgers in that group; a correction to 0L alone
  leaves other ledgers out of sync.
- **Document splitting** (New G/L) splits each line by a characteristic (profit center, segment) so every
  dimension balances, enabling segment/profit-center balance sheets. A posting that cannot derive the
  splitting characteristic **fails or falls to a default**, breaking the split balance sheet.

## Special G/L (alternative reconciliation accounts)
Special G/L transactions post to an **alternative** reconciliation account, separate from normal AP/AR.
- **A - down payment** (real): money actually paid/received before the invoice; posts to a down-payment recon
  account; later cleared against the invoice.
- **F - down payment request** (statistical / **noted item**): a single-sided memo that **does not update the
  G/L or the vendor/customer balance**; it triggers the payment program to make the down payment.
- **W - bill of exchange** (real): a payment instrument; posts to its own recon account.
- **G - guarantee** (statistical / noted): a memo of a guarantee given/received; no balance impact.
Reading a vendor/customer "balance" without the special-G/L accounts understates real exposure; treating a
noted item (F, G) as a real payable/receivable double-books it.

## Cross-company postings
- A single logical entry across two company codes (F-02 cross-company) generates **two documents**, one per
  company code, linked by a **cross-company code document number**.
- The system posts automatic **inter-company clearing** lines (clearing accounts configured in **OBYA**) so
  each company code's document balances.
- Reversing a cross-company document must reverse **both**; a wrong inter-company clearing account misroutes
  the balance between the two entities.

## Tax codes
- A **tax code** (2 characters, maintained in **FTXP**) drives the tax type (input/output VAT), the rate, the
  tax G/L account, and jurisdiction. Every tax-relevant line carries one; A0/V0 are common 0% codes.
- Tax is calculated and posted **at document time** from the code. You **cannot retro-change** the tax on a
  posted document - a wrong code needs reversal + repost.
- **Non-deductible** input tax is not recoverable, so it loads onto the **expense or asset**, not a tax account.
- Changing a code's **rate** in FTXP affects **future** postings only, and can break recurring or parked
  documents that reference it. It does not fix already-posted documents.
