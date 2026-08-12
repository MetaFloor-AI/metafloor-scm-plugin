---
name: siemens-teamcenter
description: "Siemens Teamcenter (PLM) - the safe operation of product definition and change: items and item revisions, product structure / BOMs (EBOM and MBOM, BOM View Revision), CAD datasets, revision rules and effectivity (date / unit / serial), workflows and approvals, release status and maturity, change management (problem report / ECR / ECN / ECO), variants and configurations, and access via Access Manager rules / ACLs. Use when the connected PLM is Teamcenter and the work touches product data or a change, or the user mentions Teamcenter, Active Workspace / AWC, an item or item revision, Revise vs Save As, Structure Manager / Multi-Structure Manager, a BOM View Revision (BVR), EBOM / MBOM, a revision rule (Latest Working / Latest Released / Precise), effectivity, a dataset / named reference / NX, checkout / checkin, a workflow or release status, supersede / obsolete, where-used, an ECR / ECN / ECO / problem report, or a variant / configured structure."
---

# Siemens Teamcenter - operating product definition safely

Teamcenter is the PLM system of record for **what the product is**: the parts, the revisions, the assemblies,
the CAD files, and the controlled process by which any of it changes. What makes Teamcenter dangerous is not a
single posting - it is that **a released revision is a controlled baseline the whole company builds and buys
against**. Manufacturing, procurement, and service all read the released structure through a configuration
lens (the revision rule + effectivity), so a change to a released revision, a change to effectivity, or an
obsolete of a part does not stay inside PLM - it re-points the plant and the buyers. This skill classifies
those actions so the harness can gate them, plus the config edge states (revision rules, precise/imprecise,
effectivity, variants, EBOM vs MBOM) and the recovery paths that decide whether a mistake is fixable.

## When this applies
Connector is Siemens Teamcenter and the work is product data, structure, or an engineering change. When NOT:
- a different PLM: **PTC Windchill** -> `ptc-windchill`; **Oracle Agile PLM** -> `oracle-agile-plm`
- ERP material master, the costed/planning BOM procurement and production actually consume, inventory,
  purchase orders, goods movements -> `sap-mm`
- within the Siemens family but shop-floor execution (running the MBOM to build, WIP, as-built genealogy) ->
  `siemens-opcenter`. Teamcenter defines and releases the product; the MES executes it.

Boundary with ERP/MES: Teamcenter owns the **as-designed** definition and controls its change; it **publishes** the
released EBOM/MBOM downstream. ERP (`sap-mm`) owns the material master, the manufacturing BOM used to
buy and cost, and inventory; the MES (`siemens-opcenter`) consumes the released MBOM to build. A
released Teamcenter revision or an approved change is the **upstream trigger** for an ERP BOM update and
procurement - Teamcenter does not buy parts or hold stock, ERP does not change the design.

## Contents
- Object & state model
- Vocabulary that bites
- Operations: read / write / destructive
- Reclassification rules
- Worked example (a change, end to end)
- Gotchas that bite
- Edge states & special cases
- Recovery patterns
- Guardrails
- References (separate files, loaded on demand)

## Object & state model (reason about state, not nouns)
- **Item** - the identity of a part / document / product (an Item ID). It is a container, not the design. It
  carries an item master form and **one or more Item Revisions**. Almost nothing releasable attaches to the
  bare item; it attaches to a revision.
- **Item Revision** - a specific version of the item (A, B, C…). This is the thing that actually carries the
  **structure, datasets, attributes, and release status**, and the thing a workflow releases. States (maturity):
  **Working / In-Work** -> **In Process** (locked inside an active workflow) -> **Released** (frozen baseline)
  -> superseded by a later revision (via effectivity), or **Obsolete**. Reason about the revision, never "the item".
- **BOM / product structure** - the assembly of an item revision, an ordered set of **occurrences / BOM lines**
  (child item, quantity, find number, reference designator). The structure for a revision is held by its
  **BOM View Revision (BVR)**, which has **its own release status** - releasing the item revision is not the
  same as releasing its BVR. Edited in **Structure Manager / Multi-Structure Manager (MSM)**. Detail in
  `references/bom-effectivity-and-config.md`.
