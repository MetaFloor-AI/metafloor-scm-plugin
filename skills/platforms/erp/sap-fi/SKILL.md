---
name: sap-fi
description: "SAP Financial Accounting (FI) - the ledger side of SAP S/4HANA or ECC: G/L postings, the AP and AR sub-ledgers, document types and posting keys, special G/L indicators, open-item clearing, the GR/IR interface from MM, parked vs posted documents, document reversal, fiscal periods and close, tax codes, cross-company and foreign-currency postings. Use when the connected ERP is SAP and the work touches financial postings or the ledger, or the user mentions SAP FI, FB50/FB01, FB60/FB65, FB70/FB75, F-32/F-44/F-03 clearing, FB08 reversal, FBRA reset, F110 payment run, OB52 posting periods, a G/L or reconciliation account, an open item, a special G/L down payment, a parked document, a tax code, or the GR/IR clearing account."
---

# SAP FI - operating the ledger safely

SAP Financial Accounting is the book of record in SAP (S/4HANA Universal Journal ACDOCA, or ECC classic
G/L). The thing that makes FI dangerous is simple: **almost every post is a legal accounting document that
updates balances the moment it saves, and there is no delete.** You do not edit a posted entry - you reverse
it with a new document, and both stay in the audit trail forever. This skill classifies FI actions so the
harness can gate them, plus the edge states (special G/L, clearing, cross-company, foreign currency, periods)
and recovery paths that decide whether a mistake is fixable.

## When this applies
Connector is SAP and the work is ledger-side: G/L, AP, AR, clearing, reversal, period, tax. FI **owns the
ledger**; MM owns the goods/PO side of the same money. When NOT:
- materials, PRs/POs, goods receipts, inventory postings, movement types -> `sap-mm`
- warehouse execution (bins, tasks, waves, HUs) -> `sap-ewm`
- customs, export screening, trade classification -> `sap-gts`
- planning / MRP -> `sap-ibp` or `kinaxis`

Shared seam with MM: a goods receipt and an invoice both hit the **GR/IR clearing account**. MM posts the
movement; FI owns the clearing and write-off of that account. See below and `references/clearing-payments-grir.md`.

## Contents
- Object & state model
- Vocabulary that bites
- Operations: read / write / destructive
- Gotchas that bite
- Edge states & special cases
- Recovery patterns
- Guardrails
- References

## Object & state model (reason about state, not nouns)
- **G/L account** (FS00) - a line in the chart of accounts. Flags that change behavior: **open-item managed**
  (items stay open until cleared, e.g. GR/IR and bank clearing), **line-item display**, and whether it is a
  **reconciliation account** (posted only through a sub-ledger, never directly).
- **Accounting document** - every post creates one. Header (document type, posting date, currency) + line
  items (each with a **posting key** and account). It must **balance to zero per company code** (and per
  splitting dimension); a one-sided entry is refused, except a genuine noted/statistical item.
- **Sub-ledgers** - **AP** (vendor, FI-AP) and **AR** (customer, FI-AR). Each vendor/customer posts to its
  **reconciliation account** in the G/L automatically; the sub-ledger detail and the G/L stay in lockstep.
- **Document lifecycle (state):** **held** (private temporary save, **no number**, no balance impact,
  deletable with no trace) -> **parked** (FV50/FV60, **has a number**, visible for review/release,
  editable/deletable but logged, **no balance update yet**) -> **posted** (FB50/FB01, balances + sub-ledger
  updated, open items created) -> **cleared** (open items matched to net zero, a clearing document links them)
  -> **reversed** (a counter-document, FB08; the original remains). A parked document may require **release**
  (approval workflow) before FBV0 will post it; a release block is why an otherwise valid park fails to post.
- **Read source (S/4HANA vs ECC):** in S/4HANA the Universal Journal table **ACDOCA** is the single source of
  truth for line items and balances, with document splitting typically active so profit center/segment sit on
  **every** line; in ECC classic G/L the reads come from **BKPF** (headers) + **BSEG** (line items) + totals
  tables, where BSEG may not carry those characteristics. Querying the wrong one, or comparing ACDOCA to BSEG
  for the same document, returns different line counts or stale data.
