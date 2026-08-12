---
name: labware
description: "LabWare LIMS and ELN - safe operation of a validated (GxP, 21 CFR Part 11) laboratory information management system: sample login, result entry, second-person review and result authorization (e-signature), specifications and spec/warning limits, in-spec vs out-of-spec flagging, batch/lot disposition and release on spec, certificates of analysis (COA), out-of-specification (OOS) and out-of-trend (OOT) handling, stability studies, and instruments on an immutable audit trail. Use when the connected lab system is LabWare, or the user mentions LabWare LIMS or ELN, a sample login or backlog, an analysis/test/result, result entry, review/verify or authorize/approve a result, an e-signature / 21 CFR Part 11 / GxP, a specification or spec limits, in-spec/out-of-spec, an OOS or OOT investigation, a reportable result, a stability study or pull/timepoint, an instrument interface or calibration, a batch/lot release on spec, a certificate of analysis (COA), LIMS Basic, or the audit trail."
---

# LabWare LIMS - operating the lab data system safely

LabWare LIMS (and its ELN companion) is where lab data is generated and made official: samples are logged,
analyses are run, results are entered, reviewed, and **authorized**, then a batch is dispositioned and a
certificate of analysis is issued. The thing that makes it dangerous is simple: **it is a validated GxP
system, and authorizing a result is a Part 11 electronic signature that turns a raw number into the record
of quality.** An authorized result feeds the COA and the batch disposition the instant it is signed; an OOS
result that gets overridden waives a real failure; a spec limit edited to pass a failing value fakes the
gate; and the audit trail keeps every entry, change, and signature forever. You are not filling a
spreadsheet - you are creating inspectable evidence a regulator will read. This skill classifies those
actions so the harness can gate them, plus the edge states (reportable result, OOS/OOT, stability,
instruments, spec versioning) and the recovery paths, almost all of which are "correct forward".

## When this applies / when NOT
Connector is LabWare LIMS or LabWare ELN and the work is lab sample testing, results, review/authorization,
specs, batch disposition, COA, OOS/OOT, stability, or instruments. When NOT:
- SAP QM inspection lots, the usage decision, quality-inspection stock postings in the ERP -> `sap-qm`.
- The formal quality-event world - deviations, the full OOS root-cause investigation, CAPA, complaints,
  change control, audits - in a dedicated QMS -> `veeva-vault-qms` (or `mastercontrol`).
- ERP physical stock disposition (block / release / scrap / return the lot, movement types, valuation) -> `sap-mm`.

Seam to hold: **LabWare owns the number; the ERP owns the stock; the QMS owns the investigation.** LabWare
authorizes the result and can carry a batch disposition/release-on-spec status; the physical goods movement
that follows (release QI stock, scrap, return) posts in the ERP (`sap-qm`/`-sap-mm`); the deviation
and CAPA that an OOS drives live in the QMS. LabWare's own OOS handling is the **laboratory-phase**
investigation (analyst check, retest under protocol) that feeds those, not the full root-cause/CAPA record.

## Contents
- Object & state model
- Vocabulary that bites
- Operations: read / write / destructive
- Reclassification rules
- Worked example (a batch release, end to end)
- Gotchas that bite
- Edge states & special cases
- Recovery patterns
- Guardrails
- References

## Object & state model (reason about state, not nouns)
- **Sample** - the central object: a physical sample logged into LIMS against a **product/grade** and a
  **sampling point**, which resolve the **specification** and pull in the **analyses** to run. Logging can be
  manual or driven by a template, a sampling plan, or (stability) an auto-schedule. Sample status runs (names
  are configurable per install) **logged/unreceived -> received/in progress -> complete -> reviewed/authorized**,
  with off-path **cancelled**. Detail in `references/results-specs-and-coa.md`.
- **Analysis / Test** - an **analysis** is the master test method (its result fields, calculations, limits,
  and any LIMS Basic subroutines); assigned to a sample it becomes a **test** with its own status. A test is
  not done until its required results are entered and it is reviewed/authorized.
- **Result** - a single measured or calculated field on a test. On entry it is auto-evaluated against the
  spec and flagged **in-spec** or **out-of-spec**. Result status runs **entered -> reviewed -> authorized**,
  with **modified** as a branch when a result is re-entered/changed (not a required step), plus **cancelled**
  (default LabWare codes E / M / R / A / X, but the letters are configurable per install - read what a status
  means, do not assume a letter). The **reportable result** (after replicates,
  calculation, and rounding) is the value compared to spec - not the raw entry.
