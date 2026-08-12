# Oracle ERP - Inventory and costing

Where "quantity on hand at a price" is wrong, and which inventory moves post to the ledger. Read when a
workflow reads on-hand, transacts material, or reasons about item cost, consigned stock, or multi-org.

## Contents
- On-hand vs available
- Material transaction families
- Reservations
- Consigned inventory
- Costing methods and variances
- Multi-org / MOAC

## On-hand vs available
- **On-hand** is the physical quantity in a subinventory/locator. **Available** subtracts reservations and
  excludes stock that is not usable: consigned, stock in an inspection/hold subinventory, or not-yet-delivered
  receipts. **Available-to-transact** and **ATP** are the numbers to promise against, not on-hand.
- Lot/serial/revision-controlled items cannot transact without their control attribute; the usable quantity is
  the on-hand *of the right lot/serial*, not the item total.

## Material transaction families
- **Receipt into inventory** (from a PO deliver, or a miscellaneous receipt) - + on-hand; may accrue/post cost.
- **Issue** (miscellaneous issue, issue to an account/project, sales-order issue/COGS) - - on-hand; expense/COGS.
- **Subinventory transfer** - moves stock between subinventories/locators; availability can change (e.g. into
  or out of a hold subinventory) with no value change.
- **Inter-organization transfer** - moves stock between inventory orgs; can post in-transit and intercompany.
- **Cycle count / physical inventory adjustment** - reconciles system to counted; posts an adjustment and a
  variance to the ledger. This is a committing/destructive posting, not a display.
- Gating note: receipts, issues, transfers, and adjustments update on-hand and (for costed orgs) post to the
  ledger. An adjustment or a miscellaneous issue is committing; a count adjustment that writes off stock is
  destructive.

## Reservations
- A **reservation** soft-allocates on-hand to a specific demand (sales order, work order). Reserved quantity is
  on-hand but not available to other demand. Deploying reserved stock elsewhere over-promises.

## Consigned inventory
- **Consigned** stock physically sits in your subinventory but is **owned by the supplier** until you consume
  it. The **consumption** transaction transfers ownership to you and creates the payable (self-billed / aging
  based). Counting consigned stock as owned overstates inventory value and the balance sheet.

## Costing methods and variances
- **Standard cost** - each item has a frozen standard. A receipt or invoice at an off-standard price posts a
  variance: **Purchase Price Variance (PPV)** at receipt, **Invoice Price Variance (IPV)** at invoice match.
  Stock value stays at standard; the P&L absorbs the difference.
- **Average cost** - the item value is the running average; a receipt at a different price **moves the
  average**. A small-quantity receipt at an outlier price can distort the whole on-hand value.
- **FIFO / Actual** - value tracked by layer/actual cost.
- A **standard-cost update** or a cost adjustment **revalues** on-hand inventory and posts the revaluation - a
  committing/destructive financial action, not a display refresh.
- Rule: know the costing method (and cost organization) before reasoning about "cost" or the effect of a move.

## Multi-org / MOAC
- Data is partitioned by **inventory organization** (and, upstream, **Business Unit** in Fusion / **Operating
  Unit** in EBS). **Multi-Org Access Control** (a data access set) bounds which orgs' stock and transactions
  you can see and post.
- Consequence: an on-hand read or a transaction against the wrong org shows nothing or posts to the wrong
  books. Confirm the org context before reading or transacting.
