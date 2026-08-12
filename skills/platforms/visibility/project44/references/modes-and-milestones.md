# project44 modes, data sources, and milestones

Load when working a specific mode. Each mode has its own data sources, milestone set, identifiers, and update
cadence, and that difference decides how fresh and how trustworthy a status or ETA is. The rule under all of it:
a milestone is a claim from its source, freshness is set by the source, and every mode reports differently - so
read the source and the cadence before you rely on the event.

## Contents
- Data sources by mode
- Truckload (FTL) and LTL
- Ocean: milestones, LFD, demurrage and detention, discharge vs available
- Air
- Parcel
- Rail / intermodal and multi-leg
- EDI 214 status codes (selected)
- Freshness by mode

## Data sources by mode
| Mode | Primary source(s) | Cadence | What can go wrong |
|---|---|---|---|
| Truckload (FTL) | ELD / telematics, mobile driver app, carrier API | high (minutes) | app closed / device off -> ping gap; consent scope on driver GPS |
| LTL | carrier API / EDI 214 | low (milestone-driven) | self-reported status; batch-sent, back-dated timestamps |
| Ocean | AIS vessel position + carrier / terminal milestones | low (hours / per-event) | milestone lag; transshipment handoff; LFD changes |
| Air | airline / forwarder feed, IATA cargo status | per-event | flight change; house vs master AWB confusion |
| Parcel | parcel-carrier scan events | per-scan | scan gaps; last-mile handoff |
| Rail / intermodal | railroad milestones, drayage leg | low (per-event) | leg handoff between rail and truck / ocean |

A carrier must be **connected / onboarded** for any of these to flow. An unconnected carrier's shipment is
invisible, not on-time; "no exceptions" on it means "no data."

## Truckload (FTL) and LTL
- **Tracking method** decides everything downstream: ELD / telematics and the mobile app give frequent GPS
  pings and a live predicted ETA; carrier API / EDI 214 gives milestone events only, no continuous position.
- **Geofence-based events** - arrival and departure fire when the truck crosses a facility geofence. The
  **radius and placement** set when the event fires, and therefore when the **dwell** and **detention** clocks
  start. A too-large geofence fires arrival on a nearby road; a too-small one fires late.
- **Ping gaps are normal** - coverage, a closed app, or a powered-down ELD all drop pings. A gap is missing
  data, not a stopped truck. The last ping is last-known, not current.
- **Detention** starts when dwell passes the free time at a stop; the accuracy of the detention claim depends on
  the arrival event being correctly timed.

## Ocean: milestones, LFD, demurrage and detention, discharge vs available
Ocean is milestone-driven with AIS position between events. Identifiers: **booking number**, **bill of lading
(B/L)**, **container number**, vessel / voyage.
- **Milestone chain (typical):** gate-in at origin -> loaded on vessel -> vessel departed -> (transshipment:
  discharged / loaded at a hub) -> vessel arrived -> discharged at destination -> gate-out (picked up) ->
  empty return.
- **Discharged is not available.** A discharged container needs **customs release**, **line / freight release**
  (carrier lien released, freight paid), and **terminal availability** before it can be picked up. Planning
  drayage off the discharge event alone strands the box.
- **Last free day (LFD)** - the last day before **demurrage** starts. It is set by the carrier / terminal and
  **can change**; re-read it at decision time. Missing the LFD accrues demurrage per day.
- **Demurrage vs detention (ocean):** **demurrage** = the loaded / laden container sitting at the terminal past
  free time; **detention** = holding the carrier's equipment (container / chassis) outside the terminal past
  free time. Different clocks, different owners, different free-time windows.
- **Transshipment** - a container that changes vessels at a hub has a handoff where the milestone chain and the
  ETA to final destination depend on the connection. A single-leg read misses the transshipment risk.

## Air
- Identifiers: **master air waybill (MAWB)** and **house air waybill (HAWB)**; a consolidation has one master
  over many house bills - do not read a master-level status as every house shipment's status.
- **IATA cargo status** milestones (selected): **RCS** received from shipper, **DEP** departed (uplifted on a
  flight), **ARR** arrived, **RCF** received from flight at destination, **NFD** notified / available, **DLV**
  delivered. Each is per-flight-segment; a multi-segment journey has several.
- Flight changes (re-book to a later flight) move the ETA; read the current segment.

## Parcel
- Tracked by **carrier scan events**: manifest / label created, picked up, in-transit scans, out-for-delivery,
  delivered (with POD scan). A "label created" scan is not "picked up."
- Scan gaps and last-mile handoffs are common; a missing scan is not proof of non-movement.

## Rail / intermodal and multi-leg
- Rail milestones (release, placement, departure, interchange, arrival, notify) often sit **inside** a larger
  journey - an ocean container on rail drayage, or a truckload leg after a rail move.
- **Multi-leg / intermodal** - the ETA to final destination is the sum of legs plus the handoff risk at each
  interchange; reason on the leg that is the current constraint, not just the final planned date.

## EDI 214 status codes (selected)
EDI 214 is the Transportation Carrier Shipment Status Message - the carrier **self-reports** these. A code is a
claim, and its timestamp can be batch-sent or back-dated; a delivery code without a **POD** is weaker evidence.
| Code | Meaning |
|---|---|
| X3 | Arrived at pickup location |
| AF | Carrier departed pickup location |
| X6 | En route to delivery |
| AG | Estimated delivery |
| X1 | Arrived at delivery location |
| OA | Out for delivery |
| D1 | Completed unloading / delivered |
| AP | Delivered |
| SD | Shipment delayed / exception |
This is a selection, not the full set. Codes and their exact use vary by carrier: some carriers send
**proprietary** codes outside the standard set, and the **same code can carry different semantics at pickup vs
delivery** (an "arrived" is arrived-at-pickup or arrived-at-delivery depending on the stop). Do not treat the
table as exhaustive or universal - read the code, the stop it belongs to, and its source, not just the word.
For an **unrecognized code**, treat the status as unknown: do not infer it from the code word alone, re-read the
stop context and source, and if it is still ambiguous, escalate rather than guess.

## Freshness by mode
Raw cadence is in the **Data sources by mode** table above; what follows is what "stale" means per mode for a
decision. What is stale for one mode is normal for another: an ELD ping older than a few minutes is stale, but
hours between LTL / ocean milestones is expected, so a gap there is not an exception. Two ocean-specific traps:
AIS fills vessel position between milestones (position is fresher than the milestone chain), and LFD / terminal
status change **independently** of the vessel position, so re-read them on their own. Re-read at decision time;
do not act on a cached ETA or a stale ping as if it were live.
