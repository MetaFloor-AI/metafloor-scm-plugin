# SAP GTS - classification, legal control, licensing

Why classification is the highest-leverage (and highest-risk) master data in GTS, how legal control turns a
code into a license requirement, and the export types that have no domestic shipment. Read when classifying a
product, when legal control blocks a document, or when a license is required/assigned.

## Contents
- Two separate numbering schemes: customs vs export control
- Control classes and legal regulations
- ECCN, EAR99, and the CCL
- ITAR / USML
- Legal control: per-transaction determination
- License determination and depletion
- Embargo check
- Exports with no domestic shipment (deemed export, re-export, de-minimis)

## Two separate numbering schemes: customs vs export control
A product carries codes in more than one scheme, and they answer different questions:
- **HS / commodity code** (customs) - drives duty, declarations, and preference. Right for customs, silent on export control.
- **ECCN / control class / USML category** (export control) - drives license requirements.
A correct HS code with a wrong export-control code still ships illegally. Classification state is **proposed
(draft) -> confirmed**; confirming commits the code that every future check uses.

## Control classes and legal regulations
GTS maps each export-control code to a **control class** (a grouping) under an active **legal regulation** (US
EAR, US ITAR, EU Dual-Use, national embargo frameworks). Each regulation activates its own checks, so one
product/lane can be free under one regulation and blocked under another. Changing a product's control class
re-runs legal control on in-flight documents and can auto-release existing blocks - which is why a control-class
change is a legal-control decision, not routine master-data maintenance.

## ECCN, EAR99, and the CCL
- **ECCN** (Export Control Classification Number) sits on the **Commerce Control List (CCL)** under the EAR. It
  decides, together with destination and end use, whether a license is required.
- **EAR99** is the residual bucket for items subject to the EAR but not listed on the CCL. It is **not
  license-free**: an EAR99 item still cannot go to an embargoed destination or a denied party.
- Downgrading an ECCN (for example, calling a controlled item EAR99) makes legal control pass and ships a
  controlled item without a license. Misclassification is the most common root cause of an export violation.

## ITAR / USML
Defense articles and defense services on the **US Munitions List (USML)** are controlled by the State
Department (DDTC) under **ITAR**. This is the strictest tier: licenses are DDTC-issued, and USML items **never
auto-clear**. No classification proposal or clearance the agent makes can release a USML legal-control block;
it routes to a human licensing officer.

## Legal control: per-transaction determination
Legal control is not a per-product yes/no flag. It evaluates the combination of **product (ECCN/control class)
+ destination country + end use + party** for each transaction. A license required for one lane may not be
required for another, so a prior clean check does not carry to a new destination or end user.

## License determination and depletion
When legal control determines a license is required, GTS looks for a valid **license** (a master record with a
value and/or quantity limit and a validity period) and **assigns** it to the transaction. Each assignment
**depletes** the license's remaining value/quantity. Consequences:
- An expired, exhausted, or over-depleted license blocks the next shipment.
- Assigning the wrong license depletes the wrong authorization and mis-reports usage.
- A partial-cover assignment (license remaining < shipment) blocks the balance.
Restoring depleted value is done only by reversing the assignment (a controlled action), not by editing the number.

## Embargo check
The embargo service blocks documents to sanctioned countries/regions. It is keyed on the **ultimate
destination and consignee**, not the routing: shipping through a third country does not remove an embargo, and
**sub-regions** (for example Crimea within Ukraine) and sectoral sanctions need the region and end use, not
just the country code.

## Exports with no domestic shipment
Standard "did the goods leave the country" logic misses three export types GTS still controls:
- **Deemed export** - releasing controlled technology or technical data to a foreign national counts as an
  export to that person's country, even with no shipment.
- **Re-export** - shipping a US-origin (or US-content) item from one foreign country to another is still
  subject to US jurisdiction.
- **De-minimis** - a foreign-made item with more than the de-minimis threshold of US-controlled content remains
  subject to the EAR. "Not shipped from the US" does not remove US jurisdiction.
