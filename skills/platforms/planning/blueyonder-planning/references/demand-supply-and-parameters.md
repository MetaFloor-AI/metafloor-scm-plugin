# Blue Yonder - demand, supply (ESP), inventory, and why parameters ripple

Why a forecast is only as trustworthy as the stage it is in, how ESP turns it into a constrained supply plan, and
why a single parameter change re-plans the whole network. Read when a task builds or publishes a forecast, reasons
about constrained vs unconstrained supply, sets a safety-stock/service-level target, or changes sourcing.

## Contents
- The demand build (statistical -> consensus -> sensing)
- ESP: constrained vs unconstrained supply
- Netting and pegging
- Multi-echelon Inventory Optimization (safety stock, service level)
- Sourcing / BOD
- Measures / series (input vs calculated)
- Why a parameter change ripples network-wide
- The freshness rule

## The demand build (statistical -> consensus -> sensing)
- **Statistical / ML baseline (Cognitive Demand)** - the engine's forecast from history and causals. A starting
  point, not the agreed number.
- **Planner overrides** - manual adjustments layered on the baseline. An override that erases a real spike or
  hides a shortage misleads everything downstream; flag it, do not smooth it.
- **Consensus forecast** - the agreed demand number after collaboration/S&OP. This is what gets published to supply.
- **Demand sensing (Demand Edge)** - short-horizon ML that reads recent signals (orders, POS, shipments) and can
  override the baseline near term. The near-term sensed number and the statistical baseline can diverge, so know
  which one owns which horizon before you reason about near-term demand.
- Each stage is a different level of commitment: a baseline is cheap to change; publishing the consensus to supply is not.

## ESP: constrained vs unconstrained supply
- **Enterprise Supply Planning (ESP)** turns the published demand into a supply plan (a Master Plan, MPS + DRP)
  and generates planned orders across the network.
- **Unconstrained plan** - ignores capacity, material and lead-time limits; it shows what you would need in a
  perfect world. Aspirational.
- **Constrained plan** - respects capacity, supplier capability, material availability and lead times; it shows
  what you can actually build/ship. The two can differ materially.
- Reason and release off the **constrained** plan. Releasing off the unconstrained plan promises what you cannot make.

## Netting and pegging
- **Netting** - ESP nets demand against supply (on-hand + in-transit + planned receipts) to compute projected
  on-hand and shortages. Firm and released supply is protected; planned supply is re-derived each run.
- **Pegging** - the link from a specific supply order to the demand it covers. Releasing only a filtered subset of
  orders can break pegging and leave dependent supply behind, so release with dependents and confirm the set is complete.

## Multi-echelon Inventory Optimization (safety stock, service level)
- **Inventory Optimization (IO / MEIO)** sets **safety-stock targets** across echelons to hit a **service level**,
  balancing stock against variability and lead time. The target is a number the plan aims for, not a physical count.
- A safety-stock or service-level change is not a local edit: it changes the replenishment the next ESP run
  generates at every SKUL it touches. Raising service level network-wide can add planned orders everywhere at once.

## Sourcing / BOD
- **Sourcing rules / Bill of Distribution (BOD)** define the network routing - which node or vendor supplies which
  demand, and the path stock takes across echelons.
- Changing a sourcing rule re-plans coverage: commit it and real orders re-route to a different plant, DC or
  supplier on the next run. It is a silent change to the physical supply path, not a display tweak.

## Measures / series (input vs calculated)
- The planning grid is built of **measures** (also called series). **Input measures** - forecast, overrides,
  safety-stock target, lead time, lot size, sourcing - are editable and drive the plan.
- **Calculated measures** - projected on-hand, netting, planned orders, RecShips, accuracy - are read-only outputs
  that recompute from the inputs. You never type over a calculated measure; you change the driving input and re-plan.
- Editing the wrong measure either does nothing (it is calculated) or edits the wrong driver - confirm the measure
  is an input, and confirm the SKUL, before you write.

## Why a parameter change ripples network-wide
- Safety stock, service level, lead time, lot size, min/max and sourcing all feed the **next** solver run. They do
  not change one number in place; they change what the engine computes for every SKUL that parameter touches.
- So a change made to force a single line's answer re-plans the whole network on the next run - extra planned
  orders, shifted deployment, different replenishment. Make the change in a scenario, run it, quantify the delta
  across SKULs and periods, and gate the publish. Never twist a parameter to force one number.

## The freshness rule
Two staleness axes decide whether a publish or release is safe: freshness vs **ERP/source** (last inbound sync)
and freshness vs the plan's own state (a scenario inheriting a moved parent, or a baseline shifted by a scheduled
batch). Check both before you publish or release - the plan is correct math on whatever data is loaded, and stale
data makes correct math produce the wrong answer.
