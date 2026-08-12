---
name: o9
description: "o9 Solutions (the Digital Brain) - the safe operation of demand, supply, inventory and S&OP/IBP planning on o9's Enterprise Knowledge Graph: measures and dimensions, driver-based planning, IBPL rules, versions and scenarios, what-if simulation, solvers/plugins, and publishing or committing a plan into the baseline and releasing it to execution/ERP. Use when the connected planning system is o9, or the work mentions o9, the Digital Brain, the Enterprise Knowledge Graph / EKG, a measure or dimension, driver-based planning, IBPL, a plan version or baseline / mainline, a scenario or what-if, a solver or plugin (demand forecast, supply, inventory optimization), consensus demand, an active view or planning workbook, aggregation / disaggregation / spreading, or publishing / committing / releasing a plan to ERP."
---

# o9 (the Digital Brain) - operating it safely

o9 is a cloud planning platform built on the **Enterprise Knowledge Graph (EKG)** - a graph model of the
enterprise (items, locations, customers, suppliers, demand, supply) with **measures** hanging off it and
**IBPL rules** that recompute dependent measures as data changes. It plans demand, supply, inventory and
S&OP/IBP; it is not the book of record. o9 is dangerous in the way a graph is dangerous: **an edit
propagates along relationships to measures you never touched, and a plan overwrite is silent with no
document trail.** Nothing here posts to a ledger, but a measure that gets overwritten with no snapshot is
just gone, and once a version is committed to the baseline or released to execution it drives real orders.
Reading, simulating, and what-if in a scenario are free. The damage is in four moves: overwriting stored
measures, committing a version into the baseline (the plan of record), releasing a plan to ERP/execution,
and changing an IBPL rule or dimension (which recomputes the graph for everyone). This skill classifies
those so the harness can gate them, and gives the edge states and the one real recovery lever (snapshots)
that decide whether a mistake is fixable.

## Contents
- When this applies (+ when NOT) · Object & state model · Vocabulary that bites
- Operations: read / write / destructive (the matrix + reclassification rules)
- Gotchas that bite · Edge states · Reconciliation & freshness
- Recovery patterns · Guardrails · Worked example · References

## When this applies
Connected planning system is o9 and the work is demand/supply/inventory/S&OP planning, scenario analysis, or
releasing plan output. When NOT:
- Kinaxis RapidResponse / Maestro planning -> `kinaxis`
- SAP IBP (time-series / Response) planning -> `sap-ibp`
- Blue Yonder / JDA demand & fulfillment planning -> `blueyonder-planning`
- Anaplan connected planning -> `anaplan`
- ERP inventory/procurement postings, goods movements, real stock and PO documents -> `sap-mm`
  (o9 plans; MM executes - releasing an o9 plan lands there)
- Ledger, costing, financial actuals -> `sap-fi`

## Object & state model (reason about the plan's state, not the noun)
Measure and dimension names below (Consensus Demand, Demand Planning Qty, and so on) are **illustrative** -
exact names, grains, and whether a measure is input/computed or version-scoped/shared vary by tenant
configuration. Confirm a measure's type from the tenant's own model before editing it; do not assume the name.
- **Enterprise Knowledge Graph (EKG) / Digital Brain** - the graph model: nodes are dimension members
  (an item, a location, a customer), edges are relationships (item sourced-from location, ships-to customer),
  and measures are stored against grains of the graph. An edit **propagates along the edges** to every
  dependent measure. Reasoning is about what an edit re-derives across the graph, not the single cell.
- **Dimension** - a master-data axis (Item, Location, Customer, Channel, Supplier, Time), each with
  **levels** forming a hierarchy (Item -> Product Family -> Category). Adding a member creates new cells to
  plan; removing one drops its stored measure data. Dimensions are shared master data, not per-planner.
- **Measure** - a value at a grain (Demand Forecast, Consensus Demand, Supply, Projected Inventory, Safety
  Stock). **Input** measures are editable; **computed** measures are derived by an IBPL rule and cannot be
  typed over. A measure is stored/computed at a specific grain; what you see may be aggregated above it.
