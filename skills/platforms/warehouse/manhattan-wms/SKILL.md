---
name: manhattan-wms
description: "Manhattan Active Warehouse Management (Active WM) - safe operation of warehouse execution and on-hand inventory: available vs on-hand stock, LPN / license plate and nested containers, locations and zones, wave release and order streaming, allocation, pick / put-away / replenishment / cycle-count work and task confirmation, receiving and ASN, pack / load / ship confirm, inventory holds, QA and damaged stock, and inventory adjustments. Use when the warehouse system is Manhattan Active WM (or Manhattan WMS / SCALE) and the work touches on-hand, an LPN, a wave or order streaming, a warehouse task or work confirmation, allocation, a cycle count, an inventory adjustment or status hold, receiving, pick / pack / ship, or the user mentions license plate, short pick, replenishment, staging, manifest, de-allocation, or a goods movement published to the ERP."
---

# Manhattan Active WM - operating it safely

Manhattan Active Warehouse Management (Active WM, the cloud microservices product; the older on-prem line
is Manhattan WMS / SCALE) runs warehouse execution: receiving, put-away, storage, allocation, picking,
packing, and shipping. It is the **system of record for on-hand** inside the four walls. The ERP does not
know where a unit physically sits; Active WM does, and it publishes each movement back so the ERP posts the
matching goods movement and often a financial value document. Two facts make it dangerous. First, most
writes here move physical stock and the moment of movement is **task confirmation**, not planning. Second,
an **inventory adjustment writes the book directly with no offsetting document** - it overwrites on-hand,
so a mistake is a real loss or a phantom, not a reversible entry. This skill gives the judgment to classify
each action so the harness can gate it, plus the edge states and recovery paths that decide if a mistake is
fixable.

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
Warehouse system is Manhattan Active WM and the work is execution or on-hand inside the DC. When NOT:
- SAP-native warehouse execution (storage bins, handling units / HUs, `/SCWM/` transactions, warehouse
  tasks in EWM) -> `sap-ewm`.
- ERP inventory **valuation**, movement types, GR/IR, financial postings and period close -> `sap-mm`
  (Active WM triggers those postings; it does not own the ledger).
- Transportation, carrier rating, load tendering as a planning act -> a TMS skill (Active WM does the
  physical load/manifest, not the rate/route decision).

Active WM vs legacy: **order streaming** and continuous real-time publishing are Active WM features. On the
older on-prem line (Manhattan WMS / SCALE) release is **batch-wave only** and ERP integration is typically
batch/interface-based, so do not apply streaming or real-time-publish logic to a SCALE deployment.

## Object & state model (reason about state, not nouns)
- **Inventory / on-hand** - quantity of an item at a **location**, carried on an **LPN**, qualified by
  **inventory attributes** (lot, serial, expiry, country of origin) and an **inventory status / type**
  (available, on-hold, damaged). The same physical quantity is not equally usable. Available is a derived
  number, not raw on-hand (see the formula below).
- **LPN (License Plate Number)** - the container identifier (pallet, carton, tote) that inventory lives on.
  LPNs **nest**: a pallet LPN contains case LPNs. Moving a parent moves every child and its inventory.
- **Location** - a physical slot. Types: receiving/dock, reserve (bulk storage), active (forward pick face),
  staging, ship dock. Grouped into **zones** / areas for work routing.
- **Inbound: ASN / receipt** - an ASN (Advance Ship Notice) is the expected inbound against a PO. Receiving
  confirms it into an LPN in a receiving location. States: expected -> received -> put-away.
- **Outbound order (distribution order) / shipment** - demand to fulfil. States: created -> allocated ->
  in-pick -> packed -> staged -> loaded -> shipped.
- **Wave** - a batch of order lines released together for allocation and work creation. States: planned ->
  released (allocated + work generated) -> in progress -> complete. **Order streaming** is the newer
  continuous alternative that allocates and generates work as orders arrive, with no discrete wave to hold.
