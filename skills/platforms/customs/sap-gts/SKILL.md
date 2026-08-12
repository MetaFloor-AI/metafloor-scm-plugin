---
name: sap-gts
description: "SAP GTS (Global Trade Services / GTS edition for HANA) - the safe operation of export and import trade compliance: HS and ECCN/USML classification, Sanctioned Party List (SPL) / denied-party screening with exact and fuzzy name matching (OFAC SDN, BIS Entity/Denied Persons, EU/UN/UK lists), embargo and legal-control checks, export license determination and depletion, blocked trade/customs documents, customs declarations, and preference/origin determination. Use when the connected trade system is SAP GTS and the work touches a compliance block, an SPL or SDN hit, releasing a blocked sales order or delivery, an ECCN/ITAR/EAR classification, license determination, an embargo or legal-control check, a customs declaration, or preference/origin, or the user mentions GTS, SPL screening, denied party, sanctioned party list, good-guy list, control class, EAR99, USML, deemed export, de-minimis, or a blocked export document."
---

# SAP GTS - operating it safely

SAP Global Trade Services is the export/import compliance layer between the ERP and the physical shipment. A
sales order or delivery is created in the feeder ERP, transferred to GTS, and screened by three compliance
services (Sanctioned Party List, Embargo, Legal Control) plus customs and preference. The thing that makes GTS
different from every other system in this plugin: **a GTS block is a legal control, and releasing a blocked
document is an export-control decision, not a data fix.** A wrong release is a violation of OFAC / EAR / ITAR
law with civil penalties over $300,000 per violation (the statutory maximum is adjusted annually for inflation)
or twice the transaction value, whichever is greater, and criminal penalties up to $1,000,000 and 20 years. This skill gives the judgment to classify GTS actions so the harness gates them,
plus the edge states and the reason certain actions can never be automated.

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

## Read this first (constraints for any release or clearance)
- **HARD GATE - a compliance-blocked document is released only by the named, authorized compliance/trade
  officer**, with a written adjudication rationale and retained evidence. The agent proposes and prepares; it
  does not release. A ship date, a waiting truck, or a VP asking is not authorization.
- **Controlled parts never auto-clear.** Anything classified ITAR/USML or EAR-controlled (an ECCN on the CCL
  that needs a license) routes to a human licensing officer. The agent never auto-assigns a license, never
  clears a legal-control block, and never proposes a downgrade of a control classification.
- **Sanctions (SDN and other denied-party) fuzzy hits are always human-adjudicated.** A low similarity score is
  not permission to clear; a denied party rarely uses the exact listed spelling.
- **Fail closed.** If GTS or a screening list is unavailable, treat the document as blocked. No shipment
  proceeds without a completed compliance check, even where the feeder ERP could be configured to release on a
  GTS timeout. An incomplete check is a block, not a pass.
- **When classification is uncertain, classify up.** If it is unclear whether an item is ITAR/USML vs
  EAR-controlled, or EAR-controlled vs EAR99, default to the stricter control and route to a human; never
  resolve the doubt toward the lower control to let a shipment clear.
- **Egress is tight.** Party names, screening lists, adjudication notes, ECCNs, and license data are
  export-control records. Do not send them to external tools or unapproved endpoints.

