---
name: mastercontrol
description: "MasterControl Quality Excellence (Qx) and Manufacturing Excellence (Mfg-Ex) - safe operation of a validated (GxP, 21 CFR Part 11) quality and manufacturing suite: quality events (deviations/NCR, CAPA and effectiveness verification, complaints and reportability, change control, audits/findings), document control (DCC), training/exams, routes and tasks (workflow/signature engine), electronic batch/production records (EBR, review by exception), e-signatures, and the immutable audit trail. Use when the connected quality or manufacturing system is MasterControl, or the user mentions Qx or Mfg-Ex, a route or task, a deviation/NCR, a CAPA or effectiveness check, a complaint or reportability/MDR, a change control, an audit/finding, a controlled SOP / document control / DCC / periodic review, a training/curriculum/exam, an electronic batch record / production record / review by exception, a batch/lot release, an e-signature / 21 CFR Part 11 / GxP, a disposition or verdict, or the audit trail."
---

# MasterControl - operating it safely

MasterControl runs quality events, controlled documents plus training, and electronic batch/production
records on one validated platform, and it moves every one of them through **routes** - its workflow and
signature engine. The thing that makes it dangerous is simple: **it is a validated GxP system, and almost
every meaningful write is a routed, e-signed act on a permanent, immutable audit trail.** Advancing a route
step is a 21 CFR Part 11 electronic signature that cannot be removed; releasing a controlled document
supersedes its prior revision and auto-assigns training to the workforce; a disposition (classify a
deviation, decide a complaint is non-reportable, release a batch) sets or misses a regulatory clock; and in
Manufacturing Excellence a batch is dispositioned by **review by exception** - only flagged exceptions get
reviewed, so a mis-flagged or suppressed exception ships unverified product. You are not editing a ticket;
you are creating inspectable evidence. This skill classifies those actions so the harness can gate them,
plus the edge states (routes, DCC document control, training cascade, Mfg-Ex master template vs production
record, environments) and the recovery paths - almost all of which are "correct forward", because nothing
here truly rewinds.

## When this applies / when NOT
Connector is MasterControl (Quality Excellence / Qx, or Manufacturing Excellence / Mx / Mfg-Ex) and the work
is quality events, documents/training, routes, or electronic batch/production records. When NOT:
- Veeva Vault QMS: a quality suite on the Veeva Vault platform (object records, lifecycles, DAC) -> `veeva-vault-qms`.
- SAP QM: inspection lots, the usage decision, quality-inspection stock postings in an ERP -> `sap-qm`.
- LabWare LIMS/ELN: lab sample login, result entry/authorization, the LIMS OOS lab-phase, stability -> `labware`.
- ERP physical stock disposition (block / scrap / return a lot, movement types, valuation) -> `sap-mm`.

Seam to hold: **MasterControl owns the quality record, the controlled document + training, and the electronic
batch record.** The lab number that feeds a disposition lives in the LIMS (`labware`) or SAP QM;
the physical goods movement that follows a batch decision (release QI stock, scrap, return) posts in the ERP
(`sap-qm` / `sap-mm`). MasterControl carries the routed decision and its signature, not
the stock posting or the raw lab value. When a request crosses this seam, do the MasterControl portion only and
name what belongs to the other system - do not proxy a stock movement or a lab authorization from here.

## Contents
- Object & state model
- Vocabulary that bites
- Operations: read / write / destructive
- Reclassification rules
- Worked example (a change control -> document + training, and an Mfg-Ex batch release)
- Gotchas that bite
- Edge states & special cases
- Recovery patterns
- Guardrails
- References

## Object & state model (reason about state, not nouns)
- **Route (and route template)** - the workflow and signature engine that drives every record. A **route
  template** defines the ordered **steps** (Collaboration/Author -> Review -> Approval -> Release, or a
  quality-event phase sequence); a live route issues **tasks** and advances only as required tasks complete.
  Advancing a step is what moves the record and fires its actions; it is never just a status flip. Detail in
  `references/qx-quality-and-documents.md`.
- **Task** - the unit of work assigned to a **user or role**. A **signature task** requires an e-signature to
  complete; a data/collaboration task does not. The record does not advance while a required task is open,
  and you cannot complete a task assigned to someone else.
