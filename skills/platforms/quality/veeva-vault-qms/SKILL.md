---
name: veeva-vault-qms
description: "Veeva Vault QMS - safe operation of a validated (GxP, 21 CFR Part 11) life-sciences quality system: quality events (deviations, CAPA, complaints, change control, audits), effectiveness checks, lifecycle states and workflows, electronic signatures, dispositions/verdicts, controlled-document linkage to Vault QualityDocs, and the immutable audit trail. Use when the connected quality system is Veeva Vault Quality/QMS, or the user mentions Veeva Vault, a quality event, a deviation, a CAPA (corrective and preventive action), a product complaint or reportability/MDR, a change control, an audit or finding, an effectiveness check, an OOS/OOT investigation, a lifecycle state change, a workflow task, an e-signature / electronic signature / 21 CFR Part 11 / Annex 11 / GxP, a disposition or verdict, an object type, dynamic access control / sharing settings, QualityDocs or a controlled SOP, a sandbox vs production vault, VQL, or the audit trail."
---

# Veeva Vault QMS - operating it safely

Vault QMS runs quality events (deviations, CAPA, complaints, change control, audits) as object records on
the Veeva Vault platform, alongside Vault QualityDocs which owns the controlled documents (SOPs, specs) those
events reference. The thing that makes it dangerous is simple: **it is a validated GxP system and almost
every meaningful write is a regulated act with a permanent, immutable audit trail.** A lifecycle state
change fires automation, an e-signed task is a 21 CFR Part 11 signature that can never be removed, a
disposition (classify a deviation, decide a complaint is non-reportable, invalidate an OOS) sets or misses a
regulatory clock, and a closure locks a regulated record. You are not editing a ticket; you are creating
inspectable evidence. This skill classifies those actions so the harness can gate them, plus the edge states
(object types, dynamic access, sandbox vs production, linked-document versions) and the recovery paths -
almost all of which are "correct forward", because nothing here truly rewinds.

## When this applies / when NOT
Connector is Veeva Vault Quality/QMS and the work is quality events, CAPA, complaints, change control, audits,
effectiveness checks, or their linked controlled documents. When NOT:
- SAP QM: inspection lots, usage decisions, quality-inspection stock in an ERP -> `sap-qm`.
- LabWare LIMS: lab sample login, instrument results, stability, the LIMS OOS workflow -> `labware`.
- MasterControl: a MasterControl-based QMS (its own quality suite) -> `mastercontrol`.
- ERP stock/batch disposition postings (scrap, block, return a physical lot in the ERP) -> `sap-mm`.
- Deep controlled-document authoring/lifecycle beyond the QMS linkage is the QualityDocs module of the same
  Vault; this skill covers the linkage and the publish/version hazards, not full doc-control administration.

## Contents
- Object & state model
- Vocabulary that bites
- Operations: read / write / destructive
- Reclassification rules
- Worked example (a deviation -> CAPA, end to end)
- Gotchas that bite
- Edge states & special cases
- Recovery patterns
- Guardrails
- References

## Object & state model (reason about state, not nouns)
- **Quality event records** - the QMS objects: **Deviation / Nonconformance**, **CAPA** (corrective and
  preventive actions with an **effectiveness check**), **Complaint** (product/customer complaint, with a
  **reportability** assessment), **Change Control**, **Audit** (with **findings/observations**), plus
  **Lab Investigation / OOS-OOT**. Each is an **object record**, not a document.
- **Object type** - one Vault object often carries several **object types**, each with its **own lifecycle,
  fields, and security**. A "Quality Event" object can have types Deviation, Complaint, Lab Investigation.
  Read the record's object type before reasoning about its rules; there is no single generic lifecycle.
- **Lifecycle & lifecycle state** - the state machine a record follows. Names are configured per customer;
  a typical deviation runs **Draft/Initiated -> Triage/Assessment -> Investigation/In Progress -> In
  Approval -> Closed**, with off-path **Cancelled/Void**. A state change is what advances the record and
  fires automation; treat state names as illustrative, read the actual lifecycle. Detail in
  `references/quality-event-lifecycles.md`.
