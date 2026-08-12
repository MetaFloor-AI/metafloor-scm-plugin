---
name: anaplan
description: Anaplan connected-planning platform - the safe operation of models, modules and line items,
  lists / numbered lists / hierarchies, versions, the Hyperblock in-memory engine, saved views, dashboards and
  UX Apps / Pages, data-integration actions (import / export / delete / process), and ALM dev-to-prod model
  sync. Viewing, filtering and version / what-if analysis are safe; running an import, export, delete or
  process action, switching the current period or version actuals boundary, and ALM-syncing dev to prod are
  the committing or destructive events - a delete or bad import can wipe or overwrite list data at scale, with
  no per-action undo. Use when the connected planning system is Anaplan, or the user mentions a model, module,
  line item, a list or numbered list, a version, Hyperblock or Polaris, a saved view, a Page / App, an
  import / export / delete action or process, CloudWorks or Anaplan Connect, selective access or DCA, a
  revision tag, ALM or model sync, or dev vs prod models.
---

# Anaplan - operating it safely

Anaplan is a cloud connected-planning platform: customers build their own multidimensional models (FP&A,
sales / quota, workforce, S&OP) on the **Hyperblock** in-memory engine. It is a planning and modeling layer,
not the book of record and not a purpose-built supply APS. What makes it dangerous is not one posting - it is
two things: **the model is live and shared with no data-entry sandbox** (type into a driver cell and every
user and every downstream formula sees it instantly), and **the bulk power - import / delete / process
actions and ALM model sync - can overwrite or wipe list data at scale with no per-action undo.** Analysis is
cheap and safe. The actions and the deploy are where damage is permanent. This skill gives the judgment to
tell them apart so the harness can gate them.

## Contents
- When this applies (+ when NOT) · Object & state model · Vocabulary that bites
- Operations: read / write / destructive (the matrix + escalation rules)
- Gotchas that bite · Edge states · Reconciliation / freshness
- Recovery patterns · Guardrails · Worked example · References

## When this applies
Connected planning system is Anaplan and the work is modeling, data entry, running actions, or deploying
model changes. When NOT:
- Supply-focused APS decisions - constrained supply/demand planning, netting, MRP, capable-to-promise - on a
  purpose-built engine: Kinaxis -> `kinaxis`; o9 -> `o9`; SAP IBP -> `sap-ibp`;
  Blue Yonder -> `blueyonder-planning`. (Anaplan can model S&OP, but those vendors' engines have
  their own scenario/commit/release model - use their skill when the connected system is one of them.)
- The plan output becomes a real ERP order / stock / ledger posting - create/cancel a PO, post a goods
  receipt, value inventory, post to the ledger -> `sap-mm` / `sap-fi`. Anaplan reads from
  and pushes to those systems via actions; the real commitment and its recovery live there.

## Object & state model (reason about state, not nouns)
- **Workspace** - the memory container with a fixed size cap (GB). Models live in it and consume its memory; a
  model that bloats can starve the workspace and block other models from opening.
- **Model** - the unit of planning. Holds lists, time, versions, modules, saved views, dashboards/Pages,
  actions, and roles. Model **states**: online/offline, open/closed, **archived** (frees memory), and
  **development vs production** (a production model's structure is locked - changes come only via ALM sync,
  see `references/alm-and-model-management.md`). A model has a **size** = roughly cell count = product of
  applied dimensions x line items; size drives memory and calc time.
- **List (dimension)** - the members you plan over: **flat**, **hierarchical** (parent-child, composite
  multi-level), **numbered** (members keyed by code, for large transactional data), plus **subsets** and
  **properties**. Deleting a member deletes its data at that member **across every module** that uses the
  list - a model-wide cascade.
- **Module** - a calculation grid dimensioned by lists + time + versions. Not a report; it holds the calc.
- **Line item** - the atomic field inside a module. Either **input** (a person or an import writes it) or
  **formula-driven** (calculated, read-only - you change the input, never type over the output). Cell
  writability is further gated live by role, **selective access**, and **Dynamic Cell Access (DCA)**.
