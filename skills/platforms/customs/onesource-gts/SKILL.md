---
name: onesource-gts
description: "Thomson Reuters ONESOURCE Global Trade - safe operation of the content-led trade platform over one or many ERPs - HS and export (ECCN/USML) classification off the Global Trade Content database, restricted-party / Denied Party Screening (DPS) against OFAC SDN, BIS Entity/Denied Persons, EU/UN/UK lists, license determination, FTA / preference and origin qualification (supplier solicitation, rules of origin, certificates), Foreign-Trade Zone (FTZ) management, customs filing (ACE import entry, AES EEI / ITN export), and duty / landed-cost calc. Use when the connected trade system is ONESOURCE Global Trade (or Integration Point) and the work touches a Denied Party Screening / DPS hit, releasing a screening-blocked party or shipment, an ECCN/ITAR or HS/HTS classification, a license determination, an FTA / preference or certificate-of-origin solicitation, an FTZ admission / weekly entry, an ACE entry or AES filing, or the user mentions ONESOURCE, Global Classification, or DPS."
---

# ONESOURCE Global Trade - operating it safely

Thomson Reuters ONESOURCE Global Trade (heritage: **Integration Point**) is a standalone global trade
management platform that layers over one or many ERPs and runs classification, screening, licensing,
preference, FTZ, and customs filing from a single trade system of record. Two things make it different from
every other system in this plugin. First, **it is content-led**: classification, screening list content,
duty, and preference rules all draw on the Thomson Reuters **Global Trade Content** database, versioned and
effective-dated across 180+ countries. A stale content version silently mis-classifies, mis-screens, or
mis-prices. Second, **a screening block and a customs transmission are legal acts, not data edits**:
releasing a party or shipment that failed Denied Party Screening is an export-control decision, and filing an
AES EEI or ACE entry is a legal declaration to the authority. A wrong release is an OFAC / EAR / ITAR
violation; a false customs declaration is an offense under 19 USC 1592 (penalties scaled by culpability, up
to the domestic value of the goods). This skill gives the judgment to classify ONESOURCE actions so the
harness gates them, plus the edge states and the reason certain actions never auto-clear.

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

## Read this first (constraints for any filing, release, or clearance)
- **HARD GATE - a screening-blocked party or shipment is released, and a customs declaration is transmitted,
  only by the named, authorized compliance/trade officer or licensed broker**, with a written rationale and
  retained evidence. The agent proposes and prepares; it does not release or transmit. A ship date, a truck
  at the border, or a VP asking is not authorization.
- **Controlled items never auto-clear.** Anything classified ITAR/USML or EAR-controlled (an ECCN on the CCL
  needing a license) routes to a human licensing officer. The agent never auto-assigns a license, never
  clears a legal-control block, never proposes a control downgrade.
- **Denied Party Screening (DPS) fuzzy hits are always human-adjudicated.** A low match score is not
  permission to clear; a denied party rarely uses the exact listed spelling. ONESOURCE runs the screen; the
  decision on a government-list hit is a human's.
- **Fail closed.** If ONESOURCE, an ERP feed, a customs authority, or a content/list update is unavailable,
  treat the document as blocked and do not transmit or clear blind. If **any single required government list**
  is unavailable for a party, that party's screen is incomplete - block it, do not clear on the lists that did
  run. An incomplete check or an unconfirmed transmission is a block, not a pass.
- **Content freshness is a compliance control.** Classification, screening, duty, and preference are only as
  right as the **content version** behind them. Re-read the content/list version at execute; a rate, control,
  or list current last week can be superseded. Never classify, screen, or price against an expired version.
- **When classification is uncertain, classify up** (stricter export control, higher-duty HS) and route to a
  human; never resolve doubt toward the code that lets goods clear cheaper or faster.
- **Egress is tight.** Party names, screening lists, adjudication notes, ECCNs, HS codes, license data, and
  declaration content are export-control and customs records. Do not send them to external tools or
  unapproved endpoints.

