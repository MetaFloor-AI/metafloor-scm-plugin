---
name: rockwell-factorytalk
description: "Rockwell FactoryTalk MES / production management - safe shop-floor execution across FactoryTalk ProductionCentre (FTPC), PharmaSuite (GxP), FactoryTalk Batch (ISA-88 procedural control), and FactoryTalk Historian: production / work orders, master and control recipes, procedures / operations / phases, the phase state model and commands (Start / Hold / Restart / Stop / Abort / Reset), equipment arbitration and unit binding, weigh-and-dispense and material consumption, genealogy, electronic batch records (EBR), exceptions and deviations, review by exception, electronic signatures (21 CFR Part 11 / GxP), equipment integration (PhaseManager / Logix). Use when the connected MES is Rockwell or FactoryTalk, or the user mentions FTPC, PharmaSuite, FactoryTalk Batch, a master or control recipe, a phase or operation, phase hold / abort / restart, weigh and dispense, an EBR, a deviation or exception, review by exception, an e-signature, Part 11 / GxP, a batch abort, or line clearance."
---

# Rockwell FactoryTalk MES - operating the shop floor safely

Rockwell's FactoryTalk MES layer runs the plant floor and, in life sciences, the compliance record with it.
It authorizes production against an order, drives material through a recipe or routing, commands the
equipment that physically makes the product, records what was consumed and measured, and decides whether the
result is fit to release. The model differs by product: **FactoryTalk Batch** and **PharmaSuite** run the
**ISA-88 procedural model** (procedure -> unit procedure -> operation -> **phase**) against **recipes**;
**FactoryTalk ProductionCentre (FTPC)** runs **work orders** through **operations** on a routing; **FactoryTalk
Historian** is the time-series process record. What makes it dangerous is simple: **running a phase or
operation is not a status flip - it commands real equipment (opens valves, doses, heats, agitates) and
consumes material in the same transaction**, and in a regulated line an **electronic signature** makes that
record permanent and legally attributed. This skill classifies those actions so the harness can gate them,
plus the edge states (phase failure recovery, equipment arbitration, review by exception, e-sign) and
recovery paths that decide whether a mistake is fixable.

## When this applies
Connector is Rockwell FactoryTalk (FTPC / PharmaSuite / FactoryTalk Batch / Historian) and the work is
shop-floor execution. When NOT:
- a different MES: Siemens Opcenter / Camstar / SIMATIC IT -> `siemens-opcenter`
- SAP's MES: SAP Digital Manufacturing (DM / DMC) -> `sap-dm`
- ERP material/inventory postings, the goods receipt MES triggers, procurement, valuation -> `sap-mm`
- a formal quality management system / inspection lots / CAPA / complaints on the ERP or QMS side -> `sap-qm`
- within the FactoryTalk family but a different product: **HMI / SCADA** = FactoryTalk View; **OEE / downtime**
  = FactoryTalk Metrics; **asset / change management / controller backups** = FactoryTalk AssetCentre;
  **plant analytics / ML** = FactoryTalk Analytics. This skill is MES **execution** (FTPC / PharmaSuite /
  Batch) plus the Historian read - shop-floor build and its record, not visualization, OEE, or asset config.

Seam with ERP/QM: FactoryTalk owns the execution truth (where a batch is, what phase it is in, what was
consumed and dispensed, as-built genealogy) and dispositions defects at the point of manufacture; ERP
(`sap-mm`) values the inventory and books the finished-goods receipt FactoryTalk triggers on batch
completion, and a formal QMS (`sap-qm`) owns inspection lots and CAPA. FactoryTalk contains and
dispositions on the floor; the QMS/ERP is the financial and compliance system of record downstream.

## Contents
- Object & state model
- Vocabulary that bites
- Operations: read / write / destructive
- Reclassification rules
- Worked example (a batch, end to end)
- Gotchas that bite
- Edge states & special cases
- Recovery patterns
- Guardrails
- References

## Object & state model (reason about state, not nouns)
- **Order (production / work order)** - authorizes building a quantity of a product; usually downloaded from
  ERP. States: **Created / Scheduled** -> **Released** (the floor may build and consume against it) ->
  **Started / Active** -> **Completed** -> **Closed**. Releasing binds material and capacity; completing posts
  the finished quantity back to ERP.
- **Master recipe / Master Batch Record (MBR)** - the approved production template (formula + procedure +
  material list + equipment requirements + sign-off rules). Lifecycle: **In Preparation** (draft) -> **In
  Review** -> **Approved / Effective** -> **Retired / Obsolete**. Editing a draft is reversible; approving it
  to effective is a change-control event; an **effective** recipe governs every new batch that instantiates
  it. Detail in `references/isa88-phases-and-equipment.md`.
