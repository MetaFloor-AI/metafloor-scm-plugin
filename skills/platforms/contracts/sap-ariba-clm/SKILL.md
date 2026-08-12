---
name: sap-ariba-clm
description: "SAP Ariba Contracts (CLM within SAP Ariba) - safe operation of the contract lifecycle - contract requests and workspaces, authoring the main agreement from templates and the clause library, contract terms and line items, approval and signature tasks, e-signature via DocuSign, publishing and amendments, expiration and renewal, and compliance tracking. Use when the connected CLM is SAP Ariba Contracts, or the user names Ariba CLM things - a contract workspace (CW), contract terms or contract line items, a contract template, the clause library or a fallback or conditional clause, an assembled main agreement, a deviation report, a review or approval or negotiation or signature task, publishing or republishing a contract, an amendment type, a renewal or termination amendment, term type (fixed, auto renew, evergreen, perpetual), an expiration notification, a contract hierarchy or sub-agreement, contract compliance accumulators, or sending a contract to DocuSign for signature."
---

# SAP Ariba Contracts (CLM) - operating it safely

SAP Ariba Contracts runs the contract lifecycle inside the SAP Ariba suite as the system of record for what
the company is committed to on a contract. Two things make it dangerous, and they are different from a
document CLM. First, the object you operate is a **contract workspace** - a project container that bundles the
contract terms, the priced line items, the assembled legal agreement, the workflow tasks, and the team - not a
single document; changing any part changes what goes live. Second, a workspace becomes binding through **two
distinct committing acts**: the **signature** (the legal execution, usually through the DocuSign integration)
and the **publish** (the Ariba act that activates the workspace, stamps a version, arms the expiration and
renewal clocks, and pushes the contract line items into contract compliance and, if integrated, the ERP). A
signed-but-unpublished contract is not active in the system; a published contract with the wrong line items or
an unreviewed clause deviation is live and releasing spend against bad terms. This skill gives the judgment to
classify Ariba Contracts actions so the harness can gate them, plus the edge states and recovery paths that
decide whether a mistake is fixable.

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
Connector is SAP Ariba and the work is contract authoring, terms and line items, approval and signature,
publishing, amendments, or renewal/termination inside Ariba Contracts. When NOT:
- The **procurement transaction** the contract governs - a requisition, a PO issued against the contract, a
  receipt, a supplier invoice, a sourcing event or award, or the **contract compliance accumulator being
  consumed** by requisitions and POs -> `sap-ariba`. This skill authors the contract terms and line
  items and publishes them; the requisition/PO that releases against the accumulator lives in the spend suite.
- **Icertis (ICI)** is the CLM in play, not Ariba -> `icertis`. Different vendor, different object
  model (Icertis operates a single "agreement" record and binds on execution alone; Ariba operates a workspace
  and also has a distinct publish act). Do not apply Ariba workspace/publish mechanics to Icertis or the reverse.
- The **e-signature engine's own mechanics** - envelope routing, signer authentication, signing order, voiding
  or correcting an envelope mid-flight -> `docusign-clm`. Ariba's signature task orchestrates the send
  and records the executed result; the signature capture and envelope state belong to the signing platform.
- The **ERP ledger** behind an executed contract - AP posting, the payment run, revenue recognition, period
  close -> `sap-fi`. Ariba governs the commitment and the compliance ceiling; the ERP posts and pays.

## Object & state model (reason about state, not nouns)
- **Contract Request** - an intake form a requester submits to ask for a contract. On approval it creates a
  contract workspace. A request is a draft ask, not a contract; reversible until the workspace is created.
- **Contract Workspace (CW)** - the container project and the object you operate on. Typed as **procurement**
  (buy-side), **sales** (sell-side), or **internal** (no counterparty). It holds the contract terms, line
  items, the main agreement, tasks, team, and ancillary documents. Status flow: **Draft** (authoring) ->
  **Published** (active, version stamped) -> **Amending** (a new-version draft in progress) -> back to
  **Published**, and eventually **Expired** or **Closed**; **On Hold** pauses it. Reversible while Draft;
  binding once published and signed.