- **Specification / limits** - the spec resolves from **product + grade + sampling point (+ version)** and
  sets, per result, the **spec limits** (lower/upper - fail outside) and often **warning/control limits**
  (flag-for-review inside spec). A result outside spec limits is OOS; inside spec but outside warning/control
  or historical trend is **OOT**. Same number, different gate.
- **Batch / lot** - the manufactured lot, sampled across sampling points and (stability) timepoints. Many
  samples/tests roll up to one batch. Its **disposition** (release on spec / reject / hold) depends on **every**
  contributing sample being complete, authorized, and in-spec, with **no open OOS**.
- **OOS / OOT** - an out-of-specification result and its **laboratory investigation** (LabWare OOS workflow);
  an out-of-trend result flagged against control limits or a trend. See `references/oos-stability-and-part11.md`.
- **Stability study** - a study with a **protocol** (storage conditions, **pull points/timepoints**, tests
  per pull); LabWare auto-generates the samples per pull. Results trend across timepoints and drive
  shelf-life. See `references/oos-stability-and-part11.md`.
- **Instrument** - an interfaced or manually-read instrument with a **calibration/maintenance status**;
  results can post automatically from an interface. An out-of-calibration instrument taints the result.
- **COA** - the certificate of analysis, generated from **authorized** results against the spec; issuing it
  certifies the batch to a customer. See `references/results-specs-and-coa.md`.
- **Audit trail** - system-generated and **immutable**: every result entry, change (with reason), status
  change, and e-signature, with user + timestamp + old/new value. A correction is a new entry, never an erasure.
- **Static data & LIMS Basic** - products, analyses, specs, users/roles, and the **LIMS Basic** scripts
  (calculations, subroutines, workflow triggers) are **configuration**, not data. In validated production,
  changing them is a computer-system change, not an operator edit.

## Vocabulary that bites
- **Authorize / approve a result** - the committing act: a Part 11 e-signature that locks the result and
  releases it to the COA and the batch disposition. Not a save; not reversible without un-authorizing.
- **Review / verify (second person)** - segregation of duties: the analyst who **entered** a result cannot be
  the one who **reviews/authorizes** it. Signing both roles, or on another's behalf, is a data-integrity violation.
- **Reportable result** - the value actually compared to spec, after averaging **replicates**, running the
  **calculation**, and applying the **rounding** rule. A raw value in-spec can round OOS, and vice versa;
  judging the raw number mis-dispositions.
- **In-spec / out-of-spec flag** - set automatically at entry from the **active spec version** and its limits.
  A stale or wrong spec assignment silently passes or fails stock - the flag is only as right as the spec.
- **Spec vs warning/control limits** - spec limits fail a result (OOS); warning/control limits flag it for
  review while still in-spec (OOT signal). Treating only spec limits as the gate misses the early drift.
- **OOS (out of specification)** - a failing reportable result. It is **not** a rejected batch by itself; it
  opens a **laboratory investigation**. Invalidating it without a justified, documented root cause is falsification.
- **OOT (out of trend)** - in-spec but off its historical/control trend; a leading indicator (especially in
  stability), not a pass to ignore.
- **Batch disposition / release on spec** - the decision that a lot's results clear the spec so it can be
  released. High blast: it gates whether product ships. Requires all contributing samples authorized and in-spec.
- **Certificate of analysis (COA)** - a quality claim to the customer built from authorized results; a COA on
  a wrong spec, an unauthorized value, or an omitted failing result is a false certification.
- **Instrument calibration/maintenance status** - a result taken on an out-of-calibration or overdue
  instrument is suspect; LabWare can block entry or flag it. Authorizing such a result certifies invalid data.
- **LIMS Basic / subroutine** - LabWare's scripting behind calculations, limit checks, and workflow triggers.
  Editing it in production changes how results are evaluated for every future sample - a validated config change.
- **Static data** - products, analyses, specs, users. Changing a spec re-defines pass/fail for future (and can
  re-evaluate open) samples; it is master data, not a per-sample edit.
- **Cancel vs delete** - cancelling a sample/test/result voids it but keeps it in the trail; in validated
  production, deletion of GxP records is blocked by design.

## Operations: read / write / destructive
Classify every operation family by what it does to the record, the batch, and the audit trail. No tool/screen
names below - kinds of action; the harness maps the customer's real connector (LabWare GUI, Web LIMS, or API)
onto these classes.

