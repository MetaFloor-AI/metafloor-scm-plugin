---
name: blueyonder-wms
description: "Blue Yonder Warehouse Management (heritage RedPrairie DLx / JDA WMS; the MOCA- and policy-driven WMS, on-prem or cloud-native Luminate) - safe operation of warehouse execution and on-hand inventory: available vs on-hand, ILPN (inbound license plate) and OLPN (outbound carton), locations and zones, wave / waveless release (allocates + generates task work), allocation, directed RF task work (pick / put-away / replenishment / cycle-count; task confirm posts the inventory move), receiving / ASN, pack / load / ship confirm, inventory adjustment and status holds, labor, and host / ERP integration. Use when the warehouse system is Blue Yonder WMS (or RedPrairie, JDA WMS, DLx, Luminate Warehouse) and the work touches on-hand, an ILPN or OLPN, a wave or waveless release, a task or directed work, allocation, a cycle count, an inventory adjustment or hold, receiving, pick / pack / ship, a MOCA command or a policy (poltype / polvalue), catch weight, or a goods movement published to the ERP."
---

# Blue Yonder WMS - operating it safely

Blue Yonder Warehouse Management (the current cloud-native / Luminate product; heritage **RedPrairie DLx**
and then **JDA WMS**) runs warehouse execution: receiving, put-away, storage, allocation, picking, packing,
and shipping. It is the **system of record for on-hand** inside the four walls; the ERP/host does not know
where a unit physically sits, so Blue Yonder publishes each movement back and the host posts the matching
goods movement and often a value document. Three facts make it dangerous. First, most writes move physical
stock and the moment of movement is **task confirmation** (usually an RF-directed task), not planning.
Second, an **inventory adjustment writes the book directly with no offsetting document** - it overwrites
on-hand, so a mistake is a real loss or a phantom, not a reversible entry. Third, behavior is **policy- and
MOCA-driven**: a policy change re-shapes how every wave allocates or how tasks direct, warehouse-wide, and a
hand-run MOCA command writes past the checks the RF flow enforces. This skill classifies each action so the
harness can gate it, plus the edge states and recovery paths that decide if a mistake is fixable.

## Contents
- When this applies / when NOT
- Object & state model
- Vocabulary that bites
- Operations: read / write / destructive matrix
- Gotchas that bite (the causal chains)
- Edge states & special cases
- Freshness & reconciliation
- Recovery patterns
- Guardrails
- References

## When this applies / when NOT
Warehouse system is Blue Yonder WMS (RedPrairie / JDA / DLx / Luminate Warehouse) and the work is execution
or on-hand inside the DC. When NOT:
- **Manhattan** Active WM / WMS / SCALE warehouse execution -> `manhattan-wms`. Same object model
  (LPN, wave, task, allocation) but different vocabulary and internals: Manhattan has no MOCA/policy engine,
  uses a single generic LPN rather than the **ILPN / OLPN** split, and (Active WM) streams orders where Blue
  Yonder is wave-centric. Do not apply Blue Yonder policy or MOCA logic to a Manhattan site, or vice versa.
- **SAP EWM** warehouse execution (storage bins, handling units / HUs, `/SCWM/` transactions, EWM warehouse
  tasks and warehouse orders) -> `sap-ewm`.
- ERP inventory **valuation**, movement types, GR/IR, financial postings and period close -> `sap-mm`
  (Blue Yonder triggers those host postings; it does not own the ledger).
- **Blue Yonder planning** - forecast, supply/deployment planning, inventory optimization, releasing planned
  orders -> `blueyonder-planning`. Same vendor, different suite: planning decides *what/when to
  move*; this WMS *executes and records* the physical move. Do not confuse a planned/deployment order with a
  warehouse task.
- **WMS administration / setup** - user and role management, warehouse / location / item master
  configuration, and authoring policies as an admin project - is a different risk domain (config blast radius,
  not a live stock move) with its own change-control and recovery. This skill covers operational execution; a
  policy touched *during operations* is still gated as change-control (see the matrix).

Modern vs legacy: the cloud-native line adds **waveless / continuous flow** and near-real-time host events.
The on-prem RedPrairie/JDA line is **wave-centric** with batch/interface host integration, so do not assume
real-time publishing or waveless behavior on a legacy DLx deployment.

