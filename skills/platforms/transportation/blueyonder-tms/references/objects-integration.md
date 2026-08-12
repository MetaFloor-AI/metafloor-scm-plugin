# Blue Yonder TMS - objects, modes, orgs, appointments, integration

The business-document model and the boundaries around it. Read when a task needs to reason about which object
it is acting on, which mode/org it is in, buy vs sell, or how the TMS connects to the host and the carrier.

## Contents
- The order / shipment / load model
- Business units / organizations (data scoping)
- Carriers, SCAC, modes
- Buy vs sell / the LSP scenario
- Dock appointments
- Integration (host + carrier)

## The order / shipment / load model
- **Order / Shipment** - the transportation demand from the host. A *request to move* goods; not a commitment.
  Order-level and line-level movement are not the same object. It carries a planning state (unplanned ->
  planned -> tendered -> in transit).
- **Load** - the consolidated movement built from one or more orders/shipments; the **rateable, tenderable,
  bookable, payable** unit, keyed by a **load ID**. Its state: Planned -> Available/Ready -> Tendered ->
  Accepted -> Dispatched -> In Transit -> Delivered -> Settled/Closed. Reason about the transition, not the noun.
- **Stop / leg** - a load has stops (pickups/deliveries) and, for multi-modal, legs. Carrier, rate, and tender
  can be **per leg** - "the carrier" on a multi-leg move is per leg, not per load.
- Act on the right object: rating or tendering the order when you meant the load (or vice versa) commits or
  costs the wrong thing.

## Business units / organizations (data scoping)
- Blue Yonder partitions data by **business unit / organization** (multi-tenant / multi-BU). Orders, loads,
  rates, routing guides, and carriers live within an org.
- An object in the **wrong org is invisible or wrong**. Acting in the wrong org reads stale/absent data or
  writes to the wrong business unit. Confirm the org context on every read and write.

## Carriers, SCAC, modes
- A carrier is identified by its **SCAC** (Standard Carrier Alpha Code). A carrier can be inactive,
  capacity-capped, or off-contract/blocked on a lane at the SCAC level - tendering to an ineligible carrier
  fails or commits off-contract spend.
- **Mode** drives the whole flow: **TL** (full truckload), **LTL** (class + CWT rating), **parcel** (zone/
  weight, its own manifest/label flow), **ocean/rail/intermodal** (booking against a sailing/voyage). Tender,
  booking, rating, and manifesting differ per mode - "tender the load" is not one flow.

## Buy vs sell / the LSP scenario
- The core Blue Yonder TMS use is **shipper buy-side**: you pay the carrier (the tender/booking/settlement is
  cost, money out). Gate and cost-check the **buy** side.
- Configured as an **LSP / broker**, there is also a **sell/customer-billing side** (revenue - what you bill
  your customer). Buy and sell are different sides; acting on the wrong side pays or bills the wrong party.
- If the deployment is shipper-only, treat everything as buy-side and do not assume a sell side exists.

## Dock appointments
- A **dock appointment** reserves a slot and a resource at an origin/destination facility (Blue Yonder yard/
  appointment scheduling, or an integrated WMS).
- Reversible in itself, but a **Live vs Drop** activity mistake mis-plans the yard and can cause detention on
  arrival. A missed/late appointment can also **fail routing-guide compliance** for that carrier.
- The appointment is a plan-side reservation, distinct from the tender - scheduling one commits no carrier.

## Integration (host + carrier)
- **Host side** - orders/shipments come from the OMS/ERP; the approved payable posts to AP/ERP. The
  transportation requirement is not standalone - changing the source order upstream can re-issue the demand
  and re-plan or orphan existing loads.
- **Carrier side** - the messages that cross the boundary, by direction: **EDI 204** (tender, **outbound**
  you -> carrier), **990** (carrier accept/decline, **inbound**), **214** (status/tracking, **inbound** from
  the carrier), **210** (freight invoice, **inbound**). The 204 is the only one you send; a tender is
  externally visible the moment it sends, and a carrier acceptance (990) commits the load without a human on
  your side.
- **WMS / warehouse** - loading, HUs, and pick/pack are warehouse execution -> `blueyonder-wms` or
  the connected WMS, not this skill. Blue Yonder TMS plans and commits the transport; the WMS executes the dock.

Gating note (aligned to the SKILL.md matrix): display/list any object, preview a mode/org, check appointment
availability = **Read**. Create/edit an order before planning, schedule/change an appointment = **Write
(reversible)**. The committing/destructive lines live in `consolidation-tendering.md` (tender/book) and
`rating-settlement.md` (settle/pay).
