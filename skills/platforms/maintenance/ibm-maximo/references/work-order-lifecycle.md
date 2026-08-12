# Maximo work-order lifecycle - what each status transition runs

The work order is a governed state machine. The hazard is that each status change is an **action**, not a
label: it reserves stock, posts actuals, resets a PM, or locks the record. Read when a workflow approves,
completes, closes, cancels, or reopens a WO, or works a parent/child WO hierarchy.

## Contents
- The status flow and what each transition does
- What you can do in each status
- Side / wait statuses
- Work-order hierarchy (parent and task WOs)
- Reopen and correction mechanics

## The status flow and what each transition does
Happy path: **WAPPR -> APPR -> INPRG -> COMP -> CLOSE**.

- **WAPPR (waiting on approval)** - the draft. Planned labor, materials, services, and tasks can be added and
  edited freely; nothing is reserved or posted. This is the only truly reversible state.
- **APPR (approved)** - committing. Approval creates **hard reservations** for the WO's storeroom material
  lines (removing that quantity from available for others), makes the WO schedulable, and for direct-issue /
  special-order lines can **auto-generate a PR or PO**. Editing materials or scope after APPR is a committing
  change, not a benign edit.
- **INPRG (in progress)** - work has started. Actuals (labor, materials issued, tools) post against the WO
  here; each is a costed transaction.
- **COMP (complete)** - the work is physically done but the WO is **still open** for late actuals and cost
  postings. COMP on a PM-generated WO **resets the PM next-due** from the completion date (or last meter) and
  can update meters and warranty. It is not a lock.
- **CLOSE (closed)** - the lock. Actuals freeze, cost rolls up to the asset / location / GL, and no further
  labor, material, or cost transaction is accepted. A charge that arrives after CLOSE is stranded. CLOSE is
  terminal in the normal flow.

## What you can do in each status
The most common agent decision is "can I do X while the WO is in status Y?". Quick guide (deployments can
tighten this with security groups):

| Action | WAPPR | APPR | INPRG | COMP | CLOSE |
|---|---|---|---|---|---|
| Edit planned labor / materials / scope | yes | committing change | committing change | no (post actuals only) | no |
| Hard-reserve / issue materials | no (reserve at approve) | yes | yes | yes | no |
| Report actual labor / tools | no | yes | yes | yes | no |
| Change priority / work type | yes | committing | committing | no | no |
| Cancel (-> CAN) | yes | yes if no actuals | config-dependent | no | no |
| Move forward a status | approve | start work | complete | close | terminal |

"Committing change" means allowed but it is a committing action (reservations exist, cost may be posted), so
gate it. Non-costed **work log / notes** are usually still allowed on a closed WO; the CLOSE lock is on
actuals and cost, not on annotation. For any costed transaction, past CLOSE nothing is editable; the only
path is a reopen (if configured) or a new corrective WO.

## Side / wait statuses
- **WSCH (waiting to be scheduled)** - approved-adjacent holding state used by scheduling; the WO is planned
  but not yet dispatched.
- **WMATL (waiting on material)** - parts are not available; the WO is held pending stock or a PO receipt.
- **WPCOND (waiting on plant condition)** - held until the asset can be safely taken down (a shutdown window).
- **CAN (cancelled)** - the WO is voided. Cancelling releases hard reservations back to available. A WO that
  already carries **actuals cannot be cancelled**; it must run to COMP/CLOSE or be corrected with a new WO.

Treat WMATL / WPCOND / a hold as **stop** signals: they were set for a reason (no stock, unsafe to work).
Do not push a WO past them to force progress.

## Work-order hierarchy (parent and task WOs)
- A WO can have **child work orders** or **tasks**. Cost and actuals **roll up** to the parent.
- The parent cannot move to COMP/CLOSE until its children are complete.
- Charge labor and materials to the **correct level**: cost booked to the wrong child or to the parent
  distorts the per-task and per-asset cost history that reliability analysis reads.
- A PM or a job plan can generate a multi-task WO in one shot; each task carries its own labor and material.

## Reopen and correction mechanics
- **Reopening a closed WO is not a status transition** in the normal flow. Some deployments enable a re-open
  path (moving CLOSE back to an editable status, sometimes exposed as HISTEDIT-style history editing); if it
  is not configured, the only correction is a **new corrective WO**.
- Frozen actuals stay in history whether or not a reopen is possible; a reopen does not erase the original
  postings.
- A wrong PM reset (from an early/late COMP) is fixed by correcting the PM's last-completion / last-meter, but
  any WO already generated from the shifted schedule remains and must be cancelled or worked.
- A forced or scripted status jump that skips APPR or COMP bypasses the reservation and actuals logic those
  transitions run, leaving orphaned reservations or unposted cost - avoid it; walk the flow.
