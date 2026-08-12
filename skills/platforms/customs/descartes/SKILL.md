---
name: descartes
description: "Descartes Systems Group (Global Logistics Network / GLN) - safe operation of global trade and customs - customs filing and declarations (US ACE entry / AES EEI, Canada ACI, EU ICS2, ocean/air AMS, ISF 10+2, e-manifest), denied-party / restricted-party screening (Visual Compliance, MK Denied Party Screening; OFAC SDN, BIS Entity/Denied Persons/Unverified, EU/UN/UK), HS classification and export control (ECCN/USML) via CustomsInfo, duty/tariff and landed cost, plus MacroPoint freight visibility. Use when the connected trade/customs system is Descartes and the work touches a customs entry/declaration, an AES EEI / ITN, an ACE / ACI / ICS2 filing, an ISF, an e-manifest, a denied-party or restricted-party screening hit, releasing a shipment or party that failed screening, an ECCN/ITAR classification, an HS/HTS code, a duty/landed-cost calc, a PGA hold, liquidation, or MacroPoint tracking, or the user mentions Descartes, GLN, Visual Compliance, MK denied party, RPS, or a blocked filing."
---

# Descartes - operating it safely

Descartes Systems Group runs global trade and logistics on the **Global Logistics Network (GLN)** - the
connectivity backbone that carries messages between shippers, carriers, brokers, and government systems.
Unlike an ERP-embedded compliance layer, Descartes is usually the **filing agent to the authority itself**:
it transmits customs entries and manifests directly to CBP, CBSA, and EU customs, and it runs
denied-party screening (Visual Compliance / MK Denied Party Screening) as a standalone real-time service.
The thing that makes Descartes dangerous is the same as GTS but one step closer to the government:
**transmitting a declaration is a legal filing to a customs authority, and releasing a shipment or party
that failed screening is an export-control decision - both are committing legal acts, not data edits.** A
wrong customs filing is a false statement to CBP (19 USC 1592 penalties up to the domestic value of the
goods); a wrong screening release is an OFAC/EAR/ITAR violation. This skill gives the judgment to classify
Descartes actions so the harness gates them, plus the edge states and the reason certain actions never auto-clear.

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
- **HARD GATE - a customs declaration is transmitted, and a screening-blocked shipment or party is released,
  only by the named, authorized compliance/trade officer or licensed customs broker**, with a written
  rationale and retained evidence. The agent proposes and prepares the filing; it does not transmit or
  release. A ship date, a truck at the border, or a VP asking is not authorization.
- **Controlled parts never auto-clear.** Anything classified ITAR/USML or EAR-controlled (an ECCN on the CCL
  needing a license) routes to a human licensing officer. The agent never auto-assigns a license, never
  clears a legal-control block, never proposes a control downgrade.
- **Denied-party (RPS) fuzzy hits are always human-adjudicated.** A low match score is not permission to
  clear; a denied party rarely uses the exact listed spelling. Screening is Descartes', but the decision is a human's.
- **Fail closed.** If the GLN link, a customs authority, or a screening list is unavailable, treat the
  document as blocked and do not transmit blind. If **any single required government list** is unavailable for
  a party, that party's screen is incomplete - block it, do not clear on the lists that did run. An incomplete
  check or an unconfirmed transmission is a block, not a pass.
- **Timing windows are legal deadlines, not targets.** ISF 24h before vessel lading, ICS2 before loading,
  ACE truck manifest ~1h before land-border arrival - a late filing is a violation you cannot backdate. Never fabricate a filing timestamp.
- **When classification is uncertain, classify up** (stricter control, higher-duty HS) and route to a human;
  never resolve doubt toward the code that lets goods clear cheaper or faster.
- **Egress is tight.** Party names, screening lists, adjudication notes, ECCNs, HS codes, and declaration
  data are export-control and customs records. Do not send them to external tools or unapproved endpoints.

