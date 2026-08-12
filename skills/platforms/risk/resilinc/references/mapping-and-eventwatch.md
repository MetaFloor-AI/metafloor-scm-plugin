# Resilinc multi-tier map, BCP data, and EventWatch - attestation, exposure, alerts

The mapping layer and the monitoring layer. Load when working with the multi-tier / part-site map, BCP data, the
event/alert feed, a data-collection campaign, the war-game simulator, or adjudication. The rule under all of it:
the map is largely supplier-attested and partly incomplete, and an alert is an early correlated signal, so
source, freshness, and completeness decide how far you can act - and the map, watchlist, and adjudication trail
are shared config, not a private scratchpad.

## Contents
- Multi-tier map: attested vs inferred, completeness
- Part-site / BOM mapping
- Absence is not safety
- BCP data and the neutral-party trust
- Data-collection campaigns
- Events vs alerts and impact assessment
- The monitored network / watchlist
- The war-game / what-if simulator
- Adjudication and the audit trail
- Tier-1 reconciliation to the ERP

## Multi-tier map: attested vs inferred, completeness
The n-tier graph maps supplier relationships below tier-1 (tier-2 ... tier-N) at company, site, part, and
sub-commodity / BOM level. Its distinctive source is **supplier attestation**: mapped suppliers complete
profiles reporting their own sites and sub-tier suppliers, supplemented by customer-provided and external data.
- **Supplier-attested** edges are stronger than pure inference but are still self-reports: a supplier can omit
  sub-tiers it does not want to disclose, or leave the profile stale.
- **Completeness is a response rate.** The map reflects who actually completed a profile; a large unmapped
  fraction means silence in the graph is unreliable.
- **Validating or rejecting a reported edge is a committing write** - it rewrites the shared map everyone
  downstream reasons on. A wrong validation propagates a false relationship; a wrong rejection hides a real one.

## Part-site / BOM mapping
Parts are mapped to the manufacturing sites that make them, and up through the bill of materials to your
products and their revenue. This backbone drives Revenue-at-Risk and impact assessment:
- A **missing part-site edge** silently under-states exposure - the site looks low-impact only because the map
  does not know what it makes for you.
- The mapping exposes your product's recipe and sourcing; treat it as competitively sensitive, egress-controlled
  data, not internal plumbing.

## Absence is not safety
The map shows what suppliers reported and what external data found. A missing tier-N node is not proof of no
exposure - it may be unmapped, newly added, or withheld. Do not read a clean map as "no single point of
failure"; read it as "none that has been reported." Statements to auditors, customers, or the public about "no
exposure to X" must rest on validated data, not on silence.

## BCP data and the neutral-party trust
Business-continuity data - recovery plans, reported **TTR**, alternate sites, emergency contacts - is the
highest-sensitivity supplier data class. Suppliers share it with Resilinc under a **neutral-third-party** model,
trusting it stays permissioned and does not leak to competitors or beyond approved users.
- Treat BCP data as held in trust: egressing it to another supplier, a competitor-adjacent audience, or an
  external tool breaks that trust, may breach NDA, and cannot be recalled.
- Emergency contacts are **personal data** - forwarding them outside the approved audience is a privacy exposure
  with its own legal weight.
- A reported TTR is a **claim, often untested**; pressure-test it against your TTS rather than banking on it.

## Data-collection campaigns
A campaign (or survey) sends outbound requests to suppliers to complete or refresh their profiles - sub-tier,
sites, BCP, TTR.
- Launching a campaign **contacts real third parties** (usually by email) at scale; it is a relationship-weighty,
  attributable outbound action, and it **cannot be un-sent**.
- Scope the audience and the content before launch. A broad or repetitive blast fatigues suppliers, lowers
  response quality, and can strain relationships. Do not fire one casually to "just get more data."
- Completeness improves only as suppliers respond; a launched campaign does not backfill the map instantly.

## Events vs alerts and impact assessment
- An **event / incident** is a real-world happening EventWatch detects worldwide (weather, geopolitical, fire,
  financial, cyber, health, logistics), with a category, severity, geofenced area, and time.
- An **alert** is that event **correlated to your mapped network** - the sites, parts, and Revenue-at-Risk it
  touches ("potentially impacted"). An alert is an **early warning**, not a confirmed impact on you.
- **"Potentially impacted"** is a correlation of the event's area to your map: a flagged site may be unaffected,
  and one just outside can still be down. Validate before acting.
- Event states: **emerging -> updated -> closed**, and a closed event can **re-open or escalate** (an aftershock,
  a secondary closure, a sanctions expansion). Re-read status at execute, not only at first alert.
- Alerts carry **recommended actions and a severity**. Treat them as guidance to validate against your own
  inventory (TTS) and network, not as instructions to execute verbatim.

## The monitored network / watchlist
The monitored network (and watchlists within it) is the configured surveillance scope - which suppliers, sites,
and parts generate alerts.
- **Adding** a node is a low-blast, reversible local write.
- **Removing** a node stops all its alerts - a monitoring **blind spot**. It is reversible by re-adding, but the
  alerts that would have fired during the gap are gone, and re-collecting its map/BCP may need a fresh campaign.
  Never remove monitoring to reduce noise.
- **Muting / snoozing** an alert suppresses the signal, not the event; a real disruption missed during the mute
  costs lead time you cannot recover.

## The war-game / what-if simulator
The simulator models a disruption - a site, a supplier, a region - and shows modeled exposure, TTR/TTS gaps, and
Revenue-at-Risk across the network.
- A **run is a simulation** - it changes nothing and is a read.
- **Saving a draft** is a local write; **publishing or sharing** a scenario, or pushing its output into a plan,
  is a committing action others will act on. Do not publish a scenario built on stale or low-completeness data as
  if it were validated exposure.

## Adjudication and the audit trail
Adjudicating an alert (impacted / not-impacted / resolved) and writing a risk-register entry are **attributable,
logged decisions**:
- A not-impacted / resolved mark on a real alert leaves a record that you saw it and dismissed it - adjudicate
  with evidence, not to clear the queue.
- Corrections are made by a **new entry**; the trail keeps both, so the original decision stays attributable.
  There is no silent undo.

## Tier-1 reconciliation to the ERP
Resilinc's tier-1 layer should reconcile to the **ERP supplier master** - the record of who you actually buy
from. Where they disagree at tier-1, the ERP is the record; Resilinc's value is the resiliency overlay, the BCP
data, and the supplier-reported network **below** tier-1. Do not let a Resilinc tier-1 entry override the ERP's
actual supplier of record.
