---
name: korber
description: "Korber WMS (ex-HighJump; Korber Supply Chain Software / K.Motion Warehouse Advantage and Warehouse Edge) - safe operation of warehouse execution and on-hand inventory: available vs on-hand, LPN / license plate and nested containers, locations and zones, wave release and work creation (allocates + directs RF task work), allocation, directed work (pick / put-away / replenishment / cycle count; confirming work posts the inventory move), receiving / ASN, pack / load / ship confirm, inventory adjustment and status holds, multi-client / owner 3PL stock, and the HighJump Architect workflow / business-rules configuration layer. Use when the warehouse system is Korber WMS (or HighJump, K.Motion, Warehouse Advantage, Warehouse Edge, Accellos) and the work touches on-hand, an LPN, a wave or work, allocation, a cycle count, an inventory adjustment or hold, receiving, pick / pack / ship, an Architect business-rule or workflow change, or a goods movement posted to the host / ERP."
---

# Korber WMS - operating it safely

Korber Warehouse Management (the ex-**HighJump** WMS, now sold under **Korber Supply Chain Software** and the
**K.Motion** brand; the enterprise line is **Warehouse Advantage**, the SMB / 3PL line is **Warehouse Edge**,
ex-Accellos) runs warehouse execution: receiving, put-away, storage, allocation, picking, packing, and
shipping. It is the **system of record for on-hand** inside the four walls; the ERP / host does not know
where a unit physically sits, so Korber posts each movement back and the host posts the matching goods
movement and often a value document. Three facts make it dangerous. First, most writes move physical stock
and the moment of movement is **work / task confirmation** (usually an RF-directed task), not planning.
Second, an **inventory adjustment writes the book directly with no offsetting document** - it overwrites
on-hand, so a mistake is a real loss or a phantom, not a reversible entry. Third, Korber is **extremely
configurable**: the **HighJump Architect** workflow / business-rules layer lets the customer redefine how
almost any transaction behaves, so you cannot assume a screen does the standard thing, and an Architect
change re-shapes execution warehouse-wide. This skill classifies each action so the harness can gate it, plus
the edge states and recovery paths that decide if a mistake is fixable.

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
Warehouse system is Korber WMS (HighJump / K.Motion / Warehouse Advantage / Warehouse Edge / Accellos) and
the work is execution or on-hand inside the DC. When NOT:
- **Manhattan** Active WM / WMS / SCALE warehouse execution -> `manhattan-wms`. Same object model
  (LPN, wave, work / task, allocation) but Manhattan has no Architect business-rules layer and (Active WM)
  streams orders; do not apply Korber Architect logic to a Manhattan site.
- **Blue Yonder** WMS (RedPrairie / JDA / DLx / Luminate) -> `blueyonder-wms`. Also heavily
  config-driven, but through **MOCA** commands and **policies** (poltype / polvalue) and the **ILPN / OLPN**
  split; Korber uses a single generic **LPN** and the **Architect** layer, not MOCA / policies. Do not apply
  Blue Yonder MOCA / policy logic to a Korber site, or Korber Architect logic to Blue Yonder.
- **SAP EWM** warehouse execution (storage bins, handling units / HUs, `/SCWM/` transactions, EWM warehouse
  tasks and warehouse orders) -> `sap-ewm`. EWM's HU / quant model is not Korber's LPN.
- ERP inventory **valuation**, movement types, GR/IR, financial postings and period close -> `sap-mm`
  (Korber triggers those host postings; it does not own the ledger).
- Transportation, carrier rating, load tendering as a **planning** act -> a TMS skill (Korber does the
  physical load / manifest, not the rate / route decision).
- **WMS administration / setup** - user and role management, warehouse / location / item master
  configuration, and authoring Architect workflows or business rules as an admin project - is a different
  risk domain (config blast radius, not a live stock move) with its own change-control. This skill covers
  operational execution; an Architect rule or workflow touched *during operations* is still gated as
  change-control (see the matrix).

**Which product** matters: **Warehouse Advantage** (enterprise, ex-HighJump, the Architect-configured line)
and **Warehouse Edge** (ex-Accellos, SMB / 3PL, more out-of-box) are different products with different
internals. Confirm which one the site runs before assuming Architect-level configurability or a given
screen's behavior; do not carry one product's model onto the other. Concrete divergences to expect on an
**Edge** site: little or no Architect configuration layer (so the "read the configured rule" step has less to
read and behavior is closer to out-of-box), integration to the host that is more likely **batch / interface**
than near-real-time (so reconciliation lag is longer - see Freshness), and a lighter execution model tuned to
SMB / 3PL volumes. Do not assume Advantage's Architect configurability, waveless flow, or real-time host
publishing on an Edge deployment.