## Object & state model (reason about state, not nouns)
- **Inventory / on-hand** - quantity of an **item** at a **location**, carried on an **LPN**, qualified by
  **inventory attributes** (lot, serial, expiry, country of origin, and for food/grocery a **catch weight**)
  and an **inventory status** (available, hold, QC, damage). The same physical quantity is not equally
  usable; **available** is derived, not raw on-hand (formula below).
- **ILPN (inbound license plate)** - the container built at receiving (pallet, carton, tote). **OLPN
  (outbound license plate / shipping carton)** - the container built at pack/put-wall for shipping. LPNs
  **nest** (a pallet ILPN holds case LPNs); moving a parent moves every child and its inventory. Confusing an
  ILPN with an OLPN mis-routes a container between the inbound and outbound flow.
- **Location** - a physical slot. Types: receiving/dock, reserve (bulk storage), active / forward pick,
  case-pick, staging, ship dock. Grouped into **zones** / areas for work and task routing.
- **Inbound: ASN / PO receipt** - an ASN (Advance Ship Notice) is the expected inbound against a PO.
  Receiving confirms it into an ILPN in a receiving location. States: expected -> received -> put-away.
- **Order (shipment / distribution order)** - demand to fulfil. States: created -> allocated -> in-pick ->
  packed -> staged -> loaded -> shipped. A **work order** covers kitting / value-added service (VAS).
- **Wave / wave template** - a batch of order lines released together for allocation and work creation.
  States: planned -> released (allocated + task work generated) -> in progress -> complete. **Waveless flow**
  (cloud) is the continuous alternative that allocates and generates work as orders arrive, with no discrete
  wave to hold.
- **Allocation** - the reservation of specific on-hand (location + LPN + attributes) to an order line. A hard
  allocation commits that stock; it is still physically present but no longer available to others.
- **Task / directed work** - the unit of labor, usually **RF-directed** (radio terminal). Types: pick,
  put-away, replenishment, cycle count, pack, load. States: ready -> in progress -> confirmed (or short /
  cancelled). **Confirming a task posts the inventory move.**
- **Inventory adjustment** - a direct write to on-hand (quantity or status) under a reason code, with no
  offsetting document. It is the book, corrected by fiat.
- **Policy (poltype / polvalue) + MOCA** - Blue Yonder behavior is configured as **policies** and executed
  through **MOCA** commands. A policy is warehouse-wide config, not per-order data; MOCA is the command layer
  under every operation. Both are levers that change or bypass the rules the rest of this skill relies on.

## Vocabulary that bites
(Each term is only named here; its causal chain is in Gotchas below.)
- **Available vs on-hand** - `available = on-hand - allocated - non-available (hold / QC / damage)`. "On-hand"
  is everything in the building; only *available* can be promised. Read the status split, not just the total.
  Here *allocated* covers both order-line reservations and move-task reservations, so in-transit stock on an
  unconfirmed task is already netted out; do not add it back as available at the source or count it as
  available at the destination before the task confirms. Hold, QC, and damage are all just **non-available
  statuses** - the general form is `available = on-hand - allocated - (everything not in an available
  status)`, so do not double-subtract and do not assume the only non-available statuses are those three.
- **ILPN / OLPN** - inbound license plate vs outbound shipping carton. Both nest; an operation on a parent
  cascades to every child LPN.
- **Task confirmation** - the write that actually moves stock. Before confirm an RF-directed pick/put-away is
  only planned and the source location still shows the quantity. The book changes at confirm, not at release.
- **Wave release** - not a report run. Release **allocates** on-hand to the released orders and **generates
  task work**; committed stock leaves the available pool for everyone else.
- **Waveless flow** - continuous release (cloud). Allocation commits the instant an order flows in; there is
  no wave sitting in planned that you can hold to reprioritize.
- **Allocation / de-allocation** - reserve / un-reserve stock. De-allocating after picking has started frees
  the reservation but does not physically return already-picked stock.
- **Hold / QC / damage status** - a status that makes stock unavailable **without moving it**. Physically
  there, invisible to allocation and ATP. Distinct from an **order hold**, which pauses one order from
  allocating but does not touch stock ATP. The specific status codes are configurable; the rule is simple -
  any non-available status is out of ATP, so treat an unfamiliar status as hold-equivalent (unavailable)
  until you confirm otherwise.
- **Cycle count** - a count of a location/LPN. If the count differs and is approved it **posts an
  adjustment**; the count is a write, not a look.
