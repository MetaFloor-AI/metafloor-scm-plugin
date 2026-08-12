# SAP PM notifications, maintenance plans, and measuring points

The report side (notifications) and the scheduling side (maintenance plans, counters). The hazard: a
notification is not an order and posts no cost, and the plan / IP30 engine generates **real** due orders with
reservations and spend. Read when a workflow raises or completes a notification, schedules or edits a
maintenance plan or strategy, works a task list, or enters a measuring-point / counter reading.

## Contents
- Notifications (M1 / M2 / M3) and status
- Notification items, tasks, activities, malfunction data
- Maintenance plans (single-cycle / strategy / multiple-counter)
- Maintenance items and task lists
- Strategies and packages
- Scheduling and IP30 deadline monitoring
- Measuring points, counters, measurement documents

## Notifications (M1 / M2 / M3) and status
The notification is the **report / request** - no cost, no execution. Types:
- **M1 - maintenance request** - a request for work to be planned.
- **M2 - malfunction report** - a fault; captures **malfunction start / end** and the **breakdown** indicator,
  which feed downtime, MTBF, and MTTR.
- **M3 - activity report** - documents work already done (often after the fact).

Status flow: **OSNO** (outstanding) -> **NOPR** (in process) -> **NOCO** (completed). A notification can be
**postponed** and put back in process. Completing it (NOCO) records the report is handled - it does **not**
confirm or cost the work. A notification can be linked to one order (or an order created directly from it); the
two close **independently** - closing the order does not auto-complete the notification, and NOCO does not TECO
the order.

## Notification items, tasks, activities, malfunction data
- **Item** - the problem detail: object part, damage code, cause code. Feeds failure analysis.
- **Task** - a planned corrective step tracked on the notification (with its own status and responsible party).
- **Activity** - what was actually done, recorded on the notification.
- **Malfunction / breakdown data** - start, end, and breakdown flag on an M2. Wrong or missing times corrupt the
  reliability history that drives the preventive strategy, so capture them accurately.

## Maintenance plans (single-cycle / strategy / multiple-counter)
The **maintenance plan** is the scheduling object (IP01/IP02/IP03). Three shapes:
- **Single-cycle plan** - one time interval or one counter interval (e.g. every 3 months, or every 500 hours).
- **Strategy plan** - driven by a **maintenance strategy** with several **packages** (e.g. 1M / 3M / 12M cycles),
  so different task lists fire at different multiples.
- **Multiple-counter plan** - triggered by more than one counter (e.g. hours or mileage, whichever comes first).

## Maintenance items and task lists
- A **maintenance item** is what the plan does: the technical object, the planner group, the order type, and the
  **task list** to use. One plan can hold several items.
- A **task list** (general / equipment / functional-location) is a reusable set of operations, components, and
  PRTs. The order or plan **copies** the task list at generation; editing the task list afterward does not change
  orders already created - fix the order itself.

## Strategies and packages
A maintenance strategy defines the packages (cycle lengths) and their hierarchy. Editing a strategy or a plan's
cycle changes **every future call** generated from it across all assigned objects - one edit reschedules
maintenance fleet-wide. A plan / strategy / task list is cleanly reversible only **before** it has generated
call objects or been copied onto an order; once **live calls** exist, an edit is high-blast and committing -
re-read the outstanding calls after changing it, because they may need cancelling or regenerating. Treat a
strategy / plan edit as high-blast, not a local tweak.

## Scheduling and IP30 deadline monitoring
- **Scheduling** a plan (IP10 single, IP30 mass) computes call dates and, when a call is due, generates the
  **maintenance call object** - a real maintenance order or notification with its reservations and potential spend.
- **IP30** is the background **deadline-monitoring** run that schedules many plans at once; it can create a batch
  of due orders with no human in the loop, firing reservations for scarce spares and raising PRs.
- A call has a completion requirement; a missed or manually-skipped call shifts subsequent dates depending on the
  **scheduling parameters** (shift factor, tolerance). Do not skip or reschedule a call to force a run - it moves
  the whole future schedule.

## Measuring points, counters, measurement documents
- A **measuring point** records a condition on a technical object; a **counter** is a measuring point that
  **accumulates** (operating hours, mileage, cycles).
- A **measurement document** (IK11 create, IK13 display) is a single reading. Counter readings advance the counter
  and drive **counter-based** maintenance plans and **condition-based** maintenance (a reading past a limit can
  generate a call or an order).
- A reading **below** the previous on a counter is interpreted as an **overflow / reversal** (or a replaced
  counter), not a decrease; a wrong reading shifts the counter-based schedule or trips a spurious call. The
  **annual estimate** on a counter is what the plan uses to project the next due date between readings.
- Correcting a bad reading (reverse / new document) does not retract a call it already generated - cancel or work
  that call separately.
