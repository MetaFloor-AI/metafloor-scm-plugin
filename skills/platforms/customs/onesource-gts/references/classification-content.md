# ONESOURCE classification, trade content, and license management

Load when classifying a product, reading trade content, or determining an export license. Content comes from
the Thomson Reuters **Global Trade Content** database; it drives both duty and export control.

## Contents
- The Global Trade Content database and effective dates
- Two schemes: HS/HTS vs ECCN/USML
- Global Classification workflow
- License determination and depletion
- Deemed export / re-export / EAR de minimis

## The Global Trade Content database and effective dates
ONESOURCE's crown jewel is the **Global Trade Content** database: HS/HTS codes, export controls, duty rates,
regulations, and sanctioned-party list content across 180+ countries, maintained by Thomson Reuters
regulatory analysts. Content is **effective-dated and versioned** - a duty rate, a control, or a list current
last quarter can be superseded, and each content record carries an effective (and sometimes expiration) date.
The platform's accuracy is the content's accuracy: classifying, screening, or pricing against a stale version
silently mis-declares the entry or misses a new control. Check the effective date of the content version you
act against, and re-read it at execute - content drift is a compliance event, not a cosmetic refresh.

## Two schemes: HS/HTS vs ECCN/USML
Two separate numbering systems live on the same product and must not be conflated:
- **HS / HTS** - the commodity code for **customs duty and admissibility**. Country-specific at the tariff
  line (10-digit HTSUS in the US). Drives duty rate, PGA flags, AD/CVD scope, and marking.
- **ECCN / USML** - the **export-control** classification. ECCN (EAR / Commerce Control List) decides whether
  an export license is needed by destination and end use; **EAR99** is the residual bucket (still
  EAR-controlled, not license-free). **USML / ITAR** items are State/DDTC-controlled, the strictest tier, and
  never auto-clear. (Verify against the rule, not just the platform: EAR is 15 CFR 730-774; ITAR is 22 CFR 120-130.)
A correct HS code for duty says nothing about export control. A right HS with a wrong ECCN still ships a
controlled item illegally. Classify both, and when uncertain, classify up (stricter control / higher-duty line).

## Global Classification workflow
**Global Classification** is the ONESOURCE module that assigns HS and ECCN/USML codes off content. A code is
**proposed (draft)** then **confirmed**; confirming commits the code every future check uses. Mass / assisted
classification can propose codes across a catalog against content, but a proposal is not a confirmation - a
human confirms, especially for anything control-relevant. Confirming a wrong code silently mis-screens and
mis-declares every future order for that product until someone reclassifies, and reclassifying an
already-confirmed code re-prices duty and re-runs export control on future documents (and can auto-release
existing blocks) - which is why a control-class change is a legal-control action, not master-data cleanup.

## License determination and depletion
For a controlled export, legal control determines whether a **license** is required (by ECCN + destination +
end use + party). A license has states **required -> assigned -> depleted**: each shipment draws down its
remaining value/quantity, and an expired or exhausted license blocks the next shipment. A partial-cover
assignment that blocks the balance is correct behavior, not a failure to fix. License **management** tracks
expiry, conditions, and provisos; a license used past its conditions is a violation even if value remains.
The agent never auto-assigns a license or clears a legal-control block for a controlled (ITAR/USML or EAR-CCL)
item - that routes to a licensing officer. A routine **EAR99 / NLR** determination is a bounded committing
action, but note what it means: NLR records that **no license is required**, so there is nothing to assign or
deplete on an NLR case. Assignment and depletion apply only where a license actually exists; depleting an
already-assigned, valid license within its terms is committing, while assigning a license to a controlled
item is the licensing officer's call.

## Deemed export / re-export / EAR de minimis
- **Deemed export** - releasing controlled technology or technical data to a foreign national is an export to
  that person's country, even with no goods shipped. "Nothing moved" logic misses it.
- **Re-export** - a US-origin or US-content item moving between two foreign countries stays under US
  jurisdiction. "It never left our country" logic misses it.
- **EAR de minimis** - a foreign-made item with more than the de-minimis US-controlled content stays subject
  to the EAR. "Not made/shipped from the US" logic misses it. This is a different de minimis from the
  **preference** de minimis in `preference-ftz-customs.md` (a small % of non-originating material still
  allowing origin) - do not apply one where the other belongs.
