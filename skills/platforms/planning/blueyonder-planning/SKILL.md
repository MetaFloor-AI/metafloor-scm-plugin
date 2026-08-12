---
name: blueyonder-planning
description: Blue Yonder Luminate Planning (heritage JDA, i2, Manugistics) - demand planning (statistical / ML
  forecast, Cognitive Demand, Demand Edge sensing), Enterprise Supply Planning (ESP) constrained master
  planning (MPS + DRP), Deployment and Recommended Shipments, multi-echelon Inventory Optimization, what-if
  scenarios vs the published / baseline plan, snapshots, and releasing planned orders to execution / ERP.
  Reads and what-if are safe; publishing a plan, releasing planned orders, and overwriting the operating plan
  are committing / destructive. Use when the connected planning system is Blue Yonder or Luminate Planning, or
  the user mentions JDA, i2, Manugistics, ESP, MPS / DRP, a demand or consensus forecast, Cognitive Demand,
  Demand Edge / demand sensing, a planned order or firm planned order (FPO), a Recommended Shipment / RecShip
  / STO, Inventory Optimization / MEIO / safety stock, SKU-Location / SKUL, a what-if scenario, publish /
  commit a plan, or a time fence / frozen zone.
---

# Blue Yonder Luminate Planning - operating it safely

Blue Yonder Luminate Planning (heritage **JDA**, and before that **i2** and **Manugistics**) is a supply-chain
**planning suite** on the Luminate Platform - it sits on top of the ERP, not as the book of record. It reads
demand history, orders, inventory and master data from source systems, recomputes forecasts and supply plans,
and can push plan output back out to execution. It is a suite, not one engine: **Demand** produces the forecast,
**Enterprise Supply Planning (ESP)** turns that forecast into a constrained supply plan and planned orders,
**Deployment** hardens near-term planned orders into Recommended Shipments, and **Inventory Optimization** sets
safety-stock targets. One rule governs the risk: **analysis in a scenario changes nothing shared; the three
promotions - publish demand to supply, publish/commit a scenario to the baseline, and release planned orders to
execution - are what move shared reality and the real world.** This skill gives the judgment to tell those apart
so the harness can gate them, plus the edge states and recovery patterns that decide whether a mistake is fixable.

## Contents
- When this applies (+ when NOT) · Object & state model · Vocabulary that bites
- Operations: read / write / destructive (the matrix + escalation rules)
- Gotchas that bite · Edge states · Reconciliation / freshness
- Recovery patterns · Guardrails · Worked example · References

## When this applies
Connected planning system is Blue Yonder / Luminate Planning and the work is demand or supply planning, scenario
analysis, deployment, inventory targets, or releasing plan output. When NOT:
- Concurrent planning in Kinaxis RapidResponse / Maestro (scenarios, commit, CTP) -> `kinaxis`.
- SAP-native planning (IBP time-series/response, S/4 MRP, PP/DS pegging) -> `sap-ibp`.
- Blue Yonder **WMS** (heritage RedPrairie) - bins, waves, tasks, LPNs, execution -> `blueyonder-wms`.
- The **ERP** order/stock postings a release lands on (create/cancel a PO, post a goods receipt, move stock).
  Once a planned order is released it lives in ERP -> `sap-mm` (the real commitment + recovery are there).

## Object & state model (reason about state, not nouns)
- **SKU-Location (SKUL)** - the planning grain: item x location/node. A quantity is meaningless without its
  location, the same way a stock figure is meaningless without a plant. Confirm the SKUL before you read or write.
- **Demand plan** - the forecast, built in stages: **statistical / ML baseline** (Cognitive Demand) -> **planner
  overrides** -> **consensus forecast** (the agreed S&OP number) -> **published to supply** (handed to ESP). Near
  term, **Demand Edge** demand sensing can override the baseline. Each stage is a different level of commitment.
- **Supply plan / Master Plan** - ESP's answer: an **unconstrained** plan (ignores limits) and a **constrained**
  plan (respects capacity, material, lead time). It nets demand against supply and generates **planned orders**.
