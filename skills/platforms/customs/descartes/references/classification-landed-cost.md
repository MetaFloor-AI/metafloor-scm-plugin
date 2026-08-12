# Descartes classification, duty/landed cost, licensing, and MacroPoint visibility

Load when classifying a product, computing duty or landed cost, determining an export license, or reading
MacroPoint tracking. Classification content comes from **CustomsInfo**; it drives both duty and export control.

## Contents
- Two schemes: HS/HTS vs ECCN/USML
- CustomsInfo and effective dates
- Duty, tariff, and landed-cost build-up
- License determination and depletion
- Deemed export / re-export / de-minimis
- MacroPoint visibility scope

## Two schemes: HS/HTS vs ECCN/USML
Two separate numbering systems live on the same product and must not be conflated:
- **HS / HTS** - the commodity code for **customs duty and admissibility**. Country-specific at the tariff
  line (10-digit HTSUS in the US). Drives duty rate, PGA flags, AD/CVD scope, and marking.
- **ECCN / USML** - the **export-control** classification. ECCN (EAR / Commerce Control List) decides whether
  an export license is needed by destination and end use; **EAR99** is the residual bucket (still
  EAR-controlled, not license-free). **USML / ITAR** items are State/DDTC-controlled, the strictest tier, and
  never auto-clear.
A correct HS code for duty says nothing about export control. A right HS with a wrong ECCN still ships a
controlled item illegally. Classify both, and when uncertain, classify up (stricter control / higher-duty line).

## CustomsInfo and effective dates
Descartes **CustomsInfo** is the trade-content database (HS codes, duty rates, controls, regulations) that
classification and landed cost draw on. Content carries **effective dates** - duty rates and controls change,
and a rate that was right last quarter can be superseded. Using stale content misprices the entry or misses a
new control. Check the effective date of the content version you classify or price against.

## Duty, tariff, and landed-cost build-up
Landed cost estimates total delivered cost: **product value + freight + insurance + duty + tariffs (incl.
Section 301/232 where applicable) + merchandise/harbor fees + broker/PGA fees**. Every component is an
estimate:
- Duty depends on the confirmed HS code, origin, and any AD/CVD or special tariff program.
- **The estimate is provisional until liquidation.** CBP's final duty can differ (reclassification, AD/CVD
  rate change, valuation adjustment) up to ~314 days after entry. Treating a landed-cost quote as the final
  liability understates exposure. Preferential origin (USMCA, FTAs) lowers duty only with valid origin
  documentation - claiming it without support is a customs false statement.

## License determination and depletion
For a controlled export, legal control determines whether a **license** is required (by ECCN + destination +
end use + party). A license has states **required -> assigned -> depleted**: each shipment draws down its
remaining value/quantity, and an expired or exhausted license blocks the next shipment. A partial-cover
assignment that blocks the balance is correct behavior, not a failure to fix. The agent never auto-assigns a
license or clears a legal-control block - that routes to a licensing officer.

## Deemed export / re-export / de-minimis
- **Deemed export** - releasing controlled technology or technical data to a foreign national is an export to
  that person's country, even with no goods shipped. "Nothing moved" logic misses it.
- **Re-export** - a US-origin or US-content item moving between two foreign countries stays under US
  jurisdiction. "It never left our country" logic misses it.
- **De-minimis** - a foreign-made item with more than the de-minimis US-controlled content stays subject to
  the EAR. "Not made/shipped from the US" logic misses it.

## MacroPoint visibility scope
**MacroPoint** is Descartes' real-time freight visibility - carrier tracking, load telemetry, and ETAs
(including capacity matching). It is **read-only**: an ETA is an estimate and a position or "delivered" ping
is telemetry, **not** legal proof of export, delivery, or a customs event. A tracking position can be stale
or provider-estimated. Do not drive a customs status, a screening decision, or a compliance record off a
MacroPoint event. For deeper real-time visibility needs beyond MacroPoint's scope, see `project44`
or `fourkites`.