## Object & state model (reason about state, not nouns)
- **Inventory / on-hand** - quantity of an **item / SKU** at a **location**, carried on an **LPN**, qualified
  by **inventory attributes** (lot, serial, expiry, country of origin, and for food / grocery a **catch
  weight**), an **inventory status** (available, hold, QA / QC, damage), and in a 3PL site an **owner /
  client**. The same physical quantity is not equally usable; **available** is derived, not raw on-hand
  (formula below).
- **LPN (License Plate Number)** - the container identifier (pallet, carton, tote) inventory lives on. Korber
  uses a **single generic LPN** for both inbound and outbound (not the Blue Yonder ILPN / OLPN split). LPNs
  **nest**: a pallet LPN holds case LPNs holds units; moving a parent moves every child and its inventory.
- **Location** - a physical slot. Types: receiving / dock, reserve (bulk storage), active / forward pick,
  case-pick, staging, ship dock. Grouped into **zones** / areas for work and travel routing.
- **Inbound: ASN / PO receipt** - an ASN (Advance Ship Notice) is the expected inbound against a PO.
  Receiving confirms it onto an LPN in a receiving location. States: expected -> received -> put-away.
- **Order (shipment / distribution order)** - demand to fulfil. States: created -> allocated -> in-pick ->
  packed -> staged -> loaded -> shipped. A **work order** covers kitting / value-added service (VAS).
- **Wave** - a batch of order lines released together for allocation and work creation. States: planned ->
  released (allocated + work generated) -> in progress -> complete. Newer deployments can run **waveless /
  flow-through** continuous release; older / Edge sites are wave-centric with batch host integration.
- **Allocation** - the reservation of specific on-hand (location + LPN + attributes + owner) to an order
  line. A hard allocation commits that stock; it is still physically present but no longer available to
  others.
- **Work / task** - the unit of directed labor, usually **RF-directed**. Korber calls the labor unit
  **work**. Types: pick, put-away, replenishment, cycle count, pack, load. States: ready -> in progress ->
  confirmed (or short / cancelled). **Confirming the work posts the inventory move.**
- **Inventory adjustment** - a direct write to on-hand (quantity or status) under a reason code, with no
  offsetting document. It is the book, corrected by fiat.
- **Architect (workflow / business rules)** - HighJump / Korber behavior is defined in the **Architect**
  configuration layer: business rules, workflow / screen steps, validations, labels, and integration maps.
  It is warehouse-wide config, not per-order data, and it is the lever that changes or bypasses the standard
  behavior the rest of this skill assumes.

## Vocabulary that bites
(Definitions are brief; the full causal chain and hazard for each term are in Gotchas below.)
- **Available vs on-hand** - `available = on-hand - allocated - (everything not in an available status)`.
  Hold, QA / QC, and damage are all just **non-available statuses**; the list is site-configurable, so do not
  assume those three are the only ones, and do not double-subtract. "On-hand" is everything in the building;
  only *available* can be promised. Read the status split, not just the total.
- **LPN / license plate** - a generic container ID, and containers nest; an operation on a parent LPN
  cascades to every child LPN and its inventory.
- **Work / task confirmation** - the write that actually moves stock. Before confirm an RF-directed pick /
  put-away is only planned and the source location still shows the quantity. The book changes at confirm, not
  at release.
- **Wave release / work creation** - not a report run. Release **allocates** on-hand to the released orders
  and **creates the work**; committed stock leaves the available pool for everyone else.
- **Waveless / flow-through** - continuous release. Allocation commits the instant an order flows in; there
  is no wave sitting in planned that you can hold to reprioritize.
- **Allocation / de-allocation** - reserve / un-reserve stock. De-allocating after picking has started frees
  the reservation but does not physically return already-picked stock.
- **Hold / QA / damage status** - a status that makes stock unavailable **without moving it** (QA, recall,
  quality, damage). Physically there, invisible to allocation and ATP. Distinct from an **order hold**, which
  pauses one order from allocating but does not touch stock ATP.