- **EBOM vs MBOM** - the **engineering** (as-designed) structure and the **manufacturing** (as-planned, by
  plant/line) structure. They are different structures for the same product; an EBOM change does **not** flow to
  the MBOM by itself.
- **Dataset** - the file container attached to a revision (a CAD model, a drawing, a document), holding
  **named references** (e.g. the NX part file, the drawing sheet). Datasets are internally versioned.
- **Release status** - a status object a workflow **stamps** on a revision (and separately on a BVR) when it
  completes: e.g. **Prototype**, **Production / Released**, **Obsolete**. Multiple statuses can coexist on one
  revision, each with its **own effectivity**. The status, not the revision number, says what is usable and where.
- **Workflow (process)** - an instance of a workflow template driving **tasks** (review, approve, sign-off,
  condition, notify) that culminate in applying a release status. While an object is In Process the workflow
  controls it, not the user.
- **Change objects** - **Problem Report (PR)** -> **Engineering Change Request (ECR)** -> **Engineering Change
  Notice / Order (ECN / ECO)**. The controlled vehicle to change released content: the PR states the problem,
  the ECR proposes the solution and scope, the ECN/ECO authorizes and implements it. Detail in
  `references/change-and-release.md`.
- **Revision rule + effectivity** - the **configuration lens**. A revision rule (**Latest Working**, **Latest
  Released**, **Precise**, or by **date / unit / serial effectivity**) decides *which* revision of each child you
  see and build. Effectivity is the date or unit-number window over which a revision/occurrence is valid. Same
  assembly, different rule -> a different structure.
- **Access - Access Manager rule / ACL** - a rule tree over ownership, project/program, group, and IP / export
  (ITAR) classification decides who may read / write / release / change an object; the ACL is **state-dependent**
  (a Working object you can edit flips to read-only once Released).

## Vocabulary that bites
- **Item vs Item Revision** - the item is the identity; the **revision** carries the design, BOM, and status.
  "Change the item" almost always means **create a new revision**, not edit the item.
- **Revise vs Save As** - **Revise** makes a **new revision of the same item** (keeps the ID, the history, the
  supersede chain). **Save As** makes a **new item** (new ID, no supersede relationship). Using Save As where you
  meant Revise breaks traceability; using Revise where you meant a genuinely new part collides identities.
- **Revision rule** - the lens that resolves which revision each occurrence points to. **Latest Working** shows
  in-progress design; **Latest Released** shows what production builds; a **date/unit** rule shows what ships on
  that date or serial. The BOM you "see" is meaningless without the rule that produced it.
- **Precise vs imprecise occurrence** - an **imprecise** BOM line points at the **item** and floats to whatever
  the revision rule resolves; a **precise** line pins a **specific revision**. Releasing typically pins
  occurrences precise, so a later child revision does **not** flow into a released parent by itself.
- **BOM View Revision (BVR)** - the object that actually holds a revision's structure and carries its own
  release status. You release (and can separately fail to release) the BVR, not just the item revision.
- **EBOM / MBOM** - as-designed vs as-manufactured. The MBOM adds plant/line structure, phantom assemblies,
  consumables, and process. A designer's EBOM change is invisible to the plant until propagated to the MBOM and re-released.
- **Effectivity (date / unit / serial)** - the window a revision or occurrence is valid. Changing effectivity
  re-points which revision production uses **without editing a single BOM line** - a silent, high-blast switch.
- **Change (PR / ECR / ECN / ECO)** - the controlled path to touch released content. You do not edit a released
  revision; you raise a change, revise under it, and the **change approval is the release event**.
- **Checkout / checkin** - a **pessimistic lock** on a workspace object (revision, dataset) for edit. A
  checked-out object is locked to one user; **cancel checkout** discards **all** edits made since checkout and
  reverts to the last checkin - it is not undo-last-edit, every change since the checkout is lost.
- **Dataset / named reference** - the file container and the files inside it. Replacing a dataset or a named
  reference changes what everyone downstream consumes; the item ID and rev can look unchanged while the CAD flips.
