# PharmaSuite - EBR, weigh-and-dispense, deviations, and electronic signatures

The GxP compliance surface of Rockwell FactoryTalk PharmaSuite: how the electronic batch record executes and
releases, how material is dispensed and consumed, how exceptions become deviations, and why an electronic
signature is a hard gate. Read when a task touches an EBR, a dispense, a deviation / exception, review by
exception, an e-signature, or line clearance.

## Contents
- The electronic batch record (EBR) lifecycle
- Weigh-and-dispense and material consumption
- Exceptions vs deviations, and disposition
- Electronic signatures (21 CFR Part 11)
- Review by exception
- Line clearance
- Gating notes

## The electronic batch record (EBR) lifecycle
The EBR is the executed record of a batch against its master recipe: every phase, parameter value, dispense,
signature, and exception, in order, permanently. Lifecycle:
- **In Execution** - the batch is running; phases post progress, dispenses and consumptions record actual
  lots, exceptions flag as they occur.
- **Complete** - the last operation finished; the finished quantity posted and (via the ERP hand-off) a goods
  receipt was triggered.
- **In Review** - the executed record is reviewed. Under **review by exception**, only flagged exceptions /
  deviations are reviewed, not every step.
- **Approved / Released** - review passed; **this approval is the batch release** (the product may ship /
  advance). **Rejected** - the GxP rejection of the batch.

The EBR is the compliance system of record for the batch. It cannot be edited after signing; a correction is
an appended record, never an overwrite.

## Weigh-and-dispense and material consumption
- **Weigh-and-dispense** - a dispensing step that reserves a specific material **lot**, weighs the required
  quantity against a **tolerance**, verifies the material / container (often by scan), captures the weight,
  and requires an **electronic signature**. A dispense outside tolerance **blocks or flags** (an exception).
- The dispensed container is later **consumed** into the batch at the relevant phase / operation. Consumption
  ties the **actual lot and quantity** to the batch **genealogy / as-built**.
- Why it bites: a wrong lot mis-formulates the batch and mis-records traceability even when the quantity is
  correct; expiry / FEFO rules govern which lot is valid; and the genealogy is permanent, so a wrong
  consumption is corrected forward, not erased.

## Exceptions vs deviations, and disposition
- An **exception** is a runtime event the system flags in the EBR: an out-of-tolerance dispense or data value,
  an equipment fault, a sequence / interlock violation, a missed signature. It is a **flag**, not a decision.
- A **deviation** is the quality record opened to investigate and resolve an exception (or a manual
  observation). It must be **dispositioned**: **use-as-is**, **rework**, **scrap**, or **reject**. An **open**
  deviation **blocks batch release**.
- A single review can **split** the disposition across a batch quantity: part use-as-is, part rework, part
  scrap / reject. Use-as-is and rework are **committing**; scrap and reject are **destructive**. Gate each
  path, not the whole disposition at the lowest risk.
- Recording the exception contains nothing on its own - the **disposition** is the gate that decides release.

## Electronic signatures (21 CFR Part 11)
- An electronic signature is an **authenticated, attributed** sign-off with a **meaning** (performed by /
  verified by / reviewed by / approved by). It binds a specific user identity to a specific record at a
  specific time.
- A phase, dispense, parameter change, or EBR step that requires a signature **cannot complete without it** -
  it is a blocking precondition, not an optional edge case.
- Once applied, a signature is **permanent**: it cannot be removed, cannot be signed on another's behalf, and
  a correction is an **appended** record / signature, never an edit of the original.
- The full **audit trail** captures who / what / when / why for every action; a mistake is corrected by a
  forward transaction, and the correction (and the original) both stand.

## Review by exception
Review by exception (RBE) is the pharma execution+review model: because the executed EBR is built and checked
in real time, the post-execution review examines only the **flagged exceptions / deviations**, not every
step. The reviewer's **approval releases the batch**. Consequence: approving an EBR with an **unresolved
deviation** releases a batch that should be held - the approval is the single most consequential write in the
flow, not a formality.

## Line clearance
Line clearance is a **gated verification** that the line, equipment, and area are clear of the prior product,
labels, and materials before a new batch starts. It is signed and recorded. Skipping it risks
**cross-contamination** and produces an EBR exception. It is a precondition on starting the next batch, not a
checkbox to click through.

## Gating notes
- Dispense within tolerance + consume material = committing (material + genealogy + signature).
- Raising an exception / opening a deviation = reversible (a record before disposition).
- Disposition use-as-is / rework = committing; disposition **scrap / reject** = destructive.
- Any **electronic signature** = a hard gate on the write it belongs to.
- **Review-by-exception approval** = committing and is the **batch release**; **reject** = destructive (GxP
  rejection).
- Editing / deleting a **signed** EBR record = destructive (append a correction instead).
- Line clearance = a gated precondition before a new batch.
