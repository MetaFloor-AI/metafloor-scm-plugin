# Blue Yonder - scenarios, publish, planning runs, release, automation

How the scenario sandbox works, why the two publishes differ, what a regeneration can wipe, and where a plan
turns into real orders. Read when a task creates/edits/publishes a scenario, runs the solver, releases planned
orders or RecShips, or touches a scheduled batch. The rule underneath all of it: analysis is free and reversible;
publish and release are not.

## Contents
- The scenario sandbox (and nesting)
- The published / baseline plan
- The two publishes (demand->supply, scenario->baseline)
- Planning-run modes: regeneration vs net-change
- Time fences / frozen zone
- Deployment and Recommended Shipments
- Release to ERP / execution
- Snapshots
- Scheduled batch and automation

## The scenario sandbox (and nesting)
- A scenario is a working copy of the plan you edit privately. The solver recomputes **inside** the scenario as
  you change forecasts, parameters or orders, so projected on-hand, planned orders and RecShips all reflect the
  scenario's data while you work in it.
- Nothing in a scenario is visible outside it, to other planners, or to ERP until you publish it.
- Scenarios can **nest**: scenario -> scenario -> baseline. A publish's blast radius depends on where it lands -
  into a child scenario it is contained one level up; into the baseline it is shared with every planner and every
  downstream run. Know the parent and the depth before you publish.
- **Private** scenarios are yours to edit and discard freely (a clean revert). **Shared** scenarios others build
  on; deleting one destroys their uncommitted work, and publishing it affects their analysis.

## The published / baseline plan
- The baseline is the shared operating plan every planner, ESP, Deployment and downstream execution consume.
- Editing the baseline directly, or running the solver on it, is **live for everyone immediately** - there is no
  sandbox between you and the shared plan. The safe pattern is always: fork a scenario, work there, publish deliberately.

## The two publishes (demand->supply, scenario->baseline)
Blue Yonder is a suite, so "publish" is overloaded. Both are committing; they differ in what they move.
- **Publish demand to supply** - hands the consensus forecast from Demand to ESP. On the next supply run the
  whole network re-plans off that forecast: netting, planned orders, deployment and safety-stock replenishment all
  shift. The blast radius is every SKUL the forecast touches. A bad forecast published here propagates to all of supply.
- **Publish / commit a scenario to the baseline** - merges the scenario's plan changes (overrides, parameters,
  firmed orders, solver output) into the shared plan. Every planner and automation now reads your change.
- There is no clean **unpublish** for either. You correct a bad publish by making offsetting changes in a new
  scenario and publishing again - and any automation that already acted on the bad plan is unwound separately.
- Before either publish, verify two freshness facts: (1) the last inbound integration/source-sync time (is the
  data current vs ERP), and (2) whether the parent/baseline moved since you forked (a concurrent planner or a
  scheduled batch). A publish off stale or drifted data promotes a bad plan.

## Planning-run modes: regeneration vs net-change
- **Net change (NCR)** - an incremental run that updates only what changed since the last run. Lighter, faster,
  and it preserves the rest of the plan. Prefer it for incremental work.
- **Regeneration (full regen)** - rebuilds the entire plan from scratch. It **re-derives every planned order
  outside a time fence** and discards ad-hoc changes that are not protected. Firm planned orders and orders inside
  a time fence survive; un-firmed manual overrides can be blown away.
- A run on the **live baseline** (either mode) recomputes the shared numbers in place - that is effectively a
  publish. Run the solver in a scenario, review the delta, then publish deliberately.
- Before a regen, know what it will discard: which manual work is firmed/fenced (survives) vs loose (lost).

## Time fences / frozen zone
- A **time fence** is a horizon inside which the engine will not auto-create or auto-change orders. The **demand
  time fence (DTF)** freezes the forecast near term (so the near horizon uses actual orders/sensing, not the
  statistical forecast); the **planning time fence (PTF)** freezes supply orders (the engine will not add or move
  planned orders inside it).
- Inside a fence the plan is meant to be stable. A naive edit there is ignored, or the next run overrides it,
  unless you make it a **firm** order. Do not assume a near-term change stuck just because the grid accepted it.
- A regen respects firm orders and time fences and re-derives everything outside them.

## Deployment and Recommended Shipments
- **Deployment** hardens near-term planned orders into **Recommended Shipments (RecShips)** - stock transfer
  orders that move real inventory between nodes (DC -> store, plant -> DC).
- A RecShip is not a paper step: releasing deployment creates STOs that ship physical stock. Size the deployment
  set (which SKULs, which lanes, quantity) before releasing.

## Release to ERP / execution
- **Releasing** takes plan output - planned orders and RecShips - and sends it **out** to ERP/execution through
  integration. There they become real requisitions, POs, production orders or STOs. This is the real-world event:
  money committed, materials ordered, stock moved.
- Only **released** orders exist in ERP. **Planned** and **firm** orders live only in Blue Yonder; firming
  protects an order from the engine but does not release it.
- Releasing only the orders visible in your current filter can release a **subset**, miss dependent supply and
  break **pegging**, leaving ERP with an unbalanced plan. Release with dependents; confirm the release set is complete.
- Recovery after release is an ERP action (cancel the req/PO/production order, or the STO if not yet shipped) with
  its own trail and commitment effects, covered by `sap-mm`. It is not a Blue Yonder undo.

## Snapshots
- A **snapshot** is a frozen, read-only copy of measures at a point in time. It powers **waterfall / lag /
  bias / MAPE** forecast-accuracy comparisons (this week's forecast vs the forecast made N weeks ago vs actuals).
- A snapshot is not the live plan. Reading a snapshot value as current plans on numbers that have since moved.
- **Reset / restore of the baseline from a snapshot overwrites the current live plan** - it replaces every
  planner's plan with the snapshot. That is destructive, not a safe rollback; gate it and name an approver.
- **Deleting a snapshot** breaks the accuracy history that depends on it; do not delete a shared snapshot.

## Scheduled batch and automation
- Blue Yonder runs **scheduled batch** jobs (nightly regen, demand publish, deployment, integration to ERP) with
  no human in the loop at run time.
- A publish you make can feed a batch that releases orders downstream automatically - and enabling, editing or
  manually triggering a job can release **many orders at once** (a whole planned-order set, not one line).
- Treat running, enabling or editing a batch/automation that publishes or releases as a committing-to-destructive
  action: know its scope, gate it, and confirm what it will release before it runs. A publish across an active
  batch window can also mix pre- and post-run numbers - publish outside the window or re-read after it completes.
