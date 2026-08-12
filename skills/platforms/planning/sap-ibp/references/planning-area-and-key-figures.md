# SAP IBP - planning area, key figures, levels, and data integration

The data model under every plan. Get this wrong and an edit lands at the wrong grain, spreads by the wrong
basis, or overwrites shared history. Read when a workflow edits a key figure above its base level, touches
calculated KFs, changes structure, or loads/exports data.

## Contents
- Planning area (the container)
- Master data types and planning combinations
- Key figures: stored vs calculated
- Planning levels and base level
- Aggregation and disaggregation basis
- Time profile and lock horizons
- Data integration (actuals in, plan out)

## Planning area (the container)
The **planning area** holds the whole model: master data types, attributes, the time profile, planning
levels, key figures, and versions. It is configured and **activated**; a structure change (new KF, changed
level, new master data type) requires re-activation and can invalidate or require re-load of stored data.
This is admin/config work, not a planning edit - never change structure to unblock a planning task under
time pressure.

## Master data types and planning combinations
Master data types (Product, Location, Customer, Resource, and compound types) define the dimensions;
**attributes** are their fields. A **planning combination** (a valid Product-Location-Customer tuple, etc.)
is what actually gets planned. Adding a combination creates new cells to plan; removing one drops its stored
key-figure data. A **local member** added in an Excel view is not real master data until saved - saving it
creates a combination that is then planned everywhere.

## Key figures: stored vs calculated
- **Stored KF** - holds its own data; editable (subject to level and lock rules). Writing to it persists.
- **Calculated KF** - derived from other KFs by a calculation at a defined level; **not directly editable**.
  Trying to "set" a calculated KF either is rejected or actually writes an input KF underneath, which then
  recalculates. Know which KFs in your view are calculated before writing.
- KFs also differ by **version dependency**: version-specific (copied per version) vs version-independent
  (one shared copy, e.g. many actuals/history KFs). See `versions-scenarios-snapshots.md`.

## Planning levels and base level
Every KF has a **base planning level** - the finest grain at which it is stored/calculated (e.g.
product-location-week). A planning view can show it aggregated above that. Reads aggregate up cleanly;
**writes above the base level must be disaggregated back down**, which is where the risk is.

## Aggregation and disaggregation basis
- Aggregation up = sum/average per the KF's rule; unambiguous.
- **Disaggregation down** = a value typed at an aggregate level is split to detail by a **disaggregation
  basis**, usually the proportional share of another KF (e.g. last year's actuals, or the KF's own current
  values). Edit product-group demand and it spreads across products by that basis.
- The trap: if the basis KF is **empty or zero** at the target level, IBP falls back to an **even split**
  or the value lands nowhere - a silent mis-distribution. Before editing above base level, confirm the
  basis KF has meaningful data at that level.

## Time profile and lock horizons
- The **time profile** is the calendar hierarchy (day/week/month/quarter/year) with technical vs storage
  periods; a KF stored monthly shown weekly is disaggregated by the calendar.
- **Lock / frozen horizons** - some KFs are locked in the near-term or the past (a frozen forecast horizon,
  closed history). Edits there are rejected or ignored. Editing past periods also rewrites the history the
  statistical forecast learns from and breaks accuracy comparison against snapshots.

## Data integration (actuals in, plan out)
- **Inbound** - master data and actuals (sales history, stock, open orders) load from S/4HANA or ECC via
  SAP Cloud Integration for data services (CI-DS; also Smart Data Integration / SDI, formerly HCI), usually
  on a schedule. A load can be **delta**
  (update) or **replace** (wipe and re-write); a replace load of the actuals/history KF overwrites it, so a
  bad or partial file corrupts the seed for every forecast that reads it.
- **Freshness** - because loads are scheduled (often nightly), IBP's actuals and projected stock **lag** the
  live ERP position. Check the last successful integration run before trusting a quantity; the live physical
  position lives in `sap-mm`.
- **Outbound (release)** - the agreed plan exports to execution: planned orders, purchase/stock-transfer
  requisitions, planned independent requirements (PIRs) to S/4HANA / ECC / PP-DS, or Response
  deployment/confirmation to orders. This creates real execution documents and cannot be undone from IBP -
  correct in the receiving system and re-integrate.
