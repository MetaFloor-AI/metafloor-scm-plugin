# NetSuite OneWorld, costing, and inventory

The cases where a naive read of "which entity, at what cost, how much on hand" is wrong. Read when a
workflow spans subsidiaries, values inventory, or moves lot/serial/multi-location stock.

## Contents
- OneWorld subsidiaries and currency
- Intercompany and elimination
- Costing methods (and why the cost is ambiguous)
- Negative inventory and the true-up
- Locations, bins, lot and serial

## OneWorld subsidiaries and currency
- **Subsidiary** is a required dimension on every transaction in OneWorld - the legal entity it belongs to.
  It is set at creation and generally **cannot be changed after the transaction posts**; a wrong subsidiary means void/delete and re-enter.
- Each subsidiary has a **base currency**. A transaction posts in the subsidiary's currency; the item/customer/vendor may transact in a different currency, converted at the transaction-date exchange rate.
- Consolidated reporting rolls subsidiaries up a **hierarchy** and translates each into the parent's currency using **consolidated exchange rates** set during close.
- Access is scoped: a role restricted to certain subsidiaries cannot see or post to others. A number that looks missing may be a subsidiary you cannot see, not an absent record.

## Intercompany and elimination
- An **Intercompany Journal Entry** posts in two subsidiaries at once and must balance across them.
- Intercompany transactions (sales/purchases between subsidiaries) create receivable/payable pairs that
  must **eliminate** in consolidation so the group is not counted trading with itself.
- Elimination runs at period close through the **elimination subsidiary**; until it runs, consolidated
  statements overstate revenue/expense by the intercompany volume. Confirm both legs balance and elimination is configured before trusting a consolidated figure.
- Elimination **requires a configured elimination subsidiary** to exist in the hierarchy. If none is set up,
  the period-close elimination step fails with no clean diagnosis - a missing elimination subsidiary is a common cause of a stuck close.

## Costing methods (and why the cost is ambiguous)
Set on the item, **frozen once transactions exist**:
- **Average** - value is the moving average of what is on hand; a receipt at an off-average cost moves the average.
- **FIFO / LIFO** - value follows the cost layers in first-in / last-in order (LIFO is US-only and rarely configured; IFRS prohibits it).
- **Standard** - value is a fixed standard cost; a PO/bill gap posts to a **purchase price variance** account, so the item value stays at standard and the P&L absorbs the difference.
- **Group Average / Lot / Serial** - group or specific-unit costing for lot- and serial-numbered items.

Consequence: "the cost" is meaningless without the method. Costing or margin math that ignores it (for
example treating a Standard-cost item's value as actual cost) is wrong, and the real variance sits in a separate account.

## Negative inventory and the true-up
NetSuite allows on-hand quantity to go **below zero** (a fulfillment or issue before the receipt posts). When it does:
- COGS books at an **estimated** cost (last purchase or current average), because there is no real cost layer yet.
- When the receipt finally posts, NetSuite creates **inventory cost-adjustment** postings to true up the earlier estimate.
- So COGS and margin for the negative period are provisional until the receipt lands. The period-close
  checklist's **Review Negative Inventory** step exists to catch this before close.

## Locations, bins, lot and serial
- **Multi-location inventory** - on-hand is tracked **per location**; the company-wide total is not all available at one site. Net by location before promising stock.
- **Bins** - a further subdivision within a location; advanced bin / WMS adds putaway and picking bins.
- **Lot-numbered** - each quantity belongs to a lot (expiry, origin). A move must name the lot; FEFO/expiry logic depends on lot data being present.
- **Serialized** - each unit tracked by serial number; every movement records the specific units. A fulfillment or adjustment without the lot/serial fails or misassigns.

Gating note: none of these change whether an action is read/write/destructive, but they change **what the
number means**. A workflow that nets, costs, or deploys stock must scope by subsidiary and location, respect
the costing method, and supply lot/serial - otherwise it acts on a quantity or cost that is not cleanly comparable.