- **Planned order lifecycle** - **planned / recommended** (an engine suggestion, re-derived or deleted every run)
  -> **firm planned order (FPO)** (a planner protected it from the engine; still only in Blue Yonder) ->
  **released** (pushed to ERP/execution, becomes a real requisition, PO, production order or transfer order/STO)
  -> **actual** (comes back from ERP as the real order). Blue Yonder owns planned and firm; ERP owns released and actual.
- **Deployment / Recommended Shipment (RecShip)** - Deployment hardens near-term planned orders into RecShips
  (stock transfer orders that move real inventory across the network). Releasing deployment moves real stock.
- **Scenario (what-if)** - a copy of the plan you edit privately. The plan recomputes inside it; nothing shared
  moves until you publish/commit it. Scenarios can nest (scenario -> scenario -> baseline).
- **Published / baseline plan** - the shared operating plan every planner, ESP, Deployment and downstream
  execution consume. Editing or running against it directly is live for everyone, with no sandbox.
- **Snapshot** - a frozen, read-only copy of measures at a point in time, used for comparison and forecast
  accuracy (waterfall / lag). A snapshot is not the live plan; reading it as live plans on stale numbers.
- **Measure / series** - a data element in the grid. **Input measures** (forecast, overrides, parameters) are
  editable; **calculated measures** (projected on-hand, netting, planned orders, accuracy) are read-only outputs
  that recompute. You never type over a calculated measure; you change the driving input and re-plan.

## Vocabulary that bites
- **Publish** - has two meanings in this suite, both committing. **Publish demand** hands the consensus forecast
  to ESP so the whole supply network re-plans on it. **Publish/commit a scenario** merges its changes into the
  baseline. Neither is "save"; both change shared reality, and there is no clean unpublish.
- **Baseline / published plan** - the shared live plan. A change here is immediate for every planner and every
  downstream run. Work in a scenario instead.
- **Scenario** - not a saved report or a snapshot. A live what-if copy that recomputes as you edit. Safe to edit
  and discard; the hazard is publishing it.
- **Planning run / batch** - the ESP solver. **Regeneration (full regen)** rebuilds the entire plan from scratch;
  **net change (NCR)** updates only what changed. A regen is heavier and can wipe unprotected manual work (below).
- **Planned order** - an engine suggestion, volatile: the next run can move or delete it. Not a commitment.
- **Firm planned order (FPO)** - protected from auto-replanning and from a regen, but still only in Blue Yonder
  until released. Firm is not released.
- **Time fence / frozen zone** - a horizon inside which the engine will not auto-create or auto-change orders:
  the **demand time fence (DTF)** freezes the forecast near term, the **planning time fence (PTF)** freezes
  supply orders. Inside the fence the plan is meant to be stable; a naive change there is ignored or needs a firm order.
- **Deployment / RecShip** - the near-term shipment recommendation (an STO). Releasing it moves real stock across nodes.
- **Consensus forecast** - the agreed demand number after collaboration/S&OP. Publishing it drives all of supply.
- **Demand sensing (Demand Edge)** - short-horizon ML that can override the statistical baseline near term; the
  near-term number and the baseline can diverge, so know which one drives which horizon.
- **Safety-stock target / service level** - an Inventory Optimization output/target, not a physical count.
  Changing it re-plans replenishment across every SKUL it touches on the next run.
- **Sourcing / BOD (Bill of Distribution)** - the network routing that decides which node/vendor supplies which
  demand. Change one and real orders re-route on the next run.
- **Pegging** - the link from a supply order to the demand it covers. Releasing without dependents can break pegging.
- **Waterfall / lag / bias / MAPE** - snapshot-based forecast-accuracy views. Reading is safe; they do not change the plan.

## Operations: read / write / destructive
Classify every operation family by what it does to state. Kinds of action, no tool names.

