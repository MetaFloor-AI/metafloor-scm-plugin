# Korber WMS - adjustments, cycle counts, holds, owner / 3PL, catch weight, and host integration

The write side that touches the book directly and the paths back to the host / ERP. Read when a workflow
adjusts inventory, posts a cycle count, places or lifts a hold, works multi-client / owner stock or catch
weight, voids an LPN, or reconciles a WMS-host disagreement.

## Contents
- Inventory adjustment classes
- Cycle count as a write
- Holds and status codes
- Owner / client segregation (3PL)
- Catch weight
- LPN void / consume
- Host / ERP integration and posting
- Split-brain recovery (inbound and outbound)

## Inventory adjustment classes
An **inventory adjustment** writes on-hand directly under a reason code, with **no offsetting document**. It
is the book corrected by fiat, and there is no undo - only a new opposite adjustment.
- **Quantity up** (found stock) - injects on-hand and posts a gain to the host; a wrong up-adjustment creates
  phantom inventory that ATP will promise and picking cannot find (a future short).
- **Quantity down** (loss / shrink) - removes on-hand and ATP immediately, can un-allocate committed orders,
  and posts a loss + host value document. A down-adjustment above the site's approval threshold is high blast.
- **Status change** (available -> damage / hold, or the reverse) - moves stock between available and
  non-available without a quantity change; flipping damage / hold to available without resolving the reason
  puts unusable stock back into ATP (destructive).
- **Attribute / owner correction** (re-lot, re-date, re-serialize, re-owner) - rewrites the identity of
  existing on-hand; wrong values mis-drive FEFO / FIFO or mis-own stock in a 3PL site, and any picks already
  made on the wrong identity cannot be recalled from the WMS.
- Rule: size the adjustment (quantity, reason code, owner, loss / gain) and **re-count the physical location
  first**; never split a large adjustment into small ones to slip under an approval threshold; never adjust
  purely to force a WMS-host match.

## Cycle count as a write
A cycle count is a count, but an **approved variance posts an adjustment** - so the variance posting, not the
request, is the write.
- **Count classes (ABC)** - count frequency by item velocity. A high-velocity location counted mid-shift
  catches in-flight moves (an open pick, a replen not yet confirmed) and can post a **false variance**;
  freeze or drain the location's open work before counting, or reconcile the in-flight moves first.
- **Over-count** injects phantom inventory into ATP; **under-count** writes off a loss. Counting the wrong
  location or LPN corrupts good inventory.
- A short pick should trigger a count of the short location - the short signals on-hand was overstated, and
  re-picking without re-counting repeats it.

## Holds and status codes
A hold makes stock unavailable **without moving it**; it stays physically in place but leaves ATP.
- Statuses (available, hold, QA / QC, damage, and site-configured others) split on-hand into available and
  non-available. The set is configurable, so treat an unfamiliar status as non-available until confirmed.
- **Inventory hold** removes stock from ATP; an **order hold** only pauses one order from allocating and does
  not touch stock ATP. Do not conflate them.
- **Releasing a hold** is committing when the disposition is resolved (QA passed, recall cleared) and
  **destructive** when it is not (unusable stock back into ATP). Resolve the reason, do not flip the status.

## Owner / client segregation (3PL)
Korber's ex-HighJump / Accellos heritage makes multi-client 3PL buildings common. On-hand belongs to a
specific **owner / client**, often segregated by zone.
- The owner is part of on-hand identity, like lot or status. Allocation, adjustment, and movement must carry
  the owner; allocating client A's order against client B's stock mis-owns inventory.
- Adjustments and storage moves feed **client billing** (storage, handling, activity charges); a wrong owner
  or a phantom adjustment corrupts the client's invoice, not just the book.
- A re-owner (moving stock from one client to another) is a destructive write - it changes whose inventory
  and whose bill; gate it with a named approver and a reason.

## Catch weight
A **catch-weight** item (variable-weight food / grocery) is tracked in dual UOM: a nominal count and an actual
weight. The weight must move with the count on every transaction.
- Receiving captures the actual weight; picking / shipping must carry it. Adjusting, allocating, or shipping
  on the count alone mis-states the weight-based value and the customer invoice.
- A cycle count or adjustment on a catch-weight item must reconcile both the count and the weight, or the two
  UOMs drift apart.

## LPN void / consume
Voiding or consuming an LPN destroys its identity permanently. Its inventory must be re-established under a
new LPN via a receipt or an adjustment. Do this only when the LPN is genuinely empty or being intentionally
collapsed; voiding an LPN that still carries allocated stock strands the allocation.

## Host / ERP integration and posting
Korber is the on-hand system of record inside the four walls; the host / ERP mirrors it and holds valuation.
Movements post back to the host.
- **Receipt confirm** posts a goods receipt to the host (creates / values stock there). **Ship / load /
  manifest confirm** posts a goods issue (relieves stock, posts COGS). **Adjustments and cycle-count
  variances** post inventory + value documents.
- Integration timing: modern K.Motion deployments publish host events in near real time (seconds to minutes);
  legacy Warehouse Edge / batch-interface sites (flat file / EDI / API) can lag hours. A WMS-host gap is not
  a true discrepancy until that publish window has passed.
- A **retried** posting can double-post (a stuck / re-sent event, or a re-run confirm) - a second goods
  receipt, goods issue, or adjustment to the host. Before retrying a failed posting, check whether the first
  already posted rather than re-sending blindly.
- Reconcile the transaction stream; never adjust WMS on-hand purely to make it match the host - that writes a
  phantom loss or gain on top of a timing gap.

## Split-brain recovery (inbound and outbound)
A movement can post on one side and fail on the other, leaving the WMS and host disagreeing about the same
physical event. Do not blind-retry - re-read both sides and reconcile from whichever already posted.
- **Outbound split-brain** - ship confirm posted the goods issue to the host but the WMS status update
  failed: the host reads shipped while WMS shows staged. Correct the WMS status to physical reality; do NOT
  re-confirm the ship (that double-posts the goods issue).
- **Inbound split-brain** - the receipt / GR posted on one side but the confirmation failed on the other.
  Check whether the goods receipt already posted to the host first. If it did, correct the WMS receipt / LPN
  state to match; do NOT re-confirm the receipt (that double-posts the GR). If only WMS received and the host
  GR failed, re-trigger the host publish, not a second WMS receipt.