- **Time** - the native calendar (years/quarters/months/weeks/days) and the model's **current period** (the
  actuals cutoff). **Time Ranges** scope a module to a subset of the calendar; data outside the range is absent.
- **Version** - the native scenario dimension (Actual / Budget / Forecast + custom). The **current version /
  switchover** is the actuals-forecast boundary: it decides which periods are locked actuals vs editable
  forecast. Moving it, or adding/deleting a version, is a real state change.
- **Saved view** - a saved pivot/filter/hidden-item configuration over a module. It is the **scope an
  import/export/dashboard reads or writes through** - the view's filter decides what an action moves, not the
  action's name.
- **Action / process** - the data-movement and bulk mechanism: **import**, **export**, **delete**, and
  **process** (an ordered bundle of actions run as one). This is the committing/destructive surface - detail
  in `references/actions-and-integration.md`.
- **ALM** - revision tags (structure snapshots) + model sync deploy structure from a **dev** model to a
  **prod** model; data flagged **production data** survives the sync.

## Vocabulary that bites
- **Hyperblock** - the always-on in-memory engine. There is **no recalc button and no data-entry sandbox**: a
  change to a driver recomputes the whole model instantly and is live for every user. (Very large sparse
  models may run on the newer **Polaris** engine instead; the live-and-shared property is the same.)
- **Line item** - one field/formula, not a column of a report. Input vs formula-driven decides whether you
  may write it; a formula-driven cell is a calculated output.
- **List member** - a dimension row. Deleting one is not deleting a row of data - it removes that member's
  slice from **every** module, permanently.
- **Numbered list** - members keyed by a code, used for large transactional data. Re-importing with changed
  codes can duplicate or orphan members rather than update them.
- **Version** - a scenario, not a saved copy. The **current period / switchover** is the actuals boundary;
  moving it re-locks/unlocks periods and changes what is editable.
- **Saved view** - the action's scope. Change the view's filter or pivot and you silently change what an
  import overwrites or an export ships.
- **Action** (import/export/delete) - a bulk operation. Its blast radius is set by its saved view + mapping,
  which you must read before running it.
- **Process** - an ordered bundle of actions run in one click. A "reload" process often **clears then loads**;
  running it wipes first, and a failure after the clear leaves you wiped.
- **DCA (Dynamic Cell Access)** - driver-line-item-controlled read/write/invisible per cell. A cell can look
  editable and be blocked, or an import can write cells a user could not edit in the UI.
- **Selective access** - data-level security limiting which list members a user sees/edits. A read can be
  partial without saying so.
- **Breakback** - editing a calculated aggregate spreads the change **down into the input cells**. Editing one
  total is really a multi-cell write.
- **ALM / revision tag / production data** - dev-to-prod structure deployment; a list/data not flagged
  **production data** gets overwritten by the source model's members on sync.

## Operations: read / write / destructive
Classify every operation family by what it does to state. Kinds of action, no tool names. "Gate one at a
time" = present each write for individual human approval (not batched) so each state change is reviewed
before the next runs; the gate confirms the operator, the scope (view/mapping/selection), and freshness.