- **Control recipe / batch** - the executed instance of a master recipe, **bound** to a specific order and to
  specific equipment (unit). Batch states: **Created** -> **Running** -> (**Held**) -> **Complete** or
  **Aborted**. The control recipe is one batch; the master recipe is the fleet.
- **ISA-88 procedural model** - **procedure -> unit procedure -> operation -> phase**. The **phase** is the
  smallest element that actually commands equipment. In FTPC discrete work the analogue is an **operation** on
  a routing (start / complete), but the gating logic is the same: the element that runs equipment and consumes
  material is the commit.
- **Phase state (per running phase / PhaseManager)** - **Idle** -> **Running** -> **Complete**, with the
  branches **Pausing / Paused** (a light pause, resumed by **Resume**), **Holding / Held** (paused to a safe
  state, resumed by **Restart**), **Stopping / Stopped**, and **Aborting / Aborted**; **Reset** returns a
  Stopped / Aborted / Complete phase to Idle. Hold/Restart and Pause/Resume are recoverable; **Stop and Abort
  are terminal for the run** (only Reset to Idle, never Restart). Detail in
  `references/isa88-phases-and-equipment.md`.
- **Equipment / area model** - **process cell -> unit -> equipment module -> control module**. A batch
  **acquires** (binds to) a unit; shared equipment is **arbitrated** so two batches do not run into the same
  vessel. A unit must be **available and qualified** to run a phase.
- **Material** - material classes, **containers**, and **lots** with expiry / FEFO. **Weigh-and-dispense**
  produces a signed, tolerance-checked dispensed container that is later **consumed** into the batch; actual
  consumed lots write the batch **genealogy / as-built**. Detail in `references/ebr-deviations-and-signatures.md`.
- **Electronic batch record (EBR)** (PharmaSuite) - the executed record of a batch: every phase, parameter,
  dispense, signature, and exception. States: **In Execution** -> **Complete** -> **In Review** -> **Approved
  / Released** or **Rejected**. Under **review by exception**, only flagged exceptions are reviewed; approval
  is the batch release.
- **Exception / deviation** - an **exception** is a runtime event flagged in the EBR (out-of-tolerance value,
  equipment fault, sequence violation); a **deviation** is the quality record that must be **dispositioned**.
  An open deviation blocks release. States: **Open** -> **Dispositioned** (use-as-is / rework / scrap /
  reject) -> **Closed**.
- **Hold** - a containment that stops a batch, order, material lot, or unit from proceeding. States:
  **Active** -> **Released**. Placing is reversible; releasing is the gate.
- **Historian tag / point** - a time-series data point in **FactoryTalk Historian** (OSIsoft PI lineage) with
  an archived value history. Reads and trends are safe; editing archived values is a data-integrity act.

## Vocabulary that bites
- **Phase** - the smallest ISA-88 procedural element that commands equipment. Starting a phase runs real
  logic in the controller (dose, transfer, heat, agitate); it is not a status flip. Confusing "advance the
  phase in the client" with "run the phase" under-gates the physical action.
- **Master recipe vs control recipe** - the master recipe is the approved, versioned template governing every
  new batch; the control recipe is one bound, executing batch. Editing an **effective** master recipe is a
  fleet change; editing the control recipe is one batch. Not interchangeable.
- **Binding / equipment acquisition (arbitration)** - a batch **acquires** a unit exclusively; a **class-based**
  recipe binds to any qualified unit at runtime, an **instance-based** one is fixed. Re-read which unit a
  batch actually bound before acting - a class-based recipe may not be on the vessel you assume.
- **Phase command (Start / Hold / Restart / Stop / Abort / Reset / Pause / Resume)** - the S88 command set.
  **Hold** pauses to a safe state and **Restart** resumes it; **Pause / Resume** is a lighter pause at the
  next safe step - both are recoverable. **Stop** (controlled) and **Abort** (fast) both **end the run
  terminally**: from Stopped / Aborted you can only **Reset** to Idle, never Restart, and Abort usually loses
  the in-process product. **Reset** clears a finished / stopped / aborted phase back to Idle.
- **Weigh-and-dispense** (PharmaSuite) - a signed, tolerance-checked dispensing step that reserves and
  consumes a specific material lot into the batch. Dispensing outside tolerance blocks or flags; a wrong lot
  mis-formulates the batch and mis-records genealogy.
- **Material consumption / genealogy (as-built)** - consuming BOM material at a phase/operation ties the
  actual lots and equipment to the batch's permanent as-built record. It scopes recall; a wrong consumed lot
  cannot be cleanly rewritten, only corrected forward.