- **IBPL rule** - o9's rule/expression language defines computed measures and the graph logic that spreads
  and derives values. A rule change re-derives every dependent measure across the graph, for every version
  and planner. This is config, not a planning edit.
- **Version** - a named copy of the plan's measure data. The **baseline / mainline** version is the plan of
  record everyone sees and integration exports; **alternative versions** are sandboxes for simulation.
- **Scenario / what-if** - a simulation layer on top of a version that stores only your deltas. Simulate
  freely, then either discard it (no effect) or **commit/promote** it into the version (a one-way write).
- **Solver / plugin** - the engines that write measures: demand forecast (statistical + ML), supply
  (unconstrained / constrained / optimizer), inventory optimization (MEIO), allocation/deployment. A run
  overwrites its target measure for the whole selected scope. Solvers run interactively or as scheduled jobs.
- **Snapshot** - a frozen copy of a measure at a point in time, kept in a snapshot measure. This is the main
  backup and accuracy-comparison mechanism; with no snapshot there is no "before" to restore.
- **Active View / Planning Workbook** - the configured, editable grid over the graph. Every edit lands in the
  **active version**; which version is active decides what an edit touches.
- **Plan state ladder** - draft edits in a view (unsaved) -> save to a version/scenario -> commit/publish into
  the baseline -> release to execution/ERP. Each arrow is a larger, harder-to-undo commit.
- **System boundary** - o9 = the plan and analytics; ERP = system of record for inventory and orders. They
  sync via integration and drift; an o9 measure can be stale relative to the last sync.

## Vocabulary that bites
- **Enterprise Knowledge Graph (EKG)** - not a set of tables; a graph where an edit ripples along
  relationships. The propagation is the hazard: a change has non-local effects you did not see on the grid.
- **Measure vs dimension** - measures are the editable/computed values; dimensions are the master-data axes
  with levels. You plan by editing measures at a grain; you do not "edit a dimension" casually - that is
  master data.
- **Computed (rule-driven) vs input measure** - you cannot fix a computed measure by typing over it (the
  next recompute or solver overwrites it); change the **input driver** instead. Same trap as IBP calc vs stored.
- **Driver-based planning** - dependent measures derive from **drivers** via IBPL rules. Overwrite a driver
  and every measure downstream of it shifts silently along the graph.
- **IBPL** - o9's rule/expression language. Changing a rule recomputes every dependent measure across the
  graph, for all versions and planners - it can restate committed plans. Admin/config, never a fix for one number.
- **Baseline / mainline version** - not a software version; the live plan of record. Editing or committing
  into it changes what every other planner and every export sees.
- **Scenario / what-if** - a simulation overlay that stores only deltas. Safe to edit; the hazard is
  committing it into the version. Simulating changes nothing shared.
- **Solver / plugin** - the demand/supply/IO engines. A run is a **replace over its scope**, not a merge or
  add: the source clobbers the target measure for every cell in the selection, including planner overrides.
- **Aggregation / disaggregation (spreading)** - editing a measure above its base grain spreads the value
  down to detail by a **spreading basis** (usually another measure). An empty or zero basis spreads evenly or
  nowhere - a silent mis-distribution across the leaf grain. o9's single most common quiet error.
- **Publish / commit** - promoting plan output. The word is used loosely for both promoting a version into
  the baseline **and** releasing to execution; confirm which one is meant - one changes the shared plan, the
  other creates real ERP documents. Both are committing.
- **Consensus demand** - the agreed demand measure that feeds supply and inventory planning. Overwriting it
  changes what every downstream supply and IO run plans to.
- **Version-independent / shared measure** - some measures (actuals, history, many master-style measures) are
  one copy shared by all versions. A "sandbox" edit to one is not sandboxed - it corrupts shared history and
  the forecast seed.

## Operations: read / write / destructive
Classify every operation family by what it does to plan state. Kinds of action, no tool names.