- **Quality-event records (Qx)** - **Deviation / Nonconformance (NCR)**, **CAPA** (with a separate
  **effectiveness verification/check**), **Customer Complaint** (with a **reportability / adverse-event**
  assessment), **Change Control** (with impact assessment and linked documents/training), **Audit** (internal
  / supplier / external, with **findings/observations**). Each is a record moved through a route, not a
  document; its phase/state is defined by the route configuration, not a single generic lifecycle.
- **Controlled document (Document Control / DCC)** - SOPs, specs, forms, work instructions. Lifecycle:
  **Draft -> In Review/Collaboration -> Approval (routed, e-signed) -> Released -> Effective (on the
  effective date) -> Periodic Review -> Obsolete/Retired**. **Released is not the same as Effective**: a
  document can be approved/released with a **future effective date** and is not in force until then.
  Releasing supersedes the prior **revision** and can auto-assign training. Detail in `references/qx-quality-and-documents.md`.
- **Revision / controlled copy** - documents are revision-controlled; a new revision supersedes the old, and
  a record that references a document binds to a **revision**, not "the latest". Printed/controlled copies
  must track the effective revision.
- **Training task / curriculum / exam** - training is tied to documents. Releasing a document (or a change
  control's training requirement) auto-assigns **training tasks** to the mapped **job roles / curricula**;
  completion is an **e-signed training record**, and some require passing an **exam/assessment**. "Released"
  is not "trained"; the workforce is not qualified on the new SOP until training completes.
- **Manufacturing Excellence (Mfg-Ex) production record** - the electronic batch record (EBR / EPR / eDHR).
  A **master template** (the approved batch-record design) is issued as a **production record** instance for a
  specific batch/lot. Operators enter data and sign steps in sequence; the record is dispositioned by
  **review by exception** and then **released** (batch disposition). Master template vs instance, review by
  exception, and enforced flow are detailed in `references/mfgex-and-part11.md`.
- **Exception (Mfg-Ex)** - a flagged departure in a production record: an **out-of-limit** value, a skipped
  or out-of-order step, an enforced-flow override. Exceptions are what **review by exception** reviews; an
  un-flagged or suppressed exception is not seen at review.
- **Disposition / verdict** - the regulated decision on a record: deviation **classification** (minor / major
  / critical), complaint **reportability** (reportable vs not), CAPA **effectiveness** (effective vs not),
  audit **finding** severity, and **batch/lot release** (release / reject / hold). Looks like a picklist;
  sets scrutiny, timelines, and statutory clocks.
- **Electronic signature (Part 11)** - completing a signature task captures the signer, a **signature meaning**
  (from a controlled set: Authored / Reviewed / Approved / Released), a timestamp, and a link to the record.
  It is permanent and attributable; it cannot be removed, and you never sign on another's behalf or share
  credentials. Detail in `references/mfgex-and-part11.md`.
- **Environments (validation vs production)** - configuration (route templates, forms, master templates,
  exams, roles) is built and tested in a **validation/sandbox** environment and promoted to **production**
  under change control. Records do not copy across; a validation-environment result is not live.
- **Audit trail** - system-generated and **immutable**: every field change, route/step advance, and signature
  with user + timestamp + old/new value (+ reason where required). It cannot be edited or deleted; a
  correction is a new entry, never an erasure.

## Vocabulary that bites
- **Route / advance a step** - advancing a record's route is the committing act: it fires the step's actions
  (notify, issue the next task, lock fields, start clocks) and usually captures a signature. Not a save; past
  a signed approval most routes do not rewind.
- **Signature meaning** - the controlled meaning bound to an e-signature (Authored/Reviewed/Approved/
  Released). It states what the signer attests to; the wrong meaning mis-states the record and cannot be
  edited off the signature.
- **Released vs Effective (documents)** - **Released** = approved and issued; **Effective** = in force on the
  effective date. A future-dated release means the new SOP is not yet the controlling revision; acting as if
  it is uses a document not yet in force (or ignores the old one still governing).
- **Periodic review** - a scheduled re-review of a released document; it auto-generates a task on its due
  date. An ignored periodic review is an overdue, inspectable compliance item.
- **Training cascade** - releasing a document assigns training to the mapped roles/curricula automatically.
  "Document effective" without "training complete" leaves the workforce unqualified on the current SOP - an
  audit gap, and a reason a change control is not truly implemented.
- **Effectiveness verification (CAPA)** - a separate, scheduled check that the CAPA actually worked.
  "Implemented" is not "effective"; closing a CAPA on implementation alone skips the proof.
- **Reportability / adverse event** - the complaint decision that determines whether a regulatory report
  (MDR to FDA, MIR/vigilance in EU) is due and by when. The clock starts at **awareness** (intake), not at
  your convenience; a wrong non-reportable call misses a statutory deadline.
- **Review by exception (Mfg-Ex)** - the batch-record review reviews only **flagged exceptions**, not every
  entry. Its safety depends entirely on the flags being right; a suppressed or mis-classified exception is
  never seen at review, so it releases unverified.
- **Enforced flow / forced entry (Mfg-Ex)** - the production record enforces step order and prevents skipping;
  an override of the enforced order or a forced value is itself a logged exception, not a quiet edit.
- **Batch / lot release** - the QA disposition that commits product to ship. High blast: releasing over an
  open exception, an open deviation, or a missing signature ships unverified product.
- **Master template vs production record** - the template is **configuration** (validated design); the
  production record is **data** (one batch). Editing the template changes every future batch; editing an
  issued record's data is a per-batch act with exceptions.
- **Delegation / proxy signature** - a task can be delegated, but the signature records the **actual signer**
  and that it was by proxy. Delegating a compliance-critical approval (QA release, reportability) changes who
  makes the regulated decision.
- **Void vs Cancel** - two terminal off-path states, not synonyms. **Void** = created in error, no regulated
  content committed. **Cancel** = stopped after work started (a trail exists). Both keep the record forever;
  pick the one that reflects what happened.
- **Configuration vs data** - a **data** action edits a record; a **configuration** action edits a route
  template, form, master template, exam, or security role. In production the latter is a validated
  computer-system change, not an operator task.
- **Reason for change / signature comment** - a validated system demands a reason on certain edits and a
  comment/meaning on signatures, captured in the audit trail. It is compliance evidence; a placeholder to
  clear the gate falsifies the record.

## Operations: read / write / destructive
Classify every operation family by what it does to the record, the route, and the audit trail. No tool/API
names - kinds of action; the harness maps the customer's real connector (MasterControl UI or API) onto these.

| Class | MasterControl operation families | Gate | Why |
|---|---|---|---|
| **Read** | view a quality event / CAPA / complaint / change control / audit and its fields; view a controlled document, its revision history, and effective revision; view a production record / EBR and its exceptions; view route/task status and who holds a task; view training assignments/curricula/exam status; view the audit trail; run a report / Insights query | always pass | no state change; read the record's route + step + open tasks + revision/effective state before any write, re-read at execute |
| **Write (reversible)** | create a record in **Draft** (before it enters a route); edit fields on a draft or open record (with reason - logged but correctable); author/edit a **document revision in Draft/Collaboration** before approval routing; enter production-record data **before the step is signed** (correctable draft); attach or relate a document/record; **link/unlink a child record** (deviation<->CAPA, change<->document) - reversible routing, though the child's state then constrains the parent's closure (unlinking a child that **gates** the parent's closure is committing, not routine); add a comment; **reassign or delegate an open task** (routing, no state change); create/edit a route or template **in the validation environment** | gate one at a time | uncommitted or correctable; no signature, no step advanced, no disposition bound; audit-logged but not compliance-committing |
| **Write (committing)** | **advance a route step / complete a signature task** (a Part 11 sign - fires the step's actions); **assign owner / start the SLA clock**; record a **disposition/verdict** (classify a deviation, decide complaint reportability, set CAPA effectiveness, grade an audit finding); **release a document** (supersedes the prior revision, auto-assigns training, starts the periodic clock); **complete a training task / pass an exam** (an e-signed training record); **issue a production record** from a master template; **sign an in-process step** in a production record; **place a batch/record on hold** (withholds it - reversible by release); initiate a regulatory report (committing only **after** the reportability call is confirmed - the reportability decision itself is the destructive gate below) | gate + human approve | binds a signature, an owner, a regulated decision, a document in force, or a schedule; each is inspectable evidence and mostly one-way |
| **Destructive / irreversible** | **release / disposition a batch or lot** (commits product to ship; **releasing over an open exception / deviation / missing signature** ships unverified product); **close/void/cancel** a record, or **close prematurely / skip a required step** (close a CAPA before its effectiveness check, complete a change before the SOP is Effective and trained); a **wrong disposition** that mis-routes or misses a reporting clock; **override or suppress an Mfg-Ex exception** / bypass enforced flow; **obsolete/retire a Released document still referenced or trained-against**; **delete** a record/document (blocked for GxP records in validated production); **any configuration change in the production environment** (route template, form, master template, exam, role); sign on another's behalf / share credentials / back-date a signature or training | hard gate + named approver + re-read | permanent trail; crosses a compliance/validation boundary; ships product or certifies quality; misses a statutory clock; cannot be cleanly undone |

**What the gate column means:** *gate one at a time* = confirm each write with the user/harness and execute
it singly; never batch reversible writes without per-action confirmation. *gate + human approve* = a named
approver signs off before it executes. *hard gate + named approver + re-read* = re-read the live state, get the
named approver, log the reason, then execute that one action only. When a request **spans systems** (e.g.,
"release this batch and move the stock"), do the MasterControl part only, state plainly what falls to the LIMS
or ERP, and do not proxy the other system's action.

> **Highest-risk single action - a complaint reportability / adverse-event call.** It starts an MDR/vigilance
> clock at **awareness** (intake); a wrong **non-reportable** decision misses a statutory deadline that no
> forward correction repairs, only a late/supplemental report. Never guess it to close faster - route it to the
> named regulatory/QA approver, and treat the reporting-relevant disposition as the hardest gate in the system.
> Do not pre-emptively file a report "just in case" either - filing an unnecessary report is itself a regulated
> act (agency follow-up, documentation burden); initiate one only after the reportability assessment is confirmed.

## Reclassification rules (read this)
Quick classify (take the first that matches): 1) releases/dispositions a batch, closes/voids/cancels,
overrides/suppresses an exception, skips a required step, deletes, changes production config, or **starts a
statutory reporting clock** (a reportability call/report) -> **destructive**. 2) advances a route step /
e-signs a task, sets owner, records a disposition/verdict, releases a document, completes training, or issues
a production record -> **committing**. 3) edits a field / authors a draft / enters unsigned data / attaches /
comments / reassigns an open task -> **reversible**. 4) **cannot tell? STOP - do not execute.** Treat it as
**destructive**, escalate to a qualified human, and document the ambiguity. In a validated system, guessing at
a classification and then proceeding - even guessing "destructive" - is itself unsafe; halt at the strictest
class, do not act on the guess. Then apply the nuances:
- **A field edit on a draft or open record is reversible; after a step is signed, fields lock.** Editing an
  unlocked field is a correctable write (both values persist in the trail). Once you advance the step, e-sign
  a task, or record a verdict, the act is one-way - and step-entry actions commonly lock fields, so the edit
  may no longer be possible at all.
