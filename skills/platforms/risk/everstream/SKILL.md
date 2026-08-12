---
name: everstream
description: Everstream Analytics - the safe operation of supply-chain risk intelligence and multi-tier (n-tier)
  supplier visibility. Because it is mostly a read/intelligence system, actions are classified by data
  sensitivity and egress, not money or stock. Use when the connected risk system is Everstream and the work
  touches a risk score or unified risk score, a sub-tier / tier-2 / tier-3 / tier-N supplier map, a disruption
  alert or incident (weather, geopolitical, financial, ESG, forced-labor / UFLPA, cyber, port congestion), an
  exposure or impact-radius / geofence assessment, a watchlist or monitored network, a scorecard weighting, or
  a scenario; or the user mentions Everstream Discover, Explore, or Reveal, unified risk score, sub-tier
  visibility, supplier risk monitoring, or pushing a supplier risk flag back to the ERP or procurement system.
---

# Everstream Analytics - operating it safely

Everstream is a supply-chain risk intelligence layer, not a system of record. It maps your supplier network
below tier-1 (**Discover**), scores nodes for risk (**Explore**), and watches the world 24/7 for events that
hit your network (**Reveal**). Almost every operation is a read - and that is exactly what makes it different
from the ERP/WMS/trade systems in this plugin. **Here the danger is not posting money or stock; it is what the
intelligence is and where it goes.** The reads are safe. The hazards are three: (1) sensitive supplier and
sub-tier data leaving the trust boundary (egress), (2) tenant-wide config that silently re-scores or stops
watching, and (3) treating a probabilistic score, an inferred relationship, or an early alert as confirmed
fact and committing an irreversible action on it - usually in another system. Classify by **data sensitivity
and egress**, not by stock or dollars.

## Contents
- Read this first
- When this applies
- The three products
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
- **Egress is the high-risk act here.** Sub-tier maps ("who supplies whom"), named-supplier risk scores,
  financial-distress / forced-labor / sanctions findings, and the licensed third-party data behind the score
  are the most sensitive assets in the platform. Sending any of it to an external tool, an unapproved endpoint,
  a supplier, or a broad audience is a controlled disclosure, not a data pass-through. Once it leaves you
  cannot recall it. Keep intelligence inside the approved tenant and audience.
- **Your own reply is an egress channel.** Summarizing, quoting, or paraphrasing a sensitive read back to a
  user who lacks clearance is egress even though the read itself was "always pass." Before rendering a
  named-supplier score, a sub-tier edge, or a legally sensitive finding in a response, confirm the audience and
  role, and prefer an aggregate / de-identified summary over named-supplier detail.
- **Know if the destination is approved.** Before any export, forward, share, or push, check the tenant's
  approved-endpoint / allowlist or confirm with the data owner. If no allowlist is available, default to
  blocking egress of any named-supplier or sub-tier data rather than assuming it is permitted.
- **A score / inference / alert is a prior, not a verdict.** A risk score is a predictive estimate, a sub-tier
  edge is inferred with a confidence level, and an alert is an early signal matched to your network. None of
  them is a confirmed fact. Do not de-source a supplier, invoke force majeure, halt shipments, or push a
  hard block on a single unconfirmed read. Corroborate and re-read first.
- **The irreversible action lives in the other system.** Everstream informs; the ERP, procurement, planning,
  or trade system acts. When intelligence here would drive a committing write there (block a supplier for
  sourcing, cancel a PO, re-plan), gate that write in the target system under its own rules - and base it on
  corroborated risk, not a raw number.
- **Do not silence the signal to quiet the queue.** Removing a node from the monitored network, or muting an
  alert, creates a blind spot; a real disruption that fires during the gap is a missed disruption with lead
  time already lost.
- **Compliance decisions are not data edits here.** A sanctions or forced-labor hit is risk intelligence that
  routes to the compliance/trade system and a human officer; it is not adjudicated by editing a record in
  Everstream.