## When this applies
Connector is ONESOURCE Global Trade (or Integration Point) and the work is classification, screening,
licensing, preference, FTZ, customs filing, or landed cost. When NOT:
- ERP-embedded compliance that blocks the sales order/delivery inside SAP -> `sap-gts`
- Descartes GLN customs/manifest filing and Visual Compliance / MK screening -> `descartes`
- e2open's network-based Global Trade Management -> `e2open-gts`
- the ERP order/PO/customer master behind the shipment (pricing, credit, the order itself) -> `sap-mm` (or the ERP's own skill)
- warehouse pick/pack/ship execution -> the WMS skill (`sap-ewm`, `manhattan-wms`)
- freight visibility / real-time tracking -> `project44` or `fourkites`
- transactional/indirect **tax** determination (VAT/GST/sales tax) -> ONESOURCE Determination / Indirect Tax, a separate ONESOURCE product, not this trade module (a VAT/GST question on a ONESOURCE system belongs there, not here)

ONESOURCE often runs alongside an ERP-embedded control (SAP GTS) or a separate filing agent (Descartes).
When two trade systems disagree, the **stricter status governs** - an ERP-side release does not override a
live ONESOURCE screening block, and a ONESOURCE clearance does not override an ERP legal-control block.
Operationally: keep the block in both systems and escalate to the compliance officer for the one holding the
stricter status; do not clear either side to make the two agree.

## Object & state model (reason about state, not nouns)
- **Trade transaction / compliance document** - the ONESOURCE mirror of a feeder ERP document (order,
  delivery, shipment, PO). States: **not checked -> checked-OK -> blocked (hold) -> released**. A block feeds
  back to the ERP integration and can hold delivery, goods issue, and billing. Released means a human
  overrode the hold on record. The only path into **released** is the named authorized officer with a written
  rationale and retained evidence - there is no other transition to released.
- **Classification** - the product's assigned codes, sourced from Global Trade Content. States: **proposed
  (draft) -> confirmed**. Two separate schemes live here: the **HS / HTS** code (customs duty, admissibility)
  and the **ECCN / control class / USML category** (export control). Confirmed is the code every future check
  uses. A right HS with a wrong ECCN still ships illegally. See `references/classification-content.md`.
- **Screening result (DPS)** - a party-vs-list comparison. A **hit** has states: **potential (alert) ->
  reviewed -> cleared (recorded false positive) / confirmed (true match, blocked)**. Cleared is an audited
  decision attributed to the reviewer. See `references/screening.md`.
- **License** - authorization for a controlled export. States: **required (determined) -> assigned ->
  depleted**. Each use draws down remaining value/quantity; an expired or exhausted license blocks the next
  shipment.
- **FTA / preference qualification** - whether a product qualifies for preferential origin under an agreement
  (USMCA, EU FTAs, etc.). States: **not solicited -> solicited (supplier declaration requested) -> received ->
  qualified / not-qualified -> certificate issued**. Rests on valid supplier declarations + BOM rules of
  origin. See `references/preference-ftz-customs.md`.
- **FTZ inventory** - goods admitted into a Foreign-Trade Zone. Each unit carries a **zone status**
  (privileged foreign / non-privileged foreign / domestic / zone-restricted) fixed at admission that governs
  the duty owed at withdrawal. States: **admitted (e-214) -> in zone -> withdrawn (consumption entry) or
  transferred / exported**. See `references/preference-ftz-customs.md`.
- **Content version** - the effective-dated Global Trade Content and screening-list version a check ran
  against. Not a noun to ignore: a check is only valid for the version behind it.

## Vocabulary that bites
- **Global Trade Content** - the Thomson Reuters content database (HS/HTS, export controls, duty rates,
  regulations, sanctioned-party list data) that classification, screening, duty, and preference draw on.
  Effective-dated and versioned; the platform's accuracy is the content's accuracy.
- **Denied Party Screening (DPS)** - ONESOURCE's restricted/denied-party screening service (real-time and
  batch) that compares business partners against government and commercial lists. A hit blocks the party and
  the transaction.
- **Exact vs fuzzy match** - screening runs exact AND fuzzy (phonetic / edit-distance / transliteration)
  matching above a configured similarity threshold to catch misspellings and aliases. A fuzzy hit is a
  *potential* true match needing human review, not noise.
- **ECCN** - Export Control Classification Number (EAR / Commerce Control List); decides whether a license is
  required by destination and end use. **EAR99** is the residual bucket - still EAR-controlled, not license-free.
