# Oracle OTM - tendering, secure resources, continuous move

Tendering is the commit point of the whole system: it offers freight spend and reserves carrier capacity,
and several tender modes hand the *choice of carrier* to OTM itself. Read when a workflow plans, secures,
tenders, re-tenders, or cancels a shipment.

## Contents
- Secure Resources vs plain tender (the double action)
- Tender modes: sequential / broadcast / spot bid
- Tender lifecycle and statuses
- Timeout and auto-decline behavior
- Routing guide
- Continuous move tours
- The outbound messages (EDI 204 / 990)

## Secure Resources vs plain tender (the double action)
- **Approve for Execution** locks the shipment plan (itinerary + SP + cost) so it can be executed.
- **Tender Shipment** sends the offer to the SP and moves the status to SECURE RESOURCES_TENDERED.
- **Secure Resources** is a shortcut that runs *both* in one step: it approves for execution AND tenders.
  So "secure resources" is a commit, not a staging action - it puts an offer in front of a carrier.
- Un-approving for execution after the fact can drop the tender; re-securing sends a *new* offer.

## Tender modes: sequential / broadcast / spot bid
| Mode | How the carrier is chosen | The hazard |
|---|---|---|
| **Sequential** | offered down a ranked list (the routing guide), one SP at a time, each with a response window | a NO RESPONSE / timeout auto-declines and rolls to the next SP - an unattended tender walks the list and can commit a worse carrier |
| **Broadcast** | sent to many SPs at once; the **first to accept wins**, a withdrawal auto-fires to all others | used for "hot" loads; you do not choose the winner, so firing it on the wrong load commits to whoever answers first |
| **Spot bid** | an auction; bids are collected and at timer expiry the freight **auto-awards to the lowest adjusted cost** | the award fires on the clock, unattended; a forgotten or misconfigured spot bid awards freight on its own |

All three are committing: the moment a carrier accepts (or the timer awards), freight spend and capacity are bound.

## Tender lifecycle and statuses
Shipment status runs two type/value stacks:
- **SECURE RESOURCES** - NOT_STARTED (no tender) -> TENDERED (offer sent) -> ACCEPTED / DECLINED /
  PARTIALLY ACCEPTED / PICKUP NOTIFY. This is the commit stack.
- **ENROUTE** - NOT_STARTED (not picked up) -> ENROUTE (picked up) -> COMPLETED (delivered), with
  intermediate execution points (pickup-notify, arrived-at-stop) along the way. Whether an in-motion
  diversion or carrier swap is still possible depends on where in this stack the load is.
- Tender **acceptance status** on the offer: ACCEPTED (SP agrees), DECLINED (SP refuses), NO RESPONSE (none
  yet), PARTIALLY ACCEPTED (SP took only some transport handling units - the rest is still uncovered).

## Timeout and auto-decline behavior
- Each tender carries a response window, **configurable per carrier / lane / tender type**. Re-read the
  window value at execute; do not assume a default. On expiry OTM treats it as no response and, per config, auto-declines.
- Sequential: auto-decline rolls the offer to the next SP in the routing guide, with no human step.
- Broadcast/spot bid: the timer is the decision point (first-accept / lowest-bid award).
- Consequence: an agent or a long-running plan that tenders and walks away can commit a carrier purely on timers.

## Routing guide
- The ranked carrier/lane preference OTM tenders against (by cost, service, allocation, or business rules).
- Editing the routing guide re-routes *future* tenders - a sourcing change, not a display tweak.

## Continuous move tours
- A continuous move links two or more shipments of the same SP into one tour for a lower rate (empty-mile reduction).
- The legs are financially and operationally linked: un-tendering or canceling one leg can unravel the whole
  tour and forfeit the discount, and can strand the other legs. Treat a CM leg cancel as affecting the tour.

## The outbound messages (EDI 204 / 990)
- **204** - the load tender that leaves OTM for the carrier (price, stops, equipment, terms). Sending it is
  outbound and externally visible; it is the offer.
- **990** - the carrier's tender response (accept/decline) coming back.
- **214** - shipment status/tracking updates; **210** - the freight invoice inbound (see freight-settlement).
- GlogXML is the on-prem/integration equivalent envelope for these flows.

Gating note: every tender mode is committing; a re-tender or un-tender of an accepted shipment is destructive
(retracts a promise, forfeits capacity, risks charges); editing the routing guide is a committing sourcing change.