- **Allocation** - the reservation of specific on-hand (location + LPN + attributes) to an order line. A
  hard allocation commits that stock; it is still physically present but no longer available to others.
- **Work / task** - the unit of labor. Types: pick, put-away, replenishment, cycle count, pack, load. States:
  ready -> in progress -> confirmed (or short / cancelled). **Confirming a task posts the inventory move.**
- **Inventory adjustment** - a direct write to on-hand (quantity or status) under a reason code, with no
  offsetting document. It is the book, corrected by fiat.

## Vocabulary that bites
(Each term is only named here; its causal chain is in Gotchas below.)
- **Available vs on-hand** - `available = on-hand - allocated - held - damaged`. "On-hand" is everything in
  the building; only *available* can be promised. That formula is the core; additional inventory-type
  qualifiers (cycle-count-pending, inspection-pending) can further restrict availability, so read the status
  split, not just the totals. Treating raw on-hand as available over-promises.
- **LPN / license plate** - a container ID, and containers nest. The gotcha is the nesting: an operation on
  a parent LPN cascades to all children.
- **Task confirmation** - the write that actually moves stock. Before confirmation a pick/put-away is only
  planned and the source location still shows the quantity. The book changes at confirm, not at release.
- **Wave release** - not a report run. Release **allocates** on-hand to the released orders and **generates
  work**; committed stock leaves the available pool for everyone else.
- **Order streaming** - continuous release. Allocation commits the instant an order streams; there is no
  wave sitting in "planned" that you can hold to reprioritize.
- **Allocation / de-allocation** - reserve / un-reserve stock to an order. De-allocating after picking has
  started frees the reservation but does not physically return already-picked stock.
- **Hold / inventory hold** - a status that makes stock unavailable **without moving it** (QA, recall,
  quality, damage). Physically there, invisible to allocation and ATP. Distinct from an **order hold**, which
  blocks an order from allocating but does not touch stock ATP: an inventory hold removes stock from the
  available pool, an order hold only pauses one order.
- **Damaged / QA (unavailable) status** - counted in a raw on-hand total but excluded from allocation. A
  net-available read that includes damaged over-promises.
- **Short pick / short** - the picker cannot find the allocated quantity. The order goes short and either
  re-allocates from another location or back-orders; the usual root cause is on-hand overstated by a missed
  prior adjustment.
- **Replenishment (replen)** - a move from reserve to active pick locations to feed picking. Confirming a
  replen is a real move; planned against stale reserve on-hand it can leave the pick face short.
- **Cycle count** - a count of a location/LPN. If the count differs and is approved it **posts an
  adjustment**; the count is a write, not a look.
- **Cross-dock** - received stock allocated straight to an outbound order, skipping put-away to storage.
- **Manifest / ship confirm** - the outbound close. Ship confirm posts the **goods issue** to the ERP; once
  manifested / tendered / picked up the shipment has left the system's control.

## Operations: read / write / destructive
Classify every operation family by what it does to on-hand and to the ERP. Kinds of action, not tool names.

