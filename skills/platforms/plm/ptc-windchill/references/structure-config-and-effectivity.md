# Windchill - structure, versioning, config specs, effectivity, variants

The cases where "read the BOM and act on the part" is wrong. In Windchill the structure you see is
**configured** - a **config spec** (and, for options, a variant specification) resolves the version tree into the
one structure that builds, and the **part** and the **CAD document** are two separate objects with separate
versions. Read when a task touches a BOM, a config spec, iteration vs revision, EBOM / MBOM alignment,
effectivity, a baseline, or a variant.

## Contents
- Part vs CAD document, and versioning (revision.iteration)
- Views - EBOM (Design) vs MBOM (Manufacturing) and MPMLink
- Config specs - the configuration lens
- Effectivity (date / lot / serial)
- Baselines
- Options & variants
- Structure compare

## Part vs CAD document, and versioning (revision.iteration)
- The **WTPart** is the engineering item and the BOM identity; it holds the product structure (**uses** links),
  attributes, lifecycle state, and a **view**. The **CAD Document (EPMDocument)** is the Creo (or other CAD) file
  object holding geometry. They are **separate objects**, each with its own Number, version stream, and lifecycle.
- They are joined by an **owner / build association**. The part's **EBOM can be built (published) from the CAD
  assembly structure** via build rules, or the part structure can be managed independently. If the CAD assembly
  changes and the part is not rebuilt, the **part BOM is stale** relative to the CAD.
- **Version = `revision.iteration`** (A.1, A.2, B.1). **Iteration** increments automatically on every **check-in**
  and is **not** a controlled step - it is a new working snapshot. **Revision** increments only via **Revise**,
  which starts a new **In Work** revision. A released revision is frozen; you Revise to change it.
- Only the **latest iteration of a revision** is the working head; a config spec decides which revision (and, for
  some specs, which iteration) of each child resolves.

## Views - EBOM (Design) vs MBOM (Manufacturing) and MPMLink
- A WTPart carries a **view**. The **Design view** structure is the **EBOM** (as-designed); the **Manufacturing
  view** structure is the **MBOM** (as-planned, by plant / line - adds process structure, phantoms, consumables,
  alternates). Each view has its **own version stream and its own release**.
- **MPMLink** transforms the EBOM into the MBOM (**BOM transformation**) and maintains **associativity** so you
  can see which EBOM lines map to which MBOM lines and what is out of sync. It also links the MBOM to process
  plans / operations / work instructions.
- An **EBOM change does not automatically become an MBOM change.** Manufacturing keeps building the current MBOM
  until it is transformed and the Manufacturing view is **re-released** and published. A designer's change is
  invisible to the plant until propagated. Releasing the Design view is **not** releasing the Manufacturing view.

## Config specs - the configuration lens
A **config spec** decides which iteration / revision of each child a structure expansion returns. Common specs:
- **Latest** - the newest iteration of the newest revision (optionally filtered to a working / in-work head).
  Shows in-progress, unreleased design. Do **not** build or buy from Latest.
- **Released (by lifecycle state)** - the newest revision in a given lifecycle state (e.g. Released). What
  production should read.
- **Baseline** - resolves to the exact iterations captured in a named **managed baseline** (below).
- **Effectivity (date / unit / serial)** - resolves to the revision whose effectivity is valid for a given date or
  unit / serial number - the "what actually ships on this date / this serial" view.
- **As-Stored** - the exact iterations that were stored when a structure was last saved (a pinned snapshot).
The **same assembly under two different config specs is two different structures**. Never compare, net, or act on
a structure without stating the config spec that produced it. Engineering (Latest), manufacturing (Released), and
service (effectivity) routinely see three different BOMs for one product.

## Effectivity (date / lot / serial)
- Effectivity is the window over which a revision (or an occurrence) is valid: a **date** range, or a **lot / unit
  / serial number** range (from unit N, or N-M), often defined against an end item / product.
- It is how supersession works **without editing the BOM**: rev A effective units 1-4999, rev B effective 5000+
  means the configured structure returns rev A or rev B depending on the unit you configure for. No BOM line
  changed; the effectivity did the switch.
- **Overlaps** (two revisions effective for the same unit) make the configuration ambiguous - it may return two
  revs or an error. **Gaps** (a unit covered by no revision) return an empty / underspecified structure. Both are
  config errors that mis-ship or ship nothing.
- Changing effectivity on a **released** configuration is high-blast: it retroactively re-points which units get
  which revision, including already-built or shipped product. Gate it as a supersede, and know the field fleet it
  moves before changing it.

## Baselines
- A **managed baseline** captures **specific iterations** of a set of objects - a frozen snapshot for
  configuration management (a design review baseline, an as-released baseline, an as-shipped baseline).
- A **Baseline config spec** resolves a structure to the iterations in that baseline, not to Latest. A change made
  after the baseline does **not** appear in it - trusting a baseline as "current" reads stale content.
- A baseline is a reference others may rely on; deleting one, or treating a stale baseline as live, misleads
  downstream. Do not confuse a baseline (a snapshot) with a Release (a lifecycle state on the object itself).

## Options & variants
- An **Options & Variants** (WOV) product is a **generic / configurable** structure - a superset ("150%") BOM
  whose occurrences carry **option / choice expressions** and appear only when their option is selected.
- A **variant specification** (a set of option-value choices) resolves the superset to a specific configured
  product ("100%"). The structure you act on depends on the variant spec **as well as** the config spec and effectivity.
- Acting on a superset generic BOM as if it were a single product double-counts option-exclusive parts; acting on
  one configured variant misses parts other option selections would include. State the variant spec.

## Structure compare
- Structure compare is the reconciliation tool: rev A vs rev B, EBOM (Design view) vs MBOM (Manufacturing view),
  structure vs baseline, or as-planned vs as-built. It reports added / removed / re-quantified / re-pointed uses.
- A compare is only meaningful when **both sides are pinned** to a stated config spec (and variant spec /
  effectivity where they apply). Comparing Latest against Released, or two different variant resolutions, produces
  a diff that is an artifact of the configuration, not a real design change. Pin both, then read the diff.
