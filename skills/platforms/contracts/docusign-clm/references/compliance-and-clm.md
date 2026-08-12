# DocuSign compliance, legal sufficiency, retention, and the CLM module

Deep material behind the SKILL.md. Read when a workflow deals with the Certificate of Completion, legal
sufficiency (which signature is valid where), retention / purge, transferable records, or the DocuSign CLM
(formerly SpringCM) contract lifecycle. The read / write / destructive judgment lives in SKILL.md.

## Contents
- Certificate of Completion and the audit trail
- Legal frameworks and signature levels (ESIGN / UETA, eIDAS SES / AES / QES)
- Electronic-records consent
- Authoritative copy and transferable records
- Retention and purge
- DocuSign CLM object model
- DocuSign CLM operations (read / write / committing)
- CLM gotchas that bite
- CLM workflow failure and recovery
- Where CLM hands off to eSignature and to other systems

## Certificate of Completion and the audit trail
- On completion DocuSign generates a **Certificate of Completion** and attaches it to the executed PDF. It
  records, per recipient: the name and email, the **authentication method** used, IP addresses, and the
  timestamps for each event (sent, viewed / delivered, signed), plus acceptance of the **electronic-record and
  signature disclosure**.
- The certificate is **tamper-evident and cannot be edited**; it is the evidence that makes the signature
  defensible in a dispute.
- **Keep the certificate with the signed pages.** Distributing only the signature pages, or storing the PDF
  without the certificate, throws away the proof of who signed, when, and under what identity check.
- The completed PDF is also **digitally sealed** (tamper-evident); any change after completion invalidates the
  seal, which is how downstream parties detect alteration.

## Legal frameworks and signature levels
Electronic signatures are legally valid in most jurisdictions, but **which** signature is sufficient depends on
the jurisdiction and the transaction.

| Framework | Region | What it establishes |
|---|---|---|
| **ESIGN Act** + **UETA** | US (federal + state) | an electronic signature and record are as valid as wet ink if the parties consented to transact electronically; some documents are excluded (wills, certain notices) |
| **eIDAS** | EU / EEA | three tiers of electronic signature with rising legal weight and identity assurance |

eIDAS tiers (map a use case to the tier its jurisdiction / contract requires):

| Tier | DocuSign term | Identity assurance | When it is required |
|---|---|---|---|
| **SES** (simple / standard) | standard electronic signature | basic (email, maybe access code) | most ordinary commercial agreements |
| **AES** (advanced) | uniquely linked to the signer, signer-controlled, tamper-detecting | strong (usually IDV) | higher-value or regulated agreements |
| **QES** (qualified) | AES + a qualified certificate from a trusted service provider + qualified device | highest; legal equivalent of a handwritten signature EU-wide | where law mandates a qualified signature |

Danger: a technically **completed** envelope signed with SES can still be **legally insufficient** for a
contract type or country that requires AES or QES. "Completed in DocuSign" is not the same as "valid for this
purpose." Match the signature level to the requirement before sending.

## Electronic-records consent
- Under ESIGN / UETA the signer must be given the chance to **consent to do business electronically** (the
  "Electronic Record and Signature Disclosure"), and that consent is logged on the certificate.
- If the disclosure is suppressed or the signer never accepted it, the electronic signature can be
  **challenged** as not validly consented. Do not disable the disclosure to shorten the signing flow for an
  external party.

## Authoritative copy and transferable records
- For a **transferable record** (a negotiable instrument such as a loan note under UETA / ESIGN), there must be a
  single **authoritative copy** that is the controlling original; all other copies are marked as copies.
- DocuSign manages this via an **authoritative copy / electronic-original vault** (eOriginal-style custody). A
  plain **downloaded PDF is a copy, not the authoritative original** - relying on it as the original breaks the
  chain of the negotiable instrument and can make it unenforceable as a note.
- If a workflow deals with loans, leases, or other negotiable instruments, route the executed record into the
  authoritative-copy flow, not a shared drive.

## Retention and purge
- An account **retention / purge** policy deletes documents and their field data a set period after completion
  (e.g., 30 or 90 days), for privacy / data-minimization reasons.
- Once **purged**, the documents are **gone from DocuSign** and cannot be recovered. Keep an independent
  retained copy of the completed PDF **and** its Certificate of Completion before the purge window.
- Purge is destructive: it permanently removes the record, so it is a named-approver, logged action.

## DocuSign CLM object model
DocuSign CLM (formerly SpringCM) is DocuSign's own contract lifecycle product - covered here, not deferred to
the Icertis or Ariba skills.

- **Repository / folders** - documents are stored in a folder hierarchy with **versioning**; each save can be a
  new version, and access is controlled by folder security.
- **Document / agreement** - the contract record, with metadata (agreement type, parties, dates, value) that
  drives search, obligations, and reporting.