- **A batch/production-record release is destructive, not just the last committing step.** Review by exception
  means only flagged exceptions were reviewed; releasing while an exception, an open deviation, or a required
  signature is outstanding commits unverified product to ship. Gate a release hardest, and check every open
  exception on the record, not the summary.
- **Releasing a document is committing; obsoleting one still in use is destructive.** A release supersedes the
  prior revision and cascades training. Obsoleting/retiring a Released document that open records reference or
  the workforce is trained against strands links and de-qualifies people - a destructive control change.
- **A disposition's class rises with its blast radius.** Classifying a deviation or setting CAPA effectiveness
  is committing; a complaint reportability call that could miss an MDR/vigilance deadline is destructive - it
  can waive a statutory obligation. Gate the reporting-relevant dispositions hardest.
- **Withholding is asymmetric from releasing.** Placing a batch/record on **hold** only withholds it and is
  reversible by release - committing, because it stops shipment, but recoverable. **Releasing** a held batch,
  or lifting a hold to push product through, is the committing/destructive direction and belongs to the
  disposition owner. Same field change; the direction decides the class.
- **Config in production is always destructive, never a data edit.** Changing a route template, form, master
  template, exam, or security role in the production environment is a validated computer-system change
  requiring change control and validation-then-promote - regardless of how small the field looks.
