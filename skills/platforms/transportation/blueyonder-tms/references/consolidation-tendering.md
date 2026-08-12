# Blue Yonder TMS - consolidation, routing guide, tendering, booking

How freight goes from an order to a committed carrier. Read when a task consolidates orders into loads, runs
the optimizer, works the routing guide, or tenders/books a load. The commit point is the tender and the
carrier's acceptance, not the plan.

## Contents
- Order-to-load consolidation and the optimizer
- The routing guide (the ranked waterfall)
- Tender methods (routing-guide/sequential vs spot)
- Tender statuses and timeout behavior
- Booking (ocean / rail / parcel)
- Fixing, continuous move, and pool loads

## Order-to-load consolidation and the optimizer
- Orders/shipments arrive from the host (OMS/ERP). Consolidation groups them into **loads** - the equipment/
  vehicle move that is rated, tendered, and settled.
- The **optimizer** (Transportation Planner / modeler) pools shipments, sequences multi-stops, picks mode +
  equipment, respects capacity / time windows / compatibility, and pre-selects a low-cost carrier from the
  rates and routing guide. A **scheduled/background run** does the same unattended.
- The optimizer **commits nothing**. It produces a plan (a load + route + proposed carrier). The commit is the
  tender/booking later. Conflating "build the load" with "tender it" commits freight spend early.
- What the optimizer sees is driven by its selection/planning scope - a wrong scope plans against the wrong
  freight or constraints, producing a plausible plan on the wrong orders.

## The routing guide (the ranked waterfall)
The routing guide is the ranked carrier + lane preference the system tenders against, built from:
- **Contracted rates** - the cost per candidate carrier on the lane.
- **Allocations / business shares** - contracted volume splits per lane (e.g. give carrier A 60%).
- **Carrier priority / service level** - master-data preference and required service.
- **Compatibility / eligibility** - hard constraints (equipment, hazmat, lane restriction, carrier block).

Rule: run the routing guide and let it rank. Hand-picking a carrier, or **editing the routing guide** to route
around an allocation, silently violates the contracted allocations and compatibilities that exist on purpose -
a sourcing/compliance move, not a convenience. Editing the routing guide re-routes **all** future tenders on
that lane.

## Tender methods (routing-guide/sequential vs spot)
Tendering offers a load to a carrier and asks it to accept. The offer leaves the building as **EDI 204**
(or a carrier-portal message) the moment it fires - externally visible even if you meant to stage it.

| Method | How it awards | The hazard |
|---|---|---|
| **Routing-guide (sequential)** | offered down the routing guide **one carrier at a time**; a decline or response-timeout auto-declines and rolls to the next tier | an unattended tender marches down the waterfall and commits a worse/higher-cost carrier on timeout |
| **Spot / spot bid** | off-contract auction to the spot market; bids collected, **awarded on the timer** to the best/lowest adjusted bid | a forgotten spot tender awards on its own at a higher, off-allocation cost; you do not pick the winner |
| **Manual / direct** | planner assigns a specific carrier and tenders directly | bypasses the routing guide's allocations/compatibilities; use only with reason |

**Auto-tender** applies any of these on a rule with no human. An auto-tender is a committing actor - gate it
(insert a confirmation step, or remove the auto action), do not trust it because "the rule fired."

## Tender statuses and timeout behavior
- Tender lifecycle: **Tendered -> Accepted (Confirmed) / Declined / Expired (no response) / Withdrawn.**
- **Accepted (EDI 990)** is the commit - capacity + cost are bound. An **inbound acceptance flips the load to
  Accepted on its own**, with no human on your side pressing confirm; re-read status and treat it as a live
  commitment.
- Each tender has a **response window**. No response within it is treated as a decline (routing-guide rolls to
  the next; spot closes on the timer).
- A tender is a live external offer - on a retry or a duplicate, confirm whether the first 204 already fired
  before re-sending (the commit is not idempotent).
- **When the tender exhausts / all decline** - routing-guide walks the whole waterfall with no acceptance, or a
  spot tender expires with no usable bid: the load returns to un-tendered with no carrier committed and no
  charge incurred. The safe next step is re-optimize, re-tender (a different method or list), or escalate -
  **not** hand-assign a carrier to dodge the routing guide, and not loosen a compatibility to force a match.

## Booking (ocean / rail / parcel)
- A **booking** reserves carrier capacity for ocean/rail/parcel against a sailing/voyage/flight, usually ahead
  of the cargo. Confirming the booking commits the allocation.
- Higher stakes than a road load tender: cancelling a booking gives the allocation back and it **may not be
  re-securable** at the same rate or at all. Size and confirm before booking.
- Parcel has its own manifest/label flow; ocean/rail carry container/equipment and sailing schedules that a
  road TL load does not.

## Fixing, continuous move, and pool loads
- **Fixing / locking** - a fixed load is protected from the next optimizer run; an **unfixed** one can be
  de-consolidated/rebuilt by a re-optimize. Fix a load before it is safe from a later run.
- **Continuous move (CM)** - two or more loads strung into one tour tendered to one carrier for a lower rate;
  the legs are financially linked. Un-tendering/cancelling one leg can unravel the tour and forfeit its discount.
- **Pool / multi-stop load** - one load consolidating several orders/stops; dropping one stop or order can
  break the consolidation and its rate. Re-cut deliberately, not as a reflex.

Gating note (aligned to the SKILL.md matrix): consolidate / optimize / rate / de-consolidate before tender =
**Write (reversible)** (no carrier committed). Tender (routing-guide or spot), accept, book/confirm, edit the
routing guide, re-optimize a load with an open tender = **Write (committing)**. Cancel/withdraw a
tendered-and-accepted load, or cancel a booking = **Destructive**.