- **Replenishment (replen)** - a move from reserve to active pick locations to feed picking. Confirming a
  replen is a real move; planned against stale reserve on-hand it can leave the pick face short.
- **Catch weight** - a variable-weight item tracked in dual UOM (nominal count + actual weight). Adjusting or
  shipping on the count alone mis-states the weight-based value and invoice.
- **Policy (poltype / polvalue)** - a config parameter that changes system behavior (allocation strategy,
  wave rules, task direction) for the **whole warehouse**, not one order.
- **MOCA command** - the direct command layer. A hand-run command runs business logic **past** the RF-flow
  validations and can post an unbalanced or unchecked inventory move.
- **Deconsolidation / put-to-store / put-wall** - building OLPN cartons from bulk picks; cancelling
  mid-consolidation strands partially built cartons.
- **Manifest / ship confirm** - the outbound close. Ship confirm posts the **goods issue** to the host; once
  manifested / loaded / tendered the shipment has left the system's control.

## Operations: read / write / destructive
Classify every operation family by what it does to on-hand and to the host/ERP. Kinds of action, not command names.

| Class | Blue Yonder WMS operation families | Gate | Why |
|---|---|---|---|
| **Read** | on-hand inquiry by item, location, or LPN; ILPN/OLPN track / contents; order, wave, and task status; ASN and receipt inquiry; location / zone view; cycle-count and adjustment history / audit trail; labor and dashboard reports; **reading a policy value**; a read-only MOCA query | always pass | no state change; read on-hand before every write and re-read at execute |
| **Write (reversible)** | build or edit a **wave template** / waveless rule before release; create or edit an outbound order before allocation; **cancel a wave or de-allocate before any pick is confirmed** (tasks may exist in `ready` but nothing is physically pulled, so it is a clean release of the reservation); assign / re-assign a **task** to a user or zone (labor routing, no stock move); create a cycle-count request before counting; place or lift an **order** hold before allocation | gate one at a time | uncommitted planning or labor routing; low blast, no inventory moved yet |
| **Write (committing)** | **wave release / waveless allocation** (reserves on-hand, generates task work, starves the pool for others); confirm a **pick** (source location decrements, stock rides the pick/OLPN); confirm a **put-away** or **replenishment** (physical move posts); **receive** against ASN/PO into an ILPN (creates inventory, publishes a goods receipt to the host); **pack** into an OLPN; place an **inventory hold / QC** status (removes ATP) | gate + human approve | binds the physical world or commits stock; each publishes an inventory transaction to the host |
| **Destructive / irreversible** | **inventory adjustment** up or down (overwrites on-hand, no offset, posts loss/gain + host value doc); **cycle-count variance posting**; **ship / load / manifest confirm** (goods issue to host, then carrier owns it); **cancel a wave or de-allocate after picking started** (strands staged stock); **cancel a staged / loaded / manifested shipment**; **void / consume an ILPN or OLPN**; **force-close / short-close** an order or task; **release held / QC / damage stock to available** without resolving the reason; **status down-adjustment** (available -> damage); **attribute correction** (re-lot / re-date / re-serialize); **change a policy (poltype / polvalue)**; **a direct MOCA write** that moves inventory or forces a task | hard gate + named approver + re-read on-hand | overwrites the book, records a real loss/gain, re-shapes warehouse-wide behavior, or crosses a point of no clean return |

**Gate semantics:** "gate one at a time" means confirm each write with the approver and see it execute
before starting the next, never batch a run of reversible writes on one approval. In practice: pause after
each write, re-read on-hand to verify the expected state change landed, then proceed. A **cycle-count
request** is reversible while it is only a request; it becomes a write the moment its variance is approved and
posts an adjustment, so gate the variance posting, not the request.

**Hold-release reclassification:** releasing a hold *with* a resolved disposition (QC passed, recall cleared)
is a **committing** write, not destructive: it returns ATP and publishes a status change, so gate it
normally. The **destructive** case is flipping held / QC / damage stock to available *without* resolving the
reason, because that puts unusable stock back into ATP.

