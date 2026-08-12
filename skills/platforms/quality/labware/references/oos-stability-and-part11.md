# LabWare LIMS - OOS/OOT, stability, Part 11 signatures, validated config

The controls that make LabWare a validated GxP system and decide what an operator may and may not do around a
failure, a trend, a stability study, a signature, and a configuration change. Read when a task hits an OOS or
OOT, works a stability study, e-signs or authorizes, or would touch LIMS Basic / spec / static-data
configuration.

## Contents
- OOS vs OOT
- The OOS laboratory investigation (and the QMS seam)
- Stability studies
- Electronic signatures (21 CFR Part 11 / Annex 11) and segregation of duties
- The immutable audit trail and ALCOA+
- Configuration vs data (LIMS Basic, static data, sandbox/production)

## OOS vs OOT
- **OOS (out of specification)** - the **reportable result** is outside a **spec limit**. LabWare flags it
  automatically and (if configured) opens an **OOS record/workflow**. An OOS is a **stop for investigation**,
  not a rejected batch and not a value to overwrite.
- **OOT (out of trend)** - the result is **inside spec** but outside a **warning/control/action limit** or off
  its historical trend. It is a leading indicator - an emerging drift - not a failure. Especially in stability,
  an OOT foreshadows a future OOS and a shelf-life problem.
- They are **two independent gates**: in-spec is not the same as in-trend. Judging only spec limits misses the
  early signal; treating an OOT as a failure over-rejects.

## The OOS laboratory investigation (and the QMS seam)
- LabWare owns the **laboratory phase** of the OOS: confirm the result is not a lab artifact - check the
  analyst technique, the calculation, the instrument calibration/state, the standards and prep, and the sample
  itself. Only an **assignable, documented laboratory error** justifies **invalidating** the original result.
- **Confirming the OOS is the default; invalidating it is the exception.** The baseline outcome of the lab
  phase is that the OOS **stands** (confirmed) and the batch heads toward reject/hold pending the full
  investigation. Invalidation - declaring the result void for an assignable cause - is the exceptional path
  that must be justified and approved; do not treat invalidation as the reflex to "clear" an OOS.
- **Retest vs resample are different, and the protocol decides which.** A **retest** re-measures the **same
  prepared sample/solution**; a **resample** draws a **new sample** from the batch. The OOS protocol dictates
  which is permissible and when - conflating them (e.g. resampling for a fresh number when only a retest is
  allowed) is testing-into-compliance by another name.
- **You cannot test into compliance.** Repeating the test until a passing value appears and discarding the OOS
  is falsification. A retest or resample happens only under the OOS protocol (defined replicates, a second
  analyst, pre-approval), and the original OOS and every retest stay in the trail.
- **Invalidating an OOS is a destructive quality decision.** The system flags OOS with no judgment; declaring
  it invalid (assignable cause) is the human call that waives a failure - it belongs to the documented
  investigation and an approver, not the analyst at the keyboard.
- **The seam:** the full root-cause investigation, the **deviation**, and the **CAPA** are managed in the QMS
  (`veeva-vault-qms` or `mastercontrol`); the **physical stock disposition** (block, scrap,
  return, release QI stock) posts in the ERP (`sap-qm` / `sap-mm`). LabWare's OOS handling
  is the lab-phase evidence that feeds those - do not mistake invalidating an OOS in LIMS for closing the
  quality investigation.

## Stability studies
- A **stability study** runs a product under defined **storage conditions** (e.g. 25C/60%RH long-term,
  40C/75%RH accelerated) against a **protocol** that sets **pull points / timepoints** (e.g. 0, 3, 6, 9, 12, 18,
  24 months) and the tests per pull.
- LabWare **auto-generates the samples** per pull point on schedule. Missing a pull, or entering a timepoint
  late, breaks the study's integrity; the pull schedule is part of the validated protocol, not a suggestion.
- Results **trend across timepoints** and drive **shelf-life / expiry** and re-test dates. A stability **OOS or
  OOT** is rarely a one-off: a confirmed stability failure can trigger a **field alert** and a shelf-life or
  expiry-date impact on product already released - far beyond the one sample.
- Because a stability result can re-open shelf-life for released lots, treat a stability OOS/OOT with elevated
  scrutiny and route it to the QMS, not as a routine lab disposition.

## Electronic signatures (21 CFR Part 11 / Annex 11) and segregation of duties
- **Authorizing/approving a result, completing a sample, and releasing a batch** capture the **signer's
  credentials**, a **signature meaning** (Reviewed / Approved / Authorized), and a **timestamp**, and **link**
  the signature to the specific result/record (Part 11 §11.70 signature-to-record linking; §11.50 manifestation).
- A signature is **permanent and attributable**: it cannot be removed or edited and it appears on the record's
  audit trail. Modifying an authorized result does not delete the signature - it un-authorizes the result and
  the prior signature stays as history.
- **Segregation of duties:** the analyst who **entered** a result cannot **review/authorize** it. Signing both
  roles, **sharing a login**, or **signing on another's behalf** is a data-integrity violation, not a shortcut.
- Treat a required signature as a **hard gate**: the step cannot complete without it, and forcing past it (or
  authorizing around a missing required result) falsifies the record.

## The immutable audit trail and ALCOA+
- LabWare keeps a **system-generated, immutable audit trail** of every **result entry, change (with a change
  reason), status change, and e-signature**, with **user + timestamp + old value + new value**.
- It **cannot be edited or deleted**. A mistake is corrected by a **new entry** (a re-entry with a reason, a
  superseding COA, a corrective record) - never by erasing the original. Every prior value stays visible to an
  inspector; a rushed wrong result is inspectable forever.
- **ALCOA+** is the data-integrity standard the trail supports: Attributable, Legible, Contemporaneous,
  Original, Accurate (+ Complete, Consistent, Enduring, Available). A **placeholder change reason**, a required
  field filled with junk to clear a gate, or a back-dated entry violates it and is itself a finding.

## Configuration vs data (LIMS Basic, static data, sandbox/production)
- A **data** action creates or edits a **record** - a sample, a result, a disposition - normal operator work,
  gated per the read/write/destructive matrix.
- A **configuration** action changes **how the system behaves**: **LIMS Basic** subroutines/calculations,
  **spec versions and limits**, **rounding rules**, workflow triggers, **static data** (products, analyses,
  users/roles). In validated production this is a **computer-system change**.
- A production config change must go through the customer's **change control and validation**: assessed, built
  and tested in a **sandbox/test** environment, and migrated - **not hand-edited in production**. Changing a
  calculation or a limit in the production LIMS changes how **every future result** is evaluated and breaks the
  validated state; it is an inspection finding.
- An operator/agent acting on samples and results **does not touch production configuration**. If a task seems
  to need a spec change or a calculation fix, that is a change-control request to the LIMS owner, not an action
  to perform. In validated production, GxP records are **not deletable** by design - cancel/void through the
  defined path instead.
