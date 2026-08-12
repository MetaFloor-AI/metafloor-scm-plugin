# Descartes denied-party / restricted-party screening (Visual Compliance / MK)

Load when handling any RPS hit or a screening-blocked party or shipment. Descartes runs the screening
engine; the clear/release decision on a government-list hit is always a human's.

## Contents
- The two engines
- What gets screened (lists)
- Exact vs fuzzy matching and the match score
- Screening touchpoints and re-screening
- Hit states
- Party roles and addresses
- The good-guy / whitelist
- Block propagation and the release decision

## The two engines
- **Visual Compliance** - Descartes' restricted-party screening suite (desktop lookup, batch screening, and
  API/embedded screening at order or checkout), plus export-classification and license-management content.
- **MK Denied Party Screening** (MK Data Systems) - Descartes' denied-party screening data and matching
  service, often embedded in ERP/e-commerce flows for real-time screening.
Both compare business partners against government and commercial lists and raise a hit when a party matches.
When both engines are configured, **any hit from either engine governs** - a clear on one does not override a
hit on the other, since they carry different list coverage, matching algorithms, and thresholds.

## What gets screened (lists)
Government denial and sanctions lists - every fuzzy hit on these is human-adjudicated, never auto-cleared:
- **OFAC SDN** and OFAC consolidated (SSI, FSE, etc.)
- **BIS Entity List**, **BIS Denied Persons List**, **BIS Unverified List**
- **State/DDTC debarred** parties
- **EU / UN / UK** consolidated sanctions lists, plus national lists
Plus optional commercial/internal adverse-media or watch lists. A low-weight commercial/internal list is the
only place an authorized reviewer may clear a within-threshold fuzzy hit as a routine committing action.

## Exact vs fuzzy matching and the match score
Screening runs **exact** and **fuzzy** (phonetic / edit-distance / transliteration) matching above a
configured similarity threshold, so it catches misspellings and aliases. The **match score** is a
similarity percentage, not a probability of guilt. A **low score is not safety**: denied parties rarely use
the exact listed spelling, and aliases/transliterations score low by design. A fuzzy hit is a *potential
true match* needing review, not noise to dismiss.

## Screening touchpoints and re-screening
The same party is screened at many points: new-customer onboarding, order entry, web checkout, before
shipment, and in **batch re-screening** when a list updates. Lists change constantly, so a party that
screened clean can newly hit an in-flight order after a list update. A "no-hit" is only as fresh as the last
run and the **list version** behind it - record and re-check the version at execute.

## Hit states
- **Potential (alert)** - a match was raised; the party/transaction is blocked pending review.
- **Reviewed** - a reviewer has looked at it.
- **Cleared (false positive)** - recorded as not-a-match, attributed to the reviewer, with retained evidence. Auditable.
- **Confirmed (true match)** - a real listed party; stays blocked and escalates.
"Cleared" is a recorded control decision tied to a named releaser; on audit a wrong clear is treated as a knowing violation.

## Party roles and addresses
RPS screens on name + address + country, and **every party, role, and address on the shipment screens
independently**: sold-to, ship-to, bill-to, end user, freight forwarder, and contacts. Clearing the sold-to
does not clear the ship-to or the end user. Deemed-export and end-user checks matter even when the immediate
customer is clean.

## The good-guy / whitelist
Parties previously cleared are placed on a **good-guy / whitelist**, which suppresses future hits for them.
This is a reviewed control decision, not a way to silence repeat alerts. A whitelisted party can later become
a true match (newly listed); a stale whitelist entry is a live compliance hole, so adding an entry should
trigger an immediate re-screen and entries need periodic revalidation. Adding a party with an open or
true-match hit to the whitelist silently enables future evasion - that is a destructive action.

## Block propagation and the release decision
A screening block stops the transaction it is attached to. **Releasing a shipment or party that failed
screening is an export-control decision, not a data fix** - only the named authorized reviewer/compliance
officer may do it, with a written rationale and retained evidence (list version, score, reviewer, timestamp).
If the screening service or a list is unavailable, fail closed: treat the party as blocked; an incomplete
screen is a block, not a pass. A wrongly-cleared hit cannot be unseen - re-block, retain evidence, and
escalate immediately (the disclosure clock starts at discovery: BIS initial notice within 180 days; OFAC/DDTC
prompt disclosure), and whether to disclose is the officer's legal call.