| Class | Blue Yonder operation families | Gate | Why |
|---|---|---|---|
| **Read** | open worksheets/workbooks, queries, dashboards (unless opening a workbook triggers a **baseline recalc** on open - then escalate to committing); view the demand plan, supply/Master Plan, planned orders, RecShips, projected on-hand, safety-stock targets, alerts/exceptions; compare scenarios; view snapshots, waterfall/lag/accuracy; run a what-if **simulation or planning run inside a private scenario**; **export to local session only** (no external system, inbox, or distribution) | always pass | no shared state change; the recompute stays inside the private scenario |
| **Write (reversible / sandboxed - private scenario only)** | create/copy a scenario; **create/save a snapshot** (a frozen read-only copy - it consumes storage but changes no plan); **inside your scenario** override the forecast, edit a parameter (safety stock, service level, lead time, lot size, min/max, sourcing/BOD), **firm/unfirm or delete a planned order**, run the solver/optimizer/deployment | confirm intent | contained to your scenario; discard it and nothing shared moved |
| **Write (committing)** | **publish the demand plan to supply**; **publish/commit a scenario to the baseline**; edit or run the solver on the **baseline directly**; **release** planned orders or RecShips to ERP/execution; commit a parameter/sourcing change to the baseline; unfirm/cancel a firm planned order on the baseline; an **export that egresses** to an external system or distribution policy | gate + human approve | promotes to the shared plan or binds ERP / moves real stock / egresses; each is real |
| **Destructive / irreversible** | any publish/commit/release on **stale or wrong** data (per the freshness rule); **release en masse** (a whole planned-order set via automation, not one reviewed line); **regeneration on the baseline** (rebuilds the shared plan, can wipe unprotected work); **overwrite / reset / restore the baseline** from a snapshot; **delete a shared scenario or snapshot** others depend on; **enable, edit or trigger a scheduled batch/automation** that auto-publishes or auto-releases | hard gate + named approver + re-read | no clean undo; downstream automation may already have acted; mass blast; recovery crosses into ERP |

**What each gate checks (so it is not hand-wavy) - two weights, not one:**
- **Sandboxed write -> confirm intent (light).** Confirm the target is a *private* scenario (not the baseline or a
  shared scenario) and the SKUL/measure is the intended one, then proceed. It changes nothing shared, so it needs
  correct scoping, not human sign-off. If the target turns out to be the baseline or a shared scenario, escalate.
- **Committing / destructive write -> human approve with impact (heavy).** Present to a human one at a time, showing
  the target (which scenario or the baseline), the affected SKULs/periods and the quantity moved, and what re-plans
  downstream. On denial or missing edit rights the action does not run. "Gate one at a time" = never batch several
  committing writes behind one approval; each shared state change is seen before the next.

**Sandbox-escalation rule (read this):** the "reversible/sandboxed" class only holds *inside a private scenario*.
The same override, firm, parameter edit or solver run performed **on the baseline directly** is live for every
planner at once - escalate it to committing. A **shared** scenario is in between: editing inside one is contained
until publish, but publishing or deleting a shared scenario affects everyone building on it - treat that publish/
delete as committing/destructive. There is no such thing as a sandboxed edit to shared data.

**Cancel / delete / unfirm escalates with the order's stage (read this):** the same verb has three risk levels by
target. Deleting or canceling a *planned* order **inside a scenario** is a sandboxed write (the next run re-derives
it anyway). **Unfirming or canceling a firm planned order on the baseline** is committing - it removes protection
and changes netting for everyone. **Canceling a released order** is an ERP action, destructive, handled under
`sap-mm`. Read the lifecycle stage before you cancel.

**Release-scope rule (read this):** a single reviewed planned-order or RecShip release is committing. A release is
**destructive** when it is triggered by automation/batch, spans a whole planned-order set rather than a reviewed
line, or where downstream ERP/execution may already have acted (per the freshness rule). When in doubt on scope,
treat it as destructive.

**Integration operations (classify by direction):** an **inbound** load into a *scenario* is a read into the plan
(safe); an inbound load that refreshes the **baseline** re-plans shared numbers (committing). An **outbound**
integration (push to ERP, message queue/IGC, distribution policy) is committing/egress and can trigger downstream
automation - gate it by direction and scope, never as a pure read. **Egress = any export or publication that reaches
another system, a user inbox, or a distribution/subscription list** (auto-distributed reports and scheduled
publications count); only an export that stays in your local session is a pure read.

**Freshness-default rule (read this):** the line between committing and destructive turns on data freshness, which
you must verify, not assume. **If you cannot confirm freshness** - last ERP/source sync current AND the scenario's
parent unchanged since you forked - treat any publish / commit / release as **destructive**: hard gate, named
approver, re-read. Do not publish on unverifiable data.

