# SAP EWM - stock types, posting changes, GR/GI to ERP, integration

How EWM stock maps to ERP stock, which actions cross into the ERP ledger, and how embedded and decentralized
deployments differ. Read when a task changes stock type / status, posts a goods receipt or issue, or when EWM
and the ERP disagree.

## Contents
- EWM stock types and availability groups
- What is ERP-relevant vs internal
- Posting changes
- Goods receipt (GR) posting to ERP
- Goods issue (GI) posting to ERP
- Embedded vs decentralized integration and queues

## EWM stock types and availability groups
- EWM **stock type** encodes availability and category, e.g. **F1** available unrestricted-use, **Q** quality
  inspection, **B** blocked. Only available stock (F-type) is promiseable to outbound and ATP; Q and B are
  physically present but excluded from allocation. These are SAP standard codes; a custom implementation can
  define its own (F2, Z1, and so on), so read the availability-group mapping before assuming what a code means.
- The **availability group** ties an EWM stock type to an ERP storage location and stock category
  (unrestricted / quality inspection / blocked). It is the bridge that decides whether a stock change in EWM
  posts to the ERP IM and how the ERP sees the same physical quantity.
- The same physical unit therefore has an EWM view (stock type + bin + HU) and an ERP view (stock category +
  storage location + valuation). They are reconciled by postings, not automatically identical at every instant.

## What is ERP-relevant vs internal
- **Internal (no ERP posting)** - a bin-to-bin move that stays inside one ERP stock category (a putaway, a
  replenishment, an internal move, a pick to staging). The ERP does not see the bin, only the total per stock
  category, so these do not post to the ERP.
- **ERP-relevant (posts a material document)** - a goods receipt, a goods issue, and any posting change that
  crosses the ERP stock category (Q or B -> F1, or F1 -> B). These write the ERP IM and, for GR / GI, an FI
  value document.
Misjudging which class an action falls in is how EWM and the ERP quietly drift apart.

## Posting changes
A **posting change** changes stock type, owner, category, or batch **without a physical move** - the stock
stays in the same bin / HU. Examples: quality inspection -> unrestricted after a usage decision; unrestricted
-> blocked to hold; an owner change for consignment.
- If the posting change crosses the ERP stock category, it posts to the ERP IM (a material document); if it
  stays inside one category it is internal to EWM.
- A posting change from Q to F1 frees stock into ATP with no physical move - do it only when the disposition
  is resolved. Corrected only by an opposite posting change, which posts again if it crossed the ERP category.

## Goods receipt (GR) posting to ERP
- The GR is posted against the **inbound delivery** (the warehouse request replicated from the ERP PO / ASN).
  Posting the GR writes the ERP material document (movement 101 in the standard case) and an FI value
  document - it valuates the stock and hits the ledger. 101 is the default; the actual movement type is
  configurable per process (e.g. 103 / 105 for a two-step GR into blocked stock), which changes the ERP
  posting semantics.
- The GR and the putaway are separate steps. Depending on configuration the GR can be posted at receiving
  (then putaway follows) or after putaway; either way, confirming the putaway WT is the internal bin move and
  the GR posting is the ERP financial event.
- Reversing a GR posts a counter material document to the ERP; both stay in the trail, it re-values, and it
  cannot restore a quantity already picked or issued.
- An expected goods receipt or ad-hoc goods movement without a delivery / PO reference posts stock with
  nothing downstream to reconcile it (the EWM analogue of a 501 in MM) - flag it for scrutiny.

## Goods issue (GI) posting to ERP
- The GI is posted against the **outbound delivery order** after picking and staging. It posts the ERP
  material document (movement 601 for a customer issue; 641 for a stock-transport issue) and COGS - the stock
  leaves the book and the cost is recognized. The movement type is configurable per process, so read it.
- Reversing / cancelling a GI is possible only before the shipment physically departs and is a new posting.
  After tender / pickup, the path back is a return / RMA into receiving, not an un-ship.

## Embedded vs decentralized integration and queues
- **Embedded EWM** runs inside the same S/4HANA system as the ERP (available since embedded EWM's
  introduction in S/4HANA; verify the exact lower release for a given deployment). It shares the database, so
  there is no transfer queue between EWM and IM; deliveries and goods movements post in-system. EWM stock and
  IM stock are still distinct views reconciled by the GR / GI / posting change.
- **Decentralized EWM** runs as a separate system connected to the ERP by qRFC / CIF and delivery / goods-
  movement interfaces. Deliveries replicate inbound; goods movements post outbound to the ERP asynchronously.
  A stuck or backlogged queue (visible in the qRFC queue monitor) means EWM and the ERP disagree until it
  drains - the gap is in-flight, not a true discrepancy, until the queue clears.
- A **retried goods movement** in decentralized EWM (a re-sent stuck queue entry, or a re-run GR / GI) can
  post the ERP material document twice. Before retrying a failed posting, check the queue and the monitor to
  confirm the first did not already post rather than re-posting blindly.
- **Split-brain**: if a GI posts to the ERP but the EWM status update fails (or the reverse), one side reads
  shipped and the other staged. Reconcile from the posted side and correct the other; do not re-post.
