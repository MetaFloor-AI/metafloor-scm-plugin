# Infor EAM PM schedules, meters, and maintenance purchasing

The three engines that generate maintenance demand and the spend behind it: PM schedules that auto-create
work orders, meters that drive due dates and alarms, and the requisition / PO chain that buys the parts. Read
when a workflow generates PMs, sets a route, corrects a meter reading, or raises / receives a purchase for
maintenance.

## Contents
- PM schedules: fixed, floating, meter-based
- Standard WOs and maintenance patterns
- Routes
- Meters: types and rollover
- Condition monitoring
- Purchasing: requisition / PO / receipt / invoice flow

## PM schedules: fixed, floating, meter-based
A **PM schedule** auto-generates work orders. Three due-date engines:
- **Fixed (calendar)** - next due from the planned / **last start** date. The schedule is anchored to a fixed
  calendar and **does not slip** if the work is done late; useful for regulatory or seasonal work.
- **Floating (calendar)** - next due from the **last completion** date. The schedule **slips** with actual
  completion, so completing a floating PM early or late moves every future occurrence for that equipment.
- **Meter-based** - next due from accumulated meter units (e.g. every 250 hours). A schedule can combine
  calendar and meter; whichever comes first triggers the WO.

Fixed vs floating is the classic Infor EAM confusion: correct a wrong shift on a floating PM by fixing its
last-completion / last-meter, not by editing an already-generated WO (which is a copy). Overlapping engines
(a time PM and a meter PM on the same asset) can both come due and generate more than one WO - reconcile the
overlap rather than treating each WO as unique.

## Standard WOs and maintenance patterns
- A **Standard Work Order** lists the tasks, planned trades / labour, parts, and tools for a type of work; a
  PM points at one. (Infor EAM's analog of a "job plan" - use the Infor term.)
- The standard is **copied onto the WO** at generation. Editing the standard afterward does **not** change
  already-open WOs; the fix must be applied to each WO. The WO records what it was generated from.
- A **Maintenance Pattern** sequences several standard WOs across successive PM cycles (e.g. a small service
  each quarter, a major every fourth). Editing the pattern reshapes only future cycles.

## Routes
- A **route** is a PM / WO that covers **many pieces of equipment** in one pass (inspection rounds,
  lubrication loops). The PM generates child equipment lines / WOs for the route members (controlled by an
  install parameter).
- Completing or closing the route acts on the whole round; a fault on one member still needs its own
  corrective WO. Reserving parts for a route reserves for every member, so a route can commit a lot of stock.

## Meters: types and rollover
- **Continuous** - accumulates (running hours, odometer). A reading **below** the previous is read as a
  **rollover** (the meter wrapped or was re-installed), not a correction; the meter-PM due-calc must treat it
  as a rollover or the PM never comes due.
- **Gauge** - a level between limits (pressure, vibration); drives condition monitoring, not accumulation.
- **Characteristic** - a coded state (e.g. on / off, colour); used for inspections.
- A reading is a **committing** entry: it can generate a PM WO or trip a condition alarm. A wrong reading
  manufactures unneeded work or hides a real fault. Correcting it later (edit or delete) does **not** retract
  a WO or alarm it already generated - handle those separately (cancel the spurious WO, clear the alarm).

## Condition monitoring
- A meter reading crossing a **limit** (warning or action) can auto-generate a work order or raise an alarm.
  This is the predictive path: the reading is the trigger, so its accuracy is safety-relevant.
- A false high reading creates spurious breakdown work; a false low reading suppresses a needed alarm.

## Purchasing: requisition / PO / receipt / invoice flow
- **Requisition (PR)** - the request. A reorder run, a direct / non-stock WO part, or a user (a "requestor")
  can raise one. It routes for approval.
- **Purchase Order (PO)** - the commitment to a supplier. Approving the PO commits spend.
- **Receipt** - committing; increases inventory (for stock parts) or charges the WO directly (direct /
  non-stock parts), and posts received-not-invoiced. Received is not closed.
- **PO close** - locks the PO; no further receipts. A partial delivery arriving after close is stranded and
  needs a new PO or a reopen if config allows.
- **Invoice** - matching and approving a supplier invoice commits the AP liability and clears
  received-not-invoiced. A quantity or price mismatch is a match exception; resolving it is a finance
  decision, not a silent balance edit. When EAM interfaces to an ERP, AP and valuation usually live on the
  ERP side.

Gating note (supplementary to the matrix in SKILL.md, consistent with it): requisition create is reversible
before approval; requisition / PO approval and PO receipt are committing (spend and stock); PO close and
invoice approval are destructive / irreversible (lock, AP liability). A meter reading and a PM / route
generation are committing because they create maintenance demand - all of these are classified in the main
operations matrix; this note just groups the purchasing-specific ones.
