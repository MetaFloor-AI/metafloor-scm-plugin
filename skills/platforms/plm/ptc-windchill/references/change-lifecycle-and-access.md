# Windchill - change management, lifecycle, promotion, checkout, access

How controlled content actually changes and gets released, and who is allowed to touch it. Read when a task
touches a change (PR / CR / CN / Change Task), a lifecycle state or promotion request, a workflow / vote, check-out
locking, access (contexts / domains / policies / OIRs / IP-ITAR), or the ESI publish hand-off to ERP / MES.

## Contents
- The change lifecycle (PR -> CR -> CN -> Change Task)
- Lifecycle states, promotion requests, and Set State
- Workflow and voting
- Check-out / check-in, workspace vs commonspace
- Contexts, domains, policies, OIRs, IP / ITAR
- ESI publish / export to ERP and MES

## The change lifecycle (PR -> CR -> CN -> Change Task)
The controlled vehicle to change **released** content. Editing a released revision directly is blocked by
lifecycle policy; you change it under a change object. (Windchill Change Management follows a CMII-style flow;
sites relabel objects, and some call the Change Notice an ECN / ECO.)
- **Problem Report (PR)** - reports a problem / defect against released product. Identity of "what is wrong", not
  yet a solution. Creating one is reversible (a draft record).
- **Change Request (CR)** - analyzes and **proposes** a solution, and **scopes** it: which parts / revisions are
  affected (validated with **where-used**), disposition of stock / product in the field, cost / impact. The CR is
  reviewed and either rejected or **approved into** a Change Notice. Approval is the decision gate.
- **Change Notice (CN)** - **authorizes and implements** the approved change. It carries **Change Tasks / Change
  Activities**, each listing **Affected objects** (the existing revisions being changed) and **Resulting objects**
  (the new revisions produced). **Completing the CN is the release event** - it drives the resulting revisions to
  Released and triggers downstream (ERP BOM update, procurement re-point). The most consequential write.
- After downstream implementation the change is effectively spent: cancelling the CN in Windchill does **not**
  undo the ERP update or un-buy parts. Reverse an implemented change with a **new change**, not by cancelling the old.
- A **Variance / Deviation / Waiver** grants temporary, bounded permission to depart from the released definition;
  it does not change the baseline.

## Lifecycle states, promotion requests, and Set State
- A **lifecycle template** drives an object through states - typically **In Work -> Under Review -> Released ->
  (Obsolete / Superseded)** (configurable per template). The state, evaluated against **domain policy**, decides
  who can read / modify and whether the object is frozen. A **Released** object is a read-only baseline.
- A **Promotion Request** moves a **set of objects** to a target lifecycle state (e.g. In Work -> Released),
  routed for review / approval. It is **lighter than a Change Notice**: it changes state only, creates **no
  revision**, and carries **no change audit**. Use it for governed state changes that are not a formal engineering
  change; do **not** use it to slip changed released content out without the change process.
- **Obsolete** ends a revision's life and **cascades** to where-used assemblies and procurement (stop buying it) -
  run where-used first. **Demote / revert state / de-release** is a controlled, rare action that breaks every
  downstream that trusted the baseline - prefer a new revision.
- **Set State** is an admin action that changes lifecycle state **directly**, bypassing promotion / change and
  their approvals and audit. It is a governance shortcut - treat any Set-State around a controlled process as destructive.

## Workflow and voting
- Promotion requests and change objects run on **workflow processes** (instances of workflow templates) that drive
  tasks: review, **vote / approve** (may need multiple approvers / a quorum), decision branches, notify, and a
  final task that **applies the lifecycle state / completes the change**.
- While an object is under an active workflow it is controlled by that process - it is not freely editable; edits
  happen only at a task that permits them, or after the workflow ends.
- **The final vote is the commit.** It applies the release / completes the CN and freezes the object. A **rejected**
  workflow returns the object to its **prior state** - a reject is not a release. After any workflow ends, read the
  object's **actual lifecycle state**, not the request you launched.