- **Open item vs cleared item** - an open item awaits offset (an unpaid invoice, an unmatched GR/IR line);
  "open" means unmatched, not overdue. Clearing sets a clearing date + document; it does not delete anything.
- **Ledgers** - a **leading ledger** (0L) plus optional non-leading ledgers for parallel accounting (IFRS vs
  local GAAP). A ledger-group-specific posting hits only some ledgers.

## Vocabulary that bites
- **Posting key** (2 digits) - sets **both** the debit/credit side **and** the account type of a line. 40/50 =
  G/L debit/credit; 31/21 = vendor invoice/credit-memo; 01/11 = customer invoice/credit-memo; 09/19/29/39 =
  special G/L. A wrong key posts the wrong side to the wrong account type. Table in `references/posting-keys-document-types.md`.
- **Document type** (SA, KR, DR, KZ, AB, RE...) - controls the **number range**, which account types are
  allowed, and the reversal document type. Not cosmetic; it decides what the document may contain.
- **Reconciliation account** - the G/L account behind AP/AR (or an alternative one for special G/L). You
  **cannot post to it directly**; it moves only via the sub-ledger. Changing it on a master re-routes future postings.
- **Parked vs held vs posted** - parked and held do **not** update balances and can be deleted cleanly; posted
  updates the ledger and can only be undone by reversal. Held has no document number and is private.
- **Open-item management** - a per-account flag; items stay open until cleared. Sub-ledgers are always
  open-item managed; GR/IR and bank clearing accounts are the classic OIM G/L accounts.
- **Clearing** - matching debits and credits to net zero, creating a clearing document. Cleared items still
  exist; **FBRA** resets the clearing and reopens them. Clearing is not deletion.
- **Special G/L indicator** - reroutes a posting to an **alternative reconciliation account** (down payments,
  bills of exchange, guarantees). Some are **statistical / noted items** that do not update the ledger at all.
- **Noted item / statistical posting** - a single-sided memo (down payment request, guarantee) that does
  **not** hit the G/L or the vendor/customer balance. It is a reminder, not a liability or an asset.
- **Baseline date** - the anchor from which payment terms and dunning are calculated. A **residual** clearing
  resets it (new item, new clock); a **partial** clearing keeps it.
- **Reversal reason** - on FB08, it decides the reversal's posting date/period and whether it is a **negative
  posting** (reduces the original side) instead of a normal offset.
- **GR/IR clearing account** - the open-item-managed G/L account bridging MM goods receipt and invoice
  receipt; a qty/price mismatch leaves a residual open item that **MR11** writes off to P&L.
- **Document splitting** (S/4HANA New G/L) - splits each line by profit center / segment so every dimension
  balances; a posting that cannot derive the splitting characteristic fails or falls to a default.

## Operations: read / write / destructive
Classify every operation family by what it does to the ledger. The tcodes name the action-kind; the class is
the same whether the connector drives the GUI transaction or a BAPI/RFC (e.g. `BAPI_ACC_DOCUMENT_POST` for a
G/L document). The harness maps the customer's real connector onto these classes.

