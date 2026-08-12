---
name: resilinc
description: Resilinc - the safe operation of supply-chain risk and supplier-resiliency intelligence built on
  supplier-attested data. Because it is mostly a read/intelligence system, actions are classified by data
  sensitivity and egress, not money or stock. Use when the connected risk system is Resilinc and the work
  touches multi-tier / n-tier / sub-tier supplier mapping, part-site / BOM exposure mapping, a Resiliency Score
  or a RiskShield financial / ESG / cyber / restricted-party risk score, Time-to-Recover (TTR) / Time-to-Survive
  (TTS), Revenue-at-Risk, an EventWatch / EventWatchAI disruption alert or incident, a supplier
  business-continuity (BCP) plan or recovery data, a war-game / what-if simulation, a supplier data-collection
  campaign or survey, a watchlist or monitored network; or the user mentions Resilinc, EventWatch, RiskShield,
  Resiliency Score, supplier-attested / self-reported sub-tier data, or pushing a Resilinc supplier risk flag
  back into the ERP or procurement system.
---

# Resilinc - operating it safely

Resilinc is a supply-chain risk and resiliency intelligence layer, not a system of record. Its distinctive
asset is **supplier-attested data**: suppliers log into a portal and report their own sub-tier relationships,
sites, parts, and business-continuity plans, which Resilinc maps down to part, site, and BOM level
(**multi-tier mapping**), scores for resiliency and risk (**Resiliency Score**, **RiskShield**), and watches
24/7 for real-world events that hit that map (**EventWatch / EventWatchAI**). Almost every operation is a read - and that
is what makes it different from the ERP/WMS/trade systems in this plugin. **The danger is not posting money or
stock; it is what the intelligence is and where it goes.** The reads are safe. The hazards are four: (1)
sensitive supplier, sub-tier, and BCP data leaving the trust boundary (egress) - Resilinc holds it under a
neutral-third-party model, so egress breaks a supplier's trust, not just a data policy; (2) treating
**self-reported** data (a supplier's own TTR, sub-tier list, or BCP claim) as verified fact; (3) tenant-wide
config or an outbound supplier campaign that acts on third parties; and (4) committing an irreversible action -
usually in another system - off a probabilistic score or an early alert. Classify by **data sensitivity and
egress**, not by stock or dollars.

## Contents
- Read this first
- When this applies
- The products
- Object & state model
- Vocabulary that bites
- Operations: read / write / by data sensitivity and egress
- Gotchas that bite
- Edge states & special cases
- Reconciliation / freshness
- Recovery patterns
- Guardrails
- References

## Read this first (constraints for any egress, commit, or outbound campaign)
- **Egress is the high-risk act here.** Sub-tier maps ("who supplies whom"), part-site / BOM mappings (which
  reveal your product's recipe and sourcing), supplier BCP plans and recovery data, emergency contacts (PII),
  and financial / ESG / restricted-party findings are the most sensitive assets in the platform. Resilinc holds
  much of it under a **neutral-third-party** arrangement: the supplier shared it trusting it would not leak to
  competitors or beyond permissioned users. Sending any of it to an external tool, an unapproved endpoint,
  another supplier, or a broad audience is a controlled disclosure that can breach that trust, an NDA, or a
  data license. Once it leaves you cannot recall it.
- **Your own reply is an egress channel.** Summarizing, quoting, or paraphrasing a sensitive read back to a
  user who lacks clearance is egress even though the read itself was "always pass." Before rendering a named
  supplier's BCP detail, a sub-tier edge, an emergency contact, or a legally sensitive finding, confirm the
  audience and role, and prefer an aggregate / de-identified summary over named-supplier detail.
- **Attested is not verified.** A supplier's reported TTR, sub-tier list, alternate site, or BCP maturity is a
  self-report, not an audit. It can be stale (last refreshed a year ago), incomplete (the supplier skipped
  sub-tiers it did not want to disclose), or optimistic (a claimed 2-week recovery it has never tested). Read
  the data's source and freshness before you rely on it.
- **A score / map / alert is a prior, not a verdict.** A Resiliency or RiskShield score is a modeled estimate,
  a sub-tier edge is only as good as who reported it, and an EventWatch alert is an early correlated signal.
  None is confirmed fact. Do not de-source a supplier, invoke force majeure, halt shipments, or push a hard
  block on a single unconfirmed read. Corroborate and re-read first.
- **An outbound campaign contacts third parties.** Launching a data-collection campaign or survey sends
  requests (often email) to your real suppliers asking them to complete or refresh profiles. It is a
  relationship-weighty, attributable outbound action at scale - scope the audience and the content, and do not
  fire it casually or broadly to "just get more data."
- **The irreversible action usually lives in the other system.** Resilinc informs; the ERP, procurement,
  planning, or trade system acts. When intelligence here would drive a committing write there (block a supplier
  for sourcing, cancel a PO, re-plan), gate that write in the target system under its own rules - and base it
  on corroborated risk, not a raw number.
- **Do not silence the signal to quiet the queue.** Removing a node from the monitored network, or muting an
  alert, creates a blind spot; a real disruption that fires during the gap is a missed disruption with lead
  time already lost.
- **Compliance decisions are not data edits here.** A restricted-party or sanctions hit from RiskShield is risk
  intelligence that routes to the compliance/trade system and a human officer; it is not adjudicated by editing
  a record in Resilinc.

## When this applies
Connector is Resilinc and the work is supplier-resiliency scoring, multi-tier / part-site mapping, disruption
monitoring, BCP data, or war-gaming. When NOT:
- AI-inferred sub-tier mapping and broad event monitoring where the graph is data-science-derived rather than
  supplier-attested -> `everstream`
- interconnected-risk graph modeling and continuous risk propagation across a relationship network -> `interos`
- denied-party / sanctions screening with block-and-release as the compliance system of record -> `sap-gts`
  (Resilinc / RiskShield *flags* restricted-party risk; GTS *adjudicates and blocks* it)
- the ERP supplier master, PO, and inventory the scores sit on top of -> `sap-mm` / `oracle-erp`
- real-time multimodal shipment ETA tracking as the system of record -> `project44` / `fourkites`

## The products (know which surface you are on)
- **Multi-Tier Mapping** - the supplier network mapped beyond tier-1 (tier-2, tier-3 ... tier-N) down to
  supplier company, site, part, and sub-commodity / BOM level. Built primarily from **supplier-attested**
  survey data (suppliers report their own sites and sub-tiers), supplemented by customer-provided and external
  data. Completeness depends on who responded. Mechanics in `references/mapping-and-eventwatch.md`.
- **EventWatch** (EventWatchAI) - 24/7 AI-driven global event monitoring across many event types and 100+
  languages, correlated to *your* mapped sites and parts, producing alerts with a severity and an impact
  assessment (potentially impacted sites, parts, and Revenue-at-Risk). Mechanics in `references/mapping-and-eventwatch.md`.
- **RiskShield** - supplier risk screening and continuous due diligence: financial-health, ESG / sustainability,
  cyber, restricted / denied-party, geographic, and adverse-media risk, for onboarding and ongoing monitoring.
  Draws on licensed third-party feeds. Deep taxonomy in `references/scores-and-resiliency.md`.
- **Resiliency Score** - Resilinc's proprietary composite of a supplier's resiliency (mapping completeness,
  BCP maturity, recovery capability, financial and geographic factors). **Higher = more resilient**, the
  opposite direction from a RiskShield risk score - confirm the direction before acting. `references/scores-and-resiliency.md`.
- **War-gaming / What-if** - scenario simulation and collaborative tabletop response: model a disruption (a
  site, a region, a supplier) and see modeled exposure, TTR/TTS gaps, and Revenue-at-Risk across the network.
  A run is a simulation; publishing or sharing it is a committing artifact.

## Object & state model (reason about state, not nouns)
- **Node (supplier / site / entity)** - a company or physical site in your network. Carries Resiliency Score,
  RiskShield category scores, reported TTR, and mapping completeness. Monitoring state: **monitored** (alerts
  fire) or **not monitored** (silent).
- **Supplier profile / questionnaire** - the data the supplier submits about itself. States: **not-started ->
  in-progress -> submitted -> validated -> stale** (past its refresh cycle). The **supplier owns and maintains
  it** - you request updates, you do not author it.
- **Sub-tier relationship (edge)** - a supply link at tier-N. Source: **supplier-attested** (reported by a
  mapped supplier) or **inferred / external**. States: **reported -> validated** or **unconfirmed**. Direction
  and part matter (who supplies whom, for what).
- **Part-site / BOM mapping (edge)** - which parts are made at which sites, feeding which of your products and
  revenue. The backbone of Revenue-at-Risk; only as good as the mapping behind it.
- **BCP record** - a supplier's business-continuity data: recovery plan, reported **TTR**, alternate sites,
  emergency contacts. Supplier-reported, highly sensitive, held under the neutral-party model.
- **Risk score (Resiliency Score / RiskShield categories)** - per node, per material. A moving snapshot,
  refreshed as underlying data and feeds land, not a fixed attribute.
- **Event / incident** - a real-world happening EventWatch detects (weather, geopolitical, fire, financial,
  cyber, health, logistics). States: **emerging -> updated -> closed**, and a closed one can **re-open or escalate**.
- **Alert** - an incident correlated to your mapped network (sites, parts, Revenue-at-Risk). States: **new ->
  acknowledged -> adjudicated** (impacted / not-impacted / resolved) **-> closed**. Adjudication is attributable.
- **Data-collection campaign / survey** - an outbound request to suppliers to complete or refresh their profile.
  States: **draft -> launched -> collecting -> closed**. Launching contacts third parties.
- **What-if / war-game scenario** - a saved simulation. States: **draft -> saved -> published / shared**.
- **Risk-register / mitigation entry** - a logged risk plus owner and action; attributable, part of the audit trail.

## Vocabulary that bites
- **Supplier-attested / self-reported** - sub-tier lists, BCP plans, and TTR are provided by the supplier, not
  measured by Resilinc. Attested is not verified; the data can be stale, incomplete, or optimistic, and the
  supplier controls it. This is Resilinc's strength (it is not pure inference) *and* its trap (it is a claim).
- **Multi-tier / n-tier map** - relationships below tier-1, down to part / site / BOM. "Tier-N" is depth, not
  certainty, and the map's completeness is a **response rate**, not a census.
- **Mapping completeness / response rate** - the share of your suppliers who actually completed a profile. Low
  completeness means the map's silence is unreliable: a missing sub-tier may be unmapped, not absent.
- **TTR (Time-to-Recover)** - the supplier's reported time to restore output at a site after a full-stop
  disruption. A self-reported claim, often untested, per site.
- **TTS (Time-to-Survive)** - how long your on-hand and pipeline inventory can meet demand if a site stops. The
  exposure is where **TTR > TTS** - you run out before the supplier recovers.
- **Revenue-at-Risk (RaR)** - modeled revenue exposed if a site or supplier goes down, computed from the
  part-site / BOM mapping. Only as accurate as that mapping; a missing part-site edge under-states it.
- **Resiliency Score** - proprietary composite where **higher = more resilient** (less risk). Runs the opposite
  direction from a RiskShield risk score - read the scale before acting (gotcha #6).
- **RiskShield** - supplier risk screening (financial / ESG / cyber / restricted-party / geographic /
  adverse-media). A due-diligence signal to investigate, **not** a compliance ruling or a screening system of record.
- **EventWatch / impact assessment** - an event correlated to your map yields "potentially impacted" sites and
  parts and a modeled RaR. "Potentially impacted" is a correlation, not a confirmed hit on you.
- **Business Continuity Plan (BCP) data** - recovery plans, alternate sites, emergency contacts. The highest
  supplier-sensitivity data class; held under the neutral-party model and often NDA-bound.
- **Neutral-third-party model** - suppliers share data with Resilinc trusting it stays permissioned. Egress
  beyond the approved audience breaks that model, not just an internal policy.
- **Data-collection campaign / survey** - an outbound request to suppliers; a real communication to third
  parties, with relationship and response-fatigue weight.
- **Resilinc vs Resiliency Score** - Resilinc is the platform; the **Resiliency Score** is one composite metric
  inside it (higher = more resilient). Do not conflate them or abbreviate the score to "Resilinc score."

## Operations: read / write / by data sensitivity and egress
Almost everything is a read - so gate by where the data goes, what a config change moves, and who an outbound
action touches, not by "does it write." No tool names; kinds of action.

| Class | Resilinc operation families | Gate | Why |
|---|---|---|---|
| **Read (in-boundary)** | display a supplier's Resiliency / RiskShield scores and category breakdown; view the multi-tier / part-site / BOM map; read a BCP record, TTR, TTS, or Revenue-at-Risk; list events and alerts and their impact assessment; view "my network"; run a war-game / what-if without saving; view a watchlist / monitored network; view the audit / adjudication trail | always pass in-boundary *(role/clearance still required to view the highest-sensitivity payloads - see below the table)* | no state change - but egress rules apply before any output to a user or another system (below). Read the data's **source, freshness, and completeness** before you rely on it |
| **Write (reversible, local scope)** | *additive / annotation:* add a node, part, or site to your monitored network or watchlist; subscribe / unsubscribe an alert notification; annotate a node or alert; save a war-game / what-if as a draft. *coverage-reducing:* remove a node from a watchlist; snooze / mute an alert | *additive:* gate one at a time. *coverage-reducing (mute / snooze / remove from a watchlist): elevate to human approve unconditionally* | additive writes change *your* view, low blast. But a coverage-reducing write is reversible while its consequence is not: muting an alert or dropping a node opens a monitoring blind spot, and a disruption missed during the gap costs lead time that cannot be backfilled - so it always gets a human, not a solo one-at-a-time gate |
| **Write (committing - shared, outbound, or cross-system)** | change scorecard weights or alert-severity thresholds (re-scores / re-alerts the tenant); validate or reject a reported sub-tier edge (rewrites the shared map); adjudicate an alert as not-impacted / resolved (attributable, suppresses future signal); **launch a data-collection campaign or survey to suppliers** (outbound to third parties); publish or share a war-game scenario; write a risk-register entry; **push a Resilinc score or risk flag into the ERP / procurement / planning system** (drives a committing write there) | gate + human approve | binds a shared model or map, contacts third parties, or hard-codes a probabilistic score into a downstream action others act on |
| **Destructive / high-sensitivity** | **egress of sub-tier maps, part-site / BOM mappings, BCP data, emergency contacts, or financial / ESG / restricted-party findings to an external tool, unapproved endpoint, another supplier, or a broad audience**; delete or overwrite a curated map, BCP record, or adjudication history; remove a supplier / site from monitoring entirely; drive an irreversible real-world action (de-source, cancel, invoke force majeure) on a single unconfirmed read | HARD GATE + named owner + re-read | data that leaves cannot be recalled and can breach NDA, the neutral-party trust, a data license, or law; curated maps and BCP history are not cheaply rebuilt; a wrong irreversible call off a probabilistic or self-reported read is a real-world loss |

**The gate ladder (what each Gate cell means in practice):**
- **gate one at a time** (reversible local write) - a confirmation before acting, a captured reason (why this
  node is dropped, why this alert is muted), and an audit-log entry, per action and not batched.
- **gate + human approve** (committing) - explicit human sign-off before it binds the shared map, re-scores the
  tenant, contacts suppliers, or drives a downstream write; re-read the current state first, because scores,
  maps, and profile freshness drift.
- **HARD GATE + named owner + re-read** (destructive / high-sensitivity) - a specific accountable person
  authorizes; block until they sign off; re-read the current state at execute; log the payload class and the
  reason. For egress with no approved destination, the default is refuse and escalate, not proceed.

**Reading sensitive data in-boundary is not unconditional.** "Always pass in-boundary" means no *state* change,
not "show anyone anything." The highest-sensitivity payloads (BCP plans, restricted-party / sanctions findings,
emergency-contact PII, licensed feed values) need confirmed **role / clearance** even to view. If you cannot
confirm the user's role or clearance for a sensitive payload class, **refuse and escalate - do not render it**;
prefer a de-identified summary over named detail. And a **bulk** in-boundary read of sensitive data (for
example, 500 supplier BCP records to answer a portfolio question) inherits the egress gate of its payload class
the moment it is rendered - treat it as an egress decision, not a routine read.

**The read gate and the action gate are independent.** A read that passes authorizes *seeing* the data, not
*acting* on it. Reading a restricted-party flag, a low Resiliency Score, or a sub-tier edge does not authorize
de-sourcing, blocking, cancelling, or any irreversible move in the same session - re-gate the action on its own
class (committing or destructive), separately from the read that surfaced it.

**Egress is its own axis (read this):** the read/write columns describe state change; egress is orthogonal. The
*same* read that is safe in-platform becomes the most dangerous action the moment its output crosses the trust
boundary - and that boundary includes your own reply to a user who lacks clearance. Before any export, forward,
share, push, or rendering of sensitive detail, treat the payload as a controlled disclosure: what data class is
it (sub-tier map? part-site / BOM? BCP plan? emergency-contact PII? financial / ESG / restricted-party
finding?), who is the audience, and is that destination approved (allowlist or data owner; if unknown, default
to block). Aggregate, portfolio-level reads are lower sensitivity than a named supplier's BCP or flag, though a
risk distribution across your network (for example, "list every site with TTR > TTS") still exposes network
composition and is gated on egress. **Combining sources raises the class:** joining a Resilinc BCP or sub-tier
map with SAP supplier-master or an Everstream score creates a new data class whose sensitivity is the union of
both - gate the combined output as egress from both systems, not the lower of the two. **Bulk amplifies the
class:** exporting a whole sub-tier map, a full BOM mapping, or every supplier's BCP at once is a larger
disclosure than one lookup - a bulk read of sensitive data is the top egress class, gate it hardest.

**Egress-class ladder (apply this to the payload *regardless* of the row above - a "read" that leaves becomes this):**

| Payload class | Sensitivity | Egress gate |
|---|---|---|
| Aggregate / de-identified (counts, portfolio distribution) | low | confirm audience; portfolio composition can still leak |
| Named-supplier score / TTR / single sub-tier edge | medium | confirm audience + approved destination |
| Sub-tier map, part-site / BOM mapping, financial / ESG / restricted-party finding | high | named owner + approved destination; default block if unknown |
| BCP plan, emergency-contact PII, licensed third-party feed value, or any **bulk** export of the above | highest | HARD GATE + named owner; egress cannot be recalled |

Worked example: a user asks to email a named supplier's BCP recovery plan to their procurement team -> payload
= BCP plan -> highest -> HARD GATE + named owner + re-read, and prefer a de-identified summary. The same user
asks for the aggregate TTR distribution across 50 suppliers -> payload = aggregate -> low -> confirm the
audience and proceed (but note it still exposes network composition).

**Cross-system push can be destructive-by-proxy.** A flag pushed back into the ERP / procurement / planning
system is a committing write in Resilinc, but in a target system configured for automation it can trigger an
automatic supplier block, a PO cancellation, or a re-source that is practically irreversible (for example, a
Resilinc risk flag pushed to SAP MM that fires an automatic vendor block or cancels open POs - shipments
already diverted, POs already cancelled). Before pushing, **check the target system's automation state**: does a
received flag/score auto-trigger a block, cancel, or re-source, or does it land as a passive attribute a human
later acts on? Gate the push against the *target system's* automation, not just Resilinc's write class; if the
target auto-acts on the pushed flag, treat the push as destructive and apply the hard gate regardless of
Resilinc's own write class. **If you cannot confirm the target's automation posture, default to treating the
push as destructive-by-proxy and hard-gate it** - assume it may auto-act until proven otherwise.

Universal rules to teach: read the **source (attested vs inferred), the freshness, the completeness, and the
"my network" scope** before you rely on a score/map/alert; re-read at decision time because scores, maps, and
profiles all drift; never silence monitoring to reduce noise; never let a probabilistic or self-reported read
trigger an irreversible action without corroboration; route restricted-party / sanctions findings to the
compliance/trade system and a human, not a data edit here; keep sensitive intelligence inside the approved
audience and the neutral-party boundary.

## Gotchas that bite (the real set - causal chains)
The safety-critical chains - check these before any irreversible or outbound action - are egress (#12, #13,
#14, #15), acting on an unconfirmed or self-reported read (#1, #2, #6, #9, #20), and silencing the signal (#16,
#17). The rest corrupt a decision but do not by themselves cause an irreversible loss.
1. **Supplier-attested data is a self-report, not an audit.** A sub-tier list, an alternate site, or a BCP plan
   is what the supplier chose to tell you; de-sourcing or reassuring an auditor on it as if verified can be flatly wrong.
2. **A reported TTR is a claim, often untested.** A supplier's "2-week recovery" may never have been exercised;
   planning inventory to that number and finding real recovery is 10 weeks leaves you exposed exactly when it matters.
3. **Exposure is where TTR > TTS, not where a score is red.** A high-scoring supplier with a TTR far longer than
   your TTS is a real single point of failure; reading the score alone misses the recovery-vs-inventory gap.
4. **Revenue-at-Risk is only as good as the part-site / BOM mapping.** A missing part-site edge silently
   under-states RaR - the site looks low-impact only because the map does not know what it makes for you.
5. **Mapping completeness is a response rate, not a census.** If only part of your base completed profiles, a
   "clean" sub-tier map is silence, not safety; an unmapped tier-N single-source can be invisible.
6. **Resiliency Score and RiskShield run opposite directions.** Resiliency: higher = more resilient (less risk);
   RiskShield: higher = more risk. Reading one on the other's scale inverts the decision - confirm the direction
   and the category before acting. `references/scores-and-resiliency.md`.
7. **A high category score is not a compliance ruling.** A RiskShield restricted-party or sanctions flag says
   "investigate"; the legal screening, adjudication, and block belong in the trade/compliance system, never a data edit here.
8. **Absence of a sub-tier link is not proof of no exposure.** The map shows what suppliers reported; "not shown"
   is "not reported," not "not there." Statements of "no exposure to X" must rest on validated data, not silence.
9. **An EventWatch alert is an early correlated signal, not a confirmed impact.** Acting irreversibly - halting
   shipments, invoking force majeure - on an emerging, uncorroborated event can be premature and self-inflicted.
10. **"Potentially impacted" is a correlation of event to map, not a hit on the ground.** A site flagged
    impacted by a geofenced event may be unaffected, and one just outside can still be down; halting a lane or
    pre-buying against the flag alone can spend or disrupt on an event that never touched you - validate before acting.
11. **Scores embed licensed third-party feeds.** Financial-health, ESG, or adverse-media values come from
    licensed data (for example, a licensed financial-health rating); exporting them outside the approved tenant
    breaches the license, and the score inherits the feed's refresh lag. `references/scores-and-resiliency.md`.
12. **BCP data is the highest-sensitivity class, held under a neutral-party trust.** Suppliers shared recovery
    plans, alternate sites, and contacts trusting they stay permissioned; egressing them to a competitor-adjacent
    audience, another supplier, or an external tool breaks that trust and cannot be recalled.
13. **Part-site / BOM mappings expose your product's recipe and sourcing.** Leaking who makes which part for
    which product hands over a trade secret; treat the mapping as egress-controlled, not internal plumbing.
14. **Emergency contacts and supplier PII are personal data.** Forwarding an emergency-contact list outside the
    approved audience is a privacy exposure with its own legal weight, separate from the commercial sensitivity.
15. **Sub-tier maps are competitively sensitive and often NDA-bound.** Egressing "who supplies whom" to an
    external tool or the supplier itself can breach NDA and expose a customer's sourcing; once sent it cannot be recalled.
16. **Removing a supplier / site / part from monitoring stops all its alerts.** A silent blind spot - you learn
    it mattered only after the disruption you no longer see.
17. **Muting or snoozing an alert suppresses the signal, not the event.** A muted alert that was real becomes a
    missed disruption, and lead time is the thing you cannot get back.
18. **Marking an alert not-impacted / resolved is an attributable decision.** If it was real, the record shows
    you saw it and dismissed it; adjudicate with evidence, not to clear the queue.
19. **Validating or rejecting a reported sub-tier edge rewrites the shared map.** Everyone downstream reasons on
    it; a wrong validation propagates a false relationship and a wrong rejection hides a real one across every future analysis.
20. **Launching a data-collection campaign contacts real suppliers.** A broad or ill-scoped survey blast fatigues
    the base, lowers response quality, and can strain relationships; scope the audience and content, and do not fire it to "just get more data."
21. **Changing scorecard weights or alert-severity thresholds re-scores / re-alerts the whole tenant.** A tuning
    tweak silently moves every supplier's standing and changes who trips an alert for everyone; it is a committing config change, not a personal view.
22. **A stale profile is a moving target read as fixed.** A supplier's profile last refreshed a year ago may not
    reflect a new sub-tier, a closed site, or a degraded BCP; re-read the freshness, do not trust a cached submission.
23. **A closed event can re-open or escalate.** Standing down monitoring on an early "handled" read can miss the
    second wave (an aftershock, a secondary closure, a sanctions expansion).
24. **Correlated risk: one event hits many nodes at once.** Reading a single site's alert misses that one region
    or commodity event exposes your whole category - and worse, it leads you to fail over to alternate suppliers
    that sit in the *same* affected region, concentrating your response in the one failure mode you were fleeing;
    read the event's full impact set, not one node's flag.
25. **Pushing a Resilinc flag back into the ERP / procurement system commits in that system.** The score's
    uncertainty gets hard-coded into a sourcing block or a stopped PO; gate that write under the target system's
    rules, and base it on corroborated risk, not a raw score.

(More per-topic detail: `references/scores-and-resiliency.md`, `references/mapping-and-eventwatch.md`.)

## Edge states & special cases
Each breaks naive "the score is high / the map is clean, so act" logic - key rule inline, full behavior in references.
- **Attested vs inferred data** - the map and BCP carry supplier-reported and externally-derived data; the
  source decides how far you can act. Reason on source and freshness, not just on whether a value exists. `references/mapping-and-eventwatch.md`.
- **Stale / incomplete profile** - a supplier that never finished or last refreshed long ago yields gaps read as
  facts; when you hit a stale or missing profile, flag it and propose a data-collection refresh, do not record the gap as "no risk."
- **Score-direction reversal** - Resiliency (higher = better) vs RiskShield (higher = worse) point opposite
  ways; confirm the scale before you act on either. `references/scores-and-resiliency.md`.
- **TTR vs TTS gap** - exposure is the recovery-versus-inventory gap, not the score; a resilient-looking supplier
  with TTR > TTS is still a single point of failure.
- **Correlated / aggregated exposure** - one event exposes many nodes; per-node reading misses concentration in a
  region, port, or commodity, and one supplier's site outage can hit multiple of your parts.
- **Emerging vs confirmed vs re-opened event** - an emerging event is low-corroboration; a closed one can
  escalate. Re-read status at execute, not just at first alert.
- **Degraded / error / timeout** - if Resilinc errors, times out, or serves data past its refresh cycle, fail
  safe. Concretely: (1) report the error and state that the data may be stale or partial; (2) refuse to score,
  rank, or drive an irreversible action on the degraded read; (3) fall back to the ERP supplier master for
  tier-1 facts only; (4) treat missing monitoring or a blank alert feed as **unknown**, not an all-clear, and
  say so. Do not silently substitute a cached number for a live one. If the decision is time-critical (an active
  disruption), present the best-available read with explicit uncertainty labels, name corroboration sources, and
  still gate any irreversible action behind human approval - degraded data lowers confidence, it does not raise autonomy.
- **Tier-1 reconciliation** - Resilinc's tier-1 should reconcile to the ERP supplier master (who you actually
  buy from); its tier-N is supplier-reported beyond it. Where they disagree at tier-1, the ERP is the record.

## Reconciliation / freshness
A score, an alert, a map, and a supplier profile are all snapshots. Re-read at decision time: scores refresh as
feeds and profiles land, events update and re-open, sub-tier and BCP data is only as current as the supplier's
last submission, and mapping completeness changes as campaigns close. When Resilinc and the ERP disagree at
tier-1, trust the ERP supplier master for who you buy from; Resilinc's value is the resiliency overlay, the BCP
data, and everything below tier-1. Treat a profile or score older than its refresh cycle as stale, not current.
When Resilinc and another risk system (Everstream, Interos) disagree on the same supplier, do not silently pick
one: surface the conflict with each system's source and freshness and let a human weigh it - a divergence is
itself a signal to corroborate, not a tie to break automatically.

## Recovery patterns (can it be undone, and what can't)
- **Egress cannot be undone.** Data that crossed the trust boundary - a sub-tier map, a BCP plan, an
  emergency-contact list, a licensed financial value - cannot be recalled; a wrong disclosure is a reportable
  event, not a fixable edit. This is the irreversible action in the platform - gate it hardest. If it happens in
  error: notify the data owner and the compliance / data-privacy officer immediately; document what was disclosed, to whom, and which data
  classes (sub-tier / BOM / BCP / PII / licensed feed) so compliance can scope the NDA/license breach; revoke
  the destination's access if that is possible; and do not try to "fix" it by deleting data in the target system
  - that is a separate write with its own gate.
- **A launched supplier campaign cannot be un-sent.** The suppliers already received the request; you can close
  the campaign, but the outreach and any relationship effect stand. Scope before launch, do not un-send after.
- **Removing a node from monitoring** is reversible by re-adding, but the alerts that would have fired during the
  blind window are gone, and re-collecting its map/BCP may need a fresh campaign. The coverage gap does not backfill.
- **Muting an alert** is reversible, but a real disruption missed during the mute costs lead time you cannot recover.
- **A scorecard weight / threshold change** is reversible by reverting, but any decision made on the changed
  scores in between still stands.
- **Adjudication / risk-register entries** are corrected by a new entry (the trail keeps both), not a silent
  undo; the original decision remains attributable.
- **A deleted curated map, BCP record, or scenario** may not be reconstructable - much of it took supplier
  outreach and human curation to build; treat deletion as destructive, not housekeeping.

## Guardrails
- If your action logic reduces to "score is high, so act" or "map is clean, so no exposure," stop: a modeled
  score and a partly-self-reported, partly-complete map do not support an irreversible move on their own.
- Read the **source (attested vs inferred), the freshness, the completeness, the category, and the direction**
  of any score before you rely on it; re-read at decision time because scores, maps, and profiles drift.
- Egress is the high-risk act: before any export, forward, share, or push, classify the payload (sub-tier map /
  part-site-BOM / BCP plan / emergency-contact PII / financial-ESG-restricted-party finding), confirm the
  audience, and confirm the destination is approved. Prefer aggregate, de-identified reads over named-supplier detail.
- Treat BCP and sub-tier data as held under a neutral-party trust: keep it inside the permissioned audience.
- Never de-source, cancel, halt, or invoke force majeure on a single unconfirmed or self-reported read; corroborate first.
- Scope any data-collection campaign before launch - it contacts real suppliers and cannot be un-sent.
- Do not change tenant-wide scorecard weights or alert thresholds casually - they re-score and re-alert everyone.
- Do not remove monitoring or mute alerts to quiet noise; a blind spot is a missed disruption.
- Route restricted-party / sanctions findings to the compliance/trade system and a named officer; do not adjudicate them by editing a record here.
- When intelligence here would drive a committing write in the ERP / procurement / planning system, gate that write under the target system's rules and base it on corroborated risk.

## References (load on demand)
- `references/scores-and-resiliency.md` - load when reading, comparing, or configuring a score: the RiskShield
  category taxonomy (financial, ESG, cyber, restricted-party, geographic, adverse-media), the Resiliency Score
  composition and direction, TTR / TTS / Revenue-at-Risk mechanics, the licensed third-party feeds and their
  licensing and freshness, scorecard weighting as a tenant-wide change.
- `references/mapping-and-eventwatch.md` - load when working with the multi-tier map, BCP data, the alert feed,
  or a campaign: supplier-attested vs inferred data and completeness, part-site / BOM mapping, absence-is-not-safety,
  events vs alerts and impact assessment, the monitored network / watchlist, data-collection campaigns, the
  war-game / what-if simulator, and adjudication.