- **Cycle count** - a count of a location / LPN. If the count differs and is approved it **posts an
  adjustment**; the count is a write, not a look.
- **Replenishment (replen)** - a move from reserve to active pick locations to feed picking. Confirming a
  replen is a real move; planned against stale reserve on-hand it can leave the pick face short.
- **Owner / client (3PL)** - in a multi-client building, on-hand belongs to a specific owner. Allocating,
  adjusting, or moving across owners mis-owns stock and mis-drives client billing.
- **Catch weight** - a variable-weight item tracked in dual UOM (nominal count + actual weight). Adjusting or
  shipping on the count alone mis-states the weight-based value and the invoice.
- **Architect business rule / workflow** - a config change that alters how a transaction behaves for the
  **whole warehouse** (or a zone / client), not one order. Changing it silently re-shapes every future
  receipt, allocation, or task.
- **Manifest / ship confirm** - the outbound close. Ship confirm posts the **goods issue** to the host; once
  manifested / loaded / tendered the shipment has left the system's control.

## Operations: read / write / destructive
Classify every operation family by what it does to on-hand and to the host / ERP. Kinds of action, not
screen or command names. Two rules apply at the point of classification, not after: **read on-hand (and its
status split) before every write and re-read at execute**, and **gate committing / destructive writes one at
a time** (approve, execute, re-read, then the next).

| Class | Korber WMS operation families | Gate | Why |
|---|---|---|---|
| **Read** | on-hand inquiry by item, location, owner, or LPN; LPN track / contents; order, wave, and work / task status; ASN and receipt inquiry; location / zone view; cycle-count and adjustment history / audit trail; labor and dashboard reports; **reading an Architect rule / config value** | always pass | no state change; read on-hand before every write and re-read at execute |
| **Write (reversible)** | build or edit a **wave template** / waveless rule before release; create or edit an outbound order before allocation; **cancel a wave or de-allocate ONLY while every line is still `ready`** (nothing pulled - a clean release of the reservation; one confirmed or in-progress line escalates this to destructive, see Wave-cancel reclassification); assign / re-assign **work** to a user or zone (labor routing, no stock move); create a cycle-count request before counting; place or lift an **order** hold before allocation | gate one at a time | uncommitted planning or labor routing; low blast, no inventory moved yet |
| **Write (committing)** | **wave release / waveless allocation** (reserves on-hand, creates work, starves the pool for others); confirm a **pick** (source location decrements, stock rides the pick / ship LPN); confirm a **put-away** or **replenishment** (physical move posts); **receive** against ASN / PO onto an LPN (creates inventory, posts a goods receipt to the host); **pack** into a shipping carton; **assemble a kit / VAS work order** (consumes components, creates the kit as new on-hand - a two-sided move); place an **inventory hold / QA** status (removes ATP) | gate + human approve | binds the physical world or commits stock; each posts an inventory transaction to the host |
| **Destructive / irreversible** | **inventory adjustment** up or down (overwrites on-hand, no offset, posts loss / gain + host value doc); **cycle-count variance posting**; **ship / load / manifest confirm** (goods issue to host, then carrier owns it); **cancel a wave or de-allocate after picking started** (strands staged stock); **cancel a staged / loaded / manifested shipment**; **void / consume an LPN**; **force-close / short-close** an order or work / task; **release held / QA / damage stock to available** without resolving the reason; **status down-adjustment** (available -> damage); **attribute correction** (re-lot / re-date / re-serialize); **re-owner stock between clients (3PL)**; **disassemble / unpick a kit** (a compensating write); **change an Architect business rule or workflow**; **a hand-run action that bypasses the configured workflow** (direct data edit, admin / support utility, or a step run outside the RF flow - it skips the workflow validations and is unbalanced by design, the most dangerous write class) | hard gate + named approver + re-read on-hand | overwrites the book, records a real loss / gain, re-shapes warehouse-wide behavior, skips validations, or crosses a point of no clean return |

**Gate semantics ("gate one at a time" = gate + verify sequentially):** confirm each write with the approver
and see it execute before starting the next; re-read between writes; never batch a run of reversible writes
on one approval. In practice: approve one wave-template edit, re-read to confirm it saved, then edit the next
- never batch five template changes under a single approval. A **cycle-count request** is reversible while it
is only a request; it becomes a write the moment its variance is approved and posts an adjustment, so gate
the variance posting, not the request.