| Class | LabWare operation families | Gate | Why |
|---|---|---|---|
| **Read** | display a sample / test / result and its in-spec flag; view the spec and limits (product/grade/sampling point/version); view a batch/lot and its open samples; view a stability study, protocol, and pull schedule; view the backlog/worklist; view instrument calibration status; preview (not issue) a COA; view the audit trail; run a query/report | always pass | no state change; read the sample + spec + limits + open OOS + instrument status before any write, re-read at execute |
| **Write (reversible)** | log a sample and assign/remove analyses before results; **cancel a sample/test before any result is authorized** (voids it, kept in the trail, no signed value lost); **enter or re-enter a result before authorization** (auto-flagged vs spec, correctable with a change reason - both values persist); edit a draft stability protocol before it is active; reassign a backlog/worklist item (routing) | gate one at a time | uncommitted or correctable; no signature, no disposition bound, no COA fed; audit-logged but not compliance-committing |
| **Write (committing)** | **review/verify a result** (second-person sign-off); **authorize/approve a result** = a Part 11 e-signature that locks it and feeds the COA + batch disposition; **complete a sample** (all tests done, releases it downstream); **release a batch/lot on spec** (disposition, gates whether product ships); **issue/print a COA** to a customer; **place a batch on hold/quarantine** (withholds it - reversible by release, but halts shipment); create/activate a **stability study** (auto-schedules future samples); change an **instrument to calibrated/released** so its results count | gate + human approve | binds a signed decision, a disposition, a certification, or a schedule; each is inspectable evidence and mostly one-way |
| **Destructive / irreversible** | **invalidate an OOS result / override the OOS** without a justified investigation (waives a real failure); **modify an authorized result** (un-authorizes it, re-opens the sample/batch, can invalidate an issued COA); **edit a spec limit or rounding rule to pass a failing result** (gaming the gate); **release a batch with an open OOS, an unauthorized result, or a missing required test** (bypasses the quality gate); **retest/resample to replace an OOS without the protocol** (testing into compliance); cancel an authorized sample or one already on a COA; **any LIMS Basic / spec / workflow config change in production**; sign on another user's behalf or share credentials | hard gate + named approver + re-read | permanent trail; crosses a quality/compliance boundary; certifies or ships bad product; cannot be cleanly undone |

**What "irreversible" means here:** the *compliance* effect is permanent, not that the data can never be corrected forward. Modifying an authorized result, for instance, is recoverable as a data state (un-authorize -> re-review -> re-authorize), but the original value and signature stay in the immutable trail and an already-issued COA becomes a false claim - so it carries a destructive blast radius and a hard gate even though a forward correction exists. Gate by the compliance impact, not by whether a field can be re-entered.

**Entering a result is reversible but not side-effect-free:** a value that flags OOS on entry immediately opens the OOS record/workflow. You can re-enter the value (a correctable draft), but you cannot un-flag the OOS by re-typing - acknowledge the flag and follow the OOS path, do not silently overwrite it.

**Authorize-gate quick check** (before signing a result, completing a sample, or releasing a batch - take the first that fires):

| Condition | Action |
|---|---|
| Entering analyst == the reviewing/authorizing analyst | REFUSE - segregation-of-duties violation; a different person must review/authorize |
| Any required result missing / not entered | BLOCK - you cannot authorize or complete around a missing mandatory result |
| Result flagged OOS, investigation not resolved | STOP - route to the OOS lab-phase; never authorize/release over an open OOS |
| Instrument behind the value out of calibration / overdue / unqualified | FLAG - the data is suspect; do not authorize until the instrument state is resolved |
| Reportable result (not a raw replicate) not yet computed, or rounding rule unclear | HOLD - disposition on the reportable result, never a raw value |
| Wrong spec resolved (product/grade/sampling point/version) | FIX first - correct the assignment so the right limits apply before judging pass/fail |
| Spec version / effective date changed since the result was entered | RE-CHECK - a re-spec can silently re-flag an already-entered result; confirm the in-spec/OOS flag reflects the spec that governs this sample, not a stale one |
| Releasing a batch with any contributing sample unauthorized, OOS-open, or missing a test | REFUSE - the disposition is the AND of every sample; do not release at the average |
| All clear | proceed as a committing action: gate + human approve + logged signature |