| Class | SAP FI operation families | Gate | Why |
|---|---|---|---|
| **Read** | display document (FB03); line items (FBL1N/FBL3N/FBL5N, from ACDOCA on S/4 or BKPF/BSEG on ECC); G/L balances (FS10N/FAGLB03); master display (FK03/FD03/FS03); open-item lists; period-status display; tax report; a payment-run **proposal** (before it is carried out) | always pass | no ledger change; read before every write, re-read at execute |
| **Write (reversible)** | park a document (FV50/FV60/FV70, FBV0-save); change **non-value** fields on a posted doc (FB02: text, assignment, payment terms); **set** a payment/dunning block (see note); create/change a recurring-entry template (FBD1); edit a payment **proposal** before it runs | gate one at a time | no balance impact yet, or a cleanly deletable/editable draft; low blast |
| **Write (committing)** | post a G/L document (FB50/FB01); post an AP invoice/credit memo (FB60/FB65) or the MM invoice (MIRO); post an AR invoice/credit memo (FB70/FB75); **post a parked document** (FBV0) = commit it; clear open items (F-32 customer / F-44 vendor / F-03 G/L / F-30 post-with-clearing); post a manual payment (F-53/F-58/F-28); post a down payment (special G/L); post an asset acquisition/transfer (F-90/ABUMN); change a vendor/customer/G/L **master** - payment terms, block, texts (FK02/FD02/FS00; see reclassification rules) | gate + human approve | updates balances / sub-ledger / creates or clears open items, or re-routes/re-times all future postings; each binds money |
| **Destructive / irreversible** | reverse a document (FB08) or mass-reverse (F.80); **reset a clearing (FBRA)**; carry out the **F110 payment run** once it generates payment documents + bank file; MR11 GR/IR write-off; run depreciation (AFAB) or post an asset retirement (ABAVN); open/close a posting period (OB52); year-end balance carryforward (FAGLGVTR); change a tax-code rate (FTXP); change a master **reconciliation account or bank details** (see reclassification rules); lift a payment/dunning block to force a payment through | hard gate + named approver + re-read | permanent counter-entry in the trail; moves real money; crosses a close/compliance boundary; cannot be cleanly undone. Config/behavioral changes (FTXP, OB52, master fields) leave **no** counter-document - they silently alter all future postings, so re-check before and after |

**Reclassification rules (read this):**
- A payment-run **proposal** is a reversible draft, but **carrying out the run** creates payment documents,
  clears the invoices, and produces the bank file - committing, and once the bank file leaves, effectively
  irreversible. Treat "run F110" as destructive, "edit the proposal" as reversible.
- A payment/dunning **block** is asymmetric: **setting** one via FB02 is reversible (it only holds an item),
  but **lifting** one is destructive (it releases the item to be paid/dunned) and belongs to the person who set
  it. The mechanical FB02 field change is the same; the direction decides the class.
- A **master-data** change is not always benign: editing text is low-risk, but changing a **reconciliation
  account, bank details, payment terms, or a block** on a vendor/customer/G/L master re-routes or re-times
  every future posting for that account - treat those field changes as committing or destructive, not an edit.

Universal rules: read the document + its clearing/period/block state before any write, and **re-read at
execute** (another user may have cleared or reversed it). Never post to a **closed period** or reopen one to
force a posting through; never post **directly** to a reconciliation account; never lift a payment/dunning
block to push a payment; a block means stop; every document must balance to zero before it will post.

## Gotchas that bite (the real set - causal chains)
1. **Posting is not saving a draft.** FB50/FB60/FB70 update G/L + sub-ledger + open items the instant they
   post, assign a document number, and cannot be deleted. Only **parked/held** documents are safe to abandon.
2. **FB08 reversal is a new document, not an undo.** It posts a counter-entry with a reversal reason; the
   original and the reversal both stay in the trail forever. Balances net; the history shows both.
3. **You cannot reverse a cleared document.** A payment that cleared an invoice must first have its clearing
   **reset with FBRA** (which reopens the invoice) before the payment can be reversed. Skipping FBRA blocks
   the reversal or leaves orphaned open items.
4. **Reversing an FI document that originated in MM or SD via FB08 only fixes the ledger, not the source.** A
   MIRO logistics invoice is reversed with **MR8M**, an SD billing document with **VF11**; FB08 alone leaves
   the sub-ledger / logistics side inconsistent.
5. **A reversal into a closed period fails or misdates.** The reversal reason sets the posting date; a reason
   that forces the original (closed) month is refused. Corrections post in the current open period.
6. **You cannot post directly to a reconciliation account.** AP/AR recon accounts move only through the vendor
   or customer sub-ledger; a direct G/L line to a recon account is rejected.
7. **A down payment request (special G/L F) is a noted/statistical item.** It does not update the G/L or the
   vendor balance - it is a memo that triggers the payment program. Counting it as a real payable double-books it.
8. **A special G/L posting sits on an alternative reconciliation account.** A down payment is on a different
   G/L than normal payables; reading the vendor's "balance" without the special G/L account understates exposure.
9. **Partial and residual clearing behave differently.** **Partial** leaves the original open item open and
   adds the payment as its own open item; **residual** clears the original and creates a **new** open item for
   the remainder with a **new baseline date**, resetting dunning and cash-discount timing.
