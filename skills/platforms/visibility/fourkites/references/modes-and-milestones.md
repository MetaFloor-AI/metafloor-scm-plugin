# FourKites modes, data sources, milestones, and Tracking Score

Load when working a specific mode. Each mode has its own data sources, milestone set, identifiers, and update
cadence, and that difference decides how fresh and how trustworthy a status or ETA is - and it drives the
**Tracking Score**. The rule under all of it: a milestone is a claim from its source, freshness is set by the
source, the Tracking Score tells you how thin the data is, and every mode reports differently - so read the
source, the cadence, and the score before you rely on the event.

## Contents
- Data sources by mode
- Tracking Score (what it measures, how to use it)
- Over-the-road (OTR) truckload and LTL
- Dynamic Ocean: milestones, LFD, demurrage and detention, discharge vs available
- Air
- Parcel
- Rail / intermodal and multi-leg
- EDI 214 status codes (selected)
- Freshness by mode

## Data sources by mode
| Mode | Primary source(s) | Cadence | What can go wrong |
|---|---|---|---|
| OTR truckload | ELD / telematics, Tracker mobile driver app, carrier API | high (minutes) | app closed / device off -> ping gap; consent scope on driver GPS |
| LTL | carrier API / EDI 214 | low (milestone-driven) | self-reported status; batch-sent, back-dated timestamps |
| Ocean (Dynamic Ocean) | AIS vessel position + carrier / terminal milestones | low (hours / per-event) | milestone lag; transshipment handoff; LFD changes; rollover |
| Air | airline / forwarder feed, IATA cargo status | per-event | flight change; house vs master AWB confusion |
| Parcel | parcel-carrier scan events | per-scan | scan gaps; last-mile handoff |
| Rail / intermodal | railroad milestones, drayage leg | low (per-event) | leg handoff between rail and truck / ocean |

A carrier must be **connected / onboarded** for any of these to flow (FourKites tracks through its carrier
network, direct ELD / telematics integrations, and the Tracker app). An unconnected carrier's load is invisible,
not on-time; "no exceptions" on it means "no data."

## Tracking Score (what it measures, how to use it)
FourKites computes a per-load **Tracking Score** - roughly a 0-100% measure of how completely and freshly the
load is being tracked (is the carrier connected, is the ELD / app reporting, are pings recent, are milestones
landing). It is the confidence signal, not a status.
- **A green status with a low score is thin data.** A load can read "in-transit, on-time" while the score is low
  because it is EDI-only with stale pings; the ETA and status are then low-confidence. Read the score before you
  rely on the status.
- **The score varies by mode and method.** An ELD-tracked OTR load scores high when reporting; an EDI-only LTL
  or a milestone-driven ocean container is structurally lower-cadence, so a single confidence rule across modes
  misreads the low-score ones.
- **Use it to prioritise, not to act.** A low score means corroborate before an irreversible move (promise,
  reject, dispute, penalty); it does not by itself mean the load is late.
- **A dropping score is an early warning** that tracking is degrading (app closed, device offline, carrier feed
  stalled) before the ETA visibly moves - worth a nudge to re-establish tracking, not an exception to act on.

## Over-the-road (OTR) truckload and LTL
- **Tracking method** decides everything downstream: ELD / telematics and the Tracker app give frequent GPS
  pings and a live predictive ETA; carrier API / EDI 214 gives milestone events only, no continuous position.
- **Geofence-based events** - arrival and departure fire when the truck crosses a facility geofence. The
  **radius and placement** set when the event fires, and therefore when the **dwell** and **detention** clocks
  start. A too-large geofence fires arrival on a nearby road; a too-small one fires late.
- **Ping gaps are normal** - coverage, a closed app, or a powered-down ELD all drop pings. A gap is missing
  data, not a stopped truck. The last ping is last-known, not current.
- **Detention** starts when dwell passes the free time at a stop; the accuracy of the detention claim depends on
  the arrival event being correctly timed by the geofence.

## Dynamic Ocean: milestones, LFD, demurrage and detention, discharge vs available
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
- **Rollover** - a booked container bumped to a later vessel / voyage; the ETA and the whole milestone chain
  shift, and a plan built on the original sailing is stale. Read the current vessel / voyage, not the booked one.
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
EDI 214 is the ANSI X12 Transportation Carrier Shipment Status Message; most of the codes below are ANSI X12 214
shipment-status codes as surfaced in FourKites, but exact codes and their meaning vary by carrier and
integration, and some carriers send proprietary ones - so treat this as a common-case guide, not an
authoritative X12 dictionary. The carrier **self-reports** these. A code is a claim, and its timestamp can be
batch-sent or back-dated; a delivery code without a **POD** is weaker evidence.
| Code | Meaning |
|---|---|
| X3 | Arrived at pickup location |
| AF | Carrier departed pickup location |
| X6 | En route to delivery |
| AG | Estimated delivery |
| X1 | Arrived at delivery location |
| OA | Out for delivery |
| D1 | Completed unloading / delivered |
| AP* | Delivered (context-dependent - some carriers use AP differently; read the stop, not the word) |
| SD | Shipment delayed / exception |
This is a selection, not the full set. Codes and their exact use vary by carrier: some carriers send
**proprietary** codes outside the standard set, and the **same code can carry different semantics at pickup vs
delivery** (an "arrived" is arrived-at-pickup or arrived-at-delivery depending on the stop). Do not treat the
table as exhaustive or universal - read the code, the stop it belongs to, and its source, not just the word. For
an **unrecognized code**, treat the status as unknown: do not infer it from the code word alone, re-read the
stop context and source, and if it is still ambiguous, escalate rather than guess.

## Freshness by mode
Raw cadence is in the **Data sources by mode** table above; what follows is what "stale" means per mode for a
decision. What is stale for one mode is normal for another: an ELD ping older than a few minutes is stale, but
hours between LTL / ocean milestones is expected, so a gap there is not an exception. The Tracking Score already
folds freshness in - a load whose pings have gone stale drops in score. Two ocean-specific traps: AIS fills
vessel position between milestones (position is fresher than the milestone chain), and LFD / terminal status
change **independently** of the vessel position, so re-read them on their own. Re-read at decision time; do not
act on a cached ETA or a stale ping as if it were live.
