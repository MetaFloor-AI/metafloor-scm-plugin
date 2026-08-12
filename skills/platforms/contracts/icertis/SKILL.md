---
name: icertis
description: "Icertis Contract Intelligence (ICI) - safe operation of contract lifecycle management: contract requests, authoring from templates and the clause library, negotiation and redlining, deviation approvals, delegation-of-authority sign-off, e-signature and execution, obligation and milestone management, amendments, renewals, and termination. Use when the connected CLM is Icertis (ICI), or the user names Icertis-specific things: an ICI agreement or contract record, the clause library or a fallback clause, a deviation or deviation approval, an association, DiscoverAI bulk import, or ICI for Word; and, once Icertis is the system in play, when they mention a template, an amendment or renewal, an auto-renewal or evergreen notice window, an obligation or commitment, third-party paper, a signature-authority matrix or DoA, sending a contract out for signature, or executing or terminating a contract."
---

# Icertis (ICI) - operating it safely

Icertis Contract Intelligence runs the contract lifecycle (request to renewal) as the system of record for
what the company is legally committed to. The thing that makes Icertis dangerous is simple: its committing
writes bind the company to a third party and its attributes drive everything downstream. Executing an
agreement is a legal act you cannot take back; the effective date, expiration date, auto-renew flag, and
value you record are what fire obligations, renewal alerts, and spend or revenue commitments. You are not
saving a document, you are binding the company and arming the clocks that govern it. This skill gives the
judgment to classify Icertis actions so the harness can gate them, plus the edge states and recovery paths
that decide whether a mistake is fixable.

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
Connector is Icertis and the work is contract authoring, negotiation, approval, execution, obligations, or
renewal/termination. When NOT:
- The procurement transaction the contract governs - a requisition, PO issued to a supplier, receipt, or
  supplier invoice -> `coupa` or `sap-ariba`. Icertis holds the master or contract that
  sets the price and terms; the PO and invoice live in the procurement suite. Do not create or amend a PO here.
- The e-signature engine's own mechanics - envelope routing, signer authentication, signing order, voiding
  or correcting an envelope mid-flight -> `docusign-clm`. Icertis orchestrates the send and records
  the executed result; the signature capture and envelope state belong to the signing platform.
- The ERP ledger behind an executed contract - AP posting, the payment run, revenue recognition, period
  close -> `sap-fi`. Icertis governs the commitment; the ERP posts and pays against it.
- The sell-side opportunity, quote, or account value that precedes a sales contract -> the CRM skill.
  Icertis holds the resulting agreement, not the pipeline.

## Object & state model (reason about state, not nouns)
- **Contract Request (intake)** - the request to create an agreement, typed as buy-side (procurement),
  sell-side (sales/revenue), or corporate (NDA, employment, IP). A request is a draft ask, not a contract;
  it is reversible until it becomes an agreement in authoring.
- **Agreement** - Icertis's word for the contract record and the object you operate on. It carries a
  contract type, an origin (template or third-party paper), attributes, clauses, associations, obligations,
  and a status. Typical status flow (configured per contract type): request -> in authoring -> under
  negotiation -> pending approval -> approved -> out for signature -> executed / in effect -> then amended,
  renewed, expired, or terminated. Reversible while pre-approval; binding once executed.
- **Template** - a pre-approved agreement skeleton with standard clauses and rules. Authoring from a template
  is the governed fast path; the clauses in it already carry approval.
- **Clause & Clause Library** - the central repository of approved clauses. Each has a preferred/standard
  version plus fallback or alternate positions and its own attributes. Anything not from the library, or an
  edit to a library clause's language, is a deviation.
- **Attributes** - the metadata on an agreement (parties, signing legal entity, effective date, expiration
  date, contract value and currency, notice period, auto-renew flag, governing law). Attributes are not
  cosmetic: the rules engine, obligations, and alerts all read them.
- **Association** - a child object linked to a parent agreement: an amendment, renewal, extension,
  termination letter, change order, or a SOW under an MSA. A contract is a family, not a single document.
- **Obligation** - a tracked post-signature commitment (a delivery, an SLA, a rebate, a payment term, a
  reporting duty). It has an owner, a due date or milestone, and a status: open -> fulfilled, or breached.
- **Commitment** - a financial obligation: a contract value, a spend or revenue commitment, a take-or-pay
  floor or minimum-volume band. It drives downstream spend/revenue tracking and penalty exposure.
