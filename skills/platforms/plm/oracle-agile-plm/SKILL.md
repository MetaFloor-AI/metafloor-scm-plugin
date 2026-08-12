---
name: oracle-agile-plm
description: "Oracle Agile PLM (Agile 9 / A9) - the safe operation of product definition and change: items and item revisions (lifecycle phases Preliminary / Prototype / Production / Inactive, plus a change-driven Pending revision state), BOMs and AML/AVL (approved manufacturer / vendor list, manufacturer parts / MPNs), redline BOM/AML, change management (ECR, ECO, MCO manufacturer change order, SCO site change order, deviation, stop ship), CCB approval routing, change analyst, sites, effectivity, file folders, and PG&C product compliance. Use when the connected PLM is Oracle Agile (not Windchill or Teamcenter) and the work touches an item, a revision, a BOM or AML, or a change; or the user mentions Agile PLM, Agile 9 / A9, an ECR / ECO / MCO / SCO, a deviation or stop ship, AML / AVL / manufacturer part / MPN, a pending revision, redline BOM, CCB / change analyst, a lifecycle phase, sites, PG&C / RoHS / REACH, or a file folder. Not Agile PLM for Process (recipe / spec) - a different product."
---

# Oracle Agile PLM - operating product definition safely

Oracle Agile PLM (Agile 9, also called A9) is the PLM system of record for **what the product is**: the
items, their revisions, the BOMs, the approved manufacturers, the attachments, and the controlled process by
which any of it changes. What makes Agile dangerous is not a single posting - it is that **a released item is
a controlled baseline the whole company builds and buys against**, and **the change objects that touch it
propagate straight to manufacturing and procurement**. Releasing an ECO creates a new revision; releasing an
MCO re-points the approved manufacturers with **no revision bump at all**; a deviation authorizes production
to depart from the baseline; a stop ship halts it. This skill classifies those actions so the harness can
gate them, plus the Agile-specific edge states (change-driven revisioning, the MCO/SCO no-rev traps, redlines,
pending vs released revisions, AML/AVL sourcing, sites, effectivity) and the recovery paths that decide
whether a mistake is fixable.

## How Agile differs from Teamcenter / Windchill (read this)
Do not carry the peer model across. In Teamcenter and Windchill a user **Revises** an item as a direct
action. **Agile has no standalone Revise** - a new revision exists only when you put the item on a change
(an ECO) and **release** that change; before release it is a **Pending** revision. Agile also splits change
into **several subclasses with different blast radius** (ECR, ECO, MCO, SCO, deviation, stop ship), and two
of them - **MCO and SCO** - change sourcing or site data **without creating a new revision**. That no-rev
change is the Agile trap the peer systems do not have.

## When this applies
Connector is Oracle Agile PLM and the work is product data, an AML/AVL, or a change. When NOT:
- a different PLM: **Siemens Teamcenter** -> `siemens-teamcenter`; **PTC Windchill** ->
  `ptc-windchill`. The vocabulary differs (Agile has MCO/SCO, AML, redlines, lifecycle phases,
  file folders; the others have BVRs / config specs, WTPart / EPMDocument) - do not carry one across.
- the ERP material master, the manufacturing/costed BOM procurement and production actually consume,
  inventory, purchase orders, goods movements -> **Oracle ERP** `oracle-erp`.
- **Agile PLM for Process** (recipe / formulation / spec management for food / CPG / pharma) is a **different
  Oracle product** with a different model - this skill does not apply there.

Boundary with ERP: Agile owns the **as-designed** item, its BOM, and its AML, and controls their change; it
**publishes** the released item / BOM / AML downstream. Oracle ERP (`oracle-erp`) owns the material
master, the manufacturing BOM used to buy and cost, and inventory. A released Agile change is the **upstream
trigger** for an ERP BOM/AML update and procurement - Agile does not buy parts or hold stock, ERP does not
change the design.

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
- **Item** - the identity of a **Part** or a **Document** (an item number). It carries a Title Block, a
  **BOM**, an **AML**, attachments, sites, compliance, and **one or more revisions**. Reason about the
  revision, not the bare item.
- **Item revision** - a specific version of the item (Introductory, A, B, C…). Each revision carries its own
  **BOM, AML, attachments, and lifecycle phase**. A new revision is **created by releasing an ECO**, not by a
  user action. The initial **Introductory** revision can exist without a change; every later revision requires
  a released ECO.
