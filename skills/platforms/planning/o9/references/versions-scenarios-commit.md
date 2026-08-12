# o9 - versions, scenarios, commit/publish, and recovery

How a plan becomes shared reality in o9, and where undo stops being free. Read when a task saves to a
version, commits or promotes a scenario, publishes/releases a plan, or needs to recover from a bad write.

## Contents
- Versions: baseline/mainline vs alternatives
- Scenarios: simulate vs commit
- Commit / publish - the two meanings
- Snapshots and backup versions (the recovery mechanism)
- Release to execution / ERP
- Recovery decision summary

## Versions: baseline/mainline vs alternatives
- A **version** is a named copy of the plan's measure data. The **baseline / mainline** is the plan of record:
  every planner sees it and integration exports read it.
- **Alternative versions** are sandboxes - copy the baseline into one to simulate a change in isolation.
- Saving a measure edit or running a solver **into the baseline** changes shared reality immediately. Doing
  the same **into an alternative version** is contained and reversible (discard or re-copy from baseline).
- The active version in a workbook/view decides where an edit lands; the baseline is often the default target.
  Confirm the active version before every save.

## Scenarios: simulate vs commit
- A **scenario / what-if** is a simulation layer on a version that stores only your **deltas**.
- **Simulate** recomputes inside the scenario only; it persists nothing shared and is a safe read-class action.
- **Commit / promote** writes the scenario's deltas into the version's data - a **one-way** write, not a
  preview. Committing into the baseline makes the deltas shared for every planner.
- A scenario inherits its parent version: if the parent changes after you fork, your what-if sits on a moving
  base and a number you never touched can shift. Re-check the parent before committing.

## Commit / publish - the two meanings
The word "publish" (and "commit") is used loosely for two different committing actions - confirm which:
- **Promote a version into the baseline** - copies its measures into the plan of record and overwrites it.
  Shared-plan change, no ERP document yet.
- **Release / publish to execution** - pushes plan output **out** to ERP/execution, where it becomes real
  planned orders, requisitions, PIRs, or deployment/allocation. The real-world commitment.
Both are gated; the second creates documents you cannot recall from o9. Never assume which one a "publish"
button does - check what it writes.

## Snapshots and backup versions (the recovery mechanism)
- A **snapshot** freezes a measure's values into a snapshot measure at a point in time. Taking one writes only
  to the snapshot measure and overwrites no source, so it is always safe (read-class) - even on the baseline.
- A **backup version** copies the baseline into an alternative version before a risky baseline-writing run.
- These are the **only** real "before." o9 has no transaction-log undo of plan data: with no snapshot and no
  backup, an overwritten measure cannot be restored. Take one before any baseline-writing solver or commit.

## Release to execution / ERP
- Releasing planned orders, purchase / stock-transfer requisitions, PIRs, or deployment/allocation
  confirmations pushes them to ERP, where they become real documents with vendor, material and capacity
  consequences.
- Undo is **not** in o9. Canceling a released order is an ERP action under `sap-mm` gating.
- Before releasing: re-read the driving data and the last integration timestamp (o9 can be stale vs ERP);
  confirm the release set including dependent orders; know what automation the release triggers.

## Recovery decision summary
The change-by-change recovery decision table lives in `SKILL.md` (Recovery patterns) so it is available under
time pressure without loading this reference. The mechanics behind each row - snapshots, backup versions,
offsetting commits, release correction in ERP - are described above.