10. **Clearing is not deletion.** Cleared items still exist and can be reopened by FBRA. "Cleared" means
    matched to net zero, not gone.
11. **A closed posting period (OB52) is a wall.** Posting into a closed period is refused. OB52 has **two
    intervals per account-type row**: interval 1 for normal postings (with an authorization group restricting
    who may post) and interval 2 usually for special periods. A close-time failure usually means the needed
    account-type row is closed or the user lacks the authorization group - opening a period is a finance decision, not a workaround.
12. **OB52 is per account-type row (+, S, D, K, M, A).** Opening G/L (S) but leaving vendors (K) closed lets a
    pure-G/L posting through while blocking the AP side, so a document that touches both cannot post cleanly.
13. **The GR/IR account is cleared by matching, not by posting.** GR debits, IR credits; a quantity or price
    mismatch leaves a residual open item, and **MR11** resolves it by **writing the difference to P&L** - an
    adjustment with expense impact, not housekeeping.
14. **Cross-company postings generate two documents,** one per company code, linked by a cross-company number,
    with automatic inter-company clearing lines (config OBYA). Reversing must reverse both; a wrong clearing account misroutes the balance.
15. **Foreign-currency valuation is usually reversing.** F.05 / FAGL_FCV posts an **unrealized** gain/loss at
    the period-end rate and reverses it on day one of the next period; the **realized** difference posts only
    at actual clearing/payment. Treating unrealized as realized double-counts FX.
16. **A ledger-group-specific posting hits only some ledgers.** A correction posted to the leading ledger (0L)
    but not the local-GAAP ledger leaves the two out of sync at period end.
17. **FB02 can change only non-value fields** (text, assignment, payment terms, payment/dunning block). Amount,
    account, posting key, cost object, and tax are frozen once posted; fixing those needs reversal + repost.
18. **A payment block exists for a reason** (dispute, hold, missing goods). Lifting it to make F110 pay is an
    authority/compliance violation, not a fix.
19. **The F110 run is committing the moment it produces payment media.** The proposal is editable and
    deletable; after the run posts payment documents, clears the invoices, and cuts the bank file, recalling it
    means FBRA on the clearing **and** recalling the bank file manually - the money is already moving.
20. **Tax posts from the tax code at document time and cannot be retro-changed.** A wrong tax code needs
    reversal + repost; **non-deductible** input tax loads onto the expense/asset, not a recoverable tax account.
21. **A document must balance to zero** per company code and per splitting dimension, or it will not post; only
    a genuine noted/statistical item is single-sided.
22. **Document numbers are not globally unique.** Number ranges are per document type, company code, and fiscal
    year; the same number can exist in another year or company code.
23. **A master-data field change is a silent committing action.** Changing a vendor's reconciliation account,
    bank details, or payment terms re-routes or re-times **every future posting** for that account - no
    document to reverse, and often no obvious trail. Bank-detail changes are a known fraud vector; gate them.
24. **A P&L line needs a CO account assignment, and splitting needs a profit center.** Every cost/revenue
    (P&L) line requires a controlling object - **cost center, internal order, WBS element, or profit center**;
    in S/4HANA the Universal Journal merges FI and CO, so a P&L posting without a valid CO object, or one where
    document splitting cannot derive the profit center/segment, is refused with a cryptic "Balancing field
    profit center is not filled". Recovery: supply the CO object / profit center on the line (or fix the
    derivation rule), not force a default that breaks the split balance sheet.
25. **A parked document can fail at post.** Only some fields are validated at park time, and it may need
    **release** first: parking above a threshold routes to release codes/groups (an approval workflow), and
    FBV0 is refused until released (check status via FBV3). A release block, not a data error, is often why a valid park will not post.

(Deep tables: `references/posting-keys-document-types.md`, `references/clearing-payments-grir.md`, `references/periods-currency-special.md`.)

## Edge states & special cases
Each breaks naive "debit here, credit there" logic - the key rule inline, full behavior in references.
- **Special G/L (down payments A, bills of exchange W, guarantees G, down-payment request F)** - reroutes to
  an alternative recon account; **F and G are statistical/noted** and never hit balances. Detail in `references/periods-currency-special.md`.
