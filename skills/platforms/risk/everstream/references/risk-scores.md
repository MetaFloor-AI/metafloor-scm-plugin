# Everstream risk scores - taxonomy, composition, freshness

The scoring layer (Explore). Load when reading, comparing, or configuring a risk score, or deciding how much
weight a score should carry in a decision. The one rule under all of it: a score is a predictive estimate
built from feeds of varying freshness, so it is a prior for investigation, not a fact to act on blindly.

## Contents
- The category taxonomy
- How the unified score composes (direction, scope)
- Predictive and climate projection
- Third-party feeds - licensing and freshness
- Scorecard weighting - a tenant-wide change
- What a score does NOT tell you

## The category taxonomy
Everstream models risk across roughly 30 categories and sub-categories, exposed as 50+ risk scores (the exact
count varies by tenant entitlement and platform release, so treat these as an order of magnitude, not a fixed
list). The families that matter for judgment:
- **Financial** - viability, distress, payment behavior (fed partly by RapidRatings, D&B). Note: deep
  financial-health scoring as a system of record is `resilinc`'s surface; here it is one dimension.
- **Operational** - reliability, on-time delivery, quality, capacity, single-source concentration.
- **ESG / ethical** - forced and child labor, human-rights and UFLPA exposure, environmental and social
  violations, governance. Fed partly by EcoVadis and Everstream's own intelligence. Legally sensitive.
- **Geopolitical / sociopolitical** - conflict, sanctions exposure, political instability, trade policy,
  strikes and civil unrest.
- **Environmental / climate** - natural-hazard exposure (flood, wildfire, seismic, storm) and forward climate
  projection.
- **Compliance** - regulatory and sanctions-adjacent risk; a signal to investigate, not a compliance ruling.

## How the unified score composes (direction, scope)
- The **unified risk score** is a composed roll-up of the category scores. **Higher = more risk.** Confirm the
  direction and the category before acting; a high financial score and a high climate score call for different
  responses.
- Scoring is both **location-based** (a site's exposure by where it sits) and **entity-based** (a company's
  risk). The same supplier can score differently by site; a company-level score can hide a single high-risk plant.
- A score exists per node, and can roll up per material, per lane, and per category. Reading only the unified
  number loses the reason; open the category breakdown before you decide.

## Predictive and climate projection
Scores are **predictive**, not just historical - they estimate forward exposure, and climate projection scores
model hazard exposure years out. Predictive means uncertainty: the score is a modeled likelihood, so treat a
high predictive score as "investigate and prepare," not "this has happened."

## Third-party feeds - licensing and freshness
The score embeds licensed external data. Two consequences for judgment:
- **Licensing.** Feeds such as **Dun & Bradstreet**, **RapidRatings**, and **EcoVadis** are licensed into the
  platform. Exporting or forwarding those values (or a score visibly derived from them) outside the approved
  tenant and users can breach the data license. The embedded number is not yours to redistribute.
- **Freshness.** The score is only as current as its feeds. A financial or ESG score can lag a real event by
  days because the upstream feed has its own refresh cycle. Re-read at decision time, and treat a score older
  than its feed's cycle as stale rather than as current truth.

## Scorecard weighting - a tenant-wide change
The scorecard is the configurable model that combines category scores into the unified score, and alert
thresholds decide who trips an alert. Changing either **re-scores every node on the tenant** and changes the
alerting for everyone, silently. It is a committing configuration change, not a personal preference:
- Weight and threshold changes need an owner and a reason; log what changed and why.
- Any decision taken on the changed scores between the change and a revert still stands - reverting the weights
  does not un-make those decisions.

## What a score does NOT tell you
- It is not a measurement or an audit finding; it is a modeled estimate.
- It does not confirm a sub-tier relationship - that lives in the map, with its own confidence.
- It does not replace the compliance system: a high compliance or sanctions score flags investigation, it does
  not screen or clear a party.
- A single node's score misses **correlated risk** - many nodes exposed to one region, port, or commodity
  event. Read the concentration, not just the individual number.
