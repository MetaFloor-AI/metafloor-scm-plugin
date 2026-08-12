---
name: e2open-gts
description: "e2open Global Trade Management (GTM, formerly Amber Road) - safe operation of cloud multi-enterprise trade compliance - HS and ECCN/USML classification, Restricted Party Screening (RPS) against denied-party lists (OFAC SDN, BIS Entity/Denied Persons/Unverified, EU/UN/UK) with exact + fuzzy matching, export license determination, embargo and sanctions checks, customs entry filing and landed cost, and FTA / preferential-origin qualification with supplier solicitation and certificate issuance, on the Global Knowledge content feed. Use when the connected trade system is e2open or Amber Road and the work touches an RPS / denied-party hit, releasing a shipment or party that failed screening, an ECCN/ITAR/EAR classification, license determination, a customs entry, landed cost, an FTA / preference / rules-of-origin / RVC qualification, a supplier declaration or LTVD, a certificate of origin, an FTZ or duty drawback, or the user mentions e2open, Amber Road, GTM, Global Knowledge, or RPS."
---

# e2open GTM - operating it safely

e2open Global Trade Management (formerly **Amber Road**) runs export/import compliance as a
**cloud multi-enterprise network** on the e2open (Harmony) platform. It is neither embedded in the ERP the
way SAP GTS is, nor purely the messaging backbone the way Descartes is - it is a subscribed platform whose
compliance decisions are driven by **Global Knowledge**, a managed trade-content feed (HS codes, duty rates,
controls, denied-party lists, FTA rules for 160+ countries, each carrying effective dates). Modules:
Restricted Party Screening, Product Classification, Export Management, Import Management, Trade Agreement
Management (preferential trade / FTA), Duty Management, and Foreign-Trade Zone.

Two things make it dangerous. First, the same as every trade system: **releasing a screening or license block,
and transmitting a customs entry, are committing legal acts** - a wrong screening release is an OFAC/EAR/ITAR
violation (civil and criminal penalties into six and seven figures per violation; treat the numbers as
approximate statutory floors that are adjusted periodically, and do not quote a specific current amount as
authoritative); a wrong customs filing is a false statement (19 USC 1592, up to the domestic value of the
goods). Second, e2open's marquee surface: **self-certifying preferential origin and issuing a certificate of
origin is a legal claim that rests on supplier declarations you did not author, and every determination is
only as current as the Global Knowledge content version behind it.** This skill gives the judgment to classify
e2open actions so the harness gates them, plus the edge states and the reason certain actions never auto-clear.

## Contents
- Read this first
- When this applies
- Object & state model
- Vocabulary that bites
- Operations: read / write / destructive
- Gotchas that bite
- Edge states & special cases
- Recovery patterns
- Guardrails
- References

## Read this first (constraints for any release, filing, certification, or clearance)
- **HARD GATE - a screening-blocked shipment or party is released, a customs entry is transmitted, and a
  certificate of preferential origin is issued or signed, only by the named, authorized compliance/trade
  officer** (or licensed broker), with a written rationale and retained evidence. The agent proposes and
  prepares; it does not release, transmit, or certify. A ship date, a truck at the border, or a VP asking is not authorization.
- **Controlled parts never auto-clear.** Anything classified ITAR/USML or EAR-controlled (an ECCN on the CCL
  needing a license) routes to a human licensing officer. The agent never auto-assigns a license, never clears a legal-control block, never proposes a control downgrade.
- **Restricted-party (RPS) fuzzy hits are always human-adjudicated.** A low match score is not permission to
  clear; a denied party rarely uses the exact listed spelling. e2open runs the screen; the decision is a human's.
- **Managed service does not move the decision.** Where e2open manages the content or the screening lists for
  you, "managed" means the data is maintained, not that a hit auto-clears or a block auto-releases. The release/clear stays with your officer.
- **Preferential origin rests on valid, unexpired supplier declarations.** The agent never qualifies a BOM or
  self-certifies origin on missing, assumed, or expired declarations, and never signs a certificate of origin.
