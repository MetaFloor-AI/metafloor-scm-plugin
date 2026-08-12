---
name: coupa
description: "Coupa business spend management (BSM) - safe operation of procure-to-pay: requisitions, approval chains, purchase orders, receipts, supplier invoices via the Coupa Supplier Portal (CSP), budgets, AP holds, match exceptions, contracts, and payment. Use when the connected spend system is Coupa, or the user mentions Coupa, a requisition or PR, an approval chain or force-approve, a PO issued to a supplier, the CSP or SAN, a supplier invoice, an AP hold or match exception, a budget hard block or soft warning, an overbill or short-pay, voiding an invoice, disputing one back to a supplier, a PO amendment, or a supplier on hold."
---

# Coupa - operating it safely

Coupa runs business spend management (requisition to payment) as the system of record for committed
spend. The thing that makes Coupa dangerous is simple: its writes commit money and reach outside the
company. Approving a requisition commits the spend and can issue a purchase order to a supplier the same
second; approving a supplier invoice creates the payable and authorizes the payment. You are not editing
a draft, you are moving money and sending orders to third parties. This skill gives the judgment to
classify Coupa actions so the harness can gate them, plus the edge states and recovery paths that decide
whether a mistake is fixable.

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
Connector is Coupa and the work is procure-to-pay, budgets, supplier records, invoices, or holds. When NOT:
- The connected S2P suite is SAP Ariba, not Coupa (requisitions, guided buying, Ariba Network) -> `sap-ariba`.
- The ERP ledger posting behind an approved invoice: the AP subledger post, the payment run, GL account
  determination, period close -> `sap-fi`. Coupa approves and exports the invoice; the ERP posts and pays it.
- Payment execution itself is downstream of invoice approval and out of scope here: Coupa Pay virtual-card
  issuance, digital settlement, and stop-payment, and the ERP payment run. This skill covers committing the
  payable and authorizing export, not the disbursement -> `sap-fi` for the ERP-side pay and stop-pay.
  Do not improvise Coupa Pay settlement actions from this skill.
- Physical warehouse receiving (bins, putaway) as opposed to the receipt record that clears a match -> the WMS skill.

## Object & state model (reason about state, not nouns)
- **Requisition (PR)** - a *request* to buy, from a hosted catalog, a punchout, or a free-form (non-catalog)
  line. States: draft -> pending approval (submitted) -> approved -> becomes a PO. Off-path: returned (sent
  back to requester), rejected, withdrawn (by requester before final approval), cancelled, buyer hold.
  Reversible only while in draft; once it enters the chain, edits re-route it.
- **Approval chain** - the ordered list of approvers a requisition, invoice, or budget must clear. Driven by
  rules on amount, commodity, account/cost-center coding, and budget. Each approver can approve, reject,
  return, add an approver/watcher, or (with permission) approve on behalf.
- **Purchase Order (PO)** - the *commitment* to the supplier, generated from an approved requisition
  (auto-issued, or released by a buyer where auto-PO is off; do not assume every approval transmits instantly).
  States: issued (transmitted) -> acknowledged (if supplier ack is on) -> (partially) received -> (partially)
  invoiced -> closed. Off-path: buyer hold, cancelled, soft-closed (reopenable), error. Once issued it is contractual.
- **Receipt** - the record that goods/services arrived. Quantity-based or amount-based. Posting a receipt is
  the physical-control leg of the match; it is what lets a matched invoice pass to payment.
- **Invoice** - the supplier's bill, submitted through the CSP, SAN, cXML, or OCR (InvoiceSmash), or entered
  by a buyer on the supplier's behalf. States: draft -> pending approval -> approved -> exported for payment.
  Off-path: on hold, disputed (bounced to supplier), voided. (An approver may *abstain* on the chain; that is
  an approval-step outcome, not an invoice state.) Approving the invoice is the money event.
- **Match** - 2-way (PO + invoice), 3-way (PO + receipt + invoice), or 4-way (adds inspection). Within
  tolerance it can auto-approve; outside tolerance it raises an exception that puts the invoice on hold.
- **Budget** - a period-scoped spend limit checked at requisition/PO. Three outcomes: within budget, soft
  warning (proceeds once acknowledged), hard block (submission refused). See `references/matching-holds-and-budgets.md`.
- **Supplier** - the master record with remit-to and banking. A supplier can be active, pending onboarding,
  or on hold/inactive; a held supplier cannot transact until released.

## Vocabulary that bites
- **Requisition vs PO** - the requisition approval, not a later PO step, is where spend is committed; the PO
  is generated after and is usually auto-issued. Do not wait for a "PO approval" that will not come.
