---
name: project44
description: "project44 (the Movement platform) - safe operation of real-time multimodal transportation visibility across ocean / air / parcel / LTL / truckload / rail: shipment and order tracking, predictive / dynamic ETAs, carrier and telematics / ELD connections, milestone and status events, exception detection, and inventory-in-transit. Use when the connected visibility system is project44 or Movement and the work touches a predicted or dynamic ETA, a carrier connection or tracking method (ELD, telematics, mobile driver app, API, EDI 214), a shipment / load / order status, a milestone or geofence arrival / departure event, a tracking gap or stale ping, an exception (late, at-risk, dwelling, detention, off-route, temperature excursion), an ocean container / booking / bill of lading / last free day / demurrage, an air waybill / flight status, a parcel scan, a dock or yard appointment, or sharing / exporting shipment, customer, or location data to another party."
---

# project44 (Movement) - operating it safely

project44's Movement platform (**Movement is the platform product; project44 is the company that builds it - a
user query may use either name to mean the platform**) is a real-time transportation visibility layer, not a
system of record. It connects to carriers,
telematics / ELD devices, mobile driver apps, ocean and air feeds, and terminals to track shipments across every
mode, and it computes a predictive ETA and detects exceptions against the plan. Almost
every operation is a read - and that is exactly what makes it different from the ERP / TMS / WMS systems in this
plugin. **Here the danger is not posting money or stock; it is what the telemetry is and where it goes.** The
reads are safe. The hazards are four: (1) sensitive shipment, customer, and location data leaving the trust
boundary or crossing a party / tenant line (egress), (2) treating a predicted ETA, a self-reported carrier
milestone, or a single sensor read as confirmed fact and committing an irreversible action on it - usually in
another system, (3) the genuinely committing writes the platform does have (booking or moving a dock / yard
appointment, pushing status back into a TMS / OMS, notifying a customer), and (4) config that silently changes
what is tracked or what fires an alert. Classify by **data sensitivity and egress**, not by stock or dollars.

## Contents
- Read this first
- When this applies
- The surfaces
- Object & state model
- Vocabulary that bites
- Operations: read / write / by data sensitivity and egress
- Gotchas that bite
- Edge states & special cases
- Reconciliation / freshness
- Recovery patterns
- Guardrails
- References

## Read this first (constraints for any egress or commit)
- **Egress is the high-risk act here.** Who ships what to whom, on which lane, at what volume; a facility's
  location and throughput; a driver's / asset's real-time GPS position; a customer's PO and order detail; a
  carrier's performance and on-time record - these are the platform's most sensitive assets. Sending any of it
  to an external tool, an unapproved endpoint, another party, or a broad audience is a controlled disclosure,
  not a data pass-through. Once it leaves you cannot recall it. Keep telemetry inside the approved tenant,
  party scope, and audience.
- **Your own reply is an egress channel.** Summarizing, quoting, or paraphrasing a customer's shipment
  locations, a driver's live position, a carrier's performance, or PO detail back to a user who lacks
  entitlement is egress even though the read itself was "always pass." Before rendering named-shipment,
  location, or party detail in a response, confirm the audience and their entitlement, and prefer an aggregate
  or de-identified summary over named-shipment / live-location detail.
- **Party and tenant lines are trust boundaries.** A shipper sees its shipments, a carrier its loads, a
  broker / LSP the lanes it manages - a shipment visible to you can carry another party's data (rate, other
  legs, contact, competing-shipper detail) that is not yours to forward. Moving data across a party or tenant
  line is egress, not an internal move. Driver / asset location comes through the carrier's ELD / telematics
  under the carrier's consent; forwarding it beyond the authorized scope is a privacy and consent breach.
