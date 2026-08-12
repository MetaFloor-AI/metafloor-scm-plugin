# Canonical entities

One vocabulary every app pack maps to, so a workflow can read "an InventoryPosition"
or "a PurchaseOrder" without caring whether it came from SAP, Coupa, or Kinaxis. The
app packs (`skills/<app>-*`) own the field maps from each system's objects to these.

v1 exercises the **Source + Plan** subset the replenish→buy loop needs; the rest are
declared so later packs/workflows have a target to map onto.

| Entity | What it is | Key fields (canonical) | Write stakes |
|---|---|---|---|
| **Supplier** | a vendor you buy from | `id`, `name`, `status` (active/on-hold/pending), `site` | switching/activating one is high-impact |
| **SKU / Material** | a thing you stock or buy | `id`, `description`, `uom`, `catalog` (bool), `commodity`, `gl_account` | free-text (non-catalog) needs coding |
| **InventoryPosition** | on-hand vs. targets for a SKU at a location | `sku`, `location`, `on_hand`, `safety_stock`, `reorder_point`, `lead_time_days` | the trigger signal for replenishment |
| **Requisition** | a *request* to buy — not a commitment | `id`, `lines[]` (sku, qty, price), `status` (draft/submitted), `requester` | reversible until approved |
| **PurchaseOrder** | the commitment; sending it is money out | `id`, `supplier`, `lines[]`, `total`, `status` (draft/issued/received) | issuing = irreversible spend |
| SalesOrder | a customer's demand signal | `id`, `customer`, `lines[]`, `promise_date` | — (read in v1) |
| Forecast | expected demand over time | `sku`, `period`, `qty`, `scenario` | edit scenarios, never the live baseline |
| Shipment | goods in motion | `id`, `lane`, `eta`, `status` | expedites are high-impact |
| WorkOrder | a production order | `id`, `material`, `qty`, `due` | — (Make, roadmap) |
| Lane | an origin→destination transport path | `origin`, `dest`, `mode`, `carrier` | carrier bookings are high-impact |
| Contract | agreed price/terms with a supplier | `id`, `supplier`, `terms`, `expiry` | — (read in v1) |

## The replenish → buy loop (v1)

```
InventoryPosition (on_hand < reorder_point)      ← the signal (read, any level)
   → Requisition (draft lines to safety_stock + lead-time cover)   ← reversible
      → PurchaseOrder (issue to Supplier)         ← the gated money-out moment
```

The value/quantity the harness reads for bounded-auto limits comes from the
PurchaseOrder `total` and line `qty`. A write whose value the harness can't read
is gated (it can't confirm it's within budget).