- **Where-used / where-referenced** - the blast-radius query: which assemblies use this part, which objects
  reference this dataset. Run it **before** revising, replacing, or obsoleting anything.
- **Supersede / obsolete** - marking a revision obsolete (end of life) or superseded by a newer one. It cascades
  to every where-used assembly and to procurement (stop buying the old, buy the new). High blast.
- **In Process** - an object inside an active workflow; the workflow owns it and it is locked from ad-hoc edit.
- **Variant / configured structure** - a superset ("150%") BOM carrying option-dependent occurrences; a
  **variant rule** resolves it to a specific "100%" configured product. The structure you act on depends on the variant rule too.

## Operations: read / write / destructive
Classify every operation family by what it does to state and to the controlled baseline. The verbs below name
the action-kind; the class is the same whether the connector drives Active Workspace (AWC), the rich client,
Structure Manager, or a server integration. The harness maps the customer's real connector onto these classes.
No tool names - kinds of action.

| Class | Teamcenter operation families | Gate | Why |
|---|---|---|---|
| **Read** | open / query an item, item revision, dataset (view / download a CAD file or drawing); browse or expand a structure in Structure Manager / MSM **under a stated revision rule**; **where-used / where-referenced**; compare two structures (EBOM vs MBOM, rev A vs rev B); view release status, effectivity, workflow state and audit / signoff history, ownership and ACL | always pass | no state change; read the revision + its status + the revision rule + effectivity + ACL before any write, re-read at execute |
| **Write (reversible)** | **create a new item** (item ID + master form - reversible while Working, but note some deployments auto-number the ID, auto-assign ACLs, or **auto-launch a classification / naming-validation workflow** on create, which locks it In Process and makes it committing - not always trivially undone); **Revise** an item to create a new **Working** revision; check out and edit a **Working** (unreleased) revision or dataset; add / remove / re-quantity BOM lines on an **unreleased** BVR; attach or update a dataset on a working revision; set attributes on a working revision; create a **PR / ECR** in draft; save changes before checkin | gate one at a time | a working, uncommitted draft - not yet released, not yet in a committing workflow; low blast while it stays Working |
| **Write (committing)** | **check in** (commits the new version); **release** a revision and/or its **BVR** by completing a workflow (stamps the release status, freezes it); **approve / sign off** a workflow task; **promote a change** (ECR approved -> ECN/ECO authorized/implemented); **set or publish effectivity** on a **Working** revision that has **no** release status and **no** active workflow (the only non-destructive case; the moment the revision carries any release status or is in a workflow, an effectivity change is **destructive** - see the destructive row, this is a hard rule, not a judgment call); **publish / export** a released EBOM/MBOM to ERP / MES (the downstream hand-off); **transfer ownership** or reassign an object's **project / program** (can flip the ACL so the transferring user immediately loses access - confirm you keep the access you need before moving it) | gate + human approve | binds the controlled baseline others build and buy against, or hands it downstream; each re-points manufacturing, procurement, or access |
| **Destructive / irreversible** | **abort / abandon an in-flight workflow mid-approval** (loses the accumulated sign-offs unrecoverably and returns the object to Working - the collected approvals cannot be restored); **edit released content in place** (blocked by design - the controlled path is Revise under a change; forcing it breaks the audit chain); **de-release / remove a release status** (breaks every downstream that trusted the baseline); **supersede / obsolete a part** (cascades to all where-used assemblies + procurement); **change effectivity on a released configuration** (silently re-points which rev ships to which units/dates); **cancel / close a change after downstream implementation** (ERP/procurement already acted); **force cancel-checkout or checkin on another user's lock** (discards their work); **delete or purge** an item / revision / dataset (both blocked while referenced; a **delete** may be a soft delete an admin can restore, but a **purge is permanent** - know which the connector does); **override an Access Manager rule or IP / ITAR classification** to grant access or export | hard gate + named approver + re-read | permanent or export-controlled; re-points the whole company's structure; cannot be cleanly undone; crosses a compliance boundary |