- **ITAR / USML** - defense articles on the US Munitions List, State/DDTC controlled. Strictest tier; licenses are DDTC-issued and these items never auto-clear.
- **Legal / export control** - the determination of license requirement per transaction (product + destination + end use + party), not a per-product flag.
- **License determination / management** - assigning a license to a transaction and drawing down (depleting) its remaining value/quantity; managing expiry and conditions.
- **FTA / preference** - free-trade-agreement preferential-origin treatment (USMCA, EU FTAs) that lowers duty when rules of origin are met.
- **Rules of origin** - the tests a product must pass to be "originating": a **tariff shift** (change in tariff classification of non-originating inputs) and/or **regional value content (RVC)** threshold; **preference de minimis** allows a small % of non-originating material. This is a different de minimis from the EAR one.
- **Supplier solicitation** - the campaign that requests **long-term supplier declarations / certificates of origin** from vendors, the evidence a preference claim rests on. No valid declaration = no supported claim.
- **FTZ (Foreign-Trade Zone)** - a US secure area treated as outside customs territory for duty; goods are **admitted** on a CBP e-214, held with a **zone status**, and duty is paid only at **withdrawal** via a **weekly entry**.
- **Zone status** - privileged foreign (PF, duty rate locked at admission), non-privileged foreign (NPF, rate set at withdrawal), domestic, or zone-restricted (export/destroy only). Fixed at admission; it decides the duty owed later.
- **ACE** - US CBP's Automated Commercial Environment; the channel for import entries. Transmitting to ACE is a filing to CBP.
- **AES / EEI / ITN** - Automated Export System; the Electronic Export Information filing returns an Internal Transaction Number that must appear on export docs. Filing EEI is a legal export declaration.
- **Landed cost** - product value + freight + insurance + duty + tariffs (incl. Section 301/232) + fees; an estimate until the entry liquidates.
- **Good-guy list** (a.k.a. whitelist) - parties previously cleared; future hits are suppressed. A reviewed control decision, not a way to silence repeat alerts.
- **Deemed export** - releasing controlled technology/technical data to a foreign national, counted as an export to that person's country even with no shipment.

## Operations: read / write / destructive
Classify every operation family by what it does to state and to legal exposure. No tool names - kinds of action.

| Class | ONESOURCE Global Trade operation families | Gate | Why |
|---|---|---|---|
| **Read** | display a classification (HS/ECCN/USML); display a DPS hit, match score, and list version; look up HS / ECCN / duty / control content and its effective date; display a license and remaining value; display a landed-cost estimate; display an FTA/preference qualification result or solicitation status; display FTZ inventory and zone status; display the blocked-document/hold worklist and audit trail; **validate** a draft entry or **simulate** a screening run (no transmit, no persisted result) | always pass | no state change; read the status, block reason, content version, and prior calls before acting |
| **Write (reversible)** | create/edit a **draft** entry, EEI, or FTZ admission before transmission; propose an HS or ECCN classification (unconfirmed); build a landed-cost quote; **initiate a supplier solicitation** (requests a declaration; commits nothing on the shipment); edit a screening adjudication before saving | gate each action individually | a draft/request; nothing is filed and no check has run on it; low blast radius |
| **Write (committing)** | confirm a routine HS/ECCN classification (commits the code future checks use); clear a **low-weight commercial/internal watch-list fuzzy hit within threshold** (never a government list) by an authorized reviewer, with retained evidence; record a **routine EAR99 / NLR** legal-control determination (commits that no license is required for future checks - there is nothing to assign or deplete; note NLR on a **CCL-listed** ECCN is not EAR99 - the item IS controlled, just not for this lane - so escalate it rather than treat it as routine); submit a **PGA** (FDA/USDA/EPA...) message set inside an entry; deplete an already-assigned, valid license within its terms (draws down remaining value/quantity); qualify a product for preference **and issue a certificate of origin** off valid supplier declarations; **admit goods into an FTZ (e-214)** and set zone status; **transmit an ACE import entry**; **file an AES EEI (returns an ITN)**; **file the FTZ weekly entry**; add a party with **no open hit** to the good-guy list (needs periodic revalidation, triggers an immediate re-screen) | gate + human approve | files with an authority, binds future screening/duty/origin, issues a certificate relied on downstream, or suppresses a party's future hits; bounded but real, legally attributable, evidence-logged |
| **Destructive / irreversible** | **release a party or shipment that failed DPS**; **clear or override a denied-party hit on a government list** (SDN, BIS Entity/Denied Persons/Unverified, EU/UN/UK); **auto-clear or downgrade a controlled item** (ITAR/USML, EAR CCL); **assign a license to a controlled item** (the licensing officer's call, not the agent's); **suppress or bypass a PGA hold**; **change/downgrade an already-confirmed classification** (re-prices duty and re-runs export control on future filings); **issue a certificate of origin without valid supplier declarations** (a customs false statement); **amend or cancel a transmitted entry / EEI / weekly entry** (a correction on the record); add a party with an open or true-match hit to the good-guy list; file a knowingly false or undervalued declaration; split/undervalue/re-route to slip under a license, duty, or reporting threshold | HARD GATE + named compliance officer / broker + evidence + re-read | a legal filing or export-control decision; permanent authority record; a wrong call is a violation, not a typo |