- **Electronic batch record (EBR)** - the executed record; permanent once signed. **Review by exception**
  reviews only flagged exceptions, and **approval releases the batch**.
- **Exception vs deviation** - an exception is the runtime flag in the record; a deviation is the quality
  record that must be dispositioned. Recording the exception contains nothing on its own; the **disposition**
  decides release, and an open deviation blocks it.
- **Electronic signature (e-sign) / 21 CFR Part 11** - an authenticated, attributed sign-off with a **meaning**
  (performed by / verified by / approved by). The phase, dispense, or EBR step cannot complete without it;
  once applied it is permanent and cannot be signed on another's behalf.
- **Formula / parameter (setpoint)** - the recipe values downloaded to phases. A runtime parameter change on
  a running batch alters what the equipment does; it is signed and audited, and deviates the batch from the
  approved recipe unless it stays inside recipe-allowed limits.
- **Line clearance** (PharmaSuite / process) - the gated verification that the line and equipment are clear of
  prior product before a new batch. Skipping it risks cross-contamination and an EBR exception.
- **PhaseManager / equipment phase** - the phase state machine that lives in the ControlLogix controller;
  FactoryTalk Batch commands it. A command from the batch server runs PLC logic on live equipment - the MES
  action and the physical action are the same event.

## Operations: read / write / destructive
Classify every operation family by what it does to state, to material, and to the compliance record. The
names below name the action-kind; the class is the same whether the connector drives the FactoryTalk Batch
server, an FTPC operation, a PharmaSuite EBR step, an eProcedure prompt, or an equipment message. The harness
maps the customer's real connector onto these classes - it is the connector layer that translates these
action-kinds into the customer's specific API calls, so the skill classifies the action and the harness gates
and runs it. No tool names - kinds of action.

| Class | FactoryTalk MES operation families | Gate | Why |
|---|---|---|---|
| **Read** | display an order / batch / control recipe and its status and current phase; batch execution state and per-phase states; the master recipe / routing and formula; material dispensing records and consumed lots; **genealogy / as-built**; the exception and deviation list and dispositions; the hold list; equipment / unit status, qualification, and arbitration ownership; the EBR and its review state; **Historian tags / trends**; the audit trail | always pass | no state change; read batch + phase state + holds + material + unit ownership before any write, re-read at execute |
| **Write (reversible)** | author or edit a master recipe **while In Preparation** (formula, procedure, material list); create / schedule an order before release; create a batch (control recipe instance) before it starts; **cancel a Created / Scheduled order or a not-yet-started batch** (nothing consumed yet - a Released order with material consumed is not cleanly cancellable, see the destructive row); **acquire / bind a unit** before the batch runs material on it (reservation, releasable while idle); place a **hold** on a batch / material / unit, or **Hold / Pause** a running phase (protective park to a safe / next-safe step); **Reset** a terminal phase to Idle for reuse; record in-progress data collection **before sign-off**; raise an exception / deviation record before disposition; download a formula / parameter to a phase **before Start** | gate one at a time | a draft, a reservation, a containment, or a correctable record; no new equipment run, no material consumed, no disposition made |
| **Write (committing)** | **Start / run a phase or operation** = command equipment (dose, transfer, heat, agitate) and, where the step has a BOM, consume material; **weigh-and-dispense** a material = reserve + consume a lot with a signed record; explicitly **consume / add** a material into the batch; **complete a phase / operation** = post progress + material consumption; **complete a batch / order** at the last step = post finished quantity + trigger the ERP goods receipt; **change a formula parameter (setpoint) at runtime** on a running batch; **Restart / Resume** a phase (resumes live equipment from Held / Paused); **disposition a deviation** use-as-is / rework; **release a hold** (returns stock / a batch to flow - the gated direction); **sign** a phase, dispense, or EBR step (e-sign); **approve a batch under review by exception** = release the batch; **release / approve a master recipe to effective** (change-control); **qualify a unit** (a verified certification decision) or **disqualify a unit** (protective, but can strand an in-process batch) | gate + human approve | binds material and the physical / financial world: runs equipment, consumes inventory, certifies a record, releases a batch |
| **Destructive / irreversible** | **Abort a batch or phase** (terminal; equipment to safe state, in-process product usually lost); **Stop** a phase (terminal for the run - only Reset to Idle, never Restart; in-process material impact varies by context); **scrap** a batch quantity or a dispensed container (yield + value loss); **force a phase transition / skip a step / manual-mode override** past interlocks or a failed phase; **override** an out-of-tolerance dispense or data value, equipment arbitration, or a down / disqualified / unverified unit to force a run; **disposition a deviation -> scrap or reject**; **reject a batch record** (the GxP rejection); **modify or delete a signed EBR record / signature** (appending a corrective record is the permitted forward path; changing the original is the destructive act); **change an effective master recipe / route while batches are in flight**, or **retire an effective master recipe** (Effective -> Retired / Obsolete) - both fleet-level change-control; **edit or backfill Historian archive data** (corrupts the process record - a data-integrity breach) | hard gate + named approver + re-read | permanent audit trail; runs / destroys / re-routes material and equipment; crosses a GxP / compliance boundary; cannot be cleanly undone |

