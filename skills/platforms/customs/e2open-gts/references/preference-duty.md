# Preference / FTA qualification and duty management (e2open GTM)

Load when qualifying preferential origin, running a supplier solicitation, issuing a certificate of origin, or
computing duty / landed cost. This is e2open's (Amber Road) marquee surface, and its most-abused one: a
preferential-origin claim is a legal statement to customs that rests on **supplier declarations you did not author**.

## Contents
- The qualification chain
- Rules of origin (the tests a BOM must pass)
- Supplier solicitation and LTVD lifecycle
- Certificate of origin and self-certification
- Duty management: landed cost, FTZ, drawback, AD/CVD

## The qualification chain
`classify the finished good (HS) -> pick the agreement + its rule of origin -> gather valid supplier
declarations for the inputs -> qualify the BOM against the rule -> issue the certificate of origin`.
Qualification states: **not qualified -> under solicitation -> qualified (originating) / not qualifying**.
Every link depends on the one before; a defect upstream (stale content, expired declaration, wrong RVC method)
flows into every certificate issued from it.

## Rules of origin (agreement- and HS-specific)
The finished good must pass the **exact** rule for that agreement and HS heading. Common tests:
- **Wholly obtained** - entirely produced in the territory (raw materials, agriculture).
- **Tariff shift / change in tariff classification (CTC)** - each non-originating input must undergo a
  specified HS change (heading or subheading) through processing in the territory. If an input does not shift, it fails unless de minimis covers it.
- **Regional Value Content (RVC)** - a minimum percent of value must originate. Two methods give **different
  answers** for the same BOM; the agreement dictates which applies:
  - **Transaction-value method** - RVC = (transaction value - value of non-originating materials) / transaction value.
  - **Net-cost method** - RVC = (net cost - value of non-originating materials) / net cost (USMCA autos use net cost).
- **De minimis** - a small share of non-originating value is tolerated (for example, 10% under USMCA);
  above it the good fails. It rescues a near-miss tariff-shift, not a wholesale failure.

"Mostly made here" does not qualify. The rule is mechanical, and the wrong method or a missing input value flips the result.

## Supplier solicitation and LTVD lifecycle
- Qualification rests on **supplier declarations** attesting the origin of purchased inputs. A **long-term
  vendor declaration (LTVD)** covers repeated shipments over a **validity period**.
- **Solicitation** is an outbound campaign asking suppliers to provide/renew these. Sending it **egresses
  part/BOM data to external suppliers** - keep the payload minimal, recipients verified, and never attach controlled technical data.
- Declaration states: **requested -> received -> valid (within validity period) -> expired**. An **expired
  declaration silently invalidates a prior qualification** - re-solicit before relying on it; do not carry the old answer forward.
- Qualifying a BOM on **missing, assumed, or expired** declarations produces a **false origin claim** and is a
  destructive action (see SKILL.md matrix). Qualifying on complete, valid, unexpired declarations is committing.

## Certificate of origin and self-certification
- The output document claiming preferential origin: **USMCA certification of origin** (self-certified by
  exporter/producer/importer), **EUR.1 / EUR-MED** movement certificate, or an **invoice/origin declaration**.
- Issuing/signing it is a **legal claim** to the authority, and your **customer relies on it to claim reduced
  or zero duty** - so the exposure runs to both parties. A false certificate is a **customs false statement**
  (19 USC 1592, up to the domestic value of the goods); the exporter/producer is liable on audit.
- It is **issued and signed by the authorized person only** (the hard gate). An issued certificate is
  **withdrawn/invalidated and re-issued, not edited**; a customer who already claimed preference on a bad certificate must be notified - a disclosure matter.

## Duty management: landed cost, FTZ, drawback, AD/CVD
- **Landed cost** - duty + tax + freight + fees estimate; **provisional until liquidation**. CBP liquidates
  (final duty) up to ~314 days later; reclassification or AD/CVD can move it.
- **Foreign-Trade Zone (FTZ)** - a duty-deferral/elimination zone. **Admission status fixes the duty
  treatment at withdrawal:** **privileged foreign** locks the HS/rate at admission; **non-privileged foreign**
  is assessed at withdrawal in its then-condition. A wrong status mis-computes the entry, and a missed **weekly entry** (its filing window) loses the FTZ benefit.
- **Duty drawback** - a **refund claim to CBP** for duties on re-exported or destroyed goods. A claim is a
  filing; an overstated or unsupported claim is a **false claim**, not a rebate you are owed.
- **AD/CVD** - antidumping / countervailing case numbers carry cash deposits and large **retroactive
  liability at liquidation**; misapplied or omitted, they surface as a major bill later.
