# SAP TM - objects, document flow, and ERP integration

The business-document model and how SAP TM connects to ERP. Read when a task needs to know which object is a
demand vs a commitment, which is buy vs sell, or how a requirement got into TM and how cost leaves it. The
document flow is where "one order, one carrier, one cost" stops being true.

## Contents
- The document flow (demand -> plan -> commit -> settle)
- Requirements: OTR vs DTR
- Forwarding orders (the LSP/sell side)
- The TOR framework: FO, FB, consignment order, TU, stages
- Buy vs sell
- Embedded vs standalone TM and the integration path

## The document flow (demand -> plan -> commit -> settle)
```
Requirement (OTR/DTR)  or  Forwarding Order (FWO)      <- demand, from ERP or the customer
        |  Freight Unit Building (FUBR)
        v
Freight Unit (FU)                                       <- planning unit, no commit
        |  VSR optimizer / Transportation Cockpit
        v
Freight Order (FO) / Freight Booking (FB)               <- plan + proposed carrier, no commit
        |  carrier selection -> tendering -> subcontract/confirm
        v
Confirmed FO/FB                                         <- COMMIT: capacity + cost
        |  execution
        v
Freight Settlement Document (FSD)                        <- COMMIT: money out, cost to ERP/FI
```
The revenue side branches from the FWO to a **Forwarding Settlement Document (FWSD)** that bills the customer.
A change upstream in the flow can re-issue downstream documents - the demand is not standalone.

## Requirements: OTR vs DTR
- **OTR (Order-based Transportation Requirement)** - created from a sales order or purchase order via the ERP
  integration. The demand exists as soon as the order does.
- **DTR (Delivery-based Transportation Requirement)** - created from a delivery (later in the ERP process,
  closer to the physical move).
- Both are **requests to move**, not commitments. Because they are tied to the source order/delivery,
  **changing the source upstream can re-issue the requirement** and re-plan or orphan freight already built
  from it.

## Forwarding orders (the LSP/sell side)
- A **Forwarding Order (FWO)** is the freight-forwarder/LSP scenario: the **customer's** order to move goods,
  the **sell side** (revenue). It is paired with a **Forwarding Quotation** and settled via the **FWSD**.
- It is distinct from the freight order you **buy** from a carrier. In a 3PL/4PL flow both exist for the same
  cargo - the FWO is what you bill the customer, the FO is what you pay the carrier.

## The TOR framework: FO, FB, consignment order, TU, stages
- **Freight Order (FO)** - executable land/road transport document; where a carrier is subcontracted.
- **Freight Booking (FB)** - ocean/air capacity booked with a carrier/co-loader against a sailing/flight,
  usually ahead of the cargo. Cancelling forfeits the allocation.
- **Consignment order** - consolidates freight (LCL / co-load) into one carrier movement; unravelling one
  order can break the consolidation and its rate.
- **Transportation Unit (TU)** - the physical load/container/trailer that moves and carries loading/unloading
  events. Distinct from the order that governs it.
- **Stage** - a leg of the route (source -> destination + means of transport). **Carrier, charges, and
  tendering run per stage.** On a multi-modal move "the carrier" is per leg, not per document.
- FO / FB / consignment / TU are all managed under the **TOR** (Transportation Order) business-object
  framework - the shared model behind the transport documents.

## Buy vs sell
- **Buy side**: Freight Order (FO) -> Freight Settlement Document (FSD) -> pay the carrier. Gate and
  cost-check this side.
- **Sell side**: Forwarding Order (FWO) -> Forwarding Settlement Document (FWSD) -> bill the customer.
- They are separate documents. Acting on the sell side as if it were the buy side (or vice versa) pays or
  bills the wrong party.

## Embedded vs standalone TM and the integration path
- **Embedded S/4HANA TM** - TM runs inside the S/4HANA system; requirements come from the same box, and
  settlement posts to the same MM/FI. The common current deployment.
- **Standalone SAP TM (on SCM)** - TM is a separate system integrated to one or more ERPs; requirements and
  settlements cross a system boundary.
- Effect on the books is the same - a confirmed FO commits, an FSD transfers cost - but the integration path
  and the object IDs differ. The ERP-side detail (PO / service entry sheet / invoice verification) is
  `sap-mm`; the GL / period close is `sap-fi`.

Gating note (aligned to the SKILL.md matrix): OTR/DTR/FWO/FU are demand and **Write (reversible)** planning;
FO/FB become **Write (committing)** at subcontract/confirm; FSD/FWSD are the **Destructive**-class ledger
events. Always confirm buy-vs-sell and the stage before acting.