- **State type** - Vault's normalized category behind a state (e.g., Starting, In Progress, Complete,
  Cancelled). Reports, metrics, and automations key off the **state type**, not the display name.
- **Workflow & task** - the routing engine. A workflow issues **tasks** to **roles/users**; a record does
  not advance until required tasks complete, and a task may **require an e-signature** to finish. Object
  (multi-record) workflows and legacy document workflows both exist.
- **Lifecycle actions** - **entry actions** fire automatically on entering a state (lock fields, auto-create
  a child CAPA or effectiveness check, notify, start a due-date clock); **user actions** are manual; **event
  actions** fire on events. Advancing a state is never just a status flip - it runs these.
- **Roles, sharing & dynamic access** - record visibility and permissions follow **role assignment on the
  record** (Owner, Editor, Viewer, Approver, Coordinator) via **Dynamic Access Control (DAC)** and
  **sharing settings**; **atomic/field-level security** can gate a single field or state action. Not in a
  role on the record = cannot see or act on it.
- **Controlled document (QualityDocs)** - SOPs/specs/forms as **documents** (not object records) with their
  own lifecycle: **Draft -> In Review -> Approved -> Effective -> Periodic Review -> Superseded/Obsolete**.
  QMS records **reference** these; the reference binds to a **version**.
- **Audit trail** - system-generated and **immutable**: every field change, state change, and signature with
  user + timestamp + old/new value (+ change reason where required). It cannot be edited or deleted; a
  correction is a new entry, never an erasure. Separate object, document, system (config), and login trails.
- **Sandbox vs production vault** - config is built/tested in a **sandbox** vault and migrated to the
  validated **production** vault via a configuration package; records do not copy across. See
  `references/part11-validation-and-config.md`.

## Vocabulary that bites
- **Lifecycle state change** - advancing a record. Not a save: **entry actions** fire (lock, auto-create
  children, notify, start clocks), and past a signed approval most lifecycles do not rewind. Committing.
- **Disposition / verdict** - the regulated decision on a record: deviation **classification** (minor /
  major / critical), complaint **reportability** (reportable vs not), **OOS** confirmed vs invalidated, CAPA
  **effectiveness** effective vs not, audit **finding** severity. It looks like a picklist; it sets scrutiny,
  timelines, and statutory reporting clocks. A wrong disposition is high-risk.
- **Reportability** - the complaint decision that determines whether a regulatory report (MDR to FDA, MIR/
  vigilance in EU) is due and by when. The clock starts at **awareness**, not at your convenience; a
  non-reportable call that is wrong misses a statutory deadline.
- **Effectiveness check** - a separate, scheduled verification that a CAPA actually worked. "Implemented" is
  not "effective"; closing a CAPA on implementation alone skips the proof. A failed check should reopen the
  CAPA or raise a new one.
- **E-signature (Part 11)** - completing a signed task captures credentials + a **signature meaning** (from a
  controlled picklist: Approved / Reviewed / Completed) + timestamp, and links to the record. It is
  **permanent and attributable**; it cannot be removed, and you never sign on another user's behalf or share
  credentials (a data-integrity violation).
- **Configuration vs data** - a **data** action edits a record; a **configuration** action edits a lifecycle,
  workflow, picklist, field, or security rule. In production the latter is a validated **computer-system**
  change, not an operator task.
- **Reason for change / required field** - a validated vault demands a change reason on certain edits and
  mandatory fields to advance a state, captured in the audit trail. It is compliance evidence; a placeholder
  to get past the gate falsifies the record.
- **Object type** - the sub-classification that decides a record's lifecycle, fields, and security. Two
  records on the same object can behave completely differently by type.
- **Dynamic Access Control (DAC)** - visibility/permission by role on the record. "The record isn't there"
  is usually a role/sharing gap, not a missing record; adding a role changes who can act and is logged.
