---
name: interos
description: "Interos - the safe operation of continuous supply-chain risk and resilience intelligence built on an AI-modeled interconnected relationship graph. Because it is mostly a read/intelligence system, actions are classified by data sensitivity and egress, not money or stock. Use when the connected risk system is Interos and the work touches the i-Score or a factor score (financial, operational, restrictions/governance, geopolitical, ESG, cyber), a multi-tier / n-tier / sub-tier supplier relationship graph, continuous monitoring or a risk event/alert, concentration or single-source or shared-node exposure, risk propagation / cascading through the graph, an entity-resolution question, a watchlist or portfolio, a scorecard weighting, or a restricted-party / sanctions / forced-labor flag; or the user mentions Interos, the Interos Resilience Cloud, i-Score, the supply-chain knowledge graph, concentration risk, or pushing an Interos risk flag back into the ERP or procurement system."
---

# Interos - operating it safely

Interos is a supply-chain risk and resilience intelligence layer, not a system of record. Its distinctive
asset is a single, continuously-modeled **interconnected relationship graph**: an AI-built map of companies,
sites, and their multi-tier (n-tier) supply relationships at massive scale, scored by the **i-Score** across
risk factors and watched by **continuous monitoring** that fires events and alerts against your entities.
Almost every operation is a read - and that is what makes it different from the ERP/WMS/trade systems in this
plugin. **The danger is not posting money or stock; it is what the intelligence is and where it goes.** The
reads are safe. The hazards are four: (1) sensitive supplier, sub-tier-graph, and concentration data leaving
the trust boundary (egress); (2) treating an **AI-modeled** edge, a propagated risk, or a probabilistic score
as confirmed fact; (3) tenant-wide config that silently re-scores or re-alerts, or an entity-resolution error
that attaches the wrong risk to the wrong company; and (4) committing an irreversible action - usually in
another system - off a modeled score or an early alert. Classify by **data sensitivity and egress**, not by
stock or dollars.

## Contents
- Read this first
- When this applies
- The surface
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
- **Egress is the high-risk act here.** The sub-tier graph ("who supplies whom"), concentration and
  single-source / shared-node maps (which reveal your hidden points of failure), named-entity i-Scores and
  factor scores, restricted-party / sanctions / forced-labor findings, and the licensed third-party data behind
  the score are the most sensitive assets in the platform. Sending any of it to an external tool, an unapproved
  endpoint, a supplier, or a broad audience is a controlled disclosure, not a data pass-through. Once it leaves
  you cannot recall it. Keep intelligence inside the approved tenant and audience.
- **Your own reply is an egress channel.** Summarizing, quoting, or paraphrasing a sensitive read back to a
  user who lacks clearance is egress even though the read itself was "always pass." Before rendering a
  named-entity score, a sub-tier edge, a concentration finding, or a legally sensitive flag in a response,
  confirm the audience and role, and prefer an aggregate / de-identified summary over named-entity detail.
- **The graph is AI-modeled, not attested.** Interos derives most relationships from public, licensed, and
  model-inferred data, not from suppliers self-reporting (that is `resilinc`). Each edge and each
  resolved entity carries model uncertainty; a link may be inferred, and an entity may be mis-resolved (the
  wrong company matched to a name). Read the confidence and the entity match before you rely on it.
- **A score / edge / propagated risk / alert is a prior, not a verdict.** An i-Score is a modeled estimate, a
  sub-tier edge is inferred with a confidence, a cascading risk is propagated through modeled links, and an
  alert is an early correlated signal. None is confirmed fact. Do not de-source a supplier, invoke force
  majeure, halt shipments, or push a hard block on a single unconfirmed read. Corroborate and re-read first.
- **Confirm score direction before any action.** The i-Score is a *resilience* score (higher tends to mean more
  resilient / lower risk), but a factor or embedded third-party sub-score can run as *risk* (higher = worse).
  Reading one on the other's scale inverts the decision - check the scale and the factor first (gotcha #2).
- **The irreversible action lives in the other system.** Interos informs; the ERP, procurement, planning, or
  trade system acts. When intelligence here would drive a committing write there (block a supplier for sourcing,
  cancel a PO, re-plan), gate that write in the target system under its own rules - and base it on corroborated
  risk, not a raw number.