## Reclassification rules (read this)
- **A change to a released revision is not an edit - it is a new revision under a change.** Released content is
  frozen. The only controlled path is **Revise** (new rev) inside an ECN/ECO; the change **approval** is the
  committing release. Treat any "edit the released part" request as create-revision-under-change, never in-place.
- **Releasing the item revision is not releasing the BOM.** The **BVR** carries its own status. A released item
  revision with an unreleased BVR means the structure is still uncontrolled - release/gate them as a pair, and
  read both statuses before trusting "this rev is released".
- **Effectivity is a committing (often destructive) config change, not an attribute edit.** Setting or changing
  date/unit effectivity re-points which revision production consumes without touching a BOM line. On a released
  configuration it can supersede a part in the field - gate it like a supersede, know which units/dates it moves.
- **A workflow approval is the release event.** Signing off the final task applies the release status and freezes
  the object; approving a change authorizes and implements it downstream. The approval is the most consequential
  write in the flow, not a review formality - never auto-approve to move a workflow along.
- **Obsolete / supersede is a fleet action.** It cascades to every where-used assembly and to procurement. Run
  where-used first and gate it as destructive; do not obsolete a rev to "clean up" without the blast radius.
- **An imprecise occurrence floats; a precise one is pinned.** Adding a child imprecisely means the revision
  rule decides what builds - a different rule (or a new child revision) silently changes the product. Know which
  before you rely on "the BOM".
- **Item creation escalates to committing when you cannot prove it is clean.** Creating an item is reversible in
  a vanilla deployment, but many sites auto-launch a classification / naming-validation workflow or auto-assign
  ACLs on create, which locks it In Process. If you cannot confirm the deployment does neither, gate item
  creation as committing - do not assume reversible.
- **A bulk / mass operation is the same action at fleet scale - gate at the amplified blast radius.** Mass
  revise, mass obsolete, a spreadsheet / import load, or a bulk effectivity change applies to many
  items/assemblies at once. Classify each by its per-item class, then treat the batch as the higher-blast form:
  a mass obsolete or mass effectivity change is destructive at scale and needs the destructive gate, not the
  single-item one. Read the full target set (where-used across all of it) before running it.

Universal rules to teach: read the revision + its release status + the BVR status + the **revision rule** + the
effectivity + the ACL state before any write, and **re-read at execute** (another user may have released, checked
out, or re-revised since you read); never edit released content in place, never bypass a workflow/approval or
auto-approve a change, never obsolete/supersede/replace without where-used, never change effectivity on a
released config without knowing which production it re-points, and never override an IP/ITAR classification.

