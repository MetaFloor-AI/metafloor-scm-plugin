# Infor EAM work orders and equipment - status logic and the four-level hierarchy

Two things that break naive reasoning: the WO status is not a label (a user code pinned to a **system status**
that runs logic), and the equipment register is a **four-level hierarchy** whose cost and history roll up.
Read when a workflow releases, completes, closes, cancels, or reopens a WO, works a route or a parent/child
WO, or installs / removes / reads the cost of an asset.

## Contents
- The equipment hierarchy (Location / System / Position / Asset)
- Install / remove an asset and what moves with it
- Cost and history roll-up
- The WO status model (user code -> system status)
- What each transition runs
- Route work orders
- WO tasks and hierarchy
- Reopen and correction mechanics

## The equipment hierarchy (Location / System / Position / Asset)
Four equipment types, top to bottom:
- **Location** - a site or area at the top of the tree; maintenance cost rolls up here for a plant view.
- **System** - a functional grouping of positions / assets (e.g. a production line, a utility system).
- **Position** - a **fixed functional slot** in the plant ("Pump P-101 seat", "Conveyor drive 3"). It stays
  put and holds the maintenance program, the PM schedules, and the location. Think of it as the role.
- **Asset** - the **serialized physical unit** that is installed into a position. It carries its own
  maintenance history and can be removed and installed elsewhere. Think of it as the individual.

Data is shared **up** the tree: a WO booked on an asset is also visible at its position, system, and location.
This is the main structural difference from Maximo (asset + location) and SAP PM (functional location +
equipment): Infor EAM makes the **position vs asset** distinction first-class.

## Install / remove an asset and what moves with it
- **Installing** an asset into a position links the unit to the slot; from then on work on the position's
  program is done on that asset, and its cost rolls to the position.
- **Removing** an asset (to a store, to repair, or to another position) detaches the unit; its history travels
  **with the asset**, while the position keeps the slot-level history.
- Removing a position or higher level requires its child positions / equipment be removed first - the tree is
  ordered, so you cannot delete a parent out from under live children.
- Consequence: reading "this asset's history" and "this position's history" are different questions after a
  swap. A rebuilt pump installed into P-101 does not inherit the old pump's failures; the position does.

## Cost and history roll-up
- Work and cost booked to an asset appear at the asset **and** roll up to position, system, and location.
- Never sum an asset with its parent levels as if independent - that double-counts. Read the single level you
  actually mean (asset cost, or the location total), not both added together.
- At **WO close** the actuals roll up the hierarchy and freeze; a wrong equipment link at close mis-attributes
  cost permanently.

## The WO status model (user code -> system status)
- Each site defines its own **status codes**, but every code is bound to a fixed **system status** (its
  **R-Type**). The **system status** is what the engine acts on; the code is display text.
- The lifecycle in system-status terms:
  - **Unfinished** - the draft. Tasks, trades, planned parts, and tools can be added and edited freely;
    nothing is reserved or posted. The only truly reversible state.
  - **Released (R)** - committing. Release **reserves** the WO's stock parts against store balances, makes the
    WO schedulable and printable, and for non-stock / direct parts can **auto-raise a requisition**. Editing
    parts or scope after release is a committing change.
  - **Completed** - the work is physically done but the WO is **still open** for late labour, parts, and cost.
    On a PM-generated WO, completion recalculates a **floating** PM's next due (a fixed PM does not slip).
    Not a lock.
  - **Closed** - historizes the WO: actuals freeze, cost rolls up the equipment hierarchy, and no further
    transaction is accepted. A charge arriving after close is stranded. Terminal in the normal flow. Some WO
    types are configured to **auto-close** on completion or to skip Completed (Released -> Closed), which
    removes the window for late actuals - know the type before assuming a done WO is still open for cost.
- Because codes are configurable, two deployments can name these differently, and a custom code can be mapped
  to the wrong system status. Always resolve the **system status** before acting, and never create or force a
  code whose system status skips reserve / complete / historize logic.

## What each transition runs
| Transition | What it does (beyond the label) |
|---|---|
| create (Unfinished) | draft; nothing reserved. But a "quick" / EM WO type may be **created directly in Released** - check routing |
| -> Released | reserves stock parts; makes schedulable / printable; auto-raises requisitions for non-stock / direct parts |
| -> Completed | marks work done; recalculates a floating PM's next due; updates meters / warranty; WO still open for cost |
| -> Closed | historizes; freezes actuals; rolls cost up the hierarchy; blocks further transactions |
| -> Cancelled | voids; releases reservations back to available; **barred once the WO has actuals** |
| force / custom status | runs whatever the mapped system status dictates - a forced jump can orphan reservations or unposted cost |

Non-costed comments / notes are usually still allowed on a closed WO; the lock is on actuals and cost, not on
annotation.

## Failure coding (captured at completion)
- On a corrective WO, the failure is coded in a three-level hierarchy: **problem** (what was observed) ->
  **cause** (why it failed) -> **remedy** (what was done). The codes are dependent - a cause is valid only
  under its problem, a remedy only under its cause.
- These codes feed reliability analysis (MTBF, MTTR, failure-mode Pareto) and future PM decisions. A missing
  **cause** code makes root-cause analysis impossible; a wrong code skews the metrics and can drive the wrong
  PM change. Capture them at completion, before close, because a closed WO cannot take them.

## Route work orders
- A **route** WO covers many pieces of equipment in one pass (an inspection round, a lubrication loop). The
  PM / route generates child equipment lines (and, per config, child WOs) for each member.
- Completing or closing the route acts on the **whole round**. A fault found on one member still needs its own
  corrective WO.
- Reserving parts for a route reserves for every member - a route can lock a lot of stock at once.

## WO tasks and hierarchy
- A WO carries **tasks / activities**, each with its own planned trades, parts, and tools; a standard WO or a
  PM can generate a multi-task WO in one shot.
- A WO can have child WOs; cost and actuals roll up to the parent, and the parent should not close until its
  children are complete. Book cost to the **correct level** or the per-task / per-asset history is distorted.

## Reopen and correction mechanics
- **Reopening a closed WO is not a status transition** in the normal flow. Some deployments configure a
  re-open path; if it is not configured, the only correction is a **new corrective WO**.
- Historized actuals stay in the record whether or not a reopen is possible; a reopen does not erase them.
- A wrong PM reset (from an early / late completion on a floating PM) is fixed by correcting the PM's
  last-completion / last-meter, but any WO already generated from the shifted schedule remains and must be
  cancelled or worked.
- A forced status jump that skips Released or Completed bypasses the reserve and actuals logic those
  transitions run, leaving orphaned reservations or unposted cost - walk the flow instead.
