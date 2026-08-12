# Interos relationship graph and monitoring - inference, entity resolution, concentration, propagation, alerts

The mapping layer and the monitoring layer. Load when working with the AI-modeled relationship graph, the
concentration / single-source analytics, risk propagation, the event/alert feed, the watchlist/portfolio, or
adjudication. The rule under all of it: the graph is model-derived and the alert is an early signal, so
confidence, entity match, and freshness decide how far you can act - and the graph and watchlist are shared
config, not a private scratchpad.

## Contents
- The graph: model-inferred vs curated, confidence
- Entity resolution
- Concentration / single-source / shared-node exposure
- Risk propagation / cascading
- Absence is not safety
- Events vs alerts
- The watchlist / portfolio and continuous monitoring
- Graph curation as a shared write
- Adjudication and the audit trail
- Tier-1 reconciliation to the ERP

## The graph: model-inferred vs curated, confidence
The interconnected graph maps supplier relationships below tier-1 (tier-2, tier-3 ... tier-N) at company and
site level. Its distinctive property is that it is **AI-modeled at scale**, built from three kinds of data:
- **Public / external** - customs, trade, corporate registry, and open data.
- **Licensed** - purchased data feeds.
- **Model-inferred** - links Interos' models predict from patterns in the data.
Unlike a supplier-attested map (`resilinc`), most edges are not self-reported by the supplier. Each
edge carries a **confidence**. A high-confidence, corroborated edge is close to fact; a low-confidence inferred
tier-4 edge is a lead. Reasoning on the graph means reasoning on confidence and source, not just on whether a
line is drawn.

## Entity resolution
Every node is a **machine-resolved** entity: Interos matches a real-world company (with its many name variants,
subsidiaries, and locations) to one graph node. This is a graph-scale failure point unique to this platform:
- A **name collision** or a bad match can attach another company's i-Score, sanctions status, financial
  distress, or events to your supplier.
- Before acting on an attached score or flag, **verify the entity match** (right legal entity, right site). When
  the match is uncertain, propose a correction rather than trusting the attached risk.
- Correcting a resolution (merge / split an entity) rewrites the shared graph - it is a committing curation.

## Concentration / single-source / shared-node exposure
Interos' signature analytic reads the graph for hidden single points of failure:
- **Geographic concentration** - many of your suppliers (or one supplier's sites) clustered in one region or
  hazard zone.
- **Single-source** - a part or material with only one viable source in your mapped graph.
- **Shared-node exposure** - the case the graph is built to catch: many of your otherwise-independent tier-1s
  route up to **one shared upstream node** (a tier-3/4 sub-supplier) - a concentration invisible at tier-1.
Consequences for judgment:
- The finding is **modeled from the graph**, so a missing edge silently understates it; absence of a
  concentration finding is not proof of no concentration.
- **Failover can worsen concentration:** switching to "alternate" suppliers that share the same upstream node
  concentrates you into the very failure you were fleeing. Read the shared-node map before recommending failover.

## Risk propagation / cascading
Interos pushes a node's risk **through** the modeled links, so a disruption or a factor hit at a deep upstream
node surfaces as exposure at your tier-1.
- Propagated risk rides on a **chain of inferred edges**; its certainty is the **weakest edge in the path**.
- Treat a cascading alert as a **lead to trace** (walk the path, check each edge's confidence and each entity's
  resolution), not a confirmed impact to act on irreversibly.

## Absence is not safety
The graph maps what it can model. A missing tier-N node is not proof you have no exposure there - it may be
unmapped, newly formed, or below the data's visibility. Do not read a clean graph as "no single point of
failure"; read it as "none that has been modeled." Statements to auditors, customers, or the public about "no
exposure to X" must rest on corroborated edges, not on silence in the graph.

## Events vs alerts
- An **event / incident** is a real-world happening Interos detects (financial distress, cyber breach, natural
  hazard, geopolitical, a new sanctions listing, ESG violation), with a factor category, severity, and time.
- An **alert** is that event (or a score/factor change) **correlated to your graph** - and it may be
  **propagated** from an upstream node rather than a direct hit on your tier-1. An alert is an **early warning**,
  not a confirmed impact on you.
- Event states: **emerging -> updated -> closed**, and a closed event can **re-open or escalate** (an aftershock,
  a secondary closure, a sanctions expansion). Re-read status at execute, not only at first alert.
- Alerts carry a **severity and suggested context**. Treat them as guidance to validate against your own
  inventory and network, not as instructions to execute verbatim.
- One region or shared-node event is **correlated risk** across many of your entities at once; read the full
  impact set, not one entity's flag.

## The watchlist / portfolio and continuous monitoring
Interos monitors the graph **continuously and by default**; the watchlist/portfolio is the set of entities you
**actively track and get alerted on**, not whether the world is watched.
- **Adding** an entity to a watchlist is a low-blast, reversible local write.
- **Removing** an entity stops its active alerts to you - a monitoring **blind spot**. It is reversible by
  re-adding, but the alerts that would have fired during the gap are gone. Never remove monitoring to reduce noise.
- **Muting / snoozing** an alert suppresses the signal, not the event; a real disruption missed during the mute
  costs lead time you cannot recover.

## Graph curation as a shared write
Confirming or rejecting an inferred edge, or correcting an entity resolution, is a **committing write on shared
state**:
- Everyone downstream reasons on the curated graph. A wrong confirmation propagates a false relationship, a wrong
  rejection hides a real one, and a wrong entity merge/split mis-attributes risk across every future analysis.
- A curation is corrected only by a new edit, and the wrong one has already flowed through every analysis run
  against it in the interim. Gate it as committing, re-read first, and capture the reason.

## Adjudication and the audit trail
Adjudicating an alert (relevant / not-relevant / resolved) and writing a risk-register entry are **attributable,
logged decisions**:
- A not-relevant / resolved mark on a real alert leaves a record that you saw it and dismissed it - adjudicate
  with evidence, not to clear the queue.
- Corrections are made by a **new entry**; the trail keeps both, so the original decision stays attributable.
  There is no silent undo.

## Tier-1 reconciliation to the ERP
Interos' tier-1 layer should reconcile to the **ERP supplier master** - the record of who you actually buy from.
Where they disagree at tier-1, the ERP is the record; Interos' value is the risk overlay, the n-tier graph, and
the concentration analytics **below** tier-1. Do not let a model-inferred Interos tier-1 edge override the ERP's
actual supplier of record.
