# RPS - Restricted Party Screening (e2open GTM)

Contents: what RPS screens · exact vs fuzzy · hit states · managed feeds and re-screening · good-guy list ·
embargo · fail-closed rules · recovery.

Load when handling any denied-party / restricted-party hit or a screening-blocked transaction. The block
propagates to the shipment; releasing it is an export-control decision, not a data fix. Screening runs off
**Global Knowledge** managed list feeds, so a result is only as fresh as the list version behind it.

## What RPS screens
- Every **party and role** on the transaction - sold-to, ship-to, bill-to, end user, freight forwarder,
  contacts - and their **addresses and countries**. Each screens independently; a clear on one role is not a clear on all.
- Against **government lists** (the adjudicated set): OFAC **SDN** and consolidated non-SDN, BIS **Entity
  List**, BIS **Denied Persons List**, BIS **Unverified List**, and EU / UN / UK consolidated lists, plus
  sectoral/sanctions programs. A hit on any of these is human-adjudicated.
- Against **commercial / internal watch lists** (adverse media, internal blocklists). Lower weight; a
  below-threshold fuzzy hit here may be cleared by an authorized reviewer with retained evidence.

## Exact vs fuzzy matching
- **Exact** - the party name/ID matches a listed entry. Keep blocked, confirm, escalate.
- **Fuzzy** - phonetic/similarity match above a configured threshold, to catch misspellings, transliterations,
  aliases, and reordered name parts. A fuzzy hit is a **potential true match**, not noise; a denied party
  rarely uses the exact listed spelling. Match score is **not** safety - a low score is not permission to clear.
- Screening also weighs **address and country**, so a common name in the wrong country can be a real hit.

## Hit states
`potential (alert) -> under review -> cleared (recorded false positive) / confirmed (true match, blocked)`.
Cleared is an **audited decision attributed to the reviewer**, with the list version, score, rationale, and
timestamp retained. On audit a wrong clear is treated as a knowing violation. Some organizations gate **all**
clearances at the destructive tier regardless of list type - follow the stricter local policy.

## Managed feeds, list versions, and re-screening
- Global Knowledge refreshes the lists as a managed feed; a party clean under one version can hit under the
  next. **"Managed" means the data is maintained, not that a hit auto-clears.**
- Screening re-runs at multiple touchpoints - order/party creation, transaction save, checkout, and periodic
  **delta/batch** re-screens against new list versions. A previously green party can newly block an in-flight shipment.
- Re-read screening status **at execute**, not just at order entry. A no-hit is only as fresh as the last run and the version behind it.

## Good-guy / whitelist
Parties previously cleared, whose future hits are suppressed. A **reviewed control decision**, not a way to
silence repeat alerts. Adding a party with **no open hit** is committing (it triggers an immediate re-screen
and needs periodic revalidation). Adding a party with an **open or true-match hit** is destructive - it
silently enables shipping to a denied party. A stale whitelist entry is a live compliance hole.

## Embargo and controlled destination
Governed by **ultimate destination and end use**, not routing. Shipping through a third country does not
remove an embargo; sub-regions and sectors matter; the end user governs. EAR99 is not exempt from these checks.

## Fail-closed rules
- Platform or a required government list unavailable -> treat the party/document as blocked; do not screen blind.
- One required government list did not run -> the screen is **incomplete**; block, do not clear on the lists that did run.
- If two trade systems disagree (e2open vs GTS vs Descartes), the **stricter status governs**.

## Recovery
A wrongly-cleared hit cannot be unseen: re-block the party, retain all evidence (list version, score,
reviewer, rationale, timestamp), and escalate to the compliance officer immediately - the disclosure clock is
already running (BIS prompt initial notice, days not weeks; OFAC/DDTC prompt). Re-blocking is not remediation;
whether to disclose is the officer's legal call.
