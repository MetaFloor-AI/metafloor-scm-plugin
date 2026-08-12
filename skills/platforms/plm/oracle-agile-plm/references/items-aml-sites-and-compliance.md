# Agile PLM - items, revisions, BOM, AML/AVL, sites, attachments, compliance

The object detail behind the operating judgment in SKILL.md. Read when a task touches an item's structure, the
approved-manufacturer list, a site override, an attachment, effectivity, or compliance. The read/write/
destructive classification lives in SKILL.md - this file is the "how the objects behave" detail.

## Contents
- Items and revisions, lifecycle phases
- BOM and redline BOM
- AML / AVL and manufacturer parts
- Sites and site-specific data
- File folders and attachments
- Effectivity
- PG&C compliance rollup and declarations

## Items and revisions, lifecycle phases
- An **item** is a **Part** or a **Document** (an item number + Title Block). It carries a **BOM**, an **AML**,
  attachments, sites, compliance, and **one or more revisions**.
- A **revision** (Introductory, A, B, C…) carries its **own** BOM, AML, attachments, and lifecycle phase. The
  **Introductory** revision can be created without a change; **every later revision is created by releasing an
  ECO**. There is no standalone "Revise" action - the change creates the rev.
- A revision introduced by an **unreleased** change is **Pending** (shown with the change number); it becomes
  the **current Released** revision only when the change releases. Production always uses the current Released rev.
- **Lifecycle phase** is a configurable attribute on the revision, commonly **Preliminary -> Prototype ->
  Production/Released -> Inactive/Obsolete**. It states fitness-for-use and is **separate** from the change's
  release status: a Production item can still have an open Pending change. A **Preliminary** item may often be
  edited without a formal change (subject to SmartRules); a **Released/Production** item may not - change it
  through a change order.
- Moving an item to **Inactive/Obsolete** (via a released change) ends its life and **cascades** to Where Used
  parents and to procurement - a fleet action, run Where Used first.

## BOM and redline BOM
- The **BOM** on a revision lists child items with **quantity, find number, reference designator**, and
  optional per-line effectivity (effective / inactive dates). It is **rev-specific**.
- On a **released** item the BOM changes only inside a change, as a **redline BOM**: a staged set of add /
  remove / re-quantity / re-reference edits shown against the current BOM. The redline **applies only when the
  change Releases** - before that the live BOM tab still shows the old structure.
- Reading the live BOM before release shows old data; reading the redline shows the proposal. Act on the wrong
  one and you build against the wrong structure.
- A **BOM with errors** (missing child, unreleased child, duplicate) can be blocked from Release by SmartRules
  (see SKILL.md) - a change that looks ready fails Release until the rule is satisfied.

## AML / AVL and manufacturer parts
- The **AML (Approved Manufacturer List)** on an item lists the approved **manufacturer parts (MPNs)**, each
  from a **Manufacturer** object, each with a **preferred** flag. The AML says which manufacturer part is
  approved to satisfy this item - it **drives sourcing**.
- The **AVL (Approved Vendor List)** is the approved **suppliers/vendors** that supply those MPNs; AVL and
  supplier sourcing sit in Agile **Sourcing / PCM**. AML (manufacturers) and AVL (vendors) are distinct lists;
  changing either re-points procurement.
- The AML is changed by an **MCO** (**no** item revision) or by an **ECO** (with a revision, as a **redline
  AML**). Because an MCO does not bump the rev, a released MCO re-points which manufacturer part is bought **on
  an item whose revision number looks unchanged** - the central Agile sourcing trap.
- Removing, adding, or **de-preferring** an MPN is a sourcing change even when the physical part is identical.
  A "cleanup" of the AML changes what procurement buys.
- **Manufacturer parts** are shared objects: the same MPN can be on many items. A change to the manufacturer
  part object itself (not just its use on one AML) has multi-item blast radius - check where it is used.

## Sites and site-specific data
- A **site** is a manufacturing location. An item can hold **site-specific** BOM and AML that **override** the
  common (global) data for that site only.
- An **SCO (Site Change Order)** changes **one site's** BOM/AML with **no item revision** and **no effect on
  the common data or other sites**. A site-scoped fix is invisible globally; another site keeps the old data.
- Always read **which site** you are acting on. A read of only the common data misses site overrides; a fix on
  the common data does not reach a site that has an override.

## File folders and attachments
- Attachments are stored in **File Folder** objects, each with its **own version stream**. An item or change
  attaches a **specific file folder version**.
- Checking a **new version** into a file folder can change what everyone downstream consumes **without an item
  revision and without a change** - the item number and rev look identical while the file changed. Track the
  **file folder version**, not just the item rev.
- File folder contents can be **checked out / checked in** (a lock). Forcing another user's checkout aside
  discards their in-progress edit. Old versions stay in the folder history; a wrong check-in is corrected by a
  new version, and if a released item consumed it, under a change.

## Effectivity
- The primary effectivity is the **change's release / effective date** - it decides **when** the change bites.
  A **past or immediate** effective date re-points production now and can retroactively hit already-shipped
  units; a **future** date schedules the switch.
- BOM lines can also carry **per-line effectivity** (effective / inactive dates) that phase a component in or
  out. Overlaps and gaps in these dates decide which component is active on a given date - an overlap resolves
  to two, a gap to none.
- Choose the effectivity that matches how the fleet is tracked; know the date/window before Release, and treat
  a change to effectivity on an already-released change as a supersede.

## PG&C compliance rollup and declarations
- **PG&C (Product Governance & Compliance)** manages substance/material compliance (**RoHS, REACH**, and
  similar), supplier **declarations** (the data suppliers submit about substances in their parts), and **specs**
  (the regulatory requirements an item must meet).
- Compliance **rolls up the BOM**: a part's compliance contributes to its parents. A **BOM or AML change** can
  change the rollup - adding a non-compliant part or a non-compliant manufacturer part can **flip** the product's
  compliance state, often with no obvious flag on the change itself.
- Re-check the compliance rollup after any BOM/AML change, and before releasing a change that alters the
  structure of a compliance-controlled product. A released change that breaks compliance has already published
  the non-compliant structure downstream.