## Reclassification rules (read this)
- **Running a phase is a physical commit, not a client action.** Advancing a phase in Batch View sends a
  command that runs controller logic on live equipment and (if the step has a BOM) consumes material. It is
  committing even though it "just runs the next step" - gate it as a material + equipment posting, never as a
  navigation step.
- **Placing a Hold / Pause is protective; resuming and stopping are the gated directions.** Holding or
  Pausing a running phase parks it to a safe state - low-friction and reversible (when in doubt, hold).
  **Restart / Resume** resumes live equipment. **Stop** and **Abort** end the run terminally: from Stopped /
  Aborted you can only Reset to Idle, never Restart, and Abort usually loses the in-process product, so a new
  batch is needed. Gate each S88 command by direction, not as one lump:

  | Command | What it does | Class |
  |---|---|---|
  | **Start** | runs the phase on live equipment (+ BOM consume) | Write (committing) |
  | **Hold / Pause** | parks the phase to a safe / next-safe state (protective) | Write (reversible) |
  | **Restart** (from Held) / **Resume** (from Paused) | resumes live equipment from its safe state - match the command to the source state | Write (committing) |
  | **Stop** | terminal controlled end of the run (Reset to Idle only) | Destructive |
  | **Abort** | terminal fast end; in-process product usually lost | Destructive |
  | **Reset** | clears a Complete / Stopped / Aborted phase to Idle for reuse (does not clean or re-qualify the equipment) | Write (reversible) |
- **A hold is asymmetric - placing is protective, releasing is the gate.** Placing a hold is a low-friction,
  reversible containment: when in doubt, hold. **Releasing** it returns the batch / material to flow, belongs
  to the role that set it, and needs the reason resolved (the deviation dispositioned) - do not lift a hold to
  hit a schedule.
- **A split deviation disposition is several actions - gate each path.** One review decision can send part of
  a batch use-as-is, part to rework, part to scrap or reject. Use-as-is / rework are committing; scrap /
  reject are destructive. Do not gate the whole disposition at the lowest risk.
- **An effective-recipe edit is a fleet change, not a local edit.** Changing an effective master recipe /
  formula / route re-instantiates for every new batch and, if applied mid-flight, re-routes or re-consumes
  in-flight batches at their next operation. Treat it as destructive / change-controlled - a pre-effective
  (In Preparation) edit is the only reversible kind.
- **An e-signature is a hard gate, not a field.** In a GxP setup a phase, dispense, parameter change, or EBR
  step may require an electronic signature; the step cannot complete without it and it is permanent, so treat
  it as a blocking precondition on that write, never an optional edge case.
- **A parameter change on a running batch is a recipe deviation unless in-limits.** Changing a setpoint
  mid-batch alters what the equipment does; it is signed and audited, and it deviates the batch from the
  approved recipe unless it stays inside recipe-allowed operating limits.
- **Disqualifying a unit is not always a protective-committing change.** Disqualifying an **idle** unit is a
  protective certification change (committing); disqualifying a unit with an **in-process batch** strands that
  batch - it forces an Abort + scrap and removes a compliance certification, so treat that case as
  destructive. And **Reset** to Idle is a reversible state transition, not a clean-and-requalify: verify the
  unit's physical (residual material) and compliance (qualification, line clearance) state independently
  before the next Start.
- **Command scope: phase vs unit procedure vs batch.** Hold / Stop / Abort exist at the phase, unit-procedure,
  and batch level. A **batch-level Abort cascades** to every running phase in the batch; a unit-procedure Hold
  holds its phases. Read the scope before issuing - a batch-level command is many phase commands at once.

Universal rules to teach: read the batch state + current phase + holds + unit ownership + material
availability before any write and **re-read at execute** (another operator or the equipment may have moved,
held, aborted, or consumed since you read); never force a phase past an out-of-tolerance value or a fault,
override arbitration or equipment qualification, lift a hold, or skip a step to go faster; a hold or open
deviation means stop; an e-signature and a review-by-exception approval are compliance gates, not paperwork.

