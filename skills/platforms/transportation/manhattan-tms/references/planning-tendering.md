# Manhattan Active TM - planning, rating, and tendering

Tendering (and booking) is the commit point of the whole system: it offers freight spend and reserves
carrier capacity, and several tender modes hand the *choice of carrier* to the process itself. Read when a
workflow optimizes, rates, tenders, re-tenders, books, or cancels a load.

## Contents
- Load building and optimization (commits nothing)
- Rating and rate shopping
- The routing guide and waterfall tendering
- Spot bid / spot tender / RFP
- Tender lifecycle and statuses
- Timeout and auto-roll behavior
- Booking (capacity commitment)
- Continuous move / multi-stop / pool tours
- The outbound messages (EDI 204 / 990)

## Load building and optimization (commits nothing)
- **Load optimization** consolidates order lines / shipments into least-cost loads: it picks mode, carrier
  candidate, equipment, sequences stops, respects capacity/time windows/incompatibilities, and computes cost.
- It is planning. Building or re-optimizing a load assigns a carrier candidate and a cost but **commits
  nothing** - no capacity is reserved and no money is bound until the tender or booking.
- A re-optimize can rebuild/unbuild loads that are not yet tendered; a tendered load should be excluded from
  re-optimization or it can be pulled out from under a live offer. Re-plan of a tendered load can double-tender.

## Rating and rate shopping
- **Rating** computes a load's cost from a rate record/structure under a carrier agreement, plus accessorials
  (fuel surcharge, detention, liftgate) and discounts. It **reads** rates; it commits nothing.
- **Rate shopping** compares eligible carriers/services and returns the least-cost option for a load or parcel.
  The choice binds only when you tender / book / manifest.
- A rate is only valid for its **lane + carrier + mode + effective-date window + weight/volume basis**. A
  re-weigh or re-measure can jump the freight into a different rate tier (a weight/CWT break, or a parcel
  dim-weight bracket), changing the *base* cost - not an accessorial, and not caught by an invoice-tolerance
  check. Re-rate at execute if the plan is old or the cargo changed.

## The routing guide and waterfall tendering
- The **routing guide** is the ranked carrier/lane preference (by cost, service, allocation, business rules).
- **Waterfall (sequential) tendering** offers the load down the guide one carrier at a time, each with a
  response window. A decline or a **no-response timeout auto-rolls to the next carrier** with no human step.
- Consequence: an unattended tender can march down the list and commit a worse or wrong carrier. An agent or
  a long-running plan that tenders and walks away can commit purely on timers.
- **Editing the routing guide re-routes future tenders** - a sourcing change, not a display tweak. Gaming a
  rank or a rate to drop a load under an approval threshold is an audit violation.

## Spot bid / spot tender / RFP
- A **spot bid / spot tender** is an auction to a set of carriers for a load (typically when the routing guide
  is exhausted or for irregular freight). Bids are collected and the load is **awarded on a timer or by pick**.
- Firing a spot bid delegates the choice to the process; a forgotten or misconfigured spot tender awards
  freight on its own when the clock runs out. The award is committing the moment it lands.

## Tender lifecycle and statuses
- Tender status runs: **not tendered -> tendered (204 sent) -> accepted / declined / no-response (expired) /
  spot-awarded**. Accepted (or spot-awarded) = capacity + cost committed.
- **Partial acceptance** - a carrier can accept only part of a load (some stops/handling units); the accepted
  portion stays with that carrier and the rest is still uncovered. Do not treat a partial as fully covered.
- An **inbound carrier acceptance (EDI 990) flips the load to accepted on its own** - the freight is committed
  with no human pressing confirm on your side. Re-read status and treat an accepted load as a live commitment.

## Timeout and auto-roll behavior
- Each tender carries a response window, **configurable per carrier / lane / tender type**. Re-read the window
  at execute; do not assume a default. On expiry the tender is treated as no-response.
- Waterfall: expiry rolls the offer to the next carrier in the guide, unattended.
- Spot: the timer is the decision point (award to the best bid at expiry).

## Booking (capacity commitment)
- A **booking** reserves a hard capacity slot with a carrier - an ocean sailing, an intermodal ramp, a
  drayage move, sometimes parcel - usually ahead of the cargo. Confirming a booking commits the allocation.
- Cancelling a booking gives the space back and it **may not be re-securable** at the same rate or at all -
  higher stakes than un-tendering a road load. Treat a booking cancel as destructive.

## Continuous move / multi-stop / pool tours
- A **continuous move** links two or more loads/movements of the same carrier into one tour for a lower rate
  (empty-mile reduction); a **pool point** consolidates freight through an intermediate node.
- The legs are financially and operationally linked: un-tendering or cancelling one leg can unravel the whole
  tour and forfeit the discount, and can strand the other legs. Treat a CM/pool leg cancel as affecting the tour.
- On a **multi-stop or multi-leg** load, carrier, mode, tender, and cost can be **per leg** - "the carrier" is
  per leg, not per load.

## The outbound messages (EDI 204 / 990)
- **204** - the load tender that leaves TM for the carrier (price, stops, equipment, terms). Sending it is
  outbound and externally visible; it is the offer.
- **990** - the carrier's tender response (accept/decline) coming back.
- **214** - shipment status/tracking updates; **210** - the freight invoice inbound (see freight-audit-payment);
  **997** - the functional acknowledgement.

Gating note: every tender mode and every booking is committing; a re-tender or cancel of an accepted load or
booking is destructive (retracts a promise, forfeits capacity, risks TONU/detention/demurrage); editing the
routing guide or a rate is a committing sourcing change.