**"Low-weight watch list" means** an internal or commercial adverse-media/watch list, **never a government
denial or warning list**. SDN, EU/UN/UK consolidated, BIS Entity/Denied Persons/Unverified are all
human-adjudicated; a fuzzy hit on any of them is never cleared as a routine committing action.

**Reclassification rule (read this):** changing an already-confirmed classification is not a benign edit - it
re-prices duty and re-runs export control on in-flight and future documents, and can auto-release existing
blocks; downgrading a control class is a legal-control decision. Treat any control-class or duty-affecting HS
change as its destructive row above.

Universal rules to teach: read the status, block reason, match score, list/content version, and prior
adjudication before any transmit or clearance, and **re-read at execute** (lists, classifications, and content
drift); never bypass a screening block or split/re-route/re-value a shipment to dodge a threshold, duty, or
embargo; a block or hold means stop; the ultimate destination and end user govern, not the routing; a
transmission is confirmed only when the authority returns acceptance - a reject means nothing was filed.
**Volume does not lower the class:** a batch re-screen or a mass classification proposal is the same
read/write/destructive judgment applied per record, not one lower-risk bulk action - a 10,000-record batch
that auto-clears hits is 10,000 destructive decisions.

### Screening hit - adjudication decision
The one transition an agent gets asked to make. Where the hit lands decides who may act.

| Hit signal | What to do | Class |
|---|---|---|
| Exact match on any government denied-party list | keep blocked; confirm; escalate to the compliance officer | release = destructive |
| Fuzzy hit on any government list (SDN, BIS Entity/Denied Persons/Unverified, EU/UN/UK) | human adjudication only; the agent prepares the case, never clears | release = destructive |
| Fuzzy hit below threshold on a low-weight commercial/internal watch list (not a government list) | an authorized reviewer may clear as false positive, with retained evidence | committing |
| Party already on the good-guy list, entry current | passes screening; verify the entry is still valid | read |

## Gotchas that bite (the real set - causal chains)
1. **The platform is only as right as its content version.** Global Trade Content is effective-dated; a duty rate, control, or list current last quarter can be superseded, so classifying/screening/pricing against a stale version silently mis-declares or misses a new control. Re-read the version at execute. `references/classification-content.md`.
2. **A DPS hit must not auto-clear.** Releasing a party or shipment that failed screening is an export-control decision; a fuzzy hit is a potential true match, since denied parties use aliases and transliterations. A low match score is not safety.
3. **Screening re-runs on list updates and at many touchpoints** (new party, order, batch re-screen). A previously clean party can newly hit an in-flight shipment; a "no-hit" is only as fresh as the last run and the list version behind it.
4. **DPS screens every party, role, and address independently** - sold-to, ship-to, bill-to, end user, forwarder, contacts. Clearing the sold-to does not clear the ship-to or the end user. `references/screening.md`.
5. **ECCN drives license determination, so a wrong or downgraded ECCN passes legal control and ships a controlled item without a license.** Misclassification is the most common root cause of an export violation.
6. **EAR99 is not "uncontrolled."** It still cannot go to an embargoed destination, a denied party, or a prohibited end use (WMD, certain military). Treating EAR99 as license-free ignores the checks that still apply.
7. **ITAR/USML items are State/DDTC controlled and never auto-clear.** No classification proposal or clearance the agent makes releases a USML legal-control block.
8. **A confirmed classification commits the code every future check uses.** A wrong confirmed ECCN or HS silently mis-screens and mis-declares each future order for that product until someone reclassifies.
9. **HS/HTS is not the ECCN.** A correct customs HS code for duty says nothing about export control; the two schemes are maintained separately, and a right HS with a wrong ECCN still ships a controlled item illegally.
10. **Preference rests on valid supplier declarations, not on the duty saving looking routine.** Issuing a certificate of origin without the underlying long-term supplier declarations and a passing BOM rule-of-origin test is a customs false statement, penalized on audit even when the goods truly qualify. `references/preference-ftz-customs.md`.
11. **Two different de minimis rules live here.** Preference de minimis (a small % of non-originating material still allows origin) is not EAR de minimis (US-controlled content in a foreign item keeps it under EAR). Applying one where the other belongs mis-qualifies origin or misses US jurisdiction.
12. **A supplier declaration is dated content that expires.** A long-term declaration covers a stated period; claiming preference on an expired or superseded declaration is an unsupported claim. Solicitation status is not the same as a valid received declaration.
13. **FTZ zone status is fixed at admission and decides the duty later.** Privileged foreign locks the rate at admission; non-privileged foreign is rated at withdrawal. Admitting under the wrong status mis-computes the duty owed on the weekly entry, and status cannot be casually re-elected after admission.
14. **The FTZ weekly entry is a customs filing.** Duty is paid at withdrawal via the weekly entry to CBP; a missed, wrong, or late weekly entry is a filing error with the authority, not an internal inventory note.
15. **Admitting goods into a zone does not screen or classify them.** FTZ admission defers duty; it does not clear export controls, denied-party screening, or PGA requirements, which still apply at admission and withdrawal.
16. **Transmitting an ACE entry is a legal filing to CBP, not a save.** Once transmitted it is on the record; correcting it is a Post-Summary Correction (before liquidation) or protest (after), each a new filing. `references/preference-ftz-customs.md`.
17. **An AES EEI returns an ITN that goes on the export paperwork.** Filing it is a legal export declaration; canceling after export leaves the record and can flag the shipment.
18. **Landed cost is an estimate until liquidation.** CBP's final duty (up to ~314 days later) can differ via reclassification or AD/CVD; treating the quote as final understates the liability.
19. **Country of origin governs duty, AD/CVD, and preference - not the port of export.** Routing goods through a third country does not change origin; a wrong origin claim is a false statement.
20. **A good-guy list entry suppresses future hits for that party.** Add a party that later becomes a true match and the system silently ships to a denied party; an entry is a reviewed control decision needing periodic revalidation.
21. **A screening clear is legally attributable once recorded.** "Cleared as false positive" is an audited decision tied to the reviewer; a wrong clear is treated on audit as a knowing violation.
22. **Deemed export: releasing controlled technology to a foreign national is an export** even with no goods moved; a "nothing shipped" transaction can still require a license.