- **Do not silence the signal to quiet the queue.** Dropping an entity from a watchlist/portfolio, or muting an
  alert, creates a blind spot; a real disruption that fires during the gap is a missed disruption with lead time
  already lost.
- **Compliance decisions are not data edits here.** A restrictions-factor sanctions or forced-labor hit is risk
  intelligence that routes to the compliance/trade system and a human officer; it is not adjudicated by editing
  a record in Interos.

## When this applies
Connector is Interos and the work is i-Score risk scoring, n-tier graph mapping, concentration / single-source
exposure, continuous monitoring, or risk propagation. When NOT:
- supplier-**attested** resiliency data, BCP / TTR / TTS, Resiliency Score, data-collection campaigns -> `resilinc`
- Everstream's Discover / Explore / Reveal products, unified risk score, weather/event exposure framed on that platform -> `everstream`
- denied-party / sanctions **screening and adjudication** with block-and-release as the compliance system of record -> `sap-gts` (Interos *flags* restricted-party risk; GTS *adjudicates and blocks* it)
- the ERP supplier master, PO, and inventory the scores sit on top of -> `sap-mm` / `oracle-erp`
- real-time multimodal shipment ETA tracking as the system of record -> `project44` / `fourkites`

**What makes Interos its own skill (vs the two risk siblings):** Everstream and Resilinc are also read/egress
risk systems, but Interos' unit of value is the **one continuous graph** - risk propagates *through* modeled
relationships, and its signature analytic is **concentration / shared-node exposure** (finding the single
upstream node many of your suppliers secretly share). Resilinc's edges are supplier-attested; Everstream ships
three separate products; Interos is graph-first, model-derived, and continuously monitored by default.

**The action boundary:** Interos *informs; it does not act.* It does not adjudicate compliance, execute a
procurement action, confirm a real supplier relationship as contract, or move inventory. Every operational
consequence happens in another system under that system's gates - never treat an Interos read as authority to act there.

## The surface (know where you are)
- **The relationship graph** - one AI-modeled, continuously-updated map of entities (companies, sites) and
  their n-tier supply relationships at large scale. Edges are derived from public / licensed / inferred data and
  carry a confidence; entities are machine-resolved. Mechanics in `references/graph-and-monitoring.md`.
- **The i-Score** - a multi-factor resilience/risk score per entity, composed from factor scores across roughly
  six families (financial, operational, restrictions & governance, geopolitical, ESG, cyber; the exact factor
  set varies by entitlement and release). Predictive, drawing on licensed third-party feeds plus Interos'
  modeling. Deep taxonomy in `references/i-score-and-factors.md`.
- **Concentration / single-source exposure** - graph analytics that surface hidden single points of failure: a
  supplier concentrated in one geography, a single-source part, or a shared upstream node that many of your
  tier-1s route through. This is Interos' signature read; it is modeled from the graph, so it is only as good as
  the graph. Details in `references/graph-and-monitoring.md`.
- **Continuous monitoring (events and alerts)** - 24/7 detection of real-world events (financial distress, cyber
  breach, natural hazard, geopolitical, a new sanctions listing) correlated to entities in your graph, with risk
  **propagation** so a hit deep in the graph surfaces as exposure at your tier-1. Because monitoring is graph-wide
  and continuous, your config surface is the watchlist/portfolio (what you actively track) and alert subscriptions.

