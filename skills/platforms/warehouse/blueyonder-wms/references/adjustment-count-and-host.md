# Blue Yonder WMS - inventory adjustments, cycle counts, holds, catch weight, and host posting

The write families that change on-hand **without a matching order or receipt**. These are the destructive
edge of the system: they overwrite the book by fiat and publish to the host/ERP. Read when a workflow adjusts
inventory, posts a cycle count, places or lifts a hold / QC / damage status, handles catch-weight stock,
voids an LPN, or reconciles against the host.

## Contents
- Inventory adjustment classes
- Reason codes
- Cycle-count posting
- Holds and status codes
- Catch weight
- ILPN / OLPN void / consume
- How each publishes to the host
- Recovery

## Inventory adjustment classes
An adjustment is a direct write to on-hand with no offsetting document. Classes by what they change:
- **Quantity up** - injects on-hand that no receipt created. It becomes available / ATP immediately. If the
  physical stock is not really there, this is a **phantom** that will cause a short pick later.
- **Quantity down** - removes on-hand. It leaves available / ATP at once, records a **loss**, and can
  **un-allocate** orders already committed to that stock. High blast: size it and confirm the physical count
  before posting.
- **Status change** - moves the same quantity between available, hold, QC, and damage. Available -> damage is
  effectively a down-adjustment against ATP plus a loss disposition; damage -> available is an up-adjustment
  into ATP and must not be used to dodge a real hold.
- **Attribute correction** - re-lots, re-dates, or re-serializes stock. Wrong attributes mis-drive FEFO/FIFO
  and can send expired or wrong-lot stock to a pick.

None of these have an undo. The correction for a bad adjustment is a **new opposite adjustment**, and both
entries stay in the audit trail forever.

## Reason codes
Every adjustment carries a reason code (found, lost, damage, count variance, expiry write-off, sample, etc.).
The reason code is not cosmetic: it routes the financial treatment on the host (scrap expense vs shrink vs
found-gain) and it is what audit reviews. Never pick a soft reason code to make a loss look smaller, and never
split one large adjustment into several small ones to slip each under an approval threshold - it is the same
write with extra rows and it is auditable.

## Cycle-count posting
A cycle count is a **write path**, not a read.
- Count entered -> compared to system on-hand -> if it differs, a **variance** is calculated -> on approval
  the variance **posts an inventory adjustment**.
- **Over-count** injects phantom inventory into ATP; **under-count** writes off a loss. Both flow to the host
  like any adjustment.
- Counting the wrong location or LPN posts a variance against good inventory - it corrupts a correct number.
- **Count classes** (ABC by velocity, set as a policy) control frequency. Counting a high-velocity location
  mid-shift catches in-flight moves (unconfirmed picks / replens) and can post a **false variance**; count
  when the location is quiet or reconcile in-flight work first.

## Holds and status codes
- Blue Yonder inventory carries a **status** (available, hold, QC, damage; the specific codes are
  configurable). A hold / QC / damage status makes stock unavailable **without moving it**. It stays
  physically in place, drops out of allocation and ATP, and shows on a raw on-hand read but not an available
  read.
- Placing a hold is a committing write (removes ATP). **Lifting a hold** to make an allocation or wave
  succeed, without resolving the underlying reason, is destructive: it returns unusable stock to ATP and ships
  bad product. Resolve the disposition (release to good, scrap, return) rather than flipping the status.
- An **order hold** is different: it pauses one order from allocating but does not change stock ATP.

## Catch weight
Food / grocery items are often **catch weight** - variable-weight, tracked in dual UOM: a nominal count (e.g.
cases) and an **actual weight**. On-hand, allocation, picking, and shipping must carry the actual weight along
with the count.
- Adjusting or shipping on the nominal count alone mis-states the weight-based value and the customer invoice
  (the customer is billed on actual weight).
- A cycle count of a catch-weight location that captures only the count, not the weight, posts a variance that
  looks right on units but is wrong on value.

## ILPN / OLPN void / consume
- **Void** an LPN (ILPN or OLPN) - the license-plate identity is discarded. Any inventory on it must be
  re-established under a new LPN via receipt or adjustment; there is no restore of the old LPN.
- **Consume** an LPN - its contents are used up (e.g. into a kit or as VAS components). The consumed inventory
  is gone from on-hand as a real event, and the kit / output is new on-hand - a two-sided inventory change.

## How each publishes to the host
Blue Yonder WMS is the on-hand system of record; the host / ERP mirrors it through published transactions.
- A **receipt** (into an ILPN) publishes a goods receipt -> host posts the inbound movement (and GR/IR against
  the PO).
- A **ship confirm** (of OLPNs on a shipment) publishes a goods issue -> host posts the outbound movement and
  COGS.
- An **inventory adjustment / count variance** publishes an inventory adjustment -> host posts the quantity
  change **and often a financial value document** (shrink, scrap, or found-gain per the reason code).
- Publishing can lag posting, and a **legacy DLx batch interface (flat file / IDoc / API) lags more than the
  cloud line's near-real-time events**. A quantity delta between WMS and host is usually an in-flight transaction not yet posted, not a
  true discrepancy. Reconcile the transaction stream; do not adjust WMS on-hand to force the host number to
  match - that writes a phantom loss or gain on both sides.

## Recovery
- **Adjustment** - new opposite adjustment; both stay in the trail; if the first published, the correction
  publishes again (two host postings). No recovery of stock that is physically gone.
- **Count variance** - re-count and post a correcting adjustment; the first variance already hit ATP and the host.
- **Status / hold** - reversible as a status write, but each flip is itself an ATP change and an audit event.
- **Catch weight** - a wrong weight is corrected by a further adjustment carrying the right weight; a shipment
  already invoiced on the wrong weight is a billing correction, not just a stock fix.
- **Void / consume LPN** - not reversible; re-establish inventory under a new LPN via receipt or adjustment.
