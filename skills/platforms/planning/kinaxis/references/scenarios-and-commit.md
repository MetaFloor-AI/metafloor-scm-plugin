# Kinaxis - scenarios, commit, publish, automation

How the scenario sandbox actually works, why commit is one-directional, and where a commit turns into a
real-world release. Read when a task creates, edits, commits or publishes a scenario, or touches an
automation chain. The rule underneath all of it: analysis is free and reversible; commit and publish are not.

## Contents
- The scenario data model (deltas, inheritance)
- Private vs public scenarios
- The baseline (root) scenario
- Commit - merge up, no uncommit
- Publish / release to ERP
- Automation chains and scheduled tasks

## The scenario data model (deltas, inheritance)
- A scenario is a **child of a parent** scenario. It stores only the **differences** from that parent
  (copy-on-write), not a full copy of the data. That is why a scenario is cheap to create and why thousands
  can coexist.
- Because it stores only deltas, a scenario **inherits** everything it did not change from the parent -
  including changes made to the parent **after** the scenario was created. Your what-if therefore sits on a
  moving baseline: a value you never touched can shift under you when the parent changes or a new sync lands.
- The plan recomputes **inside** the scenario as you edit (concurrent/always-on planning). Netting, projected
  on-hand, ATP/CTP and alerts all reflect your scenario's data, not the baseline's, while you work in it.
- Nothing you do in a scenario is visible outside it or to ERP until you commit (up) or publish (out).

## Private vs public scenarios
- **Private** - only you see and edit it. Discarding it is a clean revert; use private scenarios so mistakes
  stay discardable.
- **Public / shared** - other planners can see, edit and build child scenarios on it. Deleting a public
  scenario destroys everyone's uncommitted work in it; committing or editing it affects their analysis. Treat
  a public scenario's data as shared state.

## The baseline (root) scenario
- The root of the tree is the shared operating plan, often named "Enterprise Data" or "Actual". Every planner
  and every downstream automation reads it.
- Editing the baseline directly is **live for everyone immediately** - there is no sandbox between you and the
  shared plan. The safe pattern is always: fork a scenario, work there, commit deliberately.

## Commit - merge up, no uncommit
- **Commit merges a scenario's deltas up into its parent.** If the parent is another working scenario, the
  blast radius is that one scenario. If the parent is the baseline, the change becomes shared reality for
  every planner and every automation that reads the baseline.
- Commit is **one-directional**. There is no clean "uncommit" or rollback. To reverse a bad commit you create
  a new scenario, post the offsetting changes, and commit again - and any automation that already fired off
  the bad commit (a release, a downstream publish) has to be unwound separately in its own system.
- Before committing, verify two freshness facts: (1) the last inbound integration/sync time (is the data
  current vs ERP), and (2) whether the parent changed since you forked (did your baseline move). A commit off
  stale or drifted data promotes a bad plan.

## Publish / release to ERP
- **Publishing/releasing** takes plan output - typically planned orders - and sends it **out** to ERP through
  integration. In ERP those become real purchase requisitions, purchase orders or production orders. This is
  the real-world event: money committed, materials ordered, capacity booked.
- Only **released** orders exist in ERP. **Planned** and **firmed** orders live only in Kinaxis; firming
  protects an order from the planning engine but does not release it.
- Releasing only the orders visible in your current worksheet filter can release a **subset** and miss
  dependent orders, leaving ERP with an unbalanced plan. Confirm the release set is the complete, intended set.
- Recovery after release is an ERP action (cancel the req/PO/production order) with its own trail and
  commitment effects, covered by `sap-mm`. It is not a Kinaxis undo.

## Automation chains and scheduled tasks
- RapidResponse can run **automation chains** / scheduled tasks that commit scenarios and publish/release
  orders on a timer or trigger, with no human in the loop at run time.
- That means a commit you make can feed automation that releases orders downstream automatically - and
  editing, enabling or manually triggering a chain can release many orders at once (for example the whole
  daily planned-order set, not one line).
- Treat running, enabling or editing an automation chain that commits or publishes as a committing-to-
  destructive action: know its scope, gate it, and confirm what it will release before it runs.