- **Approval chain** - the routing is dynamic. Coding (account, cost center, commodity) and amount decide who
  approves, so changing a line's coding re-routes it to different approvers, not a cosmetic edit.
- **Force-approve / approve on behalf** - an admin pushing an approval through, skipping the intended
  approvers. It is recorded but it bypasses the control; treat it as an authority action, never a shortcut.
- **Budget hard block vs soft warning** - they look almost identical on screen. A soft warning still lets the
  spend proceed; only a hard block stops it. Assuming a warning halted the buy is the classic mistake.
- **AP hold / match exception** - a hold (price, quantity, receipt, tax, tolerance) parks an invoice so it
  cannot pay. Releasing the hold is what authorizes payment despite the mismatch.
- **CSP (Coupa Supplier Portal)** - where suppliers submit invoices and flip POs to invoices. A CSP invoice is
  the supplier's legal document; the buyer disputes or rejects it, and generally cannot silently edit its amounts.
- **SAN (Supplier Actionable Notifications)** - email actions for suppliers not on the CSP; they acknowledge a
  PO or create an invoice straight from the email. Same commitments, different channel.
- **Compliant invoicing** - Coupa's legal e-invoicing for country tax mandates (rules are country- and
  deployment-specific). A non-compliant invoice cannot be legally processed in a mandated country; editing tax
  on it can break the compliance record. Read the invoice's compliance status rather than assuming it is fine.
- **Tolerance** - the allowed price/quantity variance below which a match auto-clears with no human. Raising a
  tolerance pre-authorizes spend up to that variance.
- **Void vs delete vs dispute** - a draft invoice is deleted (clean); an approved or exported invoice is only
  voided (permanent, often needs a credit note); a disputed invoice is returned to the supplier but still exists.
- **Contract-backed** - a catalog line backed by a contract enforces the contracted price; changing that price
  breaks compliance and is usually blocked or flagged.
- **Soft close vs close (PO)** - a soft-closed PO can be reopened; a close is meant to be final and can strand
  open receipts or invoices against it.

## Operations: read / write / destructive
Classify every operation family by what it does to state and to money. Kinds of action, not tool names.

| Class | Coupa operation families | Gate | Why |
|---|---|---|---|
| **Read** | view requisition / PO / invoice / receipt / supplier / budget / contract; list pending approvals; match status; hold reasons; budget remaining; audit trail; add a comment/watcher (watcher/comment writes are stateless for financial purposes, read-classified by convention) | always pass | no state change; read before every write and re-read at execute |
| **Write (reversible)** | create or edit a requisition in draft; save a supplier or budget draft; create a draft (buyer-entered) invoice before submit; withdraw one's own requisition before final approval | gate one at a time | uncommitted request; low blast radius; cleanly undoable |
| **Write (committing)** | submit a requisition; approve a requisition (commits spend, usually auto-issues the PO); issue a PO to a supplier; amend an issued PO (a quantity/price/line change re-transmits the order and can change committed spend); re-open a soft-closed PO (re-activates committed spend); post a receipt (clears the physical match leg); approve an invoice (creates the payable, authorizes payment/export); dispute an invoice or reject a supplier-submitted one (returns it to the supplier, stops the pay clock); create or apply a credit memo (commits a payable reduction, mis-nets if it references the wrong document); acknowledge a budget soft warning to proceed | gate + human approve | binds money, sends an order to a third party, or lets an invoice pay |
| **Destructive / irreversible** | force-approve / approve on behalf past a chain; release an AP hold or override a match exception; cancel an issued PO that has receipts/invoices; void an approved or exported invoice; lift a supplier hold or transact with a held supplier; override a budget hard block; change a contract-backed price; hard-close a PO with open invoices; raise a tolerance to auto-pass a variance | hard gate + named approver + re-read | authorizes payment despite a flag, bypasses a control, or leaves a permanent trail that cannot be cleanly undone |

**Committing vs destructive on approval:** approving a requisition or invoice is committing, not destructive,
because the approval chain itself is the named-approver gate. Force-approving *past* the chain removes that gate
and reclassifies the same action to destructive.

**Buyer draft vs supplier (CSP) invoice:** a buyer-entered *draft* invoice is a reversible write, edit or delete
it freely before submit. A supplier-submitted CSP or SAN invoice is the supplier's legal document: you cannot
silently edit its amounts or tax, only dispute or reject it back. Same object, different write class by origin.

**Prohibited circumvention (not operations to perform, patterns to block):** splitting a requisition or PO into
smaller pieces to drop each under an approval or budget threshold; renumbering an invoice to slip past duplicate
detection; re-coding a line only to route around a specific approver; swapping a held supplier for an active one
to force an order through. These are not Coupa features to use; they are audit-flagged workarounds. If a request
amounts to one of these, stop and route to the real approver.