- **Deviation** - a recorded departure from approved template or clause-library language; it routes to a
  deviation approval. **Rules** - the engine that selects clauses, routes approvals, creates obligations,
  and raises alerts based on attributes and deviations. See `references/lifecycle-authoring-approvals.md`.

## Vocabulary that bites
- **Agreement** - the contract record, not a Word file. Editing its clauses or attributes changes what the
  company is bound to and what the rules engine does next; it is not a benign document edit.
- **Contract type (buy / sell / corporate)** - decides the template, the approval chain, the DoA thresholds,
  the obligations created, and which downstream system it syncs to. Setting or changing the type is a
  routing decision, not a label.
- **Deviation** - the single most important negotiation concept. Using a non-library clause or editing
  standard language is a deviation that triggers a deviation approval; pushing it through unapproved ships an
  unvetted legal position into a binding contract.
- **Fallback position** - a pre-approved alternate the library offers when the counterparty rejects the
  standard clause. It is not "free" - reaching for a deeper fallback can still require the approval the rules
  set for that position.
- **Third-party paper** - a contract on the counterparty's template. It has no pre-approved clauses, so every
  term is effectively a deviation; it needs full clause extraction and risk review, not a template fast path.
- **Association** - a child agreement bound to a parent. An amendment does not replace the original; it
  associates to it, and the effective terms are the parent as changed by the amendment.
- **Attribute** - a metadata field that arms a clock. A wrong expiration date or notice period silently
  mis-fires a renewal alert or lets an auto-renewal lapse; a wrong value mis-states a commitment.
- **Obligation** - a commitment that does not self-fulfill. It sits open until an owner marks it done; an
  unmonitored obligation becomes a breach with financial or legal exposure.
- **Delegation of Authority (DoA) / signature-authority matrix** - who may approve or sign at what value or
  risk. DoA is the authority policy; the signature-authority matrix is how Icertis implements it. The
  approval workflow enforces both; signing above authority binds the company without the right signer.
- **Executed / execution** - the signature event that legally binds. It is irreversible in the sense that you
  cannot un-sign; you can only amend or terminate, each a new binding instrument.
- **Effective date vs execution date** - when the contract legally starts vs when it was signed. Obligations
  and renewal windows key off the effective and expiration dates, not the signature date.
- **Evergreen / auto-renewal** - a clause that renews the contract for another term unless notice is given
  inside the notice window (counted back from expiration). Miss the window and the renewal is legally locked.

## Operations: read / write / destructive
Classify every operation family by what it does to legal and obligation state. Kinds of action, not tool names.

| Class | Icertis operation families | Gate | Why |
|---|---|---|---|
| **Read** | view an agreement, its attributes, clauses, deviations, associations, obligations, and audit trail; search or report across the portfolio; view approval status and the assigned approvers; view the clause library and templates; obligation and milestone dashboards; expiration and renewal reports; view a DiscoverAI extraction | always pass | no state change; read before every write and re-read at execute |
| **Write (reversible)** | create a contract request; author a draft agreement from a template; edit attributes or clauses on a draft (pre-approval, pre-execution); change the contract type on a draft (re-runs the rules - new template, approval chain, DoA tier, obligations); save negotiation redlines and versions; assign an obligation owner on a not-yet-active agreement; delete or withdraw one's own draft request or draft agreement before approval | gate one at a time | an uncommitted draft ask; nothing legally binding yet; cleanly reversible |
| **Write (committing)** | submit an agreement for approval; approve within one's DoA; insert a deviation or a non-library clause (routes a deviation approval); send an agreement out for signature; recall or void the signing envelope before the counterparty signs (stops the send and re-opens the version; the envelope void itself is a signing-platform action -> `docusign-clm`, not a simple reversible undo); mark a live obligation fulfilled (can release a downstream payment or close an alert, so it must carry evidence); create an amendment, renewal, extension, or SOW association; change a live attribute that drives an obligation, renewal, or commitment (expiration date, notice period, value, auto-renew flag); reassign the owner of a live obligation | gate + human approve | binds the company, changes an obligation or commitment, or arms/re-arms a legal clock |
| **Destructive / irreversible** | execute or sign an agreement (legally binds the company; cannot be un-executed); terminate an executed agreement (a notice-bound legal act); override or bypass an approval or deviation gate; sign above DoA, or split a contract's value across pieces to drop each under a DoA or approval threshold; send the wrong (un-agreed) version to signature; let an auto-renewal notice window lapse; bulk-activate DiscoverAI-imported agreements without verifying the extracted key terms; run a bulk mutation across many agreements at once (bulk status change, bulk obligation reassignment, bulk amendment) | hard gate + named approver + re-read | permanent legal trail; binds or ends a commitment; one wrong attribute becomes hundreds; the unapproved position or missed clock cannot be cleanly undone |

