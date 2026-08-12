---
name: sap-ewm
description: "SAP Extended Warehouse Management (EWM) - safe operation of warehouse execution and warehouse-managed stock in S/4HANA embedded or decentralized EWM: storage bins, types, sections and activity areas; handling units (HUs) and quants; warehouse tasks (WT) and warehouse orders (WO); waves and putaway / stock-removal strategies; goods receipt and goods issue that post the ERP material document (often an FI value document); posting changes for stock type and status; physical inventory and difference clearing; and quality-inspection disposition. Use when the warehouse system is SAP EWM and the work touches a storage bin, a handling unit, a warehouse task or warehouse order, a wave, putaway or stock removal, a goods receipt or goods issue posted to the ERP, a posting change, physical inventory or a stock difference, quality-inspection stock, or the user mentions /SCWM/ transactions, /SCWM/MON, a warehouse process type (WPT), stock type F1 / Q / B, an availability group, or a quant."
---

# SAP EWM - operating it safely

SAP Extended Warehouse Management runs warehouse execution inside a warehouse number: receiving, putaway,
storage, internal moves, replenishment, picking, packing, and goods issue, down to the individual storage
bin. It is the system of record for **where a unit physically sits and how it moves inside the four walls**.
The ERP (MM-IM) does not know the bin; EWM does. Two facts make it dangerous. First, the moment stock
physically moves is **warehouse-task confirmation**, not task creation or planning - before confirmation the
source bin still shows the quantity. Second, EWM sits in front of the ERP ledger: a **goods receipt or goods
issue posted in EWM writes the ERP material document (and often an FI value document)**, and a **physical-
inventory difference posted to the ERP** books a real loss or gain. A bin-to-bin move inside EWM is
operational; a goods movement to the ERP is a financial event. This skill gives the judgment to classify
each action so the harness can gate it, plus the edge states and recovery paths that decide whether a
mistake is fixable.

## Contents
- When this applies / when NOT
- Object & state model
- Vocabulary that bites
- Operations: read / write / destructive matrix
- Gotchas that bite (the causal chains)
- Edge states & special cases
- Freshness & reconciliation (embedded vs decentralized)
- Recovery patterns
- Guardrails
- References

## When this applies / when NOT
Warehouse system is SAP EWM (embedded in S/4HANA, or a decentralized EWM system) and the work is warehouse
execution or warehouse-managed stock. When NOT:
- Non-SAP warehouse execution (LPN / license plate, wave, task confirm on Manhattan / Blueyonder / Korber)
  -> `manhattan-wms`. EWM's HU is not an LPN and its /SCWM/ model is different.
- ERP inventory **valuation**, movement types, GR/IR three-way match, release strategy, and MM posting
  periods -> `sap-mm`. EWM triggers the ERP goods movement; MM owns the movement-type semantics,
  valuation, and period close.
- Ledger-only postings, account determination, FI period close -> `sap-fi`.
- Deep quality-inspection master data, inspection plans and QM usage-decision configuration ->
  `sap-qm` (EWM carries the warehouse-side inspection and disposition move, not the QM master).
- Classification / export screening / customs -> `sap-gts`; planning / MRP / ATP strategy ->
  `sap-ibp` or `kinaxis`; carrier rating and load tendering as a planning act ->
  `sap-tm` (EWM does the physical load / staging, not the rate / route decision).

## Object & state model (reason about state, not nouns)
- **Warehouse structure** - **warehouse number** (the whole EWM facility) contains **storage types** (bulk,
  high rack, fixed-bin pick area, staging, goods-receipt zone, goods-issue zone, work center), each split
  into **storage sections** (e.g. fast / slow movers), down to the **storage bin** (the smallest addressable
  slot). An **activity area** is a logical grouping of bins across storage types for one activity (putaway,
  picking, physical inventory) - it drives work sorting and resource assignment, not physical location.
- **Quant** - the stock of one material in one bin qualified by its attributes (batch, stock type, owner,
  category). It is EWM's atom of on-hand at a location. Quants split and merge as stock moves.
- **Handling Unit (HU)** - a physical container (pallet, carton, tote) with a unique HU number holding stock
  and / or nested HUs. HUs nest: a pallet HU contains carton HUs. Everything can be HU-managed. Built from a
  **packaging specification**.
- **Warehouse request** - the delivery document EWM executes against: an **inbound delivery** (from a PO /
  ASN, replicated from the ERP) or an **outbound delivery order** (ODO, from a sales order / STO). It carries
  the expected quantity and drives task creation.
