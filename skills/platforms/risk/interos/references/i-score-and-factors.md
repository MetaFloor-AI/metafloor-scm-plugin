# Interos i-Score and factors - taxonomy, composition, direction, freshness

The scoring layer. Load when reading, comparing, or configuring an i-Score or a factor score, or deciding how
much weight a number should carry in a decision. The rule under all of it: the i-Score is a modeled, predictive
estimate built from feeds of varying freshness, so it is a prior for investigation, not a fact to act on
blindly - and its direction is not the same as a raw risk number, so confirm the scale before you act.

## Contents
- Direction - confirm the scale
- The factor taxonomy
- How the i-Score composes (scope)
- Predictive, not historical
- Third-party feeds - licensing and freshness
- Scorecard / model weighting - a tenant-wide change
- What a score does NOT tell you

## Direction - confirm the scale
Interos brands the i-Score as a **resilience** score: higher tends to mean *more resilient* (less risk), the
opposite direction from a raw risk number. But individual factor scores and embedded third-party sub-scores can
be presented as **risk** (higher = worse). Reading one on the other's scale inverts every decision, so:
- Confirm which you are reading (composite resilience i-Score vs a factor/feed risk value) and the factor.
- A high i-Score with a high single-factor risk is not a contradiction - it means an otherwise-resilient entity
  with one sharp exposure. Read the factor breakdown, not just the roll-up.

## The factor taxonomy
The i-Score composes factor scores across roughly six families (the exact factor set and sub-factors vary by
tenant entitlement and platform release, so treat this as the shape, not a fixed list):
- **Financial** - viability, distress, payment behavior, liquidity. Drawn partly from licensed financial data. A
  signal, not an audited statement.
- **Operational** - reliability, delivery performance, capacity, and concentration / single-source dependency in
  the operating footprint.
- **Restrictions & governance** - sanctions, denied / restricted parties, export-control and debarment exposure,
  forced labor / UFLPA, ownership / beneficial-ownership and governance risk, adverse regulatory status. This
  **flags** for investigation; it is not a screening ruling (adjudication and block belong in `sap-gts`).
  Legally and reputationally sensitive.
- **Geopolitical** - country and location risk: conflict, political instability, trade policy, sanctions
  exposure, civil unrest, and natural-hazard geography.
- **ESG** - environmental, social (labor / human-rights), and governance sustainability risk. Legally and
  reputationally sensitive; overlaps the restrictions factor on forced-labor exposure.
- **Cyber** - the entity's external cyber-risk posture and exposure.

A factor score is a due-diligence prior. Open the factor, do not act on the rolled-up i-Score alone.

## How the i-Score composes (scope)
- The composite **i-Score** is a roll-up of the factor scores per entity. The roll-up hides which factor drives
  it - a financial-driven and a cyber-driven score of the same value call for different responses.
- Scoring is both **entity-based** (a company's risk) and location/site-aware; the same supplier can read
  differently by site, and a company-level score can hide a single high-risk plant.
- A score exists per entity and can roll up per factor and across the graph; reading only the composite loses
  the reason. Open the breakdown before you decide.

## Predictive, not historical
The i-Score is **predictive** - it estimates forward exposure, not only what has already happened. Predictive
means uncertainty: treat a low resilience / high factor-risk score as "investigate and prepare," not "this has
occurred." Corroborate before any irreversible move.

## Third-party feeds - licensing and freshness
The score embeds licensed external data (financial, cyber-ratings, sanctions/watchlist, ESG, adverse-media).
Two consequences for judgment:
- **Licensing.** Those embedded values (or a score visibly derived from them) are licensed into the platform.
  Exporting or forwarding them outside the approved tenant and users can breach the data license - the number is
  embedded intelligence, not yours to redistribute.
- **Freshness.** The score is only as current as its feeds. A financial, cyber, or sanctions value can lag a real
  event by days because the upstream feed has its own refresh cycle. Re-read at decision time, and treat a score
  older than its feed's cycle as stale rather than as current truth.

## Scorecard / model weighting - a tenant-wide change
The scorecard is the configurable model that combines factor scores into the i-Score, and alert thresholds
decide who trips an alert. Changing either **re-scores every entity on the tenant** and changes the alerting for
everyone, silently. It is a committing configuration change, not a personal preference:
- Weight and threshold changes need an owner and a reason; log what changed and why.
- Any decision taken on the changed scores between the change and a revert still stands - reverting the weights
  does not un-make those decisions.

## What a score does NOT tell you
- It is not a measurement or an audit finding; it is a modeled, predictive estimate.
- It does not confirm a sub-tier relationship - that lives in the graph, with its own confidence and entity match.
- It does not replace the compliance system: a high restrictions / sanctions factor flags investigation, it does
  not screen or clear a party.
- A single entity's score misses **concentration and correlated risk** - many entities exposed to one region,
  one shared upstream node, or one commodity event. Read the concentration and the shared-node map, not just the
  individual number.