- **Revision state (relative to a change)** - a revision introduced by an **unreleased** change shows as
  **Pending** (the change number in parentheses); it becomes the **current Released** revision only when the
  change releases. "Pending" is a change-relative state, distinct from the lifecycle phase attribute below.
- **Lifecycle phase** - a configurable attribute on the revision (commonly **Preliminary -> Prototype ->
  Production/Released -> Inactive/Obsolete**). It says what the item is fit for; it is **separate** from
  whether a change is released. A Production item can still have an open Pending change against it.
- **BOM** - the item revision's structure: child items with quantity, find number, reference designator, and
  optional per-line effectivity. Rev-specific. Editing it on a released item happens through a change, as a
  **redline BOM**. Detail in `references/items-aml-sites-and-compliance.md`.
- **AML (Approved Manufacturer List)** - the approved **manufacturer parts (MPNs)** on the item, each with a
  **preferred** flag. This drives which manufacturer procurement may buy. Changed by an **MCO** (no rev) or an
  ECO (with rev). **AVL (Approved Vendor List)** - the approved suppliers/vendors that supply those MPNs; AVL
  and supplier sourcing live in Agile Sourcing / PCM. Both re-point procurement.
- **Change** - the controlled vehicle to touch a released item. Subclasses (each a different blast radius):
  **ECR** (request/analyze), **ECO** (revises the item - new revision, redline BOM/AML/attachments), **MCO**
  (changes the AML with **no** rev), **SCO** (changes **site-specific** BOM/AML with **no** rev), **PCO**
  (price change, PCM), **Deviation** (bounded authorized departure), **Stop Ship** (halts shipment). Runs a
  **workflow**. Detail in `references/change-workflow-and-access.md`.
- **Change workflow / status** - a change moves through status types: **Pending -> Submit -> CCB/Review ->
  Released -> Implemented -> Complete** (plus **Hold**, **Cancel**). **Released** is the commit that applies
  the redlines and drives downstream. Approvers/observers are added per status; the **CCB (Change Control
  Board)** signs off; the **Change Analyst** owns and routes it.
- **Redline** - inside a change, a staged edit (redline BOM / redline AML / redline attachments) shown against
  the current data. Redlines **only apply when the change Releases** - before that the item's live tabs still
  show the old data.
- **Site** - a manufacturing location that can hold **site-specific** BOM/AML overriding the common data. An
  **SCO** changes one site's data only.
- **File folder** - the object that holds attachments; it has **its own version stream**. An item/change
  attaches a **specific file folder version**; a new version can change what everyone consumes with no item rev.
- **PG&C (Product Governance & Compliance)** - substance/material compliance (RoHS, REACH…), supplier
  **declarations**, and **specs**, with a **compliance rollup** over the BOM.

## Vocabulary that bites
These are the terms whose Agile meaning hides a hazard - definitions here, the causal chains in Gotchas below
(the same rules seen twice, not new ones).
- **Item vs revision** - the item is identity; the **revision** carries the BOM, AML, attachments, and phase.
  "Change the item" almost always means create a new revision **through an ECO**, not edit the item.
- **No Revise - the change makes the rev** - unlike Teamcenter/Windchill, there is no standalone Revise action.
  Adding an item to an ECO and redlining it creates a **Pending** rev; only **Release** makes it the current rev.
- **ECO vs MCO vs SCO** - an **ECO** revises the item (new rev). An **MCO** changes the **AML** with **no rev
  bump**. An **SCO** changes **one site's** BOM/AML with **no rev bump** and no effect on common data. Same
  word "change", very different blast radius - classify by the subclass.
- **AML / MPN / preferred** - the approved manufacturer list, its manufacturer part numbers, and the preferred
  flag. Removing or de-preferring an MPN re-points sourcing even though the physical part and rev are unchanged.
- **AVL** - approved vendors/suppliers (Sourcing / PCM). Distinct from the AML (manufacturers); both re-point buying.
- **PCO (Price Change Order)** - a change that re-points published costs/prices (Agile PCM) with **no rev bump** -
  the same no-rev trap as MCO/SCO. Removing or zeroing a price can stall quoting the way removing a preferred MPN stalls procurement.
- **Obsolete vs supersede** - **obsolete** ends an item's life (lifecycle phase -> Inactive/Obsolete).
  **Supersede** replaces item A with item B: a change redlines every parent from A to B and obsoletes A, and
  downstream ERP consumes the replacement to swap its material master. Both are fleet actions; supersede
  additionally re-points every parent onto a new item, so run **Where Used** on A first.