Universal rules to teach: **work in a scenario, not the baseline**; read the plan and re-read the driving data at
execute (the plan recomputes and ERP drifts); verify data freshness (last integration/sync) before any publish or
release; never twist a single parameter to force one number - it ripples across every SKUL on the next run; a
released order is an ERP object, gate its cancellation there; an export that feeds an external system or a
distribution policy is egress, not a pure read - gate it accordingly; **after a write on shared data, re-read the
measure to confirm it persisted** - role/permission can silently suppress an edit that the grid appeared to accept.

## Gotchas that bite (the real set - causal chains)
1. **A scenario is a sandbox until publish/commit.** Overrides, parameter edits and solver runs inside it simulate and recompute but change nothing shared; discard the scenario and it all reverts. The risk begins at publish, not at the edit. See `references/plan-lifecycle-and-publish.md`.
2. **Publishing a scenario to the baseline overwrites the shared plan.** Every planner, ESP and Deployment now plan on your change and downstream execution acts on it. There is no clean unpublish - you undo only by publishing offsetting changes, and automation may already have moved.
3. **Publishing the demand plan is a separate promotion that drives all of supply.** A bad consensus forecast published to ESP re-plans the whole network's supply and deployment on the next run - the blast radius is every SKUL that forecast touches, not one line.
4. **A planning run (regen or net-change) on the live baseline is effectively a publish.** It recomputes the shared numbers in place. Run the solver in a scenario; running it on the baseline moves the shared plan.
5. **A full regeneration rebuilds the entire plan and can wipe unprotected manual work.** Firm planned orders and changes protected by a time fence survive; ad-hoc overrides that are not firmed can be blown away. Prefer net-change for incremental work; know what a regen will discard before you run it. See `references/plan-lifecycle-and-publish.md`.
6. **Releasing planned orders or RecShips turns theory into real orders.** They become requisitions, POs, production orders or STOs in ERP/execution, and RecShips move physical stock across nodes. Canceling one is now an ERP action with vendor and commitment consequences, not a Blue Yonder undo.
7. **A planned order is a suggestion the next run re-plans or deletes.** Firming (FPO) protects it from auto-replanning and regen, but firmed is still only in Blue Yonder - it is not released. Do not treat "firmed" as "on order".
8. **The planning grain is SKU-Location.** A quantity without its location/node is meaningless; reading or writing the wrong SKUL touches the wrong node and mis-states the plan there.
9. **A time fence freezes a horizon.** Inside the demand or planning time fence the engine will not auto-change orders; a naive edit there is ignored or silently overridden by the next run unless you firm the order. Do not assume a near-term change stuck just because you typed it.
10. **Parameter changes ripple across every SKUL on the next run.** Safety stock, service level, lead time, lot size, min/max and sourcing are not local edits - they change what the *next* solver run produces network-wide. Make the change in a scenario, run it, quantify the delta, then gate the publish.
11. **Calculated measures are outputs, not inputs.** You cannot fix a projected-shortage number by typing over it; you change the driving data (forecast, supply, lead time) and let the plan recompute. Editing the wrong measure does nothing or edits the wrong thing.
12. **A forecast override that smooths a real signal misleads the whole plan.** Erasing a genuine demand spike or hiding a shortage into the consensus number propagates to supply. Flag it; do not smooth it into the baseline.
13. **The unconstrained plan ignores capacity and material limits.** Releasing off the unconstrained plan promises what you cannot build. Reason and release off the constrained plan; the two can differ materially.
14. **Concurrent planning and scheduled batch make your read stale (TOCTOU).** Another planner or a nightly batch can move the baseline between when you read and when you publish. Re-read and re-diff the baseline at publish; if it moved, stop - **re-fork from the current baseline, re-apply your changes, and re-seek approval** rather than publishing your scenario over the top. Two publishes to the baseline should serialize; if a concurrent publish is detected, queue behind it and re-diff.
15. **Deployment hardens near-term planned orders into RecShips that move stock.** Releasing deployment is not a paper step - it creates STOs that ship real inventory between nodes. Size it before releasing.
16. **A snapshot is a frozen copy, not the live plan.** Snapshots feed waterfall/lag accuracy comparisons; treating a snapshot value as current plans on numbers that have since moved.
17. **Releasing only the orders in your current filter can release a subset and break pegging.** Dependent supply and downstream orders may be left out, leaving an unbalanced plan in ERP. Release with dependents and confirm the release set is complete, not just what is on screen.
18. **Changing sourcing / BOD re-routes which node or vendor covers which demand.** Commit it and real orders re-route to a different plant or supplier on the next run - a silent change to the physical supply path.
19. **Blue Yonder is a plan, not the book of record.** Inventory and order truth live in ERP; a Blue Yonder figure can be stale relative to the last sync. Re-sync/re-read before you release, or you release off a stale on-hand.
20. **Publish/commit can feed automation.** A scheduled integration or batch can release orders to ERP with no further human step - know what your publish sets in motion before you publish.
21. **Deleting a shared scenario or snapshot destroys others' work or the audit baseline.** There is no recycle bin for the analysis, and a deleted snapshot breaks the accuracy history. A private scenario is yours to discard; a shared one is not.
22. **Reset/restore of the baseline from a snapshot overwrites the current live plan.** A "restore" is not a safe rollback - it replaces every planner's current plan with the snapshot; treat it as destructive.
23. **A firm planned order left stale holds phantom demand or supply.** A firmed order no longer needed will not be cleaned up by the engine; it distorts netting until you unfirm it.
24. **A change the UI accepted may not have committed.** Role/permission can silently suppress an edit or publish on shared data - it looks applied on screen but did not take. Confirm it committed (and that you had edit rights), or you plan on a change that is not there.
25. **Demand sensing can diverge from the statistical baseline near term.** Demand Edge overrides the near horizon; if you reason off the baseline while sensing drives the near term, your supply signal and the sensed demand disagree. Know which number owns which horizon.