- **Closure** - closing a record is a compliance gate that locks it; reopening is restricted (QA/admin,
  logged) or impossible. Closing before required steps (QA approval, root cause, effectiveness) leaves a gap.
- **Void vs Cancelled** - two different terminal off-path states, not synonyms. **Void** = created in error,
  no regulatory content was ever committed (use it to retire a mistaken record). **Cancelled** = stopped
  after work had started (an investigation/audit trail exists). They carry different regulatory weight and
  reason requirements; both keep the record and its history forever. Pick the one that reflects what happened.
- **VQL / Vault Loader** - VQL (Vault Query Language) is read-only query; Vault Loader / the API drive bulk
  create/update. Bulk writes carry the same per-record gating, multiplied.

## Operations: read / write / destructive
Classify every operation family by what it does to the record and the audit trail. No tool/API names - kinds
of action; the harness maps the customer's real connector onto these classes.

| Class | Vault QMS operation families | Gate | Why |
|---|---|---|---|
| **Read** | view a quality event / CAPA / complaint / change control / audit and its fields; view related records and linked documents; run a VQL query or report; view a document and its rendition; view the audit trail; view workflow tasks/state; view roles/sharing | always pass | no state change; read the object type + state + tasks + sharing before any write, re-read at execute |
| **Write (reversible)** | create a record in **Draft/Initiated** (before it enters a workflow); edit fields on a draft or open record (with change reason - the edit is logged but correctable); attach or relate a document/record; add a comment; reassign an **open task** to another user (routing, no state change); add a user to a role on the record (changes who can see/act on it; logged) | gate one at a time | uncommitted or correctable; no state advance, no signature, no disposition bound; audit-logged but not compliance-committing |
| **Write (committing)** | **advance a lifecycle state** (fires entry actions); **complete a workflow task with an e-signature** (a Part 11 approve/review/sign); **assign a record / set owner** (starts accountability + SLA clock); record a **disposition/verdict** (classify a deviation, decide complaint reportability, confirm/invalidate an OOS, set effectiveness effective/not); start a workflow; make a linked controlled document **Effective**; initiate a regulatory report; **push a record to a connected vault** (e.g., a complaint to a Safety/RIM vault) - creates an obligation in that vault and can start a statutory clock (destructive if it commits a reporting deadline) | gate + human approve | binds a regulated decision, a signature, an owner, or a clock; each is inspectable evidence and mostly one-way |
| **Destructive / irreversible** | **close/void/cancel** a record (terminal, reopening restricted); **close prematurely** or **override a required step** (skip QA approval, close a CAPA before its effectiveness check); a **wrong disposition** that mis-routes or misses a reporting deadline; **obsolete/retire an Effective document** that is still referenced; **delete** a record/document (blocked once referenced or in a controlled state; blocked outright for GxP records in validated production); **any Admin configuration change in production**; sign on another's behalf / share credentials | hard gate + named approver + re-read | permanent trail; crosses a compliance/validation boundary; misses a statutory clock; cannot be cleanly undone |

## Reclassification rules (read this)
Quick classify (take the first that matches): 1) closes/voids/cancels, deletes, overrides a required step,
changes production config, or **starts a statutory reporting clock** (a reportability call/report, or a
cross-vault push that commits a deadline) -> **destructive**. 2) advances a lifecycle state, e-signs a task,
sets an owner/assignment, records a disposition/verdict, publishes a document Effective, or pushes to a
connected vault with no deadline committed -> **committing**. 3) edits a field / attaches / comments / adds a
role on a draft or open record, no state or signature -> **reversible**. Then apply the nuances below.
- **A field edit on a draft or open record is reversible; after a state advance many fields lock.** Editing an
  unlocked field is a correctable write (both values persist in the audit trail). Once you advance the state,
  e-sign a task, or record a verdict, the act is one-way - and entry actions commonly **lock fields on state
  entry**, so the edit may no longer be possible at all, not merely inadvisable.
