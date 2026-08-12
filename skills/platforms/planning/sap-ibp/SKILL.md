---
name: sap-ibp
description: "SAP IBP (Integrated Business Planning), cloud - the safe operation of demand, supply, inventory, and S&OP planning: planning areas, key figures and planning levels, versions, scenarios and snapshots, planning operators and application jobs, the IBP Excel add-in and Fiori planning UI, and sharing or releasing a plan into the baseline and to execution. Use when the connected planning system is SAP IBP, or the work mentions IBP for Demand / Response and Supply / Inventory Optimization / S&OP, a planning area or planning level, a key figure (consensus demand, statistical forecast, projected stock, safety stock), a version / baseline / scenario, a copy / snapshot / S&OP supply / inventory-optimization operator, Simulate vs Save Data in the Excel add-in, disaggregation, an application job, or publishing a version to the baseline and releasing supply to S/4HANA / ERP / execution."
---

# SAP IBP - operating it safely

SAP IBP is SAP's cloud planning suite (Demand, Response and Supply, Inventory Optimization, S&OP,
Demand-Driven Replenishment, Control Tower), planned in a Microsoft Excel add-in and in Fiori web apps over
a time-series data model. IBP is dangerous in a different way from an ERP: nothing here posts to a ledger,
but a plan overwrite is silent and has no document trail. **A key-figure value that gets overwritten is
just gone** unless a snapshot or a backup version was taken first, and once a plan is promoted to the
baseline or released to execution it drives real orders. Reading, simulating, and what-if in a scenario are
free. The damage is in three moves: overwriting stored key figures (a copy or operator run), promoting a
version into the baseline (the plan of record), and releasing supply to ERP. This skill classifies those so
the harness can gate them, and gives the edge states and the one real recovery lever (snapshots) that
decide whether a mistake is fixable.

## Contents
- When this applies / when NOT
- Object & state model
- Vocabulary that bites
- Operations: read / write / destructive
- Gotchas that bite
- Edge states & special cases
- Reconciliation & freshness
- Recovery patterns
- Guardrails
- References

## When this applies
Connector is SAP IBP and the work is demand/supply/inventory/S&OP planning. When NOT:
- Kinaxis RapidResponse planning -> `kinaxis`
- Blue Yonder / JDA demand & fulfillment planning -> `blueyonder-planning`
- o9 planning -> `o9`; Anaplan -> `anaplan`
- ERP inventory/procurement postings, goods movements, real stock and PO documents -> `sap-mm`
  (IBP plans; MM executes - releasing an IBP plan lands there)
- Ledger, costing, financial actuals -> `sap-fi`

## Object & state model (reason about the plan's state, not the noun)
- **Planning area** - the data model container: master data types, attributes, time profile, planning
  levels, key figures, and versions. It is the model, not a plan. A structure change needs **activation**
  and can invalidate or drop stored data - admin territory, not a planning edit.
- **Master data & planning combinations** - Product, Location, Customer, Resource and the valid
  combinations that get planned. Adding a combination creates new cells to plan; removing one drops its
  stored key-figure data.
- **Key figure (KF)** - a measure at a planning level. **Stored** KFs hold data; **calculated** KFs derive
  from others by a calculation and cannot be edited. Editing a stored KF at a level above its base
  **disaggregates** the value down to detail.
- **Planning level** - the granularity a KF is stored/calculated at (e.g. product-location-week). What you
  see in a planning view may be aggregated above it.
- **Version** - a full parallel copy of the plan's key figures. The **baseline** version is the plan of
  record everyone sees and integration exports; **alternative versions** are sandboxes for simulation.
- **Scenario** - a what-if layer on top of a version that stores only your deltas. Simulate freely, then
  either discard it (no effect) or **save it into the version** (a one-way commit of the deltas).
- **Snapshot** - a frozen copy of a key figure at a point in time, kept in a snapshot KF. This is the main
  backup and accuracy-comparison mechanism; without one there is no "before" to restore.