- **Warehouse task (WT)** - the atomic instruction to move a quantity or HU from a source bin to a
  destination bin (putaway, pick, replenishment, internal move), or to post a change / GR / GI. States:
  created (open) -> confirmed, or cancelled before confirm. **Confirming the WT posts the physical move**:
  source bin decrements, destination increments.
- **Warehouse order (WO)** - a bundle of WTs that form one unit of work for one operator in one visit, built
  by warehouse-order-creation rules and pulled from a **queue** by a **resource** (the operator / equipment).
- **Warehouse process type (WPT)** - the configuration key on a delivery item / movement that drives how
  warehouse tasks are created and confirmed (source / destination determination, confirmation requirement, GR
  relevance). It is config, not an operation; unexpected WT behavior (a task that auto-confirms, or targets
  the wrong bin) usually traces to the WPT, not to the stock.
- **Wave** - a grouping of outbound delivery items released together. States: created -> released ->
  in progress -> completed. **Releasing a wave generates the pick WTs** and earmarks stock for those items.
- **Stock type** - EWM's availability-and-category code, e.g. **F1** available unrestricted-use, **Q** quality
  inspection, **B** blocked. The same physical quantity is not equally usable; only available stock can be
  promised. These codes are SAP standard defaults and are client-configurable (a custom build may use F2 / Z1
  etc.), so read the **availability group** mapping before assuming a code's meaning. The availability group
  maps EWM stock types to the ERP storage location / IM stock and decides whether a change is ERP-relevant
  (see `references/stock-types-postings-integration.md`).
- **Goods movement to ERP** - the **goods receipt (GR)** posted against the inbound delivery writes the ERP
  material document (movement 101 in the standard case) and an FI value document; the **goods issue (GI)**
  against the outbound delivery posts 601 and COGS. These are the ERP-facing financial events, distinct from
  the internal WT move. 101 / 601 are the standard defaults; the actual movement type is configurable per
  plant / process (e.g. 103 / 105 for GR into blocked stock, 641 for a stock-transport issue), and it changes
  the ERP posting semantics - read it, do not assume 101 / 601.

## Vocabulary that bites
(Each term is named here; its causal chain is in Gotchas below.)
- **Warehouse task (WT)** - not a to-do. Confirming it IS the physical stock move; before confirm the source
  bin still shows the quantity. (Gotchas 1, 2, 15.)
- **Warehouse order (WO)** - the bundle of WTs an operator executes in one visit. Cancelling or
  force-completing a WO acts on all its WTs at once.
- **Handling Unit (HU)** - a container with its own ID, and containers nest. An operation on a parent HU
  cascades to every nested HU and its stock. (Gotcha 7.)
- **Quant** - stock of a material in a bin with attributes; the atom of on-hand. Batch / lot / serial ride
  the quant, so a move that ignores them nets across lots.
- **Stock type (F1 / Q / B)** - availability plus category, not a label. F1 is available to outbound and ATP;
  Q (quality inspection) and B (blocked) are physically present but not allocatable.
- **Availability group** - the key that ties an EWM stock type to the ERP stock and decides ERP relevance. A
  move that stays inside one ERP category may never post to the ERP; one that crosses categories does.
- **Posting change** - a change of stock type, owner, category, or batch **without a physical move**. It is a
  real posting; if it crosses the ERP stock category it posts to the ERP IM too. (Gotchas 5, 14.)
- **Goods receipt / goods issue posting** - the ERP-facing financial event. A confirmed putaway or pick WT is
  the internal bin move; the GR / GI is a separate posting step against the delivery that writes the ERP
  material document.
- **Activity area** - the logical bin grouping that orders and routes work. A wrong activity-area sort sends
  putaway or picking work to the wrong zone or in the wrong sequence.
- **Wave** - the outbound grouping whose **release** generates pick work and earmarks stock. Not a report run.
- **Stock removal / putaway strategy** - the rule that picks the source quant (removal: FIFO, FEFO, LIFO,
  fixed bin, partial quantity) or the destination bin (putaway: fixed bin, addition to existing stock,
  near-fixed-bin, bulk). It decides which batch / lot leaves and which bin fills.
- **Difference analyzer** - where physical-inventory count differences sit before they are posted / cleared.
  A difference is not a loss until it is posted to the ERP.
- **Interim / logical bin** - EWM's in-process bins (GR zone, GI zone, differences, clarification, work
  center). Stock in an interim bin is on the book but not yet in a final storage bin.
