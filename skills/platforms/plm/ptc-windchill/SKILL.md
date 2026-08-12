---
name: ptc-windchill
description: "PTC Windchill (PDMLink) - the safe operation of product definition and change: parts (WTPart) vs CAD documents (EPMDocument / Creo), iteration vs revision vs version, BOMs (EBOM / MBOM via views and MPMLink transformation), lifecycle states, promotion requests, change management (PR -> CR -> CN -> change task), config specs (Latest / Released / Baseline / Effectivity / As-Stored), effectivity (date / lot / serial), baselines, and access via contexts and domain policies. Use when the connected PLM is Windchill and the work touches product data or a change, or the user mentions Windchill, PDMLink, a WTPart or CAD document / EPMDocument, Creo / Workgroup Manager, iteration vs revision (A.1 / B.1), Revise vs Save As, a config spec, EBOM / MBOM, MPMLink, effectivity, a baseline, check-in / check-out or undo checkout, a lifecycle state or promotion request, supersede / obsolete, where-used, a problem report / change request / change notice (CN / ECN), an OIR, or options and variants."
---

# PTC Windchill - operating product definition safely

Windchill (PDMLink, with MPMLink for manufacturing and Options & Variants for configuration) is the PLM system
of record for **what the product is**: the parts, the CAD, the assemblies, and the controlled process by which
any of it changes. What makes Windchill dangerous is not a single posting - it is that **a Released iteration is
a controlled baseline the whole company builds and buys against**. Manufacturing, procurement, and service all
read the released structure through a **config spec** (plus effectivity), so a change to a released revision, a
change to effectivity, or an Obsolete of a part does not stay inside PLM - it re-points the plant and the buyers.
This skill classifies those actions so the harness can gate them, plus the config edge states (config specs,
iteration vs revision, EBOM vs MBOM views, effectivity, baselines, the WTPart / CAD-document split) and the
recovery paths that decide whether a mistake is fixable.

## When this applies
Connector is PTC Windchill and the work is product data, structure, or an engineering change. When NOT:
- a different PLM: **Siemens Teamcenter** -> `siemens-teamcenter`; **Oracle Agile PLM** ->
  `oracle-agile-plm`. The vocabulary differs (Windchill has iterations, config specs, WTPart vs
  EPMDocument, contexts / OIRs; Teamcenter has BVRs, revision rules, item revisions) - do not carry one across.
- ERP material master, the costed / planning BOM procurement and production actually consume, inventory,
  purchase orders, goods movements -> `sap-mm`.

Boundary with ERP / MES: Windchill owns the **as-designed** definition and controls its change; it **publishes**
the released part / EBOM / MBOM downstream (via ESI / an integration). ERP (`sap-mm`) owns the material
master, the manufacturing BOM used to buy and cost, and inventory; the MES consumes the released MBOM to build. A
released Windchill revision or a completed Change Notice is the **upstream trigger** for an ERP BOM update and
procurement - Windchill does not buy parts or hold stock, ERP does not change the design.

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
- **Part (WTPart)** - the engineering item / BOM identity (a Number + Name). It carries the product structure
  (**uses** links to child parts), attributes, a **lifecycle state**, and a **view**. It is **not** the CAD file.
- **CAD Document (EPMDocument)** - the Creo (or other CAD) file object holding geometry. Its own Number, its own
  version stream, its own lifecycle. Linked to a WTPart by an **owner / build association**; the part's EBOM can
  be **built (published) from the CAD assembly structure**. Two objects, two version streams (see
  `references/structure-config-and-effectivity.md`).
- **Version = Revision + Iteration** - every object's version is `revision.iteration` (A.1, A.2, B.1).
  **Iteration** bumps automatically on every **check-in** (A.1 -> A.2); it is not a controlled revision.
  **Revision** bumps only via **Revise** (A -> B), starting a new **In Work** revision. Reason about the exact
  version, and hold that iteration is not revision.
- **Lifecycle state** - the maturity a lifecycle template drives: **In Work -> Under Review -> Released ->
  (Obsolete / Superseded)** (states are configurable per template). The state plus **domain policy** decides who
  may read / modify and whether the object is frozen. A **Released** object is a read-only baseline; change = Revise under control.