- **Cross-company** - one logical entry becomes two documents with inter-company clearing; reverse both together.
- **Foreign currency / valuation** - realized (at clearing) vs unrealized (at F.05 valuation, reverses next period); rate type + parallel currencies matter.
- **Document splitting / parallel ledgers** - a posting missing a splitting characteristic (profit center/segment) fails or defaults; a ledger-group posting touches only some ledgers.
- **Tax** - the tax code drives rate + tax account; non-deductible tax loads onto the base; changing a rate (FTXP) affects only future postings.
- **GR/IR** - the open MM/FI bridge; residual balances are an MR11 write-off, not a clean netting.
- **Asset accounting (FI-AA)** - a sub-ledger with its own objects: an **asset master** in an **asset class**
  (defaults the G/L accounts + depreciation terms), and one or more **depreciation areas** (parallel
  valuations, e.g. local GAAP vs IFRS). Lifecycle: acquired -> depreciating -> retired. Its postings hit the
  asset sub-ledger **and** the G/L: acquisition (F-90) and transfer (ABUMN) are committing; retirement (ABAVN)
  and the period-bound **depreciation run (AFAB)** are destructive (AFAB cannot be casually re-run). Deep FI-AA
  config (classes, areas, keys) is out of this skill's core - gate the postings and defer the setup.

## Recovery patterns (can it be undone, and what cannot)
- **Reverse (FB08 / F.80)** - a new counter-document, not an undo; original + reversal are permanent in the
  trail. The reversal reason controls the date/period; it cannot land in a closed period.
- **Reset clearing (FBRA)** - reopens cleared items and (optionally) reverses the clearing/payment document.
  Required **before** reversing a payment; it does not un-send money that already left via the bank file.
- **Parked / held** - the safe undo path: delete before posting, no ledger impact. Once posted (FBV0), only reversal remains.
- **FB02 change** - only non-value fields. A wrong amount/account/tax/cost object is corrected by reversal +
  repost, never by editing.
- **Closed period** - a wall; correct in the current open period. Reopening (OB52) is a finance decision, not an agent action.
- **Sent payment (F110)** - not cleanly reversible; needs FBRA on the clearing plus a manual bank-file recall, and may already be irrecoverable.

Failure -> recovery, at a glance:

| Situation | Recovery path |
|---|---|
| Wrong amount / account / tax / cost object on a posted document | reverse (FB08) + repost; FB02 cannot fix value fields |
| Posted to the wrong but still-open period | reverse + repost in the intended period; never reopen a closed one |
| A cleared item must be reversed | FBRA to reset the clearing (reopens the items), then FB08 |
| The F110 run already went out | FBRA on the clearing + reverse the payment docs + recall the bank file manually |
| An MM/SD-sourced FI document is wrong | reverse at the source: MR8M (MIRO) or VF11 (SD billing), not FB08 |
| A parked document is wrong or unneeded | delete it before posting - no ledger impact |

## Guardrails
- Read the document and its **clearing + period + block + special-G/L** state before acting; re-read at execute.
- Never post to a closed period, never reopen one to force a posting, never post directly to a reconciliation account.
- Never lift a payment/dunning block to push a payment; a block means stop.
- Reverse in the module that owns the source (MR8M for MIRO, VF11 for SD); FBRA before reversing a cleared/paid item.
- Treat carrying out F110, MR11 write-off, OB52 period change, and year-end carryforward as destructive:
  named approver, re-read, log the reason. Size any reversal before posting - it is a permanent trail entry, not a correction.

## References (load on demand)
- `references/posting-keys-document-types.md` - posting keys (40/50, 31/21, 01/11, 09/19/29/39), document types, number ranges, field status, reconciliation accounts.
- `references/clearing-payments-grir.md` - open-item management, F-32/F-44/F-03 clearing, partial vs residual, FBRA reset, the F110 payment run and blocks, GR/IR and MR11.
- `references/periods-currency-special.md` - OB52 periods and close, fiscal year variant, year-end carryforward, foreign-currency valuation, special G/L, tax codes, cross-company, document splitting and ledgers.