**Reclassification: a post-approval edit is a re-approval.** Approval in Icertis is per version. A material
change after approval - a late redline, a clause edit, an attribute that crosses a DoA tier - invalidates the
prior approval and must re-route. Sending a post-approval-edited version to signature ships terms nobody
approved. Treat any edit after approval as a committing re-route and re-read the approval state.

**Committing vs destructive on approval.** Approving an agreement within your DoA is committing, not
destructive, because the approval chain and the authority matrix are themselves the named-approver gate.
Overriding the chain, or approving/signing above your DoA, removes that gate and reclassifies the same action
to destructive.

**A draft attribute or clause edit still re-runs the rules.** Editing an attribute or clause on a draft is
reversible, but it re-evaluates the rules engine and can swap clauses in or out and re-route the approval
chain. Re-read the deviation set and approval state after any attribute change; it is not a silent field edit.

**Editing an attribute on an executed agreement.** Some attributes on an executed agreement are locked
read-only by configuration; a genuine change to a term the counterparty is bound to is an amendment, not a
field edit. Whether the platform allows the edit directly or forces it through the amendment path, the safe
classification holds: a change to a live term is at least committing, and a change to a binding term is the
amendment path (a new approval plus signature).

**Prohibited circumvention (patterns to block, not operations to perform):** splitting one contract into
smaller agreements so each falls under a DoA or approval threshold; swapping a deviating clause back to
standard on screen after approval but signing the deviating version; back-dating an effective date to change
which obligations or renewal windows apply; marking an obligation fulfilled without evidence to clear an
alert. These are audit-flagged workarounds. If a request amounts to one, stop and route to the named approver.

Universal rules to teach: read before every write and **re-read at execute** - and re-read a concrete set:
the status, the current version, the deviation set, the approval state, any legal hold, and the key
attributes (effective date, expiration date, notice window, auto-renew flag, contract value, and the signing
legal entity). Never bypass the approval or deviation gate and never sign above DoA; a pending approval, an
open deviation, or a legal hold means **stop**; the notice window on an auto-renewal or termination is a wall
- it counts back from a date and does not wait.

## Gotchas that bite (the real set, as causal chains)
1. **Executing an agreement legally binds the company, and there is no un-execute.** Signature is the money
   and law event, not a save. A mistake in an executed contract is corrected only by an amendment or a
   termination, each its own approval plus signature; the original stays in the trail forever.
2. **A deviation from an approved clause or template is not a benign edit.** Editing standard language or
   inserting a non-library clause triggers a deviation approval; pushing it through unapproved puts an
   unvetted legal position into a binding contract.
3. **Approval is per version, so a post-approval edit un-approves it.** A late redline or a clause change
   after sign-off invalidates the approval and must re-route; sending the edited version to signature binds
   the company to terms nobody approved.
4. **Attributes arm clocks.** A wrong expiration date, notice period, or auto-renew flag silently mis-fires
   a renewal alert or lets an auto-renewal lapse. The metadata is the mechanism, not a label.
5. **An evergreen or auto-renewal clause renews silently if you miss the notice window.** The window counts
   back from expiration (often 60 or 90 days). Let it pass and the company is legally locked into another
   full term; there is no system undo, only a negotiation with the counterparty.
6. **An amendment changes obligations and is itself a binding instrument.** It associates to the parent
   rather than replacing it; the effective terms are the original as modified, so the live obligation set is
   parent plus amendment combined. It needs its own approval and signature.
7. **Third-party paper has no pre-approved clauses.** On the counterparty's template every term is effectively
   a deviation. Running it through the template fast path skips the clause-by-clause risk review it needs and
   can bind the company to an unreviewed liability cap or indemnity.
8. **Obligations do not self-fulfill.** An obligation created from a contract term sits open until an owner
   marks it done. A missed delivery, SLA, rebate, or reporting duty is a breach with financial or legal
   exposure; an unowned obligation is an unmonitored one.
9. **The clause library's fallback positions are not free.** Reaching for a deeper fallback when the
   counterparty pushes back can still require the approval the rules attach to that position; a fallback in
   the library is a pre-approved option, not a bypass of the approval it carries.
10. **Terms inherit down a master-child hierarchy.** A SOW or change order under an MSA is governed by the
    MSA's liability cap, penalties, and termination terms. Reading only the child misses the terms that
    actually bind; the obligation lives across the family.