- **View** - a WTPart carries a **view** (**Design** = EBOM, **Manufacturing** = MBOM); each view has its **own
  version stream**. EBOM and MBOM are different structures for the same part, linked by **MPMLink** associativity;
  an EBOM change does not flow to the MBOM by itself.
- **Uses / occurrence (BOM line)** - a parent-to-child link carrying quantity, find number, reference designator,
  and optionally effectivity.
- **Config Spec** - the configuration lens that resolves *which* iteration / revision of each child you see:
  **Latest**, **Released** (by lifecycle state), **Baseline**, **Effectivity** (date / unit / serial),
  **As-Stored**. Same structure, different config spec -> a different BOM. Detail in `references/structure-config-and-effectivity.md`.
- **Change objects** - **Problem Report (PR) -> Change Request (CR) -> Change Notice (CN) -> Change Task /
  Change Activity** (carrying **Affected** objects, the old, and **Resulting** objects, the new revisions). The
  controlled vehicle to change released content. Detail in `references/change-lifecycle-and-access.md`.
- **Promotion Request** - a lighter request to move a set of objects to a new lifecycle state (e.g. In Work ->
  Released), routed for approval; it does not create a revision or carry a change's audit.
- **Baseline** - a **managed baseline** captures specific iterations of a set of objects (a frozen snapshot),
  resolvable by a Baseline config spec.
- **Access - contexts, domains, policies** - data lives in a **context** (**Product / Library / Project /
  Program / Organization**), each with a **team** (roles) and administrative **domain**; **policy ACLs** keyed on
  domain + object type + **lifecycle state** + role grant read / modify / etc. **OIRs (Object Initialization
  Rules)** set defaults (number, lifecycle template, team) on create. Access is **state-dependent**.

## Vocabulary that bites
- **Iteration vs revision vs version** - version = `revision.iteration`. Iteration bumps on every check-in
  (A.1 -> A.2, uncontrolled); revision bumps only on **Revise** (A -> B). A "new version" from a check-in is a
  **new iteration**, not a new revision and not a change. This is the Windchill trap Teamcenter users miss.
- **WTPart vs CAD Document (EPMDocument)** - the part (BOM item) and the CAD file are **separate objects** with
  separate versions and lifecycles, joined by an owner / build association. Editing and checking in the CAD
  document does not update the part EBOM until the build / associativity re-runs.
- **Revise vs Save As** - **Revise** makes a new **revision of the same object** (keeps the Number, the history,
  the supersede chain). **Save As** makes a **new object** (new Number, no link). Save As where you meant Revise
  breaks traceability; Revise where you meant a genuinely new part collides identity.
- **Config Spec** - Windchill's resolution lens (Teamcenter calls it a revision rule): **Latest / Released /
  Baseline / Effectivity / As-Stored**. The BOM you "see" is meaningless without the config spec that produced it.
- **Latest vs Released vs As-Stored** - **Latest** shows the newest iteration (in-work design); **Released** shows
  the newest released revision (what production builds); **As-Stored** pins the exact iterations saved with a
  stored structure. Different lens, different product.
- **View (Design / Manufacturing) = EBOM / MBOM** - a part carries per-view versions; the Design view is the
  EBOM, the Manufacturing view is the MBOM (built via **MPMLink** BOM transformation). A Design change is
  invisible to the plant until transformed into the Manufacturing view and re-released.
- **Effectivity (date / lot / serial)** - the window a revision / occurrence is valid; it re-points which revision
  is used **without editing a BOM line** - a silent, high-blast switch on a released config.
- **Baseline** - a frozen snapshot of specific iterations; a Baseline config spec resolves to those, not Latest. A
  change made after the baseline does not appear in it.
- **Lifecycle state** - In Work / Under Review / Released / Obsolete; drives access (state-dependent ACL) and
  whether the object is frozen. Released = read-only baseline.
- **Promotion Request** - moves lifecycle state for a set of objects, routed for approval; **lighter than a
  Change Notice** and carries no revision or change audit. Using a promotion to release *changed* content skips
  the change process - know which governance the content requires.
- **Change (PR / CR / CN / Change Task)** - the controlled path to touch released content. The **Change Notice**
  with its **Change Tasks** carries **Affected** (old) and **Resulting** (new-revision) objects; **completing the
  CN is the release event** that drives downstream. (Some sites label the CN an ECN / ECO.)
