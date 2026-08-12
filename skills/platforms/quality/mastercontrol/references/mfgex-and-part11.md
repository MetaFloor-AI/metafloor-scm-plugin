# MasterControl Manufacturing Excellence (Mfg-Ex) + Part 11 / validation (deep reference)

Load when reasoning about an electronic batch/production record, review by exception, enforced flow, an
in-process exception, batch release, or the validated-system rules (signatures, config vs data, environments).
SKILL.md carries the operating judgment and the read/write/destructive matrix; this file carries the
mechanics. One fact lives in one place - the classification stays in SKILL.md.

## Contents
- Master template vs production record
- Executing a production record (enforced flow, in-process data)
- Exceptions and out-of-limit handling
- Review by exception
- Batch/lot release (disposition)
- The seam to LIMS and the ERP
- Part 11 electronic signatures and ALCOA+
- Validated configuration vs data
- Validation vs production environments

## Master template vs production record
Manufacturing Excellence replaces the paper batch record with an electronic one (EBR / EPR / eDHR).
- **Master template** - the approved, version-controlled batch-record design: steps, parameters, limits,
  required signatures, and enforced order. It is **configuration** - a validated artifact. Editing it changes
  every future batch and is a change-controlled, validated action.
- **Production record** - a **data** instance issued from the master template for one specific batch/lot.
  Operators enter values and sign steps as the batch runs; exceptions attach to this instance.
Confusing the two is a common, serious error: editing the template to "fix" one batch changes all future
batches; editing an issued record's data outside the exception path hides a batch deviation.

## Executing a production record (enforced flow, in-process data)
- **Enforced flow** - the record enforces step order and required entries; an operator cannot skip a required
  step or sign out of order. This is a control, not a UI nicety.
- **In-process data entry** - values are entered against defined **limits**; entry before the step is signed is
  a correctable draft, but once the step is signed the entry and its signature are on the record.
- **Forced entry / override** - forcing a value or an out-of-order step is permitted only as a logged
  **exception**, never as a silent edit; the override itself becomes something the review must catch.

## Exceptions and out-of-limit handling
- An **exception** is a flagged departure: an **out-of-limit** value, a skipped/out-of-order step, or an
  enforced-flow override.
- An out-of-limit entry **raises an exception that blocks clean completion** - the record cannot be
  completed/released with an open, un-dispositioned exception.
- **Dispositioning** an exception means justifying it, linking a deviation/NCR where the departure is real, and
  routing it for the required review. Entering a value inside limits to avoid the flag is **falsification** -
  the original entry stays in the immutable trail regardless.

## Review by exception
The batch-record review reviews **only the flagged exceptions**, not every entry - that is the efficiency of
the method and also its single point of failure:
- Its safety depends entirely on the flags being right. A **suppressed, overridden, or mis-classified**
  exception is never surfaced at review and releases unverified.
- Never treat "no exceptions to review" as "the batch is clean" without confirming exceptions were actually
  raised where limits were breached. Check that the flagging fired, not just the review queue.

## Batch/lot release (disposition)
- **Batch release** is the QA disposition that commits product to ship. It requires the production record
  complete, all required signatures captured, and every exception dispositioned (with linked deviations
  resolved).
- **Releasing over an open exception, an open linked deviation, or a missing signature ships unverified
  product.** The release signature is permanent.
- **Hold** withholds the batch and is reversible by release; **release** (or lifting a hold to push product
  through) is the committing/destructive direction and belongs to the disposition owner.
- MasterControl records the disposition; it does **not** move physical stock. Un-shipping a bad release is not
  possible here - the physical hold/recall posts in the ERP.

## The seam to LIMS and the ERP
- The **lab number** that feeds a release lives in the LIMS (`labware`) or SAP QM
  (`sap-qm`); MasterControl consumes the result, it does not authorize it.
- The **physical goods movement** after a batch decision (release QI stock, scrap, return) posts in the ERP
  (`sap-mm` / `sap-qm`). A batch hold/recall is a parallel physical action, not a
  MasterControl state change.

## Part 11 electronic signatures and ALCOA+
- A signature captures the **signer + signature meaning (Authored/Reviewed/Approved/Released) + timestamp**,
  bound to the record; it is permanent, attributable, and never removable.
- **Segregation of duties** and role-based signing mean the wrong person cannot (and must not) sign a step;
  never sign on another's behalf, share credentials, or back-date.
- **ALCOA+** (Attributable, Legible, Contemporaneous, Original, Accurate, + Complete, Consistent, Enduring,
  Available) is the data-integrity standard the audit trail exists to satisfy. A **reason for change** and a
  correct signature meaning are compliance evidence; a placeholder falsifies the record.
- The **audit trail is immutable**: every entry, change, step advance, and signature is kept with user +
  timestamp + old/new value. A correction is a new entry, never an erasure.

## Validated configuration vs data
- A **data** action edits a record (a field on a deviation, a value in a production record). A
  **configuration** action edits a route template, form, master template, exam, or security role.
- In the production environment, a configuration change is a **validated computer-system change** requiring
  change control and validation evidence - regardless of how small the field looks. An ad-hoc prod config
  change breaks the validated state and is itself an inspection finding.

## Validation vs production environments
- Configuration is built and tested in a **validation/sandbox** environment and **promoted to production**
  under change control; **records do not copy across**.
- A behavior proven in validation is not live until promotion; a validation-environment record is throwaway.
- A revert of a production config change is itself a change-controlled, validated action - not a simple undo,
  and it may require re-validation.