- **A bulk operation is the per-record class times N.** A bulk approve of documents, a bulk training
  completion, or a bulk disposition commits every one at once; gate **each record by its own class** - a bulk
  action is not a single gate. A bulk disposition that includes one reportability call is destructive for that
  record and committing for the rest; never gate the batch at the lowest risk.
- **An escalation/timeout auto-action carries the class of what it does.** If the route config auto-advances or
  auto-signs a step on timeout/escalation, treat the result exactly as a manual advance of that step - same
  class, same gate - and read the escalation config before assuming a task still sits where you left it.
- **Delegation is reversible routing; overriding a control is not.** Reassigning or delegating an open task is
  low-blast routing (the signature still records the actual signer). Force-completing another's task, signing
  for them, or bypassing a required task is a data-integrity violation in the destructive row - and delegating
  a compliance-critical approval (QA release, reportability) changes who makes a regulated decision, so treat
  it with elevated scrutiny even though no state changes yet.

Universal rules to teach: read the record's route + current step + open tasks + document revision/effective
state + open exceptions before any write and **re-read at execute** (another user may have advanced the step,
signed, released, or closed it); **if the live state changed since your read - a step advanced, a signature or
release landed, the record closed - abort the write and re-evaluate, never force a stale-state write through**;
never bypass a required task or enforced flow, sign on another's behalf, or
make configuration changes in production; a required field, reason, or signature meaning exists for a reason -
do not placeholder past it; the audit trail is immutable - correct forward, never try to alter it; a reporting
clock starts at awareness.

