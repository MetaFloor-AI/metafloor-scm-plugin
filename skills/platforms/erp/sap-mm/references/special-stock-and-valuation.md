# SAP MM — special stock, valuation, batch/serial

The cases where "quantity on hand at a price" is wrong. Each changes ownership or value, so a naive
netting/costing/deploy read misfires. Read when a workflow touches consignment, subcontracting, project
stock, split-valuated materials, or batch/serial items.

## Contents
- Price control S vs V (and why the same GR posts differently)
- Split valuation
- Consignment (K)
- Subcontracting (O)
- Sales-order (E) and project (Q) stock
- Batch and serial management

## Price control S vs V
- **V (moving average)** — the material's value is the average of what's on hand. A GR at a PO price
  different from the current average **moves the average**. Small-quantity GRs at outlier prices distort the
  whole on-hand value — a costing effect, not just a line.
- **S (standard price)** — value is fixed at standard. A GR at an off-standard PO price posts the difference
  to a **price-difference (variance) account**; stock value stays at standard, the P&L absorbs the gap.
- Same physical action, different financial result. Know the price control before reasoning about "cost".

## Split valuation
One material carries several **valuation types** (e.g. in-house vs procured, origin A vs B), each with its
own price and stock. "The price" is ambiguous without the valuation type. Costing, netting, or a transfer
that ignores the type mixes values and mis-states inventory.

## Consignment (K)
Stock physically at your site but **owned by the vendor until you withdraw it**. It sits as special stock
(indicator K). It is not your inventory to value or sell as own-stock. **411 K** transfers it to own stock
(that withdrawal is the liability-creating event). Counting consignment as own-stock overstates owned
inventory and mis-values the balance sheet.

## Subcontracting (O)
You provide components to a subcontractor who returns a finished assembly. The components sit as special
stock **at the vendor** (provided-to-vendor). A subcontracting PO consumes those components on receipt of the
assembly. Reasoning about your on-hand must exclude components already at the subcontractor.

## Sales-order (E) and project (Q) stock
Stock **assigned** to a specific sales order or project (make-to-order / engineer-to-order). It is not freely
available — it cannot be deployed to another demand without an unassignment. Treating it as free stock
over-promises against other orders.

## Batch and serial management
- **Batch-managed** — every quantity belongs to a batch (shelf-life, origin, quality). A move without a
  batch fails; a wrong batch mis-assigns shelf-life/quality and can ship expired or non-conforming stock.
- **Serialized** — each unit tracked by serial number; movements record the specific units.
- FEFO/FIFO picking and shelf-life expiry only work if the batch data is respected.

Gating note: none of these change the read/write/destructive class of an action, but they change **what the
number means**. A workflow that nets or deploys stock must exclude consignment/subcontracting/assigned stock
and respect valuation type and batch — otherwise it acts on a quantity that isn't freely, cleanly available.