- **A cross-vault push escalates with what it commits.** Pushing a record to a connected Safety/RIM vault is
  committing; when that push **starts a statutory reporting clock** (vigilance / MDR), it is destructive - it
  commits a deadline that cannot be retracted, only followed by a corrective report.
- **Closing direction matters.** Advancing toward closure is committing; closing (locking the record) is
  destructive because reopening is restricted or impossible. Do not treat "Close" as the last harmless click.
- **A disposition's class rises with its blast radius.** Classifying a deviation or setting effectiveness is
  committing; a reportability decision that could miss an MDR/vigilance deadline, or invalidating an OOS, is
  destructive - it can waive a statutory obligation. Gate the reporting-relevant dispositions hardest.
- **Config in production is always destructive, never a data edit.** Changing a lifecycle, workflow, picklist,
  field, or security rule in the production vault is a validated computer-system change requiring change
  control and sandbox-then-migrate - regardless of how small the field looks.
- **A bulk write is the per-record class times N.** A Vault Loader / API update that advances states or writes
  dispositions across many records is committing/destructive at scale; gate it as such, do not treat bulk as clerical.
- **A configured User Action that advances state or fires a workflow is committing, not just a button.** Custom
  state-change actions (beyond a plain "next state") carry the same entry-action side effects; classify by what
  the action does to the record, not by its label.
- **Adding a role is reversible; overriding a control is not.** Adding a reviewer to a record is a low-blast
  sharing write; force-completing another user's task, signing for them, or bypassing a required task is a
  data-integrity violation in the destructive row. Reassigning an open task is reversible routing, but moving a
  **compliance-critical task** (QA approval, reportability assessment) to a different reviewer changes who makes
  a regulated decision and is logged - treat it with elevated scrutiny even though no state changes.

Universal rules to teach: read the object type + lifecycle state + open tasks + role/sharing + linked
document versions before any write and **re-read at execute** (another user may have advanced the state,
signed, reassigned, or closed it); never bypass a required task, sign on another's behalf, or make config
changes in production; a required field or change reason exists for a reason - do not placeholder past it;
the audit trail is immutable - correct forward, never try to alter it; a reporting clock starts at awareness.

## Worked example (a deviation -> CAPA, end to end)
A manufacturing **deviation** is created in **Draft** *(reversible write: draft record, no state committed -
but the object type Deviation is now fixed and cannot be changed)*. At **Triage** you record a
**classification disposition = Major** *(committing: a verdict that sets a tighter investigation timeline and
QA sign-off; not Minor, which would under-scope it)*. Advancing to **Investigation** *(committing state
change)* fires **entry actions**: the record locks its intake fields, notifies the QA owner, and starts a
due-date clock. Root cause is documented; a **CAPA** child record is created and **linked** *(reversible while
draft)*. The CAPA lists corrective actions referencing two **SOPs** in QualityDocs; implementation gates on
those SOPs reaching **Effective** *(making a doc Effective is itself committing)* and training completing - so
"implemented" cannot be true until the linked documents publish. At **In Approval**, the QA approver completes
a **workflow task with an e-signature** (meaning: Approved) *(committing, hard gate: a Part 11 signature -
permanent, attributed, in the audit trail)*. The CAPA schedules an **effectiveness check** 90 days out as its
own task. If someone closes the CAPA now, that **Close** is **destructive**: it closes **before** effectiveness
is proven - a premature closure, an audit gap, and reopening is a restricted QA/admin action. Correct path:
leave the CAPA open (or in a "pending effectiveness" state) until the 90-day check returns **effective**; only
then does closure reflect reality. If the check returns **not effective**, reopen the CAPA or raise a new
linked one - do not close over a failed verification.