- **/SCWM/ transactions** - the EWM namespace. **/SCWM/MON** (warehouse monitor) is the central read and
  operational-action console; **/SCWM/PRDI** inbound delivery, **/SCWM/PRDO** outbound delivery order,
  **/SCWM/ADHU** HU maintenance.

## Operations: read / write / destructive
Classify every operation family by what it does to the quant and to the ERP. Kinds of action, not tool names.

| Class | SAP EWM operation families | Gate | Why |
|---|---|---|---|
| **Read** | warehouse-monitor (/SCWM/MON) stock / quant / bin inquiry; HU display and contents; WT / WO / resource / queue status; inbound and outbound delivery status; wave status; physical-inventory document and difference-analyzer view; storage-bin and structure display; stock overview by material / bin / HU; reports | always pass | no state change; read the quant and its stock-type split before every write, re-read at execute |
| **Write (reversible)** | create or change an inbound delivery / outbound delivery order before goods movement (escalates - see the reclassification table if the delivery already has open WTs); **create** a warehouse task (open, not yet confirmed - a plan, cancellable); build a warehouse order and assign it to a resource or queue (labor routing, no stock move); assign items to a wave before release; create a physical-inventory document before counting | gate one at a time | uncommitted planning or labor routing; nothing has physically moved yet |
| **Write (committing)** | **confirm** a warehouse task (pick / putaway / replenishment / internal move) - posts the physical bin move; **release a wave** (generates pick WTs, earmarks stock); **post a goods receipt** against the inbound delivery (writes ERP material doc 101 + FI value doc); **post a goods issue** against the outbound delivery (601 + COGS); **confirm a posting change** (stock type / status / owner - but **destructive** if it releases QI / blocked stock without the disposition resolved; see the reclassification table); **pack / build / repack an HU**; **unpack / reassign stock between HUs** (stock moves, HU identity persists) | gate + human approve | binds the physical world or commits stock; GR / GI / cross-category posting change each write the ERP ledger |
| **Destructive / irreversible** | **reverse a goods receipt** (counter material doc to ERP); **reverse / cancel a goods issue** (only before the shipment departs); **post physical-inventory differences / clear the difference analyzer** (books the loss / gain, posts to ERP MM-IM); **scrap stock** (goods issue to scrap); **cancel a confirmed warehouse task** (offsetting move, may strand stock); **force-complete / force-close a warehouse order** (posts moves that may not have physically happened); **cancel a wave or delivery after picking started**; **void / consume an HU** (destroys the HU identity, unlike an unpack, which keeps it); **release quality-inspection or blocked stock to available without the disposition resolved**; **manual stock difference / adjustment outside a PI** | hard gate + named approver + re-read | permanent trail; crosses the ERP ledger; overwrites on-hand; or puts unusable stock back into ATP with no clean undo |

**Gate semantics:** "gate one at a time" means confirm each write with the approver and see it execute before
starting the next; never batch a run of reversible writes on one approval. Re-read the quant between staged
reversible writes too - creating several warehouse tasks in a row compounds against stale on-hand, so a later
task can plan against stock an earlier confirm already moved.

**Reclassification table (same action, different class by condition):**

| Action | Condition | Class |
|---|---|---|
| Posting change (stock type / status) | stays inside one ERP stock category | reversible (internal) |
| Posting change (stock type / status) | crosses the ERP category (Q or B -> F1) | committing (frees ATP, posts to ERP) |
| Release held / QI stock to available | disposition resolved (usage decision, cleared) | committing |
| Release held / QI stock to available | disposition NOT resolved | destructive (unusable stock into ATP) |
| Edit an inbound / outbound delivery | no open WTs yet | reversible |
| Edit an inbound / outbound delivery | open WTs already exist | committing (WTs now mismatched - gotcha 25) |
| Bin-to-bin move | stays inside one ERP category | reversible-to-committing (internal move, no ERP post) |
| EWM<->ERP stock delta (decentralized) | queue not yet drained | in-flight, NOT a discrepancy (do not adjust) |

Universal rules to teach: read the quant and its stock-type / bin / HU state **before every write and re-read
at execute** because on-hand drifts between read and confirm (another wave, task, replen, or count in flight).
A **blocked bin or a hold means stop** - do not flip stock type to available to make a pick or allocation
succeed. Never post a difference or adjust EWM stock purely to force a match with the ERP; that writes a
phantom loss or gain. Never split a large down-adjustment or difference to slip under an approval threshold;
it is the same write with extra steps and it is auditable.