| Class | o9 operation families | Gate | Why |
|---|---|---|---|
| **Read** | open active views / planning workbooks; view measures, KPIs, dashboards, alerts/exceptions; **simulate a what-if in a scenario** or run a solver **into a scenario without committing** (the scenario buffers the write); compare versions/scenarios/snapshots; **take a snapshot** (a protective write to a snapshot measure only - overwrites no source, so it always passes, even on the baseline); display graph/dimension/master data and job logs; export to a local session | always pass | no shared-plan change; read the current baseline and re-read at execute (others save concurrently) |
| **Write (reversible / sandboxed)** | edit measures **inside a scenario or a non-baseline version**; create a version by copy; create a scenario; run a solver/plugin (forecast/supply/IO) whose target is a **non-baseline** version | gate each individually | isolated from the plan of record; undo = discard the scenario or re-copy the sandbox from baseline |
| **Write (committing)** | **save measure edits into the baseline** version; **commit/promote a scenario into its version**; run a copy/forecast/supply/IO solver whose target is the **baseline** (copy forecast -> consensus, run supply, run IO to write safety stock into baseline); edit a **version-independent / actuals** measure; **add/save a valid combination (assortment) or dimension member** (shared master data then planned in every version); schedule a plugin/job that writes the baseline | gate + named human approver | changes the shared plan of record every planner and every export reads; no ledger, but real downstream effect |
| **Destructive / irreversible** | **commit/publish a version into the baseline/mainline** (overwrites the plan of record); a solver/plugin **overwrite of a baseline measure with no snapshot** (the prior values are unrecoverable); **release/publish a plan to execution/ERP** - planned orders, purchase / stock-transfer requisitions, PIRs, or deployment/allocation confirmations to real orders; a **mass data-integration import that overwrites actuals/measures**; **change an IBPL rule/driver or a dimension structure** (recomputes the graph for everyone); **delete a version, scenario, or dimension member** | hard gate + named approver + snapshot/backup first + re-read | no undo in o9; a released plan creates real execution documents; an overwrite with no snapshot destroys the prior plan permanently; a rule/dimension change restates the graph |

**Reclassification rule (read this):** the same overwriting solver (copy, forecast, supply, IO) is
*reversible* when its target is a scenario or non-baseline version and *destructive* when its target is the
**baseline and no snapshot exists**. The engine is identical; the blast radius is not. Always check the
target version and whether a backup was taken before you classify a run. **Snapshot is the exception** - it
writes only to a snapshot measure and overwrites no source, so it is never gated; gate the overwrite you
snapshot *before*, not the snapshot itself.

**Graph-propagation rule (read this):** editing a **driver** measure or an **IBPL rule** is never "one cell."
The change re-derives every dependent measure along the graph, across versions and planners. Treat a driver
overwrite committed to the baseline, and any rule/dimension change, as destructive - the on-screen edit hides
the real blast radius.

**Commit-target rule (read this):** committing a scenario is *reversible* when its target is another
scenario or a non-baseline version, but **committing a scenario into the baseline version is destructive, not
merely committing** - the two rows above apply at once (it promotes to the plan of record AND overwrites it).
Take the snapshot and route the named approver; do not classify it as a plain committing save.

**Scenario-sandbox exception (read this):** the "reversible/sandboxed" class holds only for **version-scoped**
measures inside a scenario. Editing a **version-independent / shared measure** (actuals, history, master-style)
inside a scenario is **committing or destructive, not reversible** - the scenario does not isolate it; the one
shared copy changes for every version. Confirm a measure is version-scoped before treating a scenario edit as safe.

**Scope-breadth rule (read this):** a solver/plugin run has two blast-radius axes - the **target version**
AND the **scope/filter** (which members and periods). An over-broad scope ("all items" when you meant one) on
the baseline is as destructive as the wrong version: it overwrites every cell in scope, including planner
overrides. Classify a run by target version AND scope, and confirm both before executing.

**Default-up rule (read this):** when you cannot tell whether an action is committing or destructive, classify
it at the **stricter** level and gate accordingly. In planning, an under-gated overwrite of shared data is the
expensive mistake; an over-gated one only costs a confirmation.

**"Publish/commit" resolver** - the word is overloaded; resolve it to the operation and gate before acting:

