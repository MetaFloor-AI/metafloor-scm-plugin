# Maximo PM, meters, and maintenance purchasing

The three engines that generate maintenance demand and the spend behind it: preventive maintenance (PM)
schedules that auto-create work orders, meters that drive due dates and alarms, and the PR/PO chain that buys
the parts. Read when a workflow generates PMs, sets or corrects a meter reading, or raises / receives a
purchase for maintenance.

## Contents
- PM: frequency, meter-based, Master PM
- Job plans and revisioning
- Meters: types and rollover
- Condition monitoring
- Purchasing: PR / PO / receipt / invoice flow

## PM: frequency, meter-based, Master PM
- A **PM** auto-generates work orders on a schedule. Two drivers: **time frequency** (every N days/weeks) and
  **meter-based** (every N meter units, e.g. 250 hours). A PM can carry both; whichever comes first triggers
  the WO.
- The **next-due** recalculates when the generated WO reaches **COMP** - from the completion date or last
  meter. Completing a PM WO early or late therefore shifts the whole future schedule for that asset. Correct a
  wrong shift by fixing the PM's last-completion / last-meter, not by editing the generated WO.
- A **Master PM** is a template. Editing it **cascades** to every associated PM, and thus to all future WO
  generation across every asset that uses it - one edit reschedules a fleet. Change a master with that blast
  radius in mind.
- Overlapping PMs (a time-based and a meter-based PM on the same asset, or a sequence/route PM) can both come
  due and generate more than one WO; expect and reconcile the overlap rather than treating each WO as unique.

## Job plans and revisioning
- A **job plan** lists the tasks, planned labor, materials, services, and tools for a type of work; a PM
  points at one.
- Job plans are **revisioned**. When a PM (or a user) generates a WO, the plan is **copied onto the WO** at
  that moment. Editing the job plan afterward does **not** change already-open WOs - the fix must be applied
  to each WO. The WO records the revision it was born from.

## Meters: types and rollover
- **Continuous** - accumulates (running hours, odometer). A reading **below** the previous is read as a
  **rollover** (the meter wrapped or was re-installed), not a correction; the PM due-calc must treat it as
  rollover or the PM never comes due.
- **Gauge** - a level between limits (pressure, vibration); drives condition monitoring, not accumulation.
- **Characteristic** - a coded state (e.g. color, on/off); used for inspections.
- A reading is a **committing** entry: it can generate a PM WO or trip an alarm. A wrong reading manufactures
  unneeded work or hides a real fault. Correcting it later (edit or delete) does **not** retract a WO or alarm
  it already generated - handle those separately.

## Condition monitoring
- A meter reading crossing an **alarm limit** (warning or action) can auto-generate a work order or raise an
  alarm. This is the predictive path: the reading is the trigger, so its accuracy is safety-relevant.
- A false high reading creates spurious breakdown work; a false low reading suppresses a needed alarm.

## Purchasing: PR / PO / receipt / invoice flow
- **PR (purchase requisition)** - the request. Status WAPPR -> APPR. A reorder run or a direct-issue WO line
  can auto-create one.
- **PO (purchase order)** - the commitment to a vendor. WAPPR -> APPR -> INPRG (issued / sent) -> RECEIVED ->
  CLOSE. Approving the PO commits spend.
- **Receipt** - committing; increases inventory (for stocked lines) or charges the WO directly (direct-issue /
  special-order), and posts received-not-invoiced. RECEIVED is not CLOSE.
- **PO close** - locks the PO; no further receipts. A partial delivery arriving after close is stranded and
  needs a new PO or a reopen if config allows.
- **Invoice** - matching and approving an invoice commits the AP liability and clears received-not-invoiced. A
  quantity or price mismatch is the classic three-way-match exception; resolving it is a finance decision, not
  a silent balance edit.

Gating note: PR create is reversible before approval; PR/PO approval and PO receipt are committing (spend and
stock); PO close and invoice approval are destructive/irreversible (lock, AP liability). A meter reading and a
PM generation are committing because they create maintenance demand.