- **Plan state ladder** - draft edits in Excel (unsaved) -> Save Data to a version/scenario -> promote into
  the baseline -> release to execution. Each arrow is a larger, harder-to-undo commit.

## Vocabulary that bites
- **Simulate vs Save Data** (Excel add-in) - *Simulate* recalculates in your local view only and persists
  nothing; *Save Data* writes your cells to whatever version the **ribbon version-selector** points at, with
  no confirmation dialog. The baseline is the default target. New planners read a simulated number as saved.
  Only Save Data changes shared state.
- **Planning filter** - the saved selection (products, locations, customers, periods) that sets the **scope**
  of a planning view, an operator run, and an application job. It is a blast-radius control equal to the
  target version: the wrong filter makes an operator overwrite the wrong products or periods. Check filter
  and target version together before any run.
- **Baseline version** - not a software version; it is the live plan of record. Editing or copying into the
  baseline changes what every other planner and every export sees.
- **Share vs Publish/Promote a version** - *sharing* only makes a version visible to other planners (a read
  and collaboration act, no data change); *publishing / promoting* copies its key figures into the baseline
  and overwrites the plan of record. The word "publish" is used loosely for both, so confirm which one is
  meant before acting: one is free, one is destructive.
- **Copy operator** - overwrites the entire target key figure in the target version with the source; it is
  a replace, not a merge or add. Source clobbers target for the whole selected scope.
- **Aggregation / disaggregation** - you edit at a summary level and the value spreads to detail by a
  **disaggregation basis** (usually another KF, e.g. historical share). A wrong or empty basis mis-spreads
  or spreads evenly, silently. This is IBP's single most common quiet error.
- **Consensus demand** - the agreed demand KF that feeds supply and inventory planning. Overwriting it
  changes what every downstream supply run plans to.
- **Actuals / historical key figures** - sales history and stock loaded from ERP that seed the statistical
  forecast. They are often version-independent (shared across versions); "editing them in my sandbox
  version" still corrupts the shared history and the forecast baseline.
- **S&OP operator** - the time-series supply engine: **unconstrained heuristic**, **constrained (finite)
  heuristic**, and **optimizer** (cost-based). The three produce very different supply, production, and
  projected-stock plans from the same demand.
- **Inventory Optimization (IO) operator** - multi-echelon safety-stock / target-inventory recommendation
  (MEIO). It writes recommended safety stock; it does not move real stock.
- **Response (order-based) planning** - a separate order-level engine (Constrained Forecast Run, Deployment,
  Confirmation, gating-factor analysis) that confirms and allocates real order quantities. Order-based, not
  the time-series supply plan; its confirmations bind toward customer commitments.
- **Application job** - a scheduled or on-demand run of an operator (copy, forecast, S&OP, IO, snapshot,
  data integration) via the *Application Jobs* app. A job writes to the version it targets; scheduling a
  bad template runs the overwrite every cycle.
- **Version-independent key figure** - a KF whose data is shared by all versions (many actuals/master-style
  KFs). A "sandbox" edit to one is not sandboxed.
- **Reason code** - the tag attached to a manual override for audit; IBP keys change history / audit trail
  by it only if enabled, so an untagged overwrite may leave no explanation.

## Operations: read / write / destructive
Classify every operation family by what it does to plan state. No tool names - kinds of action.