- **Check-out / check-in / undo checkout** - check-out **locks** the object to you and copies it to your
  **workspace**; check-in commits a **new iteration** to the **commonspace**. **Undo checkout** discards **all**
  edits since checkout (not undo-last) and reverts to the last checked-in iteration.
- **Workspace vs commonspace** - the **workspace** is the CAD user's private staging area (Creo / Windchill
  Workgroup Manager); the **commonspace** is the shared Windchill database. Edits live in the workspace until check-in.
- **Owner / build association** - the CAD-document-to-part link and the build rules that publish CAD structure to
  the WTPart EBOM; re-pointing or rebuilding it can silently add / remove / re-quantify part uses.
- **Where-used / used-in** - the blast-radius query: which assemblies use this part, what references this CAD
  document. Run it **before** revising, replacing, or obsoleting anything.
- **OIR (Object Initialization Rules)** - server rules that set default Number, lifecycle template, and team, and
  can **auto-checkout or auto-assign** on create. Why "create a part" is not always a clean, reversible In-Work draft.
- **Context (Product / Library / Project)** - the container that owns an object and its team / domain / policy.
  Moving an object across contexts re-evaluates access and can lock out the original team or expose it.
- **Options & Variants** - a **generic / configurable** product structure (a superset "150%" BOM) with option /
  choice expressions on occurrences, resolved by a **variant specification** to a specific configured product.
- **Set State** - an admin action that changes lifecycle state **directly**, bypassing promotion / change. A
  governance shortcut - treat it as destructive.

## Operations: read / write / destructive
Classify every operation family by what it does to state and to the controlled baseline. The verbs name the
action-kind; the class is the same whether the connector drives the Windchill web UI, Creo / Workgroup Manager,
or a server integration. The harness maps the customer's real connector onto these classes. No tool names - kinds
of action.

| Class | Windchill operation families | Gate | Why |
|---|---|---|---|
| **Read** | view / search a part, CAD document, or structure **under a stated config spec**; expand a BOM (Latest / Released / Baseline / Effectivity / As-Stored); **where-used / used-in**; compare structures (rev A vs rev B, EBOM vs MBOM view, structure vs baseline); view lifecycle state, effectivity, change / iteration history, ownership / policy; open a Creo View representation | always pass | no state change; read the part + version + lifecycle state + view + config spec + effectivity + policy before any write, re-read at execute |
| **Write (reversible)** | **create a WTPart or CAD document** (In Work - **but OIRs may auto-number, assign a non-In-Work lifecycle / team, or auto-checkout, which makes it committing; if you cannot confirm the OIR is benign, gate creation as committing**); **Revise** to a new **In Work** revision; check out and edit an In-Work part / CAD / attribute; add / remove / re-quantity uses on an **In-Work** structure; build / associate a part from CAD on **working** content; create a **PR / CR** in draft (note - like OIRs, change-object rules can auto-number or auto-route and **start a workflow** on create, which makes it committing; confirm before assuming reversible); save before check-in | gate one at a time | a working, uncommitted draft - not released, not in a committing process; low blast while it stays In Work |
| **Write (committing)** | **check in** (commits a new iteration); **complete a Promotion Request** to a Released state (freezes it); **vote / approve** a workflow or Change Task; **promote a change** (CR approved -> CN authorized / completed = release event); **set / publish effectivity** on a **Working** revision that has **no** released status and **no** active workflow (the **only** non-destructive effectivity case - the moment the revision is released or in a workflow, an effectivity change is **destructive**, a hard rule, see the destructive row); **create a managed baseline** (freezes a snapshot others may reference); **publish / export** a released part / BOM to ERP / MES (ESI hand-off); **transfer ownership**, **move an object to another context**, or **share an object into another context** (can flip access or expose classified content - confirm you keep the access you need, and that sharing does not expose IP / ITAR data, before doing it) | gate + human approve | binds the controlled baseline others build and buy against, or hands it downstream; each re-points manufacturing, procurement, or access |
| **Destructive / irreversible** | **edit released content in place** (blocked by lifecycle policy - the controlled path is Revise under a change; forcing it via **Set State** / admin breaks the audit chain); **demote / revert lifecycle state / de-release** (breaks every downstream that trusted the baseline); **Set State to skip the promotion / change process**; **supersede / set Obsolete** on a part (cascades to all where-used + procurement); **change effectivity on a released configuration** (silently re-points which rev ships to which units / dates); **re-point or rebuild the CAD-to-part association on a released part** (silently re-writes the released BOM - the controlled path is Revise-under-change first); **cancel / close a Change Notice or Promotion Request after downstream implementation** (ERP / procurement already acted); **force undo-checkout or check-in on another user's checkout** (discards their work); **delete** an object - an **iteration** (including **rolling back / resetting to a prior iteration**, which discards the latest), **a revision, or the whole version history** (Windchill has **no recycle bin** by default - delete is **permanent**, and blocked while referenced by a baseline / structure / change); **override a domain policy or ad-hoc ACL**, or **move / share / download / export an IP / ITAR-classified object across a context or to an external system to grant access or evade the classification** (a deliberate cross-context transfer or an export that bypasses the control is an export-control event - this is **not** routine authorized checkout by a cleared user working inside their own context, which is normal reversible edit) | hard gate + named approver + re-read | permanent or export-controlled; re-points the whole company's structure; cannot be cleanly undone; crosses a compliance boundary |

