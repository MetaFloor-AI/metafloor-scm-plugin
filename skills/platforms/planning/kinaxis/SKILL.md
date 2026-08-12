---
name: kinaxis
description: Kinaxis RapidResponse / Maestro concurrent supply-chain planning (APS) - scenarios vs the
  baseline plan, planned / firmed / released orders, commit and publish, capable-to-promise, worksheets,
  constraints, netting, and alerts. Reads, simulations and what-if analysis are safe and reversible; commit,
  publish and release are the high-consequence, gated actions - they promote changes into the shared plan
  and can release orders to ERP. Use when the connected planning system is Kinaxis, or the user mentions
  RapidResponse, Maestro, a scenario, commit or publish a plan, releasing or firming planned orders,
  capable-to-promise or CTP / ATP, available-to-promise, a worksheet or workbook, netting, a constraint,
  sourcing / substitution, or a planning alert.
---

# Kinaxis RapidResponse / Maestro - operating it safely

Kinaxis RapidResponse (rebranded Maestro) is a concurrent supply-chain planning platform - an analytics and
planning layer that sits on top of the ERP, not the book of record. It reads demand, supply, inventory and
orders from source systems (SAP, Oracle), recomputes the plan continuously as data changes, and can push
plan output back out. One rule governs its risk: **analysis in a scenario changes nothing shared; commit and
publish are what promote changes into the baseline and release orders to ERP.** Reads, simulations and what-if edits are cheap and reversible. Commit and
publish are where a plan becomes shared reality and where planned orders become real purchase requisitions,
POs and production orders. This skill gives the judgment to tell those apart so the harness can gate them.

## Contents
- When this applies (+ when NOT) · Object & state model · Vocabulary that bites
- Operations: read / write / destructive (the matrix + escalation rules)
- Gotchas that bite · Edge states · Reconciliation / freshness
- Recovery patterns · Guardrails · Worked example · References

## When this applies
Connected planning system is Kinaxis and the work is demand/supply planning, scenario analysis, promising, or
releasing plan output. When NOT:
- ERP order or stock postings - create/cancel a PO, post a goods receipt, move or value inventory. Once an
  order is released it lives in ERP -> `sap-mm` (the real commitment and its recovery are there).
- SAP-native planning (IBP time-series/response, SAP MRP, S/4 pegging) -> `sap-ibp`.
- Ledger/finance postings -> `sap-fi`.

## Object & state model (reason about state, not nouns)
- **Baseline (root scenario)** - the shared operating plan every planner sees, often named "Enterprise Data"
  or "Actual". Editing it is live for everyone, with no sandbox.
- **Scenario** - a what-if overlay of a parent scenario. It stores only the **deltas** from its parent
  (copy-on-write), so it is cheap to spin up and it inherits later changes to the parent. Private (yours) or
  public (shared). The plan recomputes inside it concurrently as you edit. A scenario changes nothing shared
  until commit.
- **Order lifecycle** - **planned** (engine suggestion, re-planned or deleted every run) -> **firmed** (a
  planner protected it from the engine; still only in Kinaxis) -> **released / published** (pushed to ERP,
  becomes a req / PO / production order) -> **actual / confirmed** (comes back from ERP as the real order).
  Kinaxis owns planned and firmed; ERP owns released and actual.
- **Data model objects** - a worksheet cell maps to a specific object: **Part** (item/site), **Demand**
  (independent forecast/sales order, or dependent from a BOM), **Supply** (scheduled receipts, planned and
  actual orders), **OnHand** (inventory), **Order** (planned/firmed/released), plus BOM, sourcing and
  constraint records. Know which object a cell is before you edit it - the object type decides what the edit
  re-plans.
- **Data vs analytics** - **data** is editable input (demand, supply, lead time, constraints). **Analytics**
  are calculated outputs (netting, projected on-hand, ATP/CTP results, alerts, metrics). Analytics are
  read-only and recompute; you never type over an analytic, you change the driving data.
- **Planning engine** - the always-on engine re-plans (nets demand/supply, regenerates planned orders) as
  data changes, per scenario. A re-plan **inside a scenario** recomputes only that scenario (safe); a re-plan
  or engine change against the **baseline** moves the shared plan (committing).
- **System boundary** - Kinaxis = the plan and analytics; ERP = system of record for inventory and orders.
  They sync via integration and can drift; a Kinaxis number can be stale relative to ERP.

## Vocabulary that bites
- **Scenario** - not a saved report or a snapshot. A live what-if that stores only deltas from its parent and
  recomputes continuously. Safe to edit; the hazard is committing it.