## Edge states & special cases
- **Two publishes, different blast radius** - publish-demand-to-supply re-plans the whole supply network off the
  forecast; publish-scenario-to-baseline merges plan changes into the shared plan. Both committing; know which one you are doing.
- **Regen vs net-change** - a net-change run is incremental and light; a full regen rebuilds everything and can
  discard unprotected work. Never run a regen on the baseline casually.
- **Constrained vs unconstrained** - the same SKUL shows two supply answers; the unconstrained one is aspirational.
  Release only against the constrained plan.
- **Scenario nesting** - scenarios can nest (scenario -> scenario -> baseline). A publish's blast radius depends on
  where it lands: into a child scenario it is contained; into the baseline it is shared with everyone. Know the parent and depth.
- **Time fence interaction** - a change inside the demand/planning time fence needs a firm order to stick; a regen
  respects firm orders and time fences but re-derives everything outside them.
- **Firmed vs released vs actual** - three "not just planned" states with three owners (planner-in-BY,
  ERP-after-release, ERP-record). Never conflate them.
- **Roles and permissions** - scenario and baseline access is role-based (view / edit / admin). A role can silently
  block an edit (it looks applied but did not publish) or silently allow one on shared data. Confirm edit rights on
  the target before relying on a change.
- **Scheduled batch window** - during a batch or inbound sync the plan is mid-refresh; a publish read across that
  window can mix pre- and post-run numbers. Publish outside the batch window or re-read after it completes.

## Reconciliation / freshness
- The plan can be stale two ways: relative to **ERP/source** (last inbound sync) and relative to **itself** (a
  scenario inheriting a moved parent, or a baseline shifted by a scheduled batch). Check both before a publish.
- At execute time, re-read the driving data and the last integration timestamp; do not publish or release off
  numbers read minutes ago, and re-diff the baseline to catch a concurrent change.
- When Blue Yonder and ERP disagree on on-hand or order status, ERP is the record - reconcile before releasing, or
  the released order is built on a plan-side figure ERP will reject or double.

## Recovery patterns (can it be undone, and what cannot)
- **Discard a private scenario** - clean revert of everything inside it, because nothing was published. This is the
  safety net; use scenarios so mistakes stay discardable.