- **Workflow** - a visual, step-based automation that routes a document: generate it, request approval, send it
  to **eSignature**, file the executed copy, and start obligation tracking. A workflow step can itself be a
  committing act (it can send an envelope).
- **Contract generation (doc gen)** - assembles an agreement from a template plus **merge data** (often from a
  CRM such as Salesforce). A wrong merge value bakes a wrong price / party / term into the generated contract.
- **Clause library** - the store of approved clauses used in generation; editing standard language is a
  deviation that should route for review (the deviation / approval **authority** judgment for a full CLM suite
  is detailed for Icertis in `icertis` and for Ariba in `sap-ariba-clm`).
- **Obligation management** - tracked post-signature commitments (deliverables, SLAs, renewal dates) with owners
  and due dates; an unowned obligation is an unmonitored one, and a wrong extracted date fires an alert on bad data.

## DocuSign CLM operations (read / write / committing)
- **Read** - view a document, its versions, metadata, workflow state, and obligations; search the repository.
- **Write (reversible)** - generate a draft contract, edit an unrouted document, save a version, configure a
  workflow, assign an obligation owner on a not-yet-active agreement.
- **Write (committing)** - launch a workflow that routes for approval or **sends to eSignature**; publish a
  generated contract into the repository as the record; mark a live obligation fulfilled (can release a
  downstream action); push metadata to an integrated CRM / ERP.
- **Destructive / irreversible** - delete or purge a stored contract; bulk-mutate metadata or obligations across
  many agreements; anything that sends to eSignature and completes (that execution is governed by the
  eSignature engine and SKILL.md, and cannot be un-completed).

## CLM gotchas that bite (causal chains)
1. **Wrong merge data bakes a wrong term into the generated contract.** Doc gen pulls price, party, dates, and
   quantities from the merge source (often a CRM). A stale or wrong source value is generated into the
   agreement and, once sent and signed, is legally binding - the merge error becomes a contract error. Verify
   the generated draft against the source before it routes.
2. **Obligation extraction errors propagate to downstream alerts and actions.** Obligations captured from
   contract terms (renewal dates, SLAs, volume floors) drive reminders and, sometimes, downstream releases. A
   wrong extracted date fires a renewal alert on bad data or misses a real one; verify key obligation fields
   before they run.
3. **Editing a library clause in a generated draft is a deviation.** Changing standard clause language should
   route for review; publishing or sending the deviating draft unreviewed ships an un-vetted legal position.
   The full deviation / approval-authority judgment for a CLM suite is in `icertis` (Icertis) and
   `sap-ariba-clm` (Ariba); the same principle applies to DocuSign CLM generation.
4. **A new document version does not re-notify or re-route on its own.** Saving a new version in the repository
   updates the stored file but does not re-run an approval or re-send an envelope; a "corrected" version can
   sit unsigned while an earlier version is the one that actually went out. Confirm which version was sent and
   signed, not just which is latest in the repository.
5. **Folder security decides what a workflow (and an agent) can see and act on.** A workflow step or a search
   scoped to a folder the actor cannot access returns empty or fails silently; an empty result can mean "no
   permission," not "no document."

## CLM workflow failure and recovery
- A **workflow step can fail mid-run** - a doc-gen merge that errors, a signature step where the send is issued
  but the completion callback never returns, or a metadata push to CRM / ERP that drops. The workflow can be
  left showing "in progress" while the real envelope state moved on, or an envelope was sent that the workflow
  does not know about.
- Recovery is **re-read, do not blind-retry**: check the live envelope status in eSignature and the workflow's
  current step before re-running. Re-running a signature step blind can **double-send** the envelope; re-running
  a generate step can create a duplicate contract version. Reconcile the workflow state to the live envelope
  status (the envelope is the source of truth for what was actually sent / signed), then roll forward.
- A failed or duplicated **doc-gen** produces a wrong or extra draft; discard the bad draft before it routes -
  it is reversible only while it is still an unrouted draft.

## Where CLM hands off to eSignature and to other systems
- When a CLM workflow reaches a **signature step**, control passes to the **eSignature engine** - the envelope,
  recipients, routing, authentication, correcting, voiding, and completion semantics in SKILL.md and
  `envelope-lifecycle-and-recipients.md` all apply from that point.
- The **executed** result flows back into the CLM repository as the record of the agreement; obligations start
  from the executed terms.
- Downstream, the **ERP / AP ledger** posts and pays against the executed contract -> `sap-fi`; the
  **procurement transaction** it governs (requisition, PO, invoice) -> `coupa` / `sap-ariba`.
- If the CLM suite in play is **Icertis** or **SAP Ariba Contracts** rather than DocuSign CLM, the authoring,
  negotiation, deviation, and approval-authority judgment lives in `icertis` /
  `sap-ariba-clm`; only the **signature engine** (the envelope) is this skill.