Parallel highest-risk path (a **complaint**): intake **logs awareness**, which **starts the regulatory clock**
*(the intake timestamp matters)*. The **reportability assessment** *(destructive disposition: it can commit or
waive an MDR/vigilance deadline)* decides whether a report is due and by when (e.g., 30-day, or 5-day for
certain events). A wrong non-reportable call here is the single most dangerous action in QMS - it misses a
statutory deadline that no forward correction fully repairs, only a late/supplemental report.

## Gotchas that bite (the real set - causal chains)
1. **A state change is not a save; entry actions fire on it.** Entering a state can lock fields, auto-create
   a child (CAPA, effectiveness check), send notifications, and start an SLA/due-date clock. Advancing "just
   to move it along" triggers side effects you cannot casually undo.
2. **An e-signed task is a Part 11 signature - permanent and attributable.** It captures the signer, meaning,
   and timestamp, links to the record, and can never be removed or edited. Signing on someone's behalf or
   sharing credentials breaks data integrity; the wrong signer is not fixable, only correctable forward.
3. **The audit trail is immutable and captures everything.** Every field change, state change, and signature
   is logged with user + timestamp + old/new value (+ reason). You cannot edit or delete it; "fixing" a
   mistake is a new correcting entry, not an erasure - so a rushed wrong action is inspectable forever.
4. **Closing a record is a compliance gate, not a status flip.** Closing a CAPA before its effectiveness
   check, or a deviation without QA approval / documented root cause, closes a regulated event prematurely
   and leaves an audit gap; reopening is restricted (QA/admin, logged) or impossible.
5. **A disposition is a regulated decision.** Classifying a critical deviation as minor, marking a product
   complaint non-reportable, or invalidating an OOS mis-routes the event and can waive scrutiny or a
   reporting obligation. It is a picklist with statutory weight - a wrong value is high-risk.
6. **Complaint reportability drives a regulatory clock that starts at awareness.** The reportability
   assessment decides whether an MDR (FDA) or MIR/vigilance (EU) report is due and by when (e.g., a 30-day or
   5-day deadline). Deferring or mis-calling it risks a missed statutory deadline, not just a late task.
7. **An effectiveness check is separate from CAPA closure.** The CAPA can be "implemented" while
   effectiveness is still pending; closing on implementation alone skips the proof the action worked. If the
   check fails, reopen the CAPA or raise a new one - do not close over a not-effective result.
8. **Config change in production is a validated computer-system change, not a data edit.** Editing a
   lifecycle, workflow, picklist value, field, or security rule in the production vault must go through change
   control, be tested in a sandbox, and migrate via a configuration package. An unqualified prod config change
   breaks the validated state and is itself an inspection finding.
9. **Sandbox and production are different vaults; config migrates, records do not.** Testing a workflow in
   sandbox changes nothing in production; a fix ships through the validated migration path, and record data
   created in sandbox is throwaway. Do not assume a sandbox result is live.
10. **Object types share an object but have their own lifecycle, fields, and security.** A Complaint and a
    Deviation on the same "Quality Event" object follow different rules; reasoning about "the quality event
    lifecycle" generically mis-steps. Read the record's object type first - and note the type is **fixed at
    creation and cannot be changed**, so a wrong type means void and recreate, not edit.
11. **Visibility follows role assignment (DAC), not a global permission.** If the user/agent is not in a role
    (Owner/Editor/Approver) on that specific record, they cannot see or act on it. "I can't find the record"
    is usually a sharing/role gap; adding a role changes who can act and is logged.
12. **Atomic/field-level security can block one field or one state action** even when you can see the record.
    A required-but-restricted field or a state action your role lacks stops the advance; the fix is the right
    role, not forcing the value in another way.
13. **A required task cannot be skipped.** A record does not advance while a required workflow task is open,
    and you cannot complete a task you are not assigned. Reassignment is the correct move; bypassing or
    force-completing another's task is a control violation.
14. **Cancelling or restarting a workflow un-does collected reviews.** Cancelling an in-flight workflow voids
    its tasks and can roll routing back; restarting re-issues tasks and may reset approvals already given. An
    "innocent" cancel discards signatures/reviews that then must be redone.