- **Baseline / Enterprise / Actual** - the shared root scenario. A change here is immediate for every planner.
- **Commit** - not "save". It merges your scenario's deltas **up** into its parent. Commit to the baseline =
  change shared reality. There is no clean "uncommit".
- **Publish / release** - pushes plan output **out** to ERP, where planned orders become real reqs / POs /
  production orders. The real-world event (money, materials, capacity). In some deployments these are two
  steps (publish = hand to the integration layer; release = create the ERP document); treat both as
  committing, and check which one actually creates the ERP order.
- **Planned order** - an engine suggestion, volatile: the next planning run can move or delete it. Not a
  commitment.
- **Firm(ed) planned order** - protected from the engine's auto-replanning, but still only in Kinaxis until
  released. Firm is not released.
- **Worksheet / workbook** - a configured, often editable grid over the data model; every edit lands in the
  **active scenario**. A workbook groups worksheets. Which scenario is active decides what an edit touches.
- **ATP vs CTP** - available-to-promise checks existing/planned supply; **capable-to-promise** simulates
  pulling constrained capacity and material to promise a date. CTP is only as true as the constraint data.
- **Constraint** - a capacity, supply or lead-time limit that drives constrained planning and CTP. Overriding
  one changes the plan's feasibility on screen, not the real world.
- **Netting / allocation / sourcing / substitution** - the rules that decide which supply covers which
  demand. Changing one re-plans real coverage, silently.
- **Alert / metric** - a computed exception (shortage, late order, constraint violation) or KPI. Reading is
  safe; acting on it via commit or release is not.

## Operations: read / write / destructive
Classify every operation family by what it does to state. Kinds of action, no tool names.

| Class | Kinaxis operation families | Gate | Why |
|---|---|---|---|
| **Read** | open/run worksheets, workbooks, queries; view metrics, scorecards, projected on-hand; filter alerts/exceptions; compare scenarios; run a what-if **simulation or engine re-plan inside a scenario**; an ATP/CTP **inquiry** that only checks (reserves nothing); export data to a local session | always pass | no shared state change; the recompute stays inside the scenario |
| **Write (reversible / sandboxed - private scenario only)** | create a scenario; edit data **inside your private scenario** - adjust demand/supply, change a planned order, override a lead time or constraint, change sourcing/substitution, **firm** a planned order | gate one at a time | contained to your scenario; discard it and nothing shared moved |
| **Write (committing)** | **commit** a scenario to its parent/baseline; edit or re-plan the **baseline/Actual directly**; **publish/release** planned orders to ERP; **commit** a sourcing-rule or substitution change; an **export that egresses** to an external system or data-distribution policy; **confirm** a CTP/ATP promise on a customer order (reserves supply/capacity); run/trigger an automation chain that commits or publishes | gate + human approve | promotes changes to the shared plan or binds ERP / a customer / egress; each is real |
| **Destructive / irreversible** | commit or publish on **stale or wrong** baseline/ERP/constraint data (per the freshness-default rule); **release** planned orders to ERP (they become real reqs/POs - undo is now an ERP cancel); overwrite the baseline with a bad commit; **override a constraint and commit** (relaxes a real limit); **delete a shared/public scenario** others depend on; a scheduled auto-commit/publish that **releases en masse** (the whole planned-order set, not one line) | hard gate + named approver + re-read | no clean uncommit; downstream automation may already have acted; mass blast; recovery crosses into ERP |

**Sandbox-escalation rule (read this):** the "reversible/sandboxed" class only holds *inside a private
scenario*. The same edit, firm or re-plan performed **directly on the baseline/Actual** is live for every
planner at once - escalate it to committing. There is no such thing as a sandboxed edit to shared data.

**Freshness-default rule (read this):** the line between committing and destructive turns on data freshness,
which you must verify, not assume. **If you cannot confirm freshness** - last ERP sync current AND the
scenario's parent unchanged since you forked - treat any commit / publish / release as **destructive**: hard
gate, named approver, re-read. Do not commit on unverifiable data.

Universal rules to teach: "gate one at a time" = present each write for individual human approval, not
batched, so each state change is seen before the next; **work in a scenario, not the baseline**; read the
plan and re-read the underlying data at execute (the plan recomputes and ERP drifts); verify data freshness (last integration/sync) before
any commit or publish; a CTP confirm is a promise, not a query; never override a constraint to make a plan
look feasible; a released order is an ERP object, gate its cancellation there; an export that feeds an
external system or a data-distribution policy is egress, not a pure read - gate it accordingly.

