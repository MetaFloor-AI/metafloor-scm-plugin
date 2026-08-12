# SAP GTS - Sanctioned Party List screening

How the denied-party screen actually works, why a hit blocks the shipment, and why a fuzzy sanctions hit is
never a routine clear. Read when a document is blocked by SPL, when a partner has a hit, or before proposing
any clearance.

## Contents
- What SPL screens (parties, roles, addresses)
- The lists
- Exact vs fuzzy matching
- Hit states and adjudication
- List versions and delta re-screening
- The good-guy (white) list
- Block propagation to the ERP

## What SPL screens
SPL (Sanctioned Party List) screening compares business partners on a trade document against denied-party
lists. It screens **every party and every role**: sold-to, ship-to, bill-to, payer, end user, contact persons,
and the addresses behind them. Each role/address screens independently, so a clean sold-to says nothing about
the ship-to or the end user. Screening runs at partner-master creation, at document transfer from the feeder
ERP, and again when a list version changes.

## The lists
GTS loads and versions government denied-party lists, including:
- **OFAC SDN** - Specially Designated Nationals and Blocked Persons (US Treasury).
- **BIS Denied Persons List**, **BIS Entity List**, **BIS Unverified List** (US Commerce).
- **EU consolidated list**, **UN consolidated list**, **UK (OFSI) list**, and national lists.
A hit against any active list blocks the partner and the document until adjudicated.

## Exact vs fuzzy matching
Screening runs two ways at once:
- **Exact** - the partner name/address matches a list entry directly.
- **Fuzzy** - phonetic and similarity matching above a configured threshold (a percentage). Catches
  misspellings, transliterations (Cyrillic/Arabic to Latin), word order, and abbreviations. A denied party
  rarely presents the exact listed spelling, so the fuzzy hit is the one that actually catches evasion.
A fuzzy hit is a **potential** match. A low similarity score narrows the review, it does not authorize a clear.
Fuzzy hits on the government lists (SDN, EU/UN/UK consolidated, BIS Entity, BIS Denied Persons, BIS Unverified)
are always adjudicated by a human and never auto-cleared; only low-risk fuzzy hits on a low-weight watch list
(an internal or commercial adverse-media/watch list, not a government list), within the configured threshold,
are in scope for an authorized reviewer to clear as a committing action.

## Hit states and adjudication
A screening hit moves through: **potential (blocked) -> released (recorded false positive) -> confirmed (true
match)**. Adjudication is the human review that decides which. Releasing records a false-positive decision that
is auditable and attributed to the releaser; confirming a true match keeps the block and drives reporting.
Every adjudication keeps: the list and version, the similarity score, the reviewer, the rationale, and the
timestamp. On a government audit, an unexplained release is treated as a knowing violation.

## List versions and delta re-screening
Lists change frequently. When GTS loads a new version it re-screens affected partners (**delta screening**); a
partner that was green last week can newly block an in-flight order today. A green status is only as fresh as
the last screening run against the current list version - so re-read screening status at execute time, not just
at order entry.

## The good-guy list (white list)
Partners confirmed clean can be added to a **good-guy list** (sometimes called a white list) so future hits are
suppressed for them. This is a control decision, not a way to silence repeat alerts: a good-guy party that later
becomes a true match will silently pass. Good-guy entries need periodic revalidation; a stale entry is a live
compliance hole. Adding a partner with no open hit is a committing action; adding a party that has an open or
true-match hit is destructive, because it enables future evasion.

## Block propagation to the ERP
A compliance block is not a GTS-only flag. GTS pushes the block back to the feeder ERP document, where it stops
**delivery creation, goods issue, and billing**. That is why releasing the block in GTS is a shipping decision:
the release is what lets the goods physically leave. Releasing a blocked document is done only by the named,
authorized compliance officer with a documented rationale and retained evidence.
