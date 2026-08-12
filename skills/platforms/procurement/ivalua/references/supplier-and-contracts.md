# Ivalua supplier management (SIM) and contracts

Read when a task changes a supplier's status, checks a Risk Center hold, consumes a contract, or edits a
contract price. The rule under all of it: registered is not qualified, a hold means stop, setting a status can
unblock spend, and a contract-backed price is the contract's, not the requisition's.

## Contents
- Supplier statuses (SIM)
- Supplier 360 and the Golden Record
- Risk Center holds
- Performance
- Contracts: authoring vs compliance
- Obligations and accumulators

## Supplier statuses (SIM)
Supplier Information Management tracks three distinct, non-implied statuses:
- **Registration** - invited -> registered on the Ivalua supplier portal. A registered supplier has an
  onboarded profile; that is all.
- **Qualification** - qualified **for a specific category** (via questionnaires, documents, certifications). A
  supplier qualified for one category is not qualified for another. Registered != qualified.
- **Segmentation / preferred** - a strategic status (preferred, strategic, approved) that can steer or unblock spend.
Setting qualification or segmentation status is a **governance write**: it can open the door to spend across
the platform. Self-qualifying a supplier to clear your own PO is a control violation, not a step.

## Supplier 360 and the Golden Record
**Supplier 360** is the single view of a supplier, including sub-tiers, across the source-to-pay cycle. The
**Golden Record** is the master profile the whole unified data model trusts. Because the model is unified,
activating or editing the Golden Record ripples into sourcing eligibility, contract validity, and whether open
POs/invoices can process - it is never a local edit. Activating the Golden Record is a governance write that
can unblock spend everywhere.

## Risk Center holds
The **Risk Center** pulls third-party and internal data (financial, sanctions/compliance, ESG, cyber) into a
supplier risk view. A **risk/compliance hold** means the supplier cannot transact. Lifting a hold - or
awarding/contracting/PO'ing a held, unqualified, or unregistered supplier - sends money to an unvetted party.
That is destructive; route it, do not clear it to move on.

## Performance
Performance scorecards rate suppliers on delivery, quality, responsiveness. They inform sourcing and
segmentation; they are read/analysis, not a gate on payment.

## Contracts: authoring vs compliance
- **Authoring** - drafting the agreement: clauses (from a clause library), obligations, milestones, approval,
  and signature. Ivalua's own Contracts module does this; a dedicated CLM (Icertis/DocuSign) does it elsewhere
  -> that skill. Award terms can auto-populate a contract.
- **Contract compliance** - the spend-gating side. A contract carries **committed vs consumed** amounts and
  **min/max release** limits (accumulators), plus **obligations** (deliverables/terms to track).
  - Coding a requisition/PO to the **wrong contract** misstates compliance.
  - Exceeding a committed/max limit is a breach - the accumulator blocks or flags it at submission; surface it,
    do not push through or re-code to another contract to dodge the limit.
  - A **contract-backed price** is the contract's, not the requisition's. Editing that price on a line breaks
    compliance; the correct path is a contract amendment (its own approval), not a line override.
  - Cancelling/terminating a contract with **consumed** amounts is destructive (open commitments, downstream invoices).

## Obligations and accumulators
An **obligation** is a tracked commitment inside a contract (a deliverable, an SLA, a rebate condition). An
**accumulator** is the running tally of spend against the contract's committed/min/max. Both live in the same
data model as the requisitions/POs that consume them, so a consumption or a limit breach is visible in real
time - and coding around it (wrong contract, split spend) is auditable.
