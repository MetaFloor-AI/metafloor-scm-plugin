# Teamcenter - change management, workflow, release, access

How controlled content actually changes and gets released, and who is allowed to touch it. Read when a task
touches a change (PR / ECR / ECN / ECO), a workflow or sign-off, a release status, checkout locking, access /
ACLs, or the publish hand-off to ERP/MES.

## Contents
- The change lifecycle (PR -> ECR -> ECN/ECO)
- Workflow, tasks, and sign-off
- Release statuses and maturity
- Checkout / checkin locking
- Access Manager, ACLs, ownership, IP / ITAR
- Publish / export to ERP and MES

## The change lifecycle (PR -> ECR -> ECN/ECO)
The controlled vehicle to change **released** content. Editing a released revision directly is not allowed; you
change it under a change object.
- **Problem Report (PR)** - states a problem/defect against released product. Identity of "what is wrong",
  not yet a solution. Creating one is reversible (a draft record).
- **Engineering Change Request (ECR)** - proposes a solution and **scopes** it: which items/revisions are
  affected (validated with **where-used**), the disposition of existing stock/product, cost/impact. The ECR is
  reviewed and either rejected or **approved into** an ECN/ECO. Approval is the decision gate.
- **Engineering Change Notice / Order (ECN / ECO)** - **authorizes and implements** the approved change: the new
  revisions are created and released under it, and it is the object that **drives downstream** (ERP BOM update,
  procurement re-point). Approving/executing the ECN/ECO **is the release event** - the most consequential write.
- After downstream implementation the change is effectively spent: cancelling it in Teamcenter does **not** undo
  the ERP update or un-buy parts. Reverse an implemented change with a **new change**, not by cancelling the old.

## Workflow, tasks, and sign-off
- A **workflow process** is an instance of a **workflow template** (a route). It drives **tasks**: review,
  **approve / sign-off** (may need multiple approvers / quorum), **condition** (branch on a rule), **notify**,
  and a final task that **applies the release status**.
- While an object is **In Process** the workflow owns it - it is locked from ad-hoc edit. Edits happen only at a
  task that permits them, or after the workflow ends.
- **Sign-off is the commit.** The final approval applies the release status and freezes the object/BVR. A
  **rejected** workflow returns the object to **Working** - a reject is not a release. After any workflow ends,
  read the object's **actual status**, not the workflow you launched.
- **Aborting a workflow mid-approval** loses the accumulated sign-offs and returns the object to Working; the
  route restarts from the beginning. Do not abort to "fix one field" if sign-offs are already collected.
- Digital signatures / approvals are attributed and retained in the audit trail; you cannot sign on another's behalf.

## Release statuses and maturity
- A **release status** is a named status object (**Prototype**, **Pre-Production**, **Production / Released**,
  **Obsolete**…) a workflow stamps on a revision **and separately on a BVR**.
- **Multiple statuses coexist** on one revision, each with its **own effectivity** - a revision can be Production
  for some units and Prototype for others. "Released" alone is not a state; read *which* status and *which*
  effectivity.
- A **Released** revision is a **frozen baseline**: read-only for most, changed only by revising under a change.
- **De-release / remove status** is a controlled, rare action that breaks every downstream that trusted the
  baseline - prefer a new revision. **Obsolete** ends a revision's life and **cascades** to where-used assemblies
  and procurement (stop buying it) - run where-used first.

## Checkout / checkin locking
- Teamcenter uses **pessimistic locking**: **checkout** locks a workspace object (revision, dataset) to one user
  for edit; others get read-only until checkin.
- **Checkin** commits the edits as a new version and releases the lock. **Cancel checkout** discards the
  in-progress edits and reverts to the last checkin - there is **no undo** for the discarded work.
- **Forcing** a cancel-checkout or checkin on **another user's lock** (an admin/override action) **destroys their
  in-progress work** unrecoverably. Coordinate; do not force-break a lock to proceed.
- An object cannot be edited while **In Process** in a workflow even if not checked out - the workflow controls it.

## Access Manager, ACLs, ownership, IP / ITAR
- **Access Manager** is a rule tree evaluated top-down: rules keyed on object type, **status**, **owning
  user/group**, **project/program membership**, and **classification** grant or deny read / write / **release** /
  change / delete.
- Access is **state-dependent**: a Working object you can edit flips to **read-only** for most once **Released**.
  "I could change it yesterday" does not survive a release.
- **Ownership / project transfer** changes who controls and who can see an object. Moving it out of a project can
  lock out the original team or expose it to a new group - a committing access change.
- **IP / export classification (ITAR / EAR)** can block **read** entirely for un-cleared users. **Publishing or
  transferring** a classified object across a project boundary or to an external system (including ERP) can be an
  **export-control event**. Overriding a classification to grant access or move data is a **compliance breach**,
  not a permissions shortcut - treat it as destructive, assume any exposure is real, and report per policy.

## Publish / export to ERP and MES
- Teamcenter **publishes** the released EBOM/MBOM and item/master data downstream (to ERP such as SAP, and to the
  MES). This is the **hand-off**: it hands the plant and buyers the controlled structure to build and procure against.
- Publish is a **commit**, not a passive sync. A **premature** publish (structure not aligned, MBOM not
  released, effectivity wrong) drives manufacturing and procurement off the wrong baseline; a **wrong** publish
  can re-point buying to the wrong part.
- Downstream does not flow back into the design: ERP owns the material master, costing, and inventory
  (`sap-mm`); the MES consumes the released MBOM to build (`siemens-opcenter`). Reconcile a
  bad publish by correcting in Teamcenter and **re-publishing** under a change, then letting ERP/MES re-align -
  editing the design on the ERP side is not the fix.