## Gotchas that bite (the real set - causal chains)
1. **A scenario is a sandbox until commit.** Edits inside it simulate and recompute but change nothing shared; discard the scenario and everything in it reverts. The risk begins at commit/publish, not at the edit. See `references/scenarios-and-commit.md`.
2. **Scenarios store only deltas from their parent,** so a scenario silently inherits later changes to that parent - your what-if sits on a moving baseline, and a number you never touched can shift under you. Re-check the parent before you commit.
3. **Committing merges your deltas up into the parent.** Commit to the baseline and every planner now plans on your change and downstream automation acts on it. There is no clean "uncommit" - you undo only by posting offsetting changes, and the automation may already have moved.
4. **Editing the baseline (Enterprise/Actual) directly skips the sandbox** - the change is live for every planner at once. Work in a private scenario and commit deliberately instead of hand-editing shared data.
5. **Publishing/releasing planned orders pushes them to ERP,** where they become real purchase requisitions, POs or production orders - the real-world commitment. Canceling one is now an ERP action with vendor and commitment consequences, not a Kinaxis undo.
6. **A planned order is a suggestion the engine will re-plan or delete on the next run.** Firming protects it from auto-replanning, but firmed is still only in Kinaxis - it is not released. Do not treat "firmed" as "on order".
7. **CTP is only as good as the constraint data** - capacity, supplier capability, material availability, lead times. Stale constraints make CTP promise a date you cannot hit, and that promise leaks straight onto the customer order. See `references/ctp-and-constraints.md`.
8. **A CTP confirm reserves constrained supply and capacity;** an aggressive confirm can allocate capacity away from other orders. A pure ATP/CTP inquiry is a safe read; a confirm is committing.
9. **Analytics are calculated, not editable.** You cannot fix a projected-shortage number by typing over it - you change the driving data (demand, supply, lead time) and let it recompute. Editing the wrong cell does nothing or edits the wrong thing.
10. **Concurrent planning means others edit the same shared data.** Two planners committing overlapping changes collide; keep work in your own private scenario and commit deliberately rather than editing shared data others are live in.
11. **Kinaxis is a plan, not the book of record.** Inventory and order truth live in ERP; a Kinaxis figure can be stale relative to the last sync. Re-read/re-sync before you release, or you release off a stale on-hand.
12. **Commit/publish can feed automation.** A scheduled integration or automation chain can release orders downstream with no further human step - know what your commit sets in motion before you commit.
13. **Firming freezes an order against the engine and against re-optimization.** A firmed order that is no longer needed will not be cleaned up automatically; it holds phantom demand or supply until you unfirm it.
14. **Overriding a constraint makes the plan look feasible without changing the real world.** Raise a capacity or shorten a lead time, commit it, and every CTP promise built on it is built on capacity you do not have.
15. **Changing a sourcing rule or substitution silently re-plans which supply covers which demand.** Commit that and you have re-routed real orders to a different plant, vendor or material.
16. **Deleting a shared/public scenario destroys everyone's uncommitted work in it.** There is no recycle bin for the analysis. A private scenario is yours to discard; a public one is shared - do not delete it.
17. **A scenario built on a stale or wrong parent commits a bad plan.** The plan is only as good as the baseline it forked from; verify the last integration/sync timestamp before committing or publishing.
18. **The always-on recompute means a metric you read a moment ago may already have moved.** For a commit or release decision, read the value at the moment you act, not the number you saw earlier.
19. **Releasing only the orders in your current worksheet filter can release a subset** and miss dependent orders, leaving an unbalanced plan in ERP. Use a dependency-aware release (release with dependents) and confirm the release set is complete, not just what is on screen.
20. **You do not firm or delete an actual (ERP) order inside Kinaxis.** Actuals come from ERP; change the plan and let a release send the correction to ERP, rather than editing the actual in the planning layer.
21. **A change the UI accepted may not have committed.** The permission model can silently suppress an edit or commit on shared data - it looks applied on screen but did not take. Do not assume a change landed because the grid accepted it; confirm it committed (and that you had edit rights), or you plan on a change that is not there.