- **Contract Terms document** - the metadata document on the workspace: contract type, **contract amount**
  (the compliance ceiling), **effective date**, **expiration date**, **term type**, hierarchy (parent), region,
  commodity, and the supplier/customer. Not cosmetic - compliance, expiration notifications, and renewal all
  read these fields.
- **Contract Line Items** - the priced items on a contract (item, price, quantity, terms); procurement
  contracts carry buy-side items, sales contracts carry revenue-side items. When the workspace is published,
  procurement line items become the released contract that **contract compliance** meters spend against.
- **Main Agreement (assembled document)** - the legal contract, assembled in Microsoft Word from the template
  and the clause library through the Ariba Word add-in. This is the legal instrument that gets signed.
- **Template (contract template)** - a pre-approved workspace blueprint: it defines which documents, tasks,
  team roles, conditions, and clauses the workspace starts with. Choosing a template is a routing decision.
- **Clause & Clause Library** - the central store of approved clauses; each has a standard version plus
  **fallback** alternates and **conditional** variants included by rule. See `references/workspace-authoring-approvals.md`.
- **Task** - a workflow unit inside the workspace: **review**, **approval**, **negotiation**, **signature**,
  **notification**, or to-do. Tasks are defined by the template with conditions and dependencies; approvals run
  serial or parallel.
- **Amendment & version** - a published workspace is not edited in place; it is **amended**, which opens a new
  version (1.0 -> 1.1 -> 2.0) and re-publishes. The amendment **type** sets the blast radius (below).
- **Contract hierarchy** - a workspace can be a **sub-agreement** under a **master**; the sub inherits the
  master's terms unless it overrides them. See `references/terms-compliance-amendments.md`.

## Vocabulary that bites
- **Contract workspace** - a project container, not a document. Editing its terms, line items, or assembled
  agreement changes what publishes and what binds; it is not a single-file edit.
- **Publish** - the Ariba act that makes a workspace active: it stamps a version, arms the expiration and
  renewal clocks, and pushes the line items into contract compliance and (if integrated) the ERP. It is
  **separate from signature**. Republish is how any later change goes live. This is the concept most unlike a
  document CLM - do not conflate publish with sign.
- **Contract Terms** - the metadata document whose effective date, expiration date, term type, and contract
  amount drive compliance, notifications, and renewal. A wrong field here mis-arms a clock or a ceiling.
- **Contract Line Items** - priced rows on a contract (buy-side items on a procurement contract, revenue-side
  on a sales contract) that meter compliance once published. Wrong price/amount lets spend release against wrong
  terms. Distinct from the legal text of the main agreement; validate line items on sell-side workspaces too.
- **Term Type** - the field that decides how the contract ends: **Fixed** (expires on the date), **Auto Renew**
  (renews for a set number of terms unless notice is given), **Evergreen** (renews indefinitely until
  terminated), **Perpetual** (no expiry). The available options are tenant-configured - some tenants expose
  Perpetual, others model an indefinite contract as Evergreen with no expiry. Setting the wrong term type
  silently renews or expires the contract.
- **Assembled document / Main Agreement** - the Word contract built from the template plus clauses. Editing an
  assembled clause's language creates a **deviation**.
- **Deviation** - a departure from the standard clause-library language, flagged in the **deviation report**.
  Publishing with unreviewed deviations ships un-vetted legal terms into a binding contract.
- **Fallback / conditional clause** - a fallback is a pre-approved alternate for when the counterparty rejects
  the standard clause; conditional clauses include or drop based on the template's conditions read from the
  terms. A fallback is a pre-approved option, not a bypass of the approval its depth may still require.