## Worked example (a change control -> document + training, and an Mfg-Ex batch release)
A process change is raised as a **Change Control** in **Draft** *(reversible write: no step signed)*. It routes
through impact assessment; QA records the **impact/risk disposition** *(committing verdict)* and the change
requires a revised SOP and re-training. The linked SOP is authored as a **new revision in Collaboration**
*(reversible while draft)*, then routed for **Approval**; each approver completes a **signature task**
*(committing: a Part 11 sign with meaning = Approved)*. On **Release**, the SOP supersedes its prior revision
and, on its **effective date**, becomes the controlling document; release **auto-assigns training tasks** to
the mapped operator curriculum *(committing cascade)*. Here is the trap: the change control's implementation
gates on the SOP being **Effective and training complete** - closing the change while the effective date is in
the future or training is still open marks it complete while the floor is still running the old SOP and the
workforce is unqualified *(that premature close is destructive - an audit gap, reopening is restricted)*. The
CAPA (if one was linked) schedules an **effectiveness verification** weeks out; closing it on implementation
alone skips the proof - if the check returns **not effective**, reopen or raise a new linked CAPA rather than
close over it.

Now the manufacturing side. A batch runs on a **production record** issued from the approved **master
template**. Operators enter in-process values and **sign each step** *(committing signatures)*; enforced flow
prevents skipping. One in-process check reads **out of limit**, which raises an **exception**. Disposition is
by **review by exception**: only that exception (and any others flagged) is reviewed. The right path is to
disposition the exception - justify, link a deviation if needed, and have QA review it - before release. The
wrong path, and the one to refuse: **override or suppress the exception**, or **force the value inside limits**
so no exception flags, or **release the batch with the exception still open** - each ships unverified product,
each leaves the original out-of-limit entry in the immutable trail anyway, and **batch release commits product
to ship** *(destructive)*. If the batch is released in error, MasterControl cannot un-ship it: put the lot on
**hold** in the record, drive the physical stock hold/recall in the ERP (`sap-mm`), and correct
forward with a deviation - the release signature stays in the trail.

Parallel highest-risk path (a **complaint**): intake **logs awareness**, which **starts the regulatory clock**.
The **reportability assessment** *(destructive disposition: it can commit or waive an MDR/vigilance deadline)*
decides whether a report is due and by when - awareness logged on day 0 starts, for example, a 30-day MDR clock
expiring on day 30 (or a 5-day clock for certain serious events). A wrong non-reportable call is the single
most dangerous action - it misses a statutory deadline no forward correction fully repairs, only a
late/supplemental report.

Third risk surface (a **deviation classification**): calling a critical deviation "minor" under-scopes its
investigation depth, approval level, and timeline; the fix is a new classification disposition on the same
record (correct forward) - the original class and its audit-trail entry persist, so the mis-call is visible.

## Gotchas that bite (the real set - causal chains)
1. **Advancing a route step is not a save; it fires the step's actions.** Entering/leaving a step can lock
   fields, notify, issue the next task, and start clocks - and usually captures a signature. Advancing "just
   to move it along" triggers side effects you cannot casually undo.
2. **A completed signature task is a Part 11 signature - permanent and attributable.** It captures the signer,
   the **signature meaning**, and a timestamp, links to the record, and can never be removed or edited. Signing
   on another's behalf, sharing credentials, or back-dating breaks data integrity; a wrong signer is corrected
   forward, never erased.