## Gotchas that bite (the causal chains)
Each is action -> hidden effect -> downstream consequence. The normative rule lives here; the vocabulary list
above only names the term.
1. **Confirming a warehouse task is the physical move, not planning.** Until the WT is confirmed the source bin still shows the quantity; two flows can plan against the same quant and one short-picks at confirm. Re-read the quant at execute.
2. **A confirmed WT is not the ERP goods movement.** A putaway or pick WT moves stock bin-to-bin inside EWM; the ERP material document posts only when the **goods receipt / goods issue** is posted against the delivery. Do not assume confirming a putaway posted the GR to the ERP - stock can be physically put away while the ERP still shows nothing received.
3. **A goods receipt posting writes the ERP material document plus an FI value document.** It valuates stock and hits the ledger; it is a financial event, not an internal note. In decentralized EWM it flows to the ERP via the queue and can lag; in embedded EWM it posts in the same system.
4. **Reversing a goods receipt is a counter-document, not an undo.** It posts an offsetting ERP material doc; the original and the reversal both stay in the trail forever, it re-values stock, and it cannot restore a quantity already picked, issued, or consumed.
5. **A posting change can silently free quality-inspection stock into ATP.** Changing stock type from Q to F1 without the inspection resolved promises stock still under inspection; because it crosses the ERP stock category it also posts to the ERP IM, so the availability jumps on both sides with no physical change.
6. **Stock type is availability, not a label.** F1 is promiseable; Q and B are physically present but excluded from outbound and ATP. Netting available from a raw on-hand total that includes Q / B over-promises stock that cannot be picked.
7. **Handling Units nest; an operation on a parent HU cascades to every child HU and its stock.** A mis-scanned or wrongly-posted parent relocates or posts far more than intended, and downstream picks against the children now point to the wrong bin.
8. **A physical-inventory difference is not a loss until it is posted.** A counted difference sits in the difference analyzer; posting / clearing it writes the book and posts to the ERP MM-IM (a value document). That posting is the loss or gain being booked, not housekeeping.
9. **A warehouse order bundles many warehouse tasks.** Cancelling or re-queuing the WO acts on all its WTs; force-completing a WO can post moves that did not physically happen, so the book reads moved while stock still sits in the source bin.
10. **The stock-removal strategy decides which quant and batch leaves.** FEFO / FIFO / LIFO / fixed-bin picks a specific batch or lot; overriding the source bin by hand can pick the wrong batch, break shelf-life / FEFO, and ship expired or wrong-lot stock.
11. **The putaway strategy decides the destination bin.** Forcing a different destination can violate bin capacity, mix incompatible or hazmat stock, or strand stock in a bin the removal strategy will not later find.
12. **Releasing a wave earmarks stock and generates pick work.** A large or careless wave commits stock a higher-priority order needed; that stock is no longer freely available until the wave or its tasks are cancelled, which strands partially-picked stock on staging.
13. **A goods issue posts the ERP 601 and COGS; once posted the stock has left the book.** Reversing a GI is possible only before the shipment physically departs and is a new posting; after the truck leaves, the path back is a return / RMA into receiving, not an un-ship.
14. **The availability group decides whether a change is ERP-relevant.** A bin-to-bin move inside one ERP stock category never touches the ERP; a GR, GI, or cross-category posting change does. Misjudging which posts leaves EWM and the ERP quietly disagreeing.
15. **Cancelling a confirmed warehouse task is a reversal move, not a delete.** It posts an offsetting move; stock already physically relocated must be physically moved back, and the trail keeps both tasks.
16. **Batch / lot / serial identity rides the quant.** Picking or posting without matching the attribute nets across lots; a wrong batch mis-drives FEFO and can ship expired or non-conforming stock; a wrong serial mis-ships and corrupts the serial trail (a compliance break for pharma / hazmat / cold chain).
17. **On-hand drifts between the read and the confirm.** A concurrent task, wave, replenishment, or count mutates the quant; an action staged against a stale read short-picks or short-puts. Re-read at execute, and know that EWM does not hard-lock a bin during picking, so a concurrent task can still slip in.
18. **A blocked bin or blocked stock means stop.** A bin or quant blocked for a reason (damage, count in progress, quality) is not allocatable; unblocking it to make a pick succeed puts unusable stock or an unreconciled count back into play.
19. **A manual stock difference or adjustment outside a PI writes on-hand directly with no offsetting document** and posts a value document to the ERP; there is no undo, only a new opposite posting.
20. **A retried goods movement can double-post.** In decentralized EWM a stuck queue entry that is re-sent, or a re-run GR / GI, can post the ERP material document twice, creating phantom inventory or a double goods issue. Before retrying a failed posting, check the queue and the monitor to see whether the first already posted rather than re-posting blindly.
21. **An expected goods receipt or ad-hoc goods movement without a delivery / PO reference** posts stock with nothing downstream to reconcile it (like a 501 in MM); flag it for extra scrutiny.
22. **A quality-inspection usage decision drives the disposition move.** Accept posts a change to unrestricted; reject posts to blocked / scrap / return. Overriding a reject or releasing before the decision puts failed or uninspected stock into ATP.
23. **A serial number binds one specific unit, and the serial trail is a compliance record.** Confirming a pick or posting against the wrong serial mis-ships that unit and corrupts the trail; a serial already on another HU or under a serial-status block cannot move until resolved. For pharma / hazmat / cold chain, a broken serial trail is a regulatory break, not a data error - a stricter failure than a batch mix-up.
24. **A partial confirmation / short-pick splits the quant and can strand stock.** Confirming a WT for less than the planned quantity short-ships the delivery item, splits the source quant, and leaves the remainder needing a re-pick, a re-allocation, or an exception move; the usual root cause is on-hand overstated by a missed earlier difference, so re-count the source rather than just re-picking.
25. **Editing a delivery already in execution is not benign.** Changing the quantity on an inbound or outbound delivery that already has open warehouse tasks leaves those WTs mismatched against the new quantity (an over- or under-planned putaway / pick). Re-check and adjust the open WTs after any such edit.
26. **The warehouse process type (WPT) silently governs how a task behaves.** A wrong or mis-configured WPT drives the wrong source / destination determination or an unintended auto-confirmation, so stock is moved to the wrong bin or posted without operator verification. Unexpected WT behavior is a WPT question, not a stock question - check the WPT before overriding the task.
27. **Multiple quants of one material can share a bin with different stock type, owner, or batch.** A pick or removal must select the correct quant; netting across quants can pull from quality-inspection, blocked, or vendor-owned (consignment) stock, or the wrong batch. Match the quant's attributes, do not just match the material and bin.
28. **A posted goods receipt does not mean the stock is in a storage bin or picking-available.** Until the putaway WT is confirmed the quant sits in the goods-receipt-zone interim bin; depending on configuration it is not yet allocatable to outbound. Reading the GR as "received, therefore available" over-promises stock still waiting to be put away.

