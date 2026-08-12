# project44 ETAs, exceptions, appointments, and the egress decision

Load when reading ETAs, handling exceptions, scheduling appointments, or deciding an outbound action. The rule
under all of it: the ETA is a moving estimate, the exception is a signal not a verdict, the appointment is a
physical commitment, and the reply / export is an egress channel - so read confidence and scope before you act
or send.

## Contents
- The three ETAs and predicted-ETA confidence
- Exception taxonomy
- Dwell and detention clock
- Geofence mechanics
- Alert / notification config
- Appointment scheduling
- Data-sensitivity classes
- Party / tenant entitlement
- The egress decision

## The three ETAs and predicted-ETA confidence
Every shipment can show three different arrival numbers:
- **Planned / appointment ETA** - the committed date / time (the appointment or the plan). This is the promise.
- **Carrier-provided ETA** - what the carrier reports. A claim from the carrier.
- **Predicted / dynamic ETA** - project44's ML estimate from position, historical lane performance, dwell, and
  conditions. It **updates continuously** as pings and events land.
Using the wrong one mis-sets a decision: quote the **planned** ETA as the commitment, use the **predicted** ETA
to see risk against that commitment, and treat the **carrier** ETA as one input. The predicted ETA carries a
confidence that inherits the **tracking method** and **data quality**: an ELD-tracked truckload prediction is
tighter than an EDI-only LTL or a milestone-driven ocean prediction. Never promise a customer the raw predicted
ETA; it is a moving snapshot, not a commitment.

## Exception taxonomy
An exception is a deviation flagged against the plan. Common types:
- **Late / at-risk** - predicted to miss (or missing) the planned ETA. "At-risk" is a prediction, not a fact yet.
- **Dwelling** - sitting at a stop longer than expected.
- **Detention risk** - dwell approaching / past free time (a charge accrues).
- **Off-route / unexpected stop** - deviation from the expected path.
- **Stopped / no movement** - no progress; may be a real stop or a **ping gap** (missing data, not a stopped truck).
- **Temperature excursion (reefer)** - a sensor read outside the product's range. One sensor's claim; corroborate
  duration and product spec before an irreversible reject.
States: **open -> acknowledged -> resolved / dismissed**. Adjudicating an exception (resolved / false-positive)
is **attributable and logged**: a false-positive mark on a real exception leaves a record you saw it and
dismissed it. Adjudicate with evidence, not to clear the queue. Muting / snoozing suppresses the signal, not the
event - a real one missed during the mute is lost lead time.

## Dwell and detention clock
- **Dwell** = time at a stop, measured from the **arrival** event to the **departure** event.
- **Detention** = dwell past the **free time** allowed at that stop; it accrues a charge per unit time.
- The clock's accuracy depends entirely on the arrival / departure events being correctly timed - which depends
  on the **geofence** (below). A mis-fired arrival mis-computes both dwell and detention, and a detention dispute
  built on a mis-timed event is baseless.
- **Time base:** milestone timestamps may be local or UTC; normalize before computing dwell / on-time, or the
  numbers are wrong.

## Geofence mechanics
A geofence is a virtual boundary around a stop / facility. Arrival fires on entry, departure on exit.
- **Radius / placement** set when the events fire. Too large: arrival fires on a nearby road, over-stating dwell.
  Too small or mis-placed: arrival fires late, under-stating it.
- Changing a geofence definition is **account-wide config** - it changes event timing for every shipment to that
  facility, not just your view. Treat it as a committing config change.

## Alert / notification config
- **Subscribing / unsubscribing** an alert or notification, and **snoozing / muting** an exception, are local,
  reversible writes - gate one at a time, capture the reason, log it.
- **Changing an alert threshold** (what counts as "at-risk," how long before "dwelling" fires) is **account-wide**
  and changes what fires for everyone. It is committing, not a personal setting.
- Sending a **customer / party notification or tracking link** is both an external commitment and **egress**
  (below).