## Object & state model (reason about state, not nouns)
- **Entity (company / site)** - a machine-resolved node in the graph. Carries i-Score and factor scores, location,
  tier. **Resolution state:** confidently-matched or ambiguous/mis-resolved (a name collision can attach another
  firm's risk). Watch state: in a **watchlist/portfolio** (actively tracked/alerted) or not.
- **Relationship (edge)** - a supply link at tier-N. Source: public / licensed / model-inferred. States:
  **inferred (with a confidence) -> confirmed** or **rejected** by your feedback. Direction and commodity matter.
- **i-Score / factor score** - per entity, per factor. A moving snapshot, refreshed as underlying data and feeds
  land; predictive, not a fixed attribute. Confirm its direction before acting (see Vocabulary).
- **Concentration / exposure finding** - a computed overlay on the graph (geographic concentration, single-source,
  shared-node). It is modeled, not confirmed on the ground; a missing edge hides a real concentration.
- **Event / incident** - a real-world happening Interos detects, with a factor category, a severity, and a time.
  States: **emerging -> updated -> closed**, and a closed one can re-open or escalate.
- **Alert** - an event (or a score/factor change) correlated to your graph, optionally **propagated** from an
  upstream node. States: **new -> acknowledged -> adjudicated** (relevant / not-relevant / resolved) **-> closed**.
  Adjudication is an attributable, logged decision.
- **Watchlist / portfolio** - the configured set of entities you actively track and alert on within the graph.
- **Relationship-feedback / curation** - confirming or rejecting an inferred edge, correcting an entity match.
  Attributable and shared: it rewrites the graph everyone downstream reasons on.
- **Risk-register / mitigation entry** - a logged risk plus owner and action; attributable, part of the audit trail.

## Vocabulary that bites
- **i-Score** - Interos' composed, predictive resilience/risk score, not a measurement. Interos brands it a
  **resilience** score (higher tends to mean more resilient, the opposite of a raw risk number), but a factor or
  third-party sub-score can be presented as risk (higher = worse). Confirm the direction and the factor before
  acting - reading the scale backwards inverts the decision (gotcha #2).
- **Risk factor** - one dimension of the i-Score (financial, operational, restrictions & governance, geopolitical,
  ESG, cyber). A rolled-up i-Score hides which factor is driving it; open the factor breakdown before you decide,
  because a financial hit and a cyber hit demand different responses.
- **Interconnected / relationship graph** - the AI-modeled n-tier map. Most tier-2+ edges are *inferred*, not
  contractual; "tier-N" is depth, not certainty.
- **Confidence** - how sure an inferred edge or an entity resolution is. A low-confidence tier-4 link, or a shaky
  entity match, is the difference between a lead and a fact.
- **Entity resolution** - the machine matching of a real-world company to a graph node. A mis-resolution attaches
  the wrong firm's score, sanctions status, or events to your supplier - a uniquely graph-scale failure here.
- **Risk propagation / cascading** - Interos pushes a node's risk *through* the graph, so a disruption at a
  tier-4 supplier can surface as your tier-1 exposure. Propagated risk is modeled over inferred links; its
  certainty is the weakest edge in the path.
- **Concentration / single-source / shared-node exposure** - the signature analytic: a hidden single point of
  failure where many of your suppliers depend on one geography, one part source, or one shared upstream node.
  Modeled from the graph; a missing edge silently understates it.
- **Continuous monitoring** - Interos watches the graph 24/7 by default; your watchlist/portfolio decides what
  you actively see and get alerted on, not whether the world is watched.
- **Event vs alert** - an *event* is a real-world happening; an *alert* is that event (or a score change) matched
  and possibly propagated to your graph. An alert is an early warning, not a confirmed impact on you.
- **Scorecard / model weighting** - the configurable model that combines factor scores into the i-Score and sets
  alert thresholds. Changing it re-scores and re-alerts every entity on the tenant.
- **Restrictions factor** - sanctions, denied/restricted parties, export controls, forced labor / UFLPA,
  debarment, adverse regulatory status. It **flags** for investigation; it is not a screening ruling (route to
  `sap-gts`). Legally sensitive; wrong or leaked, it is defamatory or material non-public information.
- **Third-party feeds** - licensed external data (financial, cyber-ratings, sanctions/watchlist, ESG, adverse
  media) embedded in the score. Redistribution breaches the license, and the score inherits their refresh lag.

## Operations: read / write / by data sensitivity and egress
Almost everything is a read - so gate by where the data goes, what a config change moves, and what a graph edit
rewrites, not by "does it write." No tool names; kinds of action.

| Class | Interos operation families | Gate | Why |
|---|---|---|---|
| **Read (in-boundary)** | display an entity's i-Score and factor breakdown; traverse the n-tier graph and confidence; run a concentration / single-source / shared-node analysis; view propagated risk paths; list events and alerts; view your watchlist/portfolio; view the audit / adjudication trail | **Conditional pass** - confirm role/clearance for sensitive payloads; egress rules apply before any output *(NOT unconditional; a **bulk** read is not a simple Read - see the note under this table)* | no state change - but egress rules apply before any output to a user or another system (below). Read the confidence, entity match, freshness, and factor direction before you rely on it |
| **Write (reversible, local scope)** | *additive:* add an entity to a watchlist/portfolio; subscribe / annotate an alert; save a draft view. *coverage-reducing:* remove an entity from a watchlist/portfolio; snooze / mute an alert | *additive:* gate one at a time. *coverage-reducing (mute / snooze / remove): elevate to human approve* | additive changes your view, low blast. But a coverage-reducing write is reversible while its consequence is not: muting an alert or dropping a monitored entity opens a blind spot, and a disruption missed during the gap costs lead time you cannot backfill |
| **Write (committing - shared or cross-system)** | change scorecard weights or alert thresholds (re-scores / re-alerts the whole tenant); confirm or reject an inferred edge, or correct an entity resolution (rewrites the shared graph); adjudicate an alert as not-relevant / resolved (attributable *and* signal-suppressing - see note); write a risk-register entry; **push an i-Score / factor / flag back into the ERP / procurement / planning system** (drives a committing write there) | gate + human approve | binds the shared graph or model, or hard-codes a modeled score into a downstream action others act on |
| **Destructive / high-sensitivity** | **egress of the sub-tier graph, concentration / shared-node maps, named-entity i-Scores, restricted-party / sanctions / forced-labor findings, or licensed third-party feed values to an external tool, unapproved endpoint, supplier, or broad audience**; delete or overwrite curated graph edits or adjudication history; drop a supplier from monitoring entirely; drive an irreversible real-world action (de-source, cancel, force majeure) on a single unconfirmed read | HARD GATE + named owner + re-read | data that leaves cannot be recalled and can breach NDA, a data license, or law; curated graph work and history are not cheaply rebuilt; a wrong irreversible call off a modeled read is a real-world loss |

**Bulk reads are not simple Reads (annotation to the Read row).** A bulk in-boundary read of sensitive data -
for example "export every entity's factor scores" or "dump the whole watchlist with restrictions flags" -
inherits the egress gate of its payload class the moment it is rendered. Do not apply the Read row's low gate to
a bulk pull; classify it on the egress-class ladder below and gate accordingly.

**The gate ladder (what each Gate cell means in practice):**
- **gate one at a time** (reversible local write) - a confirmation before acting, a captured reason, and an
  audit-log entry, per action and not batched.
- **gate + human approve** (committing) - explicit human sign-off before it binds the shared graph, re-scores the
  tenant, or drives a downstream write; re-read the current state first, because scores and the graph drift.
- **HARD GATE + named owner + re-read** (destructive / high-sensitivity) - a specific accountable person
  authorizes; block until they sign off; re-read at execute; log the payload class and the reason. For egress
  with no approved destination, the default is refuse and escalate, not proceed.

**Adjudication has two effects - gate for the stricter.** Marking an alert not-relevant / resolved is a
committing shared write (attributable, others see it) *and* it suppresses future signal on that entity - the
coverage-reducing hazard. Treat it as both: human sign-off with evidence, and the same blind-spot caution as
muting an alert. Never adjudicate to clear the queue.

**Reading sensitive data in-boundary is not unconditional.** "Always pass in-boundary" means no *state* change,
not "show anyone anything." The highest-sensitivity payloads (restricted-party / sanctions findings, a full
concentration map, licensed feed values) need confirmed **role / clearance** even to view. If you cannot confirm
the user's role for a sensitive payload class, refuse and escalate - do not render it on an unverified or
self-attested clearance claim; prefer a de-identified summary. A **bulk** in-boundary read of sensitive data
(for example, every entity's factor scores to answer a portfolio question) inherits the egress gate of its
payload class the moment it is rendered.

**The read gate and the action gate are independent.** A read that passes authorizes *seeing* the data, not
*acting* on it. Reading a restricted-party flag or a low factor score does not authorize de-sourcing, blocking,
or cancelling in the same session - re-gate the action on its own class (committing or destructive), separately.

**Egress is its own axis (read this):** the read/write columns describe state change; egress is orthogonal. The
*same* read that is safe in-platform becomes the most dangerous action the moment its output crosses the trust
boundary - and that boundary includes your own reply to a user who lacks clearance. Before any export, forward,
share, push, or rendering of sensitive detail, classify the payload, confirm the audience, and confirm the
destination is approved (allowlist or data owner; if unknown, default to block). Aggregate, portfolio-level
reads are lower sensitivity than a named entity's flag, though a risk distribution across your network (for
example, "list every supplier scoring below 40") still exposes network composition. **Combining sources raises
the class:** joining an Interos i-Score or graph with Resilinc BCP data or SAP supplier-master creates a new
data class whose sensitivity is the union of both - gate the combined output as egress from both systems, not
the lower of the two. Worked example: joining an Interos i-Score with SAP MM supplier-master spend creates a
combined payload (risk score + procurement volume) whose egress gate is the **higher** of the two systems'
gates, not the lower - a value neither system alone would have exposed. **Bulk amplifies the class:** exporting a
whole sub-tier graph or a full concentration map at once is the top egress class - gate it hardest. The boundary
is also per-tenant: moving data between two Interos tenants (different business units) is egress, not an internal move.

**Egress-class ladder (apply to the payload *regardless* of the row above - a "read" that leaves becomes this):**

| Payload class | Sensitivity | Egress gate |
|---|---|---|
| Aggregate / de-identified (counts, portfolio distribution) | low | confirm audience (approved-destination check not required for aggregate-only); portfolio composition can still leak |
| Named-entity i-Score / factor / single edge | medium | confirm audience + approved destination |
| Sub-tier graph slice, concentration / shared-node map, restricted-party / sanctions / ESG finding | high | named owner + approved destination; default block if unknown |
| Full-graph export, complete concentration map, licensed third-party feed value, or any **bulk** export of the above | highest | HARD GATE + named owner; egress cannot be recalled |

Worked example: a user asks to email the shared-node concentration map for a product line to an outside
consultant -> payload = concentration map -> high (and outbound to an external party) -> named owner + approved
destination, default block if the destination is not on the allowlist. The same user asks for the count of
suppliers by risk-factor band -> payload = aggregate -> low -> confirm audience and proceed.

**Cross-system push can be destructive-by-proxy.** A flag pushed into the ERP / procurement / planning system is
a committing write in Interos, but in a target system configured for automation it can trigger an automatic
supplier block, a PO cancellation, or a re-source that is practically irreversible (for example, an Interos
restrictions flag pushed to SAP MM that fires an automatic vendor block or cancels open POs - shipments already
diverted, POs already cancelled). Before pushing, **check the target system's automation state**: does a received
flag/score auto-trigger a block/cancel/re-source, or land as a passive attribute a human later acts on? Gate the
push against the *target system's* automation, not just Interos' write class; if the target auto-acts, treat the
push as destructive and apply the hard gate. **If you cannot confirm the target's automation posture, default to
treating the push as destructive-by-proxy and hard-gate it** - assume it may auto-act until proven otherwise.

Worked example (destructive-by-proxy): a user wants to push a high Interos restrictions-factor flag on a
supplier into SAP MM to "get it on the record." Analysis: the payload is a restrictions flag (legally sensitive,
and it is only a *flag*, not an adjudication); the target is SAP MM, whose vendor block can be automation-driven.
Check the target's posture - if a received flag auto-sets a payment/posting block or cancels open POs, the push
is destructive-by-proxy (shipments diverted, POs cancelled, hard to unwind). So: do not push the raw flag;
corroborate the restriction, route the compliance question to the trade/compliance system and a human officer
(`sap-gts`), and if a block is warranted, gate it in SAP MM under its own destructive-row rules with a
named approver - not as a silent Interos-to-ERP push.

The **pull direction is destructive-by-proxy too.** An external system set up to auto-pull Interos data on a
schedule (for example, a procurement platform that ingests i-Scores nightly and auto-blocks any vendor below a
threshold) turns your data provision into an automatic action you no longer see. If you cannot confirm the
consumer's automation posture, treat the standing data feed as destructive-by-proxy and gate it the same way -
the hazard is the auto-action on the other side, whichever direction the data moves.

Universal rules to teach: read the confidence, the entity match, the freshness, the factor direction, and the
watchlist scope before you rely on a score/edge/alert; re-read at decision time because scores, the graph, and
events all drift; never silence monitoring to reduce noise; never let a modeled read trigger an irreversible
action without corroboration; route restrictions / sanctions findings to the compliance system and a human, not
a data edit here; keep sensitive intelligence inside the approved tenant and audience.

## Gotchas that bite (the real set - causal chains)
The safety-critical chains - check these before any irreversible or outbound action - are egress (#13, #14,
#15, #16), acting on a modeled read (#1, #3, #4, #7, #21), entity-resolution error (#5), and silencing the
signal (#11, #12). The rest corrupt a decision but do not by themselves cause an irreversible loss.
1. **An i-Score is a modeled estimate, not a measurement.** De-sourcing or blocking a supplier on the score alone can drop a healthy vendor; the score is a prior that says "investigate here," not a verdict.
2. **Confirm the score direction and the factor.** Interos brands the i-Score as resilience (higher = more resilient), but a factor or third-party sub-score can run as risk (higher = worse); reading one on the other's scale inverts every decision. `references/i-score-and-factors.md`.
3. **Most graph edges are inferred, not contractual.** A low-confidence tier-3/4 link may be wrong; a re-source or a public "we have no exposure to X" statement built on an unconfirmed edge can be flatly false.
4. **Propagated / cascading risk is only as strong as the weakest edge in the path.** A tier-4 hit shown as your tier-1 exposure rides on a chain of inferred links; treat a propagated alert as a lead to trace, not a confirmed impact.
5. **Entity resolution can attach the wrong firm's risk.** A name collision or a bad match binds another company's sanctions status, financial distress, or events to your supplier; verify the entity match before you act on its score - this is the graph-scale failure unique to Interos.
6. **A rolled-up i-Score hides the driving factor.** A 60 driven by cyber and a 60 driven by financial distress need different responses; open the factor breakdown before deciding.
7. **Concentration is modeled from the graph, so a missing edge understates it.** A "no single point of failure" read can be false because the shared upstream node was never mapped; absence of a concentration finding is not proof of no concentration.
8. **Absence of a sub-tier link is not proof of no exposure.** The graph maps what it can model; an unmapped tier-N single-source can still be your point of failure. "Not shown" is not "not there."
9. **If you treat a model-inferred edge like a curated one, you reason on a guess as if it were a contract.** The graph mixes public, licensed, and inferred data; read each edge's source and confidence, not just the drawn line, before you act on it. `references/graph-and-monitoring.md`.
10. **Scores and the graph are only as fresh as their feeds.** A score built on a stale financial or sanctions feed can lag a real event by days; re-read at decision time rather than trusting a cached number. `references/i-score-and-factors.md`.
11. **Dropping an entity from a watchlist/portfolio stops its active alerts.** A silent blind spot - you learn it mattered only after the disruption you no longer see. (The graph still monitors it globally, but you are no longer told.)
12. **Muting or snoozing an alert suppresses the signal, not the event.** A muted alert that was real becomes a missed disruption, and lead time is the thing you cannot get back.
13. **The sub-tier graph and concentration maps are competitively sensitive and often NDA-bound.** Egressing "who supplies whom" or "your hidden single points of failure" to an external tool or the supplier itself can breach NDA, expose a customer's sourcing, and cannot be recalled once sent.
14. **Restricted-party / sanctions / forced-labor flags on a named entity are legally sensitive.** Leaking or misstating one can be defamatory, damage the relationship, or be material non-public information; this is the highest-sensitivity data class in the platform.
15. **Third-party feed values are licensed.** Exporting a financial, cyber-rating, ESG, or adverse-media value (or a score visibly derived from it) outside the approved tenant breaches the data license; it is embedded intelligence, not yours to redistribute.
16. **Bulk egress amplifies the class.** A whole-graph or full-concentration-map export is a larger disclosure than one lookup; treat a bulk read that leaves as the top egress class regardless of how each item alone would rate.
17. **Confirming or rejecting an inferred edge, or correcting an entity match, rewrites the shared graph.** Everyone downstream reasons on the curated graph; a wrong confirmation propagates a false relationship, a wrong rejection hides a real one, and a wrong merge/split of an entity mis-attributes risk across every future analysis.
18. **Changing scorecard weights or alert thresholds re-scores and re-alerts the whole tenant.** A tuning tweak silently moves every entity's i-Score and changes who trips an alert for everyone; it is a committing config change, not a personal view.
19. **Alerts arrive with severity and suggested context - treat them as guidance, not instructions.** Executing a generic "re-route / halt" verbatim without validating it against your own inventory and network can overreact to an event that barely touches you.
20. **A closed event can re-open or escalate.** Standing down on an early "handled" read can miss the second wave (an aftershock, a secondary closure, a sanctions expansion).
21. **Correlated risk: one event hits many nodes at once, and failover can concentrate it further.** Reading a single entity's alert misses that one region or shared-node event exposes your whole category - and failing over to "alternate" suppliers that share the same upstream node concentrates you into the very failure you were fleeing. Read the full impact set and the shared-node map, not one flag.
22. **Restrictions signals here are intelligence, not the compliance record.** A restricted-party hit flags investigation; the legal screening, adjudication, and block belong in the trade/compliance system, never a data edit in Interos.
23. **Pushing an Interos flag back into the ERP / procurement system commits in that system.** The score's uncertainty gets hard-coded into a sourcing block or a stopped PO; gate that write under the target system's rules, and base it on corroborated risk, not a raw score.
24. **When Interos disagrees with Resilinc or Everstream on the same supplier, the divergence is itself a signal.** Do not silently pick the worse (or better) number; surface both with their source and freshness and let a human weigh it - one is model-inferred, another may be supplier-attested.

(More per-topic detail: `references/i-score-and-factors.md`, `references/graph-and-monitoring.md`.)

## Edge states & special cases
Each breaks naive "the score is high / the graph is clean, so act" logic - key rule inline, full behavior in references.
- **Inferred vs confirmed edges** - the graph carries both; a confidence separates a lead from a fact. Reason on confidence and source, not just the line's existence. `references/graph-and-monitoring.md`.
- **Entity-resolution ambiguity** - an ambiguous or mis-matched entity attaches the wrong risk; when the match is uncertain, verify identity before acting and propose a correction rather than trusting the attached score.
- **Shared-node / concentration exposure** - one upstream node many suppliers share is a hidden single point of failure; per-supplier reading misses it, and failover can worsen it. Read the shared-node map. `references/graph-and-monitoring.md`.
- **Unmapped upstream** - absence of a link is not absence of exposure; a tier-N single-source can be invisible. Flag the gap to a human and propose deeper graph discovery; do not record the gap as "no exposure."
- **Propagated risk path** - a cascading alert is a chain of inferred edges; its certainty is the weakest link. Trace the path before acting on the endpoint.
- **Emerging vs confirmed vs re-opened event** - an emerging event is low-corroboration; a closed one can escalate. Re-read status at execute, not just at first alert.
- **Stale feed** - a financial, cyber, or sanctions score can lag the real event; the score's freshness is the feed's freshness. `references/i-score-and-factors.md`.
- **Degraded / error / timeout / empty result** - if Interos errors, times out, or serves data past its refresh cycle, fail safe: report the error and that the data may be stale or partial; refuse to score, rank, or drive an irreversible action on the degraded read; fall back to the ERP supplier master for tier-1 facts only; treat a blank alert feed as **unknown**, not an all-clear. A query that returns **no results is not an all-clear** either: zero concentration findings or an empty sub-tier result may mean the graph is unmapped at that depth, not that the risk is absent - treat it as unknown, not zero. Degraded data lowers confidence, it does not raise autonomy.
- **Tier-1 reconciliation** - Interos' tier-1 should reconcile to the ERP supplier master (who you actually buy from); its tier-N graph is inference beyond it. Where they disagree at tier-1, the ERP is the record.

## Reconciliation / freshness
An i-Score, an alert, and the graph are all snapshots. Re-read at decision time: scores refresh as feeds land,
events update and re-open, and the graph is continuously re-modeled as new data arrives. When Interos and the
ERP disagree at tier-1, trust the ERP supplier master for who you buy from; Interos' value is the risk overlay,
the n-tier graph, and the concentration analytics below tier-1. When Interos and another risk system (Resilinc,
Everstream) disagree on the same supplier, surface the conflict with each system's source (model-inferred vs
supplier-attested) and freshness and let a human weigh it - do not auto-resolve. Treat a cached score older than
its feed's refresh cycle as stale.

## Recovery patterns (can it be undone, and what can't)
- **Egress cannot be undone.** Data that crossed the trust boundary - a sub-tier graph slice, a concentration
  map, a licensed feed value, a restricted-party flag - cannot be recalled; a wrong disclosure is a reportable
  event, not a fixable edit. This is the irreversible action in the platform - gate it hardest. If it happens in
  error: notify the data owner and the compliance / data-privacy officer immediately; document what was
  disclosed, to whom, and which data classes; revoke the destination's access if possible; and do not try to
  "fix" it by deleting data in the target system - that is a separate write with its own gate.
- **Dropping an entity from a watchlist/portfolio** is reversible by re-adding, but the alerts that would have
  fired during the blind window are gone. The coverage gap does not backfill.
- **Muting an alert** is reversible, but a real disruption missed during the mute costs lead time you cannot recover.
- **A scorecard weight / threshold change** is reversible by reverting, but any decision made on the changed
  scores in between still stands.
- **A graph edit (edge confirm/reject, entity merge/split)** is corrected by a new edit, and a wrong one has
  already propagated through every analysis run against it in between; treat curation as committing, not casual.
- **Adjudication / risk-register entries** are corrected by a new entry (the trail keeps both), not a silent
  undo; the original decision remains attributable.

## Guardrails
- If your action logic reduces to "score is high, so act" or "graph is clean, so no exposure," stop and re-read
  the edge states: a modeled score and a partly-inferred graph do not support an irreversible move on their own.
- Read the confidence, the entity match, the freshness, the factor, and the direction before you rely on any
  score or alert; re-read at decision time because scores, the graph, and events drift.
- Egress is the high-risk act: before any export, forward, share, or push, classify the payload (sub-tier graph /
  concentration map / named-entity score / restricted-party finding / licensed feed value), confirm the
  audience, and confirm the destination is approved. Prefer aggregate, de-identified reads over named detail.
- Verify entity resolution before acting on an attached score - a mis-resolved entity is another firm's risk on your supplier.
- Never de-source, cancel, halt, or invoke force majeure on a single unconfirmed or propagated read; corroborate first.
- Do not change tenant-wide scorecard weights or alert thresholds casually - they re-score and re-alert everyone.
- Do not drop monitoring or mute alerts to quiet noise; a blind spot is a missed disruption.
- Route restrictions / sanctions / forced-labor findings to the compliance/trade system and a named officer; do not adjudicate them here.
- When intelligence here would drive a committing write in the ERP / procurement / planning system, gate that write under the target system's rules and base it on corroborated risk.

## References (load on demand)
- `references/i-score-and-factors.md` - load when reading, comparing, or configuring an i-Score or factor score: the factor taxonomy (financial, operational, restrictions & governance, geopolitical, ESG, cyber), score direction and composition, the licensed third-party feeds and their licensing and freshness, scorecard/model weighting as a tenant-wide change, and what a score does not tell you.
- `references/graph-and-monitoring.md` - load when working with the relationship graph, concentration analytics, or the alert feed: model-inferred vs curated edges and confidence, entity resolution, concentration / single-source / shared-node exposure, risk propagation / cascading, absence-is-not-safety, events vs alerts, the watchlist/portfolio, graph curation as a shared write, adjudication, and tier-1 reconciliation to the ERP.