| Class | SAP IBP operation families | Gate | Why |
|---|---|---|---|
| **Read** | open a planning view / favorite in Excel or Fiori; **Simulate** (local, unsaved); **take a snapshot** (a protective write: it writes only to a snapshot KF and overwrites no source, so it always passes the gate - safe even on the baseline); **share** a version (makes it visible to others, no data change); view dashboards, analytics, Custom Alerts, Intelligent Visibility; compare versions/scenarios/snapshots; display master data and job logs; run a forecast/IO operator into a scenario for what-if without saving (the scenario buffers the write - nothing in the plan changes) | always pass | no source-data change; read the current baseline and re-read at execute (other planners save concurrently) |
| **Write (reversible)** | Save Data into an **alternative (sandbox) version** or a **scenario**; create a version by copy; create a scenario; run a copy/forecast/S&OP/IO operator that targets a **non-baseline** version | gate one at a time | isolated from the plan of record; undo = discard the scenario or re-copy the sandbox from baseline |
| **Write (committing)** | Save Data into the **baseline** version; **save a scenario into its version**; run a copy or planning operator (copy/forecast/S&OP/IO) whose target is the **baseline** (copy forecast -> consensus, run S&OP supply, run IO to write safety stock into baseline); edit a **version-independent / actuals** KF; **create/save a new planning combination or local member** (adds shared master data that is then planned in every version); schedule an application job that writes the baseline | gate + named human approver | changes the shared plan of record that every planner and every export reads; no ledger, but real downstream effect |
| **Destructive / irreversible** | **promote/publish an alternative version into the baseline** (overwrites the current plan of record); **copy or operator overwrite of a baseline KF with no snapshot taken** (the prior values are unrecoverable); **release/export supply to ERP/execution** - planned orders, purchase/stock-transfer requisitions, PIRs to S/4HANA or ECC/PP-DS, or Response deployment/confirmation to orders; **mass data-integration import that overwrites actuals or key figures**; **delete a version, scenario, planning combination, or planning-area structure change/activation** | hard gate + named approver + reason code + snapshot/backup first + re-read | no undo in IBP; a released plan creates real execution documents; an overwrite with no snapshot destroys the prior plan permanently |

**Reclassification rule (read this):** the same *overwriting* operator (copy, S&OP, IO, statistical
forecast) is *reversible* when its target is a sandbox version/scenario and *destructive* when its target
is the baseline **and no snapshot exists**. Always check the target version and whether a backup was taken
before you classify the run - the engine is identical, the blast radius is not. **Snapshot is the
exception:** taking a snapshot only writes to a snapshot KF and overwrites no source, so it is always
protective and is never gated as committing/destructive - gate the overwrite you snapshot *before*, not the
snapshot itself.

Universal rules to teach: **Simulate is not Save** - a simulated number is not persisted; read the current
baseline and **re-read at execute** because other planners Save Data concurrently and last-write-wins;
**take a snapshot before any baseline-writing operator** so there is a "before"; never promote a version or
release to ERP to hit a plan date without the named approver; a plan is not committed until Saved, and not
real until released to execution.

## Gotchas that bite (the real set - causal chains)
1. **Simulate does not save.** Numbers shown after Simulate are a local recalculation; closing the workbook
   or refreshing loses them. Only **Save Data** persists. An agent that reports a simulated result as the
   new plan is reporting a number no one else can see.
2. **Editing a stored KF at an aggregate level disaggregates it.** Type one number at product-group level
   and it spreads across every product by the disaggregation basis. If the basis KF is empty or zero, IBP
   spreads it evenly (or not at all) - a silent mis-distribution across dozens of SKUs.
3. **A copy operator overwrites the whole target, it does not merge.** Copying statistical forecast into
   consensus demand replaces every consensus cell in scope, including planner overrides made this cycle.
   Overrides made after the source was last updated are lost with no warning.
4. **Overwriting the baseline with no snapshot is unrecoverable.** IBP has no transaction-log undo. If no
   snapshot or backup version captured the prior values, the pre-overwrite plan cannot be restored - you
   can only re-derive or re-key it.
5. **Saving into the baseline is not a sandbox.** Save Data with the baseline selected writes the plan of
   record immediately; every other planner and the next export sees it. Confirm the target version before
   saving.
6. **Version-independent key figures are not sandboxed.** Actuals and many master-style KFs share one copy
   across all versions. "I only changed it in my scenario version" still corrupts shared history and the
   forecast baseline that reads it.
7. **The three S&OP engines give different plans.** Unconstrained heuristic ignores capacity; constrained
   (finite) heuristic respects it with priority rules; the optimizer minimizes cost and can drop or resource
   supply. Running the wrong one into the baseline changes the committed supply plan and can silently unmeet
   demand the previous run met.