11. **Terminating an executed contract is a notice-bound legal act.** Termination for convenience and for
    cause differ, and each carries a notice requirement; terminating without the contractual notice can
    itself breach the contract you are trying to end.
12. **The signing legal entity is who is bound.** A parent company and a subsidiary are different legal
    persons; recording the wrong counterparty entity or your own wrong signing entity mis-binds the contract
    and can make it unenforceable or bind the wrong balance sheet.
13. **DiscoverAI extractions carry confidence, not certainty.** Bulk-imported legacy or third-party contracts
    have AI-extracted dates, values, and clauses; a renewal alert or obligation built on a low-confidence
    extraction fires on bad data. Verify key terms (effective/expiration dates, value, liability, renewal)
    before obligations run on them.
14. **Sending the wrong version to signature binds the wrong terms.** During negotiation many versions exist;
    executing an earlier redline instead of the final agreed one binds the company to un-agreed language.
    Confirm the final approved version before it goes out for signature.
15. **Changing an attribute mid-authoring re-runs the rules engine.** Altering the contract type, region, or
    value re-evaluates the rules and can swap clauses in or out and re-route the approval chain. It is a
    routing change, not a field tweak.
16. **A wrong contract value mis-states a commitment and can trip a penalty.** The value drives spend/revenue
    tracking and any take-or-pay or minimum-volume floor; understating or overstating it mis-reports the
    commitment and can breach or under-count a volume band.
17. **Splitting a contract to duck a DoA threshold is circumvention.** Two smaller agreements to keep each
    under an approval or signature-authority tier is the same authority violation with extra steps, and it is
    auditable, the same as PO-splitting in procurement.
18. **A draft or pending agreement is not enforceable.** Treating an unsigned or in-approval agreement as
    active over-promises; obligations and rights bind only after execution. Read the status before relying on
    a term.
19. **Effective date is not signature date.** Obligations and renewal windows key off the effective and
    expiration dates, so back-dating or mis-recording the effective date shifts every downstream clock and
    can retroactively create or miss an obligation.
20. **Reassigning an obligation owner does not reset its due date.** The milestone or SLA clock keeps running
    through a handoff; a reassignment that drops the ball leaves the obligation unmonitored until it breaches.
21. **A renewal starts a new term but the terms may reset.** Pricing, volume commitments, and SLAs can change
    at renewal; assuming last term's obligations carry forward unchanged mis-tracks the new term. Read the
    renewed agreement's obligations, do not copy the prior term's.
22. **A legal hold or a pending deviation means stop.** A hold is placed for a reason (litigation, dispute,
    compliance review); executing, amending, or terminating around it destroys the state the hold protects.
23. **A send or sync can fail after the action but before confirmation.** If a send-for-signature, an
    execution confirmation, or a downstream sync to the procurement suite or ERP drops mid-operation, the
    agreement can be left in a partial state. Re-read the live status and execution state before retrying; a
    blind retry can double-send an envelope or double-create an association. The confirmed executed record is
    the source of truth, not the send.
24. **A bulk mutation multiplies one mistake across the portfolio.** A bulk status change, bulk obligation
    reassignment, or bulk amendment applies one wrong attribute or owner to every agreement in the set. One
    wrong effective date is bad; two hundred is a portfolio-wide clock error. Treat any bulk mutation as
    destructive: named approver, a verified sample first, and a re-read of the affected set.

## Edge states & special cases
Each breaks naive "one contract, one document" logic. Deep mechanics: `references/lifecycle-authoring-approvals.md`
and `references/obligations-associations-renewals.md`.

| Edge state | Naive assumption | Actual behavior | Correct action |
|---|---|---|---|
| **Third-party paper** | author from a template | no pre-approved clauses; every term is a deviation | extract clauses and risk-review each; do not use the template fast path |
| **Master-child (MSA -> SOW)** | the SOW is the whole contract | the MSA governs caps, penalties, and termination for its children | read the full family; the binding terms may live in the parent |
| **Amendment** | it replaces the original | it associates to and modifies the parent; effective terms are the combination | read parent plus amendment together for the live obligation set |
| **Evergreen / auto-renewal** | it expires on its own | it renews unless notice is given inside the window (counted back from expiration) | track the notice window, not just the expiration date |
| **DiscoverAI bulk import** | extracted metadata is fact | AI-extracted dates/values/clauses carry a confidence score and can be wrong | verify key terms before obligations or alerts run on them |
| **Multi-entity signatory** | one company signs | the specific legal entity signing is who is bound; parent and subsidiary differ | confirm the signing legal entity on both sides before execution |
| **Offline / wet-signature execution** | only e-sign binds | a manually signed contract uploaded and marked executed still legally binds | treat the recorded executed status as the legal fact regardless of channel |
| **Governing-law / jurisdiction** | boilerplate | it determines which law governs and can pull in mandatory local terms | read the governing-law attribute before applying or comparing terms |
| **Concurrent operations** | one action at a time | an amendment in-flight while a renewal window opens, or two users editing one agreement, can produce version conflicts or a missed clock | serialize the action; re-read the version and the live clocks before committing |