- **Redline** - a staged BOM/AML/attachment edit inside a change that applies **only on Release**; before then
  the item's live tabs still show the old data (causal chain in gotcha #6).
- **Pending vs Released revision** - a Pending rev belongs to an unreleased change and is **not** what
  production uses; the current Released rev is. Do not build against a Pending rev.
- **Lifecycle phase** - Preliminary / Prototype / Production / Inactive-Obsolete; an attribute of the revision,
  **not** the change's release status. Read both, do not read one for the other.
- **Change status** - Pending / Submit / CCB-Review / Released / Implemented / Complete / Hold / Cancel. Only
  **Released** applies the redlines and drives downstream; a routed or approved-but-not-released change has not.
- **Effectivity** - the change's release/effective date (and optional per-BOM-line effectivity) decides **when**
  the change bites. A past/immediate date re-points production now and can hit already-shipped units.
- **Deviation** - a bounded, time/quantity-limited authorization to depart from the released definition; it
  does **not** change the baseline. A permanent change needs an ECO.
- **Stop Ship** - a change subclass that **halts** shipment/use of the affected parts (quality/safety hold). A
  fleet action; issuing and lifting are both consequential.
- **Where Used** - the blast-radius query: which parent assemblies use this item. Run it **before** obsoleting,
  replacing, or stop-shipping anything.
- **SmartRules** - site-configured rules (duplicate BOM, missing AML, incomplete fields, unreleased child…)
  that **block or warn on Release**. A change that looks ready can fail Release until a rule is satisfied.

## Operations: read / write / destructive
Classify every operation family by what it does to state and to the controlled baseline. The verbs name the
action-kind; the class is the same whether the connector drives the Agile Web Client, the Java client, or a
server integration. The harness maps the customer's real connector onto these classes. No tool names - kinds
of action.