## Edge states & special cases
- **Private vs public scenario** - private is yours to edit and discard freely; public is shared, others build on it, and deleting or committing it affects them.
- **Scenario nesting / baseline as parent** - scenarios can nest (scenario -> scenario -> baseline). A commit's blast radius depends on where it lands: into a child scenario it is contained one level up; into the baseline it is shared with every planner. Know your scenario's parent and depth before committing.
- **Firmed vs released vs actual** - three different "not just planned" states with three different owners (planner-in-Kinaxis, ERP-after-release, ERP-record). Never conflate them.
- **Constraint override in a scenario** - useful for what-if ("what if we add a shift"); dangerous once committed, because the plan now assumes capacity that does not exist.
- **Automation chain / scheduled task** - can commit and publish on a timer; editing or triggering one can release many orders at once. Treat it as a committing/destructive action.
- **Data-integration windows** - during an inbound sync the plan is mid-refresh; a commit read across that window can mix pre- and post-sync numbers.
- **Roles and permissions** - scenario access is role-based (view / edit / admin). A role can silently block an edit (it looks applied but is not committed) or silently allow one on shared data; a "private" scenario may still be visible to an admin. Confirm you have edit rights on the target scenario before relying on a change.
- **Commit merge conflict** - a commit can fail or need re-merge when the parent changed since you forked. That is the model protecting you from overwriting someone else's committed change. Procedure: re-read the parent -> diff your deltas against the new parent -> confirm your change still expresses the intended plan -> re-commit. Do not force past a conflict blindly.

## Reconciliation / freshness
- The plan can be stale two ways: relative to **ERP** (last inbound sync) and relative to **itself** (a scenario inheriting a changed parent). Check both before a commit.
- At execute time, re-read the driving data and the last integration timestamp; do not commit or release off numbers read minutes ago.
- When Kinaxis and ERP disagree on on-hand or order status, ERP is the record - reconcile before releasing, or the released order is built on a plan-side figure that ERP will reject or double.

## Recovery patterns (can it be undone, and what cannot)
- **Discard a private scenario** - clean revert of everything inside it, because nothing was committed. This is the safety net; use scenarios so mistakes stay discardable.
- **"Uncommit"** - there is no clean uncommit. You correct a bad commit by posting offsetting changes in a new scenario and committing again, and any automation that already fired off the bad commit has to be unwound separately.
- **Released to ERP (the common bad case)** - not a Kinaxis undo. First steps: (1) identify exactly which orders released, including dependents (the full release set); (2) check ERP status of each - a req/planned order is cheaper to cancel than a released PO already sent to a vendor; (3) stop or pause any automation chain that would re-release on the next run; (4) cancel/withdraw the erroneous orders in ERP under `sap-mm` gating (each cancel is its own committing/destructive ERP action); (5) correct the driving plan data in a scenario so the next legitimate run does not re-release the same error. Act fast, and read the time tiers: within minutes a still-planned requisition may cancel without the vendor knowing; after hours a released PO may already be transmitted to the vendor and now needs vendor communication, not just a system cancel.
- **Bad CTP promise already sent** - cannot be unsent; re-promise with corrected constraints and manage the customer commitment.
- **Overwritten baseline** - restore from a scenario snapshot/backup if one exists, otherwise an offsetting commit. Prevention (work in a scenario) is far cheaper than recovery.

## Guardrails
- Do the work in a private scenario, not the baseline; keep mistakes discardable.
- Verify data freshness (last ERP integration/sync and any inherited parent change) before any commit or publish.
- Treat commit-to-baseline, publish/release-to-ERP, and a CTP confirm as committing actions - gate, human approve, and re-read the underlying data at execute.
- Never override a constraint to make a plan feasible, and never commit a plan built on a constraint override without saying so.
- Do not delete a shared/public scenario; confirm the full release set before publishing; know what automation a commit triggers.
- Anything in the destructive row (release to ERP, overwrite baseline, delete a shared scenario, scheduled auto-publish): named approver, re-read, and log the reason.

## Worked example (a safe cycle, and where undo stops being free)
A planner must pull in 500 units of Part A for a new order. Safe path: (1) create a **private scenario** off
the baseline; (2) raise demand by 500 units there and run the re-plan - projected on-hand, CTP and alerts
recompute **inside the scenario only**; (3) verify freshness - last ERP sync current AND the parent unchanged
since the fork; (4) after human approval, **commit** to the baseline (now shared for every planner); (5)
**release** the resulting 12 planned orders to ERP with dependents, confirming the release set is complete.
Undo cost climbs at each step: discard the scenario at step 2 and nothing shared moved; after step 4 you can
only correct with an offsetting commit; after step 5 the 12 orders are real ERP reqs and unwinding is an ERP
cancel under `sap-mm`. This is why the work happens in a scenario and freshness is checked before
the commit, not after.

## References (load on demand)
- `references/scenarios-and-commit.md` - the scenario data model (copy-on-write deltas, parent inheritance, private vs public, the baseline), commit semantics (merge up, no uncommit), publish/release to ERP, and automation chains.
- `references/ctp-and-constraints.md` - ATP vs CTP, constraint types (capacity/supply/lead time), how CTP simulates a promise, why freshness matters, promise leakage, and netting/allocation/sourcing/substitution.