| The button/term says | Actual operation | Gate |
|---|---|---|
| Promote / commit a version into the baseline | Overwrites the plan of record, no undo | destructive - hard gate + named approver + snapshot |
| Publish / release to ERP / execution | Creates real orders, requisitions, PIRs, deployment | destructive - hard gate + named approver + snapshot + re-read |

Operating rules: **simulate is not commit** - a simulated number is not persisted; **work in a
scenario, not the baseline**; read the current baseline and **re-read at execute** because others save
concurrently and last-write-wins; **take a snapshot before any baseline-writing solver**; never commit a
version or release to ERP to hit a plan date without the named approver; change a **driver**, not a computed
measure; a plan is not committed until saved to the version, and not real until released to execution.

## Gotchas that bite (the real set - causal chains)
1. **The graph propagates your edit.** o9 is a knowledge graph: change a driver measure or an IBPL rule and every dependent measure recomputes along the relationships automatically. The blast radius is not the cell you touched - a number you never edited moves. See `references/ekg-measures-dimensions.md`.
2. **The number you want is usually computed, not typed.** Driver-based planning means most measures are derived. Overwriting a computed (rule-driven) measure either fails or is overwritten again on the next recompute/solver run; change the input driver instead.
3. **Editing a measure above its base grain disaggregates it.** Type one number at product-family or region level and o9 spreads it down to item-location by the spreading basis. If the basis measure is empty or zero, it spreads evenly (or lands nowhere) - a silent mis-distribution across dozens of SKUs.
4. **A solver/plugin overwrites the whole target for its scope; it does not merge.** Running the demand forecast into consensus, or the supply solver into the plan, replaces every cell in scope including planner overrides made this cycle. Overrides made after the source was last updated are lost with no warning.
5. **Committing a version into the baseline overwrites the plan of record.** Every planner and every downstream export now reads your version, and downstream automation acts on it. There is no clean uncommit - you correct only by an offsetting commit, and the automation may already have moved.
6. **Overwriting a baseline measure with no snapshot is unrecoverable.** o9 has no transaction-log undo of plan data. If no snapshot or backup version captured the prior values, the pre-overwrite plan cannot be restored - you can only re-derive or re-key it. See `references/versions-scenarios-commit.md`.
7. **Version-independent / shared measures are not sandboxed.** Actuals, history, and many master-style measures are one copy across all versions. "I only changed it in my scenario version" still corrupts shared history and the forecast baseline that reads it.
8. **Releasing/publishing a plan to execution creates real documents you cannot recall from o9.** Planned orders, purchase / stock-transfer requisitions, PIRs to ERP, or deployment/allocation to real orders become downstream commitments. Undo is a correction and re-integration in the receiving system, not an o9 action (see `sap-mm`).
9. **A scenario is safe only until you commit it into the version.** Simulating in a what-if touches nothing shared; **commit/promote** writes the scenario deltas into the version's data - a one-way write, not a preview.
10. **Concurrent writers overwrite each other; last write wins.** o9 does not lock cells like an ERP document. If your view was opened before another planner saved, your save overwrites theirs - and a scheduled plugin can clobber a manual save that landed seconds earlier. Refresh (re-read) immediately before saving a shared version, and check whether a job runs on the same version/scope/period.
11. **An IBPL rule change is global config, not a planning edit.** Changing a rule or expression re-derives every measure that depends on it across versions and planners - it can silently restate committed plans. Never done to fix one number under time pressure.
12. **Adding or removing a dimension member changes what gets planned.** A new item-location combination (assortment) creates new cells to plan; removing one drops its stored measure data. Master-data edits are shared, not local to your version.
13. **The three supply solver modes give different plans.** Unconstrained ignores capacity; constrained/finite respects it by priority; the optimizer minimizes cost and can drop or re-source supply. Running the wrong one into the baseline restates committed supply and can silently unmeet demand the previous run met.
14. **Inventory optimization writes a recommendation, not stock.** The IO/MEIO solver updates recommended safety-stock / target-inventory measures; it moves nothing physical. Treating its output as on-hand, or feeding it to ERP without the supply run that acts on it, over- or under-states availability.
15. **A scheduled plugin/job repeats the overwrite every cycle.** A copy/forecast/supply job with the wrong target version or scope does not misfire once - it re-runs on schedule and quietly corrupts the baseline each cycle until someone notices.
16. **o9 is a plan, not the book of record.** Inventory and order truth live in ERP; an o9 measure can be stale relative to the last integration. Re-read/re-sync before you release, or you release off a stale on-hand.
17. **A statistical/ML forecast run replaces the forecast measure for its whole scope.** Manual forecast overrides in that scope are wiped unless protected by a separate override measure or lock.
18. **Editing past / frozen periods distorts history and accuracy.** Changing actuals or forecast in closed past buckets rewrites the history the ML models learn from and breaks forecast-accuracy comparison against the snapshot of what was actually planned.
19. **A what-if built on a stale or changed baseline commits a bad plan.** A scenario inherits the version it forked from; a later change to that version shifts your what-if under you. Verify the last integration/sync and that the parent is unchanged before committing.
20. **Overwriting consensus demand re-plans everything downstream.** Consensus demand is the demand-to-supply handoff; a copy plugin or a manual save that overwrites it silently changes what the next supply and IO run plan to, propagating into projected stock and safety stock with no error.
21. **A measure's number depends on its unit and grain.** The same measure read in cases vs pallets vs base UoM, or aggregated vs leaf, is a different quantity. Net or compare across units/grains without conversion and the wrong quantity feeds the supply solver, which sizes the wrong orders, which release to ERP as real requisitions - a unit mismatch propagates all the way to a wrong purchase.
22. **A change the view accepted may not have persisted.** o9's permission/edit model can suppress a save on a protected measure or a version you lack rights to - it looks applied on the grid but did not commit. Confirm the write landed (and that you had edit rights), or you plan on a change that is not there.
23. **A solver can complete and still return garbage.** An infeasible supply problem, a non-converged optimizer, or a run over empty inputs can finish "successfully" yet write nulls, zeros, or an implausible plan across its whole scope. Committing that to the baseline propagates the degenerate plan everywhere. Check a solver's output is non-null and within plausible bounds before you commit or release it.