- **A predicted ETA / milestone / sensor read is a signal, not a verdict.** A predicted (dynamic) ETA is an ML
  estimate that updates continuously; a carrier EDI milestone is self-reported; a temperature or geofence event
  is one sensor's claim. None is confirmed truth. Do not promise a customer delivery, reject a load, dispute or
  waive a detention charge, invoke a penalty, or re-route on a single unconfirmed read. Corroborate and re-read
  first. **What "corroborate" means here (the standard):** the read is corroborated when a second *independent*
  source agrees (a carrier milestone plus a fresh GPS ping / geofence event; a predicted ETA plus the current
  position; a sensor excursion plus its duration and the product spec), OR a re-read after the next refresh cycle
  returns the same state **only if new data (a fresh ping or event) actually landed** - a predicted ETA that is
  unchanged because no new position arrived is the model restating itself, not corroboration. One source
  restating itself is not corroboration. **When corroboration is
  structurally impossible** (a single-source ocean milestone with no AIS, an unconnected carrier with no second
  source and no refresh that will change it), hold the irreversible action and escalate to a human; do not treat
  the lone source as corroborated by default.
- **The irreversible action usually lives in the other system.** project44 informs; the TMS, OMS, ERP, WMS, or
  yard system acts. When telemetry here would drive a committing write there (re-tender, cancel, expedite,
  notify the customer, post a detention charge, release inventory), gate that write in the target system under
  its own rules - and base it on corroborated status, not a raw ETA.
- **Do not silence the signal to quiet the queue.** Removing a shipment or lane from tracking, muting an
  exception, or unsubscribing an alert creates a blind spot; a real disruption that unfolds during the gap is a
  missed disruption with lead time already lost.
- **An appointment is a physical commitment, not a calendar note.** Booking or moving a dock / yard slot binds a
  real resource, notifies the facility and carrier, can bump another appointment, and can start or stop a
  detention clock. Treat it as a committing write.

## When this applies
Connector is project44 / Movement and the work is shipment tracking, ETA, exception monitoring, or appointment
scheduling. When NOT:
- the competing real-time visibility platform is FourKites, not project44 -> `fourkites`
- TMS execution - tender / book / rate / dispatch / settle a load, not just watch it -> `oracle-otm` or `sap-tm`
- the OMS / ERP order, PO, and inventory records the tracking sits on top of -> the ERP's own skill (`sap-mm`, `oracle-erp`)
- warehouse / yard execution beyond scheduling (bins, tasks, waves, dock doors as work) -> `manhattan-wms` or `sap-ewm`
- customs / export screening / entry filing on the container -> `sap-gts`
- supply-chain risk scoring and n-tier supplier mapping -> `everstream`

## The surfaces (know which mode / product you are on)
Movement is one platform over many modes; each mode has its own data sources, milestone set, and freshness.
- **Truckload (FTL) & LTL** - the highest-frequency modes. Tracked by ELD / telematics, a mobile driver app, or
  carrier API / EDI 214. Geofence-based arrival / departure, dwell and detention, dynamic ETA. Deep mechanics in
  `references/modes-and-milestones.md`.
- **Ocean** - container tracking by AIS vessel position plus carrier / terminal milestones (loaded, departed,
  transshipment, discharged, gate-out). Low-frequency, milestone-driven. Carries **last free day (LFD)**,
  demurrage and detention (D&D), booking / bill of lading / container numbers. `references/modes-and-milestones.md`.
- **Air** - master / house air waybill, flight status, and IATA cargo milestones (received, departed, arrived,
  recovered, delivered).
- **Parcel** - carrier scan events (manifest, in-transit, out-for-delivery, delivered) from the parcel carriers.
- **Rail / intermodal** - railroad milestones and drayage legs; often a leg inside an ocean or truckload journey.
- **Yard / dock & appointment scheduling** - dock and yard appointment booking, gate events, and dwell in the
  yard. Booking / moving an appointment is a committing write.
- **Order / PO visibility & inventory-in-transit** - rolls shipment status up to the customer order / PO and
  shows goods in transit as a supply position (not on-shelf inventory).
- **Emissions visibility** - modeled CO2 / GHG per shipment; an estimate from distance, mode, and factors.