## Edge states & special cases
Each breaks naive "quantity at a bin" logic. Key rule inline; deep mechanics in the references.
- **Nested HUs** - a pallet holds carton HUs holds units; an operation on the parent cascades. See `references/structure-tasks-waves.md`.
- **Interim / logical bins** - stock in a GR zone, GI zone, differences, clarification, or work-center bin is on the book but not in a final storage bin; a read that only looks at storage bins mis-locates it.
- **Quality-inspection stock (Q)** - present but not available; the usage decision drives the disposition, so release to unrestricted needs the decision, not a stock-type flip.
- **Two-step picking / consolidation** - pick to a staging or consolidation area, then a second move to the GI zone; the stock is in transit between the two confirms and allocatable at neither.
- **Cross-dock / opportunistic cross-dock** - received stock routed straight to an outbound delivery, skipping putaway to storage; the receipt and the pick collapse into one flow.
- **Kitting / value-added services at a work center** - components are consumed and the kit is new on-hand in one event; a naive read counts both the components and the kit.
- **Slotting / rearrangement** - internal reorganization moves that relocate stock without an inbound or outbound; they change the removal strategy's source without a demand behind them.
- **Batch / serial / catch-weight** - identity rides the quant; catch-weight materials carry two quantities (e.g. weight and each) and a move must carry both or the book drifts.
- **Decentralized vs embedded** - the integration lag and the same-system distinction change what "the ERP shows" means at any instant (below).

## Freshness & reconciliation (embedded vs decentralized)
The quant is a moving target: between the read that planned an action and the confirm that executes it, waves,
tasks, receipts, and counts all mutate the same numbers, so re-read at execute, not just at plan. EWM is the
on-hand / location truth for execution; the ERP holds valuation. When they disagree, the difference is almost
always in-flight transactions, and the deployment mode decides how long that lasts:
- **Embedded EWM** (inside S/4HANA) shares the database, so there is no transfer queue - but EWM-managed
  stock (in EWM stock types) and the ERP IM stock view are still distinct, reconciled by the GR / GI /
  posting change, not automatically identical at every instant.
