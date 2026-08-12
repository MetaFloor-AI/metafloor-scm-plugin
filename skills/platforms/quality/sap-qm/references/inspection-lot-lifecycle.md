# SAP QM - inspection lot lifecycle, results, usage decision, stock

The full path a quantity travels from "held for inspection" to "released, blocked, or scrapped", and the
controls that decide severity. Read when a task creates a lot, records results, makes a usage decision, or
reasons about why stock is or is not available. Deep movement-type and valuation detail lives in
`sap-mm`; this file covers the QM-side decisions.

## Contents
- Inspection origins (what triggered the lot)
- Inspection lot status (the state machine)
- Results recording (building the record)
- The usage decision and its stock postings
- Sampling: sample vs lot
- Dynamic modification and the quality level
- Recurring and source inspection

## Inspection origins (what triggered the lot)
The origin is a 2-digit class on the lot; the **inspection type** activated in the material master QM view is
what switches a given origin on for a material + plant. Common origins:
- **01** - goods receipt from a purchase order (or production order GR). Stock-relevant: the received
  quantity lands in quality-inspection (QI) stock and the lot holds it.
- **03** - in-process inspection during production, against a production/process order. Usually **not**
  stock-relevant: it confirms quality at operations but moves no inventory. In-process results can be recorded
  at **inspection points** (per operation, time, quantity, or a free key), so results aggregate differently
  than a single GR lot - each point gets its own valuation and can feed a partial confirmation.
- **04** - goods issue: inspection triggered when stock is issued (e.g. to a delivery or order), rather than
  at receipt.
- **05** - other (no fixed reference). A manual lot with no reference document commonly uses a general
  inspection type (89).
- **08** - stock transfer inspection (inspect on transfer between plants/locations). Stock-relevant.
- **09** - **recurring inspection**: re-inspect stored batches after a shelf-life interval; the system
  generates fresh lots for stock already in the warehouse.
- SD-side origins cover outbound deliveries and customer returns.

Rule: only stock-relevant origins hold and move QI stock. Creating a stock-relevant lot manually (QA01) posts
the quantity into QI, so it is a stock movement, not a neutral "create".

## Inspection lot status (the state machine)
- **CRTD** - created. The lot exists but characteristics may not be available yet.
- **REL** - released. Characteristics are available and results can be recorded. A lot needs a released
  inspection plan (or a defined reason it needs none) to release.
- **INSP** - in process: some results recorded, not yet decided.
- **UD** - a usage decision has been made; the lot is closed for results.
- **SPRQ** - stock posting required: there is still QI quantity to post out. A lot can carry SPRQ after the UD
  if the stock posting was partial or deferred; the quantity is not yet in unrestricted/blocked/etc.
- Stock posting completed clears the SPRQ condition; the lot is then fully closed.

Read the status before acting: a REL/INSP lot is still editable (results), a UD lot is decided, and an SPRQ
lot has stock still sitting in QI regardless of the decision.

## Results recording (building the record)
- Record measured values (quantitative) or attribute codes (qualitative, valued against a catalog) per
  **inspection characteristic**, for the **sample size** the sampling procedure set.
- Each characteristic is **valuated** accepted or rejected against its tolerance / catalog. A **required**
  characteristic must be recorded and valuated; an optional one may be skipped.
- Recording is a correctable draft **until the UD**: you can re-record and re-valuate (QE02). Nothing frees
  stock and the lot is not closed by recording alone.
- Worklists: QE51N (work-center / results worklist), QE01/QE02/QE03 for a single lot's characteristics.

## The usage decision and its stock postings
The UD (QA11 record, QA12 change, QA13 display) does two things at once:
1. **Valuates the lot** with a **UD code** from the plant's **selected set** (catalog type 3). Each code
   carries an **accept (A)** or **reject (R)** quality score. That score feeds vendor evaluation and the
   dynamic-modification history.
2. **Posts the lot quantity out of QI stock** into one or more dispositions. Typical dispositions (the QM
   screen labels; the underlying MM movement types and valuation are in `sap-mm`):
   - **to unrestricted use** - releases the quantity to MRP/ATP (the QI -> unrestricted transfer). This is the
     "accept" path and frees stock immediately.
   - **to blocked stock** - keeps it on the books but unavailable, pending a later decision.
   - **to sample usage** - the quantity consumed by inspection.
   - **to scrap** - destroys stock and value; a loss with a GL expense. Not a correction.
   - **return to vendor** - reverses the receipt against the PO; re-opens commitment and can drive a vendor
     credit and a Q2 complaint.
   - **to new material / reserves** - re-classify to a different material or hold.
- The postings can be **split** (e.g. part to unrestricted, part to scrap) and can be **partial or deferred**,
  leaving the lot in **SPRQ** with stock still in QI until posted.
- Making the UD also triggers follow-up: update the vendor score, update the quality level (next inspection
  stage), optionally create/close a quality notification, and (batch-managed) set the **batch status** and
  copy results into the **batch classification**.

Why the UD is the danger point: one save can free ATP, destroy stock, reverse a receipt, re-score a vendor,
and certify a batch, and changing it later (QA12) is a **new** posting that can only move stock that is still
physically there.

## Sampling: sample vs lot
- The **sampling procedure** on the characteristic sets how many units to inspect (fixed sample, percentage,
  or a sampling scheme). You measure the **sample**, but the UD dispositions the **entire lot quantity**.
- Consequence: accepting on a passing sample releases every unit in the lot, including uninspected ones; a
  sample failure can reject a whole lot even if most units were fine. The sample is evidence about the lot,
  not a per-unit gate.

## Dynamic modification and the quality level
- **Dynamic modification** adjusts inspection **severity** from quality history: **tightened -> normal ->
  reduced -> skip**. Good history relaxes it; a reject tightens it.
- The current stage per material (+ plant / vendor, depending on the rule) is tracked on the **quality
  level**. The UD's accept/reject result advances or resets the stage.
- At a **skip** stage no inspection characteristics are created and the stock can pass to unrestricted with no
  results recorded. Do not assume every receipt is inspected; check the quality level / whether a lot with
  characteristics was even created.
- Forcing a skip or overriding the modification to avoid inspection is a destructive control decision: it lets
  uninspected stock reach ATP.

## Recurring and source inspection
- **Recurring inspection (origin 09)** creates new lots for batches already in stock once a shelf-life or time
  interval elapses, so stored stock is re-tested. An open recurring lot gates that stock; ignoring it ships
  material that is due for re-inspection or expired.
- **Source inspection** (via QM in procurement) can create an inspection lot **before** or **at** the vendor,
  so a receipt is only allowed once the source lot passes and, if required, a certificate is present. This
  ties to the quality info record and certificate requirement in `notifications-and-info-records.md`.