## Worked example (a batch, end to end)
A production order for **1000 kg** of a product is released and instantiated as a **control recipe** bound to
**Reactor R-201**. (**Read** first: order Released, control recipe bound to R-201, no holds, R-201 available
and qualified.) The batch acquires R-201 (arbitration confirms no other batch owns it) [write-reversible].
At the **charge** operation you run the **weigh-and-dispense** phase: dispense **250 kg of API lot L-88**
within tolerance, e-sign the dispense [write-committing]; the lot is consumed and written to the batch
genealogy. You **Start** the **mix** phase [write-committing] - the controller runs the agitator; a
temperature data-collection value at the **react** phase reads **out of limit**, so the system raises an
**exception** and the phase goes to **Held**. You raise a **deviation**; the review decides a **split**: hold
the batch, re-measure, confirm the reading was a sensor spike, then (**re-read** at execute: batch Running,
react phase Held, no other holds, R-201 still acquired, API lot L-88 consumed and valid) **Restart** the phase
[write-committing] - not force the transition, which would have run the reaction off-spec and left a Part 11
record of the override. At the last operation you **complete** the batch [write-committing]: the finished **~990 kg** (10 kg
process loss) posts and triggers the ERP goods receipt; the EBR goes **In Review**, and under **review by
exception** the reviewer approves it [write-committing] - which is the batch release, with API lot L-88 tied
to the finished lot for recall.

**A destructive-recovery variant.** Suppose during the react phase a genuine equipment fault forces an Abort.
The safe sequence is explicit: **Abort** the react phase on R-201 [destructive] (R-201 goes to a safe condition) -> confirm
the equipment is safe and isolated -> **scrap** the compromised ~1000 kg [destructive] (batch yield drops to
zero) -> raise and **disposition a deviation** for the fault and the loss -> **re-qualify and line-clear**
R-201 (a Reset to Idle alone does not clean it) or pick another qualified unit -> start a **new batch**. You
cannot Restart an aborted batch, and the abort, scrap, and deviation all stand permanently in the audit
trail. Separately, if the batch had **completed** but the **ERP goods receipt was rejected** (closed period,
order status), do not reverse the completion - hold the finished lot, resolve the ERP-side reason
(`sap-mm`), and re-trigger the receipt.

## Gotchas that bite (the real set - causal chains)
1. **Running a phase commands real equipment.** Starting a phase opens valves, doses, transfers, heats, or
   agitates via the controller - it is not a status flip. A wrong phase or setpoint physically mis-processes
   the batch and can damage equipment or endanger people.
2. **Master recipe vs control recipe decides blast radius.** Editing an **effective** master recipe changes
   every new batch that instantiates it (a fleet change); editing the control recipe changes one batch.
   Confusing them makes a one-batch fix a fleet change, or vice-versa.
3. **Approving a master recipe to effective is a change-control event.** It governs all future batches and
   cannot be casually edited afterward - a change needs a new version and re-approval. A pre-effective
   (In Preparation) draft is the only freely editable state.
4. **A control recipe binds to a specific unit; class-based recipes bind at runtime.** A wrong bind runs the
   batch on the wrong reactor / line. Assuming a fixed unit for a class-based recipe mis-predicts where the
   batch runs - re-read the actual bound unit before acting.
5. **Equipment arbitration protects shared vessels.** A batch acquires a unit exclusively; forcing acquisition
   or overriding arbitration can run two batches into the same equipment and cross-contaminate. An acquired /
   held unit blocks other batches for a reason.
6. **Hold pauses, Stop and Abort end the run.** Hold (or the lighter Pause) takes a phase to a safe state and
   Restart / Resume brings it back (recoverable). **Stop and Abort are terminal** - the run ends and the phase
   can only be Reset to Idle, never Restarted; Abort usually loses the in-process product. Stopping or aborting
   to "reset and retry" is a batch loss, not a do-over.
7. **A weigh-and-dispense outside tolerance blocks or flags.** Overriding it mis-formulates the batch. The
   dispense reserves and consumes a specific material lot into the genealogy, so a wrong lot mis-records
   traceability even when the quantity is right.
8. **Material consumption writes permanent as-built.** Consuming a lot / quantity at a phase ties actual lots
   and equipment to the batch genealogy; a wrong consumed lot mis-scopes a future recall and cannot be cleanly
   rewritten - correction is a new transaction, not an erase.
9. **An out-of-limit value or a failed phase raises an exception.** Forcing the transition or editing the
   value to pass is a data-integrity breach; the Part 11 audit trail records who changed what and when, so the
   "fix" is itself evidence.
10. **An exception is a flag; a deviation is the gate.** Recording the exception contains nothing on its own;
    the deviation must be dispositioned, and an open deviation blocks batch release. The disposition decides
    release, not the record.
