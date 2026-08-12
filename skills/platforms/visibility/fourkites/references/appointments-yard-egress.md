# FourKites ETAs, exceptions, Appointment Manager, Dynamic Yard, and egress

Load when scheduling a dock slot, working the yard, handling exceptions, or deciding any outbound action. Two
themes run through it: (1) most of what you do here binds a physical resource or fires a signal others act on,
so know which writes commit; (2) every output is a potential egress, and the sensitivity is set by the data
class and the audience, not by whether the underlying read was "safe."

## Contents
- The three ETAs and predictive-ETA confidence
- Exception taxonomy and the dwell / detention clock
- Geofence mechanics
- Alerts, Notifications, Watchlist, and thresholds (config)
- Appointment Manager (dock scheduling)
- Dynamic Yard (yard moves and gate events)
- Data-sensitivity classes and party / tenant entitlement
- Tracey (the AI assistant) as an egress channel
- The egress decision (step by step)

## The three ETAs and predictive-ETA confidence
Three numbers live on one Load and routinely disagree - always know which you are quoting:
- **Planned / appointment ETA** - the commitment (the booked delivery window). The thing a customer promise or a
  detention claim is measured against.
- **Carrier-provided ETA** - what the carrier says (via EDI / API). Self-reported.
- **Predictive ETA** - FourKites's ML estimate from position, historical lane / facility performance, and
  network data. It **moves** as pings and events land; it is a snapshot, not a commitment.
Predictive-ETA confidence tracks the **Tracking Score** and the data: an ELD-tracked load with fresh pings has a
tighter, more trustworthy prediction; an EDI-only or stale load has a loose one. Quoting the predictive ETA as a
promise, or auto-booking a downstream appointment to it, turns a moving number into a broken commitment when it
slips. For any promise / dispute / re-plan, state which ETA and re-read it at decision time.

## Exception taxonomy and the dwell / detention clock
Exceptions are deviations flagged against the plan. Common families:
| Exception | Fires when | The trap |
|---|---|---|
| Late / behind schedule | predictive ETA past the appointment window | it is a prediction; it can recover |
| At-risk | predicted to miss, not yet late | probabilistic - do not treat as a certainty |
| Dwelling | at a stop past an expected dwell | depends on a correctly-timed arrival event |
| Detention risk | dwell approaching / past free time | the charge depends on the arrival geofence timing |
| Off-route / unexpected stop | position deviates from plan | can be a legitimate reroute or a fuel stop |
| Stopped | no movement for a threshold | a ping gap can look like a stop |
| Temperature excursion | reefer sensor outside band | one sensor's claim; corroborate duration + spec |

Exception lifecycle: **open -> acknowledged -> resolved / dismissed**. Adjudicating (resolve / false-positive)
is attributable and suppresses future signal on that pattern, so it is a committing write.

**Dwell vs detention clock:** dwell = time at a stop, measured from the arrival geofence event to the departure
event. Detention = dwell past the free time, which accrues a charge. Because both are anchored on the geofence
arrival event, a mis-placed or mis-sized geofence mis-starts the clock and makes any detention claim or dispute
built on it baseless. Normalize time zones before computing - a local-time milestone against a UTC plan
mis-reads dwell and on-time.

## Geofence mechanics
A geofence is a virtual boundary around a stop / facility; crossing it fires arrival and departure. Radius and
placement decide **when** the event fires and therefore when dwell / detention start. A too-large geofence fires
arrival on a nearby road (early); a too-small or mis-placed one fires late or not at all. A load just outside the
boundary has not "arrived." Changing a geofence definition is **account-wide config** - it changes arrival
timing for every load at that facility, not just your view. Treat borderline dwell / detention timing as
uncertain and do not build an irreversible dispute on a single geofence crossing.

## Alerts, Notifications, Watchlist, and thresholds (config)
- **Watchlist / filter / App Group (Board)** - personal scope: which loads you watch and how they are filtered.
  Adding / removing here is a reversible local write - but dropping a lane you rely on opens a blind spot.
- **Notification / alert subscription** - a rule that pushes an alert on a condition. Subscribing / unsubscribing
  is local and reversible; unsubscribing the **last remaining alert** on a load leaves it silent - functionally
  removing it from monitoring, so escalate to the destructive gate.