## Worked example (a change, end to end)
A field problem is reported on bracket **BRK-100 rev A** (Released, Production). You **raise a PR** [write-reversible]
describing the failure, then an **ECR** [write-reversible] proposing a thicker bracket and scoping it: a **where-used**
[read] shows BRK-100 is consumed by two released assemblies, ASM-200 and ASM-210. The ECR is reviewed and
**approved into an ECN** [write-committing] - which authorizes the change. You **Revise** BRK-100 to **rev B**
[write-reversible] (Working), check out and edit the model dataset, update the drawing, and set the new geometry;
BRK-100 rev A stays frozen and untouched. You run the release **workflow** on rev B **and, as a distinct
step, on its BVR** - then read **both** statuses, since the item revision going Released does not mean the
structure did (gotcha #4). The final **sign-off** [write-committing] stamps **Released** on the revision and the
BVR and applies **unit effectivity from serial 5000 on**, so units 1-4999 keep rev A and 5000+ get rev B - no BOM
line was deleted, the effectivity did the supersede. The ECN
**publishes** [write-committing] the change to ERP, which updates its manufacturing BOM and re-points procurement to
the new part from serial 5000. Editing rev A in place instead, or flipping effectivity to "all units" without
checking the field fleet, would have retroactively invalidated already-built and shipped product.

**A destructive-recovery variant.** Suppose after release you find rev B's effectivity was set to **all units**
by mistake, and ERP already pulled the change. You cannot "un-release" rev B cleanly - de-releasing breaks the
downstream that trusted it. The forward path is a **new change**: correct the effectivity to serial 5000+ (a
controlled config change), re-publish, and let ERP re-align; rev A and rev B and both effectivity settings stay
in the audit trail. Any parts already **bought** against the wrong effectivity are not un-bought by editing
Teamcenter - that reconciles on the ERP side (`sap-mm`).

## Gotchas that bite (the real set - causal chains)
1. **The item is identity; the revision carries everything.** Structure, datasets, status, and effectivity
   attach to the **item revision**, not the bare item. Acting on "the item" without pinning the revision touches
   the wrong revision or is ambiguous across all of them.
2. **A released revision is frozen - you cannot edit it in place.** The controlled path is **Revise** to a new
   rev under a change. Forcing an edit (where config even allows it) breaks the audit chain and the baseline
   everyone downstream trusts. Old rev + new rev both persist; the old is superseded by effectivity, not erased.
3. **The BOM you see depends on the revision rule.** Latest Working shows unreleased design; Latest Released
   shows production; a date/unit rule shows what ships then. Reading or acting on a structure without knowing the
   rule reads a different product than the one that builds.
4. **Releasing the item revision is not releasing the BVR - and datasets have their own status too.** The
   structure (BVR) and the attached datasets each carry a release state separate from the item revision. A
   revision that reads "Released" can sit over a Working BVR or a Working CAD dataset - the label is trusted while
   the actual structure or file is still uncontrolled. Read the status of the structure and the datasets, not just the revision.
5. **An EBOM change does not flow to the MBOM.** Manufacturing keeps building the old MBOM until it is updated
   and re-released. A designer's change is invisible to the plant until the MBOM is propagated and published.
6. **Effectivity is a silent switch.** Changing date/unit/serial effectivity re-points which revision production
   uses with **no BOM edit visible** - it can supersede a part in the field. A wrong effectivity ships the wrong
   rev to the wrong units without an obvious change.
7. **Supersede / obsolete cascades to where-used and procurement.** Marking a rev obsolete without running
   where-used strands every assembly that still calls it and can stop or misdirect buying. It is a fleet action,
   not a cleanup.
8. **Precise vs imprecise decides whether child changes flow up.** A released parent usually pins occurrences
   **precise**, so revising a child does not appear in that parent until you re-point it; an **imprecise** line
   floats to the revision rule and can change what builds when the rule or a child rev changes.
9. **Checkout is a hard lock.** A checked-out object blocks everyone else. **Cancel checkout** discards **all**
   edits since the checkout (not just the last one) and reverts to the last checkin - the discarded work has no
   undo; forcing another user's cancel-checkout or checkin **destroys their work** the same way.
10. **An In-Process object is owned by its workflow, not you.** Editing it means the workflow must reach a task
    that allows it or be aborted; **aborting mid-approval loses the accumulated sign-offs** and returns the object to Working.
11. **A change approval is the release event.** Approving/executing an ECN/ECO applies the release and triggers
    downstream (ERP BOM update, procurement). Auto-approving to advance a workflow releases uncontrolled content.
12. **Replacing a dataset or named reference silently swaps the CAD.** The item ID and rev can look unchanged
    while the actual part file everyone downstream consumes changes - a wrong swap ships the wrong geometry.
13. **Where-used is the blast radius - skipping it is flying blind.** Before revising, replacing, or obsoleting a
    component, where-used tells you which assemblies you are about to change. Not running it means you do not know.
14. **Multiple release statuses coexist, each with its own effectivity.** "Released" is ambiguous - a revision
    can be Prototype for some units and Production for others. Read *which* status and *which* effectivity, not just "released".
15. **The ACL flips on release.** A Working object you could edit becomes read-only once Released; access is
    state-dependent, so "I could change it yesterday" does not hold after the release.
16. **IP / ITAR / export classification gates who can even read a dataset.** Publishing or transferring an object
    across a project or to ERP can be an **export-control event**; overriding the classification to grant access
    is a compliance breach, not a permissions shortcut.
17. **Publish/export to ERP/MES is a downstream hand-off.** It hands the released BOM to the plant and buyers; a
    premature or wrong publish drives manufacturing and procurement off the wrong structure. It is a commit, not a sync.
18. **Revise inherits by reference, not as an independent copy.** A new rev shares datasets and imprecise
    occurrences with its predecessor until you change them - e.g. editing a dataset on rev B that still shares a
    named reference with rev A can alter rev A's view until you explicitly override it. Assuming Revise gave you an
    isolated copy leads to editing shared content or missing that a floating child moved under you.
19. **A rejected workflow is not a release - and left the object briefly locked.** Check the object's **actual
    status** after a workflow ends, not the workflow you launched; a reject returns it to Working, an approve froze it.
20. **Delete and purge differ - and both are blocked while referenced.** You cannot remove a revision a BOM or
    dataset references. A **soft delete** may be restorable by an admin (the object moves to a deleted area), but a
    **purge is permanent** and orphans history - cutting references to force a purge recovers only from backup. Know
    which one the action performs before running it.
21. **Effectivity gaps and overlaps create ambiguous or empty configurations.** If two revisions' unit/date
    ranges overlap or leave a gap, the configured structure resolves to two revs or none for those units - a config error that mis-ships or ships nothing.
22. **Two teams, two revision rules, three structures.** Engineering on Latest Working, manufacturing on Latest
    Released, service on unit-effectivity all read the same assembly differently. Reconcile the rule before comparing BOMs or acting on a diff.
23. **A change cancelled after downstream implementation does not un-do the downstream.** Once the ECN/ECO drove
    an ERP update or a purchase, cancelling the change in Teamcenter does not un-buy parts or revert ERP - reverse it with a new change.
24. **Concurrent workflows or two changes on one revision collide.** Launching a workflow on an object already In
    Process, or two ECN/ECOs targeting the same revision, locks the object and blocks or rejects one of them - work
    stalls and edits can be lost. Read the revision's current workflow / change state before starting either, and
    do not open a second change against a revision already being changed.
25. **A dataset checkin makes a new dataset version, not a new item revision.** The CAD file can change while the
    item ID and revision look identical - "the revision didn't change so nothing changed" is a blind spot.
    Manufacturing consuming that revision picks up the swapped file; track the dataset version, not just the rev.

(Deep detail: `references/bom-effectivity-and-config.md`, `references/change-and-release.md`.)

## Edge states & special cases
Each breaks naive "read the BOM, act on the part" logic - key rule inline, full behavior in the references.
- **Revision rule / precise vs imprecise** - the same structure resolves differently by rule; precise pins a
  rev, imprecise floats. Pin the rule before reading a structure. Detail in `references/bom-effectivity-and-config.md`.
- **EBOM vs MBOM divergence** - two structures for one product; changes propagate one way (E->M) on release, not
  automatically. Compare and align before publishing. Detail in `references/bom-effectivity-and-config.md`.
- **Effectivity (date vs unit/serial), overlaps and gaps** - the window that decides which rev is used; an
  overlap or gap misconfigures the shipped product.
- **Variants & configurations** - a 150% superset BOM resolved by a variant rule to a 100% product; the
  configured structure depends on the variant rule as well as the revision rule.
- **CAD-managed structure (NX / integration)** - when the BOM comes from the CAD assembly, editing structure in
  Teamcenter vs in CAD can conflict; the authoring tool owns the structure round-trip.
- **Multiple coexisting release statuses** - Prototype + Production + Obsolete on one revision, each with its own
  effectivity; "released" alone is not a state.
- **Multiple BVRs on one revision** - a revision can carry more than one BOM view (e.g. a Design/EBOM view and a
  Manufacturing/MBOM view), each an independent BVR with its own status. A released Design BVR alongside a Working
  Manufacturing BVR on the same revision is a real trap - read the status of the specific view you act on, not "the revision".
- **Access / classification (Access Manager, IP, ITAR)** - who can read/write/release/change is rule- and
  state-driven, and export classification can block read entirely. Detail in `references/change-and-release.md`.

## Recovery patterns (can it be undone, and what cannot)

| Situation | Recovery path |
|---|---|
| A working (unreleased) revision was edited wrong | edit it again or **cancel checkout** to revert to the last checkin - reversible while Working; nothing was released |
| A revision was released by mistake | you cannot cleanly edit it - **Revise** to a new rev under a change and re-release; **de-releasing** breaks downstream trust and is a controlled last resort, not an undo |
| The item revision released but its **BVR** did not (or one BVR view did, another did not) | the structure is not controlled - run the release workflow on the specific BVR (or revise and re-release both together); check every view's status, do not trust the item-revision status alone |
| The inverse - a **BVR released but the item revision is still Working** | the structure is controlled but the revision's attributes/datasets are not; release (or re-verify) the item revision too before trusting the baseline - a released structure on an unreleased revision is a half-controlled state |
| An object was **soft-deleted** (not purged) | an admin can usually restore it from the deleted area while it has not been purged; a **purged** object is gone - recover only from backup |
| Effectivity was set wrong on a released config | correct it with a **new controlled config change** (itself committing); the window may have already driven production/buying, which reconciles on the ERP side |
| A part was obsoleted / superseded in error | raise a **new change** to reinstate / re-release; procurement and ERP may already have acted on the obsolete - reconcile downstream separately |
| A workflow was aborted mid-approval | the object returns to Working and the collected sign-offs are lost; restart the workflow from the beginning |
| A checkout was cancelled and edits lost | the edits are gone (reverted to last checkin); redo them - there is no undo for cancelled-checkout work |
| Another user's lock was force-broken | their in-progress work is discarded; it cannot be recovered - avoid force-breaking a lock, coordinate instead |
| A change was cancelled after ERP/procurement implemented it | Teamcenter cancelling does not revert ERP or un-buy parts; reverse with a **new change** and let ERP re-align (`sap-mm`) |
| An item / revision / dataset was purged | permanent; blocked while referenced, and a forced purge orphans history - recover only from backup |
| An IP / ITAR classification was overridden | a compliance incident, not a technical rollback - restore the classification and report per policy; assume the exposure happened |

Reversal in Teamcenter is almost always a **new revision or a new change**, not an undo: the old revision, the
change, the workflow sign-offs, and both effectivity settings stay in the audit trail. What is truly gone is any
work lost to a cancelled checkout, any purge, and any downstream (parts bought, ERP updated, product shipped) an
earlier release already drove.

## Guardrails
- Read the item + the specific **revision** + its release status + the **BVR** status + the **revision rule** +
  effectivity + the ACL/classification before acting; re-read at execute **and again after any gate approval**
  (state can change between approval and execution, especially under concurrent workflows). A structure read
  without its revision rule is not a fact.
- Never edit released content in place - **Revise** to a new rev under a change; the change approval is the release.
- Never obsolete / supersede / replace a component, or swap a dataset, without running **where-used /
  where-referenced** first - that is the blast radius.
- Never change effectivity on a released configuration without knowing which units/dates it re-points; treat it
  as a supersede.
- Never bypass or auto-approve a workflow or a change to move it along; never override an IP / ITAR
  classification or an Access Manager rule to grant access or export.
- Never force a cancel-checkout or checkin on another user's lock - their work is destroyed and unrecoverable.
- Teamcenter deployments are heavily configured: workflow templates, change object types, release statuses, and
  ACL/classification rules vary by site. Read the actual deployed configuration - do not assume the standard
  object names or workflow steps are the ones in front of you.
- For anything in the destructive row (edit-released, de-release, supersede/obsolete, released-effectivity
  change, change-cancel-after-implementation, purge, classification override, abort-workflow-mid-approval, any
  mass/bulk variant of these): named approver, re-read, and log the reason.

## References (load on demand)
- `references/bom-effectivity-and-config.md` - item/revision/BVR structure, EBOM vs MBOM and propagation,
  revision rules (Latest Working / Latest Released / Precise / by-effectivity), precise vs imprecise occurrences,
  date/unit/serial effectivity with overlaps and gaps, variants and configured structures, and structure compare.
- `references/change-and-release.md` - the change lifecycle (PR -> ECR -> ECN/ECO), workflow templates / tasks /
  sign-off and release statuses, checkout/checkin locking, Access Manager rules / ACLs / ownership / IP-ITAR
  classification, and the publish/export hand-off to ERP and MES.
