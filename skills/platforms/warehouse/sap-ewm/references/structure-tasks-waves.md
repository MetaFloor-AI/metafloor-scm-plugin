# SAP EWM - structure, tasks, warehouse orders, waves, strategies

The execution mechanics: where stock lives, how work is created and confirmed, and how the source / destination
bin is chosen. Read when a task touches the warehouse structure, a warehouse task or order, a wave, or a
putaway / removal strategy.

## Contents
- Warehouse structure (number / type / section / bin / activity area)
- Quant and handling unit (HU)
- Interim / logical bins
- Warehouse task (WT) lifecycle
- Warehouse order (WO), resources, queues
- Wave lifecycle (outbound)
- Putaway strategies (destination bin)
- Stock-removal strategies (source quant)

## Warehouse structure (number / type / section / bin / activity area)
- **Warehouse number** - the top-level EWM facility; all structure and stock sit under it.
- **Storage type** - an area with one behavior: high rack, bulk, fixed-bin pick area, staging, goods-receipt
  zone, goods-issue zone, work center. It governs which putaway and removal strategies apply.
- **Storage section** - a subdivision of a storage type (fast movers vs slow movers, hazmat vs standard),
  used to steer putaway.
- **Storage bin** - the smallest addressable slot. Stock physically sits in a bin. Bins carry capacity /
  weight / dimension limits that putaway respects.
- **Activity area** - a logical grouping of bins (spanning storage types) for one activity: putaway, picking,
  or physical inventory. It orders and routes work and assigns it to resources; it is not a physical place.
  A wrong activity-area sort sends work to the wrong zone or in an inefficient sequence.

## Quant and handling unit (HU)
- **Quant** - stock of one material in one bin qualified by batch, stock type, owner, and category. Quants
  split when part of the stock moves and merge when compatible stock lands together. Batch / lot / serial and
  stock type ride the quant, so they must match on every move.
- **Handling unit (HU)** - a container (pallet, carton, tote) with a unique HU number holding stock and / or
  nested HUs. HUs **nest**: a pallet HU contains carton HUs contains units. An operation on the parent (move,
  post, unpack, void) cascades to every child HU and its stock. Built to a **packaging specification** that
  defines the levels and quantities.

## Interim / logical bins
EWM routes stock through in-process (interim) bins that are on the book but not final storage:
- **Goods-receipt zone** - where received stock sits after GR and before putaway.
- **Goods-issue zone** - where picked stock stages before goods issue.
- **Differences bin** - where physical-inventory differences are parked pending clearing.
- **Clarification / work-center bins** - exceptions and value-added work.
A read that only sums final storage bins mis-locates stock sitting in interim bins.

## Warehouse task (WT) lifecycle
The WT is the atomic move instruction. Types: putaway, pick, replenishment, internal (bin-to-bin) move, plus
posting-change and GR / GI tasks.
- **Created (open)** - a planned move with a source and destination bin. Reversible: it can be cancelled
  before confirmation, and it has moved nothing yet - the source bin still shows the quantity.
- **Confirmed** - the physical move is posted: source bin decrements, destination increments. This is the
  moment stock moves. A confirmed WT is reversed only by a new offsetting move task, not a delete.
- **Cancelled** - allowed before confirmation; after confirmation the correction is a reverse move.
Confirming a putaway or pick WT is an internal EWM move; it does not by itself post the ERP goods receipt /
issue - that is a separate posting against the delivery.

## Warehouse order (WO), resources, queues
- **Warehouse order** - a bundle of WTs that form one unit of work for one operator in one visit, built by
  warehouse-order-creation rules (by activity area, sort, and limits like max weight / time). The WO is the
  executable package.
- **Queue** - WOs wait in queues; a resource pulls the next WO from its assigned queue.
- **Resource** - the operator or equipment (RF handheld, forklift) that executes a WO. Assigning or
  re-assigning a WO to a resource or queue is labor routing and moves no stock.
- Cancelling or force-completing a WO acts on all its WTs at once; a force-complete can post moves that did
  not physically happen.

## Wave lifecycle (outbound)
A wave groups outbound delivery items for coordinated picking.
- **Created** - items assigned to the wave by wave template, route, time, or manually.
- **Released** - the trigger that generates the pick WTs and earmarks stock for those items. Releasing
  commits stock: a large or careless wave can starve a higher-priority order.
- **In progress -> completed** - picking runs; the wave closes when its tasks are done.
Cancelling a wave after picking started frees the reservation but strands partially-picked stock on staging /
pick HUs, which must be physically put away.

## Putaway strategies (destination bin)
The putaway strategy decides where received stock goes:
- **Fixed bin** - each material has an assigned bin.
- **Addition to existing stock** - top up a bin already holding that material.
- **Near-fixed-bin / next empty bin** - place near the fixed bin or in the next open slot.
- **Bulk storage** - block / row storage for pallets.
Forcing a manual destination can breach bin capacity, mix incompatible or hazmat stock, or strand stock where
the removal strategy will not later find it.

## Stock-removal strategies (source quant)
The removal strategy decides which quant is picked:
- **FIFO / LIFO** - by receipt date.
- **FEFO** - by shelf-life expiration; requires batch data.
- **Fixed bin** - pick from the assigned pick face.
- **Partial-quantity / stringent-FIFO** - pick to minimize broken units or hold FIFO strictly.
Overriding the strategy's source bin by hand can pick the wrong batch, break FEFO, and ship expired or
wrong-lot stock. **Batch determination** rules sit alongside the removal strategy and can further constrain
or override which batch is selected at pick time, so an unexpected source quant often traces to batch
determination, not the removal strategy alone. Replenishment feeds the pick face from reserve so the removal
strategy has stock to pick; confirming a replen is a real move, and one planned against stale reserve on-hand
leaves the pick face short.
