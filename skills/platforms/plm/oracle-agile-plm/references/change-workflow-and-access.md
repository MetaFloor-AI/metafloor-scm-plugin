# Agile PLM - change subclasses, workflow, approval, access, ERP hand-off

How controlled content actually changes and gets released, who is allowed to touch it, and how it reaches ERP.
Read when a task touches a change (ECR / ECO / MCO / SCO / deviation / stop ship), a change workflow or CCB
sign-off, roles / privileges / Discovery, or the publish hand-off to ERP. The read/write/destructive
classification lives in SKILL.md - this file is the "how the change process behaves" detail.

## Contents
- The change subclasses and their blast radius
- The change workflow (statuses)
- CCB, Change Analyst, and e-signature approval
- Redlines
- Deviation and Stop Ship
- Roles, privileges, and Discovery
- Publish / export to ERP

## The change subclasses and their blast radius
Agile splits "change" into subclasses. Same word, very different blast radius - **classify by the subclass**:
- **ECR (Engineering Change Request)** - requests/analyzes a change; it does not itself revise anything.
  Reversible while a draft. An approved ECR typically drives an ECO. It is the "should we?" object.
- **ECO (Engineering Change Order)** - the revising change: creates a **new item revision**, applies the
  **redline BOM / AML / attachments**, and can change the lifecycle phase (including to Inactive/Obsolete). Its
  **Release** is the commit that creates the rev and drives downstream.
- **MCO (Manufacturer Change Order)** - changes the **AML** on the **current released revision** with **no rev
  bump**. Used to add/remove/re-prefer manufacturer parts when the item design is unchanged. Its Release
  re-points sourcing on an item whose rev number does not change - the central no-rev trap.
- **SCO (Site Change Order)** - changes **one site's** BOM/AML with **no rev bump** and no effect on common
  data or other sites. Its Release re-points that site only.
- **PCO (Price Change Order)** - changes published prices/costs (Agile PCM). Its Release re-points costing/
  sourcing economics. Gate as committing; it does not revise the item.
- **Deviation** - a bounded, time/quantity-limited authorization to **depart** from the released definition
  (e.g. use an alternate, accept an out-of-spec lot). It does **not** change the baseline. See below.
- **Stop Ship** - halts shipment/use of the affected parts (quality/safety hold). A fleet action. See below.

## The change workflow (statuses)
- A change runs a **workflow** made of **status types**, typically: **Pending -> Submit -> CCB / Review ->
  Released -> Implemented -> Complete**, plus **Hold** and **Cancel**. Sites relabel and re-order these.
- **Pending** - the draft; the change and its redlines are editable, nothing is committed. Creating a change
  and redlining it is reversible here.
- **Submit** - routes the change into review; it enters the controlled flow.
- **CCB / Review** - the Change Control Board reviews and **approves or rejects** (e-signature). A **reject**
  returns the change; it is not a release.
- **Released** - **the commit**: redlines apply, an ECO creates the new revision, an MCO/SCO re-points AML/site,
  and the change **publishes downstream**. This is the release event.
- **Implemented / Complete** - downstream has acted / the change is closed. Cancelling or closing after Released/
  Implemented does **not** undo the downstream - reverse with a new change.
- **Hold** freezes a change in place: it does not advance and its **redlines are not applied**, and depending on
  site config the change is typically not editable/routable until an authorized user (the Change Analyst or an
  approver with the privilege) takes it **off Hold** back to its prior status. A Held change is not Released and
  has driven nothing downstream - do not treat Hold as either done or cancelled; find who can lift it and why it
  was held before acting.
- **Cancel** stops the change. After any routing, read the change's **actual status**, not the fact you routed
  it - only Released drives downstream.

## CCB, Change Analyst, and e-signature approval
- The **Change Analyst** owns and routes the change - moves it between statuses, adds approvers/observers,
  drives it to Release.
- The **CCB (Change Control Board)** is the set of approvers at the review status. Approval/rejection is an
  **attributed e-signature** (often password-confirmed) and is retained in the audit trail. You cannot sign on
  another person's behalf.
- **Approval is the consequential write** in the flow - it releases or blocks the change. Never auto-approve or
  auto-release to move a change along; the sign-off is not a formality, it is the gate.

## Redlines
- Inside a change, edits to the BOM, AML, or attachments are **redlines**: staged changes shown against the
  current data. They **apply only when the change Releases**.
- Before Release the item's live tabs show the **old** data; the redline shows the **proposed** data. Reading or
  acting on the wrong one operates on the wrong record. After Release the redline becomes the live data on the
  new revision (ECO) or the current rev (MCO/SCO).

## Deviation and Stop Ship
- A **Deviation** grants **temporary, bounded** permission to depart from the released definition - for a
  **quantity** or a **date window**. The item, BOM, and AML are **unchanged**; production is authorized to
  depart within the limit. Do **not** use a deviation as a permanent fix (that needs an ECO); do not let one
  **lapse or over-run** its quantity without re-checking what shipped under it - product outside the window is
  un-authorized.
- A **Stop Ship** **halts** shipment/use of the affected parts (a quality/safety hold on the fleet). **Issuing**
  it stops product; **lifting** it resumes. Both are fleet actions - run **Where Used** to know exactly what is
  affected, and confirm the underlying issue is truly resolved (usually via a corrective ECO) before lifting.

## Roles, privileges, and Discovery
- Access is by **role**, granting **privileges**: **Discovery, Read, Modify, Create, Delete**, and specific
  action privileges (e.g. release a change, override). Privileges can be **object- and lifecycle-phase-dependent**.
- **Discovery** controls whether a user can even **see that an object exists** - below Read. An object you
  cannot discover is invisible, not merely un-editable.
- Access is **state-dependent**: a Preliminary item you could modify may become read-only once Released; "I
  could edit it yesterday" does not survive a phase change or a change to your role scope.
- **Overriding a role / privilege or Discovery** to grant access, or exporting a restricted (e.g. export-
  controlled) item, is a **compliance breach**, not a permissions shortcut - treat it as destructive, assume any
  exposure is real, and report per policy.

## Publish / export to ERP
- Releasing a change **publishes** the released item / BOM / AML downstream to the connected ERP (typically
  **Oracle ERP** via an integration). This is the **hand-off**: it hands the plant and buyers the controlled
  record to build and procure against.
- Publish is a **commit**, not a passive sync. A **premature** publish (BOM not aligned, AML wrong, effectivity
  wrong) drives manufacturing and procurement off the wrong record; a **wrong** publish can re-point buying to
  the wrong manufacturer part.
- A publish can **fail or partially apply** (an ERP-side validation error, a mapping gap, a missing material
  master): Agile shows the change Released while ERP did **not** fully accept it, so the two systems disagree.
  Check the publish/transaction status - do not assume a completed Release means ERP took it.
- A publish **cannot be cleanly retracted.** Once ERP consumed a released BOM/AML there is no "unpublish" that
  undoes the downstream - correct in Agile under a **new change** and **re-publish**, then let ERP re-align its
  material master and re-point procurement. Parts already bought reconcile on the ERP side
  (`oracle-erp`), not by editing Agile.