15. **Linked controlled documents bind by version.** A change control or event referencing a specific document
    version does not auto-update when a new version goes Effective. Referencing "the SOP" vs "SOP v3.0"
    matters - an implementation pointed at the wrong version verifies against stale content.
16. **A change control's implementation often gates on the linked SOP reaching Effective and training done.**
    Closing the change before the new document is Effective and trained leaves the change unimplemented in
    practice while the record says complete.
17. **Making a document Effective supersedes the prior version and fires downstream.** It can trigger training
    assignments and periodic-review clocks; the superseded version becomes non-current and references to it
    may need updating. It is a committing publish, not a save.
18. **Deleting or obsoleting a referenced record/document is blocked or strands links.** Referential integrity
    stops deleting a parent with children (a deviation with CAPAs, a change with tasks); obsoleting an
    Effective SOP referenced by open events breaks those links. In validated production, GxP records generally
    cannot be deleted at all - by design.
19. **"Reason for change" and required fields are compliance evidence, not friction.** They are captured in
    the audit trail and reviewed in inspections. A placeholder entered to clear the gate falsifies the record
    and is itself a data-integrity finding.
20. **Assigning a record starts accountability and an SLA clock.** Setting the owner notifies, sets
    responsibility, and can start the on-time-closure metric. Mis-assigning delays the clock against the wrong
    person and skews quality metrics.
21. **Effective-dated and scheduled tasks fire automatically.** Periodic-review due dates on documents and
    effectiveness-check due dates on CAPAs generate tasks on schedule; ignoring an auto-created task leaves an
    overdue compliance item that is visible in metrics and to an inspector.
22. **State types, not display names, drive automation and reporting.** Renaming or adding a state without
    mapping its **state type** silently breaks metrics and automations keyed on the type. (A config concern -
    another reason config changes belong in sandbox + change control, not ad hoc in production.) Do not rename
    or add a state or state type as a workaround - that is a production config change, off-limits to an operator.

23. **A bulk operation multiplies the commitment.** A Vault Loader / API run that advances states, records
    dispositions, or completes signed tasks across many records commits every one at once - bulk-approving 50
    CAPAs or dispositioning 50 complaints is 50 regulated acts, each in the audit trail. Gate a bulk write by
    its per-record class, never as clerical throughput.

(Deep detail: `references/quality-event-lifecycles.md`, `references/part11-validation-and-config.md`.)

## Edge states & special cases
Each breaks naive "advance it and close it" logic - the key rule inline, full behavior in the references.
- **Object types** - the same object behaves differently per type (Deviation vs Complaint vs Lab
  Investigation); check the type before applying any lifecycle rule. `references/quality-event-lifecycles.md`.
- **Parent/child hierarchy** - a quality event with child CAPAs and effectiveness checks; closing or deleting
  the parent is constrained by open children, and a child's result (a failed effectiveness check) can force
  the parent back open.
- **Multi-record / multi-document workflows** - one workflow spanning several records or documents; a single
  task completion can advance many, so a bulk approve is a bulk commitment.
- **Sandbox vs production** - config is migrated, not the records; never validate a production behavior from a
  sandbox test alone. `references/part11-validation-and-config.md`.
- **Legacy vs object workflows** - older document workflows and newer object/multi-record workflows coexist;
  the routing and e-signature mechanics differ, so read which one drives the record.
- **Controlled-document steady state + version binding** - a reference to a document resolves to a version;
  "latest Effective" and "the version I linked" can diverge after a new publish.
- **Cross-vault connections** - a complaint may push to a Safety/RIM vault (vigilance, submissions); the
  reporting obligation and clock live partly in that connected vault, not only in QMS.
- **Delegated access / signature** - task completion can be delegated, but the signature records the **actual
  signer**; a signature meaning cannot be delegated away from the person who signs.

## Recovery patterns (can it be undone, and what cannot)