- **"Unpublish" a baseline change** - there is no clean unpublish. You correct a bad publish by making offsetting
  changes in a new scenario and publishing again, and any automation that already fired off the bad plan is unwound separately.
- **Released to ERP/execution (the common bad case)** - not a Blue Yonder undo. Steps: (1) identify exactly which
  orders/RecShips released, including dependents (the full release set); (2) check ERP status of each - a still-
  planned requisition or unshipped STO is cheaper to cancel than a released PO already sent to a vendor; (3) stop or
  pause any batch/automation that would re-release on the next run; (4) cancel/withdraw the erroneous orders in ERP
  under `sap-mm` gating (each cancel is its own committing/destructive ERP action); (5) correct the driving
  plan data in a scenario so the next legitimate run does not re-release the same error. A fast first move before a
  full cancel is to place a **hold/block** on the released order in ERP (a PO hold or delivery block freezes
  execution faster than a cancel and buys time). The time tiers set the urgency:
  - **Within minutes** - a still-planned requisition or an unreleased STO may cancel unnoticed; act fast, system-only.
  - **After hours** - a released PO may already be transmitted to the vendor; now it needs vendor communication, not just a system cancel.
  - **Once shipped** - a released STO's stock may already be moving; recovery is a physical/logistics reversal, not a cancel.
- **Overwritten / regenerated baseline** - restore from a snapshot if one exists (itself a destructive overwrite of
  the current plan - gate it), otherwise rebuild via offsetting changes. Prevention (work in a scenario, firm what
  matters, prefer net-change) is far cheaper than recovery.
- **Bad consensus forecast already published to supply** - cannot be unpublished; correct the forecast in a scenario,
  re-publish, and let the next supply run re-plan on the corrected number.

## Guardrails
- Do the work in a private scenario, not the baseline; keep mistakes discardable.
- Confirm the SKU-Location before reading or writing a number - a quantity without its node is meaningless.
- Verify data freshness (last ERP/source sync and any moved parent or batch) before any publish or release.
- Treat publish-demand-to-supply, publish/commit-to-baseline, and release-to-ERP as committing - gate, human
  approve, re-read the driving data at execute, and quantify the delta (which SKULs/periods, quantity moved, what re-plans).
- Never twist a safety-stock, service-level, lead-time or lot-size parameter to force one number - it ripples across
  every SKUL on the next run. Never run a regen on the baseline casually. Never release off the unconstrained plan.
- Anything in the destructive row (release to ERP, baseline overwrite/regen/restore, delete a shared scenario/snapshot,
  scheduled auto-publish): named approver, re-read, and log the reason.

## Worked example (a safe cycle, and where undo stops being free)
A planner must add 5,000 units of demand for SKU A at DC-East for a promotion. Safe path: (1) create a **private
scenario** off the baseline; (2) raise the consensus forecast by 5,000 at that SKUL there and run **net-change** -
projected on-hand, planned orders and RecShips recompute **inside the scenario only**; (3) verify freshness - last
ERP sync current AND the parent unchanged since the fork, and re-diff the baseline for concurrent edits; (4) after
human approval, **publish the demand to supply** so ESP re-plans, then **publish the scenario to the baseline**
(now shared for every planner); (5) **release** the resulting planned orders and RecShips to execution with
dependents, confirming the release set is complete. Undo cost climbs at each step: discard the scenario at step 2
and nothing shared moved; after step 4 you can only correct with an offsetting publish; after step 5 the orders are
real ERP/execution objects and a RecShip may already be shipping - unwinding is an ERP cancel under
`sap-mm`. This is why the work happens in a scenario and freshness is checked before the publish, not after.

## References (load on demand)
- `references/plan-lifecycle-and-publish.md` - the scenario/baseline/snapshot model, the two publishes (demand->supply
  and scenario->baseline), planning-run modes (regeneration vs net-change), time fences, deployment/RecShips, releasing
  to ERP, and scheduled batch/automation.
- `references/demand-supply-and-parameters.md` - the demand build (statistical/consensus/demand sensing), ESP
  constrained vs unconstrained planning, multi-echelon Inventory Optimization (safety stock/service level), sourcing/BOD,
  pegging, measures/series (input vs calculated), and why a parameter change ripples network-wide.