- **Amendment type** - chosen when amending a published workspace: **Administrative** (metadata/team, no term
  change, usually no re-signature), **Amendment** (changes terms, re-approval plus re-signature), **Renewal**
  (extends the expiration), **Termination** (ends the contract). The type sets what re-routes.
- **Signature task / DocuSign integration** - the task that sends the main agreement for e-signature through
  DocuSign (or a manual/offline channel). Ariba records the signed result; the envelope mechanics belong to the
  signing platform -> `docusign-clm`.
- **Contract compliance / compliance accumulator** - contract compliance is the capability that meters spend
  against a published contract; the **compliance accumulator** is the meter itself, tracking released spend
  against the line items up to the contract amount. Authored here; consumed by requisitions/POs in `sap-ariba`.
- **Expiration notification** - the alert Ariba fires ahead of the expiration date (configured intervals). The
  decision window on an Auto Renew/Evergreen counts back from expiration, earlier than the date itself.

## Operations: read / write / destructive
Classify every operation family by what it does to legal, version, and compliance state. Kinds of action, not
tool names.

| Class | Ariba Contracts operation families | Gate | Why |
|---|---|---|---|
| **Read** | view a workspace, its contract terms, line items, assembled main agreement, clauses, deviation report, tasks, team, approval status, version history, and audit trail; view the clause library and templates; expiration and renewal reports; contract compliance / accumulator status; search across the contract portfolio | always pass | no state change; read before every write and re-read at execute |
| **Write (reversible)** | create a contract request; create a workspace from a template; author or assemble the main agreement on a **Draft** workspace; edit contract terms or line items pre-publish; add clauses, fallbacks, or ancillary docs to a draft; save negotiation redlines and versions; add or change team members; complete a review task | gate one at a time | an uncommitted draft ask; nothing published, signed, or metered yet; cleanly reversible |
| **Write (committing)** | submit an approval task / approve within one's authority; insert a deviation or a non-library clause (routes a deviation review); route/send the **signature task** to DocuSign; **publish** the agreed, reviewed version of a workspace - stamps a version, arms the expiration/renewal clocks, pushes line items to compliance/ERP (publishing the wrong version or line items is destructive, see below); create an **Amendment**, **Renewal**, or **Administrative** amendment and re-publish; change a live Contract Terms field that drives a clock or ceiling (expiration date, term type, contract amount, auto-renew) through an amendment | gate + human approve | binds the company, activates the contract, changes a term/ceiling, or arms/re-arms a legal clock |
| **Destructive / irreversible** | **sign/execute** the main agreement (legally binds; cannot be un-signed); **Terminate** amendment (ends an active contract; notice-bound); override or bypass an approval or deviation gate; sign or approve above signature authority, or split a contract across workspaces to drop each under an approval/authority threshold; **publish an un-agreed or unsigned assembled version, or the wrong line items**; let an Auto Renew/Evergreen contract's notice window lapse; bulk-import line items or run a mass update across many workspaces; delete/close a published workspace out from under its downstream releases | hard gate + named approver + re-read | permanent legal and version trail; binds or ends a commitment; live line items release spend; the missed clock or unapproved position cannot be cleanly undone |

**Publish and sign are two gates, not one.** Publishing activates the workspace, stamps a version, and pushes
line items into compliance; signing legally executes the agreement. A contract needs both, and configurations
differ on the order (some sign the assembled document then publish; some publish the version snapshot then sign
it). The safety rule is not a fixed sequence but a match: the version that is published into compliance must be
the version that was agreed and signed. Never activate (publish) an unsigned or un-agreed assembled document
into compliance, and confirm the signed state and the published version are the same agreed version before
relying on the contract.

**Publish is committing for the right content, destructive for the wrong content.** Publishing the agreed,
signed version is committing; publishing the wrong version or the wrong line items is destructive, because live
spend releases against bad terms through the compliance accumulator and cannot be un-spent.

