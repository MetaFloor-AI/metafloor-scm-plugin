# Sourcing & availability (Manhattan Active Omni)

Read when a task turns on **where** an order sources, **whether** it can be promised, or **which**
fulfillment type applies. SKILL.md carries the judgment and the read/write/destructive matrix; this file
carries the mechanics.

## Contents
- Available-to-Commit (ATC) and ATP
- The DOM sourcing-rule engine
- Reservation: soft vs hard
- Fulfillment types
- Backorder / pre-order promising
- Node capacity and safety stock
- What each act publishes

## Available-to-Commit (ATC) and ATP
ATC is the network's promisable quantity for an item, derived - never raw on-hand:

```
ATC = supply - demand
supply = node on-hand (available status only)
       + inbound (open POs, in-transit ASNs, inter-node transfers) within the horizon
demand = existing reservations (soft + hard)
       + safety stock / protect quantity per node
       + any allocation holds
```

- **On-hand only counts available status.** Held, damaged, or QA stock at a node is on-hand but excluded, so
  ATC can be far below the raw quantity a node reports.
- **ATP** is the date-aware layer: it maps ATC plus scheduled future supply onto a **promise date**. A line
  with zero current ATC can still promise a future date if inbound supply lands inside the horizon (that is
  a backorder).
- **Eventually consistent.** Node on-hand and inbound feeds publish to the availability picture with a lag.
  Two commits inside that window can both pass and one oversells - re-read ATC at commit.
- **The supply feed is a committing surface.** ATC is only as good as the feeds behind it (node on-hand,
  inbound ASN / PO / transfer). Refreshing or correcting that supply picture re-promises every future order,
  so a wrong or mistimed feed oversells or under-promises the whole network - treat an availability / supply
  sync as a committing change to promising, not a read. The OMS consumes these feeds; it does not own node
  on-hand (that is the node's WMS, `manhattan-wms`).

## The DOM sourcing-rule engine
The distributed order management engine picks the node(s) per **line**. It weighs, per the customer's
configured rules:
- **Inventory** - only nodes with ATC for the line qualify.
- **Proximity** - closer node = lower cost + faster promise.
- **Cost** - shipping zone, node handling cost, markdown/clearance intent (clear aged stock first).
- **Split minimization** - prefer one node for the whole order over many partials; each split is another
  ship cost and another package for the customer.
- **Node capacity** - a node at its per-day limit is dropped from the candidate set.
- **Node priority / protect** - a rule can favor a flagship or protect a store's floor stock.

Output = an allocation (which node, soft or hard) + a promise (date). **Editing a live rule re-routes every
future order**, so a rule change is a committing, fleet-wide act, not a per-order setting. Test rule edits
in a non-live scope first.

## Reservation: soft vs hard
- **Soft reservation** - holds ATC against the order without binding a specific node. It protects
  availability but no node has committed the physical stock. Reading a soft reservation as fulfillable
  over-promises.
- **Hard allocation** - binds a specific node's on-hand to the line. This is what the OMS releases to the
  node's WMS / store app. Only a hard allocation is a real, node-level commitment.
- De-allocating a soft reservation is clean (frees ATC). De-allocating a **hard** allocation after the node
  started picking strands the picked stock physically at that node (see SKILL.md recovery patterns).

## Fulfillment types
| Type | What happens | The trap |
|---|---|---|
| **DC ship** | a distribution center picks/packs/ships via carrier | standard; the DC WMS executes |
| **Ship-from-store (SFS)** | a store picks and ships a web order | draws down store selling inventory; store safety stock protects the floor |
| **BOPIS** (buy online pickup in store) | reserved at the store, customer collects; no carrier | reservation holds until pickup or expiry, then must release back to ATC |
| **Curbside** | BOPIS variant; associate brings it out | same reservation/expiry mechanics as BOPIS |
| **Ship-to-store (STS)** | ship to a store, then customer pickup | two legs; not done at carrier delivery, only at pickup |
| **Dropship / vendor** | a third-party vendor ships direct | OMS loses pick/ship timing control; vendor ASN drives status; a cancel must beat the vendor's shipment |

## Backorder / pre-order promising
- A **backorder** promises a line with no current ATC against **future** supply (open PO, ASN, transfer) and
  a future promise date. If that supply slips, the promise breaks.
- The **payment authorization can expire** before a long backorder ships (a card auth commonly lapses in
  ~7 days, issuer-dependent - confirm per deployment), so a backorder that outruns the auth window must
  **re-authorize** before settlement or it ships
  unpaid / fails to settle.
- A **pre-order** is a backorder against not-yet-received supply for a launch date; same auth-expiry risk,
  amplified by the longer lead time.

## Node capacity and safety stock
- **Fulfillment capacity** - a per-day order or unit ceiling per node, protecting labor. A node at capacity
  is dropped by sourcing. Raising capacity to push more orders overloads the node and misses promises.
- **Safety stock / protect quantity** - the buffer a node withholds from ATC (store floor stock for
  walk-ins, a DC buffer for priority channels). Lowering it fills more orders now but risks in-store or
  channel oversell. Treat a live safety-stock change as committing, not a toggle.

## What each act publishes
- **Commit** publishes a reservation (decrements ATC) and requests a payment **authorization**.
- **Release** publishes the line to the node's WMS / store fulfillment app to pick.
- **Node ship confirm** publishes the physical shipment back, which drives **invoicing** and payment
  **settlement**, and the goods issue the ERP posts.
- **Re-source** publishes a de-allocation at the old node and a new allocation at the new node; if picking
  started, the physical put-back is manual.