11. **Review by exception releases a batch by approving the executed EBR.** Approving with an unresolved
    deviation releases a batch that should be held. In a GxP line the approval IS the release - treat it as
    the most consequential write, not a review formality.
12. **An electronic signature is a hard compliance gate.** The phase, dispense, parameter change, or EBR step
    cannot complete without it; it is legally attributed to the signer with a specific meaning, and it cannot
    be signed on someone else's behalf or removed once applied.
13. **Completing a batch / order posts the finished quantity and triggers the ERP goods receipt.** It is a
    committing hand-off, not an internal status flip; an ERP-side mismatch (closed period, order status,
    account assignment) fails the receipt and strands the finished stock.
14. **Line clearance is a gated verification, not a checkbox** (PharmaSuite / process). Skipping the check
    that the line is clear of prior product before a new batch risks cross-contamination and an EBR exception.
15. **Forcing a phase transition / skipping a step / manual-mode override bypasses interlocks and required
    data collection.** The genealogy and compliance record then have a gap; interlocks exist to protect
    equipment and product, and the forced action is auditable.
16. **A runtime setpoint change deviates the batch unless in-limits.** Changing a parameter mid-batch
    over/under-doses or over-heats; it is signed and audited, and it deviates the batch from the approved
    recipe unless it stays inside recipe-allowed operating limits.
17. **Historian archive data is a process record.** Reads and trends are safe, but editing or backfilling
    archived values (a manual insert or "data flush") corrupts the process history and, in a GxP context, is
    a data-integrity violation - not a cleanup.
18. **A faulted phase does not clean itself.** A phase fault must be Held, the cause corrected, and the phase
    Restarted or Aborted; resetting or forcing past the fault without resolving it can leave equipment in an
    unsafe state or the material off-spec.
19. **Genealogy / as-built is permanent and scopes recalls.** A wrong material or equipment association
    mis-scopes a recall; you append a correction, the original association stays, and you cannot cleanly
    rewrite the history.
20. **Scrapping a batch quantity or dispensed container is a loss, not a correction.** The material is
    consumed / destroyed, the order yield drops, and unscrap / return-from-scrap is limited and may not
    restore genealogy or position - size it before posting.
21. **A released order authorizes build and consumption.** A released order with an in-process batch cannot be
    cleanly cancelled - the batch must be Aborted / scrapped first, each its own destructive action, before
    the order can close.
22. **Equipment must be available and qualified to run a phase.** Commanding a down or disqualified unit is
    blocked or, if overridden, runs product through uncertified equipment - a compliance risk that also risks
    the batch.
23. **The Part 11 audit trail is immutable.** Every phase command, parameter change, dispense, and signature
    captures who / what / when / why; a mistake is corrected forward, never erased - deleting or re-signing a
    record is itself an audited event.
24. **Concurrent action on one batch / unit conflicts.** Two operators, or an operator and equipment
    automation, commanding the same phase or acquiring the same unit can have one command rejected or leave
    equipment in an unexpected state; re-read the phase state and unit ownership at execute - a stale read
    acts on the wrong phase or double-commands.
25. **Reprocess / rework re-consumes material.** Sending a batch back through an operation adds to consumption
    and genealogy; it does not replace the first pass, so total consumption and cycle time both grow.
26. **Reset does not clean or re-qualify equipment.** Resetting a Stopped / Aborted phase to Idle only frees
    the state machine; the unit may still hold residual material and be out of qualification. The next Start
    needs the unit re-qualified and line-cleared first, or it runs product on contaminated / uncertified
    equipment - a latent contamination path after an abort.
27. **Arbitration deadlock tempts an override.** In a multi-unit cell, batch A can hold unit X while waiting
    for unit Y that batch B holds while waiting for X - neither proceeds. The fix is to sequence or release
    one batch's acquisition, not to force-acquire or override arbitration; forcing it runs two batches into
    shared equipment and cross-contaminates.
28. **A lost Batch Server connection makes phase state unknown.** The controller keeps executing the phase
    even when the Batch Server / client view goes stale or disconnects; a command issued against the stale
    view can conflict with the real equipment state. If connectivity is interrupted, treat the phase state as
    unknown - do not command until the connection is restored and the live state re-read.
29. **In FTPC, completing an operation auto-posts component consumption.** A discrete routing operation posts
    / backflushes the step's components on completion just as a phase does - completing an FTPC operation is a
    material commit and a genealogy write, not a status tick.

(Deep detail: `references/isa88-phases-and-equipment.md`, `references/ebr-deviations-and-signatures.md`.)