**A published workspace cannot be edited in place - every change is an amendment.** There is no field edit on a
published contract. Any correction opens a new version through an amendment whose type (Administrative /
Amendment / Renewal / Termination) sets whether approval and signature re-route. Treat any post-publish change
as a committing (or, for Termination, destructive) re-route, and re-read the version and status first.

**A post-approval edit un-approves the version.** Approval tasks approve the current draft. A material change
after sign-off (a late redline, a clause edit, a term crossing an authority tier) invalidates that approval and
must re-route; publishing the edited version pushes terms nobody approved. Re-read the approval state after any edit.

**Changing a term re-assembles clauses.** Contract type, region, or amount are read by the template conditions;
changing one can pull conditional clauses in or out of the assembled main agreement and re-route the approval
chain. Re-assemble and re-review the deviation report after a term change - it is not a silent field tweak.

**Amendment type is not cosmetic.** Choosing **Administrative** (which normally skips re-signature) to slip a
real term or price change past re-approval and re-signature is circumvention, not a shortcut. The type must
match the actual change:

| If the change is | Amendment type | Re-routes |
|---|---|---|
| team members or workspace metadata, no term change | Administrative | usually no re-approval or re-signature |
| any term, price, clause, or line-item change | Amendment | re-approval + re-signature |
| extending the term / expiration | Renewal | re-approval + re-signature; re-read the renewed line items |
| ending the contract early | Termination | notice-bound; approval + records a termination (destructive) |

**Recalling a signature task before the counterparty signs is a reversible undo of the send, not a new
commitment.** It stops the send and re-opens the version. Gate it only because the window can close if the
counterparty signs first; the envelope void itself is a signing-platform action -> `docusign-clm`.
Once signed, only an amendment fixes it.

**Prohibited circumvention (patterns to block, not operations to perform):** splitting one contract across
multiple workspaces so each falls under an approval or signature-authority threshold; publishing the standard
clause version on screen but signing the deviating assembled document; mis-typing an amendment as
Administrative to dodge re-signature; back-dating the effective date to shift which obligations or renewal
windows apply; overstating the contract amount to remove a compliance ceiling. These are audit-flagged. If a
request amounts to one, stop and route to the named approver.

Universal rules to teach: read before every write and **re-read at execute** - and re-read a concrete set: the
workspace status, the current version, the deviation report, the approval and signature state, any On Hold, and
the key Contract Terms (effective date, expiration date, term type, contract amount, auto-renew). Never bypass
an approval or deviation gate and never sign above authority; a pending approval, an open deviation, or an On
Hold means **stop**; the notice window on an Auto Renew/Evergreen or a termination is a wall - it counts back
from a date and does not wait.

## Gotchas that bite (the real set, as causal chains)
1. **Publish is the activation event, and it is not the same as signature.** Publishing stamps a version, arms
   the expiration and renewal clocks, and pushes the line items into contract compliance and the ERP. Publish an
   unsigned or un-agreed version and the system treats it as active while the legal execution is missing or wrong.
2. **A published workspace cannot be edited - only amended.** There is no in-place fix; every correction is a new
   version through an amendment that re-routes approval and signature per its type. The "quick edit" is a full
   amendment cycle, and the wrong version stays in the trail.
3. **Signing legally binds the company, and there is no un-sign.** Execution through the DocuSign task (or an
   uploaded wet signature) is the legal act. A mistake in a signed contract is corrected only by an amendment or a
   Termination, each its own approval plus signature.
4. **Term Type decides the ending, and the failure modes are opposite.** Evergreen renews indefinitely until
   terminated; Auto Renew renews for the set number of terms unless notice is given inside the window; Fixed
   expires; Perpetual never expires. The wrong term type silently renews a contract you meant to end, or expires
   one you meant to keep.
5. **Expiration notifications fire off the Contract Terms expiration date.** A wrong expiration date mis-times
   every renewal alert and can let an Auto Renew/Evergreen lapse into another full term. The notice window counts
   back from expiration, so the decision date is earlier than the date on the contract.