(More per-topic detail: `references/screening.md`, `references/classification-content.md`, `references/preference-ftz-customs.md`.)

## Edge states & special cases
Each breaks naive "party looks fine, part looks fine, ship it" logic - key rule inline, full behavior in references.
- **Content version drift** - an effective-dated content or list update re-values duty, changes a control, or re-blocks a previously clean party. Re-read the version at execute, not just at order entry. If an update lands between a clear and export (a new SDN listing now hits an already-cleared party, or a control changes on a confirmed part), re-block, stop the shipment, and route to adjudication - a prior clear does not survive a list/content version that now hits. `references/classification-content.md`.
- **Delta / periodic re-screening** - list updates re-block in-flight, previously clean parties. `references/screening.md`.
- **Multiple roles/addresses per party** - each screens independently; a clear on one role is not a clear on all.
- **Preference qualification vs solicitation** - "solicited" is not "received," and "received" is not "still valid." A qualification and any issued certificate are only as good as the current supplier declarations and BOM behind them. `references/preference-ftz-customs.md`.
- **FTZ zone status** - PF vs NPF vs domestic vs zone-restricted decides duty at withdrawal and export/destroy-only handling; set at admission, not freely changed. `references/preference-ftz-customs.md`.
- **License near-exhaustion / partial depletion** - remaining value/quantity can cover part of a shipment; a partial-cover assignment blocks the balance (correct behavior, not a failure to fix).
- **Deemed export / re-export / EAR de minimis** - releasing controlled tech to a foreign national is an export with no goods moved; a US-origin or > EAR-de-minimis US-content item stays under EAR between two foreign countries. `references/classification-content.md`.
- **Good-guy list staleness** - a cleared party can later be listed; a stale good-guy list entry is a live compliance hole.
- **PGA hold independent of CBP release** - a Partner Government Agency hold (FDA, USDA, EPA, FWS...) can block cargo even after CBP releases the entry; clearing customs does not clear a PGA hold, and it carries its own penalty regime. `references/preference-ftz-customs.md`.
- **Multi-ERP / multi-authority feed** - ONESOURCE can consolidate several ERPs and file to several authorities; a clean US filing is not a clean EU one, and a hold from one feed still governs the shipment.
- **Jurisdiction scope** - the US channels named here (ACE, AES/EEI, e-214, weekly entry, 19 USC 1592) are one country's specifics on a 180+ country platform. A transmission to any authority (EU customs, UK HMRC, and others) carries equal legal weight under local law; the same "transmission = legal filing, confirm on acceptance, fail closed" rules apply to every jurisdiction, not only the US.

