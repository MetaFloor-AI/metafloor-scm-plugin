# o9 - solvers and plugins (what each writes)

The engines that overwrite measures in o9, and how their blast radius depends on the target version and the
scope. Read when a task runs or schedules a forecast, supply, inventory, or allocation solver, or reasons
about what a plugin writes.

## Contents
- The plugin model
- Demand forecast (statistical + ML)
- Supply solver (unconstrained / constrained / optimizer)
- Inventory optimization (MEIO)
- Allocation / deployment
- Scheduled jobs and orchestration
- Gating summary

## The plugin model
o9 runs planning logic as **solvers / plugins** over the graph. A run reads input measures for a **selected
scope** (a set of dimension members and periods) and **overwrites its target output measure** for that whole
scope. A solver run is a **replace, not a merge**: the output clobbers the target measure for every cell in
scope, including planner overrides made this cycle. Two controls set the blast radius: the **target version**
(baseline vs sandbox) and the **scope/filter** (which members and periods). Check both before any run.

## Demand forecast (statistical + ML)
- Generates a statistical/ML forecast measure from history and drivers (promotions, price, events).
- Overwrites the forecast measure across the selected products/periods. Manual forecast overrides in that
  scope are wiped unless protected by a separate override measure or lock.
- Editing past/frozen periods before a run changes the history the model learns from - it re-shapes the
  forecast and breaks accuracy comparison against the snapshot of what was planned.

## Supply solver (unconstrained / constrained / optimizer)
Three modes give different plans from the same demand - know which one a run uses before committing its output:
- **Unconstrained** - ignores capacity/material limits; shows demand-driven requirements. Good for gross need,
  not for what is achievable.
- **Constrained / finite** - respects capacity, material and lead-time limits by priority rules; can leave
  demand unmet where capacity is short.
- **Optimizer** - cost-based; minimizes total cost and can drop, defer, or re-source supply in ways a
  heuristic would not. Different objective, different plan.
Running the wrong mode into the baseline restates the committed supply plan and can silently unmeet demand a
prior run met.

## Inventory optimization (MEIO)
- Multi-echelon inventory optimization recommends **safety-stock / target-inventory** measures across the
  network.
- It writes a **recommendation, not stock** - it moves nothing physical. Treating its output as on-hand, or
  releasing it to ERP without the supply run that acts on it, over- or under-states availability.

## Allocation / deployment
- Allocates constrained supply to demand (fair-share, priority) and deploys stock across the network.
- A deployment/allocation released to execution binds toward real orders and customer commitments; re-running
  or over-allocating reshuffles who gets product and can de-commit a promise already communicated.

## Scheduled jobs and orchestration
- Solvers run interactively or as **scheduled jobs** in an orchestration chain (integration -> forecast ->
  consensus -> supply -> IO -> publish).
- A job writes to the **version it targets** on its schedule. A job with the wrong target version or scope
  does not misfire once - it **re-runs every cycle**, corrupting the baseline each time until caught.
- A scheduled publish/release can push orders to ERP with no further human step. Know what a chain sets in
  motion before enabling or triggering it.

## Gating summary
| Run | Target = scenario / alt version | Target = baseline |
|---|---|---|
| Forecast / copy / supply / IO | Write (reversible) - discard to undo | Write (committing); **destructive if no snapshot taken** |
| Allocation / deployment then release to ERP | Reversible while in o9 | Destructive - creates/updates real ERP orders |
| Scheduled job writing the baseline | n/a | Committing each cycle; a bad template corrupts the plan repeatedly |

Before any baseline-targeted run: confirm the target version and scope, take a snapshot/backup, get the named
approver, and re-read the driving data (others save concurrently; ERP drifts).
