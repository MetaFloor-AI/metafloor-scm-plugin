# Manhattan Active WM - inventory adjustments, cycle counts, holds, and ERP posting

The write families that change on-hand **without a matching order or receipt**. These are the destructive
edge of the system: they overwrite the book by fiat and publish to the ERP. Read when a workflow adjusts
inventory, posts a cycle count, places or lifts a hold, changes inventory status, or voids an LPN.

## Contents
- Inventory adjustment classes
- Reason codes
- Cycle-count posting
- Holds and status changes
- LPN void / consume
- How each publishes to the ERP
- Recovery

## Inventory adjustment classes
An adjustment is a direct write to on-hand with no offsetting document. Classes by what they change:
- **Quantity up** - injects on-hand that no receipt created. It becomes available/ATP immediately. If the
  physical stock is not really there, this is a **phantom** that will cause a short pick later.
- **Quantity down** - removes on-hand. It leaves available/ATP at once, records a **loss**, and can
  **un-allocate** orders already committed to that stock. High blast: size it and confirm the physical count
  before posting.
- **Status change** - moves the same quantity between available, on-hold, and damaged. Available -> damaged is
  effectively a down-adjustment against ATP plus a loss disposition; damaged -> available is an up-adjustment
  into ATP and must not be used to dodge a real hold.
- **Attribute correction** - re-lots, re-dates, or re-serializes stock. Wrong attributes mis-drive FEFO/FIFO
  and can send expired or wrong-lot stock to a pick.

None of these have an undo. The correction for a bad adjustment is a **new opposite adjustment**, and both
entries stay in the audit trail forever.

## Reason codes
Every adjustment carries a reason code (found, lost, damage, count variance, expiry write-off, sample, etc.).
The reason code is not cosmetic: it routes the financial treatment in the ERP (scrap expense vs shrink vs
found-gain) and it is what audit reviews. Never pick a soft reason code to make a loss look smaller, and never
split one large adjustment into several small ones to slip each under an approval threshold - it is the same
write with extra rows and it is auditable.

## Cycle-count posting
A cycle count is a **write path**, not a read.
- Count entered -> compared to system on-hand -> if it differs, a **variance** is calculated -> on approval the
  variance **posts an inventory adjustment**.
- **Over-count** injects phantom inventory into ATP; **under-count** writes off a loss. Both flow to the ERP
  like any adjustment.
- Counting the wrong location or LPN posts a variance against good inventory - it corrupts a correct number.
- **Count classes** (ABC by velocity) set frequency. Counting a high-velocity location mid-shift catches
  in-flight moves (unconfirmed picks/replens) and can post a **false variance**; count when the location is
  quiet or reconcile in-flight work first.

## Holds and status changes
- A **hold** makes stock unavailable **without moving it** - QA, recall, quality, damage. Held stock stays
  physically in place, drops out of allocation and ATP, and shows on a raw on-hand read but not an available
  read.
- Placing a hold is a committing write (removes ATP). **Lifting a hold** to make an allocation or wave succeed,
  without resolving the underlying reason, is destructive: it returns unusable stock to ATP and ships bad
  product. Resolve the disposition (release to good, scrap, return) rather than flipping the status.

## LPN void / consume
- **Void** an LPN - the license-plate identity is discarded. Any inventory on it must be re-established under a
  new LPN via receipt or adjustment; there is no restore of the old LPN.
- **Consume** an LPN - its contents are used up (e.g. into a kit or as VAS components). The consumed inventory
  is gone from on-hand as a real event, and the kit/output is new on-hand - a two-sided inventory change.

## How each publishes to the ERP
Active WM is the on-hand system of record; the ERP mirrors it through published transactions.
- A **receipt** publishes a goods receipt -> ERP posts the inbound movement (and GR/IR against the PO).
- A **ship confirm** publishes a goods issue -> ERP posts the outbound movement and COGS.
- An **inventory adjustment / count variance** publishes an inventory adjustment -> ERP posts the quantity
  change **and often a financial value document** (shrink, scrap, or found-gain per the reason code).
- Publishing can lag posting. A quantity delta between WMS and ERP is usually an in-flight transaction not yet
  posted, not a true discrepancy. Reconcile the transaction stream; do not adjust WMS on-hand to force the ERP
  number to match - that writes a phantom loss or gain on both sides.

## Recovery
- **Adjustment** - new opposite adjustment; both stay in the trail; if the first published, the correction
  publishes again (two ERP postings). No recovery of stock that is physically gone.
- **Count variance** - re-count and post a correcting adjustment; the first variance already hit ATP and ERP.
- **Status / hold** - reversible as a status write, but each flip is itself an ATP change and an audit event.
- **Void / consume LPN** - not reversible; re-establish inventory under a new LPN via receipt or adjustment.