## Edge states & special cases
Each breaks naive "the phase ran, so the quantity is good and available" logic - key rule inline, full
behavior in the references.
- **Class-based vs instance-based recipes / runtime binding** - a class-based recipe binds to any qualified
  unit at runtime; an instance-based one is fixed. Where the batch actually runs is a runtime fact, not a
  recipe constant. Detail in `references/isa88-phases-and-equipment.md`.
- **Equipment arbitration / shared units** - two batches contending for one unit are arbitrated; acquiring
  reserves it exclusively, releasing frees it. Forcing acquisition risks cross-batch use. In a multi-unit cell
  two batches can **deadlock** (each holding a unit the other needs); resolve by sequencing or releasing an
  acquisition, never by force-acquiring.
- **Phase failure -> Hold / Restart / Abort** - the S88 recovery path: hold to a safe state, correct, then
  Restart (recoverable) or Stop / Abort (terminal). Detail in `references/isa88-phases-and-equipment.md`.
- **CIP / cleaning phases** - clean-in-place runs as its own phase(s) with the same state model as production
  phases; a completed, signed CIP is what gates **line clearance** and the next batch start, and the unit's
  clean status is part of its **qualification**. Skipping or forcing a CIP compromises line clearance and can
  cross-contaminate the next batch.
- **FTPC discrete routing** - in FactoryTalk ProductionCentre the analogue is an **operation** on a
  **routing**: operation states run **not started -> started -> complete** (holds / pauses follow the same
  pattern as Batch phases), a unit / serial is bound to a **work center**, and start / complete an operation
  is the commit (progress + component consumption). The
  phase gating rules above apply to FTPC operations - the element that runs equipment and consumes material is
  the commit.
- **Manual / semi-automatic phases (eProcedure)** - operator-driven phases with prompts and signatures; the
  operator commands the step manually, and the prompt responses and signatures are part of the record.
- **Reprocess / rework routes** - a batch leaves the main flow and re-enters; re-consumption and re-inspection
  add to the record rather than replacing it.
- **Line clearance & weigh-and-dispense** (PharmaSuite) - gated verifications before / within a batch;
  dispensing consumes into the batch with a signed, tolerance-checked record. Detail in
  `references/ebr-deviations-and-signatures.md`.
- **Review by exception & e-sign** (PharmaSuite) - the executed EBR is reviewed only for flagged exceptions
  and approval releases the batch; signing / approval is a hard GxP gate. Detail in
  `references/ebr-deviations-and-signatures.md`.
- **Equipment / control integration** - phases execute in ControlLogix via PhaseManager; FactoryTalk Batch
  commands them and reads state over FactoryTalk Live Data / OPC UA. Commands drive live equipment - a "test"
  command is not a simulation unless the area is explicitly in test mode.
- **Historian data integrity** - reads and trends are safe; archive edits / backfills corrupt the process
  record and are a GxP data-integrity concern.
- **Cross-system order status with ERP** - the MES order and the ERP order can disagree (one closed, one
  active); reconcile order status before completing or scrapping, and re-read both at execute.

## Recovery patterns (can it be undone, and what cannot)

