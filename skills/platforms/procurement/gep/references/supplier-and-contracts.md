# GEP SMART supplier management and contracts

Read when a task changes a supplier's status, checks a risk hold, consumes a contract, edits a contract
price, or works a blanket order. The rule under all of it: onboarded is not qualified, a hold means stop,
setting a status can unblock spend platform-wide, and a contract-backed price is the contract's, not the
requisition's.

## Contents
- Supplier statuses
- The unified supplier record
- Risk / compliance holds
- Performance
- Contracts: authoring vs compliance
- Obligations and accumulators
- Blanket orders and releases

## Supplier statuses
GEP Supplier Management tracks three distinct, non-implied statuses:
- **Onboarding / registration** - invited -> onboarded on the GEP supplier portal. An onboarded supplier has
  a profile; that is all.
- **Qualification** - qualified **for a specific category** (via questionnaires, documents, certifications). A
  supplier qualified for one category is not qualified for another. Onboarded != qualified.
- **Segmentation / preferred** - a strategic status (preferred, strategic, approved) that can steer or unblock spend.
Setting qualification or segmentation status is a **governance write**: it can open the door to spend across
the platform. Self-qualifying a supplier to clear your own PO is a control violation, not a step.

## The unified supplier record
Because GEP SMART is one native platform on a single data model, the supplier record is shared by sourcing,
contracts, and transactions. Editing or deactivating a supplier is never a local edit to one screen: it
ripples into sourcing eligibility, contract validity, and whether open POs/invoices can process.
Deactivating/disqualifying a supplier can strand in-flight transactions - it is destructive.

## Risk / compliance holds
A supplier risk view pulls third-party and internal data (financial, sanctions/compliance, ESG, cyber). A
**risk/compliance hold** means the supplier cannot transact. Lifting a hold - or awarding/contracting/PO'ing
a held, unqualified, or un-onboarded supplier - sends money to an unvetted party. That is destructive; route
it, do not clear it to move on. A **Fraud/Anomaly Detection Agent** flag on a transaction is a related stop.

## Performance
Performance scorecards rate suppliers on delivery, quality, responsiveness. They inform sourcing and
segmentation; they are read/analysis, not a gate on payment.

## Contracts: authoring vs compliance
- **Authoring** - drafting the agreement: clauses (from a clause library), obligations, milestones, approval,
  and signature. GEP's own Contract Management does this; a dedicated CLM (Icertis/DocuSign) does it elsewhere
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
unified data model as the requisitions/POs that consume them, so a consumption or a limit breach is visible in
real time - and coding around it (wrong contract, split spend) is auditable.

## Blanket orders and releases
A **blanket order** is a standing PO (often contract-backed) against which **releases / call-offs** draw down
over time. A release commits spend like a PO and can still hit budget and approval controls - the blanket
does not pre-clear every draw. A blanket release is not a schedule line or a plan. Cancelling a blanket that
has releases against it is destructive: the releases, receipts, and invoices already drawn stay in the trail.