| Class | Agile PLM operation families | Gate | Why |
|---|---|---|---|
| **Read** | view / search an item, revision, BOM, AML/AVL, manufacturer part, attachment (file folder), site data, compliance / declaration; **Where Used** and redline preview; view a change (ECR/ECO/MCO/SCO/deviation/stop ship) status, workflow, approvers, and sign-off history; view lifecycle phase and effectivity | always pass | no state change; read the item + current **Released** revision + any open/**Pending** change + AML + relevant site + lifecycle phase + effectivity before any write, re-read at execute |
| **Write (reversible)** | **create an item** (initial Preliminary/Introductory revision - **but autonumber, the subclass, SmartRules, a lifecycle default, or auto-routing can make it committing; if you cannot confirm the deployment does none of that, gate creation as committing**); **create a change** (ECR/ECO/MCO/SCO/deviation/stop ship) in **Pending**; edit **redlines** on an unreleased change (redline BOM / AML / attachments); add affected items to a change; edit a **Preliminary**, no-change-required item's own data; check out / attach a file folder version on working content | gate one at a time | a Pending draft or an unapplied redline - nothing released; low blast while it stays Pending |
| **Write (committing)** | **submit / route** a change into its workflow (Submit / CCB Review); **approve or reject** a change (the CCB e-signature); **release an ECO** (creates the new Released revision, applies the redline BOM/AML/attachments, can change lifecycle phase); **release an MCO** that **adds** an approved MPN or re-points sourcing while **leaving a valid preferred source** (changes the AML on the current released rev, **no rev bump**); **release an SCO** that changes one site's BOM/AML while leaving it buildable (**no rev bump**); **issue / release a Deviation** (authorizes a bounded departure - production may act on it); **release a PCO** (price change, PCM - re-points costing/sourcing economics, **no rev bump**); set change **effectivity / release date**; **advance a change Implemented -> Complete** (closes it to further action; can trigger ERP finalization / archival); **publish / export** a released item / BOM / AML to ERP | gate + human approve; scale the gate to blast radius (a routine Submit is the low end; releasing a change, an MCO/SCO, or a publish is the high end - named approver) | binds the controlled baseline others build and buy against, changes sourcing, or hands it downstream; each re-points manufacturing or procurement. **An MCO/SCO that removes/de-prefers the last or preferred source, or can halt procurement, escalates to the destructive row** |
| **Destructive / irreversible** | **release a change that obsoletes / supersedes an item** (lifecycle phase -> Inactive/Obsolete, cascades to Where Used + procurement); **issue or lift a Stop Ship** (halts or resumes shipment/use of affected parts in production/field); **release an MCO/SCO that removes / de-prefers the last or preferred MPN**, or otherwise leaves an item/site un-buildable (can halt procurement, re-points sourcing silently, **no rev to signal it**); **change effectivity on a released change**; **cancel / close a change after it is Released / Implemented** (downstream already acted); **de-release / unrelease** a released change or roll back a revision (breaks every downstream that trusted the baseline); **force checkout / override another user's file-folder lock** (discards their in-progress edit, unrecoverable); **delete** an item / change / manufacturer part (**soft** delete may be restorable, a **hard** delete/purge is permanent; both blocked while referenced); **override a role / privilege or Discovery** to grant access to, or export, a restricted item | hard gate + named approver + re-read | permanent or export-controlled; re-points the whole company's structure or sourcing; cannot be cleanly undone; crosses a compliance boundary |

**Bulk / mass form of any row** - a data load / import, a mass change, or a bulk AML / effectivity update - is
not a separate class: classify it by the **per-item** row, then gate at the **amplified blast radius**. A mass
obsolete or a bulk AML change resolves to the destructive gate, not the single-item one. Read the full target
set (Where Used across all of it) before running it.

## Reclassification rules (read this)
- **A change to a released item is not an edit - it is a change order.** Released item content (BOM, AML,
  attachments) is frozen; the only path is a change, and the change's **Release** is the commit. Never edit a
  released item's data directly.
- **Revisioning is change-driven - there is no standalone Revise.** The new rev is **Pending** while the ECO is
  open and is created for real only on **Release**. Do not treat "I added it to a change and redlined it" as
  "the revision exists" - it is Pending until release.
- **MCO and SCO change data with no new revision.** A released **MCO** re-points the AML (manufacturers/
  sourcing) and a released **SCO** re-points one site's BOM/AML - both on a released item whose **rev number
  never changes**. Gate an MCO/SCO release like a committing (often destructive) sourcing/site change; never
  assume "same rev = same part or sourcing".
- **Submitting/routing a change is committing; Release is the release event.** Entering the workflow starts CCB
  review; **Release** applies the redlines and drives downstream. Approval/rejection is an attributed
  **e-signature** - never auto-approve or auto-release to move a change along, and you cannot sign for another.
- **A Deviation authorizes a departure, it does not change the baseline.** The item/BOM stay as-is; production
  may depart within the deviation's quantity/date window. Do not use a deviation as a permanent change (that
  needs an ECO), and do not let one lapse or over-run without re-checking what shipped under it.
- **A Stop Ship is a fleet action.** Issuing it halts shipment/use of the affected parts; lifting it resumes
  them. Run **Where Used** first and gate it as destructive.
- **Obsolete / supersede is a fleet action.** Releasing a change that moves an item to Inactive/Obsolete
  cascades to every Where Used parent and to procurement. Run Where Used first; gate destructive.
- **Effectivity decides when the change bites.** A past/immediate effective date re-points production now (and
  can retroactively hit shipped units); a future date schedules it. Know the date before Release.
- **Item creation escalates to committing when you cannot prove it is clean.** Autonumber, the subclass,
  SmartRules, a lifecycle default, or an auto-routing rule can put a new item into a controlling state on
  create. If you cannot confirm the deployment does none of that, gate creation as committing.
- **A bulk / mass operation is the same action at fleet scale - gate at the amplified blast radius.** A mass
  obsolete, a bulk AML change, or a mass effectivity change is destructive at scale and needs the destructive
  gate, not the single-item one. Read the full target set (Where Used across all of it) before running it.

Universal rules to teach: read the item + its current **Released** revision + any open **Pending** change +
the AML/AVL + the relevant **site** + the lifecycle phase + effectivity before any write, and **re-read at
execute** (another change may have released, or a second change opened, since you read); never edit a released
item's content directly; never bypass or auto-approve/auto-release a change or sign on another's behalf; never
obsolete/supersede/replace or stop-ship without Where Used; never change effectivity on a released change
without knowing which units/dates it re-points; never override a role/privilege/Discovery to grant access or export.

## Worked example (a change, end to end)
A field problem is reported on bracket **BRK-100**, current released revision **B** (lifecycle Production).
**Where Used** [read] shows BRK-100 is used **2x in ASM-200** and **1x in ASM-210**, both released, and
**4,999 units** are already shipped. You raise an **ECR** [write-reversible] describing the failure; it is
analyzed and approved. You create an **ECO** [write-reversible] in **Pending**, add BRK-100 as an affected
item with new rev **C** - the item now shows **rev C as Pending** while **rev B stays the current Released rev,
untouched**. You **redline the BOM** [write-reversible] to the thicker bracket and set change **effectivity so
units 5000+ get rev C and 1-4999 keep rev B**. You **Submit** the ECO into the **CCB** workflow
[write-committing]; the CCB **approves via e-signature** [write-committing]. You **Release the ECO**
[write-committing]: rev C becomes the current Released revision, the redlines apply, and the change
**publishes to Oracle ERP** which updates its manufacturing BOM and re-points procurement from the effectivity.
Editing rev B in place, or setting effectivity to "all units" without checking the field fleet, would have
retroactively invalidated the 4,999 shipped units.

**A no-rev sourcing sub-scenario (MCO).** Separately, the **preferred MPN** for capacitor CAP-22 goes
end-of-life. The physical part fits, so you do **not** revise - you raise an **MCO** [write-reversible in
Pending], **de-prefer** the old MPN and add a new approved MPN on the **current released revision**. Releasing
the MCO [write-committing] re-points procurement to the new manufacturer **while the item revision is
unchanged** - anyone trusting "same rev = same source" is now wrong (gotcha #3).

**A site sub-scenario (SCO).** Plant B qualifies an equivalent local fastener for BRK-100. You raise an **SCO**
[write-reversible] changing **only Plant B's** BOM/AML; the common data and Plant A are untouched and show **no
change and no rev**. A read of only the common BOM misses Plant B's override entirely (gotcha #4), and a later
global ECO on BRK-100 must account for Plant B's site data or it silently reverts or conflicts with it.

**A destructive-recovery variant.** Suppose after Release you find rev C's effectivity was set to **all units**
by mistake and ERP already pulled it. You cannot cleanly **de-release** rev C - unreleasing breaks the
downstream that trusted it. The forward path is a **new ECO** correcting effectivity to 5000+, re-publish, and
let ERP re-align; rev B, rev C, and both effectivity settings stay in the audit trail. If the wrongly-effective
units are unsafe, **issue a Stop Ship** [destructive] to halt them, and use a **Deviation** only if a bounded
departure is genuinely acceptable while the fix ships. Parts already **bought** against the wrong effectivity
are not un-bought by editing Agile - that reconciles on the ERP side (`oracle-erp`).

## Gotchas that bite (the real set - causal chains)
1. **Revisioning is change-driven - no standalone Revise.** A new revision exists only after an **ECO is
   Released**; before that it is a **Pending** rev tied to the change. Building against a Pending rev builds
   against a revision that is not live yet.
2. **A released item is frozen.** Its BOM, AML, and attachments change only through a change order. Forcing a
   direct edit (where config even allows it) breaks the audit chain and the baseline everyone builds and buys against.
3. **An MCO changes the AML with no new revision.** A released MCO that adds / removes / de-prefers a
   manufacturer part re-points sourcing while the item **revision number is unchanged** - "same rev = same
   sourcing" is false, and there is no rev bump to signal the change.
4. **An SCO changes only one site's BOM/AML, with no rev and no effect on common data.** A site fix is invisible
   globally and other sites keep the old data. Read **which site** you are acting on before and after.
5. **Releasing the change is the commit - submitting or approving is not.** Only **Release** applies the
   redlines, creates the rev (ECO), and drives downstream. Auto-releasing to "finish" pushes uncontrolled content live.
6. **The redline is a staged edit, not the live record.** Redline BOM/AML/attachment changes apply **only on
   Release**; the item's live tab shows old data until then. Confusing the redline with the live record acts on the wrong one.
7. **Effectivity decides when the change bites.** A past/immediate effective date re-points production now and
   can retroactively hit shipped units; a future date schedules it. Releasing without checking effectivity mis-times the switch.
8. **Approval is an attributed CCB e-signature.** Signing releases or blocks the change and is the most
   consequential write; you cannot sign on another's behalf, and auto-approving to advance the workflow releases uncontrolled content.
9. **A Deviation does not change the baseline.** It authorizes a bounded (quantity/date) departure; the item and
   BOM stay as-is. Treating a deviation as a permanent fix leaves the real definition unchanged; letting it lapse
   or over-run its quantity ships out-of-spec and un-authorized.
10. **A Stop Ship halts shipment/use of the affected parts - a fleet action.** Issuing it stops product; lifting
    it resumes. Run **Where Used** to know exactly what you are stopping or releasing.
11. **Obsolete / supersede cascades to Where Used and procurement.** Releasing a change that moves an item to
    Inactive/Obsolete strands every parent still calling it and stops/redirects buying. It is a fleet action, not cleanup.
12. **Lifecycle phase is not change-release status.** The phase (Preliminary/Prototype/Production/Inactive) is an
    attribute of the revision; whether a change is Released is separate. A Production item can carry an open
    Pending change, and a Preliminary item may be edited without a change - do not read one for the other.
13. **The AML preferred flag drives sourcing.** Removing or de-preferring an MPN, even without deleting it,
    re-points which manufacturer procurement buys. An AML "cleanup" is a sourcing change, not housekeeping.
14. **File folders version independently of the item.** An attachment points to a **file folder version**;
    checking a new version into the folder changes what everyone consumes with **no item rev and no change** -
    track the file folder version, not just the item rev.
15. **Where Used is the blast radius - skipping it flies blind.** Before obsoleting, replacing, or stop-shipping
    a part, Where Used tells you which assemblies and how many units you are about to hit. Not running it means you do not know.
16. **SmartRules gate what can Release.** Site rules (duplicate BOM, missing AML, incomplete fields, an
    unreleased child…) block or warn on Release; a change that looks ready fails until the rule is satisfied.
    Read the SmartRule outcome - do not force past a warning that hides a real error.
17. **PG&C compliance rolls up the BOM.** Changing the BOM or AML changes the substance / RoHS / REACH rollup; a
    BOM change that pulls in a non-compliant part can flip the product's compliance with no obvious flag. Re-check
    the rollup after any BOM/AML change.
18. **Cancel after Release does not undo downstream.** Once a change is Released/Implemented and ERP pulled it,
    cancelling or closing it in Agile does not un-buy parts or revert ERP. Reverse an implemented change with a **new change**.
19. **A rejected or held change is not released - and its redlines are not the live record.** Check the change's
    **actual status** (Pending / Submit / Review / Released / Implemented / Complete / Hold / Cancel), not that you
    routed it; a reject returns it (and it can be revised and resubmitted), a hold freezes it, only Release drives
    downstream. Reading a rejected/held change's **redline** tab and acting on it treats an unapplied proposal as live.
20. **Two open changes on one item collide.** An item can sit on more than one pending change; conflicting
    redlines to the same BOM/AML, or a second ECO revising the same item, race - the second to Release overwrites
    or is blocked. Read the item's open changes before starting another.
21. **Delete vs soft-delete differ and both are blocked while referenced.** A **soft** delete may be
    admin-restorable; a **hard** delete/purge is permanent and orphans history. You cannot delete an item / change
    / manufacturer part still referenced by a BOM, an AML, or another change. Know which the action performs.
22. **Discovery and privileges gate whether you even see an object.** Agile's **Discovery** privilege can hide an
    object's existence; Read/Modify/Create/Delete are separate privileges by role and can be object- and
    phase-dependent. "I could edit it before" does not survive a phase change or a role scope; overriding a
    privilege or an export restriction to grant access is a compliance breach, not a shortcut.
23. **Publish/export to ERP is a commit hand-off, not a sync.** Releasing a change publishes the item/BOM/AML to
    Oracle ERP (or the connected ERP), which updates its material/BOM and re-points procurement; a premature or
    wrong publish drives buying and building off the wrong record. It can also **partially apply** - check the
    publish status, do not assume Release = ERP accepted.
24. **The Introductory revision is free; later ones are not.** The first (Introductory) revision can be created
    directly, but every subsequent revision requires a released ECO. Assuming you can "just bump the rev" on a
    released item skips the controlled change.
25. **A PCO (price change) is the same no-rev trap as MCO/SCO.** Releasing a Price Change Order (Agile PCM)
    re-points published costs/prices used by sourcing with **no item rev bump**; a cost/quote read that trusts
    "same rev = same price" is wrong after a released PCO. Gate a PCO release as committing.

(Deep detail: `references/items-aml-sites-and-compliance.md`, `references/change-workflow-and-access.md`.)

## Edge states & special cases
Each breaks naive "read the BOM, act on the item" logic - key rule inline, full behavior in the references.
- **Change subclass (ECR / ECO / MCO / SCO / PCO / deviation / stop ship)** - each changes different content and
  only some create a rev; classify by the specific subclass. Detail in `references/change-workflow-and-access.md`.
- **Pending vs Released revision** - a rev introduced by an open change is Pending until Release; the current
  Released rev is what production uses. Do not act on a Pending rev as if live.
- **Held change** - a change on **Hold** is frozen: it has not Released, its redlines are **not** applied, and
  lifting the Hold usually needs a specific privilege (the Change Analyst or an approver). A Held change is
  neither done nor cancelled - find why it was held and who can lift it before acting. Detail in
  `references/change-workflow-and-access.md`.
- **AML / AVL and manufacturer parts** - the approved-manufacturer list and its preferred flags drive sourcing;
  an MCO changes it with no rev. Detail in `references/items-aml-sites-and-compliance.md`.
- **Sites and site-specific data** - a site can carry its own BOM/AML overriding the common data; an SCO scopes
  to one site. Reading only the common data misses site overrides.
- **File folders / attachments** - a separate version stream; a new file version changes what is consumed with
  no item rev. Read the file folder version, not just the item rev.
- **Effectivity (change date, per-BOM-line dates)** - windows, overlaps, and a past date decide which config is
  used and whether it is retroactive.
- **PG&C compliance rollup** - substance / declaration data rolls up the BOM; a BOM/AML change can flip
  compliance. Detail in `references/items-aml-sites-and-compliance.md`.
- **Roles / privileges / Discovery** - access is role-, phase-, and object-dependent, and Discovery can hide an
  object's existence entirely. Detail in `references/change-workflow-and-access.md`.

## Recovery patterns (can it be undone, and what cannot)

| Situation | Recovery path (with the gate class of the corrective action) |
|---|---|
| A **Pending** change was redlined wrong (not yet Released) | edit the redlines again, or cancel/delete the Pending change **[reversible]** - reversible while Pending; nothing was released |
| A **SmartRule blocked Release** (duplicate BOM, missing AML, unreleased child, incomplete field) | read the SmartRule outcome **[read]**, fix the underlying data - redline the BOM/AML, release the child, complete the field **[reversible]** - then re-attempt **Release [committing]**; do not force past a warning that hides a real error |
| An **ECO** was Released by mistake | you cannot cleanly unrelease it - raise a **new ECO** to correct and re-release **[committing]**; de-releasing/unreleasing **[destructive]** breaks downstream trust and is a controlled last resort, not an undo |
| An **MCO / SCO** released the wrong AML / site data | raise a **new MCO/SCO** to correct it **[committing, or destructive if it de-prefers/removes the last source]**; procurement or the site may already have acted, so reconcile sourcing/site separately; the item **rev never changed**, so there is no rev to roll back |
| Effectivity was set wrong on a released change | correct it with a **new change [committing]**; the window may already have driven production/buying, which reconciles on the ERP side |
| An item was **obsoleted / superseded** in error | raise a **new change** to reinstate / re-release **[committing]**; procurement and ERP may already have acted on the obsolete - reconcile downstream separately |
| A **Deviation** over-ran its quantity or lapsed | re-check what shipped within and outside its window; a permanent fix needs an **ECO [committing]**, not a renewed deviation |
| A **Stop Ship** must be reversed | lifting it **[destructive - fleet action]** resumes shipment - confirm the underlying quality issue is truly resolved (usually via the corrective change) before lifting; issuing and lifting are both fleet actions |
| A change was **cancelled after ERP implemented** it | cancelling in Agile does not revert ERP or un-buy parts; reverse with a **new change [committing]** and let ERP re-align (`oracle-erp`) |
| A **file folder version** was checked in wrong | check in a corrected version **[reversible]** (old versions stay in the folder history); if a released item already consumed it, correct under a change **[committing]** |
| A **change was rejected** and needs rework | it returns to an editable status (e.g. Pending); edit the redlines and **resubmit** the same change **[reversible -> committing]** - you do not need a brand-new change, and creating a duplicate orphans the history and the collected review |
| Two changes **collided** on one item (redlines already overwrote, or a second change was blocked) | read the item's current state and **which change's redlines actually applied [read]**; raise a **new change [committing]** to restore whatever the overwritten/losing redline should have set, then sequence the remaining change; prevention next time is to read the item's open changes before starting either - do not force a second ECO onto an item already being revised |
| An item / change / manufacturer part was **hard-deleted** | permanent **[destructive]** - blocked while referenced; recover only from backup. A **soft** delete may be admin-restorable - know which the action performed before running it |
| A **publish to ERP failed or partially applied** | Agile released but ERP did not fully accept - the two systems now disagree; check the publish/transaction status **[read]**, correct the cause, and **re-publish [committing]**, then reconcile ERP. A publish cannot be cleanly retracted |
| A **role / privilege or Discovery** override exposed a restricted item | a compliance incident **[destructive]**, not a technical rollback - restore the privilege and report per policy; assume the exposure happened |

Reversal in Agile is almost always a **new change**, not an undo: the old revision, the change, the CCB
sign-offs, and both effectivity settings stay in the audit trail. What is truly gone is any work lost to a
hard delete, and any downstream (parts bought, ERP updated, product shipped) an earlier Release or publish
already drove.

## Guardrails
- Read the item + its current **Released** revision + any open **Pending** change + the **AML/AVL** + the
  relevant **site** + the lifecycle phase + effectivity before acting; re-read at execute **and again after any
  approval** (another change may have released, or a second change opened, between approval and execution).
- Never edit a released item's BOM/AML/attachments directly - change it through a change order; the change's
  **Release** is the commit.
- **Remember MCO/SCO change sourcing/site data with no rev bump** - do not assume "same revision = same part or
  sourcing"; gate an MCO/SCO release like a committing (often destructive) sourcing/site change.
- Never obsolete / supersede / replace a part, or issue a **Stop Ship**, without running **Where Used** first -
  that is the blast radius.
- Never change effectivity on a released change without knowing which units/dates it re-points; treat it as a supersede.
- Never auto-approve / auto-release a change or sign on another's behalf; never override a role / privilege /
  Discovery or an export restriction to grant access. If **Discovery** hides an object you need, escalate to a
  user who holds the role, or report the access gap - do not work around the control.
- Do not use a **Deviation** as a permanent change (that needs an ECO), and do not let one lapse without checking
  what shipped under it.
- **Item creation escalates to committing when you cannot prove it is clean.** Autonumber (assigns the item
  number on create, making the item immediately visible system-wide), the subclass (sets the item's type and its
  rules), SmartRules, a lifecycle default, or an auto-routing rule can put a new item into a controlling state on
  create; if you cannot confirm the deployment does none of that, gate creation as committing rather than reversible.
- **A bulk / mass operation on N items is not N single-item gates - it is the same action at fleet scale.** Gate
  it at the amplified blast radius (a mass obsolete, bulk AML, or mass effectivity change is destructive at
  scale), and run **Where Used across the full target set** before executing.
- Agile is heavily configured: change subclasses, workflow statuses, lifecycle phases, **SmartRules**, roles /
  privileges, autonumber and subclass rules, and site setup vary by deployment. Read the actual deployed
  configuration - do not assume the standard names or steps are the ones in front of you. Before your first
  write, read the deployment's actual lifecycle phase names, workflow status names, active SmartRules, autonumber
  / subclass rules, and your own role / privilege scope.
- **Classify custom change subclasses by behavior, not name.** A site may add its own change types (e.g. a
  quality or documentation change order) beyond ECR/ECO/MCO/SCO/deviation/stop ship. Classify each by what it
  actually does - does it create a revision? change the AML or site data with no rev? - and gate it there; a
  custom no-rev AML change is an MCO-class action however it is labelled.
- **Determine whether Release and the ERP publish are coupled.** In some deployments releasing a change
  **auto-publishes** to ERP; in others publish is a separate manual step. If coupled, the Release gate must
  account for the ERP impact at the same moment - do not gate Release and publish as independent when Release fires both.
- Scope note: **Agile PLM for Process** (recipe / formulation / spec, food / CPG / pharma) is a different Oracle
  product with a different model - do not apply this skill there.
- For anything in the destructive row (obsolete/supersede, stop ship, a released MCO that de-prefers/removes an
  MPN, released-effectivity change, cancel-after-implementation, de-release/rollback, delete, privilege/Discovery
  override, any mass/bulk variant): named approver, re-read, and log the reason.

## References (load on demand)
- `references/items-aml-sites-and-compliance.md` - items and revisions, lifecycle phases, the BOM and redline
  BOM, the AML/AVL and manufacturer parts (preferred flags, sourcing), sites and site-specific data, file
  folders / attachments and their version stream, effectivity, and the PG&C compliance rollup and declarations.
- `references/change-workflow-and-access.md` - the change subclasses (ECR / ECO / MCO / SCO / PCO / deviation /
  stop ship) and each one's blast radius, the change workflow statuses (Pending -> Submit -> CCB/Review ->
  Released -> Implemented -> Complete, plus Hold / Cancel), CCB and Change Analyst, e-signature approval and
  redlines, roles / privileges / Discovery access, and the publish / export hand-off to ERP.