- **Fail closed.** If the platform, a customs authority, or a Global Knowledge list/content feed is
  unavailable, treat the document as blocked. If any single required government list did not run for a party,
  that party's screen is incomplete - block it, do not clear on the lists that did run. An incomplete check or an unconfirmed transmission is a block, not a pass.
- **When classification or origin is uncertain, resolve toward the stricter answer** (stricter control,
  higher-duty HS, not-qualifying for preference) and route to a human; never resolve doubt toward the code or origin that lets goods clear cheaper or faster.
- **Egress is tight.** Party names, screening lists, adjudication notes, ECCNs, HS codes, BOMs, and
  declaration/certificate data are export-control and customs records. A supplier solicitation sends part data
  outside your walls - keep the payload minimal and the recipients verified. Do not send any of this to unapproved tools.

## When this applies
Connector is e2open (Amber Road) and the work is trade compliance, screening, classification, licensing,
customs entry, preference/FTA, FTZ, or drawback. When NOT:
- ERP-embedded compliance that blocks the SAP sales order/delivery inside SAP -> `sap-gts`
- the GLN messaging/filing backbone to the authority, MacroPoint visibility -> `descartes`
- Thomson Reuters ONESOURCE Global Trade -> `onesource-gts`
- the ERP order/PO/customer master behind the shipment (pricing, credit, the order itself) -> `sap-mm` (or the ERP's own skill)
- warehouse pick/pack/ship execution -> `sap-ewm` or `manhattan-wms`

When e2open runs alongside another trade system (GTS determining inside the ERP, or Descartes filing to the
authority), the **stricter status governs** - one system's clear does not override another's block, and a
green e2open result does not release a live block held elsewhere. Reconcile before acting (table below).

## Object & state model (reason about state, not nouns)
- **Global Knowledge content** - the subscribed trade-content version (HS, duty rates, controls, denied-party
  lists, FTA rules) with **effective dates**, refreshed by e2open as a managed feed. A determination is bound
  to the content version behind it; a refresh can change a control, a rate, or a list without your action. See `references/classification-licensing.md`.
- **Classification** - the product's assigned codes. States: **proposed (draft) -> confirmed**. Two separate
  schemes: the **HS / HTS** code (duty, admissibility) and the **ECCN / USML** code (export control). A right HS with a wrong ECCN still ships illegally.
- **Screening result (RPS)** - a party-vs-list comparison. A **hit** has states: **potential (alert) ->
  under review -> cleared (recorded false positive) / confirmed (true match, blocked)**. Cleared is an audited decision attributed to the reviewer. See `references/screening.md`.
- **License** - authorization for a controlled export. States: **required (determined) -> assigned ->
  depleted**. Each use draws down remaining value/quantity; an expired or exhausted license blocks the next shipment. NLR / a license exception means no license needed, still not "uncontrolled."
- **Compliance / trade transaction** - an export or import document screened and controlled by the platform.
  States: **created -> screened -> held/blocked (RPS hit, license required, or embargo) -> released**. A block stops the shipment; released means a human overrode it on record. **Released is conditional on the content and list version at release time** - a release granted under content version N does not carry forward to N+1; a list/content refresh can re-block an already-released, in-flight document.
- **Preference / FTA qualification** - a product/BOM's origin determination. States: **not qualified -> under
  solicitation -> qualified (originating) / not qualifying**. Qualification rests on valid supplier declarations and produces a certificate of origin. See `references/preference-duty.md`.
- **Supplier declaration / LTVD** - a supplier's attestation of the origin of the inputs it supplies. States:
  **requested -> received -> valid (within validity period) -> expired**. A qualification is only as good as the unexpired declarations under it.
- **Customs entry (Import Management)** - the filing to the authority (US ACE, via broker connectivity or
  direct). States: **draft -> validated -> transmitted -> accepted / rejected / hold or exam -> released -> liquidated**. Accepted is not released; released is not final; liquidation (final duty) can land ~314 days later.

## Vocabulary that bites
- **Global Knowledge** - e2open's managed trade-content database (HS, duty, controls, denied-party lists, FTA rules) for 160+ countries; content carries effective dates and is refreshed by e2open. Every determination is only as current as the content version behind it.
- **Restricted Party Screening (RPS)** - screening of every party and role against government + commercial denied/restricted lists (OFAC SDN, BIS Entity/Denied Persons/Unverified, EU/UN/UK consolidated). A match blocks the party and the transaction.
- **Exact vs fuzzy match** - screening runs exact AND fuzzy (phonetic/similarity) above a configured threshold to catch misspellings and transliterations. A fuzzy hit is a potential match needing human review, not noise.
- **ECCN / EAR99** - Export Control Classification Number (EAR). EAR99 is the residual bucket: still EAR-controlled, not license-free. Drives license determination.
- **ITAR / USML** - defense articles on the US Munitions List, State Dept (DDTC) controlled. Strictest tier; DDTC-licensed; these never auto-clear.
- **License determination / NLR / license exception** - Export Management decides license-required vs No License Required or a license exception per ECCN x destination x end use x party; a license is assigned and depleted per use.
- **Preferential trade / FTA qualification** - determining a product is "originating" under an agreement's rules of origin so it can claim reduced/zero duty (USMCA, EU FTAs).
- **Rules of origin** - the test a BOM must pass: **tariff shift** (change in tariff classification / CTC), **regional value content (RVC)**, **de minimis**, or wholly obtained. Agreement- and HS-specific.
- **Regional Value Content (RVC)** - the percent of value that must originate; net-cost vs transaction-value methods give different answers.
- **Supplier solicitation / LTVD** - an outbound campaign asking suppliers to attest the origin of the inputs they supply (a long-term vendor declaration covers repeated shipments over a validity period). Qualification rests on these.
- **Certificate of origin / self-certification** - the document claiming preferential origin (USMCA certification, EUR.1/EUR-MED, invoice/origin declaration). Under USMCA the exporter/producer self-certifies; a false certificate is a customs false statement.
- **Foreign-Trade Zone (FTZ)** - a duty-deferral/elimination zone; goods are admitted (privileged vs non-privileged foreign status fixes the duty treatment), a weekly entry is filed, and zone-to-zone moves are tracked.
- **Duty drawback** - a refund claim to CBP for duties on re-exported or destroyed goods; a claim is a filing, not an automatic rebate.
- **Landed cost** - duty + tax + freight + fees estimate; provisional until the entry liquidates, and AD/CVD can move it.
- **Good-guy / whitelist** - parties previously cleared; future hits are suppressed. A reviewed control decision, not a way to silence repeat alerts.

## Operations: read / write / destructive
Classify every operation family by what it does to state and to legal exposure. No tool names - kinds of action.

| Class | e2open GTM operation families | Gate | Why |
|---|---|---|---|
| **Read** | display a classification (HS/ECCN/USML) and its Global Knowledge content version + effective date; display an RPS hit, match score, and list version; display a license and remaining value; display an FTA qualification result and the supplier declarations under it; display solicitation status; display a landed-cost estimate; display a customs entry / EEI and its authority status; **simulate a screen or validate a draft entry (no persist, no transmit)** | always pass | no state change; read the status, block reason, content version, and prior calls before acting |
| **Write (reversible)** | create/edit a **draft** classification, license request, customs entry, or EEI before transmission; build a draft FTA qualification / what-if BOM; draft (not yet send) a supplier solicitation campaign; edit a screening adjudication before saving; build a landed-cost quote | gate each action individually | a draft/request; nothing is filed, sent, or screened yet; low blast radius |
| **Write (committing)** | confirm a routine HS classification (commits the code future screens/filings/qualifications use); assign/determine and deplete a license for a **routine EAR99/NLR** case (for a controlled ITAR/USML or EAR CCL item the license *determination itself*, not just depletion, routes to the licensing officer - a wrong NLR call for a controlled item is the violation, so it is the destructive row); clear a **low-weight commercial/internal watch-list fuzzy hit within threshold ONLY (never a government denial/warning list)** by an authorized reviewer, with retained evidence; add a party with **no open hit** to the good-guy list (triggers an immediate re-screen; needs periodic revalidation); **send a supplier solicitation campaign** (part/BOM data egresses to external suppliers); qualify a BOM/product as originating on **complete, valid, unexpired** supplier declarations; **transmit a customs entry / file an AES EEI (returns an ITN)**; file an FTZ weekly entry / zone admission | gate + human approve | files with an authority, binds future screening/duty/preference, sends data outside your walls, or suppresses a party's future hits; bounded but real, legally attributable, evidence-logged |
| **Destructive / irreversible** | **clear or override a denied-party hit on a government list** (SDN, BIS Entity/Denied Persons/Unverified, EU/UN/UK); **release a shipment or party that failed screening**; **auto-clear or downgrade a controlled part** (ITAR/USML, EAR CCL); **issue/sign a certificate of origin or self-certify preferential origin** on an **unqualified BOM or incomplete/assumed/expired supplier declarations**; change/downgrade an already-confirmed classification (re-prices duty and re-runs control on future filings); amend/cancel a transmitted entry / EEI / certificate; add a party with an open or true-match hit to the good-guy list; file a knowingly false or undervalued declaration or drawback claim; override an effective-dated control or force a content mapping to make something clear; split/undervalue/re-route to slip under a license, duty, or reporting threshold | HARD GATE + named compliance officer / broker + evidence + re-read | a legal filing or export-control/customs decision; permanent authority record; a wrong call is a violation, not a typo |

**Inline safety rule (do not miss it):** "low-weight watch list" means an internal or commercial
adverse-media/watch list, **never a government denial or warning list**. A fuzzy hit on the SDN, EU/UN/UK
consolidated, BIS Entity, BIS Denied Persons, or BIS Unverified list is human-adjudicated, never cleared as a
routine committing action. **Verify the list type from the system's structured metadata before choosing the
tier;** if the source list is not unambiguously confirmed as non-government, treat the clearance as
destructive, not committing. Some organizations gate **all** screening clearances at the destructive tier
regardless of list type, because any clear is an audited decision that cannot be unseen - follow the stricter local policy.

**Reclassification rule (read this):** changing an already-confirmed classification is not a benign edit - it
re-prices duty and re-runs export control on future filings and qualifications, and downgrading a control
class is a legal-control decision. Treat any control-class or duty-impacting HS change as its destructive row above.

Universal rules to teach: read the authority status, block reason, match score, list version, content
effective date, ECCN/control class, license state, and the supplier declarations behind any qualification
before you transmit, clear, or certify, and **re-read at execute** (lists, classifications, content, and
declarations drift); never bypass a screening block or split/re-route/re-value a shipment to dodge a
threshold, duty, or embargo; a block or hold means stop; the ultimate destination and end user govern, not
the routing; a transmission is filed only when the authority returns acceptance - a reject means nothing was filed.

### Screening hit - adjudication decision
The one transition an agent gets asked to make. Where the hit lands decides who may act.

| Hit signal | What to do | Class |
|---|---|---|
| Exact match on any government denied-party list | keep blocked; confirm; escalate to the compliance officer | release = destructive |
| Fuzzy hit on any government list (SDN, BIS Entity/Denied Persons/Unverified, EU/UN/UK) | human adjudication only; the agent prepares the case, never clears | release = destructive |
| Fuzzy hit below threshold on a low-weight commercial/internal watch list (not a government list) | an authorized reviewer may clear as false positive, with retained evidence | committing |
| Party already on the good-guy list, entry current | passes screening; verify the entry is still valid | read |

### Cross-system reconciliation and fail-closed
| Situation | Behavior |
|---|---|
| e2open clear, but GTS or Descartes holds a block on the same shipment | blocked - the stricter status governs; do not release on the e2open clear alone |
| e2open block, another system shows clear | blocked - a live e2open screening/license block is not overridden by another system |
| e2open and GTS classify the same product to different ECCNs (or HS) | take the **stricter control / higher-duty** code and route to a human to reconcile; do not pick the code that clears cheaper |
| e2open shows a different screening result than Descartes for the same party | blocked until reconciled; a hit anywhere is a hit; identify why the two disagree (list version, name/address variant) |
| e2open content version is stale vs another system's | re-run against the newest content; the more current version wins, and a control it adds governs |
| Platform, authority, or a Global Knowledge list/content feed unavailable | treat as blocked; do not screen/file blind; an incomplete run is not a pass |
| One required government list did not run for a party | that party's screen is incomplete - block; do not clear on the lists that did run |
| Content effective date has moved since the last determination | re-run the check against the current content version before acting |
| Partial/ambiguous result - partial list coverage, multiple candidate HS codes, or an inconclusive qualification | treat as unresolved/blocked; escalate to a human; never resolve the ambiguity toward clearance |

### Under pressure (do not rationalize past these)
| The push | The rule |
|---|---|
| "The truck is at the border, release it now" | hard gate holds; a deadline is not authorization; only the named officer releases, with evidence |
| "Our biggest customer is asking, just clear this low fuzzy hit" | a government-list fuzzy hit is human-adjudicated regardless of score or who is asking; the agent prepares the case, never clears |
| "The content feed is down but we screened them before" | fail closed; a prior clean result is stale and the check is incomplete; block |
| "Skip the solicitation, the supplier always makes it here" | no qualification without a valid, unexpired supplier declaration; "always" is not evidence; do not self-certify |
| "We've always classified this as EAR99 / this party cleared last time" | a prior code or clearance is stale; re-check against the current content and list version before relying on it |

## Gotchas that bite (the real set - causal chains)
Clustered for lookup: screening 1-2, 19-20; content/managed-feed 2-4; classification/licensing 5-8, 14-15;
preference/FTA 9-13; customs/FTZ/drawback 16-18; cross-cutting 3, 21-22.
1. **An RPS fuzzy hit is a potential true match, not a typo.** A denied party rarely uses the exact listed spelling; clearing a low-score sanctions hit without documented adjudication can ship to a sanctioned entity. `references/screening.md`.
2. **Screening runs against Global Knowledge managed list feeds, and lists update.** A previously green party can newly block an in-flight shipment when the feed refreshes; a no-hit is only as fresh as the last run and the list version behind it.
3. **"Managed" is not "auto-cleared."** Where e2open maintains your content or screening lists, it maintains the data - it does not adjudicate a hit or release a block for you; the clear/release decision stays with your officer.
4. **A determination is bound to its Global Knowledge content version and effective date.** A stale version misclassifies, misprices duty, or misses a newly-added control; a content refresh can silently change the answer, so re-read the effective date at execute.
5. **ECCN drives license determination, so a wrong or downgraded ECCN passes as NLR and ships a controlled item without a license.** Misclassification is the most common root cause of an export violation.
6. **EAR99 is not "uncontrolled."** It still cannot go to an embargoed destination, a denied party, or a prohibited end use (WMD, certain military end uses); treating EAR99 as a free pass ignores the destination, party, and end-use checks that still apply.
7. **ITAR/USML items are State-Dept controlled and never auto-clear.** The license is DDTC-issued; no classification or clearance the agent makes can release a USML control.
8. **License determination depletes the license on each use.** Assigning the wrong license depletes the wrong authorization; an expired or exhausted license blocks the next shipment.
9. **FTA qualification rests on valid, unexpired supplier declarations.** Qualifying a BOM on missing, assumed, or expired declarations produces a false origin claim, and every downstream certificate inherits the defect. `references/preference-duty.md`.
10. **A supplier declaration / LTVD has a validity period.** An expired declaration silently invalidates a prior qualification; re-solicit before relying on it again, do not carry the old answer forward.
11. **Issuing or self-certifying a certificate of origin is a legal claim, not paperwork.** A false certificate is a customs false statement, and your customer relies on it to claim duty preference, so the exposure runs to both parties; the exporter/producer is liable on audit.
12. **Rules of origin are specific and unforgiving.** A product must pass the exact test for that agreement and HS heading (tariff shift/CTC, RVC, or de minimis); "mostly made here" does not qualify, and the wrong RVC method (net cost vs transaction value) changes the answer.
13. **A supplier solicitation campaign egresses part/BOM data to external suppliers.** Sending it is export-control-adjacent data leaving your control; keep the payload minimal, the recipients verified, and never attach controlled technical data.
14. **HS/HTS is a separate scheme from ECCN/USML.** A correct HS code for duty says nothing about export control; a right HS with a wrong ECCN still ships a controlled item illegally.
15. **A confirmed classification commits the code every future screen, filing, and qualification uses.** A wrong confirmed HS or ECCN silently mis-declares, mis-screens, and mis-qualifies each future shipment until someone reclassifies it.
16. **Landed cost is an estimate until liquidation.** CBP liquidates (final duty) up to ~314 days later; reclassification or AD/CVD can move it, so a "routine" entry can hide a large retroactive bill.
17. **FTZ admission status fixes the duty treatment at withdrawal.** Admitting goods as non-privileged vs privileged foreign changes the duty owed later; a wrong status mis-computes the entry, and a missed weekly entry loses the FTZ benefit.
18. **Duty drawback is a refund claim, a filing to CBP.** An overstated or unsupported drawback claim is a false claim, not a rebate you are owed.
19. **RPS screens every party, role, and address independently.** Sold-to, ship-to, bill-to, and end user screen separately; clearing the sold-to does not clear the ship-to or end user, and embargo is governed by ultimate destination and end use, not routing.
20. **A good-guy/whitelist entry suppresses future hits for that party.** Whitelist a party that later becomes a true match and the system silently ships to a denied party; a whitelist entry is a reviewed control decision that needs periodic revalidation.
21. **Deemed export and re-export/de-minimis break "nothing shipped" logic.** Releasing controlled technology to a foreign national is an export with no goods moved; US-origin or more-than-de-minimis US-content goods stay under EAR even between two foreign countries.
22. **Splitting, undervaluing, or re-routing to slip under a license, duty, or reporting threshold is the same violation with extra steps** and is auditable as structuring.

## Edge states & special cases
Each breaks naive "party looks fine, part looks fine, ship it" logic - key rule inline, full behavior in references.
- **Content effective dates / managed refresh** - a control, rate, or list can change with a Global Knowledge refresh you did not trigger; re-read the content version at execute. `references/classification-licensing.md`.
- **Delta / periodic re-screening** - list updates re-block previously clean, in-flight parties; re-read screening status at execute, not just at order entry. `references/screening.md`.
- **Multiple roles/addresses per partner** - each screens independently; a clear on one role is not a clear on all.
- **Expired supplier declaration** - a lapsed LTVD invalidates a prior qualification; the qualification is stale until re-solicited. `references/preference-duty.md`.
- **RVC method choice** - net cost vs transaction value gives different origin answers for the same BOM; the agreement dictates which applies.
- **License near-exhaustion** - remaining value/quantity can cover part of a shipment; a partial-cover assignment blocks the balance.
- **FTZ status / weekly entry** - privileged vs non-privileged foreign fixes duty; the weekly entry has a filing window. `references/preference-duty.md`.
- **Deemed export / re-export / de-minimis** - export events with no goods moving, or US jurisdiction between two foreign countries. `references/classification-licensing.md`.
- **Jurisdiction determination precedes classification** - deciding whether an item is ITAR/USML (State/DDTC) or EAR/CCL (Commerce/BIS) is its own high-stakes call; get the regime wrong and the whole control path is wrong. When unclear, treat as ITAR and route to a human. `references/classification-licensing.md`.
- **Good-guy list staleness** - a cleared party can later be listed; a stale whitelist entry is a live compliance hole.

## Recovery patterns (can it be undone, and what can't)
- **A release cannot recall a shipment.** Once the goods leave against a released document, the export happened; reversing the release re-blocks future processing but does not un-ship. A wrong release is a reportable event, not a fixable edit.
- **A transmitted customs entry is corrected by a Post-Summary Correction (before liquidation) or a protest (after)** - each a new filing on the record, not an edit. A filed AES EEI is corrected by a replacement or cancellation filing; after export the record persists.
- **An issued certificate of origin is withdrawn/invalidated and re-issued, not edited.** The customer who claimed preference on the old certificate must be notified; a bad certificate already relied upon is a disclosure matter.
- **A confirmed classification is corrected by a new classification version**, applied going forward; historic filings keep the code they were filed with.
- **A depleted license value is restored only by reversing the assignment** (itself a controlled action), not by editing the remaining value.
- **A wrongly-cleared screening hit cannot be unseen. Run the playbook:** (1) re-block the party; (2) retain all evidence (list version, match score, reviewer, rationale, timestamp); (3) escalate to the compliance officer immediately; (4) note the disclosure clock is already running - BIS expects an initial notification promptly (days, not weeks; the ~180-day figure is BIS's target for completing the full voluntary self-disclosure, not a safe harbor for the initial notice), OFAC and DDTC expect prompt disclosure. Re-blocking is not remediation, and whether to disclose is the officer's legal call, not the agent's.

## Guardrails
- Read the authority status, block reason, match score, list version, content effective date, HS/ECCN, license state, and the supplier declarations behind any qualification before proposing a transmit, clearance, or certification; re-read at execute because lists, classifications, content, and declarations drift.
- Never release a screening-blocked shipment/party, transmit a customs entry, or issue a certificate of origin without the named, authorized compliance officer or broker, a written rationale, and retained evidence. The agent prepares the case; the human decides, files, or signs.
- Controlled parts (ITAR/USML, EAR CCL) never auto-clear; denied-party fuzzy hits are always human-adjudicated; embargoes and controls are governed by ultimate destination and end user.
- Never qualify a BOM or self-certify origin on incomplete, assumed, or expired supplier declarations.
- Never split, re-route, or re-value a shipment to slip under a license, duty, or reporting threshold, and never backdate or fabricate a filing timestamp.
- Keep egress tight: screening data, party lists, classifications, HS/ECCN codes, BOMs, and declaration/certificate data are export-control and customs records; a solicitation sends part data outside - keep it minimal and to verified recipients.
- Fail closed: if the platform, an authority, or a Global Knowledge list/content feed is unavailable, treat as blocked and never let a shipment proceed on an incomplete or bypassed check.
- Keep the evidence trail: for any filing, clearance, release, or certification, retain the list/content version, score, reviewer, rationale, and timestamp, and keep prior screening/adjudication calls for audit.

## References (load on demand)
- `references/screening.md` - load when handling any RPS/denied-party hit or a screening-blocked transaction: exact vs fuzzy matching, government vs commercial list coverage, managed list feeds and versions, delta/periodic re-screening and touchpoints, hit states, party roles/addresses, the good-guy list, embargo by destination and end use.
- `references/classification-licensing.md` - load when classifying a product or handling a license/legal-control block: Global Knowledge content model and effective dates, HS vs ECCN vs USML schemes, control classes, EAR99, license determination / NLR / license exceptions and depletion, deemed export / re-export / de-minimis.
- `references/preference-duty.md` - load when qualifying preference, running a solicitation, issuing a certificate of origin, or computing duty/landed cost: rules of origin (tariff shift/CTC, RVC net-cost vs transaction-value, de minimis, wholly obtained), supplier solicitation and LTVD lifecycle, BOM qualification, certificate of origin and self-certification exposure, landed cost, FTZ (admission status, weekly entry), duty drawback, AD/CVD.