| Class | Manhattan Active WM operation families | Gate | Why |
|---|---|---|---|
| **Read** | inventory / on-hand inquiry by item, location, or LPN; LPN track / contents; order, wave, and work/task status; ASN and receipt inquiry; location/zone setup view; cycle-count and adjustment history / audit trail; dashboards and reports | always pass | no state change; read on-hand before every write and re-read at execute |
| **Write (reversible)** | build or edit a wave template / order-streaming rule before release; create or edit an outbound order before allocation; assign / re-assign work to a user or zone (labor routing, no stock move); create a cycle-count request before counting; place or lift an **order** hold before allocation | gate one at a time | uncommitted planning or labor routing; low blast, no inventory moved yet |
| **Write (committing)** | **wave release / order streaming allocation** (reserves on-hand, generates work, starves the pool for others); confirm a **pick** (source location decrements, stock rides the pick/stage LPN); confirm a **put-away** or **replenishment** (physical move posts); **receive** against ASN/PO (creates LPN + inventory, publishes a goods receipt to the ERP); **pack** into a shipping carton; place an **inventory hold** or change status to unavailable (removes ATP) | gate + human approve | binds the physical world or commits stock; each publishes an inventory transaction to the ERP |
| **Destructive / irreversible** | **inventory adjustment** up or down (overwrites on-hand, no offset, posts loss/gain + ERP value doc); **cycle-count variance posting** (writes an adjustment); **ship / load / manifest confirm** (goods issue to ERP, then carrier owns it); **cancel a wave or de-allocate after picking started** (strands staged stock); **cancel a staged / loaded shipment**; **void / consume an LPN**; **force-close or short-close** an order or task; **release held / damaged stock to available** without resolving the reason; **status down-adjustment** (available -> damaged); **attribute correction** (re-lot / re-date / re-serialize existing stock, which mis-drives FEFO/FIFO) | hard gate + named approver + re-read on-hand | overwrites the book, records a real loss/gain, or crosses a point of no clean return |

**Gate semantics:** "gate one at a time" means confirm each write with the approver and see it execute
before starting the next, never batch a run of reversible writes on one approval.

**Hold-release reclassification:** releasing a hold *with* a resolved disposition (QA passed, recall
cleared) is a **committing** write, not destructive: it returns ATP and publishes a status change, so gate
it normally. The **destructive** case is flipping held or damaged stock to available *without* resolving the
reason, because that puts unusable stock back into ATP.

Universal rules to teach: read on-hand **before every write and re-read at execute** because on-hand drifts
between read and confirm (another wave, another task, a count in flight). A **hold means stop** - do not
lift it to make an allocation succeed. Never adjust WMS on-hand purely to force a match with the ERP; that
writes a phantom loss or gain. Never split a large down-adjustment into small ones to slip under an approval
threshold; it is the same write with extra steps and it is auditable.