| Class | Anaplan operation families | Gate | Why |
|---|---|---|---|
| **Read** | open/view any module, dashboard, Page/App, saved view; run/refresh a view (the calc is automatic); filter/pivot; browse **model history / audit**; **preview an ALM sync comparison report** (no apply); an export **rendered to screen only** - no file written to disk, cloud, or a downstream system | always pass | no state change; Hyperblock recompute is passive |
| **Write (live-shared, no clean undo)** | enter/edit **by hand** a bounded set of cells in an **input** line item, or add a single list member in the UI (writes to the shared model immediately - recoverable only via shallow session undo or a full-model restore, **not** a private discard); enter data into an **existing** version or a scenario module for what-if; in a **development** model: add/change a line item, module, list member, saved view, or Page | gate one at a time | contained but live: **no copy-on-write and no clean per-edit undo** - the edit is live for all the instant you make it, and the only real reversal is shallow session undo or a blunt full-model restore (bulk creation of the same objects **via an import** is committing, not this class) |
| **Write (committing)** | **run an import** (overwrites mapped cell data, or adds/updates list members, at scale); **run an export that egresses** data off the platform; **run a process** (fires all its actions in order); **switch the current period / version switchover** (rolls the actuals-forecast boundary); **add a new version** (a new dimension member, re-dimensioning every module that uses versions); a **breakback** or a mass paste that writes many inputs; a **batch of Transactional-API cell writes**; publish/promote a Page | gate + human approve | binds many cells / members / a boundary at once, or ships data out; each is felt across the model or beyond it |
| **Destructive / irreversible** | **run a delete action** ("delete from list using selection" - removes members **and all their data everywhere**); a **process that clears-then-loads** (wipes first); an import set to **overwrite/blank** at scale or a list import that **replaces** members; **ALM model sync dev->prod** (deploys structure; unflagged production data is overwritten; formula/dimension changes recalc live for everyone); **delete a list / version / module / line item** that holds data; **roll back / restore the whole model** to a prior point (reverts everyone's changes since); archive/delete a model | hard gate + named approver + **backup first** + re-read | no per-action undo; a member's data across all modules is gone; a mass blast that recovery cannot fully reverse |

**No-sandbox rule (read this):** Anaplan has **no** Kinaxis-style scenario copy-on-write for data entry. Typing
a number into a shared **input** line item is a real, immediate, shared write that every downstream formula
consumes at once. "What-if is safe" holds only when it is done in a **version** or a **scenario module the
model was built with**, or a **personal view that drives nothing shared**. A one-off edit to a live shared
driver is a committing change, not a free experiment - never "try" a bulk action in the live model to see
what it does.

**Action-scope rule (read this):** an import/export/delete does what its **saved view + mapping** say, not
what its name implies. Read the view's filter and the field mapping before running. A **delete action reads
its boolean selection at run time** - it deletes every member that is true *right now*, so a wrong driving
formula or shifted data deletes the wrong members at scale.

**Production-data rule (read this):** an ALM sync deploys **structure** from dev to prod; any list or data not
flagged **production data** is overwritten by the source (dev/test) model's version of it. Before any sync to
prod: confirm the production-data flags, take a prod backup, and review the comparison report.

**Schedule-stop rule (read this):** before any recovery from a bad action, and before you scope the damage,
**pause every CloudWorks / Anaplan Connect schedule that could re-run it** - a scheduled job re-wipes on its
next cycle while you investigate. Stopping the schedule is minute-one work, ahead of everything else.

Universal rules to teach: read the current values before every write and **re-read at execute** (the model is
live and imports may have run); a formula-driven cell is read-only - change the input; a block from role /
selective access / DCA means stop, not work around; treat the current-period/switchover and any ALM sync as
finance/model-owner controls, not agent conveniences; an export that leaves the platform is **egress**, gate
it - only a pure local-screen export is a free read.

## Gotchas that bite (the real set - causal chains)
1. **There is no data-entry sandbox.** A value typed into a shared input line item is saved to the model
   instantly and is live for every user and every downstream formula - unlike a Kinaxis private scenario, there
   is nothing to discard. The only "undo" is session-local undo or a full-model rollback.
2. **Deleting a list member cascades model-wide.** The member's data at every module that uses that list is
   removed, not just the row you were looking at. One delete can empty cells in modules you never opened.
3. **A delete action deletes whatever its selection is true for right now.** "Delete from list using selection"
   runs against a boolean line item at execute time; if the driving formula is wrong, or data shifted since you
   checked, it removes the wrong members - at scale, with no undo. See `references/actions-and-integration.md`.
4. **An import overwrites the mapped cells.** It does not merge intelligently - a wrong mapping, a wrong saved
   view, or a source with blanks can blank out or overwrite existing data across the view's whole scope.
5. **A process fires all its actions in order.** A "reload" process typically **clears then loads**; run it and
   it wipes first - if the load step then fails or the source is empty that day, you are left cleared.
6. **The saved view is the action's scope, and it is silent.** Widen a view's filter or re-pivot it and the
   next import overwrites more, or the export ships more, than before - the action name did not change.
7. **ALM sync overwrites unflagged production data.** Deploy structure from dev to prod and any list/data not
   marked **production data** is replaced with the dev model's (often test) members - a mass wipe of real prod
   list data. Numbered/transactional lists especially must be flagged. See `references/alm-and-model-management.md`.
8. **An ALM sync also changes formulas and dimensionality live.** A deployed formula change silently changes
   every planner's numbers; adding/removing a dimension on a module recalculates and can drop data.
9. **You cannot hotfix a production model's structure.** Prod structure is locked - the UI does not offer the
   structural edit (the option is unavailable/greyed), it does not accept-then-discard it. A formula/list change
   must be made in the dev model and synced via ALM; do not hunt for a workaround - route it through dev -> ALM.
10. **Formula-driven cells are read-only outputs.** You cannot fix a calculated number by typing over it -
    change the driving input and let Hyperblock recompute. Editing the wrong cell does nothing or edits the
    wrong thing.
11. **Breakback hides a multi-cell write.** Editing a calculated total with breakback on spreads the change
    proportionally into the underlying input cells - a much bigger write than the one total you touched.
12. **A cell that looks editable may be blocked, and an import may write cells the UI would block.** DCA and
    selective access gate the interactive grid but an action can bypass those UI guardrails - a change the grid
    silently refused looks applied but did not land, and an import can reach protected cells.
13. **The whole model recalculates in memory on every change.** A formula on a heavily-dimensioned line item
    can spike model size and calc time, and a big list import can explode the cell count enough to blow the
    workspace memory cap - the model then won't open and blocks others.
14. **Time Ranges silently drop data outside the range.** A module scoped to a time range holds only those
    periods; a formula referencing periods outside it returns zero/blank, so numbers can vanish without an error.
15. **Moving the current period / version switchover re-locks periods.** Roll it forward and forecast periods
    become locked actuals (or vice-versa); the actuals/forecast boundary shifts for every planner and formula.
16. **Deleting a version deletes all its data.** A version is a data slice, not a saved copy - dropping "Budget"
    drops every number in Budget.
17. **The model is only as fresh as its last inbound import.** Anaplan reads source systems (ERP/CRM/warehouse)
    via scheduled imports; a module number can be stale relative to source. Confirm the last import before you
    run an outbound export/publish off it.
18. **Scheduled actions run unattended.** CloudWorks (and Anaplan Connect / API) can run an import, delete, or
    process on a timer with no human step - a bad source file that day propagates or wipes automatically. Know
    the schedule before you rely on the data or add another action.
19. **Model-to-model imports drift.** An import that reads another model's saved view breaks or shifts silently
    when the source view or source model changes; the target stays stale until the import re-runs.
20. **Positional mapping lands data in the wrong line item.** If an import maps by column position (not by name)
    and the source columns shift, values load into the wrong line items - a clean-looking import of wrong data.
21. **A full-model rollback is a blunt undo.** Restoring the model to a prior point reverts **everyone's**
    changes since that point, not just your mistake - it is a coordinated operation, not a personal Ctrl+Z.
22. **Restoring a deleted list member does not restore its data.** Re-adding the member (or re-importing it)
    brings it back empty; the data it held across all modules is gone unless you reload it from the source.
23. **A cell-level Transactional API write is a live edit at machine speed.** It writes individual cells directly
    (not through a mapped import), inheriting the same live-shared, no-undo property as a UI edit - but a script
    can fire thousands in seconds, so its blast radius rivals a bulk import. Classify it by the scale it runs at,
    not as a single harmless cell edit. See `references/actions-and-integration.md`.

## Edge states & special cases
- **Numbered lists / transactional data** - keyed by code, sized large; the classic case where an import
  duplicates or orphans members if codes don't line up, and the classic thing an ALM sync wipes if unflagged.
- **Composite (multi-level) hierarchies** - deleting a parent removes its children and all their data;
  re-parenting re-aggregates every dependent module.
- **Versions with formula scope / switchover** - a line item can use input for Actual and a formula for
  Forecast; getting the switchover or version formula wrong mixes actuals and forecast in the same line.
- **Silent-write failures** - selective access or DCA can make the grid accept an edit that did not commit (no
  rights), or hide members from a read so a total looks complete but isn't. Confirm the write landed and that
  your view is not filtered by access before trusting a number.
- **Concurrent writes are last-writer-wins** - there is no cell lock for data entry. Two users, or a user and a
  scheduled import, writing the same cell means the last write silently wins; a value you just set can be
  overwritten by an import that runs mid-edit. Re-read at execute and know the schedule before you trust a cell.
- **Polaris vs Hyperblock** - a model may run on the newer sparse engine; the calc semantics differ for sparse
  data but the live-and-shared, no-sandbox property is identical - do not assume a sandbox because it's Polaris.
- **Classic dashboards vs UX Apps/Pages** - action buttons on a Page run the same import/delete/process as the
  back-end action; a button labeled benignly can fire a destructive action. Read what the button runs.
- **Workspace at capacity** - near the memory cap, a large import or a new heavily-dimensioned line item can
  push the model (or the workspace) over the limit and block opening - a size check is part of a big write.

## Reconciliation / freshness
- The model can be stale two ways: relative to **source systems** (last inbound import) and relative to
  **another model** (a model-to-model import not yet re-run). Check the relevant one before an outbound action.
- At execute time, re-read the driving cells and the last-import timestamp; the model is live, so a value read
  minutes ago may have moved (another user's edit, or a scheduled import that ran).
- When Anaplan and the source system disagree, the source system is the record for its own data; reconcile
  before you export/publish a number back out, or you push a plan-side figure the source will reject or double.

## Recovery patterns (can it be undone, and what cannot)
- **Session undo (Ctrl+Z)** - reverts your own recent cell edits, limited depth, this session only. Not a
  recovery path for a bulk action or another user's change.
- **Model history / audit** - every cell change, action run, and structural change is logged with user, old/new
  value, and timestamp. Use it to see exactly what an action did and its scope - the basis for any recovery.
- **Full-model rollback / restore** - restores the whole model to a prior point; a full-model restore/backup
  brings back **data and structure** (unlike an ALM structure re-sync, which restores neither the data it
  dropped). But it reverts everyone's changes since, so coordinate and back up first. Blunt, not surgical.
- **Bad import / delete (no per-action undo)** - act on time tiers: (1) **stop the schedule FIRST (minute-one work)** - pause any
  CloudWorks/Connect job that would re-run and re-wipe on the next cycle, before anything else (in CloudWorks
  toggle the integration's schedule off; in Anaplan Connect disable the scheduled task / pull its API token); (2) scope it via **model history** -
  which members/cells changed; (3) **reload the correct data** from the source of truth (re-import); (4) if
  **list members were deleted**, re-add them **and** re-import their data - the members come back empty
  otherwise; (5) if the damage is wide, a **rollback** to the pre-action point may beat cell-by-cell repair, at
  the cost of losing other changes since. Minutes matter: catch it before the next scheduled run.
- **Bad ALM sync to prod** - there is no clean un-sync; restore the target from the **pre-sync backup** (take
  one before every prod sync) or sync a corrected revision. A structure sync that dropped data will **not**
  restore that data by re-syncing structure - reload the data separately.
- **Deleted version / list** - gone; restore from a model backup. Prevention (back up before the delete) is far
  cheaper than recovery.

## Guardrails
- Work through the model's built-in versions/scenario modules for what-if; remember any edit to a shared input
  is live and shared the instant you make it - there is no sandbox to discard.
- Before any import/export/delete/process: read the **saved view + mapping** (the real scope), confirm
  add/update/delete behavior, and know every action a process contains (a clear-then-load wipes first).
- Before an **ALM sync to prod**: confirm production-data flags, take a prod backup, review the comparison
  report, and know that formula/dimension changes recalc live for all.
- Before switching the current period / version switchover, or deleting a version/list/module: it moves the
  actuals boundary or deletes a whole data slice - size it and back up first.
- A formula-driven cell is read-only; a role/selective-access/DCA block means stop; treat any export whose data
  leaves your session as egress and gate it; do not run a bulk action in the live model just to see what it does.
- **Access restriction does not make an import safe.** DCA and selective access gate the interactive grid, but
  an **import action can write cells a user could never edit in the UI** - do not reason "the data is protected,
  so the import is low-risk." Gate the import on its own scope (view + mapping), not on who can type where.
- For anything in the destructive row (delete action, clear-then-load process, overwrite import, prod ALM sync,
  version/list delete, full-model rollback): named approver, backup, re-read the scope, and log the reason.

## Worked example (a safe cycle, and where undo stops being free)
An analyst must load a new month of actuals for 3,000 cost centers into the Actuals version. Safe path: (1)
**preview** the target module and the import's **saved view + mapping** - confirm it writes only the Actuals
version, only the new period, only the mapped line items (read, free); (2) confirm the model is fresh - the
inbound source file is this month's, and no scheduled import will also run mid-load; (3) **back up** the model
(a copy) because this is a bulk overwrite; (4) after human approval, **run the import** (committing - it
overwrites ~3,000 x N cells in scope); (5) if a **process** wraps it, know whether it clears first and confirm
every step; (6) **do not** roll the current-period switchover forward until the actuals are verified - that
lock is a separate committing act. Undo cost climbs at each step: a wrong single input cell in step 1 is a
Ctrl+Z; a wrong **mapping** in step 4 overwrote 3,000 members' data and now needs a reload-from-source or a
rollback that reverts everyone's other changes too; a **delete action** in the same process would have removed
those members and their data across every module - reloading brings the members back empty. This is why the
view + mapping are read before the run, and the backup is taken before the bulk write, not after.

**Destructive path (a delete action).** Asked to "clean up stale cost centers", a delete action runs "delete
from list using selection" against an **Inactive?** boolean. Safe handling: (1) read the driving formula and
**count** how many members are true *right now* - if "Inactive?" flipped because this month's actuals haven't
loaded yet, it may be true for live cost centers; (2) back up the list + affected module data; (3) named
approver confirms the count and scope; (4) run it, knowing each deleted member's data vanishes across every
module and reloading the member returns it **empty**. The same pattern applies to an **ALM sync to prod**:
confirm the production-data flags, back up prod, review the comparison report, then sync - a sync with an
unflagged numbered list replaces its members with the dev model's and wipes prod data at scale.

## References (load on demand)
- `references/actions-and-integration.md` - the action types (import / export / delete / process) in depth:
  module vs list import, named vs positional mapping, add/update/delete and overwrite/blank behavior,
  model-to-model imports via saved views, the clear-then-load process pattern, and how actions run (UX buttons,
  API, Anaplan Connect, CloudWorks scheduling) - the committing/destructive core.
- `references/alm-and-model-management.md` - ALM (dev vs prod models, revision tags, model sync, the
  production-data flag and the wipe hazard), model states (online/offline, archived), workspace memory and
  model size, and model history / rollback / backups - the deploy and recovery surface.