**Wave-cancel reclassification:** cancelling a wave / de-allocating is reversible **only while every work
line in it is still `ready`** (nothing taken, nothing confirmed). Two escalations: (1) if *any* pick is
**confirmed**, the whole cancellation is **destructive** - the book reservation frees cleanly but the
already-picked stock is stranded on staging LPNs and must be physically put away; (2) if work is
**in-progress** (a picker has taken the RF task and walked to the location) but not yet confirmed, there is
no book change yet, but you usually cannot cleanly cancel it - clearing it means **force-closing** the task,
which is destructive and strands the picker. So a wave that is "99% ready, 1% confirmed (or in-progress)" is
not "mostly reversible"; one confirmed or in-progress line makes the cancel a destructive action.

**Hold-release reclassification (effect, not mechanism):** releasing a hold *with* a resolved disposition (QA
passed, recall cleared) is a **committing** write, not destructive: it returns ATP and posts a status change,
so gate it normally. The **destructive** case is flipping held / QA / damage stock to available *without*
resolving the reason, because that puts unusable stock back into ATP. This classification follows the
**effect** (unusable stock re-entering ATP), not the screen: the same danger applies whether the flip comes
from the hold-release screen or from a status-change inventory adjustment, so gate any status flip that
returns unresolved stock to available.

**Retry-after-lock reclassification:** Korber soft-locks the inventory record during a confirm, so a
concurrent operation on the same LPN / location can fail with a lock error. Re-reading state to see whether
the first call posted is a **read** (always pass); a blind retry of the confirm is a **destructive** risk (it
can double-post). On a lock error, re-read first and retry the confirm only if the first call did not post.

**Architect reclassification:** an **Architect business-rule or workflow change** is warehouse-wide (or zone /
client-wide) configuration - treat it as change-control (named approver, tested in a lower environment,
version-promoted), not a per-order edit, because it silently re-shapes every future receipt, wave,
allocation, or task. And because Architect can redefine what any transaction does, **do not assume a screen
behaves the standard way**: read the configured behavior before classifying an operation - inspect the
Architect rule / workflow for that transaction (in particular the workflow step's **auto-confirm** flag and
any **source / destination or validation override** on the business rule), or ask the user / site admin to
confirm what it does on this site - and if you cannot establish it, default to the more dangerous class
(destructive) and gate it.

Universal rules to teach: read on-hand **before every write and re-read at execute** because on-hand drifts
between read and confirm (another wave, another task, a count in flight). A **hold means stop** - do not lift
it to make an allocation succeed. Never adjust WMS on-hand purely to force a match with the host; that writes
a phantom loss or gain. Never split a large down-adjustment into small ones to slip under an approval
threshold; it is the same write with extra steps and it is auditable.