## Reclassification rules (read this)
Quick classify (take the first that matches): 1) overrides/invalidates an OOS, edits a spec/rounding to pass a
value, releases a batch over an open failure/unauthorized result, tests into compliance, changes production
config, modifies an already-authorized result, or signs for someone else -> **destructive**. 2) authorizes /
reviews a result, completes a sample, releases/holds a batch, issues a COA, activates a stability study, or
releases an instrument -> **committing**. 3) logs a sample, enters/re-enters a result before authorization, or
routes a worklist item -> **reversible**. 4) **cannot tell?** treat it as **destructive** and apply the hard
gate - in a validated system the safe default for an unclassified or novel action is the strictest class, not
the loosest. Then apply the nuances:
- **Entering a result is reversible; authorizing it is not.** A result you have entered but not authorized is a
  correctable draft (re-enter with a change reason; both values stay in the trail). Once authorized, the
  e-signature and the release to COA/disposition are on the record; modifying it un-authorizes and requires
  re-review - a correct-forward, not an undo.
- **An OOS flag is automatic; the OOS decision is not.** The system flags OOS at entry with no judgment.
  **Invalidating** that OOS (declaring assignable lab error) is a destructive quality decision that belongs to
  the documented investigation, not the analyst at the keyboard - the same field change, but the direction and
  the justification decide the class.
- **Withholding is asymmetric from releasing.** Putting a batch on hold/quarantine only withholds it and is
  reversible by releasing - committing, because it stops shipment, but recoverable. **Releasing** a held batch,
  or releasing on spec, is the committing/destructive direction and belongs to the disposition owner.
- **Editing the spec is master data, not a sample edit.** Changing a limit or rounding rule re-defines pass/fail
  for future samples (and can re-evaluate open ones). Doing it to make a current failing result pass is
  spec-gaming - destructive, the lab analog of dodging a control.
- **A batch release is only as clean as its weakest sample.** Releasing a lot is destructive if any contributing
  sample has an open OOS, an unauthorized/missing required result, or an out-of-cal instrument behind a value.
  Do not gate the release at the average; check every open item on the batch.
- **A required result that is not entered blocks completion and authorization.** You cannot authorize around a
  missing mandatory result; entering a placeholder to close falsifies the record.
- **Legitimately releasing an instrument is committing; falsely certifying one is destructive.** Marking an
  instrument calibrated/released after the calibration was actually performed is committing (its results now
  count). Marking it calibrated/released **without** the calibration having been done certifies invalid data
  for every result behind it - a data-integrity falsification in the destructive row, not a committing edit.
- **Cancellation inherits the class of the most-committed result on it.** Cancelling a sample/test with **no**
  authorized result is reversible (voided, kept in the trail). If **any** result is already authorized (or the
  sample is on a COA), cancellation is destructive - it voids a signed value and must go through the hard gate,
  even if other results on the sample are still drafts.
- **Config in production is destructive, never a data edit.** A LIMS Basic calculation, a spec version, a
  limit, or a workflow trigger changed in the production LIMS is a validated computer-system change requiring
  change control and sandbox-then-migrate - regardless of how small the field looks.

Universal rules to teach: read the sample/test/result status + the resolved spec + limits + any open OOS +
instrument calibration state before any write and **re-read at execute** (another analyst may have entered,
reviewed, authorized, or cancelled in the meantime); never authorize your own entry (segregation of duties),
never sign on another's behalf; never invalidate an OOS, force a result in-spec, or edit a limit to pass a
failing value; never release a batch over an open OOS or an unauthorized result; the audit trail is immutable -
correct forward, never try to alter it.

