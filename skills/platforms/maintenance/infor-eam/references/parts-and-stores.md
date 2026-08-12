# Infor EAM parts and Stores - balances, transactions, part types

Where "a quantity of a part" is not a simple number. Every balance is **per store** and per **organization**,
availability is derived, and most transactions post to a cost account at the same time. Read when a workflow
reserves, issues, returns, transfers, receives, counts, or reorders spare parts, or touches a rotating /
repairable part.

## Contents
- Balances: on-hand, reserved, available
- The store transactions and their class
- Costing methods (what an issue costs)
- Part types: stock, direct / non-stock, rotating / repairable
- Reorder, preferred store / supplier, and organization scope

## Balances: on-hand, reserved, available
- **On-hand** - the physical quantity in the store. It is not what you can freely use.
- **Reserved** - quantity committed to WOs. A WO's planned stock parts reserve at **release**; a reservation
  can also be made manually.
- **Available** = on-hand - reserved. This is what a new WO can actually take. Reading on-hand and treating it
  as free over-promises; a competing reservation shorts you at issue.
- Balances are per **store** and per **organization**. There is no single global "on hand" for a part.

## The store transactions and their class
- **Reserve** - committing; removes quantity from available for others. Reserved is not issued.
- **Issue** - committing + costed; deducts on-hand and **charges the WO's cost account**. Issuing to the wrong
  WO mischarges the wrong asset. There is no un-issue, only a return.
- **Return** - a counter-transaction to an issue; credits the WO and restores balance under a reason code.
  Both the issue and the return stay in history. A consumed part cannot be returned; a **repairable** unit
  returns to its condition bin, not to good stock.
- **Receipt** - committing; increases balance from a PO (or charges a WO directly for a direct / non-stock
  part) and posts received-not-invoiced. Over-receipt or a wrong store injects stock finance must reconcile.
- **Store-to-store transfer** - committing; moves balance between stores. Creates **in-transit** stock: it
  leaves the source at once but is not available at the destination until received there. Do not count it at
  both ends.
- **Physical inventory / balance adjustment** - **destructive**; overwrites the store book directly under a
  reason code and posts a **variance** with no offsetting document. A wrong count is a real loss or a phantom,
  correctable only by a further adjustment. Never adjust to match the ERP.

## Costing methods (what an issue costs)
The part / store costing method sets the value an issue posts:
- **Average** - each receipt moves the average, so an issue's cost depends on receipt timing.
- **Standard** - value fixed at standard; an off-standard receipt posts a variance and the stock value stays
  at standard.
- **Actual / last-cost** style methods draw the specific or most-recent cost.
Know the method before reasoning about maintenance cost or a variance - "the cost" is ambiguous without it.

## Part types: stock, direct / non-stock, rotating / repairable
- **Stock part** - normal inventory held in a store with a balance and a reorder point.
- **Direct / non-stock part** - bought **straight to the WO** on receipt of its PO; never enters store
  balance. Not available to any other WO. Treating it as stock double-counts.
- **Rotating / repairable part** - a serialized unit with a tracked **condition** (new / repairable /
  rebuilt). Issuing it moves the unit to the WO / equipment and its history follows it; returning a failed
  unit puts it in the repairable bin, not good stock. Treating it as a plain consumable loses the unit
  history and overstates serviceable stock.

## Reorder, preferred store / supplier, and organization scope
- **Reorder point / min-max** - when available falls below the reorder point, an automatic **requisition**
  generates up to the reorder quantity. Issuing scarce stock can silently trip this and start a spend cycle.
  A part can be flagged to **prevent reorder** (still orderable manually).
- **Preferred supplier / preferred store** - the requisition routes to the preferred supplier; if a
  **preferred store** is set, the replenishment is a **store-to-store transfer** instead of a purchase.
- **Organization scope** - a part's balance, its costing, and its cost account are org-scoped. A read that
  nets balances across organizations treats separately-held, separately-valued stock as one pool, which it is
  not; a shortage in one org is not filled by another's balance without a transfer.