## Object & state model (reason about state, not nouns)
- **Shipment** - the tracked movement. States: **planned / booked -> tendered -> in-transit -> at-stop /
  dwelling -> delivered -> closed (POD)**, with **exception** as an orthogonal flag on any state. A shipment
  references a carrier **load** and one or more customer **orders / POs**; the mapping is not always one-to-one.
- **Milestone / status event** - a timestamped happening (departed pickup, arrived delivery, loaded, discharged,
  out-for-delivery, delivered). Source-stamped (ELD, EDI 214, AIS, scan) and can arrive **late, out of order, or
  duplicated**. A milestone is a claim from its source, not proof.
- **ETA** - three different numbers: **planned / appointment ETA** (the commitment), **carrier-provided ETA**
  (what the carrier says), and **predicted / dynamic ETA** (project44's ML estimate). They routinely disagree;
  know which one you are quoting. The predicted ETA is a moving snapshot, refreshed as pings and events land.
- **Tracking method / connection** - how a shipment is tracked: ELD, telematics, mobile app, carrier API, or
  EDI 214. Each has different frequency, coverage, and consent. A carrier must be **connected / onboarded** for
  any telemetry; an unconnected carrier's shipment is invisible, not on-time.
- **Location ping** - a GPS position with a timestamp. **Fresh** (recent) vs **stale** (old); a stale ping is
  last-known, not current. Gaps are normal (coverage, device off, app closed).
- **Geofence** - a virtual boundary around a stop / facility. Arrival and departure events fire on crossing it;
  the radius and placement decide when dwell and detention clocks start.
- **Exception** - a deviation flagged against the plan: late, at-risk, dwelling, detention risk, off-route,
  stopped, temperature excursion. States: **open -> acknowledged -> resolved / dismissed**; adjudication is an
  attributable, logged decision.
- **Appointment** - a scheduled dock / yard slot at a facility. States: **requested -> confirmed -> arrived ->
  completed**, or **rescheduled / cancelled**. Booking or moving it binds a physical resource and notifies parties.
- **Ocean container** - carries a **last free day (LFD)**; discharge does not equal pickup-ready (needs customs
  release, line release, terminal availability). Demurrage and detention clocks run off terminal / equipment
  events. `references/modes-and-milestones.md`.
- **Data quality / tracking quality** - a completeness / confidence signal on a shipment's telemetry. Low quality
  means the ETA and status are unreliable; reason on quality, do not treat every shipment as equally trustworthy.

## Vocabulary that bites
- **Predicted / dynamic ETA** - an ML estimate that updates continuously; not a carrier commitment and not the
  planned appointment. Quoting it to a customer as a promise turns a moving estimate into a broken commitment.
- **Carrier-provided vs predicted ETA** - two different numbers on the same shipment. Using the carrier's number
  where you meant the prediction (or vice-versa) mis-sets a downstream decision.
- **Milestone / EDI 214 status** - a carrier self-reported status event. A "delivered" (D1) from EDI is a claim,
  and its timestamp can be batch-sent or back-dated; treat it as reported, not verified. Codes in `references/modes-and-milestones.md`.
- **Tracking gap / stale ping** - no location for a while. It means the device / app / coverage dropped, **not**
  that the truck stopped. Absence of a ping is not absence of movement.
- **Geofence radius** - the drawn boundary that triggers arrival / departure. Too large or mis-placed and it
  fires the event early or late, mis-timing dwell and the detention clock.
- **Dwell vs detention** - **dwell** is time at a stop; **detention** is dwell past the free time, which accrues
  a charge. A mis-timed arrival event mis-computes both.
- **Last free day (LFD) / demurrage / detention (ocean)** - LFD is the last day before **demurrage** (container
  sitting at the terminal) starts; **detention** is holding the carrier's equipment past free time. LFD is
  provided by the carrier / terminal and can change; a stale LFD misses the window.
- **Discharged vs available** - an ocean container discharged from the vessel is not pickup-ready until customs
  release, line / freight release, and terminal availability. "Discharged" is not "ready."
- **Tracking method** - ELD / telematics / mobile / API / EDI, each with different frequency, coverage, and
  consent. The ETA and status confidence inherit the method's quality.
- **Carrier connection / onboarding** - a carrier must be connected for tracking. "No exceptions" on an
  unconnected shipment means "no data," not "on time."
- **Party / tenant scope** - shipper vs carrier vs broker / LSP entitlement. A shipment you can see may carry
  another party's data you may not forward. Cross-party / cross-tenant sharing is egress.
- **POD (proof of delivery)** - the delivery confirmation (signature, photo, scan). It is the record a delivery
  claim rests on; a "delivered" milestone without a POD is weaker evidence.

## Operations: read / write / by data sensitivity and egress
Almost everything is a read - so gate by where the data goes, what a config change moves, and which writes bind
a physical resource or a downstream action, not by "does it write." No tool names; kinds of action.

| Class | project44 / Movement operation families | Gate | Why |
|---|---|---|---|
| **Read (in-boundary)** | display a shipment / order / container status, milestones, and location; view the predicted / carrier / planned ETA and data quality; list exceptions and dwell / detention; view a lane, facility, or carrier performance; view an appointment; view emissions estimates; run an in-tenant report | pass for in-tenant reasoning; **egress-gate any output** | no state change - but egress and party-scope rules apply before any output to a user or another system (see below). Read the ETA type, the ping freshness, the tracking method, and the data quality before you rely on it |
| **Write (reversible, local scope)** | subscribe / unsubscribe an alert or notification; snooze / mute an exception; acknowledge or annotate an exception; add / remove a shipment or lane from a **personal watchlist or filter view** (not platform monitoring - removing from monitoring entirely is destructive, see the row below); save a **personal filter / view configuration (in-tenant, no data export)** | gate one at a time (elevate to human approve when the shipment has an active exception, a detention clock running, or a customer-facing commitment) | changes *your* coverage or view, not shared truth - but the write is reversible while its consequence is not: muting an exception or dropping a lane from a watchlist opens a blind spot, and a disruption missed during the gap costs lead time you cannot recover. Generating or **exporting a report artifact** with named-shipment data is not this row - it is egress-gated (see below) |
| **Write (committing, shared / physical / cross-system)** | create a **tracking request** - onboard a shipment / carrier to platform tracking (begins ingesting carrier / telematics data, starts the milestone and ETA pipeline, and can invoke the carrier's driver-location consent); book / confirm / reschedule / cancel a dock or yard **appointment** (binds a physical slot, notifies the facility and carrier, can start / stop a detention clock); adjudicate an exception as resolved / false-positive (attributable, suppresses future signal); change alert thresholds or geofence definitions (changes what fires / when events trigger, account-wide); send a customer / party a shipment update or tracking link (a delivery-facing commitment); **push an ETA / status / exception back into the TMS / OMS / ERP / WMS** (drives a committing write there) | gate + human approve | binds a physical resource, an attributable record, tenant-wide config, an external commitment, or a downstream action; the uncertainty in a prediction becomes a hard decision others act on |
| **Destructive / high-sensitivity** | **egress of shipment / customer / location / driver / PO data, or another party's data, to an external tool, unapproved endpoint, other party, or broad audience**; delete or overwrite a shipment's tracking history / milestone timeline (the evidence trail for a D&D or delivery dispute); disconnect a carrier or remove a shipment / lane from monitoring entirely; drive an irreversible real-world action (reject a load, dispute / waive a detention charge, invoke a penalty, cancel / re-route, refuse a delivery) on a single unconfirmed read | HARD GATE + named owner + re-read | data that leaves cannot be recalled and can breach a contract, NDA, driver-privacy consent, or a competitor line; a deleted timeline destroys dispute evidence; a wrong irreversible call off a predicted or self-reported read is a real-world loss |

**The gate ladder (what each Gate cell means in practice):**
- **gate one at a time** (reversible local write) - a confirmation before acting, a captured reason (why this
  lane is dropped, why this exception is muted), and an audit-log entry, per action and not batched. Muting a
  signal opens a blind spot, so each is confirmed and logged on its own. A batch request ("mute all exceptions
  on these 50 shipments," "export every late shipment") is gated **per item at the highest sensitivity class in
  the batch**, not at the class of the average item. Unsubscribing the **last remaining alert** on a shipment
  leaves it silent - that is functionally removing it from monitoring, so escalate it to the destructive gate.
- **gate + human approve** (committing) - explicit human sign-off before it binds a physical slot, an
  attributable record, tenant config, an external message, or a downstream write; re-read the current status
  first, because ETAs, pings, and appointment availability drift.
- **HARD GATE + named owner + re-read** (destructive / high-sensitivity) - a specific accountable person
  authorizes; block until they sign off; re-read the current state at execute; and log the payload class and the
  reason. For egress with no approved destination, the default is refuse and escalate, not proceed.

**Egress is its own axis (read this):** the read / write columns above describe state change; egress is
orthogonal. The *same* read that is safe in-platform becomes the most dangerous action in the platform the
moment its output crosses the trust boundary - and the trust boundary includes your own reply to a user who
lacks entitlement, and any move across a party or tenant line. Before any export, forward, share, tracking-link,
push, or rendering of sensitive detail in a response, treat the payload as a controlled disclosure: what data
class is it (named-shipment lane / live driver location / customer PO / another party's data / carrier
performance), who is the audience and their entitlement, and is that destination approved (allowlist or data
owner; if unknown, default to block). Aggregate, de-identified, in-tenant reads are lower sensitivity than a
named shipment's live location, though a lane-level export (for example, "every shipment on the Shanghai ->
Long Beach lane this month") still exposes network composition and is gated on egress. **Combining sources
raises the class:** joining project44 tracking with the customer's PO from the ERP, or one party's shipments
with another's, creates a new data class whose sensitivity is the union of both - gate the combined output as
egress from both, not the lower of the two.

**Cross-system push can be destructive-by-proxy.** A status / ETA / exception pushed back into the TMS / OMS /
ERP / WMS is a committing write in project44, but in a target system configured for automation it can trigger an
automatic re-tender, a customer delivery-failure notice, a detention charge posted to AP, an inventory release,
or a cancelled order - practically irreversible. Gate the push against the *target system's* automation, not
just project44's write class; if the target auto-acts, treat the push as destructive and apply the hard gate.
If you cannot determine whether the target system auto-acts on the pushed data, default to treating the push as
destructive; do not assume the target is passive.

Universal rules to teach: read the ETA type, the ping freshness, the tracking method, the data quality, and the
party scope before you rely on a status or ETA; re-read at decision time because pings, ETAs, milestones, and
appointment availability all drift; never silence tracking or mute an exception to reduce noise; never let a
predicted ETA, a self-reported milestone, or a single sensor read trigger an irreversible action without
corroboration; treat an appointment as a physical commitment; keep sensitive telemetry inside the approved
tenant, party scope, and audience.

## Gotchas that bite (the real set - causal chains)
The safety-critical chains - check these before any irreversible or outbound action - are egress (#13, #14,
#15, #16), acting on an unconfirmed read (#1, #2, #6, #7, #18), the appointment commitment (#10), and silencing
the signal (#11, #12). The rest are operational: they corrupt a decision but do not by themselves cause an
irreversible loss.
1. **A predicted / dynamic ETA is an ML estimate, not a commitment.** Quoting it to a customer as a delivery promise, or auto-booking a downstream appointment to it, turns a number that will move into a broken commitment when it slips.
2. **There are three ETAs and they disagree.** Planned / appointment, carrier-provided, and predicted are different numbers; using the wrong one for a promise, a detention dispute, or a re-plan mis-sets the decision. Confirm which ETA you are reading.
3. **A stale ping is last-known, not current.** No location for hours means the ELD, app, or coverage dropped, not that the truck stopped; reporting last-known as current under-states progress and can mis-fire an "at-risk" call.
4. **A tracking gap is normal, not an exception.** Absence of pings is absence of data, not absence of movement; treating every gap as a stopped truck floods the queue and hides the gaps that do matter.
5. **The geofence radius decides when arrival fires.** A too-large or mis-placed geofence fires arrival early or late, which mis-starts the dwell and detention clocks; a detention dispute built on a mis-timed arrival is baseless.
6. **A carrier EDI 214 milestone is self-reported.** A "delivered" (D1) or "arrived" status is the carrier's claim, and its timestamp can be batch-sent or back-dated; a delivery claim without a POD is weaker evidence. `references/modes-and-milestones.md`.
7. **Milestones arrive late, out of order, or duplicated.** A missing "delivered" does not mean not delivered, and an out-of-order "departed" after "arrived" is a data artifact; reason on the event set and its sources, not one event's presence.
8. **Discharged is not available (ocean).** A container discharged from the vessel still needs customs release, line / freight release, and terminal availability before pickup; planning drayage off the discharge event alone strands the box. `references/modes-and-milestones.md`.
9. **Last free day (LFD) changes and drives demurrage.** LFD is provided by the carrier / terminal and can move; acting on a stale LFD misses the demurrage window, and the charge accrues per day. Re-read LFD at decision time. `references/modes-and-milestones.md`.
10. **Booking or moving an appointment is a physical commitment.** It binds a dock / yard slot, notifies the facility and carrier, can bump another appointment, and can start or stop a detention clock; it is not a calendar entry, and a missed booked slot can itself trigger detention.
11. **Muting or snoozing an exception suppresses the signal, not the event.** The late shipment still runs late; a muted real exception becomes a missed disruption, and lead time is the thing you cannot get back.
12. **Removing a shipment / lane from tracking, or disconnecting a carrier, stops all its telemetry.** A silent blind spot - you learn it mattered only after the disruption you no longer see; the gap does not backfill when you re-add it.
13. **Shipment lane data is competitively sensitive.** Who ships what to whom, on which lane, at what volume, egressed to an external tool or another party, exposes a customer's sourcing and network and cannot be recalled once sent.
14. **Driver / asset live location is privacy- and consent-governed.** GPS comes through the carrier's ELD / telematics under the carrier's consent; forwarding a driver's real-time position beyond the authorized scope breaches privacy and the carrier agreement.
15. **A shipment you can see can carry another party's data.** Rates, other legs, contacts, and competing-shipper detail ride on a shipment across a party line; forwarding the whole record leaks data that is not yours to share. Scope the export to your party's entitlement.
16. **Your own reply is an egress channel.** Summarizing named-shipment locations, a driver's live position, or a carrier's performance back to an audience without entitlement is egress even when the read was "always pass"; prefer an aggregate or de-identified summary.
17. **Changing an alert threshold or geofence is account-wide config.** Loosening an "at-risk" threshold or resizing a geofence silently changes what fires and when arrival triggers for every shipment on the account, not just your view; it is a committing config change.
18. **A temperature or sensor excursion is one sensor's claim.** Rejecting a reefer load or triggering a penalty on a single excursion reading, without corroborating the sensor, the duration, and the product spec, can scrap good freight.
19. **Data quality varies by tracking method and carrier.** An ELD-tracked truckload updates far more often than an EDI-only LTL or a milestone-driven ocean container; applying one confidence rule across modes misreads the low-quality ones. Read the data-quality signal.
20. **Deleting or overwriting a shipment's milestone timeline destroys dispute evidence.** The timeline is the record a demurrage / detention or delivery dispute rests on; a gap or a wrong edit weakens the claim and cannot be reconstructed after the fact.
21. **Inventory-in-transit is not on the shelf.** Treating goods in transit as available inventory for ATP / allocation pulls the in-transit quantity into an availability promise; the ETA then slips and the goods arrive late, so the promise made on it becomes a stockout on arrival. It is on the water or the road, arrival-dated by a moving ETA, not received.
22. **One event hits many shipments at once (correlated).** A port congestion, weather, or terminal closure event exposes your whole lane or region; reading one shipment's delay misses the systemic exposure - read the event's full impact set.
23. **Time zones and local timestamps mis-compute dwell and on-time.** A milestone stamped in local time compared against a UTC plan mis-reads dwell, detention, and on-time; normalize the time base before computing.
24. **A closed / delivered shipment can re-open or correct.** A late POD, a delivery reversal, or a corrected milestone can flip a "delivered" back; standing down on an early delivery read can miss a redelivery or a claim.

(More per-topic detail: `references/modes-and-milestones.md`, `references/etas-exceptions-egress.md`.)

## Edge states & special cases
Each breaks naive "the ETA says on-time / the milestone says delivered, so act" logic - key rule inline, full
behavior in references.
- **Mode differences** - ocean (AIS + milestones, low-frequency), air (flight status), parcel (scan events), LTL
  (carrier EDI / API), truckload (ELD / mobile, high-frequency). ETA confidence and freshness differ per mode; a
  single rule across modes misreads. `references/modes-and-milestones.md`.
- **Multi-leg / transshipment / intermodal** - ocean transshipment, rail drayage, an air-to-truck handoff; the
  ETA to final destination depends on the connection, and a single-leg read misses the handoff risk. `references/modes-and-milestones.md`.
- **Tracking gap vs stopped** - no ping is missing data, not a stopped truck; corroborate before flagging.
- **Geofence boundary cases** - a shipment just outside a facility geofence has not "arrived" yet, and a large
  geofence can fire arrival on a nearby road; the radius is an estimate, so treat borderline dwell / detention
  timing as uncertain.
- **Unconnected carrier / no telemetry** - a shipment on an unconnected carrier is invisible, not on-time; "no
  exceptions" here means "no data." Flag it as untracked, do not record it as healthy. When asked for its ETA or
  status, answer with the explicit "untracked / no telemetry" qualifier and fall back to the carrier / TMS
  booking; do not synthesize an ETA from a stale or absent read.
- **Reefer / temperature** - a single excursion is one sensor's claim; corroborate duration and product spec
  before an irreversible reject. `references/etas-exceptions-egress.md`.
- **Degraded / error / timeout** - if project44 errors, times out, or serves data past its refresh cycle, fail
  safe: do not act on a cached ETA, treat a stale ping as unknown rather than current, and treat a blank
  exception feed as "unknown," not "all clear." Fall back to the carrier / TMS for the authoritative booking
  when telemetry is missing. **Systemic outage vs one shipment:** if the platform is down or serving stale data
  at scale (not one shipment), do NOT batch-act on cached data across the fleet - escalate to a human, hold
  committing writes, and wait for recovery; a single stale read is a data-quality flag, a fleet-wide one is an
  outage.
- **Order-to-shipment mapping** - one order can span several shipments and one shipment several orders; rolling
  status up to the customer PO needs the mapping, or a partial shipment reads as a whole-order status. When the
  mapping conflicts with the source systems, the OMS / ERP owns the order identity and the TMS / carrier owns the
  load; flag the discrepancy to a human, do not silently merge or re-key.

## Reconciliation / freshness
An ETA, a ping, a milestone, and an LFD are all snapshots. Re-read at decision time: predicted ETAs refresh as
pings and events land, milestones arrive late and correct, LFD moves, and appointment availability changes. When
project44 and the TMS / carrier disagree on the booking, mode, or equipment, the TMS / carrier system of record
wins for the commitment; project44's value is the live position and the predicted arrival on top of it. When
project44 and the OMS / ERP disagree on the order or PO, the ERP is the record of what was ordered; project44
tells you where it is. The system-of-record split: the **TMS / carrier owns the booking and the
milestone-of-record state, project44 owns the live position and the predicted ETA**. When the two disagree on a
milestone (project44 shows in-transit, the TMS shows delivered), do not treat either as confirmed truth -
corroborate with a second source before acting. Treat a ping older than the mode's normal update cadence, or an
ETA past its refresh, as stale. **Re-read within limits:** "re-read at decision time" does not mean poll every
shipment continuously - do not poll a single shipment faster than roughly its mode's natural cadence (ELD /
mobile in minutes, ocean in tens of minutes to hours, LTL / parcel per event), and during a correlated event
(port congestion, weather) that can hit API rate limits, prioritize the shipments with a running detention
clock, a near LFD, or a customer commitment and read the rest at a lower cadence or in batch.

## Recovery patterns (can it be undone, and what can't)
- **Egress cannot be undone.** Data that crossed the trust boundary or a party line cannot be recalled; a wrong
  disclosure of a lane, a driver's location, or a customer's PO is a reportable event, not a fixable edit. This
  is the irreversible action in the platform - gate it hardest. If egress happens in error: notify the data
  owner and the affected party immediately, document what was disclosed and to whom, and do not try to "fix" it
  by deleting data in the target system, which is a separate write with its own gate.
- **A booked / moved appointment** is reversible by rescheduling, but the notified facility and carrier already
  acted, the bumped slot may be gone, and a detention clock already started does not un-start; treat a
  reschedule as a new commitment, not an undo.
- **Muting an exception or dropping a lane from tracking** is reversible by re-enabling, but the disruption
  missed during the blind window, and the lead time lost, do not backfill.
- **An alert-threshold / geofence change** is reversible by reverting, but any events that fired (or failed to
  fire) and any decisions made on them in between still stand.
- **Exception adjudication** is corrected by a new entry (the trail keeps both), not a silent undo; the original
  decision stays attributable.
- **A deleted milestone timeline / tracking history** may not be reconstructable - treat it as destructive, not
  housekeeping, because it is the evidence a dispute rests on.

## Guardrails
- If your action logic reduces to "the predicted ETA says on-time, so promise it" or "the milestone says
  delivered, so close it," stop and re-read: a predicted ETA is a moving estimate and a milestone is
  self-reported; neither supports an irreversible move on its own.
- Read the ETA type, the ping freshness, the tracking method, the data quality, and the party scope before you
  rely on any status or ETA; re-read at decision time because pings, ETAs, milestones, LFD, and appointment
  availability all drift.
- Egress is the high-risk act: before any export, forward, share, tracking-link, or push, classify the payload
  (named-shipment lane / live driver location / customer PO / another party's data / carrier performance),
  confirm the audience and entitlement, and confirm the destination is approved. Prefer aggregate, de-identified,
  in-tenant reads over named-shipment / live-location exports.
- Respect the party / tenant line and driver-location consent: a shipment you can see can carry data you may not
  forward.
- Never promise a customer delivery, reject a load, dispute or waive a detention charge, invoke a penalty, or
  re-route on a single unconfirmed read; corroborate a predicted ETA, a self-reported milestone, or a single
  sensor reading first.
- Treat booking / moving an appointment as a physical commitment: gate it, re-read availability, and confirm the
  notified parties before acting.
- Do not change account-wide alert thresholds or geofence definitions casually - they change what fires for
  everyone.
- Do not mute exceptions or drop tracking to quiet noise; a blind spot is a missed disruption.
- When telemetry here would drive a committing write in the TMS / OMS / ERP / WMS, gate that write under the
  target system's rules and base it on corroborated status.

## References (load on demand)
- `references/modes-and-milestones.md` - load when working a specific mode: per-mode data sources (AIS, flight,
  ELD / telematics, mobile, EDI 214, parcel scan), the milestone / status-event families and the EDI 214 and
  IATA cargo codes that name them, ocean LFD / demurrage / detention and discharge-vs-available, multi-leg /
  transshipment, and per-mode freshness.
- `references/etas-exceptions-egress.md` - load when reading ETAs, handling exceptions, or deciding an outbound
  action: the three ETA types and predicted-ETA confidence, the exception taxonomy and dwell / detention clock,
  geofence mechanics, alert / notification config, appointment scheduling, and the data-sensitivity classes,
  party / tenant entitlement, and egress decision.