**Policy / MOCA reclassification:** a **policy change** is warehouse-wide configuration - treat it as
change-control (named approver, tested in a lower environment), not a per-order edit, because it silently
re-shapes every future wave, allocation, or task. A **direct MOCA write** bypasses the RF-flow validations;
treat any MOCA command that moves inventory, adjusts on-hand, or forces a task as destructive. MOCA can also
change configuration or status in ways that do not look like an inventory write, so the safe default is: **if
you cannot confirm a command is read-only, treat it as destructive and gate it.** A rough verb heuristic:
`list` / `get` commands are usually reads; a command whose verb is change / update / insert / delete / move /
adjust / confirm / close should be assumed write-class - but the heuristic never overrides the safe default.

Universal rules to teach: read on-hand **before every write and re-read at execute** because on-hand drifts
between read and confirm (another wave, another task, a count in flight). A **hold means stop** - do not lift
it to make an allocation succeed. Never adjust WMS on-hand purely to force a match with the host; that writes
a phantom loss or gain. Never split a large down-adjustment into small ones to slip under an approval
threshold; it is the same write with extra steps and it is auditable.

## Gotchas that bite (the causal chains)
Each is action -> hidden effect -> downstream consequence. The normative rule lives here; the vocabulary list
above only names the term.
1. **An inventory adjustment writes the book directly with no offsetting document.** A down-adjustment removes that quantity from available and ATP immediately, records a loss, and once published posts an inventory + value document to the host. There is no undo, only a new opposite adjustment.
2. **Available is not on-hand.** `available = on-hand - allocated - non-available (hold / QC / damage)`. A read that treats raw on-hand as promiseable over-commits stock that is reserved, held, QC, or damaged.
3. **Wave release allocates and can starve other orders.** Release reserves on-hand to the released lines first; a large or careless wave commits stock a higher-priority order needed, and that stock is unavailable until de-allocation.
4. **Task confirmation is the moment stock moves, not planning.** Until an RF-directed pick is confirmed the source location still shows the quantity; two flows can both plan against it and one shorts at confirm.
5. **On-hand goes stale between read and execute.** A concurrent task, wave, or count changes it; an allocation staged against a stale read short-picks. Re-read on-hand at execute.
6. **Held, QC, and damaged stock are present but not available.** A hold removes stock from ATP without moving it; allocating or promising against it fails at pick or ships bad product.
7. **Moving a parent ILPN/OLPN moves every nested child and its inventory.** A mis-scanned parent relocates far more than intended, and downstream picks against the children now point to the wrong location.
8. **Confusing an ILPN with an OLPN mis-routes a container.** An inbound license plate belongs to the receive/put-away flow; an outbound carton belongs to pack/ship. Acting on the wrong one sends stock down the wrong process.
9. **A short pick means the allocation was against stock that was not physically there.** It leaves the order short and re-allocates or back-orders; the root cause is usually on-hand overstated by a missed earlier adjustment, so fixing the pick without fixing the count repeats the short.
10. **Confirming a receipt into an ILPN creates inventory and posts a goods receipt to the host.** Over-receiving beyond the ASN/PO posts inventory the host did not expect and a GR that finance must reconcile.
11. **A cycle count is a write.** An approved variance posts an adjustment: an over-count injects phantom inventory into ATP, an under-count writes off a loss. Counting the wrong location or LPN corrupts good inventory.
12. **De-allocating or cancelling a wave after picking started strands partially-picked stock on staging LPNs.** That stock does not auto-return home; it must be physically put away, or the pick face and staging both show wrong quantities.
13. **Ship / load / manifest confirm posts a goods issue and hands the shipment to the carrier flow.** Once manifested, loaded, or tendered it is effectively irreversible; the reversal is a return / RMA, not an un-ship.
14. **Cancelling a staged or loaded shipment is not a delete.** Staged/packed OLPNs must be de-staged and unpacked and a loaded shipment must be unloaded and de-manifested before the order can cancel; skip that and the book reads shipped while the stock still sits in the building.
15. **Releasing held / QC / damage stock to available without clearing the reason puts unusable stock back into ATP.** The hold existed for a reason (QC, recall, damage); lifting it to make an allocation succeed ships bad stock.
16. **A down-adjustment above a threshold is high blast.** It removes promised ATP, can un-allocate committed orders, and posts a material loss to finance. The threshold is site-configured (an approval policy), not a hardcoded number - check the policy rather than assuming a value. Size it and confirm the physical count before posting.
17. **A replenishment planned against stale reserve on-hand moves stock a concurrent adjustment already removed,** leaving the active pick location short exactly when picking needs it.
18. **Inventory attributes are part of on-hand identity.** Allocating or adjusting without matching lot / serial / expiry nets across different lots and can pick expired or wrong-lot stock; FEFO / FIFO holds only if attributes are respected.
19. **A policy change (poltype / polvalue) re-shapes behavior warehouse-wide.** Changing an allocation, wave, or task-direction policy silently alters how every future wave allocates or how RF tasks direct - it is a config change with site-wide blast, not a per-order tweak, and it is easy to make one wave behave by breaking the next hundred.
20. **A direct MOCA command runs past the RF-flow validations.** Hand-running a command that writes inventory, adjusts on-hand, or forces a task skips the checks the directed-work flow enforces and can post an unbalanced or unchecked move. Treat direct MOCA writes as destructive.
21. **Catch-weight items carry dual UOM (count + actual weight).** Adjusting, allocating, or shipping on the nominal count alone mis-states the weight-based value and the customer invoice; the weight must move with the count.
22. **A retried confirmation double-posts.** A network or RF retry on a pick confirm, ship confirm, or adjustment can post the move twice, creating phantom inventory or a double goods-issue to the host. Blue Yonder soft-locks the inventory record during a confirm, so a concurrent operation on the same LPN/location can fail with a lock error - that lock failure is a common trigger for a blind retry. Before retrying anything, re-read the state to check whether the first call already posted, rather than re-confirming blindly.
23. **Force-closing or short-closing a task changes what the book thinks moved.** Reassigning a task is only labor routing and moves nothing, but a force-complete posts a move that may not have physically happened.
24. **Blue Yonder is the on-hand system of record; the host mirrors it.** When they disagree the gap is almost always an in-flight transaction not yet published/posted (worse on a legacy batch-interface site); WMS on-hand is operational truth for picking and the host holds valuation. Reconcile the transaction gap; never adjust one side just to make the numbers match.