## Edge states & special cases
Each breaks naive "read the measure, write the measure" logic - the rule inline, depth in references.
- **Computed vs input measures** - a computed measure cannot be edited; "setting" it fails or edits an input underneath. Know which is which before writing. (`references/ekg-measures-dimensions.md`)
- **Version-independent / shared measures** - actuals and master-style measures are shared across versions; a sandbox edit is not sandboxed. To tell before editing: check the measure's version-scope property, and treat any measure named or seeded from Actuals / History / master reference as shared until confirmed otherwise.
- **Graph propagation depth** - a driver edit ripples along relationships to dependents; know the dependency chain before editing a driver, or you move measures out of view.
- **Scenario / version branching** - scenarios and versions branch off a parent; a commit's blast radius depends on where it lands (into a scenario = contained; into the baseline = shared with everyone).
- **IBPL rule / dimension change** - global recompute and shared master data; admin/config territory with graph-wide data risk, not a planning edit.
- **Spreading basis empty/zero** - disaggregation lands evenly or nowhere; verify the basis measure has data at the target grain before editing above base.
- **Lock / frozen horizon** - near or past periods can be locked; edits there are rejected or ignored.
- **Solver mode (unconstrained / constrained / optimizer)** - three engines give different supply from the same demand; know which one a run uses before committing its output.
- **Silent permission drop** - o9's role/edit model can accept an edit on the grid yet not persist it (a protected measure, or a version you lack rights to). It looks applied but did not commit - a safety-critical edge, because you then plan on a change that is not there. Confirm the write landed after saving.
- **Integration lag** - inbound ERP data arrives by scheduled jobs, so o9 measures may not reflect ERP truth. Check the last successful integration run timestamp before any baseline write or release, or you commit and release against yesterday's on-hand.
- **Partial / failed solver run** - a run can error out or time out mid-scope, leaving some measures written and others not, so the plan is internally inconsistent. Do not commit a partial result; snapshot, then re-run into the same scope or restore from backup.
- **Orchestration chain cascade** - a scheduled chain (integration -> forecast -> consensus -> supply -> IO -> publish) cascades writes across measures. Re-running one mid-chain step (e.g. supply) without the downstream steps (IO) leaves the plan inconsistent; a chain's blast radius is every step after the one you touched.