### Reclassification: an in-chain edit is a re-route
Editing a requisition or invoice after it has entered the approval chain is NOT a benign edit. A material
change (amount, coding, quantity, supplier) resets or re-routes the chain: approvers who already approved must
re-approve, so an "innocent" edit can silently un-approve everyone and restart the flow. Treat any in-chain
edit as a committing re-route, and re-read the approval state after it.

Universal rules to teach: read before every write and **re-read at execute** (approval, hold, budget, and
match state all drift); never bypass an approval chain (Coupa's approval-by-amount checks total spend); a hold,
a budget hard block, or a supplier hold means **stop**; a country compliance/tax rule is a wall.

## Gotchas that bite (the real set, as causal chains)
1. **Approving the invoice IS the money event.** It creates the accounts-payable liability and authorizes
   payment (Coupa Pay) or export to the ERP. It is not a review step; it commits the company to pay.
2. **Approving the requisition commits the spend and issues the PO.** With auto-PO on, the order transmits to
   the supplier the moment the last approver clicks approve; there is no separate PO gate to catch it.
3. **Editing a requisition after partial approval resets the chain.** Approvers who already signed off must
   re-approve; a material change re-routes from the start, so an edit meant to "just fix a line" un-approves everyone.
4. **A budget soft warning looks like a block but isn't.** The requisition proceeds once the warning is
   acknowledged. Only a hard block refuses submission; treating the two the same lets over-budget spend through.
5. **Force-approve / approve on behalf bypasses the intended approvers.** It is logged with who forced it, but
   the control is skipped; it is an authority violation unless the delegation is explicit and named.
6. **Cancelling an issued PO that has receipts or invoices is not a clean recall.** The supplier may already be
   shipping, open receipts/invoices orphan, and a downstream invoice may block. Cancel != un-send.
7. **Releasing an AP hold authorizes payment despite the mismatch.** The hold (price, quantity, receipt, tax,
   tolerance) exists because something did not reconcile; overriding it pushes an unreconciled invoice to pay.
8. **A CSP invoice is the supplier's legal document.** The buyer generally cannot silently change its line
   amounts or tax; you dispute or reject it back. Editing amounts on it can break the e-invoicing compliance record.
9. **An approved or exported invoice can only be voided, never deleted.** Once past approval the trail is
   permanent; correcting it means a void plus, often, a supplier credit note, not an in-place edit.
10. **Disputing an invoice stops the clock but does not remove it.** The invoice bounces to the supplier and
    still exists; it can be resubmitted, so a dispute is a hold on payment, not a resolution.
11. **Splitting a requisition to stay under a threshold is circumvention.** Approval-by-amount is designed to
    catch total spend; two half-size requisitions to dodge the approver or a budget block is auditable, same as PO-splitting.
12. **A supplier on hold or mid-onboarding cannot be transacted.** Forcing a PO or invoice to a held supplier
    (missing banking, failed sanctions/compliance screening) sends money or orders to an unvetted party.
13. **Receiving triggers the match, so a wrong receipt can auto-pay.** Over-receiving or receiving the wrong
    quantity can clear a match hold and let an invoice pay for goods not actually received. Receipt is a financial control.
14. **Amount-based vs quantity-based receiving mis-match if crossed.** Services POs receive by amount; entering
    a quantity receipt on an amount-based line (or vice versa) breaks the match and can overpay.
15. **Coding drives routing, so changing an account re-routes approval.** Reassigning cost center, account, or
    commodity on a requisition sends it to different approvers and a different budget; it is an approval re-route, not a field tweak.
16. **Tolerance auto-approval means no human sees it.** An invoice within tolerance can pass with no reviewer;
    raising a tolerance (say to $500 variance) pre-authorizes every future invoice up to that gap.
17. **Duplicate detection keys on supplier + invoice number.** Resubmitting the same bill under a tweaked
    number slips past the duplicate check and can double-pay the supplier.
18. **Hard-closing a PO with an open invoice can strand that invoice.** The invoice may then be unable to
    match or pay; soft-close (reopenable) is the recoverable choice, a hard close is not.
19. **Budgets are period-scoped, so the commitment date matters.** Spend posts against the period of the PO /
    need-by date; posting to the wrong period distorts the remaining budget both months.
20. **Once exported to the ERP, Coupa no longer controls the payment.** Changing or stopping a payment after
    export is an ERP action, not a Coupa one -> `sap-fi`. Voiding in Coupa alone does not stop an already-exported pay.
21. **A contract-backed line is priced by the contract, not the requisition.** Editing the price on a
    contract-backed item breaks compliance; Coupa blocks or flags it depending on setup. The correct path is a
    contract amendment (its own approval), not an override on the requisition line.
22. **Amending an issued PO re-transmits it and can move committed spend.** Changing quantity, price, or a line
    on a PO already sent to the supplier is not an internal edit; it re-issues the order and can re-trigger
    approval if it crosses a threshold. Treat a PO amendment as committing, not a correction.

## Edge states & special cases
Each breaks naive "approved means done" logic. Deep match/hold/budget mechanics: `references/matching-holds-and-budgets.md`.

| Edge state | Naive assumption | Actual behavior | Correct action |
|---|---|---|---|
| **Partial receipt / partial invoice** | PO is fully open or fully done | remaining qty/amount still open; a later receipt can change whether an existing invoice passes | re-read the match before releasing any invoice against a partial PO |
| **Match exception on hold** | someone reviewing it means it will pay | it will not pay until resolved or overridden (destructive), not by being looked at | fix the source (receipt/price) or route the override to an approver |
| **Non-compliant e-invoice** | a data cleanup | Coupa flags a compliance status per the legal/tax framework configured for the supplier's country; in a mandated country a non-compliant invoice cannot be legally processed | read the compliance status; have the supplier reissue a compliant invoice, do not edit tax to force it |
| **Credit memo / credit note** | a general reduction | reduces the payable only if it references the right invoice/PO, else it mis-nets | apply against the specific referenced document |
| **Disputed invoice** | resolved / removed | open, owned by the supplier, off the pay clock but still present and resubmittable | track it as open, not closed |
| **Multi-currency** | any variance is an overbill | Coupa converts to a common currency at its configured exchange rate, then applies tolerance; a flagged gap can be an FX-rate difference | check the applied rate before treating a variance as an overbill |
| **Supplier not on CSP (SAN only)** | portal state to read | supplier acts through email notifications; no portal record to poll | expect confirmations via the SAN channel, not the CSP |
| **Prepayment / milestone PO** | 3-way match applies | pays against milestones/advances before full receipt; the standard 3-way does not fit cleanly | do not force a receipt-based match on a milestone line |

## Recovery patterns (can it be undone, and what cannot)

| Action | Undoable? | How / what cannot be restored |
|---|---|---|
| **Requisition (in chain)** | yes, before final approval | *withdraw* returns it to the requester cleanly; *cancel* is a distinct terminal action (more audit weight); after approval + PO issue neither applies, you must cancel the PO |
| **Issued PO** | no clean undo | cancel is a new action: supplier was notified, receipts/invoices may exist, the trail stays; may be too late if goods shipped |
| **Draft invoice** | yes | delete removes it cleanly |
| **Disputed invoice** | reversible via the supplier | it sits with the supplier off the pay clock; a resubmission comes back as a fresh document that re-enters approval and re-matches, so re-check the match rather than trusting the earlier read |
| **Approved / exported invoice** | no | void only (permanent), usually needs a supplier credit note; there is no un-approve, you void and re-enter |
| **AP hold release** | no, once exported | after release + export the payment proceeds; recover through the ERP stop-pay or a credit note, not in Coupa |
| **Force-approve** | no | permanent in the audit trail; cannot be un-forced; the only recovery is voiding the resulting invoice/PO downstream |
| **Budget consumption** | no direct undo | adjustments are new entries; you cannot un-consume budget without cancelling the underlying requisition/PO |

## Guardrails
- Read the requisition/PO/invoice and its approval, hold, budget, supplier, and match state before acting; re-read at execute.
- Never bypass an approval chain (force-approve / approve on behalf) without explicit named authority, and never
  split a requisition or PO to slip under an approval or budget threshold.
- An AP hold, a match exception, a budget hard block, or a supplier hold means stop. Releasing or overriding one
  authorizes payment or an order despite the flag; route it to the named approver, do not clear it to move on.
- Treat approving an invoice as committing to pay, and approving a requisition as committing the spend and
  sending the order. Size a void/cancel/hold-release before acting: it is a money or compliance event, not a correction.
- Do not edit a supplier-submitted (CSP) invoice's amounts or tax; dispute or reject it back to the supplier instead.
- For anything in the destructive row: named approver, re-read of live state, and a logged reason.

## References (load on demand)
- `references/matching-holds-and-budgets.md` - the 2/3/4-way match and tolerance mechanics, the AP hold types
  and how each clears, and budget hard-block vs soft-warning behavior with period scoping.
- `references/approvals-and-contracts.md` - how the approval chain routes (amount, coding, commodity), delegation
  and force-approve, and contract-backed pricing (what Coupa blocks vs flags and the amendment path). Read when a
  workflow re-routes approvals, hits a delegate/escalation, or touches a contract-priced line.