## Gotchas that bite (the causal chains)
Each is action -> hidden effect -> downstream consequence. The normative rule lives here; the vocabulary
list above only names the term.
1. **An inventory adjustment writes the book directly with no offsetting document.** A down-adjustment removes that quantity from available and ATP immediately, records a loss, and once published posts an inventory + value document to the ERP. There is no undo, only a new opposite adjustment.
2. **Available is not on-hand.** `available = on-hand - allocated - held - damaged`. A read that treats raw on-hand as promiseable over-commits stock that is reserved, held, or unusable.
3. **Wave release allocates and can starve other orders.** Release reserves on-hand to the released lines first-come; a large or careless wave commits stock a higher-priority order needed, and that stock is now unavailable until de-allocation.
4. **Task confirmation is the moment stock moves, not planning.** Until a pick is confirmed the source location still shows the quantity; two flows can both plan against it and one will short-pick at confirm.
5. **On-hand goes stale between read and execute.** A concurrent task, wave, or count changes it; an allocation staged against a stale read short-picks. Re-read on-hand at execute.
6. **Held and damaged stock are present but not available.** A hold removes stock from ATP without moving it; allocating or promising against held or damaged stock fails at pick or ships bad product.
7. **Moving a parent LPN moves every nested child and its inventory.** A mis-scanned parent relocates far more than intended, and downstream picks against the children now point to the wrong location.
8. **A short pick means the allocation was against stock that was not physically there.** It leaves the order short and re-allocates or back-orders; the root cause is usually on-hand overstated by a missed earlier adjustment, so fixing the pick without fixing the count repeats the short.
9. **Confirming a receipt creates inventory and posts a goods receipt to the ERP.** Over-receiving beyond the ASN/PO posts inventory the ERP did not expect and a GR that finance must reconcile.
10. **A cycle count is a write.** An approved variance posts an adjustment: an over-count injects phantom inventory into ATP, an under-count writes off a loss. Counting the wrong location or LPN corrupts good inventory.
11. **De-allocating or cancelling a wave after picking started strands partially-picked stock on staging LPNs.** That stock does not auto-return home; it must be physically put away, or the pick face and staging both show wrong quantities.
12. **Ship / load confirm posts a goods issue and hands the shipment to the carrier flow.** Once manifested, tendered, or picked up it is effectively irreversible; the reversal is a return / RMA, not an un-ship.
13. **Cancelling a staged or loaded shipment is not a delete.** Staged cartons must be de-staged and unpacked and a loaded shipment must be unloaded and de-manifested before the order can cancel; skip that and the book reads shipped while the stock still sits in the building.
14. **Releasing held or damaged stock to available without clearing the reason puts unusable stock back into ATP.** The hold existed for a reason (QA, recall, damage); lifting it to make an allocation succeed ships bad stock.
15. **A down-adjustment above a threshold is high blast.** It removes promised ATP, can un-allocate committed orders, and posts a material loss to finance. Size it and confirm the physical count before posting.
16. **A replenishment planned against stale reserve on-hand moves stock a concurrent adjustment already removed,** leaving the active location short exactly when picking needs it.
17. **Inventory attributes are part of on-hand identity.** Allocating or adjusting without matching lot / serial / expiry nets across different lots and can pick expired or wrong-lot stock; FEFO / FIFO holds only if attributes are respected.
18. **Order streaming commits allocation the instant an order streams.** There is no discrete wave to hold, so you cannot pause and reprioritize the way batch waving allows; reprioritization means de-allocation, which strands work.
19. **Active WM is the on-hand system of record; the ERP mirrors it.** When they disagree, WMS on-hand is operational truth for picking and the ERP holds valuation. Reconcile the transaction gap; never adjust one side just to make the numbers match.
20. **Force-closing or short-closing a task changes what the book thinks moved.** Reassigning work is only labor routing and moves nothing, but a force-complete posts a move that may not have physically happened.
21. **A raw inventory read includes damaged and QA stock in the total.** Netting available from that total, rather than from the available status, over-promises stock that cannot be allocated.
22. **Serial / lot capture at pick or pack binds a specific unit to the order.** Confirming the wrong serial mis-ships and corrupts the serial trail; for regulated goods (pharma, hazmat, cold chain) that is a compliance break, not just a data error.
23. **A retried confirmation double-posts.** A network retry on a pick confirm, ship confirm, or adjustment can post the move twice, creating phantom inventory or a double goods-issue to the ERP. Treat a repeated confirmation as a destructive risk: before retrying, check whether the first call already posted rather than re-confirming blindly.

## Edge states & special cases
Each breaks naive "quantity at a location" logic. Key rule inline; deep mechanics in the references.
- **Nested LPNs** - a pallet holds case LPNs holds units. An operation on the parent cascades. See `references/wave-and-task-lifecycle.md`.
- **In-transit inventory** - stock on an unconfirmed move task is still on-hand at the **source** location on the book (it has not moved yet) but is reserved for the move, so it is not freely allocatable at either end; do not double-count it as available at the destination before the task confirms.
- **Short / partial picks** - the order splits into shipped-short plus a re-allocation or back-order; do not treat a short as a data glitch, it signals an on-hand overstatement.
- **QA / recall / damage holds** - present but unavailable; releasing to available needs the disposition resolved, not a status flip.
- **Cross-dock** - received stock allocated straight to outbound, skipping put-away; the receipt and the pick collapse into one flow.
- **Cycle count classes** - ABC count frequency by velocity; a high-velocity location counted mid-shift catches in-flight moves and can post a false variance.
- **Kitting / value-added services** - components consumed to build a kit; the kit is new on-hand and the components are gone, a two-sided inventory event.
- **Split allocation** - one order line filled from several locations/LPNs; each pick confirms independently and any one can short.
- **Inter-DC / intra-company transfer** - stock moving between facilities is in-transit and belongs to neither node's on-hand until the destination receives it; counting it as available at either node double-counts or over-promises.