## Worked example (a batch release, end to end)
A finished-product lot is sampled; a **sample** is logged against product **PARA-500 / grade Release** at
sampling point **FG-Warehouse**, which resolves the spec and pulls in analyses (Assay, Dissolution, Water,
Micro). *Reversible so far: nothing is signed.* The Assay analysis runs in triplicate; the raw replicates read
**99.4, 99.7, 99.1**, the calculation averages them and the **rounding** rule gives a **reportable result of
99.4 %** against spec **95.0-105.0 %** - **in-spec**. *Entering these is reversible; re-entry with a change
reason is fine until authorization.* A second analyst **reviews** and then **authorizes** the Assay result
*(committing: a Part 11 e-signature; the entering analyst may not authorize their own result)*. Water is
**0.9 %** vs a limit of **1.5 %** max - in-spec, authorized. But **Dissolution** returns a reportable **78 %**
against a **not-less-than 80 %** limit: LabWare flags it **OOS** and opens a **laboratory investigation**
*(the OOS is not a rejected batch - it is a stop for investigation)*. The right path: run the LabWare OOS
lab-phase (confirm no analyst/instrument/prep error) and, only if the investigation justifies it, retest under
the protocol; the deviation and any CAPA are raised in the QMS (`veeva-vault-qms`). The wrong path,
and the one to refuse: **invalidate the OOS** with no assignable cause, or **retest until a passing value
appears and drop the 78 %** (testing into compliance), or **edit the dissolution limit to 75 %** so it passes -
each is destructive falsification, and each leaves the original 78 % in the immutable trail anyway.
**Releasing the batch on spec** requires **all** analyses authorized and in-spec with the OOS resolved through
its investigation; releasing while Dissolution is open **bypasses the quality gate** *(destructive)*. Once the
batch is legitimately released and a **COA** is issued, it certifies PARA-500 to the customer - so if the
dissolution result was ever wrong, the COA is a false claim and the fix is a superseding COA plus a recall
path in the ERP/QMS, not an edit.

**OOS mini-playbook (the highest-risk path, in order):** 1) The OOS flag stops the disposition - it is not a
rejected batch and not a value to overwrite. 2) Run the LabWare **laboratory phase**: check the analyst
technique, calculation, instrument calibration/state, standards and prep, and the sample. 3) The **default
outcome is to confirm the OOS** (it stands); **invalidating** it needs an assignable, documented laboratory
error and an approver - invalidation is the exception, not the reflex. 4) A **re-test** (same prepared
solution/sample) or **re-sample** (a fresh sample) happens only if the OOS protocol allows it, in the
direction the protocol dictates - never repeat-until-pass. 5) The deviation and CAPA are raised in the QMS
(`veeva-vault-qms`); any physical hold/scrap/return posts in the ERP (`sap-qm`/`-sap-mm`).
The original OOS and every retest remain in the immutable trail regardless of the outcome.

## Gotchas that bite (the real set - causal chains)
1. **A result is flagged in-spec/out-of-spec automatically at entry, from the active spec version.** The flag
   is only as right as the resolved spec (product/grade/sampling point/version); a stale or wrong spec silently
   passes or fails stock. Read which spec resolved before trusting the flag.
2. **The reportable result, not the raw value, is compared to spec.** Replicate averaging, the calculation, and
   the **rounding** rule produce the reportable result; a raw value in-spec can round OOS and vice versa.
   Dispositioning on the raw number is wrong.
3. **Authorizing a result is a Part 11 e-signature, not a save.** It locks the result and releases it to the
   COA and the batch disposition the instant it is signed. Modifying an authorized result un-authorizes it,
   re-opens the sample/batch, and can invalidate an already-issued COA - a correct-forward, not an undo.
4. **An OOS result is not a failing batch; it is a stop for investigation.** Invalidating the OOS without a
   justified, documented root cause (an assignable analyst/instrument/prep error) waives a real failure and is
   a data-integrity violation. The analyst does not get to overwrite an OOS to pass.
5. **You cannot test into compliance.** Repeating a test until a passing value appears and discarding the OOS is
   falsification; the original OOS and every retest stay in the trail. Retest/resample follows the OOS protocol,
   not the analyst's preference.
6. **Segregation of duties is enforced: the analyst who entered a result cannot review/authorize it.** Signing
   both roles, sharing a login, or signing on another's behalf breaks data integrity and is an inspection finding.
7. **Releasing a batch on spec requires every contributing sample authorized and in-spec with no open OOS.** A
   release over an open OOS, an unauthorized/missing required test, or an out-of-cal instrument bypasses the
   quality gate and can ship bad product.
8. **A COA certifies quality to the customer.** It is built from authorized results against the spec; a COA on a
   wrong spec, an unauthorized value, or an omitted failing result is a false certification, not a printout.
9. **Editing a spec limit or rounding rule re-defines pass/fail** for future samples (and can re-evaluate open
   ones). Loosening a limit to pass a failing result is spec-gaming - the lab analog of dodging a control.
10. **The audit trail is immutable.** Every result entry, change (with reason), status change, and signature is
    kept with user + timestamp + old/new value. "Fixing" a mistake is a new correcting entry, never an erasure;
    a rushed wrong result is inspectable forever.