## When this applies
Connector is SAP GTS and the work is trade compliance, classification, screening, licensing, customs, or
preference. When NOT:
- the ERP order/customer/vendor master behind the screen (pricing, credit, the sales order itself) -> `sap-mm` (or the ERP's own skill)
- warehouse pick/pack/ship execution -> the WMS skill (`sap-ewm`, `manhattan-wms`)
- a different trade/customs system (Descartes, e2open, OneSource) -> that vendor's own skill

## Object & state model (reason about state, not nouns)
- **Customs / compliance document** - the GTS mirror of the feeder document (order, delivery, PO). States:
  **not checked -> checked-OK (green) -> blocked (red) -> released**. A block propagates back to the ERP and
  stops delivery, goods issue, and billing. Released means a human overrode the block on record.
- **Classification** - the product's assigned codes. States: **proposed (draft) -> confirmed**. Confirmed is
  the code that drives every future check. Two separate schemes live here: the **HS / commodity code** (customs
  duty) and the **ECCN / control class / USML category** (export control). They are not interchangeable.
- **Screening result (SPL)** - a partner-vs-list comparison. A **hit** has states: **potential (blocked) ->
  released (recorded false positive) -> confirmed (true match)**. Cleared means released as a false positive,
  and that decision is auditable and attributed to the releaser.
- **License** - the authorization for a controlled transaction. States: **required (determined) -> assigned ->
  depleted**. Each use draws down remaining value/quantity; an expired or exhausted license blocks the next
  shipment.
- **Legal regulation** - the active rule framework (US EAR, US ITAR, EU Dual-Use, national embargo lists). Each
  regulation activates its own checks; a product/lane can be free under one and blocked under another.

## Vocabulary that bites
- **SPL / SDN** - Sanctioned Party List screening compares business partners against denied-party lists (OFAC
  **SDN**, BIS Entity List, BIS Denied Persons List, EU/UN/UK consolidated). A match blocks the partner and the document.
- **Exact vs fuzzy match** - screening runs exact AND fuzzy (phonetic/similarity) matching above a configured
  threshold to catch misspellings and transliterations. A fuzzy hit is a *potential* match needing human review, not noise.
- **ECCN** - Export Control Classification Number (EAR / Commerce Control List). Decides whether a license is
  required by destination and end use. **EAR99** is the residual bucket: still EAR-controlled, not license-free.
- **ITAR / USML** - defense articles on the US Munitions List, State Dept (DDTC) controlled. Strictest tier;
  licenses are DDTC-issued and these items never auto-clear.
- **Legal control** - the GTS service that determines and enforces license requirements per transaction.
- **Embargo check** - blocks documents to sanctioned countries/regions (including sub-regions like Crimea); keyed on destination and consignee.
- **Control class** - the GTS grouping an ECCN/USML code maps to; drives which legal-control check fires.
- **Blocked document** - a compliance failure that halts the ERP document downstream, not a GTS-only flag.
- **Good-guy list (white list)** - partners previously cleared; future hits are suppressed for them. A control decision, not a convenience.
- **License determination / depletion** - assigning a license to a transaction and drawing down its remaining value/quantity.
- **Compliance check** - the combined SPL + embargo + legal-control run against a document.
- **Preference** - free-trade-agreement preferential-origin determination (USMCA, EU FTAs), based on rules of origin and vendor declarations.
- **Deemed export** - releasing controlled technology to a foreign national, counted as an export to that person's country even with no shipment.

## Operations: read / write / destructive
Classify every operation family by what it does to state and to legal exposure. No tool names - kinds of action.

| Class | SAP GTS operation families | Gate | Why |
|---|---|---|---|
| **Read** | display a classification (HS/ECCN/USML); display an SPL screening result / hit detail / similarity score; display the blocked-document worklist; display embargo & legal-control status; display a license and its remaining value; display the adjudication/audit trail; simulate a compliance check (runs the checks without persisting results or changing document status) | always pass | no state change; read the block reason and prior calls before acting |
| **Write (reversible)** | propose a classification (HS or ECCN draft, unconfirmed); edit a screening/adjudication record before saving; maintain a draft license request | gate each action individually | a draft/request; no check runs on it yet; low blast radius |
| **Write (committing)** | confirm a routine classification (commits the code all future checks use); clear a **low-risk fuzzy hit within threshold on a low-weight watch list only** (an internal or commercial adverse-media/watch list, **never a government denial or warning list**) by an authorized reviewer; assign/determine a license and deplete it (a partial-cover assignment that blocks the balance is correct system behavior, not a failure to fix); submit a customs declaration; add a partner **with no open hit** to the good-guy list | gate + human approve | binds future screening/licensing or files with the authority; bounded but real |
| **Destructive / irreversible** | **release a document blocked by SPL, embargo, or legal control**; **clear a fuzzy SDN, EU/UN/UK, or BIS Entity/Denied Persons/Unverified match**; **auto-clear or downgrade a controlled part (ITAR/USML or EAR CCL)**; **change or downgrade an already-confirmed classification** (re-runs legal control retroactively); override an embargo; confirm a true-match partner as false positive; **add a party with an open or true-match hit to the good-guy list** (silently enables future evasion); amend or cancel a transmitted customs declaration; split/lower a shipment value to slip under a license or reporting threshold | HARD GATE + named compliance officer + evidence + re-read | a legal export-control filing/decision; permanent audited record; a wrong call is a violation, not a typo |

**"Low-weight watch list" means** an internal or commercial adverse-media/watch list, **never a government
denial or warning list**. The SDN, EU/UN/UK consolidated, BIS Entity, BIS Denied Persons, and BIS Unverified
lists are all human-adjudicated; a fuzzy hit on any of them is never cleared as a routine committing action.

**Reclassification rule (read this):** changing an already-confirmed classification is not a benign edit. It
re-runs legal control on in-flight documents and can auto-release blocks; downgrading a control class is a
legal-control decision. Treat any control-class change as destructive (its matrix row is above).

Universal rules to teach: read the block reason, similarity score, list version, and prior adjudication before
any clearance, and re-read at execute (lists and classifications drift); never bypass a compliance block or
split/re-route/re-value a transaction to dodge a threshold or an embargo; a block means stop; the ultimate
destination and consignee govern, not the routing.

### Screening hit - adjudication decision
The one transition an agent gets asked to make. Where the hit lands decides who may act.

| Hit signal | What to do | Class |
|---|---|---|
| Exact match on any denied-party list | keep blocked; confirm; escalate to the compliance officer | release = destructive |
| Fuzzy hit on any government list (SDN, EU/UN/UK, BIS Entity/Denied Persons/Unverified) | human adjudication only; the agent prepares the case, never clears | release = destructive |
| Fuzzy hit below threshold on a low-weight watch list (internal/commercial, not a government list) | an authorized reviewer may clear as false positive, with retained evidence | committing |
| Party already on the good-guy list, entry current | passes screening; verify the entry is still valid | read |

## Gotchas that bite (the real set - causal chains)
1. **A GTS block propagates to the ERP and stops the physical shipment** - delivery, goods issue, and billing are all halted; releasing the block in GTS is what lets the goods leave, so a release is a shipping decision. `references/screening.md`.
2. **A fuzzy SDN hit is a potential true match, not a typo.** A denied party rarely uses the exact listed spelling; clearing a low-similarity sanctions hit without documented adjudication is an export-control decision that can ship to a sanctioned entity.
3. **Lists update constantly, so a green partner can newly block an in-flight order.** Delta/periodic re-screening runs against the new list version; a clean status is only as fresh as the last run and the list version behind it.
4. **Adding a partner to the good-guy list suppresses future hits for that partner.** List a party that later becomes a true match and the system silently ships to a denied party - a good-guy entry is a reviewed control decision, not a way to stop repeat alerts, and it needs periodic revalidation.
5. **ECCN drives license determination, so a wrong or downgraded ECCN passes legal control and ships a controlled item without a license** (the wrong-code hazard; distinct from the forward-commit hazard in #13). Misclassification is the most common root cause of an export violation.
6. **EAR99 is not "uncontrolled."** It still cannot go to an embargoed destination or a denied party; treating EAR99 as license-free ignores the destination and party checks that still apply.
7. **ITAR/USML items are State-Dept controlled and never auto-clear.** The license is DDTC-issued; no classification proposal or clearance the agent makes can release a USML legal-control block.
8. **License determination depletes the license on each use.** Over-depletion or an expired/exhausted license blocks the next shipment; assigning the wrong license depletes the wrong authorization and mis-reports usage.
9. **Embargo is governed by ultimate destination and consignee, not routing.** Shipping through a third country does not remove an embargo; the sub-region matters (Crimea inside Ukraine), and the end user governs.
10. **A screening hit is legally attributable once released.** "Released as false positive" is a recorded, audited decision tied to the releaser; a wrong release is treated on audit as a knowing violation.
11. **SPL screens every party and address/role on the document.** Sold-to, ship-to, bill-to, end user, and contacts screen independently; clearing the sold-to does not clear the ship-to.
12. **Legal control is per-transaction, not a per-product flag.** It combines product (ECCN/control class) + destination + end use + party; a license required for one lane may not be for another, so a prior clean check does not carry over.
13. **Confirming a classification commits the code all future checks use.** A wrong confirmed ECCN silently mis-screens every future order for that product until someone re-classifies it.
14. **HS/commodity code is not the ECCN.** A correct customs HS code for duty says nothing about export control; the two numbering schemes are maintained separately and a right HS code with a wrong ECCN still ships illegally.
15. **A customs declaration is a legal filing.** Once transmitted and accepted by the authority (AES/ACE, ATLAS, NCTS) it is an official record; a correction is a new amendment/cancellation filing, and a false declaration is itself an offense.
16. **Preference (FTA origin) rests on valid long-term vendor declarations and BOM.** Claiming preferential origin without the supporting declarations is a customs false statement, penalized on audit even if the duty saving looks routine.
17. **Reclassifying an already-classified product changes checks retroactively for in-flight documents** and can auto-release existing blocks - which is why a control-class change is a legal-control action, not master-data cleanup.
18. **Deemed export: releasing controlled technology to a foreign national is an export even with no shipment.** A "no goods moved" transaction can still require a license.
19. **De-minimis / re-export: a foreign-made item with more than de-minimis US-controlled content is still subject to EAR.** "Not shipped from the US" does not remove US jurisdiction.
20. **Splitting a shipment or lowering a declared value to slip under a license or reporting threshold is the same violation with extra steps** and is auditable as structuring.

(More per-topic detail: `references/screening.md`, `references/classification-legal-control.md`, `references/customs-preference.md`.)

## Edge states & special cases
Each breaks naive "party looks fine, part looks fine, ship it" logic - key rule inline, full behavior in references.
- **Delta / periodic re-screening** - list updates re-block in-flight, previously-clean documents. Re-read screening status at execute, not just at order entry. `references/screening.md`.
- **Multiple roles/addresses per partner** - each screens independently; a clear on one role is not a clear on all.
- **Good-guy list** - suppresses future hits; a stale entry is a live compliance hole that needs revalidation.
- **License near-exhaustion / partial depletion** - remaining value/quantity can cover part of a shipment; a partial-cover assignment blocks the balance.
- **Deemed export** - releasing controlled technology/technical data to a foreign national is an export even with no goods moving; "nothing shipped" logic misses it. `references/classification-legal-control.md`.
- **Re-export** - a US-origin or US-content item moving between two foreign countries is still under US jurisdiction; "it never left our country" logic misses it.
- **De-minimis** - a foreign-made item with more than the de-minimis US-controlled content stays subject to the EAR; "not made/shipped from the US" logic misses it.
- **Embargo sub-regions** - a partly-embargoed country (specific region/sector) needs the region and end-use, not just the country code.

## Recovery patterns (can it be undone, and what can't)
- **A release cannot recall a shipment.** Once goods issue posts against a released document, the export happened; reversing the release re-blocks future processing but does not un-ship. A wrong release is a reportable event, not a fixable edit.
- **A confirmed classification is corrected by a new classification (version), not an undo.** Historic documents keep the code they screened with; the correction applies going forward.
- **A depleted license value is restored only by reversing the assignment** (itself a controlled action), not by editing the remaining value.
- **A transmitted customs declaration is corrected by an amendment or cancellation filing** with the authority, on the record - never a silent edit.
- **A wrongly-cleared sanctions hit** cannot be "unseen." Re-block the party, retain the evidence, and escalate to the compliance officer immediately: a known violation is a reportable event and the disclosure clock is already running (BIS expects an initial notice within 180 days of discovery; OFAC and DDTC expect prompt disclosure). Re-blocking is not by itself remediation, and deciding not to disclose is a legal call for the officer, not the agent.

## Guardrails
- Read the block reason, similarity score, list version, ECCN/control class, license status, and prior adjudication before proposing any clearance; re-read at execute because lists and classifications drift.
- Never release a compliance-blocked document without the named, authorized compliance officer, a written adjudication rationale, and retained evidence. The agent prepares the case; the officer decides.
- Controlled parts (ITAR/USML, EAR CCL) never auto-clear; sanctions (SDN) fuzzy hits are always human-adjudicated; embargoes are governed by ultimate destination and consignee.
- Never split, re-route, or re-value a transaction to slip under a threshold or around an embargo.
- Keep egress tight: screening data, party lists, classifications, and adjudication notes are export-control records; do not send them off to unapproved tools.
- Keep the evidence trail: for any clearance or release, retain the list version, similarity score, reviewer, rationale, and timestamp, and keep prior screening/adjudication calls for audit.
- If GTS or a list is unavailable, fail closed: treat as blocked and never let a shipment proceed on an incomplete or bypassed check.

## References (load on demand)
- `references/screening.md` - load when handling any SPL/SDN hit or a screening-blocked document: exact vs fuzzy matching, list versions and delta re-screening, hit states, party roles/addresses, the good-guy list, block propagation to the ERP.
- `references/classification-legal-control.md` - load when classifying a product or handling a legal-control/embargo block: HS vs ECCN vs USML schemes, control classes, EAR99, ITAR, license determination and depletion, deemed export / re-export / de-minimis.
- `references/customs-preference.md` - load when filing or amending a customs declaration or determining preference: authorities (AES/ACE, ATLAS, NCTS), commodity codes, preference/origin, long-term vendor declarations, penalty exposure.