## Freshness & reconciliation
On-hand is a moving target. Between the read that planned an action and the confirm that executes it, waves,
tasks, receipts, and counts all mutate the same numbers. Re-read on-hand at execute, not just at plan. When
WMS and ERP disagree, the difference is almost always in-flight transactions (a receipt or shipment not yet
published, or published and not yet posted). Real-time events publish in seconds to minutes; batch or
interface-based postings can lag hours, so a gap is not a true discrepancy until that publish window has
passed. A re-read narrows the race but does not close it: Active WM does not hard-lock a location during
picking, so a concurrent task can confirm between your re-read and your write, which is why a short pick can
still happen after a fresh read. Reconcile the transaction stream; treat a raw quantity delta as a symptom to investigate, never as a
number to force-match with an adjustment.

## Recovery patterns (can it be undone, and what cannot)
- **Inventory adjustment** - correcting a wrong adjustment is a **new opposite adjustment** under a correcting reason code that references the original adjustment ID, not an undo; both stay in the audit trail, and if the first already published to the ERP the correction publishes again (two postings). If the physical stock is truly gone, no adjustment restores it.
- **Cycle-count variance** - re-count and post a correcting adjustment; the first variance already hit ATP and the ERP.
- **Confirmed pick / put-away / replen** - reverse with a new move task or an adjustment; the inventory move and any ERP posting already went, so this is a compensating action, not a rollback.
- **Ship / load confirm** - un-ship or de-manifest only while the carrier has not taken it; after tender / pickup the only path back is a return / RMA into receiving.
- **Wave cancel / de-allocation** - the irreversibility is **physical, not logical**: the book reservation frees cleanly, but stock already pulled is stranded on staging LPNs and must be physically put away to reconcile; it does not auto-return home.
- **Attribute correction / status down-adjustment** - re-lotting, re-dating, or an available -> damaged flip is corrected only by a further attribute/status write under a reason code; the mis-driven FEFO/FIFO picks it may have already caused (expired or wrong-lot stock shipped) cannot be recalled from the WMS.
- **Void / consume LPN** - the LPN identity is gone; its inventory must be re-established under a new LPN via receipt or adjustment.
- **Cross-system split-brain** - if a ship confirm posts the goods issue to the ERP but the WMS status update fails, the ERP believes the shipment left while WMS still shows it staged. Do not re-confirm blindly (that double-posts the goods issue); reconcile from the ERP posting and correct the WMS status to match the physical reality.

## Guardrails
- Read on-hand and its available/held/damaged split before acting, and re-read at execute; state drifts.
- Size every adjustment before posting: know the quantity, the reason code, and the loss/gain, and re-count the location to confirm the physical quantity first. A down-adjustment above a set limit is high blast (removes ATP, un-allocates orders, posts a loss) and needs a named approver and that confirmed count.
- A hold means stop. Resolve the disposition (release to good, scrap, or return) rather than flipping held or damaged stock to available to make an allocation or wave succeed.
- Do not cancel a staged or loaded shipment without de-staging / unpacking / de-manifesting first, or the book ships stock still in the building.
- Never adjust WMS on-hand purely to reconcile an ERP mismatch, and never split an adjustment to dodge an approval threshold.
- Treat wave release, allocation, and every task confirmation as committing: they move physical stock and publish to the ERP. For anything in the destructive row: named approver, re-read, logged reason code.

## References (load on demand)
- `references/wave-and-task-lifecycle.md` - wave vs order-streaming release, the work/task state machine, allocation and short-pick mechanics, nested-LPN moves, cross-dock.
- `references/adjustment-and-count-classes.md` - inventory adjustment classes and reason codes, cycle-count posting, holds and status changes, LPN void/consume, and how each publishes to the ERP.