## Reconciliation & freshness
- The active view holds the data from **when you opened or last refreshed it**. Other planners and scheduled
  jobs may have saved since. **Refresh before you save a shared version**, or last-write-wins overwrites their work.
- **Actuals lag ERP.** Sales, stock, and orders arrive by scheduled data-integration jobs (often nightly),
  so o9's actuals and projected stock trail the real ERP position. Do not treat an o9 quantity as the live
  physical position - that lives in `sap-mm`.
- **When integration is stale, do not release against it.** If the last successful integration is older than
  the planning cycle (typically more than a day), trigger a manual sync first or hold the release until fresh
  data is confirmed - releasing planned orders off yesterday's on-hand creates or misses real requisitions.
- When o9 and ERP disagree on the same quantity, split by kind: for **on-hand stock and open-order
  quantities, ERP is truth**; for **forward plan figures (consensus demand, projected stock, safety stock),
  o9 is truth**. Never substitute one for the other. Reconcile to ERP for actuals, and check the last
  successful integration run before acting.

## Recovery patterns (what can be undone, and what cannot)
- **Snapshot / backup version** - the one real backup. A snapshot measure (or a baseline copied into an
  alternative version) taken before an overwrite lets you copy the prior values back. No snapshot = no restore.
- **Scenario discard** - a scenario not committed into its version leaves no trace; discard is a clean undo.
  Once committed, the deltas are part of the version's data and are not separately reversible.
- **"Uncommit"** - there is no clean uncommit of a committed version. The playbook for a bad baseline commit:
  (1) snapshot the current (wrong) baseline so you can see the delta; (2) create a scenario from the baseline;
  (3) enter offsetting deltas to restore the intended plan; (4) get the named approver; (5) commit the
  corrected scenario; (6) check whether downstream automation already fired off the bad commit and unwind
  those documents in ERP (`sap-mm`). Act fast - the longer the bad plan sits, the more automation acts on it.
- **Baseline overwrite with no backup** - unrecoverable. First freeze all scheduled baseline-writing jobs so
  nothing overwrites further while you assess, then re-derive by re-running the source solver (if the source
  is intact) or re-key manually. Treat it as permanent.
- **Release to execution / ERP** - cannot be undone from o9; identify exactly which orders released
  (including dependents), correct the created documents in the receiving system under `sap-mm`
  gating, stop any automation that would re-release next run, and fix the driving plan data so the next run
  does not re-release the error. Act on the time tiers - a still-planned requisition cancels cheaply; a
  released PO already sent needs vendor communication.
- **IBPL rule / dimension change** - do not reverse a rule or structure change to fix a planning number; it
  is config with its own graph-wide data risk. Correct the plan data, not the model.

| What happened | Recoverable? | How |
|---|---|---|
| Edit/solve into a scenario, not committed | Yes, clean | Discard the scenario - no trace |
| Edit/solve into an alternative version | Yes | Discard or re-copy the version from baseline |
| Committed a scenario into an alternative version | Yes, contained | Discard/re-copy the version, or offsetting commit |
| Committed a scenario into the baseline | Only by offsetting commit (destructive) | New scenario, corrected deltas, named approver, commit again |
| Overwrote a baseline measure, snapshot taken | Yes | Copy the prior values back from the snapshot/backup |
| Overwrote a baseline measure, no snapshot | No | Re-run the source solver if source intact, else re-key - permanent |
| Released a plan to ERP | Not in o9 | Cancel/correct the documents in ERP (`sap-mm`), stop re-release, fix plan data |
| Changed an IBPL rule / dimension | Do not reverse the change | Fix the plan data, not the model - graph-wide risk |

## Guardrails
- Do the work in a **scenario or a non-baseline version**, not the baseline; keep mistakes discardable.
- **Read the target version first, every time.** Baseline vs sandbox decides whether a save or solver run is
  reversible or destructive. Re-read (refresh) immediately before saving a shared version.
- **Confirm which version is active** in the workbook/view before every save - the baseline is often the
  default target and a save writes it immediately.