6. **Contract line items meter compliance once published.** Publish a wrong price, quantity, or contract amount
   and requisitions/POs release against wrong terms; the compliance accumulator consumes to the published
   ceiling. The consumption lives in `sap-ariba`, but the bad ceiling is set here.
7. **Editing an assembled clause creates a deviation, and publishing with unreviewed deviations ships un-vetted
   language.** The deviation report flags every departure from the standard library clause; a struck liability
   cap or indemnity that publishes without review binds the company to an unreviewed position.
8. **Fallback clauses are pre-approved options, not bypasses.** Reaching for a deeper fallback when the
   counterparty pushes back can still route the approval its depth requires; a fallback in the library is not a
   way around the review it carries.
9. **Conditional clauses swing on a term change.** Altering contract type, region, or amount re-evaluates the
   template conditions and can pull clauses in or out of the assembled main agreement and re-route the approval.
   Re-assemble and re-read the deviation report after any term change.
10. **The template is the routing decision, not a label.** It sets the documents, tasks, team, conditions, and
    starting clauses. The wrong template gives the wrong approval chain, the wrong clauses, and missing required
    documents - baked into the workspace from creation.
11. **A denied approval task sends the workspace back and un-approves the version.** Approval is per version;
    reworking after a denial invalidates prior sign-offs on that version, and approving above authority removes
    the gate the chain is there to be.
12. **Amendment type sets the blast radius.** Administrative (metadata/team, usually no re-sign), Amendment (term
    change, re-approval plus re-signature), Renewal (extends expiration), Termination (ends it). Mis-typing a real
    change as Administrative to skip re-signature is circumvention, auditable.
13. **Terminating is a Termination amendment and a notice-bound legal act.** It ends the contract and stops new
    compliance releases, but it does not unwind requisitions/POs already released against it - those continue
    their own lifecycle in the spend suite (`sap-ariba`), so size that in-flight exposure first. The
    workspace and its versions stay in the trail. Terminating without the contractual notice (convenience vs
    cause differ) can itself breach the contract you are ending; there is no un-terminate.
14. **A sub-agreement inherits the master's terms.** Reading only the sub misses the liability cap, penalties,
    governing law, and termination terms that live in the master. Amending the master can change every sub under it.
15. **Version history is permanent.** Each publish and amendment is a version (1.0, 1.1, 2.0); you cannot delete
    one. A wrong publish is corrected by a new amendment, not by editing or removing the version.
16. **The signature task orchestrates DocuSign but does not own the envelope.** Ariba sends and records the
    result; envelope routing, signer authentication, signing order, and voiding a sent envelope are DocuSign
    actions -> `docusign-clm`. Voiding mid-flight re-opens the Ariba signature task; whether it
    re-opens automatically or needs a manual sync depends on the integration, so re-read the live task state
    rather than assume it re-opened.
17. **An offline/wet signature still binds.** A paper-signed agreement uploaded and the signature task completed
    is legally executed; the recorded signed status is the legal fact regardless of channel, so do not treat it as
    less binding than an e-signed one.
18. **A contract request or a Draft workspace is not a contract.** Treating an in-request or unpublished,
    unsigned workspace as active over-promises; rights and compliance releases exist only after publish and
    signature. Read the status before relying on a term.
19. **Effective date is not publish date or signature date.** Compliance and obligation windows key off the
    effective date in Contract Terms. Back-dating or mis-recording it shifts every downstream clock and can
    retroactively create or miss an obligation.
20. **Contract amount is a control, not a label.** It caps the compliance accumulator; understating it blocks
    valid releases, overstating it removes the ceiling that stops over-release against the contract.
21. **Splitting a contract across workspaces to duck an authority tier is circumvention.** Two smaller workspaces
    to keep each under an approval or signature-authority threshold is the same authority violation with extra
    steps, and it is auditable, the same as PO-splitting in procurement.
