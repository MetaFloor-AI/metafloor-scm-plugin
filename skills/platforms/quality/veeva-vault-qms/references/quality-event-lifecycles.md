# Veeva Vault QMS - quality-event lifecycles and workflow mechanics

The per-object-type state machines and the routing engine behind them. State names are configured per
customer; treat the sequences here as the typical Veeva best-practice shape, and read the actual lifecycle
on the record. Read when a task advances a state, completes a task, or reasons about what a state entry fires.

## Contents
- How lifecycles, states, and state types fit together
- Workflows, tasks, and lifecycle actions
- Deviation / Nonconformance
- CAPA and the effectiveness check
- Complaint and reportability
- Change control
- Audit and findings
- Parent/child hierarchy and multi-record workflows

## How lifecycles, states, and state types fit together
- A **lifecycle** is the ordered set of **states** a record moves through, plus the actions/workflows that
  move it. Each object type has its own lifecycle.
- A **lifecycle state** is a named node (Draft, In Approval, Closed). Advancing to the next state is a
  **state change** - the committing act that fires automation.
- A **state type** is Vault's normalized category behind a state (Starting, In Progress, Complete,
  Cancelled). Reports, metrics, cross-lifecycle logic, and some automations key off the **state type**, not
  the display name - so two lifecycles with a "Complete" type can have differently named final states.
- **State-entry criteria / required fields**: a record cannot enter a state until mandatory fields are
  populated and required tasks are done. This is the compliance gate, not a UI nicety.

## Workflows, tasks, and lifecycle actions
- A **workflow** routes a record and issues **tasks** to **roles/users**. The record does not advance until
  required tasks complete; a task can **require an e-signature** to finish (see the Part 11 reference).
- **Entry actions** fire automatically on entering a state: lock fields, create a child record (a CAPA off a
  deviation, an effectiveness check off a CAPA), send notifications, set/start a due-date or SLA clock, update
  a status field. This is why a state change is never "just a status".
- **User actions** are manual buttons a role can invoke (e.g., "Send for approval", "Reopen"); **event
  actions** fire on system events. What is available depends on the state and the user's role.
- **Object (multi-record) workflows** can act on several records at once; **legacy document workflows** route
  documents. The e-signature and task mechanics differ slightly - read which drives the record.
- Cancelling a running workflow voids its open tasks and can roll routing back; restarting re-issues tasks and
  can reset approvals already collected. Reassigning an open task changes the assignee without a state change.

## Deviation / Nonconformance
Typical: **Draft/Initiated -> Triage/Assessment -> Investigation/In Progress -> In Approval -> Closed**
(off-path **Cancelled/Void**).
- **Triage** records the **classification** disposition (minor / major / critical) - it sets the
  investigation depth, timeline, and required approvals. A wrong classification under-scopes a serious event.
- **Investigation** documents root cause; it commonly spawns a linked **CAPA**.
- **In Approval** routes a QA e-signature; **Closed** locks the record. Closing without documented root cause
  or the required QA sign-off is a premature closure and an audit gap.

## CAPA and the effectiveness check
Typical: **Draft -> Action Plan -> Implementation -> Pending Effectiveness -> Closed**.
- The **action plan** lists corrective and preventive actions; some reference **SOPs** in QualityDocs and gate
  implementation on those documents reaching **Effective** and training completing.
- **Implementation** completing does not equal effectiveness. The **effectiveness check** is a separate,
  scheduled verification (often 30-180 days out) created as its own task/record with entry actions.
- The check returns a **verdict**: **effective** -> closure is truthful; **not effective** -> reopen the CAPA
  or raise a new linked one. Closing before the check completes, or over a not-effective result, is the
  classic CAPA gap inspectors look for.

## Complaint and reportability
Typical: **Intake -> Investigation -> Reportability Assessment -> (Regulatory Report) -> CAPA (if needed) ->
Closed**.
- **Intake** logs awareness - which starts the regulatory clock.
- **Reportability assessment** is the disposition: is this a reportable event (MDR to FDA, MIR/vigilance in
  EU, medical-device or pharmacovigilance rules)? The decision sets whether a report is due and its deadline
  (e.g., 30-day, or 5-day for certain events). A wrong non-reportable call misses a statutory deadline.
- The report may push to a connected **Safety/RIM** vault (cross-vault); the obligation and clock live partly
  there. A CAPA is linked when the complaint reveals a systemic issue.

## Change control
Typical: **Draft -> Impact/Risk Assessment -> Approval -> Implementation -> Verification/Closure**.
- The change lists **affected items**: SOPs (QualityDocs), equipment, products, other records.
- **Implementation** commonly gates on the new document version reaching **Effective** and training done;
  closing before that leaves the change unimplemented in fact while the record reads complete.
- **Verification** confirms the change achieved its purpose before **Closure**.

## Audit and findings
Typical audit: **Planned -> Scheduled -> In Progress/Fieldwork -> Findings/Observations -> Response ->
Closed**.
- **Findings/observations** carry a **severity** disposition (critical / major / minor); each may require a
  response and a linked **CAPA**.
- The audit does not close cleanly until findings are dispositioned and their CAPAs/responses are resolved.

## Parent/child hierarchy and multi-record workflows
- Quality events form a hierarchy: a deviation (parent) with child CAPAs and effectiveness checks; a complaint
  with a linked investigation and CAPA; an audit with findings and their CAPAs.
- **Referential integrity** blocks deleting a parent with children; a child result can force the parent back
  open (a failed effectiveness check reopens the CAPA, which can reopen the deviation).
- A **multi-record workflow** can advance or approve several linked records with one signed task - so a bulk
  approve is a bulk commitment, not a single-record convenience.
