# Manhattan Active TM - the unified platform, object model, and appointments

Read when a workflow reasons about how TM shares data with the Manhattan Active WM/Omni/Yard siblings, the
order/shipment/load/mode model, dock appointment scheduling, or the differences on the legacy SCALE/TLM line.

## Contents
- The unified Active platform (shared, not integrated)
- The order -> shipment -> load -> leg model
- Modes and how each behaves
- Dock appointment scheduling (live vs drop)
- Yard / WM reconciliation
- Legacy SCALE / TLM differences

## The unified Active platform (shared, not integrated)
- Manhattan Active TM is one app of the **Manhattan Active Supply Chain** platform (cloud microservices). It
  shares a **live common data foundation** with Active WM (warehouse), Active Omni (OMS/order management), and
  Active Yard. It is **not** integrated to them by nightly interface - the order, inventory, and ship-confirm
  data are the *same* data.
- Consequences that bite:
  - An upstream **Omni order change** (new line, quantity change, cancel) is true in TM immediately - a plan
    built on a stale snapshot mis-consolidates or tenders freight that changed.
  - A warehouse **ship confirm** (a WM operation) also closes the TM transportation document / triggers the
    manifest/BOL for that shipment - the goods issue and the transportation close are one event. Treat ship
    confirm as committing the TM shipment even though the pick/pack mechanics belong to `manhattan-wms`.
  - A **short/allocation change in WM** flows into the freight - a shipment can shrink or split under a load
    already being planned.
- Rule: on execute, **re-read the shared order/inventory state**, not the plan snapshot; it moves under you.
- Boundary: even though the data is shared, **operations stay in their app's skill** - waves/picks/LPNs ->
  `manhattan-wms`; order promising/allocation-to-order -> `manhattan-oms`; this skill owns
  the transportation planning, tendering, booking, and settlement operations only.

## The order -> shipment -> load -> leg model
- **Order (transportation order)** - the demand to move goods, from Omni/host. A request, not a commitment.
- **Shipment** - the planned move built from order lines (origin -> destination, mode, service). Statuses:
  planned/available -> tendered -> booked/confirmed -> in transit -> delivered -> closed.
- **Load** - the physical carrier movement: one or more shipments consolidated onto equipment across a route
  of **stops**. Load building/optimization assigns carrier, mode, equipment, cost.
- **Leg / movement** - a segment of a multi-leg move (intermodal, pool point). Carrier, mode, tender, and cost
  can be per leg - "the carrier" on a multi-leg load is per leg, not per load.

## Modes and how each behaves
| Mode | How it plans/commits |
|---|---|
| **TL (truckload)** | optimize -> tender down the routing guide / spot; commit at accept |
| **LTL** | rate-shop across LTL carriers; tender or direct-award; class/weight breaks matter |
| **Parcel** | rate-shop least-cost service; commit at **manifest close** (label + transmit + bill) |
| **Intermodal / rail** | plan + **book** the ramp/equipment; booking commits the allocation |
| **Ocean / air** | **book** capacity against a sailing/flight ahead of cargo; cancel forfeits the slot |

## Dock appointment scheduling (live vs drop)
- An **appointment** reserves a dock/delivery slot and a resource at a facility for a load's pickup/delivery.
  It is a reversible write *before* the load is committed.
- **Live vs drop**: a **live** appointment holds the carrier while the trailer is loaded/unloaded; a **drop**
  leaves the trailer for later handling. A live/drop mistake mis-plans the yard and can cause **detention** on
  arrival (the carrier waits and bills for it).
- Changing or cancelling an appointment after the load is tendered/committed can conflict with the carrier's
  plan - coordinate, do not silently move it.

## Yard / WM reconciliation
- Appointments and load arrivals/departures reconcile with **Active Yard** (gate, yard moves) and with WM
  receiving/shipping on the same platform. A TM appointment change moves the yard plan; a yard check-in updates
  the load's execution status here.
- Because these are one platform, do not treat a yard/WM event as a separate system to be integrated - it is
  live TM state.

## Legacy SCALE / TLM differences
- On the older on-prem line (**Manhattan SCALE TMS / Transportation Lifecycle Management (TLM) / Manhattan
  Carrier**), planning and integration are more **batch-oriented** and the order/inventory data is
  **interfaced** from the host, not unified.
- What specifically changes vs the Active platform:
  - **Data staleness window is wider** - orders/inventory arrive on the host feed's batch cadence, so re-read
    against that cadence (hours), not the seconds-fresh assumption of the unified platform.
  - **Ship confirm does not auto-close the TM document** - the goods issue and the transportation
    manifest/settlement are separate steps interfaced between systems, not one event; do not assume a warehouse
    ship confirm closed the transportation side.
  - **Re-plan is batch, not continuous** - an upstream change does not live-mutate an in-flight plan; it lands
    on the next interface cycle.
- The commit classifications (tender/booking/pay are committing; cancel of a committed load is destructive)
  still hold - only the freshness/coupling behavior above is an Active-platform property.