11. **Instrument calibration status gates result validity.** A result captured on an out-of-calibration, overdue,
    or unqualified instrument is suspect; authorizing it certifies invalid data. Check the instrument state
    behind a value, not just the value.
12. **Interfaced results post automatically but still need review/authorization.** An instrument interface can
    write a raw value straight onto a result; a mis-mapped channel writes to the wrong component or sample, and
    the value is not official until it is reviewed and authorized like any other.
13. **OOT is not OOS.** A result inside spec limits can still be out of trend against control/warning limits or
    history; ignoring OOT misses an emerging drift, which in stability can foreshadow a shelf-life failure.
14. **Warning/control limits and spec limits are different gates.** A result inside spec but outside a
    warning/action limit flags for review without failing; treating only spec limits as the gate misses the
    early signal.
15. **Stability samples are auto-generated per protocol pull point.** Missing a pull, entering a timepoint late,
    or dispositioning a stability OOS as a one-off breaks the study; a confirmed stability failure can trigger a
    field alert and a shelf-life/expiry-date impact far beyond one sample.
16. **A required result that is not entered blocks sample completion and authorization.** You cannot authorize
    around a missing mandatory result; a placeholder to close the sample falsifies the record.
17. **Spec resolves by product + grade + sampling point (+ version).** The same material at a different grade or
    sampling point carries different limits; a wrong spec assignment applies the wrong pass/fail with no visible error.
18. **Cancelling a sample or test is not a delete, and not a clean-up.** It voids the item but keeps it in the
    trail; cancelling a test to make a batch "look clean" hides a result an inspector will still see.
19. **Result status codes are configurable per install.** Do not assume a letter means authorized; read what the
    status actually represents (entered vs modified vs reviewed vs authorized vs cancelled) before acting on it.
20. **One batch groups many samples across sampling points and timepoints.** Authorizing or dispositioning one
    sample does not release the batch; check every open sample, test, and OOS tied to the lot before release.
21. **Config in production (LIMS Basic, spec versions, limits, workflow triggers) is a validated change, not a
    data edit.** An ad-hoc change to a calculation or a limit in the production LIMS changes how every future
    result is evaluated and breaks the validated state; it is itself a finding.
22. **A change reason on a modified result is compliance evidence.** It is captured in the audit trail and read
    in inspections; a placeholder reason to clear the gate falsifies the record.
23. **ELN results flowing into LIMS still enter the same gates.** A value produced in LabWare ELN and pushed to
    a LIMS result is not authorized by having been recorded in the notebook; it is reviewed and authorized in
    LIMS like any other result.

(Deep detail: `references/results-specs-and-coa.md`, `references/oos-stability-and-part11.md`.)

## Edge states & special cases
Each breaks naive "the number is in the box, so the stock is good" logic - the key rule inline, full behavior
in the references.
- **Reportable result vs raw** - replicates, calculation, and rounding decide the value compared to spec; the
  raw entry is not the disposition. `references/results-specs-and-coa.md`.
- **Spec resolution and versioning** - product/grade/sampling point pick the spec and its version; a re-spec
  can re-flag open samples. Same file.
- **Spec vs warning/control limits and OOT** - two independent gates; in-spec is not the same as in-trend.
  `references/oos-stability-and-part11.md`.
- **OOS laboratory investigation** - LabWare owns the lab-phase (analyst/instrument/prep check, protocol
  retest); the deviation/CAPA is in the QMS. Do not confuse invalidating an OOS with closing an investigation.
- **Stability** - protocol-driven pulls, storage conditions, timepoint trending, shelf-life impact; a stability
  OOS/OOT is rarely a one-off. Same file.
- **Instruments and interfacing** - calibration/maintenance status gates validity; interfaced values still need
  review/authorization and can mis-map. `references/results-specs-and-coa.md`.
- **Batch/lot roll-up** - a lot's disposition is the AND of all its samples; the weakest open item blocks release.

## Recovery patterns (can it be undone, and what cannot)

