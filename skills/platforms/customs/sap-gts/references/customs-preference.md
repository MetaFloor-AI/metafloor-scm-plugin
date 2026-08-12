# SAP GTS - customs declarations and preference

Why a customs declaration is a legal filing and not an editable document, how preferential origin is earned,
and the penalty exposure that makes a wrong release or false declaration a legal event. Read when filing or
amending a customs declaration, when determining preference/origin, or to size the penalty risk of a release.

## Contents
- Customs declarations and authorities
- Commodity codes on the declaration
- Amendments and cancellations
- Preference / origin determination
- Long-term vendor declarations
- Penalty exposure

## Customs declarations and authorities
Customs Management builds and transmits declarations to the government system, then tracks the authority's
response (accepted, queried, cleared). Common authorities/channels:
- **AES / ACE** - US export filing (Electronic Export Information via the Automated Export System in ACE).
- **ATLAS** - German customs.
- **NCTS** - EU/common-transit movements.
A transmitted-and-accepted declaration is an official government record, not a draft. Data on it (value,
quantity, commodity code, parties, origin) is a legal statement.

## Commodity codes on the declaration
The declaration carries the **HS / commodity code** (and national tariff extensions) that set duty and controls
at the border. This is the customs scheme, separate from the export-control ECCN/USML scheme; a correct
commodity code for duty does not satisfy legal control, and vice versa.

## Amendments and cancellations
A transmitted declaration is corrected by filing an **amendment or cancellation** with the authority, on the
record - never a silent edit. The correction is itself a legal filing. A knowingly false declaration is an
offense independent of the underlying goods.

## Preference / origin determination
Preference determination decides whether a product qualifies for reduced/zero duty under a free-trade agreement
(USMCA, EU FTAs, and others), based on the agreement's **rules of origin** (tariff-shift and/or regional-value-
content tests) applied over the product's bill of materials. Note the distinction:
- **Preferential origin** - qualifies for FTA duty treatment. Requires proof.
- **Non-preferential origin** - "made in" for marking/quota, no duty preference.
Claiming preferential origin the product has not earned is a customs false statement, penalized on audit even
when the duty saving looks routine.

## Long-term vendor declarations
Preference determination for a manufactured product depends on the origin status of its inputs, evidenced by
supplier **long-term vendor declarations (LTVDs)**. Missing, expired, or unsupported declarations mean the
finished product cannot validly claim preferential origin. Determination re-runs when the BOM or an input's
declaration changes, so a previously-qualifying product can lose preference.

## Penalty exposure
A wrong release, a mis-clear, or a false declaration is a legal event, not a data error. Order-of-magnitude
exposure:
All statutory maximums are adjusted annually for inflation, so treat these as floors, not fixed figures:
- **OFAC (sanctions)** - civil penalties over $300,000 per violation or twice the transaction value, whichever
  is greater; criminal penalties up to $1,000,000 and 20 years imprisonment.
- **EAR (BIS)** - civil penalties in the same six-figure-per-violation range or twice the transaction value;
  criminal penalties up to $1,000,000 and 20 years per violation.
- **ITAR (DDTC)** - civil penalties above $1,000,000 per violation; criminal penalties up to $1,000,000 and 20 years.
A wrongful clear can also trigger a **voluntary self-disclosure** obligation on a clock (BIS expects an initial
notice within 180 days of discovery; OFAC and DDTC expect prompt disclosure). This is why releasing a
compliance-blocked document is gated to the named, authorized compliance officer with a documented rationale
and retained evidence, and why controlled parts and sanctions hits never auto-clear.