- **Snapshot (or back up the version) before any baseline-writing solver** (copy, forecast, supply, IO). No
  "before", no safe run on the plan of record; the snapshot is the only thing that makes it recoverable.
  Verify the baseline is in a known-good state first - a snapshot of already-corrupt data just preserves the
  corruption - and confirm a snapshot measure exists and is configured, or the snapshot silently fails and you
  proceed thinking you have a backup you do not.
- **Confirm the target version AND the scope/filter of every solver run before executing.** Scope is a
  separate blast-radius axis from the version - a run set to "all items" when you meant one item clobbers
  every cell in scope, including planner overrides. An over-broad scope is as dangerous as the wrong version.
- **Before saving to a shared version, check whether a scheduled plugin/job writes the same version, scope,
  and period.** A job that lands seconds after your save overwrites it silently (and vice versa).
- **Simulate to preview; commit only when the number is the plan.** Never report a simulated value as committed.
- Change a **driver, not a computed measure**; never edit an IBPL rule or a dimension structure to force one
  number - it recomputes the graph for everyone.
- **Committing a version into the baseline and releasing a plan to execution are the two hard gates.** Named
  approver, snapshot in place, re-read, and log the reason. A release creates real execution documents; an
  unbacked baseline overwrite is permanent.
- A frozen/past period, a locked horizon, a version-independent actuals measure, and an IBPL rule are walls -
  do not edit them to make a planning number work.
- **Confirm the write landed** after saving a shared version - the grid can accept an edit that permissions
  silently dropped. Do not assume a change committed because the view showed it.

## Worked example (a safe cycle, and where undo stops being free)
A planner must raise demand for 500 units of Item A at DC-East for a new customer program. Safe path: (1)
create a **scenario** (or alternative version) off the baseline; (2) raise the input driver **Demand Planning
Qty** by 500 at the **Item x Location x Month** grain (Item A, DC-East, next month) - not the computed
Consensus Demand measure - and first confirm the spreading basis (e.g. Historical Share) is non-zero at that
grain so the 500 disaggregates to the weekly leaf correctly; the graph recomputes Consensus Demand, Projected
Inventory, Safety Stock and Supply **inside the scenario only**; (3) verify freshness - last ERP integration
current AND the parent version unchanged since the fork; (4) **take a snapshot** of the measures the run will
overwrite (Consensus Demand, Supply, Safety Stock); (5) after human approval, **commit** the scenario into the
baseline (destructive per the commit-target rule - shared for every planner); (6) run the **constrained supply
solver** into the baseline and **release** the ~12 resulting planned orders to ERP, confirming the release set
(with dependents) is complete. Failure branches: if the spreading basis is zero at step 2, the 500 disaggregates evenly across weeks - edit
at the base grain instead; if the parent version changed since the fork at step 3, re-fork the scenario so
you are not committing onto a moved baseline; if step 6's integration timestamp is stale, sync or hold rather
than release against old on-hand. Undo cost climbs at each step: discard the scenario at step 2 and nothing
shared moved; after step 5 you can only correct with an offsetting commit; after step 6 the orders are real
ERP requisitions and unwinding is an ERP cancel under `sap-mm`. This is why the work happens in a
scenario, a snapshot is taken before the baseline write, and freshness is checked before the commit.

## References (load on demand)
- `references/ekg-measures-dimensions.md` - the EKG/Digital Brain data model: graph nodes and edges,
  dimensions and levels/hierarchies, measures (input vs computed, storage grain), aggregation/disaggregation
  and the spreading basis, IBPL rules and graph propagation, version-independent measures.
- `references/versions-scenarios-commit.md` - baseline/mainline vs alternative versions, scenarios
  (simulate vs commit), commit/publish semantics and no-uncommit, snapshots and backup versions as the
  recovery mechanism, and release to execution/ERP.
- `references/solvers-and-plugins.md` - the solver/plugin families (demand forecast statistical/ML, supply
  unconstrained/constrained/optimizer, inventory optimization/MEIO, allocation/deployment) and what each
  writes, plus scheduled jobs and orchestration.
