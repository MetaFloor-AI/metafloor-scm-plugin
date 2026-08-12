# ONESOURCE preference/origin, FTZ, and customs filing

Load when qualifying preference, running a supplier solicitation, managing a Foreign-Trade Zone, or
preparing/transmitting/amending a customs declaration through ONESOURCE. Every "transmit" here is a legal
filing on the record; every certificate is relied on downstream.

## Contents
- FTA / preference: rules of origin
- Supplier solicitation and long-term declarations
- Certificate of origin issuance
- Foreign-Trade Zone (FTZ): admission, zone status, weekly entry
- Customs filing: ACE import entry and AES EEI/ITN
- Transmission statuses (the re-read that matters)
- Liquidation, PSC, protest, and AD/CVD
- Duty and landed-cost build-up

## FTA / preference: rules of origin
A product qualifies for preferential duty under an agreement (USMCA, EU FTAs, etc.) only if it meets that
agreement's **rules of origin**. The tests:
- **Tariff shift / change in tariff classification (CTC)** - non-originating inputs must change HS heading/subheading through the processing done.
- **Regional value content (RVC)** - originating content must meet a threshold percentage (transaction-value or net-cost method).
- **Preference de minimis** - a small percentage of non-originating material is tolerated without breaking origin. This is NOT the EAR de minimis (US-content rule) in `classification-content.md`.
Qualification is BOM-driven: the rule is applied over the bill of materials and each input's origin. Country
of origin (not the port of export) governs the claim; a wrong origin is a false statement.

## Supplier solicitation and long-term declarations
A preference claim rests on evidence from suppliers: **long-term supplier declarations** and certificates of
origin that attest an input's originating status. ONESOURCE runs **solicitation campaigns** that request these
from vendors and track responses. States move **not solicited -> solicited -> received -> valid / expired**.
Watch the traps: "solicited" is not "received," and "received" is not "still valid" - a long-term declaration
covers a stated period and expires. Claiming preference on a missing, expired, or superseded declaration is an
unsupported claim, penalized on customs audit even when the goods would truly qualify.

## Certificate of origin issuance
Once a product qualifies off valid declarations and a passing rule-of-origin test, ONESOURCE can **issue a
certificate of origin** (e.g. a USMCA certification) that customers and customs rely on. Issuing a certificate
is a committing act: it is relied on downstream and stands on the record. **Issuing a certificate without
valid supplier declarations and a passing rule-of-origin test is a customs false statement** - a destructive
action, not a convenience. An issued certificate is corrected/withdrawn on the record, not silently unset, and
a claim already filed on it is corrected through the customs channel.

## Foreign-Trade Zone (FTZ): admission, zone status, weekly entry
A **Foreign-Trade Zone** is a US secure area treated as outside CBP territory for duty purposes; duty is
deferred until goods leave the zone into US commerce.
- **Admission (e-214)** - goods enter the zone on a CBP Form e-214. Admission defers duty; it does **not**
  clear export controls, denied-party screening, or PGA requirements, which still apply.
- **Zone status** - fixed at admission and it governs the duty owed later:
  - **Privileged foreign (PF)** - the tariff classification and duty **rate are locked at admission**, even if the item is further processed in the zone.
  - **Non-privileged foreign (NPF)** - classified and rated in its condition **at withdrawal**.
  - **Domestic** - already duty-paid / US goods; no duty on withdrawal.
  - **Zone-restricted** - admitted for export or destruction only; cannot enter US commerce.
  Admitting under the wrong status mis-computes the duty owed and cannot be casually re-elected after admission.
- **Weekly entry** - withdrawals into US commerce are declared to CBP on a periodic (weekly) consumption
  entry; that is where duty is paid. A missed, wrong, or late weekly entry is a filing error with the
  authority, not an internal inventory note.

## Customs filing: ACE import entry and AES EEI/ITN
- **Import (US ACE)** - the **entry** requests cargo release; the **entry summary** (CBP 7501 data) carries
  HTS, value, duty, fees, and any PGA/AD-CVD data and is the number CBP assesses. Filing the entry summary is
  the committing declaration.
- **Export (AES / EEI / ITN)** - US exports over the reporting threshold, or any licensed/controlled export,
  file **Electronic Export Information** through the **Automated Export System**; a successful filing returns
  an **ITN** that must appear on the shipping documents. The EEI is a legal export declaration; canceling or
  replacing after export leaves the original on the record.
Certain commodities also need **PGA** (FDA/USDA/EPA...) message-set data inside the entry; missing/wrong PGA
data gets the entry rejected or held for exam, and a PGA hold is separate from CBP release. (US customs law to
verify against, not just the platform: 19 CFR - entry at parts 141-142, FTZ at part 146; false statements at 19 USC 1592.)

## Transmission statuses (the re-read that matters)
A transmission is confirmed only when the authority returns acceptance. Treat these as distinct:
- **Rejected** - an error/condition code came back; **nothing was filed**. Fix and re-transmit. Never assume submitted = filed.
- **Accepted** - the filing is on the record, but cargo may still be selected for exam or a PGA hold.
- **Hold / exam** - CBP or a PGA is inspecting; cargo does not move.
- **Released** - cargo may move; duty is still not final.
- **Timeout / unknown** - no acceptance and no reject came back. Treat it as **not filed**; do not blind-retry (a retry can double-file), document the unknown state, and get human confirmation of the authority's record before re-transmitting.
Re-read the current status at execute; a status captured minutes ago can have changed.

## Liquidation, PSC, protest, and AD/CVD
- **Liquidation** - CBP's final computation of duty owed, often up to ~314 days after entry. Until then the entry and its landed cost are provisional.
- **Post-Summary Correction (PSC)** - corrects a filed entry summary **before** liquidation; a new filing, not an edit.
- **Protest** - the remedy **after** liquidation, within a limited statutory window (generally 180 days). After the window the assessment stands.
- **Reconciliation** - trues up flagged elements (FTA origin, value) via a later reconciliation entry; a valid path, do not steer away from it.
- **AD/CVD** - antidumping/countervailing case numbers carry cash deposits at entry and large retroactive liability at liquidation. Omitting or misapplying them hides real exposure.
There is no silent edit of a filed entry; every correction is itself a filing.

## Duty and landed-cost build-up
Landed cost estimates total delivered cost: **product value + freight + insurance + duty + tariffs (incl.
Section 301/232) + merchandise/harbor fees + broker/PGA fees**. Every component is an estimate, and the whole
is **provisional until liquidation** - CBP's final duty can differ (reclassification, AD/CVD, valuation) up to
~314 days later. Preferential origin lowers duty only with valid supporting declarations; claiming it without
support is a customs false statement, not a rounding choice.