| Situation | Recovery path |
|---|---|
| A field was edited wrong on an open/draft record (before any state change or signature) | edit it again with a change reason; both values persist in the audit trail - nothing is erased, the old value stays visible |
| The wrong **object type** was chosen at creation | object type is fixed at creation and cannot be changed; **void** the record and create a new one of the correct type (link them so the history is traceable) |
| A record was advanced a state too early | move it forward, or use the lifecycle's defined **return/reject** path if one exists (many lifecycles are one-way past a signed approval); the state change is logged either way - there is no silent rewind |
| A record is **stuck** (e.g., In Approval with no reject/return action configured, or a required task no one available can complete) | escalate to QA/admin - reassign the blocking task to an authorized role, or raise a linked correction record; do not force, void, or cancel a record mid-approval just to unstick it |
| A workflow task was e-signed in error / by the wrong signer | the signature cannot be removed; correct forward (a new task/signature or a documented correction record); the erroneous signature stays in the trail |
| A record was closed prematurely | reopening requires the lifecycle to allow it (QA/admin action, logged) and may not restore auto-triggered downstream; if there is no reopen path, raise a new linked record referencing it |
| A wrong disposition was already reported to a regulator | cannot unsend; file a follow-up/correction (e.g., a supplemental MDR) with the agency - a corrective report, not an edit |
| An erroneous **cross-vault push** (a complaint sent to a Safety/RIM vault that should not have gone) | cannot be recalled - the obligation now exists in the receiving vault; correct forward with a cancelling/supplemental report in that vault, coordinated with its owner |
| A record was cancelled/voided | terminal; the record and its full history persist; to proceed, create a new record that references the voided one |
| An effectiveness check returned "not effective" | do not close over it; reopen the CAPA or raise a new linked CAPA; the failed result stays in the trail as evidence the first action did not hold |
| An Admin config change was made in production | a revert is itself a change-controlled config action; assess validation impact first; this is not a simple undo and may require re-validation |
| A record/document deletion is needed | in validated production, GxP records generally cannot be deleted (blocked by design); if truly required it is an admin/quality decision, logged, and often only voiding is permitted instead |

Reversal is almost always **correct forward**, not an undo: the original field value, state change, signature,
disposition, and report all remain in the immutable trail. What is truly foreclosed is a missed statutory
reporting deadline and a signed approval - neither is retractable, only followed by a corrective action.

## Guardrails
- Read the record's **object type + lifecycle state + open tasks + role/sharing + linked document versions**
  before acting; re-read at execute (state, signatures, assignment, and closure all drift as others work).
- Treat a **state change, an e-signed task, an assignment, a disposition/verdict, and a closure** as committing
  compliance actions - route to the named approver/role, never force them, and never sign on another's behalf
  or share credentials.
- Never make **Admin configuration changes in a production vault**; build and test in a sandbox and migrate
  through validated change control. A config change is not a data edit.
- A **disposition** (classification, reportability, OOS validity, effectiveness verdict) is a regulated
  decision with a downstream reporting clock that starts at awareness - get it right, do not guess to close faster.
- The **audit trail is immutable**; a mistake is corrected forward with a new entry, never erased. Do not
  attempt to alter or work around it, and do not placeholder a required field or change reason to pass a gate.
- For anything in the destructive row (close/void/cancel, premature close, override a required step, wrong
  disposition, obsolete a referenced document, delete, prod config change, credential sharing): named
  approver, re-read of live state, and a logged reason.

## References (load on demand)
- `references/quality-event-lifecycles.md` - the per-object-type lifecycles and typical states (deviation,
  CAPA + effectiveness check, complaint + reportability, change control, audit + findings), workflow/task and
  entry/user/event-action mechanics, state types, and the parent/child hierarchy.
- `references/part11-validation-and-config.md` - electronic signatures and signature meaning, the immutable
  audit trail and ALCOA+ data integrity, validated-system configuration vs data, sandbox-to-production
  migration, roles/DAC/atomic security, and controlled-document (QualityDocs) linkage and version binding.