| Situation | Recovery path |
|---|---|
| A phase is faulted / out-of-limit | **Hold** the phase, correct the cause (re-measure, fix equipment, raise + disposition a deviation), then **Restart** - recoverable while held; do not force the transition to move faster |
| A unit goes down or is disqualified while a phase is Running | **Hold** the phase (do not force it), address the unit's status; **Restart** on the same unit if it re-qualifies, else **Abort** and re-bind to another qualified unit (class-based recipe) or start a new batch - never run product through a disqualified unit |
| A phase / batch was Stopped or Aborted | not recoverable - both are terminal; the in-process product is usually lost and must be scrapped, and you create a **new batch**; the Stop / Abort stays in the trail |
| A wrong material was dispensed, not yet consumed | reverse / re-do the dispense while it is only reserved; once consumed into the batch it is in the genealogy and needs a corrective transaction, not an erase |
| A data-collection value was recorded wrong, before sign-off | re-record it - a correctable draft while unsigned; after e-sign it is a controlled record and needs a corrective transaction |
| An exception was raised / the batch auto-held | resolve the reason (re-measure, correct, or raise and disposition a deviation), then release the hold; do not lift the hold to move faster |
| A deviation was dispositioned use-as-is / rework | recoverable forward: rework re-processes; use-as-is is a decision on record that can be revisited only forward |
| A deviation was dispositioned scrap or reject | not reversible - scrap destroyed the material and cut yield; reject is the GxP rejection of the batch |
| A batch record was approved (review by exception) / an e-sign applied | cannot be un-signed or un-approved; a correcting record / signature is appended and the original stays - handle as a deviation, not an edit |
| An effective master recipe was edited and batches ran on it | you cannot un-apply it; create a corrected version going forward - batches already run carry the version they executed on |
| A batch completed but the ERP goods-receipt call failed / was rejected | the batch is complete on the MES side; do not re-complete or blindly reverse. Hold the finished lot, resolve the ERP-side reason (closed period, order status, account assignment - `sap-mm`), then re-trigger the receipt. Reversing the completion is a destructive last resort |
| A Historian archive value was edited in error | the edit is itself a recorded change; correcting is another recorded change, and the original archived context matters for the integrity investigation - do not "clean up" archived data to hide it |
| A command was rejected by a concurrent action (another operator / the equipment acted first) | re-read the phase state and unit ownership, resolve against the actual current state, then re-compose the command - do not blindly retry the stale command |
| The Batch Server connection drops mid-phase / the client view is stale | the controller keeps executing the phase; treat phase state as **unknown** - do not command. Re-establish the connection, re-read the live phase and unit state, then act; a command against a stale view can conflict with the real equipment |
| Two batches deadlock over shared units (A holds X waiting for Y, B holds Y waiting for X) | do not force-acquire or override arbitration; sequence or release one batch's acquisition so the other proceeds - forcing runs both into shared equipment |
| A phase was Reset to Idle after an abort / stop, equipment not yet cleaned | do not Start - Reset only cleared the state machine; re-qualify and line-clear the unit (residual material may remain) before the next Start |
| A class-based batch bound to / is running on the wrong unit | if it has not run material, release the acquisition and re-bind to the correct qualified unit; if material already ran, Abort and scrap the in-process material, then start a new batch bound to the correct unit - a running batch cannot be silently moved |
| An order and its ERP counterpart disagree (one closed / one active) | do not act on the stale side - reconcile order status first; scrapping or completing against an ERP-closed order can strand WIP or fail the receipt |

Reversal is almost always a **new transaction**, not an undo: the original command, its reversal, the
disposition, and every signature stay in the immutable audit trail. What is truly gone is any material
already dispensed, consumed, scrapped, or shipped, any batch already aborted, and any genealogy already built.

## Guardrails
- Read the batch state + current phase + holds + open deviations + unit ownership + material availability
  before acting; re-read at execute (the equipment or another operator may have moved, held, aborted, or
  consumed since you read). Any command is identified by at least the batch / control recipe, the phase (with
  the bound unit), and - where required - a reason / deviation code and the signature's meaning; pin those
  before composing it, and check order status on both the MES and ERP side (they can disagree).
- Treat running a phase as an equipment + material commit: know the phase's setpoints and BOM and whether it
  consumes material before you Start it, and size a scrap / abort / reversal - each is a loss or a commitment
  change, not a correction.
- Never force a phase past an out-of-limit value or a fault, edit a value to pass, override arbitration or
  equipment qualification, lift a hold, or make a skip / manual-mode / out-of-sequence move to go faster; a
  hold or open deviation means stop.
- In a GxP line, an electronic signature and a review-by-exception approval are hard gates - the step cannot
  complete without the signature, and the approval is the batch release; confirm the record is clean first.
- Genealogy / as-built is permanent and scopes recalls - verify the material lots and equipment before
  dispense / consume; a wrong association mis-scopes a future recall and cannot be cleanly rewritten.
- Do not edit or backfill Historian archive data to "correct" a reading - it is the process record and, in a
  GxP context, a data-integrity boundary.
- If the FactoryTalk Batch Server connection drops or the client view is stale, the controller keeps running
  the phase - treat phase state as unknown and do not command until reconnected and re-read. A Reset to Idle
  does not clean or re-qualify a unit; re-qualify and line-clear before the next Start.
- Do not force-acquire a unit or override arbitration to break a deadlock - sequence or release an acquisition
  instead; forcing runs two batches into shared equipment.
- For anything in the destructive row (Abort, scrap, deviation scrap / reject, force / override past a fault
  or interlock, effective-recipe change, EBR rejection, Historian archive edit): named approver, re-read, and
  log the reason.

## References (load on demand)
- `references/isa88-phases-and-equipment.md` - the ISA-88 procedural model (procedure / unit procedure /
  operation / phase), the phase state machine and command set, the equipment / area model, arbitration and
  unit binding, class- vs instance-based recipes, master- vs control-recipe lifecycle, FactoryTalk Batch
  execution and PhaseManager / Logix integration, and the FactoryTalk Historian read.
- `references/ebr-deviations-and-signatures.md` - the PharmaSuite electronic batch record lifecycle, weigh-
  and-dispense and material consumption, exceptions vs deviations and disposition paths, electronic signatures
  / 21 CFR Part 11, review by exception, and line clearance.