3. **The audit trail is immutable and captures everything.** Every field change, step advance, and signature
   is logged with user + timestamp + old/new value (+ reason). "Fixing" a mistake is a new correcting entry,
   not an erasure - a rushed wrong action is inspectable forever.
4. **Releasing a document supersedes the prior revision and cascades training.** Release is a committing
   publish, not a save: the old revision becomes non-current, training tasks auto-assign to the mapped
   roles/curricula, and a periodic-review clock starts. Downstream references to the old revision may need
   updating.
5. **Released is not Effective.** A document can be released with a **future effective date** and is not the
   controlling revision until then; acting on it early uses a document not in force, and ignoring the old one
   still governing runs the floor on a stale SOP. Controlled copies must track the effective revision.
6. **"Document effective" is not "workforce trained."** Training auto-assigns on release but completes on its
   own schedule; until it does, operators are unqualified on the current SOP - an audit gap. A change control
   that gates on training is not truly implemented until training closes.
7. **Closing a CAPA before its effectiveness verification skips the proof.** The CAPA can be "implemented"
   while effectiveness is still pending; closing on implementation alone waives the check. If it returns
   not-effective, reopen the CAPA or raise a new linked one - do not close over a failed verification.
8. **A disposition is a regulated decision, not a picklist.** Classifying a critical deviation as minor,
   marking a complaint non-reportable, or grading an audit finding wrong mis-routes the event and can waive
   scrutiny or a reporting obligation. It carries statutory weight.
9. **Complaint reportability drives a regulatory clock that starts at awareness.** The reportability call
   decides whether an MDR (FDA) or MIR/vigilance (EU) report is due and by when (e.g., a 30-day or 5-day
   deadline). Deferring or mis-calling it risks a missed statutory deadline, not just a late task.
10. **Review by exception only reviews what is flagged.** In Mfg-Ex the batch-record review looks at flagged
    exceptions, not every entry; a suppressed, overridden, or mis-classified exception is never seen at review
    and releases unverified. The method is only as safe as the flags.
11. **Batch/lot release commits product to ship.** Releasing over an open exception, an open linked deviation,
    a missing required signature, or an incomplete production record ships unverified product; the release
    signature is permanent and the physical undo (hold/recall) lives in the ERP, not here.
12. **The master template is configuration; the production record is data.** Editing the master template
    changes every future batch and is a validated change; editing an issued record's data is a per-batch act
    that should raise exceptions. Confusing the two either breaks validation or hides a batch deviation.
13. **Enforced flow prevents skipping - overriding it is a logged exception, not a quiet edit.** Forcing a
    step out of order or a value past a limit raises an exception that must be dispositioned; treating the
    override as a shortcut leaves an un-dispositioned control breach in the record.
14. **An out-of-limit entry raises an exception that blocks clean completion.** You cannot complete/release a
    production record around an open exception; entering a value inside limits to avoid the flag is
    falsification, and the original entry stays in the trail.
15. **A required task cannot be skipped, and you cannot complete a task you do not hold.** The record does not
    advance while a required task is open; reassignment/delegation is the correct move, and force-completing or
    signing another's task is a control violation.
16. **Cancelling or restarting a route can reset collected signatures/reviews.** Cancelling an in-flight route
    voids its tasks and can roll routing back; restarting re-issues tasks and may reset approvals already
    signed. Whether a given signature survives depends on the route config - check it, do not assume all prior
    work is gone (or that it all persisted); an "innocent" cancel can discard signatures/reviews that must then
    be redone.
17. **Configuration change in the production environment is a validated computer-system change, not a data
    edit.** Editing a route template, form, master template, exam, or security role in production must go
    through change control and be validated - an unqualified prod config change breaks the validated state and
    is itself an inspection finding.
18. **Validation and production are different environments; config promotes, records do not.** A route or
    template tested in the validation/sandbox environment changes nothing in production until promoted under
    change control, and its records are throwaway. Do not assume a validation-environment result is live.
19. **"Reason for change" and signature meaning are compliance evidence, not friction.** They are captured in
    the audit trail and read in inspections; a placeholder reason or the wrong signature meaning falsifies the
    record and is itself a data-integrity finding.
20. **Delegation records the actual signer; a proxy is not anonymity.** A delegated signature captures who
    really signed and that it was by proxy. Delegating a compliance-critical approval (QA release,
    reportability) moves who makes a regulated decision - logged, and to be scrutinized.
