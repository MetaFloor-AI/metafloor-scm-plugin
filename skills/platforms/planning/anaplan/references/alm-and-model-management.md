# Anaplan ALM & model management - deploy, memory, and recovery

How structure moves from development to production, how model state and memory constrain what you can do, and
how you recover when something goes wrong. Read this when a workflow deploys model changes (ALM sync), touches
model state/backup, or needs to undo a bad action.

## Contents
- ALM: structure vs data separation
- Development vs production models
- Revision tags & model sync
- The production-data flag (the wipe hazard)
- Model states, workspace memory, model size
- Model history, rollback, and backups

## ALM: structure vs data separation
**Application Lifecycle Management** separates **structure** (modules, line items, formulas, list structure,
views, actions) from **data** (the numbers and most list members). Structure is built and changed in a
**development** model and deployed to a **production** model; data stays in production and is meant to survive
the deploy. This is the discipline that lets you change a live planning model without hand-editing prod.

## Development vs production models
- A model is flagged **production** or **development**. A **production model's structure is locked** - you
  cannot add/change a line item, formula, or list structure directly in it. Structure changes are made in the
  linked **development** model and brought over by sync.
- Consequence: **you cannot hotfix a prod formula in place.** The change goes dev -> sync -> prod. Trying to
  "just fix it in prod" is not available by design; plan the change through ALM.

## Revision tags & model sync
- A **revision tag** is a named snapshot of a model's **structure** at a point in time.
- **Model sync (deploy)** applies the structural differences from a **source revision** onto a **target**
  model. Anaplan produces a **comparison / sync report** showing what will change (added/removed/modified
  modules, line items, lists, formulas) - review it before applying.
- A sync deploys structure only, but structural change has data consequences: a **formula change** silently
  changes every planner's results the moment it lands; **adding/removing a dimension** on a module
  recalculates and can **drop data**; a renamed/removed line item drops its cells.

## The production-data flag (the wipe hazard)
- Certain lists and data are flagged **production data** so a structure sync does **not** overwrite them with
  the source model's version. **Numbered lists / transactional lists** and their production members are the
  usual case.
- If a list/data that should be production is **not flagged**, a sync **replaces its members with the source
  (dev/test) model's members** - a mass wipe of real production list data. This is the single most damaging
  ALM mistake.
- Before any sync to prod: confirm the production-data flags are correct, **take a prod backup**, review the
  comparison report, and know the sync recalculates live for every user.

## Model states, workspace memory, model size
- **States** - online/offline, open/closed, and **archived** (an archived model frees its memory but keeps the
  content). Deploying, archiving, and deleting a model are model-owner acts.
- **Workspace memory** - a workspace has a fixed size cap (GB); every open model consumes it. A model that
  bloats can **starve the workspace** and block other models from opening.
- **Model size** = roughly cell count = product of applied dimensions x line items. A heavily-dimensioned line
  item or a large list import can explode the cell count, spike calc time, and push the model (or workspace)
  over the limit. A **size check** is part of any big structural change or large import. **Time Ranges**,
  subsets, and sparsity are the levers that keep size down.

## Model history, rollback, and backups
- **Model history / audit** - every cell change, action run, and structural change is logged with user,
  old/new value, and timestamp. It is the record of exactly what happened and the basis for any recovery -
  scope a bad action here first.
- **Rollback / restore** - restores the **whole model** to a prior point. It reverts **everyone's** changes
  since that point, not just the mistake - blunt, not surgical. Coordinate before using it, and take a backup
  of the current state first (so a wrong rollback is itself recoverable).
- **Backups** - a model copy or export taken **before** a destructive act (bulk delete/overwrite import, prod
  ALM sync, version/list delete). Recovery from a bad sync or bulk action leans on this backup - a structure
  re-sync will **not** restore dropped data, and re-adding a deleted list member brings it back **empty**;
  only reloading data (from backup or source) restores the numbers.

Gating note: an ALM sync to prod is destructive - hard gate + named approver + prod backup + comparison-report
review + re-read the production-data flags at execute. A full-model rollback is destructive (it discards
others' work) - gate and back up first. Archiving/deleting a model is committing/destructive - confirm scope.