## Gotchas that bite (the causal chains)
Each is action -> hidden effect -> downstream consequence. The normative rule lives here; the vocabulary list
above only names the term.
1. **An inventory adjustment writes the book directly with no offsetting document.** A down-adjustment removes that quantity from available and ATP immediately, records a loss, and once posted writes an inventory + value document to the host. There is no undo, only a new opposite adjustment.
2. **Available is not on-hand.** `available = on-hand - allocated - (everything not in an available status)`. A read that treats raw on-hand as promiseable over-commits stock that is reserved, held, QA, or damaged; because the non-available status list is site-configurable, an unfamiliar status must be treated as unavailable until you confirm otherwise.
3. **Wave release / work creation allocates and can starve other orders.** Release reserves on-hand to the released lines first; a large or careless wave commits stock a higher-priority order needed, and that stock is unavailable until de-allocation.
4. **Work / task confirmation is the moment stock moves, not planning.** Until an RF-directed pick is confirmed the source location still shows the quantity; two flows can both plan against it and one shorts at confirm.
5. **On-hand goes stale between read and execute, and Korber does not hard-lock the location during picking.** A concurrent task, wave, or count changes on-hand, and a soft lock on the record during confirm does not stop another flow from planning against the same stock; an allocation staged against a stale read short-picks. Re-read on-hand at execute.
6. **Held, QA, and damaged stock are present but not available.** A hold removes stock from ATP without moving it; allocating or promising against it fails at pick or ships bad product.
7. **Moving a parent LPN moves every nested child and its inventory.** A mis-scanned parent relocates far more than intended, and downstream picks against the children now point to the wrong location.
8. **A short pick means the allocation was against stock that was not physically there.** It leaves the order short and re-allocates or back-orders; the root cause is usually on-hand overstated by a missed earlier adjustment, so fixing the pick without fixing the count repeats the short.
9. **Confirming a receipt onto an LPN creates inventory and posts a goods receipt to the host.** Over-receiving beyond the ASN / PO posts inventory the host did not expect and a GR that finance must reconcile.
10. **A cycle count is a write.** An approved variance posts an adjustment: an over-count injects phantom inventory into ATP, an under-count writes off a loss. Counting the wrong location or LPN corrupts good inventory.
11. **De-allocating or cancelling a wave after picking started strands partially-picked stock on staging LPNs.** That stock does not auto-return home; it must be physically put away, or the pick face and staging both show wrong quantities.
12. **Ship / load / manifest confirm posts a goods issue and hands the shipment to the carrier flow.** Once manifested, loaded, or tendered it is effectively irreversible; the reversal is a return / RMA, not an un-ship.
13. **Cancelling a staged or loaded shipment is not a delete.** Staged / packed cartons must be de-staged and unpacked and a loaded shipment must be unloaded and de-manifested before the order can cancel; skip that and the book reads shipped while the stock still sits in the building.
14. **Releasing held / QA / damage stock to available without clearing the reason puts unusable stock back into ATP.** The hold existed for a reason (QA, recall, damage); lifting it to make an allocation succeed ships bad stock.
15. **A down-adjustment above a threshold is high blast** (gotcha 1 is why it cannot be undone; this adds the approval dimension). It removes promised ATP, can un-allocate committed orders, and posts a material loss to finance. The threshold is site-configured (an approval rule in Architect), not a hardcoded number - check the rule rather than assuming a value; if the threshold cannot be determined, treat any down-adjustment as above-threshold (destructive) and gate it. Size it and confirm the physical count before posting.
16. **A replenishment planned against stale reserve on-hand moves stock a concurrent adjustment already removed,** leaving the active pick location short exactly when picking needs it.
17. **Inventory attributes are part of on-hand identity, and a lot / expiry mismatch breaks FEFO / FIFO.** Allocating or adjusting without matching lot / serial / expiry nets across different lots; the allocation then picks a wrong-lot or expired unit, the pick confirms and ships before anyone notices, and a shipped wrong-lot / expired unit cannot be recalled from the WMS - for regulated goods (pharma, food, hazmat) that is a compliance breach, not just a data error. FEFO / FIFO holds only if attributes are respected on every allocation and adjustment.
18. **An Architect business-rule or workflow change re-shapes behavior warehouse-wide.** Changing an allocation, work-creation, receiving, or validation rule silently alters how every future transaction behaves - it is a config change with site-wide (or zone / client-wide) blast, not a per-order tweak, and it is easy to make one flow behave by breaking the next hundred. Treat it as change-control, and remember reverting it restores only *future* behavior; work already run under the changed rule must be found and fixed.
19. **You cannot assume a screen behaves the standard way.** Because Architect redefines validations, work creation, source / destination determination, and even whether a step auto-confirms, the same-named operation can be reversible on one Korber site and committing on another. Read the configured behavior before classifying an action; default to the more dangerous class when unsure.
20. **A retried confirmation double-posts.** A network or RF retry on a pick confirm, ship confirm, receipt, or adjustment can post the move twice, creating phantom inventory or a double goods movement to the host. Korber soft-locks the inventory record during a confirm, so a concurrent operation on the same LPN / location can fail with a lock error - that lock failure is a common trigger for a blind retry. Before retrying anything, re-read the state to check whether the first call already posted, rather than re-confirming blindly.
21. **Force-closing or short-closing a work / task changes what the book thinks moved.** Reassigning work is only labor routing and moves nothing, but a force-complete posts a move that may not have physically happened.
22. **Korber is the on-hand system of record; the host mirrors it.** When they disagree the gap is almost always an in-flight transaction not yet posted (worse on a legacy / Edge batch-interface site); WMS on-hand is operational truth for picking and the host holds valuation. Reconcile the transaction gap; never adjust one side just to make the numbers match.
23. **In a 3PL / multi-client building, on-hand belongs to a specific owner.** Allocating a client's order against another client's stock, or adjusting without the owner, mis-owns inventory and corrupts client billing / storage charges; the owner is part of on-hand identity, like lot or status.
24. **Warehouse Advantage and Warehouse Edge are different products.** Applying Advantage's Architect-level configurability or a screen's behavior to an Edge (ex-Accellos) site, or vice versa, reasons about a system that is not running. Confirm the product first.
25. **Catch-weight items carry dual UOM (count + actual weight).** Adjusting, allocating, or shipping on the nominal count alone mis-states the weight-based value and the customer invoice; the weight must move with the count.