21. **Escalation/timeout can auto-advance or reassign a task.** A route left idle may escalate to a manager who
    then holds (or signs) the task; ignoring escalation config can put a signature or an advance in a place you
    did not expect. Read the escalation rules before assuming a task is where you left it.
22. **Obsoleting or deleting a referenced record/document is blocked or strands links.** Referential integrity
    stops removing a parent with open children (a deviation with CAPAs, a change with tasks/training);
    obsoleting a Released SOP referenced by open records or trained curricula breaks those links. In validated
    production, GxP records generally cannot be deleted at all - by design.
23. **Assigning an owner starts accountability and an SLA clock.** Setting the owner notifies, sets
    responsibility, and can start the on-time-closure metric; mis-assigning delays the clock against the wrong
    person and skews quality metrics.
24. **Periodic-review, effectiveness, and training due dates fire automatically.** Scheduled tasks generate on
    their due dates; ignoring an auto-created task leaves an overdue compliance item visible in metrics and to
    an inspector.
25. **A bulk operation multiplies the commitment.** A bulk approve of documents, a bulk training completion, or
    a bulk disposition across many records commits every one at once - each an act in the audit trail. Gate a
    bulk write by its per-record class, never as clerical throughput.

(Deep detail: `references/qx-quality-and-documents.md`, `references/mfgex-and-part11.md`.)

## Edge states & special cases
Each breaks naive "advance it and close it" logic - the key rule inline, full behavior in the references.
- **Released vs Effective + revision binding** - a reference resolves to a revision; "latest Released" and "the
  effective revision" can diverge across an effective date. `references/qx-quality-and-documents.md`.
- **Training cascade** - releasing a document assigns training to whole roles/curricula; a single release can
  create many training tasks, and a bulk release is a bulk training obligation. Same file.
- **Parent/child hierarchy** - a change control with child tasks, linked documents, and training; a deviation
  with child CAPAs and effectiveness checks. Closing/deleting a parent is constrained by open children, and a
  child result (a failed effectiveness check) can force the parent back open.
- **Master template vs production record + review by exception** - the template is validated config; the
  instance is one batch dispositioned by its flagged exceptions. `references/mfgex-and-part11.md`.
- **Enforced flow + exceptions** - the production record enforces order; every override is a logged exception
  the review-by-exception step must catch. Same file.
- **Validation vs production environments** - config is validated and promoted; a production behavior is never
  proven from a validation-environment test alone. `references/mfgex-and-part11.md`.
- **Delegation / proxy signatures** - a task can be delegated but the signature records the actual signer; a
  signature meaning cannot be delegated away from the person who signs.
- **Complaint -> regulatory report** - a complaint's reportability decision and clock reach outside the QMS into
  a statutory report; the obligation persists even after the complaint record moves on.
- **Cross-record disposition consistency** - linked records must agree. A deviation reclassified to critical
  whose linked CAPA is already marked effective, or a minor deviation linked to a reportable complaint, is a
  contradiction. Check the linked records' dispositions before closing one; closing over a conflicting linked
  verdict is a compliance gap an inspector reads.

## Recovery patterns (can it be undone, and what cannot)

