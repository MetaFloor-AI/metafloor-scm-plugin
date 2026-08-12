# MasterControl Qx - quality events, routes, documents, and training (deep reference)

Load when reasoning about a specific quality-event route, a document's release/effective/revision state, or
the training cascade. SKILL.md carries the operating judgment and the read/write/destructive matrix; this
file carries the mechanics. One fact lives in one place - the classification stays in SKILL.md.

## Contents
- The route and task engine
- Signatures on a route
- Deviation / Nonconformance (NCR)
- CAPA and effectiveness verification
- Customer complaint and reportability
- Change control
- Audit and findings
- Document control (DCC): lifecycle, Released vs Effective, revisions
- The training cascade

## The route and task engine
Every Qx record moves through a **route** built from a **route template**. A template is an ordered set of
**steps**; each step issues one or more **tasks** to users or roles. The record advances only when the
required tasks of the current step complete. Common step kinds:
- **Collaboration / Author** - draft the content; multiple contributors; no signature required.
- **Review** - a reviewer checks and signs (meaning = Reviewed).
- **Approval** - one or more approvers sign (meaning = Approved); often parallel or sequential.
- **Release** - the final commit that makes a document effective / issues the record downstream.

Route facts that bite:
- A **required task** blocks the step; the record cannot advance around it, and only its assignee (or a
  delegate) can complete it.
- **Parallel vs sequential** approval changes who must sign and in what order; a parallel step needs all
  signatures before it advances.
- **Escalation / timeout** can reassign or escalate an idle task to a manager, who may then hold or sign it.
- **Cancelling/restarting** a route voids in-flight tasks and can reset signatures already collected;
  restarting re-issues them.
- A **reject/return** action (if the template defines one) is the only clean backward move; without it, past a
  signed approval the route is effectively one-way and a mistake is corrected forward.

## Signatures on a route
Completing a **signature task** captures the signer + a **signature meaning** (Authored / Reviewed / Approved /
Released, from a controlled set) + a timestamp, bound to the record. Properties to hold:
- Permanent and attributable; it cannot be removed or edited. A wrong signer or meaning is corrected forward.
- **Never** sign on another's behalf, share credentials, or back-date; each is a data-integrity violation.
- **Delegation/proxy** is allowed where configured, but the signature records the actual signer and that it
  was by proxy - the accountability does not transfer to the delegator.

## Deviation / Nonconformance (NCR)
A departure from a requirement, procedure, or spec. It routes through intake -> assessment -> investigation
(root cause) -> disposition -> closure. Key points:
- **Classification** (minor / major / critical) is a disposition that sets the investigation depth, the
  approval level, and the timeline - a wrong class under- or over-scopes the event.
- It commonly spawns a **child CAPA**; the parent cannot close cleanly while a required child is open.
- The physical disposition of any affected stock (block / scrap / return) posts in the ERP, not here
  (`sap-mm` / `sap-qm`); MasterControl carries the quality decision and its signatures.

## CAPA and effectiveness verification
A CAPA record lists corrective and preventive actions, each often a task; implementation gates on those tasks
(and any linked SOP reaching Effective + training done). The trap is closure:
- **"Implemented" is not "effective."** An **effectiveness verification/check** is a separate, scheduled task
  (days/weeks out) that proves the action worked. Closing on implementation alone skips the proof.
- A **not-effective** result should reopen the CAPA or raise a new linked one; do not close over it. The failed
  result stays in the trail as evidence the first action did not hold.

## Customer complaint and reportability
Intake **logs awareness**, which **starts the regulatory clock**. The record carries the product/issue, an
investigation, and the pivotal **reportability / adverse-event assessment**:
- **Reportability** decides whether a regulatory report is due (MDR to FDA, MIR/vigilance in EU) and by when
  (e.g., 30-day, or 5-day for certain events). The clock runs from awareness, not from your convenience.
- A wrong **non-reportable** call is the highest-risk action in the QMS - it misses a statutory deadline that
  no forward correction fully repairs, only a late/supplemental report.
- The report itself is filed to the agency (often via a connected regulatory system); once sent it cannot be
  unsent - a correction is a supplemental report.

## Change control
A controlled change with an impact/risk assessment, an approval route, and linked deliverables (revised
documents, training, validation tasks). Closure discipline:
- Implementation typically gates on the linked SOP reaching **Effective** and **training complete**. Closing
  the change before the effective date or before training closes marks it done while the floor still runs the
  old SOP and the workforce is unqualified - a premature close and an audit gap.
- Reopening a closed change is restricted (QA/admin, logged) or impossible; if there is no reopen path, raise a
  new linked change referencing it.

## Audit and findings
Internal, supplier, or external audits carry **findings/observations**, each with a **severity** disposition
and often a linked CAPA. A finding's severity drives escalation and timelines; grading it wrong mis-routes the
response. Supplier-audit findings can gate a supplier's approved status.

## Document control (DCC): lifecycle, Released vs Effective, revisions
Controlled documents (SOPs, specs, forms, work instructions) live in the Document Control Center. Lifecycle:
**Draft -> In Review/Collaboration -> Approval (routed, e-signed) -> Released -> Effective -> Periodic Review
-> Obsolete/Retired.**
- **Released vs Effective:** Released = approved and issued; Effective = in force on the **effective date**. A
  future-dated release means the new revision is not yet controlling; the prior revision still governs until
  the effective date. Acting early uses a document not in force; ignoring the old one runs a stale SOP.
- **Revision binding:** a new revision supersedes the prior; a record that references a document binds to a
  **revision**, not "latest". "Latest Released" and "the effective revision" can differ across an effective
  date. Printed/**controlled copies** must track the effective revision; uncontrolled prints go stale silently.
- **Periodic review:** a scheduled re-review generates a task on its due date; an ignored review is an overdue,
  inspectable item. Extending or waiving it is a controlled decision, not an operator edit.
- **Obsolete/retire:** removing a Released document referenced by open records or trained curricula strands
  links and de-qualifies training; it is a destructive control change, not housekeeping.

## The training cascade
Training is tied to documents and job roles/curricula:
- **Release auto-assigns training.** When a document is released (or a change control's training requirement
  fires), **training tasks** auto-assign to the mapped **job roles / curricula**. A single release can create
  many training tasks; a bulk release is a bulk training obligation.
- **Completion is an e-signed training record;** some require passing an **exam/assessment**. A failed exam
  leaves the task open and the person unqualified.
- **"Effective" is not "trained."** Until training completes, operators are unqualified on the current SOP - an
  audit gap and a reason a change control is not truly implemented. Do not treat a document going effective as
  the workforce being ready.
- Completing training on another's behalf, or back-dating it, falsifies the training record - the record
  captures the actual signer and timestamp.
