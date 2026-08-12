# Opcenter Execution - holds, nonconformance, data collection, review and e-sign

The containment and compliance controls that decide whether stock is released. Read when a workflow places or
releases a hold, raises or dispositions a nonconformance, records data against spec limits, signs a step, or
reviews/approves a batch record. Holds, NC, and data collection exist in the Camstar lineage (EX Discrete /
Semiconductor / Electronics / Medical Device); the batch record, review by exception, line clearance, and
weigh-and-dispense are the SIMATIC IT lineage (EX Process / Pharma).

## Contents
- Holds: container, future, global
- Data collection and spec limits
- Nonconformance and MRB disposition
- Electronic batch record and review by exception
- Electronic signatures / 21 CFR Part 11
- Line clearance and weigh-and-dispense
- Equipment / automation integration

## Holds: container, future, global
- **Container hold** - stops one container from moving. Its step/resource state is preserved; releasing returns
  it to flow. Placing is reversible; the **reason** governs whether it may be released.
- **Future hold** - applies at a coming step, so a container is caught when it arrives there (e.g. hold at final
  test pending a document). It affects containers not yet at that step.
- **Global / lot-family hold** - holds many containers by product, lot family, component lot, or equipment -
  including containers not yet created. Releasing it can free a large scope at once; scope it before releasing.
- **Asymmetry**: placing a hold withholds stock (committing, recoverable); **releasing** returns stock to flow
  and belongs to the role that set it plus a resolved reason (the NC dispositioned). Do not lift a hold to hit a
  schedule - that bypasses the containment.

## Data collection and spec limits
- A step defines **data-collection** parameters, each with **spec limits** (and sometimes control limits).
  Values are entered manually or fed from equipment.
- An **out-of-limit** value can **auto-place a hold** on the container and/or **block Track Out**. That is the
  control doing its job - forcing the move or editing the value to pass is a data-integrity breach, and the
  Part 11 audit trail records the edit (who, what, old/new, when, why).
- **Required** characteristics must be recorded before Track Out; skipping one blocks the move or forces a
  reject. Re-recording before sign-off is a correctable draft; after e-sign it is a controlled record.

## Nonconformance and MRB disposition
- A **nonconformance (NC) / defect** is raised against a container and step, with a defect code / reason. Raising
  it is reversible (a record); it contains nothing on its own.
- The **MRB (material review) disposition** is the gate that decides release:
  - **Use-as-is** - releases the nonconforming quantity to continue. A committing decision on record.
  - **Rework / repair** - loops the container to a rework route; re-consumes and re-inspects (recoverable).
  - **Scrap** - destroys the quantity; a loss with value and yield impact (destructive).
  - **Return** - reverses the receipt / commitment back to the source (destructive; re-opens supply).
- A **split disposition** sends different quantities down different paths in one decision - gate each path on
  its own class; do not gate the whole NC at the lowest-risk path.
- An NC/hold on one unit in a genealogy can recommend **containment of the family** (same batch, same component
  lot). Dispositioning one container does not clear the related ones.

## Electronic batch record and review by exception
- The **master batch record (MBR)** is the approved recipe/procedure; executing an order against it produces the
  **electronic batch record (eBR)** - the as-executed record with data, signatures, and deviations.
- **Review by exception (RBE)** - instead of reviewing every page, reviewers examine only the flagged
  **exceptions / deviations**. **Approval releases the batch**; rejection holds/quarantines it.
- Approving with an **unresolved exception** releases a batch that should be held - the approval IS the release,
  so it is the most consequential write in the flow. Confirm every exception is dispositioned before approving.
- The eBR state runs **not started -> in execution -> complete -> in review -> approved (released) / rejected**.

## Electronic signatures / 21 CFR Part 11
- A required **electronic signature** is an authenticated, attributed sign-off (username + password / second
  factor, with meaning: reviewed / approved / performed). The step or record **cannot complete without it**.
- It is **permanent and attributed**: it cannot be signed on another person's behalf, and it cannot be removed
  once applied. A mistake is corrected by a **new, appended** record/signature, never by an erase.
- Part 11 also mandates the **immutable audit trail**: every create/change/delete of an electronic record is
  captured with who/what/when/why. Treat the signature and the audit trail as hard compliance infrastructure.

## Line clearance and weigh-and-dispense
- **Line clearance** (Process/Pharma) - a gated verification, before starting a new batch, that the line is
  clear of prior product, labels, and materials. Skipping it risks cross-contamination and a batch-record
  exception. It is a check with a signature, not a checkbox.
- **Weigh-and-dispense** - dispensing a component against the batch consumes it into the batch with a **signed,
  tolerance-checked** record. Dispensing outside the component tolerance blocks or flags; a wrong dispense
  mis-formulates the batch and surfaces at review.

## Equipment / automation integration
- On automated lines, equipment drives transactions: **SECS/GEM** (semiconductor) and **OPC UA** (broad) can
  Track In/Out, feed data collection, and raise holds directly.
- An equipment-driven **Track Out commits exactly like a manual one** - it posts WIP and backflushes; automation
  is not an exemption from the gate. A resource must be **up and qualified** to accept a Track In; a message
  into a down/disqualified resource is blocked or flagged, and overriding qualification pushes product through
  uncertified equipment.