| Situation | Recovery path |
|---|---|
| A field was edited wrong on an open/draft record (before any step signed) | edit it again with a reason; both values persist in the audit trail - nothing is erased |
| A route step was advanced/signed too early | use the route's defined **reject/return** path if one exists (many routes are one-way past a signed approval); the advance is logged either way - there is no silent rewind |
| A record is **stuck** (in approval with no reject path, or a required task no available user can complete) | escalate to QA/admin - reassign the blocking task to an authorized role, or raise a linked correction; do not force, void, or cancel a record mid-approval to unstick it |
| A signature task was e-signed in error / by the wrong signer / with the wrong signature meaning (e.g., Reviewed where Approved was intended) | the signature and its meaning cannot be edited off; correct forward - obtain the correct signature with the right meaning, or raise a documented correction; do not attempt to alter the original, which stays in the trail |
| A document was released with the wrong content or wrong revision | release a **corrected revision** (which supersedes it) and re-cascade training; the superseded revision and its history remain |
| A document was obsoleted/retired in error | reinstate/re-release the needed revision if the lifecycle allows; open records that lost the link must be re-pointed; the obsolete action is logged |
| A change/CAPA was closed prematurely | reopening requires the route to allow it (QA/admin, logged); if there is no reopen path, raise a new linked record referencing it |
| A CAPA effectiveness check returned "not effective" | do not close over it; reopen the CAPA or raise a new linked CAPA; the failed result stays in the trail as evidence the first action did not hold |
| A deviation/NCR (or audit finding) was classified wrong (minor when it should be critical) | record a new classification disposition on the same record - correct forward; the original class and its audit-trail entry persist, and the higher class may re-trigger a deeper investigation, more approvals, or a linked CAPA |
| A **bulk** action was run in error (bulk-approved 50 documents, bulk-completed training, bulk-dispositioned) | there is no bulk undo - correct each record forward by its own class (release a superseding revision and re-cascade training per document, re-open/re-disposition per record); every original act stays in the trail, so the blast radius is per-record times N |
| A **batch/lot was released in error** | MasterControl cannot un-ship it; put the record on **hold**, drive the physical stock hold/recall in the ERP (`sap-mm` / `sap-qm`), and correct forward with a deviation - the release signature is permanent |
| An Mfg-Ex exception was suppressed/overridden and the batch shipped | cannot un-ship; investigate, raise a deviation, assess impact on the released lot, and drive any recall in the ERP/QMS - the original out-of-limit entry remains in the trail |
| A wrong disposition was already reported to a regulator | cannot unsend; file a follow-up/corrective report (e.g., a supplemental MDR) with the agency - a corrective report, not an edit |
| A training task was completed in error / on another's behalf | the training record stands in the trail; correct forward (re-assign/re-train, or a documented correction); a signed training record is not erasable |
| A configuration change was made in the production environment | a revert is itself a change-controlled, validated config action; assess validation impact first - not a simple undo, may require re-validation |
| A record/document deletion is needed | in validated production, GxP records generally cannot be deleted (blocked by design); use **void/cancel** through the defined path, logged, instead |

Reversal is almost always **correct forward**, not an undo: the original field value, step advance, signature,
disposition, released revision, and report all remain in the immutable trail. What is truly foreclosed is a
missed statutory reporting deadline and product already shipped on a bad batch release - neither is
retractable, only followed by a corrective report and a recall.

## Guardrails
- Read the record's **route + current step + open tasks + document revision/effective state + open exceptions**
  before acting; re-read at execute (steps, signatures, releases, and holds all drift as others work).
- Treat **advancing a route step, an e-signed task, an owner assignment, a disposition/verdict, a document
  release, a training completion, and a batch release** as committing compliance actions - route to the named
  approver/role, never force them, and never sign on another's behalf, share credentials, or back-date.
- **A batch/lot release commits product to ship.** Never release over an open exception, an open linked
  deviation, or a missing required signature; review by exception is only safe if every exception on the record
  is flagged and dispositioned. Check every open exception, not the summary.
- A **disposition** (deviation classification, complaint reportability, CAPA effectiveness, batch release) is a
  regulated decision with a downstream reporting clock that starts at awareness - get it right, do not guess to
  close faster.
- Never make **configuration changes in the production environment** (route templates, forms, master templates,
  exams, roles); build and validate in a validation/sandbox environment and promote under change control. A
  config change is not a data edit.
- The **audit trail is immutable**; a mistake is corrected forward with a new entry, never erased. Do not
  attempt to alter or work around it, and do not placeholder a required field, reason, or signature meaning.
- For anything in the destructive row (batch release, close/void/cancel, premature close, skip a required step,
  wrong disposition, exception override, obsolete a referenced document, delete, prod config change, credential
  sharing/back-dating): named approver, re-read of live state, and a logged reason.

## References (load on demand)
- `references/qx-quality-and-documents.md` - the route/task/signature engine; the Qx quality-event routes
  (deviation/NCR, CAPA + effectiveness verification, complaint + reportability, change control, audit +
  findings); document control (DCC) lifecycle, Released vs Effective and the effective date, revision and
  controlled-copy binding, periodic review; and the training cascade (tasks, curricula/job roles, exams).
- `references/mfgex-and-part11.md` - Manufacturing Excellence electronic batch/production records (master
  template vs production record instance, review by exception, enforced flow, in-process exceptions and
  out-of-limit handling, batch disposition/release); Part 11 electronic signatures and signature meaning,
  ALCOA+ data integrity; validated configuration vs data; and the validation-vs-production environment split.
