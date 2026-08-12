# ONESOURCE Denied Party Screening (DPS)

Load when handling any DPS hit or a screening-blocked party or shipment. ONESOURCE runs the screening engine
off Thomson Reuters content; the clear/release decision on a government-list hit is always a human's.

## Contents
- What DPS is
- What gets screened (lists)
- Exact vs fuzzy matching and the match score
- Real-time vs batch screening and re-screening
- Hit states
- Party roles and addresses
- The good-guy list
- Block feedback to the ERP and the release decision

## What DPS is
**Denied Party Screening (DPS)** is ONESOURCE Global Trade's restricted/denied-party screening service. It
compares business partners (customers, vendors, ship-to, end users, contacts) against government and
commercial lists and raises a hit when a party matches. It runs two ways: **real-time** (embedded at party
creation, order entry, or checkout through the platform integration) and **batch** (mass re-screening of the
party base, typically when a list updates). The list content is Thomson Reuters Global Trade Content, kept
current by TR and versioned; a screen is only valid for the list version behind it.

## What gets screened (lists)
Government denial and sanctions lists - every fuzzy hit on these is human-adjudicated, never auto-cleared:
- **OFAC SDN** and OFAC consolidated (SSI, FSE, etc.)
- **BIS Entity List**, **BIS Denied Persons List**, **BIS Unverified List**
- **State/DDTC debarred** parties
- **EU / UN / UK** consolidated sanctions lists, plus national lists
Plus optional commercial/internal adverse-media or watch lists. A low-weight commercial/internal list is the
only place an authorized reviewer may clear a within-threshold fuzzy hit as a routine committing action.
(Underlying regimes to verify against, not just the platform: OFAC sanctions are 31 CFR 501-599; the BIS/EAR
lists are 15 CFR 730-774.)

## Exact vs fuzzy matching and the match score
Screening runs **exact** and **fuzzy** (phonetic / edit-distance / transliteration) matching above a
configured similarity threshold, so it catches misspellings and aliases. The **match score** is a similarity
percentage, not a probability of guilt. A **low score is not safety**: denied parties rarely use the exact
listed spelling, and aliases/transliterations score low by design. A fuzzy hit is a *potential true match*
needing review, not noise to dismiss. Lowering the threshold to make a hit disappear is evasion, not tuning.

## Real-time vs batch screening and re-screening
The same party is screened at many touchpoints: new-party onboarding, order entry, checkout, before
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
DPS screens on name + address + country, and **every party, role, and address on the shipment screens
independently**: sold-to, ship-to, bill-to, end user, freight forwarder, and contacts. Clearing the sold-to
does not clear the ship-to or the end user. Deemed-export and end-user checks matter even when the immediate
customer is clean.

## The good-guy list
Parties previously cleared are placed on a **good-guy list** (a.k.a. whitelist), which suppresses future hits
for them. This is a reviewed control decision, not a way to silence repeat alerts. A listed party can later
become a true match (newly listed); a stale good-guy list entry is a live compliance hole, so adding an entry
should trigger an immediate re-screen and entries need periodic revalidation. Adding a party with an open or
true-match hit to the good-guy list silently enables future evasion - that is a destructive action. If the
immediate re-screen triggered by adding an entry returns a hit, **remove the party from the good-guy list and
adjudicate the hit** - never leave a party that hits sitting on the list.

## Block feedback to the ERP and the release decision
A DPS block stops the transaction it is attached to and feeds back through the ERP integration, which can
hold the order, delivery, goods issue, or billing on the ERP side. **Releasing a party or shipment that
failed screening is an export-control decision, not a data fix** - only the named authorized reviewer /
compliance officer may do it, with a written rationale and retained evidence (list version, score, reviewer,
timestamp). If DPS or a required government list is unavailable, fail closed: treat the party as blocked; an
incomplete screen is a block, not a pass. Where ONESOURCE runs alongside an ERP-embedded control, the
stricter status governs - one system's clear does not override the other's live block. A wrongly-cleared hit
cannot be unseen - re-block, retain evidence, and escalate immediately (the disclosure clock starts at
discovery: BIS prompt initial notification with the full self-disclosure to follow; OFAC/DDTC prompt), and
whether to disclose is the officer's legal call.