## Recovery patterns (can it be undone, and what cannot)

| Action | Undoable? | How / what cannot be restored |
|---|---|---|
| **Draft request or draft agreement** | yes, before approval | withdraw or delete cleanly; nothing binding was created |
| **Executed agreement** | no | cannot be un-executed; correct only via an amendment (new approval + signature) or termination (notice-bound); the original stays permanently in the trail |
| **Wrong attribute on an active contract** | editable, but effects are not | you can correct the date or value, but if it already fired an obligation, alert, or renewal, the downstream event already happened; correcting it does not un-send it |
| **Missed auto-renewal notice window** | no | the new term is legally in effect; recovery is a negotiation or a new termination, not a system undo |
| **Deviation pushed through / approval bypassed** | no | the unapproved position now sits in a binding contract and stays in the audit trail; recovery is an amendment, not an un-approve |
| **Terminated contract** | no clean undo | termination is a new legal state; reinstatement (if the contract allows it) or a new agreement, not an un-terminate |
| **Obligation marked fulfilled in error** | correctable in-system | the status can be reset, but any downstream action taken on the false "fulfilled" (a released payment, a closed alert) is its own recovery |
| **Wrong contract type selected at creation** | yes before authoring settles, costly after | the type drives the template, approval chain, DoA tier, and obligations; re-selecting it re-runs the rules and re-authors the draft. Once executed the type is baked in - only a new agreement with the correct type corrects it, and the wrong-type executed agreement stays in the trail |
| **Wrong version sent to signature (before the counterparty signs)** | yes, if caught in the window | recall or void the signing envelope before the counterparty signs, then re-send the correct approved version; the envelope-void action lives in the signing platform -> `docusign-clm`. Once executed, only an amendment fixes it |
| **Operation interrupted by a system error (send, execution confirmation, or ERP/procurement sync drops)** | re-read, do not blind-retry | the operation may be partially applied; re-read the live status, version, and execution state before retrying, because a blind retry can double-send an envelope or double-create an association. The confirmed record, not the send, is the source of truth |

## Guardrails
- Read the agreement, its status, version, attributes, deviations, approval state, associations, and legal
  holds before acting; re-read at execute - the negotiated version and approval state drift during negotiation.
- Never send to signature or execute a version that is not the final approved one, and treat any edit after
  approval as invalidating that approval and requiring a re-route.
- Never bypass the approval or deviation gate and never sign above DoA; never split a contract's value to
  drop under a DoA or approval threshold.
- Treat execution as legally binding: confirm the counterparty and your own signing legal entity, the
  effective and expiration dates, the auto-renew flag and its notice window, and the governing terms before signing.
- A pending approval, an open deviation, a legal hold, or a not-yet-executed status means stop; obligations
  and rights bind only after execution, and a renewal or termination notice window is a wall that counts back from a date.
- Circumvention dressed as a normal edit (splitting value to duck a DoA tier, swapping a clause back to
  standard on screen but signing the deviating version, back-dating an effective date, marking an obligation
  fulfilled without evidence) is detailed in the operations section; treat any such request as a stop-and-route
  to the named approver, not an edit to perform.
- For anything in the destructive row (execute, terminate, override, sign above DoA, bulk-activate imports,
  bulk mutation): named approver, re-read of live state, and a logged reason.

## References (load on demand)
- `references/lifecycle-authoring-approvals.md` - the full lifecycle states, authoring from templates and the
  clause library, the deviation and fallback mechanics, the rules engine, negotiation and version control,
  and approval routing with delegation of authority and the signature-authority matrix. Read when a workflow
  authors, negotiates, deviates, routes an approval, or sends for signature.
- `references/obligations-associations-renewals.md` - the obligation lifecycle (creation from terms,
  ownership, milestones, breach), commitment tracking, the association types (amendment, renewal, extension,
  termination, change order, SOW), the master-child hierarchy and term inheritance, and renewal, expiry, and
  termination mechanics. Read when a workflow manages obligations, amends or renews, or terminates.