## Edge states & special cases
Each breaks naive "quantity at a location" logic. Key rule inline; deep mechanics in the references.
- **Nested LPNs** - a pallet holds case LPNs holds units. An operation on the parent cascades. See `references/wave-work-and-architect.md`.
- **In-transit inventory** - stock on an unconfirmed move task is still on-hand at the **source** location on the book (it has not moved yet) but is reserved for the move, so it is not freely allocatable at either end; do not double-count it as available at the destination before the task confirms.
- **Short / partial picks** - the order splits into shipped-short plus a re-allocation or back-order; a short signals an on-hand overstatement, not a data glitch.
- **QA / recall / damage holds** - present but unavailable; releasing to available needs the disposition resolved, not a status flip.
- **Cross-dock / flow-through** - received stock allocated straight to an outbound order, skipping put-away; a receiving short becomes an immediate outbound short.
- **Multi-client / owner (3PL)** - one building holds several clients' stock, segregated by owner and often by zone; allocation, adjustment, and billing must respect the owner. Korber's 3PL heritage (ex-HighJump / Accellos) makes this common.
- **Catch weight** - dual-UOM items (grocery / food); on-hand, allocation, and shipping must carry actual weight with the count, or value and invoice are wrong.
- **Kitting / VAS work orders** - components consumed to build a kit; the kit is new on-hand and the components are gone, a two-sided inventory event.
- **Cycle count classes** - ABC count frequency by velocity; a high-velocity location counted mid-shift catches in-flight moves and can post a false variance.
- **Split allocation** - one order line filled from several locations / LPNs; each pick confirms independently and any one can short.
- **Waveless vs wave** - newer sites can allocate continuously with no wave to hold; Edge / legacy sites release by batch wave. Apply the model the deployment actually runs.

## Freshness & reconciliation
On-hand is a moving target. Between the read that planned an action and the confirm that executes it, waves,
tasks, receipts, and counts all mutate the same numbers - re-read on-hand at execute, not just at plan. When
WMS and host disagree, work the gap as a decision: (1) check for open / in-flight work and unposted
transactions at the affected location / LPN; (2) check the integration channel - modern K.Motion deployments
publish host events in seconds to minutes, but a legacy / Edge **batch interface** (flat file / EDI / API)
can lag hours, so a gap is not a true discrepancy until that publish window has passed; (3) only a delta that
survives both checks is a real discrepancy to investigate. A re-read narrows the race but does not close it:
Korber does not hard-lock a location during picking, so a concurrent task can confirm between your re-read and
your write, which is why a short pick can still happen after a fresh read. Reconcile the transaction stream;
treat a raw quantity delta as a symptom to investigate, never as a number to force-match with an adjustment.

## Recovery patterns (can it be undone, and what cannot)
"Reverse" is almost always a new compensating transaction, not an undo, and the original entry stays in the
trail forever.