## Edge states & special cases
Each breaks naive "quantity at a location" logic. Key rule inline; deep mechanics in the references.
- **Nested ILPN / OLPN** - a pallet holds case LPNs holds units. An operation on the parent cascades. See `references/wave-task-and-moca.md`.
- **In-transit inventory** - stock on an unconfirmed move task is still on-hand at the **source** location on the book (it has not moved yet) but is reserved for the move, so it is not freely allocatable at either end; do not double-count it as available at the destination before the task confirms.
- **Short / partial picks** - the order splits into shipped-short plus a re-allocation or back-order; a short signals an on-hand overstatement, not a data glitch.
- **QC / recall / damage holds** - present but unavailable; releasing to available needs the disposition resolved, not a status flip.
- **Cross-dock / flow-through** - received stock allocated straight to an outbound order, skipping put-away; a receiving short becomes an immediate outbound short.
- **Catch weight** - dual-UOM items (grocery/food); on-hand, allocation, and shipping must carry actual weight with the count, or value and invoice are wrong.
- **Deconsolidation / put-to-store / put-wall** - bulk picks broken into OLPN cartons at a wall; cancelling mid-consolidation strands partially built cartons that must be unwound.
- **Cycle count classes** - ABC count frequency by velocity; a high-velocity location counted mid-shift catches in-flight moves and can post a false variance.
- **Kitting / VAS work orders** - components consumed to build a kit; the kit is new on-hand and the components are gone, a two-sided inventory event.
- **Split allocation** - one order line filled from several locations/LPNs; each pick confirms independently and any one can short.
- **Waveless vs wave** - on the cloud line allocation commits continuously with no wave to hold; on legacy DLx release is batch-wave only. Apply the model the deployment actually runs.

## Freshness & reconciliation
On-hand is a moving target. Between the read that planned an action and the confirm that executes it, waves,
tasks, receipts, and counts all mutate the same numbers - re-read on-hand at execute, not just at plan. When
WMS and host disagree, the difference is almost always in-flight transactions (a receipt or shipment not yet
published, or published and not yet posted). On the cloud line events publish in seconds to minutes; a legacy
DLx **batch interface** (flat file / IDoc / API) can lag hours, so a gap is not a true discrepancy until that publish window has
passed. A re-read narrows the race but does not close it: Blue Yonder does not hard-lock a location during
picking, so a concurrent task can confirm between your re-read and your write, which is why a short pick can
still happen after a fresh read. Reconcile the transaction stream; treat a raw quantity delta as a symptom to
investigate, never as a number to force-match with an adjustment.