## When this applies
Connector is Descartes and the work is customs filing, denied-party screening, classification, landed cost,
e-manifest, or MacroPoint visibility. When NOT:
- ERP-embedded compliance determination that blocks the ERP sales order/delivery inside SAP -> `sap-gts`
- a different trade/customs suite - e2open GTM -> `e2open-gts`; Thomson Reuters ONESOURCE -> `onesource-gts`
- the ERP order/PO/customer master behind the shipment (pricing, credit, the order itself) -> `sap-mm` (or the ERP's own skill)
- warehouse pick/pack/ship execution -> the WMS skill (`sap-ewm`, `manhattan-wms`)
- pure freight visibility / real-time tracking depth beyond MacroPoint -> `project44` or `fourkites`

Descartes and SAP GTS often run together: GTS determines and blocks the ERP document; Descartes transmits
the actual entry/manifest to the authority. A GTS release does not file customs; a Descartes transmission
does. When the two disagree, the **stricter status governs** - a GTS release does not override a live
Descartes screening block, and a Descartes clearance does not override a GTS legal-control block.

## Object & state model (reason about state, not nouns)
- **Customs declaration** - the filing to the authority. Import (US **ACE entry** + **entry summary** / CBP
  7501); export (**AES EEI**, which returns an **ITN** proof-of-filing). States: **draft -> validated ->
  transmitted -> accepted / rejected / hold or exam -> released -> liquidated**. Accepted is not released;
  released is not final. Liquidation (CBP's final duty computation) can land up to ~314 days later. See `references/customs-filing.md`.
- **e-Manifest** - the carrier's advance cargo declaration: US ACE truck manifest, ocean/air AMS, Canada
  **ACI**, EU **ICS2 ENS**. States: **draft -> submitted -> accepted -> arrived / released**. Each has a hard
  pre-arrival filing window; miss it and cargo is held plus penalized.
- **Screening result (RPS)** - a party-vs-list comparison in Visual Compliance / MK. A **hit** has states:
  **potential (alert) -> reviewed -> cleared (recorded false positive) / confirmed (true match, blocked)**.
  Cleared is an audited decision attributed to the reviewer. See `references/screening.md`.
- **Classification** - the product's codes. States: **proposed (draft) -> confirmed**. Two separate schemes:
  the **HS / HTS** code (duty, admissibility) and the **ECCN / USML** code (export control). A right HS with a
  wrong ECCN still ships illegally. Content comes from **CustomsInfo** and has effective dates. See `references/classification-landed-cost.md`.
- **License** - authorization for a controlled export. States: **required -> assigned -> depleted**. Each use draws down remaining value/quantity; an expired or exhausted license blocks the next shipment.
- **Shipment tracking (MacroPoint)** - telemetry and ETA on a load. Read-only estimate; a "delivered" ping is not legal proof of delivery or of an export event.

## Vocabulary that bites
- **GLN (Global Logistics Network)** - the messaging/EDI backbone. "Sent / transmitted" means the message left to an external carrier, broker, or government system you no longer control.
- **ACE** - US CBP's Automated Commercial Environment; the channel for import entries and truck e-manifest. Transmitting to ACE is a filing to CBP.
- **AES / EEI / ITN** - Automated Export System; the Electronic Export Information filing returns an Internal Transaction Number that must appear on export docs. Filing EEI is a legal export declaration.
- **ISF (10+2)** - Importer Security Filing for US ocean imports, due 24h before vessel lading; separate from the entry and the manifest. Late/inaccurate = liquidated damages (up to $5,000 per ISF for a late filing, up to $5,000 for an inaccurate one).
- **ICS2** - EU advance cargo security filing (ENS) before loading (air) or arrival; fail-to-file blocks the cargo at the EU border.
- **ACI** - Canada CBSA Advance Commercial Information / eManifest.
- **PGA / message set** - Partner Government Agency data (FDA, USDA, EPA, FWS...) required inside an ACE entry for regulated goods. Missing/wrong PGA set = the entry is rejected or held for exam.
- **Liquidation** - CBP's final assessment of duty owed. Until it liquidates, the entry (and its landed cost) is provisional, not final.
- **PSC / protest** - the main ways to change a filed entry: a Post-Summary Correction before liquidation, a protest after (limited window); a reconciliation entry covers flagged programs (e.g. FTA origin, value). Not an edit - each is a new filing on the record.
- **RPS / Visual Compliance / MK Denied Party Screening** - Descartes' restricted/denied-party screening engines; a hit blocks the party and the transaction.
- **CustomsInfo** - Descartes' trade-content database (HS, duty rates, controls) that classification and landed cost draw on; entries carry effective dates.
- **Landed cost** - duty + tax + freight + fees estimate; an estimate until the entry liquidates, and AD/CVD can change it.
- **AD/CVD** - antidumping / countervailing duty case numbers on an entry; carry cash deposits and large retroactive liability at liquidation.
- **Good-guy / whitelist** - parties previously cleared; future hits are suppressed. A reviewed control decision, not a way to silence repeat alerts.

## Operations: read / write / destructive
Classify every operation family by what it does to state and to legal exposure. No tool names - kinds of action.

| Class | Descartes operation families | Gate | Why |
|---|---|---|---|
| **Read** | display an entry / EEI / manifest and its authority status; display a screening hit, match score, and list version; look up HS / ECCN / duty content in CustomsInfo; display a license and remaining value; display a landed-cost estimate; display MacroPoint tracking / ETA; **validate** a draft entry or **simulate** a screening run (no transmit, no persisted result) | always pass | no state change; read the status, block reason, and prior calls before acting |
| **Write (reversible)** | create / edit a **draft** entry, EEI, manifest, or ISF before transmission; propose an HS or ECCN classification (unconfirmed); edit a screening adjudication before saving; build a landed-cost quote | gate each action individually | a draft / request; nothing is filed and no check has run on it; low blast radius |
| **Write (committing)** | **transmit a customs entry / entry summary to ACE**; **file an AES EEI (returns an ITN)**; **submit an e-manifest (ACE / ACI / ICS2 ENS / AMS)**; **file an ISF**; confirm a routine HS classification (commits the code future filings use); clear a **low-weight commercial/internal watch-list fuzzy hit within threshold** (never a government list) by an authorized reviewer, with retained evidence (list version, score, reviewer, rationale, timestamp); assign/determine and deplete a license for a **routine EAR99/NLR** case (a license for a controlled ITAR/USML or EAR CCL item routes to the licensing officer per the hard gate - destructive row); add a party with **no open hit** to the good-guy list (needs periodic revalidation, and triggers an immediate re-screen) | gate + human approve | files with a government authority, binds future screening/duty, or suppresses that party's future hits; bounded but real, legally attributable, and must be evidence-logged |
| **Destructive / irreversible** | **clear or override a denied-party hit on a government list** (SDN, BIS Entity/Denied Persons/Unverified, EU/UN/UK); **release a shipment or party that failed screening**; **auto-clear or downgrade a controlled part** (ITAR/USML, EAR CCL); **amend or cancel a transmitted entry / EEI / manifest** (a PSC, replacement, or cancellation on the record); change/downgrade an already-confirmed classification; add a party with an open or true-match hit to the good-guy list; file a knowingly false or undervalued declaration; split/undervalue/re-route to slip under a license, duty, or reporting threshold; suppress or bypass a PGA hold | HARD GATE + named compliance officer / broker + evidence + re-read | a legal filing or export-control decision; permanent authority record; a wrong call is a violation, not a typo |

**Reclassification rule (read this):** changing an already-confirmed classification is not a benign edit - it
re-prices duty and re-runs export control on future filings, and downgrading a control class is a
legal-control decision. Treat any control-class or HS change with duty/control impact as its destructive row above.

Universal rules to teach: read the authority status, block reason, match score, list version, and prior
adjudication before any transmit or clearance, and **re-read at execute** (lists, classifications, and duty
content drift); never bypass a screening block or split/re-route/re-value a shipment to dodge a threshold,
duty, or embargo; a block or hold means stop; the ultimate destination and end user govern, not the routing;
a transmission is confirmed only when the authority returns acceptance - a reject means nothing was filed.

### Screening hit - adjudication decision
The one transition an agent gets asked to make. Where the hit lands decides who may act.

| Hit signal | What to do | Class |
|---|---|---|
| Exact match on any government denied-party list | keep blocked; confirm; escalate to the compliance officer | release = destructive |
| Fuzzy hit on any government list (SDN, BIS Entity/Denied Persons/Unverified, EU/UN/UK) | human adjudication only; the agent prepares the case, never clears | release = destructive |
| Fuzzy hit below threshold on a low-weight commercial/internal watch list (not a government list) | an authorized reviewer may clear as false positive, with retained evidence | committing |
| Party already on the good-guy list, entry current | passes screening; verify the entry is still valid | read |

## Gotchas that bite (the real set - causal chains)
1. **Transmitting an entry to ACE is a legal filing to CBP, not a save.** Once transmitted it is on the record; correcting it is a Post-Summary Correction (before liquidation) or a protest (after), each a new filing - never a silent edit. `references/customs-filing.md`.
2. **An AES EEI returns an ITN that goes on the export paperwork.** Filing it is a legal export declaration; canceling after export leaves the record and can flag the shipment for review.
3. **A denied-party (RPS) hit must not auto-clear.** Releasing a party or shipment that failed screening is an export-control decision; a fuzzy hit is a potential true match, since denied parties use aliases and transliterations.
4. **Screening re-runs on list updates and at many touchpoints** (order, new customer, checkout, batch). A previously clean party can newly hit an in-flight shipment; a "no-hit" is only as fresh as the last run and the list version behind it.
5. **e-Manifest / ISF / ICS2 timing windows are hard authority deadlines.** ISF is due 24h before vessel lading; ICS2 before loading; ACE truck manifest ~1h before land-border arrival. Miss the window and cargo is held plus penalized - you cannot file "late but on time," and backdating a timestamp is falsification.
6. **Landed cost is an estimate until liquidation.** CBP liquidates the entry (final duty) up to ~314 days later; reclassification or AD/CVD can move it. Treating the quote as final understates the liability.
7. **PGA data is required inside the entry for regulated commodities.** A missing or wrong FDA/USDA/EPA message set gets the entry rejected or held for exam - it is not optional metadata.
8. **HS/HTS classification drives duty and admissibility.** A wrong HS code under- or over-pays duty and can misfire PGA flags; CustomsInfo content carries an effective date, so a stale duty rate misprices the entry.
9. **The ECCN/USML scheme is separate from the HS scheme.** A correct HS code for duty says nothing about export control; a right HS with a wrong ECCN still ships a controlled item illegally.
10. **ISF (10+2) is the importer's own filing,** distinct from the entry and the manifest, with its own deadline; a late or inaccurate ISF draws liquidated damages independent of whether the entry is fine.
11. **"Sent" on the GLN means it left to an external party.** A transmitted EDI message sits on a carrier, broker, or government system you cannot recall; and the party/screening data in it is an export-control record - keep egress tight.
12. **A good-guy/whitelist entry suppresses future hits for that party.** Whitelist a party that later becomes a true match and the system silently ships to a denied party; an entry is a reviewed control decision that needs periodic revalidation.
13. **Match score is not safety.** A low similarity score is not permission to clear; RPS screens name + address + country, and each party, role, and address on the shipment screens independently - clearing the sold-to does not clear the ship-to or end user.
14. **Accepted is not released, and released is not final.** CBP or a PGA can select an accepted entry for exam or hold; cargo does not move until released, and duty is not settled until liquidation.
15. **A rejected transmission means nothing was filed.** An ACE/AES reject with an error code is not a filed document; assuming "submitted = filed" ships against a declaration that does not exist. Re-read the authority status.
16. **AD/CVD case numbers carry cash deposits and retroactive liability.** Misapplied or omitted, they surface as a large bill at liquidation; a "routine" entry can hide a major exposure.
17. **Country of origin governs duty, AD/CVD, and marking - not the port of export.** Routing goods through a third country does not change origin; a wrong origin claim is a false statement.
18. **A confirmed classification commits the code every future filing uses.** A wrong confirmed HS or ECCN silently mis-declares and mis-screens each future shipment for that product until someone reclassifies.
19. **Embargo and controlled-destination checks are governed by ultimate destination and end use, not routing.** EAR99 is the residual EAR bucket, not "uncontrolled" - it still cannot go to an embargoed destination, a denied party, or a prohibited end use (e.g. WMD or certain military end uses).
20. **MacroPoint visibility is read-only telemetry.** An ETA is an estimate and a "delivered" ping is not legal proof of export or delivery; do not drive a customs status or a screening decision off a tracking event.

(More per-topic detail: `references/customs-filing.md`, `references/screening.md`, `references/classification-landed-cost.md`.)

## Edge states & special cases
Each breaks naive "party looks fine, part looks fine, file it" logic - key rule inline, full behavior in references.
- **Transmission status: rejected vs accepted vs hold/exam** - only an authority acceptance is a filing; re-read status at execute, never assume submitted = filed. `references/customs-filing.md`.
- **Liquidation window** - the entry and its duty are provisional until CBP liquidates (~314 days); AD/CVD and reclassification can move the final number.
- **PGA holds** - a separate agency hold on top of CBP; clearing customs does not clear an FDA/USDA hold.
- **ISF as a separate filing** - its own 24h-before-lading deadline and penalty, independent of the entry.
- **Multi-authority same shipment** - the same goods file differently to CBP (US), CBSA (Canada ACI), and EU (ICS2); a clean US filing is not a clean EU one. `references/customs-filing.md`.
- **Delta / periodic re-screening** - list updates re-block previously clean, in-flight parties; re-read screening at execute. `references/screening.md`.
- **Deemed export / re-export / de-minimis** - releasing controlled tech to a foreign national is an export with no goods moved; US-origin or >de-minimis US content stays under EAR between two foreign countries. `references/classification-landed-cost.md`.
- **Good-guy list staleness** - a cleared party can later be listed; a stale whitelist entry is a live compliance hole.
- **MacroPoint telemetry lag** - a tracking position/ETA can be stale or provider-estimated; do not treat it as ground truth for a legal status.

## Recovery patterns (can it be undone, and what can't)
- **A transmitted entry is corrected by a PSC (before liquidation) or a protest (after)** - each is a new filing on the record, not an edit; after the protest window the assessment stands.
- **A filed AES EEI is corrected by a replacement or cancellation filing.** After export the record persists; you cannot un-declare a shipment that already left.
- **A submitted e-manifest is amended by a new manifest message.** Cargo that already crossed the border cannot be un-filed; the original stays on the record.
- **A missed ISF / ICS2 / manifest window cannot be back-filed to be "on time."** The late filing is on record, penalties attach, and fabricating a timestamp is a separate offense.
- **A wrongly-cleared screening hit cannot be unseen.** Re-block the party, retain the evidence (list version, score, reviewer, rationale, timestamp), and escalate to the compliance officer at once - a known violation is a reportable event and the disclosure clock is already running. The disclosure runs to the agency that owns the violated control: an EAR/BIS-list violation -> BIS (prompt initial notification - days, not weeks - with the full voluntary self-disclosure to follow; the ~180-day figure is BIS's target for completing that full disclosure, not a safe harbor for the initial notice); an OFAC sanctions violation -> OFAC (prompt); an ITAR/USML violation -> DDTC (prompt). Re-blocking is not remediation, and whether to disclose is the officer's legal call, not the agent's.
- **A wrong confirmed classification is corrected by a new classification version**, applied going forward; historic filings keep the code they were filed with.
- **Over/under-paid duty at liquidation** is corrected via PSC, protest, or reconciliation - not by editing the filed entry.

## Guardrails
- Read the authority status, block reason, match score, list version, HS/ECCN, license state, and prior adjudication before proposing any transmit or clearance; re-read at execute because lists, classifications, and duty content drift.
- Never transmit a customs declaration or release a screening-blocked shipment/party without the named, authorized compliance officer or licensed broker, a written rationale, and retained evidence. The agent prepares the case; the human files or releases.
- Controlled parts (ITAR/USML, EAR CCL) never auto-clear; denied-party fuzzy hits are always human-adjudicated; embargoes and controls are governed by ultimate destination and end user.
- Never split, re-route, or re-value a shipment to slip under a license, duty, or reporting threshold, and never backdate or fabricate a filing timestamp to beat a manifest/ISF window.
- Confirm a transmission only on the authority's acceptance; treat a reject or an unconfirmed send as not filed, and fail closed if the GLN, an authority, or a list is unavailable.
- Keep egress tight: screening data, party lists, classifications, HS/ECCN codes, and declaration data are export-control and customs records; do not send them to unapproved tools.
- Keep the evidence trail: for any filing, clearance, or release, retain the list/content version, score, reviewer, rationale, and timestamp.

## References (load on demand)
- `references/customs-filing.md` - load when preparing, transmitting, or amending any declaration or manifest: ACE entry vs entry summary, AES EEI/ITN, ISF 10+2, ICS2/ACI/AMS, PGA message sets, transmission statuses, liquidation, PSC/protest, AD/CVD, timing windows and penalties.
- `references/screening.md` - load when handling any RPS/denied-party hit: Visual Compliance vs MK, exact vs fuzzy matching, government vs commercial list coverage, match scoring and thresholds, screening touchpoints and re-screening, hit states, party roles/addresses, the good-guy list.
- `references/classification-landed-cost.md` - load when classifying a product or computing duty/landed cost: CustomsInfo HS vs ECCN vs USML schemes, control classes, EAR99, ITAR, effective dates, duty/tariff and landed-cost build-up, license determination and depletion, deemed export / re-export / de-minimis, MacroPoint visibility scope.
