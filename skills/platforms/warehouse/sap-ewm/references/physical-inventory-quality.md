# SAP EWM - physical inventory, differences, quality inspection, scrap

The count-and-disposition surface: how EWM counts stock, where differences accrue, when a difference becomes a
booked loss, and how quality-inspection stock is released or rejected. Read when a task touches physical
inventory, a stock difference, quality-inspection stock, a usage decision, or scrap.

## Contents
- Physical-inventory (PI) procedures
- The difference analyzer and clearing to ERP
- Quality inspection and the usage decision
- Scrap

## Physical-inventory (PI) procedures
EWM runs its own physical inventory over bins and HUs, independent of the ERP count. Common procedures:
- **Periodic** - a full count at a point in time (year-end / period-end).
- **Continuous / cycle counting** - count classes (ABC) by velocity spread across the period; high-velocity
  bins counted more often.
- **Low-stock check** - count triggered when a bin drops below a threshold, when the count is cheapest.
- **Putaway PI** - count a bin at the moment of putaway, when it is already being handled.
- **Threshold / ad-hoc** - triggered by an exception.
A PI document names the bins / HUs to count. Counting a high-velocity bin mid-shift can catch in-flight moves
and post a false variance - reconcile against open tasks before treating a delta as real.

## The difference analyzer and clearing to ERP
- A counted quantity that differs from book creates a **difference**, parked in a **differences bin** and
  surfaced in the **difference analyzer**. At this stage it is not yet a loss - it is a pending count result.
- **Posting / clearing** the difference writes the EWM book and posts to the ERP MM-IM: an over-count injects
  stock and a value document; an under-count writes off a loss and a value document. This posting is the loss
  or gain being **booked** - it is destructive, not housekeeping, and needs a re-count and a named approver
  first.
- Once posted to the ERP the difference is booked; correct it only by a new count or an opposite adjustment.
  If the physical stock is genuinely gone, no posting restores it.
- Never post a difference purely to force EWM and the ERP to match; a raw delta is usually in-flight
  transactions (a decentralized queue not yet drained), not a real loss. Reconcile the transaction / queue
  first, and never split a large difference into small ones to slip under an approval threshold.

## Quality inspection and the usage decision
- Received or in-process stock can be held in **quality-inspection stock type (Q)** - physically present but
  excluded from outbound and ATP. EWM carries the warehouse-side inspection (QIE / integration with QM); the
  inspection plan and master live in QM (`sap-qm`).
- The **usage decision** drives the disposition posting change:
  - **Accept** -> posting change Q -> F1 (unrestricted); the stock enters ATP and, crossing the ERP category,
    posts to the ERP IM.
  - **Reject** -> posting change to blocked, scrap, or return.
- Releasing Q stock to available without the usage decision, or overriding a reject to unrestricted, puts
  uninspected or failed stock into the available pool - a destructive action, because ATP now contains stock
  that should not ship.

## Scrap
- Scrapping stock is a goods issue to scrap: it removes the quant, posts a loss, and writes an ERP material
  and value document. It destroys stock and value irreversibly - it is a loss, not a correction.
- Size the scrap and confirm the physical quantity before posting; it needs a named approver and a logged
  reason. There is no undo - only a new receipt or adjustment can re-establish stock, and only if it physically
  exists.