## Appointment scheduling
Booking / confirming / rescheduling / cancelling a dock or yard appointment is a **committing write**:
- It **binds a physical slot** at a facility and **notifies** the facility and the carrier.
- It can **bump another appointment**, and a **reschedule** may lose the original slot.
- A booked slot can **start or stop a detention clock**; a missed booked slot can itself trigger detention.
- Re-read availability at execute (slots drift), gate it, and confirm the notified parties. A reschedule is a new
  commitment, not an undo.

## Data-sensitivity classes
From lower to higher sensitivity:
1. **Aggregate / de-identified, in-tenant** - counts, on-time rates, lane-level rollups without named shipments.
   Lower sensitivity, still in-tenant only.
2. **Named-shipment status / ETA** - a specific shipment, order, or container and its status. Sensitive; who
   ships what.
3. **Lane / network composition** - all shipments on a lane, volumes, origins / destinations. Competitively
   sensitive; exposes a customer's sourcing.
4. **Live driver / asset location** - real-time GPS. Privacy- and consent-governed (carrier ELD / telematics
   consent).
5. **Another party's data on a shared shipment** - rates, other legs, contacts, competing-shipper detail. Not
   yours to forward.
6. **Customer PO / order detail joined to tracking** - union of ERP order data and location; the combined class
   is the higher of the two.
**Combining sources raises the class** - joining project44 tracking with a PO from the ERP, or one party's data
with another's, creates a new class whose sensitivity is the union.

## Party / tenant entitlement
project44 is multi-party: a **shipper** sees its shipments, a **carrier** its loads, a **broker / LSP** the
lanes it manages. A shipment visible to you can carry another party's data you may not see the rate on or
forward. Moving data across a **party or tenant line** is egress, not an internal move. Driver location flows
through the carrier's consent; the shipper's entitlement to see it does not extend to forwarding it onward.

## The egress decision
Before any export, forward, share, tracking-link, push, or rendering of sensitive detail **in your own reply**:
1. **Classify the payload** - which sensitivity class above (named shipment / lane / live location / other
   party's data / PO join)?
2. **Identify the audience and entitlement** - do they have the right to this party's / tenant's data? Your own
   reply to an unentitled user is egress.
3. **Check the destination** - is it on the approved allowlist, or confirmed by the data owner? If unknown,
   **default to block** and escalate.
4. **Prefer the lower class** - render an aggregate / de-identified summary over named-shipment or live-location
   detail whenever it answers the question.
5. **Cross-system push** - if the destination system auto-acts on the payload (auto re-tender, customer
   delivery-failure notice, detention charge to AP, inventory release), gate the push against the **target
   system's** automation and treat it as destructive.
Egress cannot be undone: data that crossed the boundary or a party line cannot be recalled. If it happens in
error, notify the data owner and the affected party, document what went where, and do not try to "fix" it with
another write in the target system.

**Worked example.** A user asks: "What is the ETA for Acme's Shanghai -> Long Beach containers this week?"
1. **Classify** - "all of Acme's containers on a lane, this week" is a **lane / network-composition** query
   (class 3), not one named shipment; it exposes Acme's volume and sourcing on that lane.
2. **Audience / entitlement** - is the asker on Acme's tenant and entitled to that lane, or a different party?
   If they are not Acme (or an entitled LSP for Acme), the network composition is not theirs to receive.
3. **Destination** - a reply in-session to an entitled Acme planner is in-boundary; an export to an external
   tool, or a forward to a carrier or a second shipper, is egress - check the allowlist / data owner, and if
   unknown, block.
4. **Prefer the lower class** - if the planner only needs to know whether the lane is on track, answer with an
   **aggregate** ("N of M containers at-risk, worst-case ETA slip X days") rather than every named container's
   position, which drops the class from 3 to an aggregate.
5. **Target automation** - if the answer is being pushed into a downstream plan that auto-re-books or notifies
   customers, gate against that system's automation as well.