**Bulk / mass form of any row** - mass Revise, bulk promote / publish, a **CSV / spreadsheet load (Bulk Load)**,
or a mass effectivity change - is not a separate class: classify it by the **per-item** row, then gate at the
**amplified blast radius**. A mass Obsolete or mass effectivity change resolves to the destructive gate, not the
single-item one. Read the full target set (where-used across all of it) before running it.

**Gate severity scales within a class.** A routine In-Work **check-in** is the low-blast end of committing (confirm,
gate one at a time); **publishing a released BOM to ERP, completing a change, or a released-effectivity change** are
the high-blast end (named approver + re-read). Do not over-gate routine In-Work iteration to the point of driving
workarounds, and do not under-gate a downstream hand-off.

## Reclassification rules (read this)
- **A change to a released revision is not an edit - it is a new revision under a change.** Released content is
  frozen by lifecycle policy. The only controlled path is **Revise** (new revision, In Work) inside a **Change
  Notice**; the **CN completion** is the committing release. Treat any "edit the released part" request as
  revise-under-change, never in-place, and never via Set State.
- **A check-in is a new iteration, not a revision or a change.** The **Latest** config spec silently resolves to
  the newest iteration, so checking in quietly changes what "Latest" builds - but it is not a controlled release.
  Do not treat "I checked it in" as "I released the change." Controlled release still needs a promotion or change.
- **Releasing the EBOM is not releasing the MBOM.** The **Design view** and **Manufacturing view** each have their
  own version and release. A part whose Design view is Released can sit over a Working Manufacturing view - the
  plant's structure is still uncontrolled. Read the **view** you act on, do not trust the part-level state.
- **Effectivity is a committing (often destructive) config change, not an attribute edit.** Setting or changing
  date / lot / serial effectivity re-points which revision production consumes without touching a BOM line. On a
  released configuration it can supersede a part in the field - gate it like a supersede; know the fleet it moves.
- **A workflow / Change Notice approval is the release event.** Voting the final task completes the CN, applies
  the release, and drives downstream (ERP BOM update, procurement). It is the most consequential write in the
  flow, not a review formality - never auto-vote / auto-approve to move a change along.
- **A Promotion Request is not a change.** It moves lifecycle state only; it carries no revision and no change
  audit. Releasing *changed* content by promotion instead of a Change Notice skips the governed process - use the
  path the content requires.
- **Obsolete / supersede is a fleet action.** It cascades to every where-used assembly and to procurement. Run
  **where-used** first and gate it as destructive; do not Obsolete a rev to "clean up" without the blast radius.
- **The config spec decides the product you act on.** Latest vs Released vs Baseline vs Effectivity vs As-Stored
  resolve the same structure differently. State the config spec before reading, comparing, or acting on a BOM.
- **WTPart and CAD Document are two version streams.** A CAD check-in iterates the EPMDocument; it does **not**
  revise or release the linked part. Rebuild / associate, then revise and release the part separately.
  Re-pointing or rebuilding the association on a **released** part re-writes a released BOM - Revise the part under
  a change first; that is a destructive-row action, not a working-content build.
