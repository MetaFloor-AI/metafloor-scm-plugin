# SAP IBP - versions, scenarios, snapshots, publishing

The three containers that decide whether a change is a safe sandbox edit or a change to the plan of record,
and the one backup lever that makes a baseline overwrite recoverable. Read when a workflow copies a
version, simulates in a scenario, promotes/publishes a plan, or needs a restore path.

## Contents
- Baseline vs alternative versions
- Version-independent key figures
- Scenarios (simulate vs save-to-version)
- Snapshots (the backup)
- Sharing vs publishing/promoting a version
- Recovery decision table

## Baseline vs alternative versions
- A **version** is a full parallel copy of the plan's key figures. The **baseline** is the live plan of
  record: it is what every planner sees by default, what analytics report, and what data-integration
  exports to execution.
- **Alternative versions** are sandboxes. Create one by copying the baseline, plan/simulate in it freely,
  and it never touches the plan of record until you copy it back. This is the safe way to try a different
  supply mode, demand assumption, or scenario at scale.
- Editing or running an operator **into the baseline** changes shared reality immediately. Editing into an
  alternative version does not.

## Version-independent key figures
Not every KF is copied per version. Many actuals/history/master-style KFs are **version-independent** -
one shared copy read by all versions. Editing one in an "alternative version" still changes it everywhere,
including the forecast baseline that reads history. Before assuming a version is a true sandbox, know which
of the KFs you touch are version-independent.

## Scenarios (simulate vs save-to-version)
- A **scenario** is a what-if layer on top of a version that stores only your deltas. It is the cheapest
  safe simulation: change inputs, run an operator into the scenario, compare, all with zero effect on the
  version's saved data.
- Two exits: **discard** (clean undo, no trace) or **save the scenario into the version** (a one-way commit
  of the deltas into the version's data). Save-to-version is a real write; on the baseline it is committing.
- Scenarios are the right tool for "what if demand is +10%" - keep it in a scenario until the number is
  agreed, then decide whether to save it.

## Snapshots (the backup)
- A **snapshot** copies a key figure's current values into a snapshot KF stamped with time/version. It is
  the primary backup and the basis for forecast-accuracy comparison.
- The discipline: **snapshot before any baseline-writing operator or promotion.** With a snapshot you can
  copy the prior values back if the run was wrong. Without one, an overwrite of the baseline is
  unrecoverable - IBP has no transaction-log undo.
- Snapshots are also how you compare "what we planned last month" against "what actually happened".

## Sharing vs publishing/promoting a version
- **Sharing** a version makes it visible to other planners (read/collaborate). Sharing does not change the
  baseline.
- **Publishing / promoting** means making a sandbox version's numbers the plan of record - done by copying
  its key figures into the baseline (a copy operator, often as an application job). This overwrites the
  current baseline. It is destructive unless a snapshot or backup version captured the prior baseline first.
- "Publishing a version to actuals" in loose usage means writing the agreed plan into the baseline/consensus
  that downstream integration then releases. Treat it as a hard gate: named approver, snapshot in place.

## Recovery decision table
| Change | Reversible? | How to undo |
|---|---|---|
| **Take a snapshot** (before any write) | n/a (protective, not undone) | it writes only a snapshot KF and creates the restore point every other recovery depends on. Do this first. |
| Simulate (Excel or scenario), never saved | yes | close/refresh; nothing persisted |
| Scenario saved into a version | no (as a unit) | it is now version data; restore only from a snapshot/backup |
| Save Data / operator into an **alternative** version | yes | re-copy that version from the baseline, or delete the version |
| Save Data / operator into the **baseline**, snapshot taken | yes | copy the snapshot / backup version back into the baseline |
| Save Data / operator into the **baseline**, no snapshot | no | re-derive by re-running the source, or re-key; prior values are gone |
| Release/export to ERP/execution | no (not from IBP) | correct in the receiving system and re-integrate (`sap-mm`) |
| Delete a version / scenario / planning combination | no | recreate and reload; stored data for it is dropped |