| Action | Undoable? | Recovery path | What cannot be restored |
|---|---|---|---|
| Inventory adjustment | No | new opposite adjustment under a correcting reason code referencing the original; if the first posted, the correction posts again (two host postings) | stock physically gone; the original entry stays in the audit trail |
| Cycle-count variance | No | re-count and post a correcting adjustment | the first variance already hit ATP and the host |
| Confirmed pick / put-away / replen | Compensating only | a new move task or an adjustment | nothing rolls back; the move and host posting already went |
| Short pick | Forward only | the engine re-allocates from another location / LPN, else the line back-orders; then **cycle-count the short location** (the short signals overstated on-hand) | the picked-short line; re-picking without re-counting repeats the short |
| Host rejects the posting (WMS committed, host refused - period closed, vendor / posting block) | Distinct from split-brain | this is not a failed publish to re-send: the WMS is committed and the host actively refused. Hold the WMS transaction and resolve the host-side block (the ERP owns period / block - see `sap-mm`); only then re-post. If the physical move already happened and the host cannot accept it, reverse or adjust the WMS side to match reality rather than re-sending into a wall | the host posting until the block clears; do not force-match by adjusting WMS |
| Ship / load / manifest confirm | Only before tender | un-manifest / de-load while the carrier has not taken it; after tender / pickup a return / RMA into receiving | a shipment already picked up |
| Wave cancel / de-allocation | Book yes, physical no | free the reservation, then physically put away stock already pulled | staged stock does not auto-return home |
| Attribute / owner correction; status down-adjust | By further write | another attribute / status / owner write under a reason code | FEFO / FIFO picks already mis-driven (expired / wrong-lot / wrong-client stock shipped) |
| Void / consume LPN | No | re-establish inventory under a new LPN via receipt or adjustment | the old LPN identity |
| Architect rule / workflow change | Future only | identify the affected transactions from the **audit trail / transaction history** by timestamp (everything processed after the rule was promoted) filtered to the flow the rule governs; assess each for wrong behavior (wrong source / destination, skipped validation, mis-routed allocation) and post a compensating move or adjustment per affected transaction; then revert / re-promote the prior config version (the revert is itself a new change-control event) | receipts / waves / allocations / tasks already run under it, once their downstream postings have gone |
| Outbound split-brain (ship confirm posted goods issue, WMS status failed) | Reconcile | reconcile from the host posting and correct WMS status to physical reality; do NOT re-confirm (double-posts the goods issue) | - |
| Inbound split-brain (receipt / GR posted on one side, confirmation failed on the other) | Reconcile | check whether the goods receipt already posted to the host before doing anything; if it did, correct the WMS receipt / LPN state to match, do NOT re-confirm the receipt (double-posts the GR); if only WMS received and the host GR failed, re-trigger the host publish, not a second WMS receipt | - |

## Guardrails
- Read on-hand and its available / held / QA / damage split (and the owner, in a 3PL site) before acting, and re-read at execute; state drifts.
- Size every adjustment before posting: know the quantity, the reason code, the owner, and the loss / gain, and re-count the location to confirm the physical quantity first. A down-adjustment above the site's approval threshold is high blast (removes ATP, un-allocates orders, posts a loss) and needs a named approver and that confirmed count.
- A hold means stop. Resolve the disposition (release to good, scrap, or return) rather than flipping held / QA / damage stock to available to make an allocation or wave succeed.
- Do not cancel a staged / loaded / manifested shipment without de-staging / unpacking / de-manifesting first, or the book ships stock still in the building.
- Never adjust WMS on-hand purely to reconcile a host mismatch, and never split an adjustment to dodge an approval threshold. Before treating a WMS-host delta as real (or adjusting to match), confirm the integration publish window has elapsed - near-real-time on modern K.Motion, but hours on a legacy / Edge batch interface.
- Treat an **Architect business-rule or workflow change** as warehouse-wide change-control: named approver, a lower-environment test, a version-promotion, and a reason - never a quick edit to make one flow behave. And do not assume a screen's standard behavior on a heavily-configured site; read the configured rule before classifying an action.
- Confirm which product the site runs before assuming Architect-level configurability: check the system-info / about screen and version string, and whether Architect (the configuration environment) is present in the UI. Warehouse Advantage (ex-HighJump) is the Architect-configured enterprise line; Warehouse Edge (ex-Accellos) is more out-of-box - do not carry one's model onto the other.
- Verify role authorization before attempting any committing or destructive action; many gated operations require a specific role, and a role-mismatch error is a hard stop to escalate, not something to work around.
- Treat wave release, allocation, and every work / task confirmation as committing: they move physical stock and post to the host. For anything in the destructive row: named approver, re-read, logged reason code.

## References (load on demand)
Load by situation:
- Releasing a wave or waveless flow, allocating, confirming directed work, a nested-LPN move, cross-dock, or touching an **Architect workflow / business rule** -> `references/wave-work-and-architect.md` (wave vs waveless release, allocation and short-pick mechanics, the RF-directed work / task state machine, nested-LPN moves, and how the Architect layer changes or bypasses the standard rules, with config change-control).
- Adjusting inventory, posting a cycle count, placing / lifting a hold or status, multi-client / owner stock, catch weight, voiding / consuming an LPN, or reconciling with the host -> `references/adjustment-count-and-host.md` (adjustment classes and reason codes, cycle-count posting, holds and status codes, owner / 3PL segregation, catch weight, LPN void / consume, and how each posts to the host / ERP, including inbound and outbound split-brain recovery).
