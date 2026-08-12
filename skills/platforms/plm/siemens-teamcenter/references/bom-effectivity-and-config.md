# Teamcenter - structure, revision rules, effectivity, variants

The cases where "read the BOM and act on the part" is wrong. In Teamcenter the structure you see is
**configured** - a revision rule and effectivity (and, for options, a variant rule) resolve a superset into the
one structure that builds. Read when a task touches a BOM, a revision rule, effectivity, EBOM/MBOM alignment,
or a variant.

## Contents
- Item / revision / BVR - where structure lives
- Revision rules - the configuration lens
- Precise vs imprecise occurrences
- Effectivity (date / unit / serial)
- EBOM vs MBOM and propagation
- Variants and configured structures
- Structure compare

## Item / revision / BVR - where structure lives
- The **item** is identity; the **item revision** carries the design and status; the revision's structure lives
  in its **BOM View Revision (BVR)**. A revision can have a BVR for a **view type** (e.g. a Design/EBOM view and
  a Manufacturing/MBOM view).
- The **BVR has its own release status**, separate from the item revision's. Releasing the revision does not
  release the BVR. A revision that reads "Released" with a Working BVR has an **uncontrolled structure**.
- BOM lines (**occurrences**) carry quantity, find number, reference designator, and either a precise revision
  or an imprecise item reference (below).

## Revision rules - the configuration lens
A revision rule is an ordered set of entries that decides which revision of each child an expansion shows.
Common rules:
- **Latest Working** - the newest revision regardless of status; shows in-progress, unreleased design. Do **not**
  build or buy from this.
- **Latest Released** - the newest revision that has a release status; what production should read.
- **Precise** - honor the exact revision pinned on each occurrence (ignore floating).
- **By status + effectivity (date / unit)** - resolve to the revision whose release status is effective for a
  given date or unit/serial number - the "what actually ships on this date / this serial" view.
The **same assembly under two different rules is two different structures**. Never compare, net, or act on a
structure without stating the rule that produced it. Engineering (Latest Working), manufacturing (Latest
Released), and service (unit-effective) routinely see three different BOMs for one product.

## Precise vs imprecise occurrences
- An **imprecise** occurrence points at the **item**; the revision rule resolves which revision. It **floats** -
  a new child revision or a different rule changes what the parent contains.
- A **precise** occurrence pins a **specific child revision**. It does not float; a later child revision does not
  appear until the occurrence is re-pointed.
- **Releasing a parent typically converts its occurrences to precise**, freezing the exact child revisions in
  that baseline. So revising a child after the parent is released does **not** flow into the released parent -
  that requires a new parent revision (under a change).
- Consequence: whether a child change reaches an assembly depends entirely on precise-vs-imprecise plus the
  revision rule. Check both before assuming "the fix is in the BOM".

## Effectivity (date / unit / serial)
- Effectivity is the window over which a **release status** (or an occurrence) is valid: a **date** range, or a
  **unit / serial number** range (from unit N, or N-M), sometimes by end-item.
- It is how supersession works **without editing the BOM**: rev A effective units 1-4999, rev B effective 5000+
  means the configured structure returns rev A or rev B depending on the unit you configure for. No BOM line
  changed; the effectivity did the switch.
- **Overlaps** (two revisions effective for the same unit) make the configuration ambiguous - it may return two
  revs or an error. **Gaps** (a unit covered by no revision) return an empty/underspecified structure. Both are
  config errors that mis-ship or ship nothing.
- Changing effectivity on a **released** configuration is high-blast: it retroactively re-points which units get
  which revision, including already-built or shipped product. Gate it as a supersede, and know the field fleet
  it moves before changing it.

## EBOM vs MBOM and propagation
- **EBOM** (engineering, as-designed) is the designer's structure. **MBOM** (manufacturing, as-planned) is the
  plant/line structure that adds process order, phantom/consumable items, alternates, and plant-specific
  substructure. Same product, two structures.
- An **EBOM change does not automatically become an MBOM change.** Manufacturing keeps building the current MBOM
  until it is updated (often via a BOM-alignment / EBOM-to-MBOM process) and **re-released**. A designer's change
  is invisible to the plant until propagated and published.
- Align by **structure compare** (EBOM vs MBOM) to find what the manufacturing structure is missing, apply the
  change to the MBOM, release the MBOM's BVR, then publish downstream. Publishing an unaligned MBOM ships the
  plant a structure that does not match the released design.

## Variants and configured structures
- A **variant** (options & variants, classic variant conditions, or modular variants) structure is a **superset
  ("150%") BOM**: occurrences carry option/condition expressions and only appear when the option is selected.
- A **variant rule** (a set of option-value selections) resolves the superset to a specific **"100%" configured
  product**. The structure you act on depends on the variant rule as well as the revision rule and effectivity.
- Acting on a superset BOM as if it were a single product double-counts option-exclusive parts; acting on one
  configured variant misses parts that other option selections would include. State the variant rule.

## Structure compare
- Structure compare is the reconciliation tool: rev A vs rev B, EBOM vs MBOM, or as-planned vs as-built. It
  reports added / removed / re-quantified / re-pointed occurrences.
- A compare is only meaningful when **both sides are pinned** to a stated revision rule (and variant rule /
  effectivity where they apply). Comparing Latest Working against Latest Released, or two different variant
  resolutions, produces a diff that is an artifact of the configuration, not a real design change. Pin both, then read the diff.