- **Decentralized EWM** (a separate system) exchanges deliveries and goods movements over qRFC / CIF queues.
  A stuck or backlogged queue means EWM and the ERP disagree until it drains; a gap is not a true discrepancy
  until the queue has cleared. Check the queue monitor (outbound / inbound qRFC in SMQ1 / SMQ2, or /SCWM/QMON)
  before concluding a real difference.
Reconcile the transaction and queue stream; treat a raw quantity delta as a symptom to investigate, never as
a number to force-match with a difference posting or adjustment.

## Recovery patterns (can it be undone, and what cannot)
- **Goods receipt reversal** - a counter ERP material document; permanent in the trail; re-values stock;
  cannot restore a quantity already picked, issued, or consumed.
- **Goods issue reversal / cancel** - only while the shipment has not physically departed; a new posting, not
  a rollback. After tender / pickup the only path back is a return / RMA into receiving.
- **Confirmed warehouse task** - reversed by a new offsetting move task; the physical stock must be moved
  back, and both tasks stay in the trail. This is a compensating action, not an undo.
- **Confirmed WT whose physical move did not happen** (scanner error, operator skipped the bin) - distinct
  from a reversal: the book reads moved but stock still sits at the source, leaving a phantom quant at the
  destination. Do not blindly reverse. Re-read both bins, confirm the physical reality, then either complete
  the move physically or post the offsetting WT to match the book to where the stock actually is.
- **Posting change** - corrected by an opposite posting change; if the original crossed the ERP stock
  category, the correction posts to the ERP too (two postings in the trail).
- **Physical-inventory difference** - once posted to the ERP it is booked; correct it only by a new count or
  an opposite adjustment. If the physical stock is truly gone, no posting restores it.
- **Wave cancel / WT cancel after picking started** - the book reservation frees cleanly, but stock already
  pulled is stranded on staging / pick HUs and must be physically put away; it does not auto-return home.
- **Void / consume HU** - the HU identity is gone; its stock must be re-established under a new HU via receipt
  or adjustment.
- **Stuck / locked warehouse task** (neither confirmed nor cancelled, blocking further processing) - find the
  lock cause in the monitor first; if it is pre-confirmation, cancel it; if the physical move already
  happened, post a corrective WT to bring the book to reality rather than forcing the stuck one through.
- **Cross-system split-brain (decentralized)** - if a GI posts the goods movement to the ERP but the EWM
  status update fails (or the reverse), one side reads shipped while the other reads staged. Do not re-post
  blindly (that double-posts the material document); reconcile from the posted side and correct the other to
  match physical reality.

## Guardrails
- Read the quant, its stock-type split (F1 / Q / B), the bin, the HU, and the delivery status before acting,
  and re-read at execute; state drifts.
- A blocked bin, blocked stock, or quality-inspection status means stop. Resolve the disposition (usage
  decision, scrap, or return) rather than flipping stock type to available to make a pick or wave succeed.
- Treat every WT confirmation, wave release, goods receipt, goods issue, and posting change as committing;
  GR / GI / cross-category posting changes and PI-difference postings write the ERP ledger.
- Size a physical-inventory difference, a scrap, or a reversal before posting - it is a real loss / gain or a
  financial event, not a correction. Re-count the bin to confirm the physical quantity first.
- Never post a difference or adjust EWM stock purely to reconcile an ERP mismatch, and never split an
  adjustment to dodge an approval threshold. In decentralized EWM, check the qRFC queues before treating a
  gap as a real discrepancy.
- For anything in the destructive row: named approver, re-read, and a logged reason code.
- Authorization is enforced by the connected system and its role design, not assumed here. Classify the
  action's blast radius (this skill) and let the harness / connector decide whether the actor may post a GR,
  a GI, or a difference; if a write is refused, that is a permission boundary to respect, not to route around.

## References (load on demand)
- `references/structure-tasks-waves.md` - warehouse structure (number / type / section / bin / activity
  area), quant and HU model, warehouse-task and warehouse-order lifecycle, wave release, putaway and
  stock-removal strategies, interim bins, resources and queues.
- `references/stock-types-postings-integration.md` - EWM stock types and availability groups, posting
  changes, goods receipt / goods issue posting to the ERP, and embedded vs decentralized integration and
  queues.
- `references/physical-inventory-quality.md` - physical-inventory procedures, the difference analyzer and
  clearing to the ERP, quality inspection and the usage-decision disposition, and scrap.
