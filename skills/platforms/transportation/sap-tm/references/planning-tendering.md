# SAP TM - planning, carrier selection, tendering

How freight goes from a demand to a committed carrier. Read when a task builds freight units, runs the VSR
optimizer, ranks carriers, or tenders/subcontracts a freight order. The commit point is the carrier
confirmation, not the plan.

## Contents
- Freight unit building (FUB / FUBR)
- The VSR optimizer and the Transportation Cockpit
- Carrier selection - what ranks the carriers
- Tendering methods (peer-to-peer / broadcast / open)
- Subcontracting, statuses, and fixing

## Freight unit building (FUB / FUBR)
- A **Freight Unit (FU)** is the smallest transportation planning unit - the goods that must move together.
- The **Freight Unit Building Rule (FUBR)** decides how an incoming requirement (OTR/DTR) or forwarding order
  is split and grouped into FUs (by criteria like ship-to, incompatibility, or quantity/weight breaks).
- Building or re-building FUs is reversible planning - **until** an FU lands on a subcontracted freight order.
- Hazard: re-running FUB or changing the FUBR **re-cuts the freight**. FUs already planned onto orders can be
  unbuilt/rebuilt, stranding existing planning. Re-cut deliberately, not as a reflex.

## The VSR optimizer and the Transportation Cockpit
- The **Transportation Cockpit** is the planning workbench (Fiori / NWBC POWL). A planner selects freight
  units and either plans by hand or runs the **VSR optimizer** (Vehicle Scheduling and Routing).
- The optimizer builds **freight orders / bookings**: it assigns vehicle resources, sequences stops, respects
  capacity, driving-time/time-window and **incompatibility** constraints, and can pre-select a low-cost
  carrier from the rates. What it sees is driven by the **selection + planning profile** - a wrong profile
  plans against the wrong freight or constraints.
- The optimizer **commits nothing**. It produces a plan (orders + a proposed carrier). The commitment is the
  subcontracting/confirm step later.
- A **background optimizer run** does the same thing unattended - it can build orders on a schedule. Treat any
  automated run whose downstream effect subcontracts/tenders as a committing actor and gate it.

## Carrier selection - what ranks the carriers
Carrier selection produces a **ranked list** for a freight order using, together:
- **Cost** - the calculated charge per candidate carrier (from their freight agreement).
- **Carrier priority** - a master-data preference.
- **Business shares / transportation allocations** - contracted volume splits and lane allocations (e.g. give
  carrier A 60% of a lane). Hand-picking a carrier bypasses these.
- **Incompatibilities** - hard constraints (hazmat handling, equipment type, embargoed lane, carrier-product
  restriction). A carrier that fails an incompatibility must not be selected.

Rule: run selection and let the strategy rank. Overriding to hand-pick a carrier to "just get it moving"
silently violates the allocations and incompatibilities that exist on purpose - a sourcing/compliance move,
not a convenience.

## Tendering methods (peer-to-peer / broadcast / open)
Tendering offers a freight order to a carrier and asks it to accept. The offer goes **out of the building via
PPF** (Post Processing Framework) as email / EDI / a carrier-portal message the moment it fires - it is
externally visible even if you meant to stage it. Three methods, each with a different award behavior:

| Method | How it awards | The hazard |
|---|---|---|
| **Peer-to-peer (direct)** | offered down the ranked list **one carrier at a time**; a rejection or response-timeout auto-rolls to the next | an unattended tender marches down the list and can commit a worse/wrong carrier on timeout |
| **Broadcast** | sent to many carriers at once; the **first to accept wins** | you do not choose the winner; firing on the wrong order commits you to whoever answers first |
| **Open (freight exchange)** | published to a marketplace; bids collected, **awarded on the timer** to the best bid | a forgotten open tender awards freight on its own when the clock runs out |

Each method has a **tendering deadline / response window**. No response within the window is treated as a
rejection (peer-to-peer rolls on; broadcast/open close on the timer). A tender is a live external offer - on a
retry or duplicate, confirm whether the first tender already fired before re-sending.

**When the tender exhausts / all reject** - peer-to-peer walks the whole ranked list with no acceptance, or a
broadcast/open tender expires with no usable bid: the order returns to **Not Subcontracted** with no carrier
committed and no charge incurred. The safe next step is to re-optimize, re-tender (possibly a different
method or an adjusted list), or escalate - **not** to hand-assign a carrier to dodge selection, and not to
loosen an incompatibility/allocation to force a match.

## Subcontracting, statuses, and fixing
- **Subcontracting** assigns and confirms the carrier on the freight order. The **subcontracting status**
  runs: Not Subcontracted -> Ready for Tendering -> In Tendering -> **Confirmed** / Rejected.
- **Confirmed** is the commit: carrier capacity + cost are bound. Everything before it is a re-plan; after it,
  a change is a cancellation (charges) or an execution event.
- **Life-cycle status** (New -> In Planning -> Ready for Execution -> In Execution -> Executed -> Completed)
  and **execution status** move the order toward settlement. Once **In Execution**, the load is moving - a
  re-route/diversion/carrier swap is an execution change, not a plan edit.
- **Fixing** - a **fixed** freight order is protected from the next optimizer run; an **unfixed** one can be
  reorganized/unbuilt by a re-optimize. Fix an order before it is safe from a later run.

Gating note (aligned to the SKILL.md matrix): FU build / optimize / plan = **Write (reversible)** (no carrier
committed). Tender and subcontract/confirm = **Write (committing)** (a tender is outbound; the confirm binds
capacity + cost). Cancel of a **confirmed** order = **Destructive**.
