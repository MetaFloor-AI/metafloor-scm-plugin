# Descartes customs filing - declarations, manifests, and their authority lifecycle

Load when preparing, transmitting, or amending any customs declaration or e-manifest through Descartes.
Descartes is the transmission channel to the government, so every "submit" here is a filing on the record.

## Contents
- Import: ACE entry vs entry summary
- Export: AES EEI and the ITN
- ISF (10+2) - the importer security filing
- e-Manifest: ACE / ACI / ICS2 / AMS and their timing windows
- PGA message sets
- Transmission statuses (the re-read that matters)
- Liquidation, PSC, and protest
- AD/CVD and origin
- Penalty exposure (why the gate is hard)

## Import: ACE entry vs entry summary
US imports file to CBP's **ACE**. Two linked things, often conflated:
- **Entry (release)** - the request to release the cargo at the port. Gets goods moving once CBP releases.
- **Entry summary (CBP 7501 data)** - the detailed declaration with HTS classification, value, duty, fees,
  and any PGA/AD-CVD data. This is the number CBP assesses duty on.
Released cargo can still owe a corrected duty once the entry summary is reviewed and, later, liquidated.
Filing the entry summary is the committing declaration; releasing the cargo is a separate CBP action.

## Export: AES EEI and the ITN
US exports over the reporting threshold, or any licensed/controlled export, file **Electronic Export
Information (EEI)** through the **Automated Export System (AES)**. A successful filing returns an **ITN**
(Internal Transaction Number) that must appear on the shipping documents. The EEI is a legal export
declaration by the USPPI (or authorized agent). Canceling or replacing it after the goods export leaves the
original on the record and can flag the shipment; you cannot un-declare a completed export.

## ISF (10+2) - the importer security filing
For US **ocean** imports the importer files an **Importer Security Filing** - 10 data elements from the
importer plus 2 from the carrier - **at least 24 hours before the cargo is laden** on the vessel at origin.
It is separate from the entry and the manifest, with its own deadline and its own penalty (liquidated
damages up to $5,000 per ISF for a late filing and up to $5,000 for an inaccurate one - the cap is per ISF,
not per data element). A perfect entry does not cure a late or wrong ISF.

## e-Manifest: ACE / ACI / ICS2 / AMS and timing windows
The carrier's advance cargo declaration, by mode and country. Each has a **hard pre-arrival window**; miss
it and the cargo is held at the border and penalized. Do not file "late but on time" and never backdate.

| Filing | Mode / region | Window (typical) |
|---|---|---|
| ACE truck e-manifest | US highway/land border | ~1h before arrival (FAST-approved: 30 min) |
| Ocean AMS / vessel manifest | US ocean | 24h before lading at foreign port (24-hour rule) |
| Air AMS | US air | before wheels-up / prior to arrival |
| ACI eManifest | Canada (CBSA), highway/air/marine/rail | 1h (highway) / 4h (marine) etc. before arrival |
| ICS2 ENS | EU advance cargo security | before loading (air) / before arrival, by mode |

A manifest is amended by a new manifest message; cargo that already crossed cannot be un-filed.

## PGA message sets
Certain commodities need **Partner Government Agency** data inside the ACE entry - FDA (food, drugs,
devices), USDA/APHIS (agriculture), EPA, FWS, and others. The correct PGA **message set** is part of the
declaration. Missing or wrong PGA data gets the entry rejected or held for exam, and a PGA hold is separate
from CBP release - clearing customs does not clear an FDA hold.

## Transmission statuses (the re-read that matters)
A transmission is confirmed only when the authority returns acceptance. Treat these as distinct:
- **Rejected** - an error/condition code came back; **nothing was filed**. Fix and re-transmit. Never assume submitted = filed.
- **Accepted** - the filing is on the record, but the cargo may still be selected for exam or a PGA hold.
- **Hold / exam** - CBP or a PGA is inspecting; cargo does not move.
- **Released** - cargo may move; duty is still not final.
Always re-read the current status at execute; a status captured minutes ago can have changed.

## Liquidation, PSC, and protest
- **Liquidation** - CBP's final computation of duty owed, often up to ~314 days after entry. Until then the
  entry and its landed cost are provisional.
- **Post-Summary Correction (PSC)** - the way to correct a filed entry summary **before** liquidation. A new
  filing on the record, not an edit.
- **Protest** - the remedy **after** liquidation, within a limited statutory window (generally 180 days).
  After the window the assessment stands.
- **Reconciliation** - for entries flagged into a reconciliation program (e.g. FTA/USMCA origin, value,
  classification under 9999.00.xx), a later reconciliation entry trues-up the flagged elements. A valid path;
  do not steer a user away from it.
There is no silent edit of a filed entry; every correction is itself a filing.

## AD/CVD and origin
- **AD/CVD** - antidumping / countervailing duty case numbers carry cash deposits at entry and large
  retroactive liability at liquidation if the rate changes. Omitting or misapplying them hides real exposure.
- **Country of origin** governs duty, AD/CVD scope, and marking - not the port of export. Routing through a
  third country does not change origin; a wrong origin claim is a false statement, not a rounding choice.

## Penalty exposure (why the gate is hard)
A customs declaration is a legal statement to the government. Under 19 USC 1592, false statements draw
penalties scaled by culpability - up to the domestic value of the goods for fraud, multiples of the lost
duty for gross negligence/negligence. ISF and manifest violations carry their own liquidated damages. This
is why transmission and any amendment sit behind a named broker/compliance officer, with retained evidence.
