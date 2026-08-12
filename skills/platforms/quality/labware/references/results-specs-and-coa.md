# LabWare LIMS - samples, results, specs, instruments, batch disposition, COA

The path a number travels from a logged sample to an authorized result, a batch disposition, and a
certificate of analysis - and the controls that decide whether that number is right and official. Read when a
task logs a sample, enters or authorizes a result, resolves a spec, reasons about a reportable result, works
with an instrument, or disposes a batch. OOS/OOT, stability, and the Part 11 mechanics are in
`oos-stability-and-part11.md`.

## Contents
- Sample / analysis / test / result state model
- Result entry -> review -> authorization
- Spec resolution and limit types
- The reportable result (replicates, calculation, rounding)
- Instruments and interfacing
- Batch / lot roll-up and disposition
- Certificate of analysis (COA)

## Sample / analysis / test / result state model
- **Sample** - logged against a **product/grade** and **sampling point**, which resolve the **spec** and pull
  in the **analyses** to run. Status names are configured per install; a typical flow is
  **logged/unreceived -> received/in progress -> complete -> reviewed/authorized**, with off-path **cancelled**.
  A sample is not "done" until every required test is entered, reviewed, and authorized.
- **Analysis** - the master test method: its result fields, calculations, limits, sampling/replicate rules,
  and any LIMS Basic subroutines. Master data.
- **Test** - an instance of an analysis assigned to a sample, with its own status mirroring the sample flow.
- **Result** - a single measured or calculated field on a test. Status runs **entered -> reviewed ->
  authorized**, with **modified** as a branch taken only when a result is re-entered/changed (not a mandatory
  step - an unmodified result goes straight from entered to reviewed), plus **cancelled** (default LabWare
  codes E / M / R / A / X; the letters are configurable per install, so read what a status means rather than
  assuming a letter). On entry the result is auto-evaluated against the resolved spec and flagged **in-spec**
  or **out-of-spec**.

Rule: read the status before acting. An unauthorized result is a correctable draft; an authorized result is
locked and already feeding the COA and the batch disposition; a cancelled one is voided but still in the trail.

## Result entry -> review -> authorization
- **Entry** records the raw value(s); LIMS auto-flags in-spec/out-of-spec against the spec version in effect.
  Entry (and re-entry) before authorization is a **correctable draft** - re-enter with a **change reason**, and
  both values persist in the audit trail.
- **Review / verify (second person)** is the segregation-of-duties check: the analyst who entered the result
  cannot be the reviewer/authorizer. Review confirms the entry, method, and any calculation.
- **Authorization / approval** is a **Part 11 e-signature** (see `oos-stability-and-part11.md`). It **locks**
  the result and **releases** it to the COA and the batch disposition. Modifying an authorized result
  **un-authorizes** it, re-opens the sample (and any batch/COA built on it), and requires re-review - a
  correct-forward, not an undo.
- A **required** result must be entered and authorized before the sample can complete; you cannot authorize
  around a missing mandatory result.

## Spec resolution and limit types
- The **spec** resolves from **product + grade + sampling point (+ version/effective date)**. The same material
  at a different grade or sampling point carries a different spec - a wrong assignment applies the wrong
  pass/fail with no visible error.
- **Limit types** (per result):
  - **Spec limits** (lower/upper, or not-less-than / not-more-than) - **outside = OOS (fail)**.
  - **Warning / control / action limits** - **inside spec but outside these = OOT-style flag for review**, not
    a failure. They catch drift before it becomes an OOS.
  - Text/attribute results are valued against an expected value or a coded list rather than a numeric range.
- A **re-spec** (changing a limit or the assigned spec) is **master data**: it re-defines pass/fail for future
  samples and can **re-evaluate open** ones. Editing a limit to make a current failing result pass is
  spec-gaming (destructive); a legitimate spec change goes through change control.

## The reportable result (replicates, calculation, rounding)
- Many analyses take **replicates** (e.g. triplicate assay). LIMS **averages** them, runs the **calculation**
  (LIMS Basic or a formula field), and applies the **rounding** rule to produce the **reportable result**.
- **The reportable result - not any raw replicate - is what is compared to spec.** A raw value inside spec can
  round OOS, and a raw value outside can round in-spec; the rounding rule is defined per analysis and is part
  of the validated method.
- Consequence: never disposition on a raw value or a single replicate, and never change the rounding rule to
  move a borderline result across a limit - that is gaming the reportable result.

## Instruments and interfacing
- **Instrument calibration/maintenance status** gates result validity. A result captured on an instrument that
  is out of calibration, overdue for maintenance, or not qualified is suspect; LabWare can block entry against
  such an instrument or flag the result. Authorizing it certifies invalid data.
- **Interfaced results** post automatically from a connected instrument onto the result field. They still enter
  the same **review and authorization** gates - a value is not official because an instrument wrote it. A
  **mis-mapped channel** can write to the wrong result field, test, or sample, so the interface config and the
  sample/instrument assignment matter as much as the value.

## Batch / lot roll-up and disposition
- A manufactured **batch/lot** is sampled across sampling points and (stability) timepoints; **many samples and
  tests roll up to one lot**. LabWare can carry a **batch/lot disposition** status (release on spec / reject /
  hold-quarantine).
- The disposition is the **AND of every contributing sample**: a lot is releasable only when **all** required
  tests are entered, authorized, and in-spec, with **no open OOS** and no out-of-cal instrument behind a value.
  Disposing at the average or on the samples looked at so far can release a lot with an open failure.
- **Hold/quarantine** withholds a lot and is reversible by release (committing, because it stops shipment);
  **releasing** (or releasing a held lot) is the committing/destructive direction and belongs to the
  disposition owner. The physical stock movement that follows (release QI stock, block, scrap, return) posts in
  the ERP - see `sap-qm` / `sap-mm`; LabWare owns the quality decision, not the goods movement.

## Certificate of analysis (COA)
- A **COA** is generated from **authorized** results against the spec - the reportable results, their limits,
  and pass/fail. Issuing it is a **quality claim to the customer**, not a printout.
- A COA built on a **wrong spec**, an **unauthorized** value, or with a **failing result omitted** is a false
  certification. The COA template/report config decides which results print, so a wrong template can hide a
  failing test.
- A COA cannot be unsent. If a result behind an issued COA was wrong, the fix is a **corrected/superseding COA**
  plus a recall/notification path in the ERP/QMS - never a silent edit. The original COA and result stay in the trail.