8. **Inventory Optimization writes a recommendation, not stock.** IO updates recommended safety-stock /
   target-inventory key figures; it moves nothing physical. Treating its output as on-hand, or feeding it to
   ERP without the supply run that acts on it, over- or under-states availability.
9. **A scenario is safe only until you save it into the version.** Simulating in a scenario touches nothing.
   *Save to version* commits the scenario deltas into the version's data - a one-way write, not a preview.
10. **Concurrent writers overwrite each other; last save wins.** IBP does not lock cells like an ERP
    document. If your planning view was opened before another planner saved, your Save Data overwrites
    theirs - and a **scheduled application job** can clobber a planner's manual save that landed seconds
    earlier, or vice versa. Refresh (re-read) immediately before saving a shared version, and check whether
    a job runs on the same version/filter/period.
11. **Statistical forecast overwrites the forecast KF for its whole scope.** A forecast run replaces the
    output KF across the selected products/periods; manual forecast overrides in that scope are wiped unless
    protected by a separate override KF or lock.
12. **A scheduled application job repeats the overwrite every cycle.** A copy/forecast/S&OP job with the
    wrong target version or filter does not misfire once - it re-runs on schedule, so a bad template quietly
    corrupts the baseline each night until someone notices.
13. **Editing past / frozen periods distorts history and accuracy.** Changing actuals or forecast in closed
    past buckets rewrites the history the statistical models learn from and breaks forecast-error /
    forecast-accuracy comparison against the snapshot of what was actually planned.
14. **Releasing supply to ERP creates real documents you cannot recall from IBP.** Exporting planned orders,
    purchase/stock-transfer requisitions, or PIRs to S/4HANA, or Response deployment/confirmation to orders,
    creates or updates execution objects downstream. Undo is not in IBP; it is a correction and re-integration
    in the receiving system (see `sap-mm`).
15. **Response confirmations bind toward customer commitments.** Order-based confirmation/gating allocates
    finite supply to specific orders; re-running or over-confirming reshuffles who gets product and can
    de-confirm a promise already communicated.
16. **A data-integration import can overwrite actuals silently.** A batch load keyed to replace rather than
    delta-update the actuals/history KF wipes and re-writes it; a bad or partial file corrupts the seed for
    every forecast that reads it.
17. **A planning-area structure change needs activation and can drop data.** Changing key figures, levels,
    or master data types and activating the area can invalidate stored values or require re-load. Activation
    is not instant - it can run for minutes to hours and **locks the planning area so no one can plan** while
    it runs. Not a planning edit, and never done to unblock a planning task under time pressure.
18. **Overwriting consensus demand re-plans everything downstream.** Consensus demand is the demand-to-supply
    handoff; a copy operator or manual Save that overwrites it silently changes what the next S&OP supply run
    and IO run plan to. An off consensus number propagates into supply, projected stock, and safety-stock
    recommendations without any error.
19. **UoM / currency conversion means a KF's number depends on its unit.** A key figure shown in cases vs
    pallets vs base UoM, or in different currency, reads as a different quantity; netting or comparing across
    units without the conversion mixes incomparable numbers.

(More per-family detail: `references/planning-operators-and-jobs.md`,
`references/versions-scenarios-snapshots.md`, `references/planning-area-and-key-figures.md`.)

## Edge states & special cases
Each breaks naive "read the key figure, write the key figure" logic - the rule inline, the depth in
references.
- **Calculated vs stored KFs** - a calculated KF cannot be edited; attempting to "set" it either fails or
  actually edits an input KF underneath. Know which is which before writing. (`planning-area-and-key-figures.md`)
- **Disaggregation basis empty/zero** - the value spreads evenly or lands nowhere; verify the basis KF has
  data at the target level before editing above base level.
- **Version-independent KFs** - shared across all versions; a sandbox edit is not sandboxed.
- **Time-series vs order-based (Response)** - the S&OP supply plan is aggregate time-series; Response is
  order-level with confirmations. Reading one as the other mis-states what is actually promised.