22. **A publish or ERP sync can fail after the action but before confirmation.** If the publish, the signature
    return, or the downstream sync to the spend suite or ERP drops mid-operation, the workspace can be left in a
    partial state. Re-read the live status, version, and publish state before retrying; a blind retry can
    double-publish a version or double-push line items. The confirmed published record is the source of truth.
23. **A bulk import or mass update multiplies one mistake across the portfolio.** A bulk line-item import or a
    mass field update applies one wrong price, date, or amount to every affected row or contract. Treat any bulk
    mutation as destructive: named approver, a verified sample first, and a re-read of the affected set.
24. **On Hold means stop.** A workspace put on hold (dispute, legal review, compliance check) should not be
    published, amended, or signed around; the hold protects the state it was placed to protect.
25. **An edit made to the assembled document outside the Ariba Word add-in is invisible to deviation tracking.**
    The deviation report only flags changes made through the add-in against the standard library clause; a direct
    Word edit that bypasses it publishes unvetted language with no flag. Treat any out-of-add-in edit as an
    unreviewed deviation by default and re-review the language before publishing.
26. **The main-agreement signature may not cover ancillary documents.** Schedules, exhibits, or ancillary
    agreements attached to the workspace can need their own execution; assuming the main-agreement signature
    binds them leaves them unsigned and the workspace incompletely executed. Confirm which documents the
    signature task actually covers.

## Edge states & special cases
Each breaks naive "one contract, one document" logic. Deep mechanics: `references/workspace-authoring-approvals.md`
and `references/terms-compliance-amendments.md`.

| Edge state | Naive assumption | Actual behavior | Correct action |
|---|---|---|---|
| **Publish vs signature** | one act binds the contract | publish activates and meters; signature legally executes; they are separate acts and the order varies by configuration | confirm the published version and the signed version are the same agreed version; check both states |
| **Sales or internal contract type** | it behaves like a procurement contract | a sales contract carries revenue-side line items and no P2P downstream; an internal contract has no counterparty and no compliance accumulator | do not assume buy-side line items, an accumulator, or an ERP release; confirm what the contract type actually drives downstream |
| **Uploaded third-party paper** | assemble from a template | the counterparty's document has no library clauses, so every term is effectively a deviation | do a clause-by-clause risk review, not the template/clause-library fast path |
| **Master / sub-agreement** | the sub is the whole contract | the master governs caps, penalties, and termination for its subs | read the full hierarchy; the binding terms may live in the master |
| **Amendment** | it replaces the original | it opens a new version and modifies the parent; effective terms are the combination | pick the correct amendment type; re-approval and re-signature follow from it |
| **Workspace in Amending status** | the contract is frozen while amending | the prior published version stays live and spend keeps releasing against its line items until the amendment re-publishes | expect releases against the prior version (v1.0) while v1.1 is negotiated; the change takes effect only on re-publish |
| **Term Type = Auto Renew / Evergreen** | it expires on its own | it renews unless notice is given inside the window (counted back from expiration) | track the notice window, not just the expiration date |
| **No-line-item contract** | compliance meters it anyway | contract compliance only fires when priced line items are published | if spend should be metered, publish the line items; else it is text-only |
| **Standalone vs integrated Ariba Contracts** | publish always syncs to the ERP | line-item/compliance sync to the ERP happens only when integrated | confirm the integration before assuming a downstream push occurred |
| **DocuSign vs manual signature** | only e-sign binds | a manually signed, uploaded agreement with the signature task done still binds | treat the recorded signed status as the legal fact regardless of channel |
| **Concurrent access / in-flight amendment or signature** | one actor, one action at a time | Ariba locks a workspace during an in-flight amendment or signature task, so a second amendment or publish is blocked; an amendment opening as a renewal window opens can also miss a clock or conflict versions | serialize committing actions; re-read the version, the lock/status, and the live clocks before publishing or signing |