## When this applies
Connector is Everstream and the work is risk scoring, sub-tier mapping, disruption monitoring, or exposure
analysis. When NOT:
- deep supplier financial-health / viability scoring as the system of record -> `resilinc`
- interconnected-risk graph modeling and risk propagation across a network -> `interos`
- the ERP supplier master, PO, and inventory records the scores sit on top of -> `sap-mm` (or the ERP's own skill)
- denied-party / sanctions screening with block-and-release as the compliance system of record -> `sap-gts`
- real-time multimodal shipment ETA tracking as the system of record -> `project44` / `fourkites`

## The three products (know which surface you are on)
- **Discover** - multi-tier / n-tier network mapping. Reveals hidden supplier relationships and material flows
  below tier-1 (tier-2, tier-3 ... tier-N) at company, site, part, and material level. Mixes customer-provided,
  public, and data-science-derived data; many edges are inferred with a confidence level, some are curated.
- **Explore** - risk assessment and scoring. A unified risk score composed from category scores (financial,
  operational, ESG/ethical, geopolitical/sociopolitical, environmental/climate, compliance), location-based and
  entity-based, predictive, drawing on licensed third-party feeds (Dun & Bradstreet, RapidRatings, EcoVadis)
  plus Everstream's own intelligence. Deep taxonomy in `references/risk-scores.md`.
- **Reveal** - 24/7 global monitoring and alerting. Detects real-world incidents (weather, geopolitical,
  financial, ESG, cyber, health, logistics/port congestion) and matches them to *your* network ("my network"),
  producing alerts on assets, sites, lanes, materials, and shipments with recommended actions. Mechanics in
  `references/n-tier-and-monitoring.md`.

## Object & state model (reason about state, not nouns)
- **Node (supplier / site / entity)** - a company or physical location in your network. Carries category and
  unified risk scores, location, tier. Monitoring state: **monitored** (alerts fire) or **not monitored** (silent).
- **Sub-tier relationship (edge)** - a supply link at tier-N. States: **inferred (with a confidence level) ->
  confirmed** or **rejected** by curation. Direction and material matter (who supplies whom, for what).
- **Risk score** - per node, per material, per location. Predictive and refreshed as underlying data lands; a
  moving snapshot, not a fixed attribute. Higher score = more risk (confirm the direction before acting).
- **Incident / event** - a real-world happening Everstream detects, with a category, a severity, a geofenced
  impact area, and a time. States: **emerging -> updated -> closed**, and a closed one can re-open or escalate.
- **Alert** - an incident intersected with your network. States: **new -> acknowledged -> adjudicated**
  (relevant / false-positive / resolved) **-> closed**. Adjudication is an attributable, logged decision.
- **Watchlist / monitored network** - the configured surveillance scope (which nodes, materials, lanes are watched).
- **Scenario** - a saved what-if built in the Scenario Builder (geofence an epicenter or a whole country).
  States: **draft -> saved -> published/shared**. A run is a simulation; publishing is a shared artifact.
- **Risk-register entry** - a logged risk plus mitigation/owner; attributable, part of the audit trail.

## Vocabulary that bites
- **Unified risk score** - a composed, predictive estimate (higher = more risk), not a measurement. It is a
  prior for investigation, not proof; and it is only as fresh as the feeds behind it.
- **Sub-tier / n-tier** - relationships below your direct (tier-1) suppliers. Most tier-2+ edges are *inferred*,
  not contractual. "Tier-N" is depth, not certainty.
- **Confidence level** - how sure an inferred edge or attribution is. A low-confidence tier-3 link may be
  wrong; the confidence is the difference between a lead and a fact.
- **Incident vs alert** - an *incident/event* is a real-world happening; an *alert* is that incident matched to
  your network. An alert is an early warning, not a confirmed impact on you.
- **My network** - the filter that shows only incidents touching your mapped nodes/lanes/materials. It can hide
  events on unmapped upstream nodes or shared logistics hubs that still affect you.
- **Geofence / impact radius** - the drawn area of an event (a radius around an epicenter, a region, a
  country). A node just outside can still be hit; a node inside may be fine. It is an estimate.
- **Exposure / impact assessment** - the *result* of intersecting your monitored network with an event's
  geofenced impact radius: which of your nodes/lanes/materials fall inside. It is a computed overlay, not a
  separate data source, and it is modeled, not confirmed on the ground.
- **Scorecard / weighting** - the configurable model that combines category scores into the unified score.
  Changing weights or thresholds re-scores every node on the tenant.
- **Third-party data (D&B, RapidRatings, EcoVadis)** - licensed feeds embedded in the score. Redistribution
  breaches the license, and the score inherits their refresh lag.
- **Monitored network / watchlist** - the surveillance scope. Removing a node removes its alerts.
- **Scenario Builder** - what-if simulation; a run changes nothing, publishing/pushing its output does.
- **ESG / forced-labor / sanctions flag** - UFLPA, forced/child labor, sanctioned-entity findings on a named
  supplier. Legally sensitive; wrong or leaked, it is defamatory or material non-public information.

## Operations: read / write / by data sensitivity and egress
Almost everything is a read - so gate by where the data goes and what a config change moves, not by "does it
write." No tool names; kinds of action.

| Class | Everstream operation families | Gate | Why |
|---|---|---|---|
| **Read (in-boundary)** | display a node's scores and category breakdown; view the sub-tier / n-tier graph and confidence; list incidents and alerts; view "my network"; run an exposure / impact-radius assessment; run a Scenario Builder what-if without saving; view a watchlist / monitored network; view the audit / adjudication trail | always pass in-boundary | no state change - but egress rules apply before any output to a user or another system (see below). Read the confidence, freshness, and scope before you rely on it |
| **Write (reversible, local scope)** | add / remove a node, material, or lane from your monitored network or watchlist; subscribe / unsubscribe an alert notification; snooze / mute an alert; annotate a node or alert; save a scenario as a draft | gate one at a time (elevate to human approve when the node has active alerts or sits in a high-risk category) | changes *your* coverage or view, not shared truth - but the write is reversible while its consequence is not: removing a node or muting an alert opens a monitoring blind spot, and a disruption missed during the gap costs lead time you cannot recover |
| **Write (committing, shared or cross-system)** | change scorecard weights or alert thresholds (re-scores the whole tenant); confirm or reject an inferred sub-tier edge (rewrites the shared network graph); adjudicate an alert as false-positive / resolved (attributable, suppresses future signal); publish or share a scenario; write a risk-register entry; **push a risk score or flag back into the ERP / procurement / planning system** (drives a committing write there) | gate + human approve | binds shared model, graph, or downstream action; the uncertainty in a score becomes a hard decision others act on |
| **Destructive / high-sensitivity** | **egress of sub-tier maps, named-supplier scores, forced-labor / sanctions / financial-distress findings, or licensed third-party data to an external tool, unapproved endpoint, supplier, or broad audience**; delete or overwrite a curated sub-tier network or its adjudication history; remove a supplier / site from monitoring entirely; drive an irreversible real-world action (de-source, cancel, force majeure) on a single unconfirmed read | HARD GATE + named owner + re-read | data that leaves cannot be recalled and can breach NDA, data license, or law; curated maps and history are not cheaply rebuilt; a wrong irreversible call off a probabilistic read is a real-world loss |

**The gate ladder (what each Gate cell means in practice):**
- **gate one at a time** (reversible local write) - a confirmation before acting, a captured reason (why this
  node is dropped, why this alert is muted), and an audit-log entry, per action and not batched. Removing
  monitoring or muting an alert opens a blind spot, so each is confirmed and logged on its own.
- **gate + human approve** (committing) - explicit human-in-the-loop sign-off before it binds the shared model,
  graph, or a downstream write; re-read the current state first, because scores and maps drift.
- **HARD GATE + named owner + re-read** (destructive / high-sensitivity) - a specific accountable person
  authorizes; block until they sign off; re-read the current state at execute; and log the payload class and
  the reason. For egress with no approved destination, the default is refuse and escalate, not proceed.

**Egress is its own axis (read this):** the read/write columns above describe state change; egress is
orthogonal. The *same* read that is safe in-platform becomes the most dangerous action in the platform the
moment its output crosses the trust boundary - and the trust boundary includes your own reply to a user who
lacks clearance. Before any export, forward, share, push, or rendering of sensitive detail in a response, treat
the payload as a controlled disclosure: what data class is it (sub-tier map? named-supplier risk? third-party
licensed? legally sensitive finding?), who is the audience, and is that destination approved (allowlist or data
owner; if unknown, default to block). Aggregate, portfolio-level, de-identified reads are lower sensitivity
than a named supplier's flag, though a risk distribution across your network (for example, "list every supplier
scoring above 80") still exposes network composition and is gated on egress. **Combining sources raises the class:** joining an Everstream score with Resilinc
financial-health or SAP supplier-master data creates a new data class whose sensitivity is the union of both -
gate the combined output as egress from both systems, not the lower of the two. The trust boundary is also
per-tenant: moving data between two Everstream tenants (for example, different business units) is egress, not
an internal move.

**Cross-system push can be destructive-by-proxy.** A flag pushed back into the ERP / procurement / planning
system is a committing write in Everstream, but in a target system configured for automation it can trigger an
automatic supplier block, a PO cancellation, or a re-source that is practically irreversible (for example, a
risk flag pushed to SAP MM that fires an automatic supplier block or cancels open POs - shipments already
diverted, POs already cancelled). Gate the push against the *target system's* automation, not just Everstream's
write class; if the target auto-acts, treat the push as destructive and apply the hard gate.

Universal rules to teach: read the confidence, the freshness, and the "my network" scope before you rely on a
score/alert; re-read at decision time because scores, maps, and incidents all drift; never silence monitoring
to reduce noise; never let a probabilistic read trigger an irreversible action without corroboration; route
compliance (sanctions, forced labor) to the compliance system and a human, not a data edit here; keep sensitive
intelligence inside the approved tenant and audience.

## Gotchas that bite (the real set - causal chains)
The safety-critical chains - check these before any irreversible or outbound action - are egress (#13, #14,
#15), acting on an unconfirmed read (#1, #3, #6, #19), and silencing the signal (#10, #11). The rest are
operational: they corrupt a decision but do not by themselves cause an irreversible loss.
1. **A risk score is a predictive estimate, not a measurement.** De-sourcing or blocking a supplier on the score alone can drop a healthy vendor; the score is a prior that says "investigate here," not a verdict.
2. **Higher score means more risk - confirm the direction.** Reading the scale backwards inverts every decision; check the direction and the category (financial vs ESG vs geopolitical) before acting, because a high financial score and a high climate score demand different responses.
3. **Sub-tier edges are inferred with a confidence level.** A low-confidence tier-3 link may be wrong; a re-source or a public "we have no exposure to X" statement built on an unconfirmed edge can be flatly false.
4. **The n-tier map mixes customer-provided, public, and data-science-derived data.** Some edges are curated, some are probabilistic guesses; not distinguishing them treats a guess as a contract. `references/n-tier-and-monitoring.md`.
5. **Absence of a sub-tier link is not proof of no exposure.** Discover maps what it can find; an unmapped tier-N supplier can still be your single point of failure. "Not shown" is not "not there."
6. **An alert is an early signal matched to your network, not a confirmed disruption.** Acting irreversibly - halting shipments, invoking force majeure - on an emerging, uncorroborated incident can be premature and self-inflicted.
7. **Exposure is modeled by geofence / radius.** A node just outside the drawn impact area can still be hit, and a node inside may be unaffected; the radius is an estimate, not ground truth.
8. **Scores and maps are only as fresh as their feeds.** A score built on a stale D&B / RapidRatings / EcoVadis pull can lag a real event by days; re-read at decision time rather than trusting a cached number. `references/risk-scores.md`.
9. **Changing scorecard weights or thresholds re-scores the whole tenant.** A tuning tweak silently moves every supplier's score and changes who trips an alert for everyone on the tenant; it is a committing config change, not a personal view setting.
10. **Removing a supplier / site / material from the monitored network stops all its alerts.** A silent blind spot - you learn it mattered only after the disruption you no longer see.
11. **Muting or snoozing an alert suppresses the signal, not the event.** The disruption still unfolds; a muted alert that was real becomes a missed disruption, and lead time is the thing you cannot get back.
12. **Marking an alert false-positive / not-relevant is an attributable decision.** If it was real, the record shows you saw it and dismissed it; adjudicate with evidence, not to clear the queue.
13. **Third-party scores (D&B, RapidRatings, EcoVadis) are licensed feeds.** Exporting or forwarding them outside the approved tenant and users breaches the data license; the number is embedded intelligence, not yours to redistribute.
14. **Sub-tier maps are competitively sensitive and often NDA-bound.** Egressing "who supplies whom" to an external tool, a competitor-adjacent audience, or the supplier itself can breach NDA, expose a customer's sourcing, and cannot be recalled once sent.
15. **A forced-labor / sanctions / financial-distress flag on a named supplier is legally sensitive.** Leaking or misstating it can be defamatory, damage the relationship, or be material non-public information; this is the highest-sensitivity data class in the platform.
16. **Confirming or rejecting an inferred sub-tier edge rewrites the shared graph.** Everyone downstream reasons on the curated map; a wrong confirmation propagates a false relationship, and a wrong rejection hides a real one, across every future exposure analysis.
17. **The "my network" filter can hide incidents that still matter.** A disruption on an unmapped upstream node or a shared logistics hub will not appear as your alert; scope the filter deliberately and do not read silence as safety.
18. **Scenario Builder is a simulation until saved or published.** Running a what-if changes nothing, but publishing a scenario or pushing its output into a plan is a committing action others will act on.
19. **Pushing an Everstream flag back into the ERP / procurement system commits in that system.** The score's uncertainty gets hard-coded into a sourcing block or a stopped PO; gate that write under the target system's rules, and base it on corroborated risk, not a raw score.
20. **Alerts arrive with recommended actions - treat them as guidance, not instructions.** Executing a generic "re-route / pre-buy / halt" verbatim without validating it against your own network and inventory can overreact to an event that barely touches you.
21. **A closed incident can re-open or escalate.** Marking your exposure "handled" on an early read and standing down monitoring can miss the second wave (an aftershock, a secondary port closure, a sanctions expansion).
22. **Correlated risk: one event hits many nodes at once.** Reading a single supplier's alert misses that one port or region event exposes your whole category; read the event's full impact set, not one node's flag.
23. **Sanctions / denied-party signals here are intelligence, not the compliance record.** A hit flags investigation; the legal screening, adjudication, and block belong in the trade/compliance system, never a data edit in Everstream.
24. **Deleting or overwriting a curated sub-tier network or adjudication history loses real work.** The map took data science plus human curation to build and is not cheaply reconstructed; treat map and history deletion as destructive.

(More per-topic detail: `references/risk-scores.md`, `references/n-tier-and-monitoring.md`.)

## Edge states & special cases
Each breaks naive "the score is high / the map is clean, so act" logic - key rule inline, full behavior in references.
- **Inferred vs confirmed edges** - the graph carries both; a confidence level separates a lead from a fact. Reason on confidence, not just the line's existence. `references/n-tier-and-monitoring.md`.
- **Unmapped upstream** - absence of a link is not absence of exposure; a tier-N single-source can be invisible. When you hit an unmapped node or a known gap, flag it to a human and propose a Discover re-run; do not record the gap as "no exposure."
- **Correlated / aggregated exposure** - one event exposes many nodes; per-node scoring misses concentration risk in a region, port, or commodity.
- **Emerging vs confirmed vs re-opened incident** - an emerging incident is low-corroboration; a closed one can escalate. Re-read status at execute, not just at first alert.
- **Geofence boundary cases** - just-inside / just-outside a radius are both uncertain; widen the read before concluding "no exposure."
- **Stale third-party feed** - a financial or ESG score can lag the real event; the score's freshness is the feed's freshness. `references/risk-scores.md`.
- **Degraded / error / timeout** - if Everstream errors, times out, or serves data past its refresh cycle, fail safe: do not act on a cached score, fall back to the ERP supplier master for tier-1 facts, and treat missing monitoring or a blank alert feed as unknown, not an all-clear.
- **Tier-1 reconciliation** - Everstream's tier-1 should reconcile to the ERP supplier master (the record of who you actually buy from); its tier-N is inference beyond it. Where they disagree at tier-1, the ERP is the record.

## Reconciliation / freshness
A score, an alert, and a map are all snapshots. Re-read at decision time: scores refresh as feeds land,
incidents update and re-open, and the sub-tier map is re-curated as new data arrives. When Everstream and the
ERP disagree at tier-1, trust the ERP supplier master for who you buy from; Everstream's value is the risk
overlay and everything below tier-1. Treat a cached score older than its feed's refresh cycle as stale.

## Recovery patterns (can it be undone, and what can't)
- **Egress cannot be undone.** Data that crossed the trust boundary cannot be recalled; a wrong disclosure of a sub-tier map or a supplier flag is a reportable event, not a fixable edit. This is the irreversible action in the platform - gate it hardest. If egress happens in error: notify the data owner and compliance immediately, document what was disclosed and to whom, and do not try to "fix" it by deleting data in the target system - that is a separate write with its own gate.
- **Removing a node from monitoring** is reversible by re-adding, but the alerts that fired during the blind window are gone, and re-discovery of its sub-tier map may need to re-run. The coverage gap does not backfill.
- **Muting an alert** is reversible, but a real disruption missed during the mute costs lead time you cannot recover.
- **A scorecard weight / threshold change** is reversible by reverting, but any decision made on the changed scores in between still stands.
- **Adjudication / risk-register entries** are corrected by a new entry (the trail keeps both), not a silent undo; the original is preserved intact and never overwritten in place, so the original decision remains attributable.
- **A deleted curated sub-tier network or scenario** may not be reconstructable - treat it as destructive, not housekeeping.

## Guardrails
- If your action logic reduces to "score is high, so act" or "map is clean, so no exposure," stop and re-read the edge states: a probabilistic score and a partly-inferred map do not support an irreversible move on their own.
- Read the confidence, the freshness, the category, and the "my network" scope before you rely on any score or alert; re-read at decision time because scores, maps, and incidents drift.
- Egress is the high-risk act: before any export, forward, share, or push, classify the payload (sub-tier map / named-supplier risk / third-party licensed / legally sensitive finding), confirm the audience, and confirm the destination is approved. Prefer aggregate, de-identified reads over named-supplier exports.
- Never de-source, cancel, halt, or invoke force majeure on a single unconfirmed read; corroborate a low-confidence inference, an emerging alert, or a raw score first.
- Do not change tenant-wide scorecard weights or alert thresholds casually - they re-score everyone.
- Do not remove monitoring or mute alerts to quiet noise; a blind spot is a missed disruption.
- Route sanctions and forced-labor findings to the compliance/trade system and a named officer; do not adjudicate them by editing a record here.
- When intelligence here would drive a committing write in the ERP / procurement / planning system, gate that write under the target system's rules and base it on corroborated risk.

## References (load on demand)
- `references/risk-scores.md` - load when reading, comparing, or configuring risk scores: the category taxonomy (financial, operational, ESG/ethical, geopolitical, environmental/climate, compliance), score direction and composition, predictive/climate projection, the licensed third-party feeds and their licensing and freshness, scorecard weighting.
- `references/n-tier-and-monitoring.md` - load when working with the sub-tier map or the alert feed: inference vs curation and confidence, data sources, absence-is-not-safety, incidents vs alerts, geofence/exposure, the monitored network / watchlist, the Scenario Builder, and adjudication.