## Recovery patterns (can it be undone, and what can't)
- **A release cannot recall a shipment.** Once the goods export against a released document, the export happened; re-blocking stops future processing but does not un-ship. A wrong release is a reportable event, not a fixable edit.
- **A transmitted entry is corrected by a PSC (before liquidation) or a protest (after)** - each a new filing on the record, not an edit; after the protest window the assessment stands.
- **A filed AES EEI is corrected by a replacement or cancellation filing.** After export the record persists; you cannot un-declare a shipment that already left.
- **A confirmed classification is corrected by a new classification version**, applied going forward; historic documents keep the code they screened/filed with.
- **A depleted license value is restored only by reversing the assignment** (itself a controlled action), not by editing the remaining value.
- **An issued certificate of origin cannot be un-issued once relied on downstream** - it is corrected/withdrawn on the record, and a claim already filed is corrected via the customs channel; the false-statement exposure remains.
- **An FTZ admission under the wrong zone status** is corrected on the record before withdrawal where the program allows; once withdrawn on a weekly entry the duty computation stands and is corrected via the customs channel (PSC/protest), not an inventory edit.
- **A wrongly-cleared screening hit cannot be unseen.** Re-block the party, retain the evidence (list version, score, reviewer, rationale, timestamp), and escalate to the compliance officer at once - a known violation is a reportable event and the disclosure clock starts at discovery. The disclosure runs to the agency that owns the violated control, and each agency requires its own separate voluntary self-disclosure - not one combined filing: an EAR/BIS-list violation -> BIS (prompt initial notification, with the full voluntary self-disclosure to follow within its window); an OFAC sanctions violation -> OFAC (its own prompt filing); an ITAR/USML violation -> DDTC (its own prompt filing). Re-blocking is not remediation, and whether to disclose is the officer's legal call, not the agent's.

## Guardrails
- Read the status, block reason, match score, list/content version, HS/ECCN, license state, preference/certificate basis, FTZ zone status, and prior adjudication before proposing any transmit or clearance; re-read at execute because lists, classifications, and content drift.
- Never release a screening-blocked party/shipment or transmit a customs declaration without the named, authorized compliance officer or licensed broker, a written rationale, and retained evidence. The agent prepares the case; the human files or releases.
- Controlled items (ITAR/USML, EAR CCL) never auto-clear; denied-party fuzzy hits are always human-adjudicated; embargoes and controls are governed by ultimate destination and end user.
- Never issue a certificate of origin without valid supplier declarations and a passing rule-of-origin test; never split, re-route, or re-value a shipment to slip under a license, duty, or reporting threshold.
- Adding a party to the good-guy list includes its immediate re-screen: if that re-screen hits, remove the party and adjudicate the hit - never leave a hitting party on the list.
- Confirm a transmission only on the authority's acceptance; treat a reject or an unconfirmed send as not filed, and fail closed if ONESOURCE, a feed, an authority, or a content/list update is unavailable.
- Keep egress tight: screening data, party lists, classifications, HS/ECCN codes, license and declaration data are export-control and customs records; do not send them to unapproved tools.
- Keep the evidence trail: for any filing, clearance, release, or certificate, retain the list/content version, score, reviewer, rationale, and timestamp - and retain for the applicable record-keeping period (EAR and ITAR require 5 years; customs record retention varies by jurisdiction, commonly 5 years). Do not discard evidence once briefly logged.

## References (load on demand)
- `references/screening.md` - load when handling any DPS/denied-party hit: exact vs fuzzy matching, government vs commercial list coverage, match scoring and thresholds, real-time vs batch screening and re-screening, hit states, party roles/addresses, the good-guy list, block feedback to the ERP and the release decision.
- `references/classification-content.md` - load when classifying a product, reading trade content, or determining a license: the Global Trade Content database and effective/expiration dates, HS/HTS vs ECCN/USML schemes, control classes, EAR99, ITAR, license determination and depletion, deemed export / re-export / EAR de minimis.
- `references/preference-ftz-customs.md` - load when qualifying preference, running a supplier solicitation, managing an FTZ, or filing/amending a declaration: rules of origin (tariff shift, RVC, preference de minimis), long-term supplier declarations and certificate issuance, FTZ admission/zone status/weekly entry, ACE import entry and AES EEI/ITN, transmission statuses, liquidation/PSC/protest, AD/CVD, duty and landed-cost build-up.