| Situation | Recovery path |
|---|---|
| A result was entered wrong, before authorization | re-enter it with a change reason; both values persist in the audit trail - a correctable draft, nothing is erased |
| A result was authorized with the wrong value | modify it (which un-authorizes it) and re-review/re-authorize; the original value and signature stay in the trail; if a COA was issued, re-issue a superseding COA |
| An OOS was invalidated in error, or the wrong OOS disposition was recorded | handle through the OOS/investigation record and the QMS; you cannot silently erase it - the original OOS stays as evidence |
| A required result is missing so the sample will not complete | enter/authorize the mandatory result; do not force completion or placeholder it - the block is by design |
| A batch was released with an open OOS or unauthorized result | cannot cleanly unrelease; put the lot on hold/quarantine in LIMS AND, as a required parallel action, trigger the physical stock hold/recall in the ERP (`sap-qm` / `sap-mm`) - the LIMS hold does not move stock; then correct forward (investigation, re-disposition) |
| A COA was already issued to the customer | cannot unsend; issue a corrected/superseding COA and notify - a re-certification, not an edit |
| A sample or test was cancelled in error | re-log/re-add it (a new record); the cancelled one stays in the trail; it is not restored in place |
| A sample was logged against the wrong product/grade/sampling point, resolving the wrong spec | correct the sample's product/grade/sampling point so the right spec resolves, then re-evaluate/re-enter the affected results against it; if results were already authorized against the wrong spec, treat them as authorized-result changes (un-authorize, re-review) and re-issue any COA; the wrong-spec evaluation stays in the trail |
| A result posted from a mis-mapped instrument interface | correct the mapping and re-enter/re-review the affected results; the erroneous values remain in the trail as corrected entries |
| A stability OOS/OOT is confirmed on a study | do not treat it as a one-off: assess the shelf-life/expiry impact on lots already released against that study, raise a field alert / deviation in the QMS, and drive any hold/recall in the ERP/QMS - the stability result can re-open expiry dating far beyond the one sample |
| A spec limit was changed and open samples re-flagged | assess the impact on open and released lots; a re-spec is master data, so the change and its effect on evaluations are logged |
| A LIMS Basic / config change was made in production | a revert is itself a change-controlled config action; assess validation impact - not a simple undo, and may require re-validation |
| A GxP record deletion is requested | in validated production, GxP records are not deletable by design; cancel/void through the defined path instead, logged |

Reversal is almost always **correct forward**, not an undo: the original result, its change history, the
signature, the OOS, and the COA all remain in the immutable trail. What is truly foreclosed is a false COA
already sent and product already shipped on a bad release - neither is retractable, only followed by a
corrected certificate and a recall.

## Guardrails
- Read the sample/test/result status + the resolved spec (product/grade/sampling point/version) + limits + any
  open OOS + the instrument calibration state before acting; re-read at execute (results, reviews, signatures,
  and dispositions all drift as others work).
- **In-spec is two gates, not one.** A result can be within spec limits yet OOT (outside warning/control or
  trend), and a batch is only releasable when every contributing sample is authorized AND in-spec AND its OOS
  resolved. Check all of it before treating a lot as releasable.
- Result authorization, sample completion, and batch release are Part 11 signed decisions: never authorize your
  own entry (segregation of duties), never sign on another's behalf or share credentials.
- Treat an OOS as a stop for investigation, not an override. Never invalidate an OOS, force a result in-spec,
  edit a limit or rounding rule to pass a failing value, or test into compliance.
- Never release a batch on spec with an open OOS, an unauthorized or missing required result, or an
  out-of-calibration instrument behind a value; the disposition is the AND of every contributing sample.
- Issuing a COA certifies the batch to the customer; confirm the spec, that all results are authorized and
  in-spec, and that the reportable result is right before issuing.
- Never make LIMS Basic / spec / workflow configuration changes in the production LIMS. The correct forward
  action is a change-control request to the LIMS owner/config team, built and validated in a sandbox/test
  environment and migrated - not an operator edit in production.
- For anything in the destructive row (OOS override, authorized-result change, spec-gaming, release over an open
  failure, retest-to-pass, prod config change, credential sharing): named approver, re-read of live state, and a logged reason.

## References (load on demand)
- `references/results-specs-and-coa.md` - the sample/test/result status model, result entry -> review ->
  authorization flow, spec resolution (product/grade/sampling point/version) and limit types, the reportable
  result (replicates/calculation/rounding), instrument interfacing and calibration, batch/lot roll-up and
  disposition, and COA generation.
- `references/oos-stability-and-part11.md` - OOS vs OOT, the LabWare laboratory-phase OOS investigation and the
  seam to the QMS, stability studies (protocol, storage conditions, pull points, trending, shelf-life), Part 11
  electronic signatures and ALCOA+ data integrity, and validated config vs data (LIMS Basic, static data, sandbox/production).
