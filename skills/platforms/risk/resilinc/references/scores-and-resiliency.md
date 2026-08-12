# Resilinc scores and resiliency - RiskShield, Resiliency Score, TTR/TTS/RaR, freshness

The scoring layer. Load when reading, comparing, or configuring a Resiliency Score, a RiskShield risk score, or
the recovery / revenue-exposure metrics, or deciding how much weight a number should carry. The rule under all
of it: these are modeled estimates and self-reported inputs, so a score is a prior for investigation, not a
fact to act on blindly - and two of the scores run in opposite directions.

## Contents
- Two scores, opposite directions
- RiskShield category taxonomy
- The Resiliency Score - composition
- TTR / TTS / Revenue-at-Risk - the recovery math
- Licensed third-party feeds - licensing and freshness
- Scorecard weighting - a tenant-wide change
- What a score does NOT tell you

## Two scores, opposite directions
Resilinc surfaces two different kinds of number, and reading one on the other's scale inverts every decision:
- **Resiliency Score** - **higher = more resilient (less risk)**. A composite of how prepared and recoverable a
  supplier is.
- **RiskShield risk scores** - **higher = more risk**. Per-category risk (financial, ESG, cyber, ...).
Always confirm which one you are reading, and the category, before acting. A high Resiliency Score with a high
RiskShield financial-risk score is not a contradiction - it means a well-prepared supplier under financial stress.

## RiskShield category taxonomy
RiskShield screens and continuously monitors suppliers for due diligence. The families that matter for judgment:
- **Financial-health** - viability, distress, payment behavior, drawn partly from licensed financial-rating
  feeds. A signal, not an audited statement.
- **ESG / sustainability** - environmental, labor / human-rights (including forced-labor exposure), governance.
  Legally and reputationally sensitive.
- **Cyber** - a supplier's external cyber-risk posture.
- **Restricted / denied-party** - sanctioned, debarred, or restricted-entity exposure and adverse regulatory
  status. This **flags** investigation; it is not the screening system of record. Adjudication and block belong
  in the trade/compliance system (`sap-gts`).
- **Geographic** - country and location risk (political, natural-hazard, infrastructure).
- **Adverse media** - negative news signals on the entity.
A RiskShield hit is a due-diligence prior. Higher = more risk; open the category, do not act on a rolled-up number.

## The Resiliency Score - composition
The Resiliency Score is Resilinc's proprietary composite of a supplier's resiliency. It draws on factors such
as **mapping completeness** (has the supplier disclosed sites and sub-tiers; defined in `mapping-and-eventwatch.md`), **BCP maturity** (does it have a
tested recovery plan, alternate sites, reported TTR), **financial** and **geographic** factors, and monitoring
coverage. Consequences for judgment:
- **Higher = more resilient.** A low score means less-prepared / higher-risk - the opposite of RiskShield.
- Because BCP and mapping inputs are **supplier-attested**, the score partly reflects what a supplier chose to
  report. A supplier that simply completed more of its profile can score better without being more resilient.
- It is a relative, modeled indicator, not a guarantee that recovery will go as claimed.

## TTR / TTS / Revenue-at-Risk - the recovery math
This is where Resilinc turns the map into exposure, and where the real decision lives:
- **TTR (Time-to-Recover)** - the supplier's **reported** time to restore output at a site after a full-stop
  disruption, per site. A self-reported claim, frequently untested.
- **TTS (Time-to-Survive)** - how long your on-hand plus pipeline inventory can meet demand if that site stops.
  Derived from your inventory and consumption, not from the supplier.
- **The exposure is the gap: TTR > TTS.** If the site takes longer to recover than your inventory lasts, you run
  out before it is back - that is the single-point-of-failure, regardless of how the resiliency score reads.
- **Revenue-at-Risk (RaR)** - the revenue exposed if a site or supplier goes down, computed by walking the
  **part-site / BOM mapping** up to your products and their revenue. RaR is only as accurate as that mapping: a
  missing part-site edge silently under-states it, so a site can look low-impact only because the map does not
  know what it makes for you.
Read TTR/TTS/RaR together, and treat TTR as a claim to pressure-test, not a fact.

## Licensed third-party feeds - licensing and freshness
Some RiskShield categories embed licensed external data (for example, a licensed financial-health rating, and
external ESG / adverse-media data). Two consequences for judgment:
- **Licensing.** Those embedded values (or a score visibly derived from them) are licensed into the platform.
  Exporting or forwarding them outside the approved tenant and users can breach the data license - the number is
  embedded intelligence, not yours to redistribute.
- **Freshness.** The score is only as current as its feeds and the supplier's last submission. A financial or ESG
  value can lag a real event by days or longer; re-read at decision time, and treat a score past its refresh
  cycle as stale rather than as current truth.

## Scorecard weighting - a tenant-wide change
The scorecard combines category inputs into the composite, and alert-severity thresholds decide who trips an
alert. Changing either **re-scores every supplier and changes the alerting for everyone on the tenant**,
silently. It is a committing configuration change, not a personal preference:
- Weight and threshold changes need an owner and a reason; log what changed and why.
- Any decision taken on the changed scores between the change and a revert still stands - reverting does not
  un-make those decisions.

## What a score does NOT tell you
- It is not a measurement or an audit finding; it is a modeled estimate built partly on self-reported inputs.
- It does not confirm a sub-tier relationship - that lives in the map, with its own source and freshness.
- It does not replace the compliance system: a restricted-party or sanctions hit flags investigation, it does
  not screen or clear a party.
- A single node's score misses **correlated risk** - many nodes exposed to one region, port, or commodity event.
  Read the concentration and the TTR/TTS gap, not just the individual number.