## Recovery patterns (can it be undone, and what cannot)

| Action | Undoable? | How / what cannot be restored |
|---|---|---|
| **Contract request or Draft workspace** | yes, before publish | withdraw or delete cleanly; nothing was published, signed, or metered. In some tenants an audit-log entry persists after withdrawal, so "clean" means no binding effect, not necessarily no trace |
| **Approval task denied (sent back for rework)** | yes, reworkable | rework the version and re-route approval; prior sign-offs on that version are invalidated and must re-approve; nothing binds if it was pre-publish |
| **Published workspace** | no in-place edit | cannot be edited; correct only by an amendment (new version, re-routes per type); the prior version stays in the trail |
| **Signed / executed agreement** | no | cannot be un-signed; correct only via an amendment (new approval + signature) or a Termination (notice-bound); the original stays permanently |
| **Wrong publish (bad line items or version)** | not a clean undo | do not assume an un-publish; correct with an amendment that re-publishes the right version. Any spend already released against the bad line items is its own recovery |
| **Missed Auto Renew / Evergreen notice window** | no | the new term is legally in effect; recovery is a negotiation or a Termination, not a system undo |
| **Deviation published unreviewed / approval bypassed** | no | the unapproved position now sits in a binding contract and stays in the audit trail; recovery is an amendment, not an un-approve |
| **Terminated contract** | no clean undo | Termination is a new legal state; reinstatement (if the contract allows) or a new workspace, not an un-terminate |
| **Wrong version sent to signature (before the counterparty signs)** | yes, if caught in the window | recall/void the DocuSign envelope before signing, then re-send the correct agreed version; the envelope void lives in the signing platform -> `docusign-clm`. Once signed, only an amendment fixes it |
| **Operation interrupted (publish, signature return, or ERP sync drops)** | re-read, do not blind-retry | the operation may be partially applied; re-read the live status, version, and publish state first, because a blind retry can double-publish a version or double-push line items. If the re-read shows a partial state (version stamped but line items not pushed), escalate to a named approver to decide roll-forward vs amend rather than retrying blind. The confirmed record, not the send, is the truth |

## Guardrails
- Read the workspace status, current version, contract terms, line items, deviation report, approval and
  signature state, and any On Hold before acting; re-read at execute - versions and approval state drift during
  authoring and negotiation.
- Treat publish and signature as two committing gates on the same workspace: the version published into
  compliance must be the version that was agreed and signed (the order varies by configuration). Never publish
  an unsigned or un-agreed assembled document or the wrong line items, and confirm both states match.
- A published workspace has no in-place edit; make every change an amendment with the correct type, and let
  Administrative mean no term change (never use it to skip re-signature on a real change).
- Never bypass an approval or deviation gate and never sign above authority; never split a contract across
  workspaces to drop under an approval or signature-authority threshold.
- Confirm the counterparty and signing entity, the effective and expiration dates, the term type and its notice
  window, and the contract amount before signing and publishing. A pending approval, an open deviation, or an On
  Hold means stop; an Auto Renew/Evergreen or termination notice window is a wall that counts back from a date.
- For anything in the destructive row (sign, Terminate, override, sign above authority, publish an un-agreed
  version, bulk import/update): named approver, re-read of live state, and a logged reason.

## References (load on demand)
- `references/workspace-authoring-approvals.md` - the workspace lifecycle and statuses, authoring the main
  agreement from the template and clause library, standard/fallback/conditional clauses and the deviation report,
  the task types and approval routing with signature authority, and the signature/publish sequence. Read when a
  workflow creates a workspace, authors, deviates, routes an approval, sends for signature, or publishes.
- `references/terms-compliance-amendments.md` - the Contract Terms fields and term types, contract line items and
  the compliance accumulator, the contract hierarchy and term inheritance, and the amendment types with renewal,
  expiration, and termination mechanics. Read when a workflow sets terms/line items, amends, renews, or terminates.