- **Aborting a workflow mid-approval** loses the collected votes and returns the object to its prior state; the
  route restarts from the beginning. Votes / signatures are attributed and retained in the audit trail; you cannot vote on another's behalf.

## Check-out / check-in, workspace vs commonspace
- Windchill uses **pessimistic locking**. **Check out** locks a workspace object (part, CAD document) to one user
  and, for CAD, copies it into the user's **workspace** (Creo / Windchill Workgroup Manager); others get read-only
  until check-in. The **commonspace** is the shared Windchill database.
- **Check in** commits the edits as a **new iteration** and releases the lock. **Undo checkout** discards the
  in-progress edits and reverts to the last checked-in iteration - there is **no undo** for the discarded work.
- **Forcing** an undo-checkout or check-in on **another user's checkout** (an admin / override action) **destroys
  their in-progress work** unrecoverably. Coordinate; do not force-break a lock to proceed.
- **Upload** copies workspace file content to the server **without** checking in; only **check in** creates the new
  iteration in the commonspace. An object under an active workflow / change may be locked from ad-hoc edit even if not checked out.

## Contexts, domains, policies, OIRs, IP / ITAR
- Data lives in a **context**: **Product**, **Library**, **Project**, **Program**, or **Organization**. Each
  context has a **team** (roles - e.g. Guest, Member, Product Manager) and an administrative **domain**.
- **Access control** is a **policy** of ACL rules attached to a **domain + object type + lifecycle state +
  participant (role / group)**, granting Read / Modify / Create / Delete / Revise / Set-State / etc., plus optional
  **ad-hoc ACLs** on individual objects. Access is **state-dependent**: a Working object you can modify flips to
  read-only for most once **Released**.
- **OIRs (Object Initialization Rules)** run on **create** and set defaults - **auto-numbering**, the **lifecycle
  template**, the **team / owning context**, and sometimes an **auto-checkout** or attribute default. This is why
  "create a part" is not always a clean, reversible In-Work draft - the OIR may place it in a controlling state or process.
- **Ownership / context transfer** changes who controls and who can see an object; moving it out of a context can
  lock out the original team or expose it to a new group - a committing access change.
- **IP / export classification (ITAR / EAR)** can block **read** entirely for un-cleared users. **Publishing or
  transferring** a classified object across a context boundary or to an external system (including ERP) can be an
  **export-control event**. Overriding a classification or a policy to grant access or move data is a **compliance
  breach**, not a permissions shortcut - treat it as destructive, assume any exposure is real, and report per policy.

## ESI publish / export to ERP and MES
- Windchill **publishes** the released part / EBOM / MBOM and item data downstream (to ERP such as SAP, and to the
  MES) via **ESI (Enterprise Systems Integration)** or an equivalent connector. This is the **hand-off**: it hands
  the plant and buyers the controlled structure to build and procure against.
- Publish is a **commit**, not a passive sync. A **premature** publish (Manufacturing view not aligned / released,
  effectivity wrong) drives manufacturing and procurement off the wrong baseline; a **wrong** publish can re-point
  buying to the wrong part.
- Downstream does not flow back into the design: ERP owns the material master, costing, and inventory
  (`sap-mm`); the MES consumes the released MBOM to build. Reconcile a bad publish by correcting in
  Windchill and **re-publishing** under a change, then letting ERP / MES re-align - editing the design on the ERP side is not the fix.
- A publish can **fail or partially apply** (a validation error on the ERP side, a mapping gap, a missing material
  master) - the release stays committed in Windchill while ERP did not fully accept it, so the two systems now
  disagree. Check the publish / ESI transaction status, do not assume a completed release means ERP took it.
- A publish **cannot be cleanly retracted.** Once ERP consumed a released BOM there is no "unpublish" that undoes
  the downstream - the forward fix is to correct in Windchill under a change and **re-publish**, and let ERP re-align
  its material master and re-point procurement. Reconcile parts already bought on the ERP side, not by editing Windchill.
- Do not confuse the **visualization publish** (Creo View representations / viewables, produced by Windchill
  Visualization Services) with the **ESI structural publish** to ERP - the first makes a viewable, the second hands off the BOM.
