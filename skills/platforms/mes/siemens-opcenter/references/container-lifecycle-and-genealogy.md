# Opcenter Execution - container lifecycle, WIP moves, genealogy

How a container moves through a routing, what each move posts, and how genealogy is built and branched. Read
when a workflow tracks a container in/out of a step, backflushes or consumes material, splits/merges, reworks,
or completes an order. Camstar lineage (EX Discrete / Semiconductor / Electronics / Medical Device) uses the
container/spec model below; EX Process/Pharma runs the same WIP+consumption logic under an order/batch-record shell.

## Contents
- Container states and what changes them
- The Track In / Track Out state machine
- Backflush vs explicit consumption
- Genealogy / as-built and how it branches
- Split / merge
- Rework and re-entrant routing
- Yield
- The spec / effectivity model
- Completion and the ERP goods-receipt hand-off

## Container states and what changes them
- **Active / In-Process** - on the routing at a step; either waiting or Tracked In. The normal working state.
- **On Hold** - a hold stopped movement; step/resource state is preserved. Released back to Active.
- **Complete** - reached the end of the routing; finished quantity posted. Usually triggers the ERP receipt.
- **Scrapped** - quantity removed from WIP as a loss; leaves the order yield. Unscrap is limited.
- **Split / Merged** - the container was divided into children or consumed into another; its quantity/history
  moved. The parent may be closed after a full split.
- **Terminated / Cancelled** - the container was ended with WIP still on it; a destructive close, not a complete.

## The Track In / Track Out state machine
Per step, a container moves: **not started -> Tracked In -> Tracked Out**.
- **Track In (Move In)** - starts the operation, claims the resource, marks the container in-process at the
  step. Posts no completion and consumes no material by itself. Reversible: cancel / undo move-in.
- **Track Out (Move Out / Move Std)** - completes the operation. In one transaction it: posts step progress,
  **backflushes** the step BOM, records yield (good / scrap / rework at the step), applies any required
  sign-off, and advances the container to the next step. This is the committing move.
- A **combined move** (move-in and move-out together, "Move Std") does both at once - still a Track Out commit.
- Reversing a Track Out is a **counter-transaction** (reverse/undo move): it re-credits the backflush but does
  not un-advance a later step, and both entries persist. Only clean while the container has not moved past.

## Backflush vs explicit consumption
- **Backflush** - the default: at Track Out the system consumes the step BOM at **standard** quantities from
  the designated component location, with no manual pick. Fast, but blind to actual usage - if the operator
  used a different quantity, on-hand and genealogy diverge from reality until corrected.
- **Explicit consume / assemble** - the operator names the specific component container (lot/serial) consumed
  or assembled onto the parent. Slower, but it captures true as-built and true quantity. Serialized and
  regulated builds use explicit consumption so genealogy is exact.
- **Short stock** - if the component container lacks quantity, Track Out is blocked or drives negative
  inventory per config. Either the line stalls or inventory is corrupted - check component availability before moving.

## Genealogy / as-built and how it branches
- The **as-built** record ties each finished/child unit to the component lots/serials, equipment, operator, and
  parameters that made it. It is **append-only and permanent** - the basis of forward and backward traceability
  and recall scoping.
- A **wrong association** (wrong lot backflushed or assembled) mis-scopes a later recall. You cannot rewrite the
  history; you append a correcting transaction, and the original association remains in the trail.
- Backflush writes genealogy from the standard BOM and the component location; explicit consumption writes it
  from the named container. The two can disagree if the standard BOM is stale.

## Split / merge
- **Split** - divides a container into child containers (e.g. 500 -> 300 + 200). Children inherit the parent's
  genealogy and current step; quantity is reapportioned. Used to route part of a lot differently (rework a subset).
- **Merge** - combines containers into one; genealogies join, so the merged container carries all parents'
  as-built. Legitimate only when the material truly commingles.
- A mistaken split/merge corrupts traceability - the wrong units then appear to contain the wrong component
  lots. Reverse only if no further move happened on the children/merged container; after a move, correct forward.

## Rework and re-entrant routing
- **Rework / repair route** - a container leaves the main flow to a rework route and re-enters at a defined
  step. The rework pass **re-consumes** material and **re-collects** data; it adds to consumption, genealogy,
  and cycle time rather than replacing the first pass.
- **Re-entrant routing** (semiconductor) - the main flow legitimately visits the same step on multiple passes
  (e.g. lithography layers). "At step N" is ambiguous without the **pass / loop count**; per-pass data
  collection and yield must be kept distinct, not conflated across passes.

## Yield
Yield = good quantity out vs quantity in. Scrap and reject at a step cut it; rework recovers some at added cost.
Order completion posts the finished good quantity, which is the input quantity minus cumulative scrap/loss.

## The spec / effectivity model
- Product, workflow (routing), step, resource, BOM, and data-collection are all **specs** with **revisions and
  effectivity dates**. A container is governed by the spec effective for it.
- Editing a spec **before it is effective** is a reversible draft. Editing an **effective** spec is a fleet
  change: every governed container picks up the new behavior at its next step - a re-route or re-consumption
  applied broadly, normally under change control. To "revert", create a corrected revision going forward;
  containers that already moved carry the version they ran on.

## Completion and the ERP goods-receipt hand-off
Tracking out the last step **completes** the container: the finished quantity posts, and Opcenter typically
signals ERP (`sap-mm`) to book the **goods receipt** for the finished good and reconcile the
consumed components. From that point the finished stock and consumption live in ERP inventory too - completing
is a committing hand-off across the seam, not an internal status change. ERP on-hand then lags the MES WIP
truth until the next sync.
