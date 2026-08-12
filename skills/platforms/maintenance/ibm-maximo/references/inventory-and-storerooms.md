# Maximo MRO inventory and storerooms - balances, transactions, item types

Where "a quantity of a part" is not a simple number. Every balance is per storeroom and per site, availability
is derived, and most inventory transactions post to a GL account at the same time. Read when a workflow
reserves, issues, returns, transfers, receives, counts, or reorders spare parts, or touches a rotating asset.

## Contents
- Balances: current, reserved, available
- The inventory transactions and their class
- Costing types (what an issue costs)
- Item types: stocked, direct-issue, special-order, rotating
- Reorder and multi-site scope

## Balances: current, reserved, available
- **Current balance** - the physical quantity in the storeroom bin(s). It is not what you can freely use.
- **Reserved** - quantity committed to WOs by **hard** reservations. Created at WO approval or manually. A
  **soft** reservation is only a plan and does not decrement availability.
- **Available balance** = current - hard reserved. This is what a new WO can actually take. Reading current
  balance and treating it as free over-promises; a competing reservation shorts you at issue.
- Balances are per **storeroom** and per **site**. There is no single global "on hand" for an item.

## The inventory transactions and their class
- **Reserve (hard)** - committing; removes quantity from available for others. Reserved is not issued.
- **Issue** - committing + costed; deducts current balance and **charges the WO's GL account**. Issuing to the
  wrong WO mischarges the wrong asset. There is no un-issue, only a return.
- **Return (RTN)** - a counter-transaction to an issue; credits the WO and restores balance under a reason
  code. Both the issue and the return stay in history. A consumed part cannot be returned.
- **Receipt** - committing; increases balance from a PO and posts received-not-invoiced (RBNI). Over-receipt
  or a wrong storeroom injects stock finance must reconcile.
- **Transfer** - committing; moves balance between storerooms. Creates **in-transit** stock: it leaves the
  source at once but is not available at the destination until received there. Do not count it at both ends.
- **Adjustment / physical count reconciliation (current-balance adjust)** - **destructive**; overwrites the
  book balance directly under a reason code and posts a **GL variance** with no offsetting document. A wrong
  count is a real loss or a phantom, correctable only by a further adjustment. Never adjust to match the ERP.

## Costing types (what an issue costs)
The storeroom's costing type sets the value an issue posts:
- **Standard** - value fixed at standard; a receipt at an off-standard PO price posts a variance, the stock
  value stays at standard.
- **Average (weighted)** - each receipt moves the average, so an issue's cost depends on receipt timing.
- **LIFO / FIFO** - cost drawn by layer order. As with average, the number an issue posts is not "the price"
  without knowing the costing type.
Know the costing type before reasoning about maintenance cost or a variance.

## Item types: stocked, direct-issue, special-order, rotating
- **Stocked** - normal inventory item held in the storeroom with a balance and a reorder point.
- **Direct-issue** - charged **straight to the WO** on receipt of its PO; never enters storeroom balance. Not
  available to any other WO.
- **Special-order** - one-off purchase for a specific WO; behaves like direct-issue, no stock balance.
- **Rotating** - a serialized part that is **both an inventory item and an asset record**. Issuing it moves
  the physical serialized asset to the WO / location, and its maintenance history follows the unit. Returning
  it moves the asset back. Treating a rotating item as a plain consumable loses the asset and its history.

## Reorder and multi-site scope
- **Reorder point (ROP)** - when available balance falls below ROP, the reorder run auto-generates a PR (or a
  PO) up to the reorder quantity. Issuing scarce stock can silently trip this and start a spend cycle.
- Reorder respects the storeroom and site; a shortage in one storeroom is not filled by another storeroom's
  balance unless a transfer is set up.
- **Multi-site / multi-org** - an item's balance, its costing, and its GL account are site-scoped. A read that
  nets balances across sites treats separately-owned, separately-valued stock as one pool, which it is not.