## Recovery patterns (can it be undone, and what cannot)
"Reverse" is almost always a new compensating transaction, not an undo, and the original entry stays in the
trail forever.

| Action | Undoable? | Recovery path | What cannot be restored |
|---|---|---|---|
| Inventory adjustment | No | new opposite adjustment under a correcting reason code referencing the original; if the first published, the correction publishes again (two host postings) | stock physically gone; the original entry stays in the audit trail |
| Cycle-count variance | No | re-count and post a correcting adjustment | the first variance already hit ATP and the host |
| Confirmed pick / put-away / replen | Compensating only | a new move task or an adjustment | nothing rolls back; the move and host posting already went |
| Ship / load / manifest confirm | Only before tender | un-manifest / de-load while the carrier has not taken it; after tender/pickup a return / RMA into receiving | a shipment already picked up |
| Wave cancel / de-allocation | Book yes, physical no | free the reservation, then physically put away stock already pulled | staged / OLPN stock does not auto-return home |
| Attribute correction / status down-adjust | By further write | another attribute/status write under a reason code | FEFO/FIFO picks already mis-driven (expired/wrong-lot stock shipped) |
| Void / consume ILPN / OLPN | No | re-establish inventory under a new LPN via receipt or adjustment | the old LPN identity |
| Policy (poltype / polvalue) change | Future only | revert the value to restore future behavior | waves/allocations/tasks already run under it (find and fix each) |
| Direct MOCA write | No auto-offset | re-read on-hand at the affected location/LPN, compare to the expected delta, check the host posting, then post a manual compensating adjustment or move | the RF task history / confirmation record the flow would have left; balance if the write was unbalanced |
| Outbound split-brain (ship confirm posted goods issue, WMS status failed) | Reconcile | reconcile from the host posting and correct WMS status to physical reality; do NOT re-confirm (double-posts the goods issue) | - |
| Inbound split-brain (receipt/GR posted on one side, confirmation failed on the other) | Reconcile | check whether the goods receipt already posted to the host before doing anything; if it did, correct the WMS receipt/ILPN state to match, do NOT re-confirm the receipt (double-posts the GR); if only WMS received and the host GR failed, re-trigger the host publish, not a second WMS receipt | - |

## Guardrails
- Read on-hand and its available / held / QC / damage split before acting, and re-read at execute; state drifts.
- Size every adjustment before posting: know the quantity, the reason code, and the loss/gain, and re-count the location to confirm the physical quantity first. A down-adjustment above a set limit is high blast (removes ATP, un-allocates orders, posts a loss) and needs a named approver and that confirmed count.
- A hold means stop. Resolve the disposition (release to good, scrap, or return) rather than flipping held / QC / damage stock to available to make an allocation or wave succeed.
- Do not cancel a staged / loaded / manifested shipment without de-staging / unpacking / de-manifesting first, or the book ships stock still in the building.
- Never adjust WMS on-hand purely to reconcile a host mismatch, and never split an adjustment to dodge an approval threshold.
- Treat a **policy (poltype / polvalue) change** as warehouse-wide change-control: named approver, a lower-environment test, and a reason - never a quick tweak to make one wave behave. Treat any **direct MOCA write** that moves inventory or forces a task as destructive, and if you cannot confirm a MOCA command is read-only, gate it as destructive.
- Verify role authorization before attempting any committing or destructive action; many gated operations require a specific role, and a role-mismatch error is a hard stop to escalate, not something to work around.
- Treat wave release, allocation, and every task confirmation as committing: they move physical stock and publish to the host. For anything in the destructive row: named approver, re-read, logged reason code.

## References (load on demand)
Load by situation:
- Releasing a wave or waveless flow, allocating, confirming task work, a nested ILPN/OLPN move, cross-dock, or touching a **policy or MOCA** -> `references/wave-task-and-moca.md` (wave vs waveless release, allocation and short-pick mechanics, the RF-directed task state machine, and how policies (poltype/polvalue) and MOCA commands change or bypass the rules).
- Adjusting inventory, posting a cycle count, placing/lifting a hold or status, catch weight, voiding/consuming an LPN, or reconciling with the host -> `references/adjustment-count-and-host.md` (adjustment classes and reason codes, cycle-count posting, holds and status codes, catch weight, ILPN/OLPN void/consume, and how each publishes to the host/ERP).