- **Alert thresholds and rules** (what counts as "at-risk," how long dwell before "dwelling," etc.) - these are
  **account-wide config**. Loosening a threshold silences signal for everyone on the account; tightening it
  floods the queue. Changing them is a committing config write, gated + human-approved, not a personal tweak.

## Appointment Manager (dock scheduling)
Appointment Manager schedules dock appointments at a facility. States: **requested -> confirmed -> arrived ->
completed**, or **rescheduled / cancelled**.
- Booking / confirming / moving / cancelling a slot **binds a physical dock resource**, notifies the facility and
  carrier, can **bump another appointment**, and can start or stop a detention / dwell clock. It is a committing
  write, not a calendar entry.
- Re-read slot availability at execute - availability drifts. A rescheduled slot is a **new commitment**, not an
  undo of the old one: the notified parties already acted and the bumped slot may be gone.
- A missed booked slot can itself trigger detention or a facility penalty, so do not book speculatively to a
  moving predictive ETA.

## Dynamic Yard (yard moves and gate events)
Dynamic Yard manages assets inside a facility yard: gate check-in / check-out, trailer / asset location, spotting
and moves.
- A **gate event** (check-in / check-out) and a **yard move / spot** bind or relocate a physical asset and can
  start or stop a yard dwell / detention clock. Committing writes.
- Yard state can disagree with the OTR Load state (a trailer checked in at the gate but the Load still shows
  "arriving") - the yard event is the on-site truth for the asset's position; reconcile, do not assume the Load
  milestone leads.
- Do not execute a yard move or gate event on a stale read; re-read the current yard state first.

## Data-sensitivity classes and party / tenant entitlement
Rank the payload before any output leaves your reasoning:
| Class | Examples | Default |
|---|---|---|
| Aggregate / de-identified, in-tenant | lane-level counts, facility dwell benchmark (no named loads) | lowest sensitivity; still in-tenant only |
| Named-load / named-order, in-tenant | a specific load's status, ETA, PO, stops | in-tenant, entitled audience only |
| Live driver / asset location | real-time GPS from ELD / telematics / Tracker | privacy + consent governed; tightest |
| Another party's data on a shared load | rate, other legs, contact, competing-shipper detail | not yours to forward; scope to your entitlement |
| Carrier performance / Tracking Score record | a carrier's on-time and score history | competitively sensitive |

**Party / tenant lines are trust boundaries.** A shipper sees its loads, a carrier its loads, a broker / LSP the
lanes it manages. A load you can see may carry another party's data; forwarding the whole record leaks what is
not yours. Driver / asset location comes through the carrier's consent - forwarding it beyond the authorized
scope is a privacy and consent breach. **Combining sources raises the class:** joining FourKites tracking with an
ERP PO, or one party's loads with another's, creates a new class whose sensitivity is the union of both.

## Tracey (the AI assistant) as an egress channel
FourKites ships **Tracey**, a conversational / agentic AI assistant that answers natural-language questions over
the tracking data. A natural-language answer is still a disclosure: it inherits the same entitlement,
party-scope, and audience rules as any export. Asking the assistant in-tenant is a read; its **answer rendered to
a user who lacks entitlement, or forwarded across a party line, is egress**. Prefer an aggregate or de-identified
answer over named-load / live-location detail, and confirm the audience's entitlement before surfacing named or
location detail through it.

## The egress decision (step by step)
Before any export, forward, share, tracking-link, push, or rendering of sensitive detail (including a Tracey
assistant reply):
1. **Classify the payload** - which class above (aggregate / named-load / live-location / another-party / carrier
   performance)? If it combines sources, take the union.
2. **Identify the audience and entitlement** - who receives it, and are they entitled to this party's data at
   this granularity? Your own reply counts as the audience.
3. **Check the destination** - is it approved (allowlist or the data owner)? If unknown, default to block.
4. **Prefer the least-sensitive form** - aggregate / de-identified / in-tenant over named-load / live-location.
5. **For a cross-system push** - gate against the *target system's* automation, not just FourKites's write class;
   if the target auto-acts (re-tender, AP charge, inventory release, customer notice), treat the push as
   destructive and apply the hard gate. If you cannot tell whether it auto-acts, assume it does.
6. **If no approved destination exists** - refuse and escalate to the data owner; do not proceed. Egress cannot
   be recalled once sent, so this is the irreversible action in the platform.