- **Part / CAD creation escalates to committing when you cannot prove the OIR is clean.** OIRs may auto-number,
  auto-assign a lifecycle / team, or auto-checkout. If you cannot confirm the deployment does none of that, gate
  creation as committing - do not assume reversible.
- **A bulk / mass operation is the same action at fleet scale - gate at the amplified blast radius.** Mass Revise,
  bulk promote / publish, a spreadsheet / CSV load (Bulk Load), or a mass effectivity change applies to many
  objects at once. Classify each by its per-item class, then treat the batch as the higher-blast form: a mass
  Obsolete or mass effectivity change is destructive at scale and needs the destructive gate. Read the full target
  set (where-used across all of it) before running it.

Universal rules to teach: read the part / CAD + the exact version (`revision.iteration`) + lifecycle state + view
+ **config spec** + effectivity + policy before any write, and **re-read at execute** (another user may have
iterated, checked out, released, or revised since you read); never edit released content in place or Set-State
around a promotion / change; never bypass or auto-vote a workflow / change; never Obsolete / supersede / replace
or re-point a CAD association without where-used; never change effectivity on a released config without knowing
which units it re-points; never override a domain policy or an IP / ITAR classification.

## Worked example (a change, end to end)
A field problem is reported on bracket **BRK-1000**, Design view **rev A.3**, Released (Production). Where-used **under the Released
config spec** [read] shows it is consumed **2x in ASM-2000** and **1x in ASM-2100**, both released; the field fleet
is at unit 4,999. You **raise a Problem Report** [write-reversible] describing the failure, then a **Change Request**
[write-reversible] proposing a thicker bracket, scoping the two parents from where-used. The CR is reviewed and
**approved into a Change Notice** [write-committing] whose Change Task lists **BRK-1000 rev A as the Affected
object**. You **Revise** BRK-1000 to **rev B (B.1, In Work)** [write-reversible]; check out the owning **Creo CAD
document**, edit the geometry, **check it in** (the EPMDocument iterates to a new version), then **rebuild /
associate** so the WTPart EBOM reflects the new CAD - BRK-1000 rev A stays frozen and untouched. You run the
release workflow / promotion so **rev B goes Released** as the Resulting object; because EBOM release is not MBOM
release (gotcha #7), you **transform the Design change into the Manufacturing view via MPMLink** and release the
MBOM view too. The change applies **serial effectivity from unit 5000 on**, so units 1-4999 keep rev A and 5000+
get rev B - **no BOM line was deleted, the effectivity did the supersede**. Serial effectivity fits here because the
split is by unit; a **date** effectivity with a past start would retroactively re-point already-shipped units, and a
**lot** effectivity mis-targets if the wrong batch is named - pick the effectivity type that matches how the fleet is
tracked. **Completing the CN** [write-committing]
publishes via **ESI to ERP**, which updates its manufacturing BOM and re-points procurement to the new part from
serial 5000. Editing rev A in place, or flipping effectivity to "all units" without checking the field fleet,
would have retroactively invalidated the 4,999 units already built and shipped.

**A destructive-recovery variant.** Suppose after release you find rev B's effectivity was set to **all units** by
mistake, and ERP already pulled the change. You cannot cleanly **de-release** rev B - demoting it breaks the
downstream that trusted it. The forward path is a **new change**: correct the effectivity to serial 5000+ (a
controlled config change), re-publish, and let ERP re-align; rev A, rev B, and both effectivity settings stay in
the audit trail. Any parts already **bought** against the wrong effectivity are not un-bought by editing Windchill
- that reconciles on the ERP side (`sap-mm`).

## Gotchas that bite (the real set - causal chains)
1. **Version = revision + iteration; a check-in makes a new iteration, not a revision or a change.** A.1 -> A.2 on
   every check-in is uncontrolled, and the **Latest** config spec silently resolves to the newest iteration - so
   "I checked it in" quietly changes what Latest builds. Only a **Revise** or a promotion / change is a controlled step.
2. **A Released iteration is frozen by lifecycle policy - you cannot iterate it in place.** The controlled path is
   **Revise** to a new revision (In Work) under a Change Notice. Forcing an edit via **Set State** or admin
   override breaks the audit chain and the baseline everyone downstream trusts.
3. **WTPart and CAD Document are separate objects with separate versions.** Editing and checking in the Creo CAD
   document iterates the **EPMDocument** but does **not** update the part **EBOM** until the build / associativity
   re-runs - the part structure can be stale relative to the CAD.
4. **The BOM you see depends on the config spec.** Latest shows in-work design; Released shows production; Baseline
   pins a snapshot; Effectivity resolves by unit / date; As-Stored pins saved iterations. Reading or acting on a
   structure without knowing the config spec reads a different product than the one that builds.
5. **As-Stored vs Latest are not the same structure.** A stored structure pins the exact iterations saved with it;
   Latest floats to the newest. Comparing or acting under the wrong lens shows a diff that is a config artifact, not a real change.
6. **A Baseline pins specific iterations.** A Baseline config spec resolves to those, not Latest; a change made
   after the baseline does not appear in it. Trusting a baseline as "current" ships stale content.
7. **An EBOM (Design view) change does not flow to the MBOM (Manufacturing view).** Each view has its own version
   stream; manufacturing keeps building the current MBOM until the change is transformed via **MPMLink** and the
   Manufacturing view re-released and published.
8. **Effectivity is a silent switch.** Changing date / lot / serial effectivity re-points which revision
   production uses with **no visible BOM edit** - on a released config it can supersede a part in the field and mis-ship the wrong rev to the wrong units.
9. **Supersede / Obsolete cascades to where-used and procurement.** Setting a part Obsolete without running
   where-used strands every assembly still calling it and can stop or misdirect buying. It is a fleet action, not cleanup.
10. **Undo checkout discards all edits since checkout.** Not undo-last - it reverts to the last checked-in
    iteration and the discarded work has no undo. **Forcing** another user's undo-checkout or check-in destroys their in-progress work the same way.
11. **An object In Work under a workflow / change is owned by that process, not you.** Editing it needs a task that
    permits it; **aborting a workflow mid-approval** loses the collected votes and returns the object to its prior state.
12. **Completing a Change Notice is the release event.** It drives the Resulting objects to Released and triggers
    downstream (ERP BOM update, procurement). Auto-voting / auto-approving to advance a change releases uncontrolled content.
13. **A Promotion Request only moves lifecycle state.** It creates no revision and carries no change audit. Using a
    promotion to release changed content skips the change process - know which governance the content requires.
14. **Re-pointing the CAD-to-part association, or rebuilding from a restructured CAD assembly, silently re-writes
    the BOM.** The part Number looks unchanged while its uses are added / removed / re-quantified by the build.
15. **A CAD check-in makes a new EPMDocument iteration, not a new part revision.** The linked WTPart's Number and
    revision can look identical while the geometry changed - "the part rev didn't change so nothing changed" is a
    blind spot. Track the CAD document version, not just the part rev.
16. **Representations (Creo View viewables / thumbnails) are published separately and go stale.** After a CAD
    check-in the viewable can lag until re-published - a viewer sees old geometry while believing it is current.
17. **Where-used / used-in is the blast radius - skipping it is flying blind.** Before revising, replacing, or
    obsoleting a part, where-used tells you which assemblies you are about to change. Not running it means you do not know.
18. **Lifecycle state gates access (state-dependent policy).** A Working object you could modify becomes read-only
    once Released; "I could change it yesterday" does not survive the promotion.
19. **OIRs decide what "create a part" actually does.** They can auto-number, assign a lifecycle template / team,
    or auto-checkout, so creation is not always a clean reversible In-Work draft. If you cannot confirm the OIR is benign, gate creation as committing.
20. **Moving an object to another context re-evaluates its domain / policy.** It can lock out the original team or
    expose it to a new group. Ownership / context transfer is a committing access change, not a filing move.
21. **Delete is permanent - Windchill has no recycle bin by default.** Deleting an iteration, a revision, or the
    whole version history cannot be undone (recover only from backup) and is blocked while the object is referenced
    by a baseline, a released structure, or a change. Know **which scope** the delete covers before running it.
    (Contrast Teamcenter, where a soft delete may be admin-restorable - do not assume that here.)
22. **A rejected workflow / promotion is not a release.** Check the object's **actual lifecycle state** after any
    process ends, not the request you launched; a reject leaves it in the prior state, an approve froze it.
23. **Options & Variants: the generic product is a superset.** A **variant specification** resolves it to a
    configured product. Acting on the generic structure double-counts option-exclusive parts; acting on one
    configured variant misses parts other option selections include. State the variant spec.
24. **ESI publish to ERP / MES is a commit hand-off, not a passive sync.** A premature or wrong publish (MBOM not
    aligned, effectivity wrong) drives manufacturing and procurement off the wrong baseline. It is a commit.
25. **IP / ITAR / export classification gates who can even read a CAD document.** A cross-context move or an ERP
    publish of a classified object can be an **export-control event**; overriding the classification to grant
    access is a compliance breach, not a permissions shortcut.
26. **Two changes on one object collide.** An object already In Work under one Change Notice cannot be revised
    under another; launching a second change or workflow locks / blocks one. Windchill also will not hold **two
    In-Work revisions of the same master** at once - a Revise is blocked while an In-Work revision already exists,
    so you must release or discard the working rev before revising again. Read the object's current change /
    workflow / revision state before starting either.

(Deep detail: `references/structure-config-and-effectivity.md`, `references/change-lifecycle-and-access.md`.)

## Edge states & special cases
Each breaks naive "read the BOM, act on the part" logic - key rule inline, full behavior in the references.
- **Config spec (Latest / Released / Baseline / Effectivity / As-Stored)** - the same structure resolves
  differently by lens; pin the config spec before reading. Detail in `references/structure-config-and-effectivity.md`.
- **View / EBOM vs MBOM divergence** - two version streams for one part; changes propagate one way (Design ->
  Manufacturing) via MPMLink on release, not automatically. Align before publishing. Same reference.
- **Effectivity (date vs lot / serial), overlaps and gaps** - the window that decides which rev is used; an
  overlap resolves to two revs or an error, a gap to an empty structure - both mis-ship.
- **Options & Variants** - a superset generic product resolved by a variant specification; the structure you act
  on depends on the variant spec as well as the config spec.
- **CAD-driven structure (Creo / Workgroup Manager)** - when the EBOM is built from the CAD assembly, editing
  structure in Windchill vs in Creo can conflict; the authoring tool owns the structure round-trip.
- **Baselines** - a frozen snapshot of specific iterations; a Baseline config spec resolves to it, not Latest.
- **Multiple views / representations on one part** - a Design view and a Manufacturing view, each an independent
  version with its own release; a released Design view over a Working Manufacturing view is a real trap. Read the
  status of the specific view you act on.
- **Access (contexts, domains, policies, OIR, IP / ITAR)** - who can read / modify / release is context-, state-,
  and classification-driven; export classification can block read entirely. Detail in `references/change-lifecycle-and-access.md`.

## Recovery patterns (can it be undone, and what cannot)

| Situation | Recovery path |
|---|---|
| A working (In Work) iteration was edited wrong | check out and fix, or **undo checkout** to revert to the last check-in - reversible while In Work; nothing was released |
| A **Save As** was used where **Revise** was meant (new Number, no link to the original) | traceability is broken and there is no automatic fix - Revise the correct object instead, or Obsolete the stray new object under a change and re-point consumers; do not leave two unlinked identities in the field |
| A part / CAD was **created under a bad OIR** (landed Released or in a workflow, or wrongly numbered) | it is not a clean draft - if it entered a workflow, abort it (losing any votes) to return it to Working; a wrong Number or lifecycle usually needs admin correction or a fresh create; do not build on the mis-initialized object |
| A revision was released by mistake | you cannot cleanly edit it - **Revise** to a new revision under a change and re-release; **demote / de-release** breaks downstream trust and is a controlled last resort, not an undo |
| The **EBOM (Design view)** released but the **MBOM (Manufacturing view)** did not (or one view did, another did not) | the plant's structure is uncontrolled - transform / release the Manufacturing view; check each view's state, do not trust the part-level status alone |
| The CAD document changed but the **part BOM is stale** (not rebuilt) | rebuild / associate the part from CAD and re-verify; if the part was already released, Revise it under a change and re-release |
| Effectivity was set wrong on a released config | correct it with a **new controlled config change** (itself committing); the window may already have driven production / buying, which reconciles on the ERP side |
| A part was Obsoleted / superseded in error | raise a **new change** to reinstate / re-release; procurement and ERP may already have acted on the Obsolete - reconcile downstream separately |
| A workflow / change was aborted mid-approval | the object returns to its prior state and the collected votes are lost; restart the process from the beginning |
| An undo checkout discarded edits | the edits are gone (reverted to last check-in); redo them - there is no undo for discarded checkout work |
| Another user's checkout was force-broken | their in-progress work is discarded and unrecoverable; avoid force-breaking, coordinate instead |
| A change / promotion was cancelled after ERP / procurement implemented it | Windchill cancelling does not revert ERP or un-buy parts; reverse with a **new change** and let ERP re-align (`sap-mm`) |
| A **baseline** was captured from the wrong config spec or the wrong iterations | the baseline is a frozen snapshot - do not edit it; capture a **new baseline** from the correct config spec and re-point consumers; downstream that already built against the bad snapshot reconciles like any wrong release; the old baseline stays in the audit trail |
| Two changes / workflows **collide** on one object (already In Work under one) | read the object's current change / workflow state **before** starting either; sequence them or coordinate - do not open a second change against an object already being changed; aborting the first to free it loses its collected votes |
| An object (iteration / revision / version history) was **deleted** | permanent - no recycle bin by default; blocked while referenced - recover only from backup |
| An **ESI publish failed or only partially applied** (Windchill released but ERP did not accept) | the two systems now disagree - check the ESI / publish transaction status, do not treat a completed release as ERP acceptance; correct the cause and **re-publish** under a change, then reconcile ERP; a publish cannot be cleanly retracted |
| A domain policy or IP / ITAR classification was overridden | a compliance incident, not a technical rollback - restore the classification / policy and report per policy; assume the exposure happened |

Reversal in Windchill is almost always a **new revision or a new change**, not an undo: the old revision, the
change, the votes, and both effectivity settings stay in the audit trail. What is truly gone is any work lost to
an undo checkout, any delete, and any downstream (parts bought, ERP updated, product shipped) an earlier release
or publish already drove.

## Guardrails
- Read the part + the exact **version** (`revision.iteration`) + lifecycle state + **view** + **config spec** +
  effectivity + policy before acting; re-read at execute **and again after any gate approval** (state can change
  between approval and execution, especially under concurrent workflows). A structure read without its config spec
  is not a fact.
- Never edit released content in place - **Revise** to a new rev under a change; the CN completion is the release.
  Never use **Set State** to skip a promotion / change.
- Never Obsolete / supersede / replace a part, or re-point a CAD association, without running **where-used /
  used-in** first - that is the blast radius.
- Never change effectivity on a released configuration without knowing which units / dates it re-points; treat it as a supersede.
- Never bypass or auto-vote a workflow or a change to move it along; never override a domain policy or an IP / ITAR classification to grant access or export.
- Never force an undo-checkout or check-in on another user's checkout - their work is destroyed and unrecoverable.
- Windchill deployments are heavily configured: lifecycle templates, workflow and change subtypes, **OIRs**, config
  specs, domain policies, numbering, and view sets vary by site. Read the actual deployed configuration - do not
  assume the standard state names, object types, or steps are the ones in front of you. Read the site's lifecycle
  templates, OIRs, domain policies, and view sets before acting; do not act on assumed defaults.
- For anything in the destructive row (edit-released, de-release / Set-State, supersede / Obsolete,
  released-effectivity change, change / promotion cancel after implementation, force-break checkout, delete, policy
  or classification override, any mass / bulk variant of these): named approver, re-read, and log the reason.

## References (load on demand)
- `references/structure-config-and-effectivity.md` - WTPart vs CAD Document (EPMDocument) and versioning
  (revision.iteration), views (EBOM Design vs MBOM Manufacturing) and MPMLink BOM transformation, config specs
  (Latest / Released / Baseline / Effectivity / As-Stored), effectivity (date / lot / serial) with overlaps and
  gaps, managed baselines, options & variants, and structure compare.
- `references/change-lifecycle-and-access.md` - the change lifecycle (PR -> CR -> CN -> Change Task, Affected vs
  Resulting), lifecycle states / promotion requests / Set State, workflow and voting, check-out / check-in and
  workspace vs commonspace, contexts / domains / policies / OIRs / IP-ITAR classification, and the ESI publish /
  export hand-off to ERP and MES.
