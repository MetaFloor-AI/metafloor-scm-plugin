# Everstream n-tier map and monitoring - inference, exposure, alerts

The mapping layer (Discover) and the monitoring layer (Reveal). Load when working with the sub-tier graph, the
incident/alert feed, an exposure assessment, the monitored network, or a scenario. The rule under all of it:
the map is partly inferred and the alert is an early signal, so confidence and freshness decide how far you can
act - and the graph and the watchlist are shared config, not a private scratchpad.

## Contents
- Sub-tier map: inference vs curation, confidence
- Absence is not safety
- Incidents vs alerts
- Exposure, geofence, and impact radius
- The monitored network / watchlist
- The Scenario Builder
- Adjudication and the audit trail
- Tier-1 reconciliation to the ERP

## Sub-tier map: inference vs curation, confidence
The n-tier graph maps supplier relationships below tier-1 (tier-2, tier-3 ... tier-N) at company, site, part,
and material level. It is built from three kinds of data:
- **Customer-provided** - what you told it (highest trust).
- **Public / external** - customs, trade, corporate data.
- **Data-science-derived** - inferred links Everstream's models predict.
Each edge carries a **confidence level**. A high-confidence, customer-provided edge is close to fact; a
low-confidence inferred tier-3 edge is a lead. Reasoning on the graph means reasoning on confidence, not just
on whether a line is drawn. **Confirming or rejecting an edge is a committing write** - it rewrites the shared
graph everyone downstream reasons on, so a wrong confirmation propagates a false relationship and a wrong
rejection hides a real one.

## Absence is not safety
Discover maps what it can find. A missing tier-N node is not proof you have no exposure there - it may be
unmapped, newly added, or below the data's visibility. Do not read a clean map as "no single point of failure";
read it as "no single point of failure that we have found." Statements to auditors, customers, or the public
about "no exposure to X" must rest on confirmed edges, not on silence in the graph.

## Incidents vs alerts
- An **incident / event** is a real-world happening Everstream detects worldwide (weather, geopolitical,
  financial, ESG, cyber, health, logistics/port congestion), with a category, severity, geofenced area, and time.
- An **alert** is that incident intersected with **your** network ("my network") - the nodes, sites, lanes,
  materials, and shipments it touches. An alert is an **early warning**, not a confirmed impact on you.
- Incident states: **emerging -> updated -> closed**, and a closed incident can **re-open or escalate** (an
  aftershock, a secondary closure, a sanctions expansion). Re-read status at execute, not only at first alert.
- Alerts carry **recommended actions**. Treat them as guidance to validate against your own inventory and
  network, not as instructions to execute verbatim.

## Exposure, geofence, and impact radius
Exposure is modeled: an event has a **geofence / impact radius** (a radius around an epicenter, a region, a
country), and a node is flagged exposed if it sits inside. This is an estimate:
- A node just **outside** the drawn area can still be affected; a node **inside** may be fine.
- Widen the read before concluding "no exposure," and read the **full impact set** of an event, not one node's
  flag - one port or region event is **correlated risk** across your whole category.

## The monitored network / watchlist
The monitored network (and watchlists within it) is the configured surveillance scope - which nodes, materials,
and lanes generate alerts.
- **Adding** a node is a low-blast, reversible local write.
- **Removing** a node stops all its alerts - a monitoring **blind spot**. It is reversible by re-adding, but
  the alerts that would have fired during the gap are gone, and re-discovering its sub-tier map may need to
  re-run. Never remove monitoring to reduce noise.
- **Muting / snoozing** an alert suppresses the signal, not the event; a real disruption missed during the mute
  costs lead time you cannot recover.

## The Scenario Builder
The Scenario Builder runs what-ifs: geofence an epicenter, select a region or a whole country, and see modeled
exposure across your network.
- A **run is a simulation** - it changes nothing and is a read.
- **Saving a draft** is a local write; **publishing or sharing** a scenario, or pushing its output into a plan,
  is a committing action others will act on. Do not publish a scenario built on low-confidence edges as if it
  were validated exposure.

## Adjudication and the audit trail
Adjudicating an alert (relevant / false-positive / resolved) and writing a risk-register entry are
**attributable, logged decisions**:
- A false-positive mark on a real alert leaves a record that you saw it and dismissed it - adjudicate with
  evidence, not to clear the queue.
- Corrections are made by a **new entry**; the trail keeps both, so the original decision stays attributable.
  There is no silent undo.

## Tier-1 reconciliation to the ERP
Everstream's tier-1 layer should reconcile to the **ERP supplier master** - the record of who you actually buy
from. Where they disagree at tier-1, the ERP is the record; Everstream's value is the risk overlay and the
inferred network **below** tier-1. Do not let an inferred Everstream tier-1 edge override the ERP's actual
supplier of record.