- **Local members / new planning combinations** - a member added locally in Excel is not real master data
  until saved; saving it creates a combination that then gets planned everywhere.
- **Rolling horizon / lock horizon** - some KFs are locked in the near or frozen past horizon; edits there
  are rejected or ignored. (`planning-area-and-key-figures.md`)

## Reconciliation & freshness
- The Excel planning view holds the data from **when you opened or last refreshed it**. Other planners and
  scheduled jobs may have saved since. **Refresh before Save Data**, or last-write-wins overwrites their work.
- **Actuals lag ERP.** Sales, stock, and orders arrive by scheduled data-integration jobs (often nightly),
  so IBP's actuals and projected stock trail the real S/4HANA/ECC position. Do not treat an IBP quantity as
  the live physical position - that lives in `sap-mm`.
- When IBP and ERP disagree on the same quantity, split by kind: for **on-hand stock and open-order
  quantities, ERP is truth**; for **forward plan figures (consensus demand, projected stock, safety stock),
  IBP is truth**. Never substitute one for the other. Reconcile to ERP for actuals, and check the last
  successful integration run before acting.

## Recovery patterns (what can be undone, and what cannot)
Full change-by-change recovery decision table: `references/versions-scenarios-snapshots.md`.
- **Snapshot** - the one real backup. A snapshot KF taken before an operator/publish lets you copy the
  prior values back. No snapshot = no restore of the overwritten plan.
- **Backup version** - copy the baseline into an alternative version before a risky baseline-writing run;
  restore by copying it back. Same discipline as a snapshot, at version grain.
- **Scenario discard** - a scenario not saved into its version leaves no trace; discard is a clean undo.
  Once *saved to version*, it is part of the version's data and is not separately reversible.
- **Baseline overwrite with no backup** - unrecoverable; re-derive by re-running the source operator (if
  the source is intact) or re-key manually. Treat this as permanent.
- **Release to ERP/execution** - cannot be undone from IBP; correct the created documents in the receiving
  system and re-integrate. Size it before releasing - it is a real commitment, not a plan edit.
- **Structure change / activation** - do not attempt to reverse a planning-area change to fix a planning
  problem; it is an admin/config action with its own data risk.

## Guardrails
- **Read the target version first, every time.** Baseline vs sandbox decides whether a save/operator is
  reversible or destructive. Re-read (refresh) immediately before Save Data on a shared version.
- **Confirm the version selector in the Excel ribbon before every Save Data.** The baseline is the default
  target and Save Data writes it immediately with no confirmation dialog - the single most common way the
  plan of record gets changed by accident.
- **Snapshot first is the always-safe opening move.** Before any baseline write, take a snapshot; it is
  never gated and it is the only thing that makes the write recoverable.
- **Take a snapshot or a backup version before any baseline-writing operator** (copy, S&OP supply, IO,
  statistical forecast). No "before", no safe operator run on the plan of record.
- **Simulate to preview; Save Data only when the number is the plan.** Never report a simulated value as
  saved.
- **Promoting a version into the baseline and releasing supply to ERP are the two hard gates.** Named
  approver, snapshot in place, re-read, and log the reason code. A release creates real execution
  documents; an unbacked baseline overwrite is permanent.
- **A frozen/past period, a locked horizon, and a version-independent actuals KF are walls.** Do not edit
  them to make a planning number work.

## References (load on demand)
- `references/planning-operators-and-jobs.md` - the operator families (copy, statistical forecast, S&OP
  supply heuristic/optimizer, inventory optimization, snapshot, disaggregation, Response order-based run /
  deployment / confirmation) and what each writes, plus application-job scheduling.
- `references/versions-scenarios-snapshots.md` - baseline vs alternative versions, scenarios (simulate /
  save-to-version), snapshots as the backup mechanism, sharing/publishing a version, and recovery.
- `references/planning-area-and-key-figures.md` - the planning-area model, stored vs calculated key figures,
  planning levels, aggregation/disaggregation basis, time profile and lock horizons, master data, and
  data integration (actuals in, plan out).
