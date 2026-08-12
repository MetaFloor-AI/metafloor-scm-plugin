# Anaplan actions & integration - what each moves and what it overwrites

Actions are how data and bulk structure move in and out of a model. They are the committing/destructive
surface: none has a per-action undo, and each does what its **saved view + mapping** say, not what its name
implies. Read this when a workflow runs an import, export, delete, or process, or schedules one.

## Contents
- The four action types
- Import - module data vs list, mapping, overwrite/blank behavior
- Export - egress, not a free read
- Delete - the cascade with no undo
- Process - the clear-then-load trap
- Saved views as the scope
- How actions run (UX, API, Anaplan Connect, CloudWorks)

## The four action types
| Action | Does | Class |
|---|---|---|
| **Import** | loads data into module cells, or members into a list, from a file or another model's saved view | committing; destructive if it overwrites/blanks or replaces members at scale |
| **Export** | writes a saved view out to a file / downstream system | read if pure local screen; committing (egress) once it leaves the platform |
| **Delete** | removes list members selected by a boolean line item | destructive - member + all its data across every module |
| **Process** | runs an ordered sequence of the above as one unit | inherits the strongest class in the bundle - often destructive |

## Import - module data vs list
- **Module data import** - maps source columns to **line items** and writes values into the mapped cells
  within the target **saved view's** scope. It **overwrites** whatever was there; it does not merge. If the
  source has blanks and the mapping treats blank as a value, it **blanks** existing cells. Wrong view or wrong
  mapping overwrites the wrong scope.
- **List import** - **adds and updates** members (by code/name). It does not delete members - deletion is the
  separate delete action. Re-importing a **numbered list** with changed codes can **duplicate** members (new
  code = new member) or **orphan** old ones rather than update in place.
- **Mapping - named vs positional.** Named mapping ties source field -> line item by name and survives column
  reordering. **Positional** mapping ties by column order; if the source columns shift, values load into the
  **wrong line items** - a clean-looking import of wrong data. Prefer named; verify the mapping before running.
- **Source options** - a flat file (CSV/XLSX) or **model-to-model** (reads another model's saved view). A
  model-to-model import is only as fresh/correct as the source view; a change there shifts or breaks it silently.

## Export - egress, not a free read
An export renders a **saved view** to a file or hands it to a downstream system. Exporting to your own screen
is a read. An export that **leaves the platform** (to a file store, another system, a data-distribution
policy) is **egress** - governed data movement, gate it. The saved view's filter/pivot decides exactly what
ships; widening the view ships more without renaming the action.

## Delete - the cascade with no undo
- **"Delete from list using selection"** removes every member where a **boolean line item** is true. It reads
  that selection **at run time** - it deletes whatever is true *now*, so a wrong driving formula or shifted
  data deletes the wrong members.
- Deleting a member removes its data **at every module that uses the list**, not just the grid you are in - a
  model-wide cascade.
- There is **no per-action undo**. Recovery is: stop any schedule that would re-run it, scope it via model
  history, re-add the members, and **re-import their data** (re-adding brings them back empty). Back up the
  list + affected module data before running a bulk delete.

## Process - the clear-then-load trap
A process runs its actions **in order, as one click**. The common **reload** pattern is **clear-then-load**:
an import that blanks/clears the target, then an import that loads fresh data. Consequences:
- Run it and it **wipes first**. If the load step fails, or the source is empty/wrong that day, you are left
  **cleared** with no data.
- A process can chain a **delete** + an import (delete stale members, load new ones) - the delete's cascade
  fires as part of the run.
- Know **every** action in a process before running it; the process name hides its steps. Read the sequence.

## Saved views as the scope
Every import/export/delete/dashboard-source is defined against a **saved view** - its filter, pivot, and
hidden items are the exact scope of data the action reads or writes. The action does not carry its own scope;
the view does. Changing a shared view's filter silently changes what every action built on it moves. Before
running an action, open its source view and confirm the filter and the mapped line items.

## How actions run (and the unattended risk)
- **UX / dashboard button** - a Page card or classic dashboard button runs the same back-end action; a
  benign-looking button can fire a destructive delete/process. Read what the button runs.
- **API** - actions (import/export/delete/process) are callable by ID over the Anaplan **Bulk / Integration
  API**. Separately, the **Transactional API** writes/reads **individual cells** directly (not through a mapped
  import). A cell-level API write is a different blast radius than a bulk import - it inherits the same
  live-shared, no-undo properties as a UI cell edit, but a script can make many of them fast. Classify a
  cell-level API write like a live cell edit at the scale the script runs it.
- **Anaplan Connect** - the command-line/JDBC integration client; scripts run actions unattended.
- **CloudWorks** - Anaplan's managed scheduler/integration; runs actions and processes on a **timer** with no
  human step. A bad source file on a scheduled day **propagates or wipes automatically**. Know the schedule
  before relying on the data or adding another action, and **pause the schedule** first when recovering from a
  bad run.

Gating note: any import/delete/process is committing or destructive - gate + human approve (delete/overwrite
= hard gate + backup + re-read the view/mapping/selection at execute). An export is a read only when it stays
on your screen; once it egresses, gate it. A scheduled action is a standing committing/destructive act - treat
enabling or editing a CloudWorks schedule as committing.
