---
name: aveva-mes
description: "AVEVA MES (ex-Wonderware MES; Operations, Performance, and Quality modules) - safe shop-floor execution and the ERP hand-off - work orders, WIP confirmation, backflush and lot genealogy, OEE and downtime reason codes, SPC against spec / control limits, quality holds, and e-signatures - plus the hazard AVEVA's shared System Platform (ArchestrA / Galaxy) and Historian make ever-present, where the same connection that reads a device value can write a setpoint or command down to SCADA / PLC. Use when the connected MES is AVEVA or Wonderware MES, or the user mentions AVEVA MES Operations / Performance / Quality, a work / production order, an operation confirm / complete, WIP or backflush, lot genealogy, OEE / downtime / a reason code, SPC or a spec / control limit, a quality hold, an e-signature, AVEVA System Platform / ArchestrA / a Galaxy, AVEVA or Wonderware Historian, InTouch / OMI, an OI Server / DAServer, a device attribute / tag, or writing a setpoint or command to the line."
---

# AVEVA MES - operating the shop floor safely

AVEVA MES (formerly Wonderware MES, part of AVEVA's Operations & Performance Management portfolio) runs
the plant floor and its production record. It authorizes production against a work order, drives material
through a routing of operations, tracks WIP at each equipment entity, records what was consumed and measured,
computes OEE from equipment states and downtime, and hands the finished result back to ERP. Two things make it
dangerous. First, like any MES, **confirming an operation is not a status flip - it posts a WIP move,
backflushes the operation's material, and (through the ERP integration) issues and receives stock**, an audited
event with real money behind it. Second, the AVEVA-specific one: other MES vendors also reach equipment, but
AVEVA MES rides on the **shared** AVEVA System Platform (ArchestrA) and AVEVA Historian, so **the same
connection that reads a device value for data collection can write one - and a write to a device-mapped
attribute is a setpoint or command that physically actuates the line through SCADA / PLC.** The control layer
is one attribute-write away on the same channel, not a separate, designed command path. This skill classifies those actions so the harness can gate them, with the control-layer write as the
hardest gate in the whole surface.

## When this applies
Connector is AVEVA MES / Wonderware MES (Operations, Performance, or Quality) and the work is shop-floor
execution or its production record. When NOT:
- a different MES: Siemens Opcenter / Camstar / SIMATIC IT -> `siemens-opcenter`
- a different MES: Rockwell FactoryTalk / PharmaSuite / FactoryTalk Batch -> `rockwell-factorytalk`
- SAP's MES: SAP Digital Manufacturing (DM / DMC) -> `sap-dm`
- ERP material/inventory postings, the goods issue/receipt the confirmation triggers, cancelling a
  confirmation, procurement, valuation, posting periods -> `sap-mm`
- a formal quality management system - inspection lots, quality notifications, CAPA on the ERP/QMS side -> `sap-qm`
- within the AVEVA family but a different product: **recipe-driven ISA-88 batch / phase control** = AVEVA Batch
  Management (**InBatch**), closer in shape to `rockwell-factorytalk` (when MES Operations triggers or
  tracks batch phases, the phase-control logic is InBatch's, but the WIP confirmation and lot genealogy stay
  here - do not confuse the two); **building the System Platform
  application** (ArchestrA object / template design, deployment, InTouch / OMI screen design, OI Server / device
  driver config) and **pure SCADA** (AVEVA Plant SCADA / Citect) are **control / automation engineering**, not
  MES execution. This skill is AVEVA MES **execution and its record** - not recipe control, not app design, not
  writing control logic. Any MES action that reaches the control layer (a setpoint or command) is hard-gated
  below, not treated as a routine MES write.
- **labor / crew / shift tracking** exists in MES Operations but is out of scope here beyond one rule: a labor
  confirmation that feeds ERP costing is **committing** like an operation confirm; detailed workforce / payroll
  / HR belongs to those systems, not this skill.

Seam with ERP/QM: AVEVA MES owns the WIP truth (where the order is, what operation it is at, what was consumed,
as-built genealogy) and OEE / quality at the point of manufacture; ERP (`sap-mm`) values the inventory
and books the goods issue and finished-goods receipt the confirmation triggers; a formal QMS (`sap-qm`)
owns inspection lots and CAPA. AVEVA contains and dispositions on the floor; the ERP/QMS is the financial and
compliance system of record downstream.

## Contents
- Object & state model
- Vocabulary that bites
- Operations: read / write / destructive
- The control-layer write (the AVEVA hard gate)
- Reclassification rules
- Worked example (a work order, end to end)
- Gotchas that bite
- Edge states & special cases
- Recovery patterns
- Guardrails
- References

## Object & state model (reason about state, not nouns)
- **Entity / equipment model** - the plant modeled as a hierarchy of production **entities** (site -> area ->
  line -> cell -> unit / machine). Jobs run **at an entity**; the entity's own state (**Running / Idle / Down
  (unplanned) / Planned Down / Setup / Blocked / Starved**) is what OEE is computed from. Detail in
  `references/control-layer-oee-and-historian.md`.
- **Item** - the material / product master: what is produced or consumed, its BOM, its data-collection and spec
  definitions.
- **Work order (production order / job)** - authorizes building a quantity of an item; usually downloaded from
  ERP. States: **Created / Released** (the floor may build and consume against it) -> **In Process / Running** ->
  **Completed** -> **Closed** (ERP-side). The order also lives in ERP - the two copies can disagree.
- **Operation & routing** - the ordered sequence of **operations** the work order follows, each at an entity,
  each carrying required data collection, resources, material (BOM) to consume, and sign-off rules.
  Out-of-sequence and skip moves are blocked unless overridden. Per-operation WIP state: **Queued** -> **Running /
  In Work** (started at the entity) -> **Confirmed / Complete** (WIP posted, material consumed, advanced).
- **WIP move / production event** - a tracked quantity moving in, through, and out of an operation. The **move
  out / confirm** is the commit: it posts produced quantity, backflushes the operation BOM, and writes the
  event to the record. Detail in `references/wip-genealogy-and-confirmation.md`.
- **Lot / genealogy (as-built)** - material lots consumed at operations tie to the produced lot as the permanent
  **as-built genealogy** (forward and backward trace). It scopes recalls; you cannot cleanly rewrite it.
- **Downtime event + reason code** - an interval of equipment stoppage classified with a **reason code** (and
  often a category / fault code). It feeds **OEE** and loss reporting. Assigning or reclassifying a reason is a
  write to the performance record. Detail in `references/control-layer-oee-and-historian.md`.
- **Quality data collection + limits** - parameter values captured at an operation against **specification
  limits** (conformance: is the unit good?) and, for SPC, **control limits** (is the process stable?). An
  out-of-spec or out-of-control value can **auto-hold** the WIP or **block confirm**. Detail in
  `references/wip-genealogy-and-confirmation.md`.
- **Hold / quality hold** - a containment that stops a lot, WIP, or order from advancing, being consumed, or
  shipping, with a reason. States: **Active** -> **Released**. Placing is reversible; releasing is the gate.
- **Electronic signature (e-sign)** - an attributed sign-off required at a step in a regulated setup (21 CFR
  Part 11; food / beverage / pharma). The operation cannot confirm without it; once applied it is permanent.
- **System Platform attribute / Historian tag** - the process-data layer under MES: an ArchestrA object
  **attribute** (a live device value, e.g. a `PV` process value or `SP` setpoint) and an AVEVA **Historian tag**
  (its archived time series). Reading them is safe; **writing a device-mapped attribute actuates equipment** -
  see the control-layer section.

## Vocabulary that bites
- **Confirm / complete an operation** - the commit. It posts the WIP move, **backflushes** the operation BOM
  (goods issue to ERP), records data collection, and advances the order. **Start / move-in** only begins the
  operation and claims the entity - it commits nothing. Confusing the two under-gates the real material +
  financial posting.
- **Backflush** - automatic consumption of BOM components at confirm at **standard** quantities, with no explicit
  pick. It moves inventory in ERP and writes as-built in one transaction; a wrong BOM or standard qty silently
  mis-consumes and mis-records genealogy. Consumption can instead be an **explicit material issue** (a deliberate
  consume of an actual lot / quantity, not standard) - also committing, and not covered by the backflush's
  standard-qty behavior; know which mode the operation uses before you confirm.
- **Genealogy / as-built** - the permanent record of which component lots went into which produced lot, by which
  entity / operator. It drives recall scope; a correction is a new transaction, not an erase.
- **Entity** - a modeled piece of equipment, not an inventory location. Its state (Running / Down / Setup /
  Starved / Blocked) drives OEE; a job runs *at* an entity. Inventory storage locations / bins live in ERP or
  the WMS (`sap-ewm` / `manhattan-wms`), not as MES entities - do not treat an entity as a
  stock location.
- **OEE** - Overall Equipment Effectiveness = **Availability x Performance x Quality**. It is computed from
  entity states, cycle counts, and quality; changing a downtime reason or a reject count moves the number.
- **Downtime reason code** - the classification of a stoppage (planned vs unplanned, the six big losses). It is
  a record entry that drives OEE and loss analysis; reclassifying a locked reason to improve a number is a
  performance-record integrity issue, not housekeeping.
- **Spec limit vs control limit** - a **spec limit** decides conformance (is this unit good / bad); a **control
  limit** (SPC) decides process stability (is the process drifting). They are different tests - a value can be
  in-spec but out-of-control, or the reverse. Do not conflate them.
- **Quality hold** - a containment that blocks release / consumption / shipment of held material. A hold means
  **stop**; releasing it is a decision, not a status reset.
- **AVEVA System Platform (ArchestrA)** - the supervisory platform MES data collection runs on: application
  objects with **attributes**, organized in a **Galaxy** (the object namespace / repository). Attributes can be
  bound to device I/O.
- **Attribute / I/O reference** - an object attribute (e.g. `PV`, `SP`, a command bit) that **references a
  device point** through an **OI Server** (Operations Integration server; formerly **DAServer**). Reading it is
  a read; **writing it drives the device**. A plain in-memory attribute is harmless; a device-referenced one is
  a physical command - and you cannot always tell which from the value alone.
- **Setpoint (SP) / command** - a target value or discrete action written to a device attribute (target
  temperature / pressure / speed / level; start / stop a motor; open / close a valve; download a recipe value).
  Writing it changes what the physical equipment does. There is no undo for a physical action already taken.
- **AVEVA Historian (ex-Wonderware Historian / IndustrialSQL / InSQL)** - the time-series store of tag history.
  Reads and trends are safe; editing or backfilling archived values corrupts the process record.
- **OMI / InTouch** - the operator visualization (Operations Management Interface / InTouch HMI). It renders and
  can send operator commands; it is a view + control surface, not the MES system of record.

## Operations: read / write / destructive
Classify every operation family by what it does to WIP state, to material, to the compliance record, **and to
the physical line**. The names below name the action-kind; the class is the same whether the connector drives
the MES client, an MES API, a POD-style screen, an OMI graphic, or a System Platform attribute. The harness maps
the customer's real connector onto these classes. No tool names - kinds of action.

| Class | AVEVA MES operation families | Gate | Why |
|---|---|---|---|
| **Read** | display a work order / operation / entity and its status and current WIP; WIP position and counts; **genealogy / as-built**; material lots; data-collection results; **OEE / downtime / reason-code reports** (Performance); **SPC charts, spec and control limits** (Quality); the hold list; e-sign / buyoff status; the audit trail; **a System Platform attribute current value and an AVEVA Historian tag / trend** (snapshot or archived); the ERP order/confirmation status | always pass | no state change and no device action; read WIP state + holds + component availability + entity state before any write, re-read at execute |
| **Write (reversible)** | author or edit a work order / routing / operation / data-collection definition **before release / before it is used**; create a work order before release; **assign or split a downtime reason before it is locked** (a performance-record classification, correctable pre-lock); **start / move-in** an operation at an entity **when the start only claims the entity and issues no device command** - posts no WIP, consumes nothing, undoable before confirm (a start that sends a start-command to the equipment / PLC is a device action - committing, see the control-layer gate); cancel / undo such a start before any confirm; place a **hold** (protective containment, reversed by release); park in-progress data collection **before sign-off**; raise a quality / NC event before disposition | gate one at a time | a draft, a claim, a classification, or a correctable record; no WIP posted, no material consumed, no device driven, no disposition made |
| **Write (committing)** | **confirm / complete an operation** = post the WIP move + **backflush** the operation BOM (goods issue to ERP) + record data collection + advance the order; explicitly **consume / produce** a lot into genealogy; **complete the final operation** = post finished quantity + **finished-goods receipt to ERP**; **release a work order** to the floor (the ERP order must already exist and be released - do not build a stale or ERP-unreleased order); **disposition a quality hold / NC** use-as-is / rework; **release a hold** (returns material to flow - the gated direction); **apply an e-signature** at an operation; **lock / commit a downtime reason** that feeds OEE and reporting; **change a Historian tag / data-collection configuration** (alters what is recorded downstream - OEE, quality, regulatory data; lost history cannot be recovered) | gate + human approve | binds material and the financial world: consumes inventory in ERP, frees or contains stock, certifies a record, receives finished goods; re-read the WIP + holds + entity state at execute |
| **Destructive / irreversible** | **write a setpoint or command to a device-mapped attribute** (System Platform -> OI Server -> PLC / SCADA) - physically actuates equipment, no undo (the hard gate below); **download a recipe / setpoint set to the line (to the control layer - PLC / SCADA, not a definition download to MES)**; **scrap** WIP / quantity (yield + value loss); **NC disposition -> scrap or return** (destroys stock / reverses the receipt); **reverse a confirmed WIP move / consumption** (a reversing production event + an ERP counter goods movement - `sap-mm`; not an MES-side undo); **override a hold, a required data collection, an out-of-spec / out-of-control value, or entity qualification to force a confirm**; **skip / out-of-sequence operation**; **retroactively edit or reclassify a locked downtime reason to alter OEE** (performance-record integrity); **edit or backfill AVEVA Historian archive data**; **modify or delete a signed record after e-signature** (append a correction instead); **change a released routing / production definition while orders are in flight** | hard gate + named approver + re-read | permanent audit trail; drives / destroys / re-routes material; actuates or mis-reports the physical line; reverses an ERP posting; crosses a compliance boundary; cannot be cleanly undone - re-read the live state (WIP, holds, and for a device write the live device + interlock state) at execute |

**By module.** The three modules do not all classify the same way. **Performance** is mostly reads (OEE / KPI /
downtime reports), with the reason-code write as the one exception. **Quality** reads (SPC charts, results), but
editing a **released** spec / control-limit definition is a change-controlled destructive write (it re-judges
every future unit), and editing a captured value to pass is a data-integrity breach. **Operations** carries the
committing WIP / confirmation / consumption writes. Do not treat every module action as the same class.

**A start that commands equipment is not in the reversible row.** The Write-reversible start above is only the
kind that claims the entity and posts nothing. A start that issues a start-command to the equipment / PLC is a
compound action - committing for the MES state change AND a device write that carries the control-layer **hard
gate** below. Do not read the reversible row as covering a machine-integrated start.

## The control-layer write (the AVEVA hard gate)
This is the sharpest AVEVA-specific risk. Other MES vendors command equipment too, but they do it through a
separate, designed path; here, because MES data collection runs on the shared AVEVA System Platform, the
connector that reads a `PV` can, on the same object, write a `SP` or a command bit - and a device-referenced
attribute write goes straight through the **OI Server** to the **PLC / SCADA** and moves real machinery: it changes a temperature / pressure / speed / level target, starts or stops a motor, opens or closes
a valve, or downloads a recipe to the line.

**HARD GATE - a device-mapped attribute / setpoint / command write is the most destructive action in this skill.**
- A physical action has **no undo**: once the valve opened or the motor ran, product may be ruined, a batch
  spoiled, equipment damaged, or a person put at risk. Reversing it means writing a *new* command (a stop, a
  safe setpoint) - itself another physical action, not a rollback. A **safety-critical stop belongs to the plant
  safety system / qualified operator (E-stops are hardwired circuits, not MES attribute writes)** - do not try to
  fix a bad device write with another MES device write through the same channel; escalate.
- It can **bypass an interlock or override an operator** - the control system's interlocks exist to protect
  equipment and people; forcing a write past them is a safety event, not a data edit.
- **You cannot always tell an in-memory attribute from a device-mapped one** from its value. What resolves it
  is the attribute's **I/O reference** in the Galaxy (ArchestrA) object configuration - an attribute bound to an
  OI Server item writes to a device; an unbound one does not. When you cannot check that binding, treat any
  attribute that could carry an I/O reference (`SP`, an output, a command / mode bit) as a physical command until
  proven otherwise.
- **MES is meant to record and coordinate, not command the line.** The default is that the agent does **not**
  write setpoints or commands to the control layer at all; the control system and its qualified operators own
  physical commands. If a task truly requires one, it needs a named approver who owns that equipment, a re-read
  of the live device and interlock state at execute, and confirmation the line is safe for the action - never a
  blind or batched write.

**An ambiguous or timed-out device write must be assumed to have actuated.** If a setpoint / command write times
out or returns an unclear response, do not assume "nothing happened" and retry - a blind retry can double-actuate.
Verify the physical state directly (read the live device / Historian, or confirm with the operator) before any
further action; treat a comms failure as "possibly actuated," not as a no-op.

Reading attributes and Historian tags/trends stays a **read** and is how the agent should interact with the
control layer by default. The line between "read the value" and "write the value" is the line between safe and
physically destructive - hold it.

## Reclassification rules (read this)
- **Reading a device value is a read; writing one is physical actuation.** Do not treat a setpoint / command
  write as a "data write" because it looks like setting a field - it drives equipment and belongs in the
  destructive row (see the hard gate above), never in a reversible edit.
- **A start is reversible only if it commands no equipment - the axis is what the start does, not who
  triggered it.** A start that only claims the entity and posts nothing is reversible (cancel before confirm),
  whether a person or MES queue logic initiated it. A start that issues a start-command to the equipment / PLC
  (common on a machine-integrated line, but a manual start can do it too) begins physical processing, may not be
  cleanly cancellable, and is committing - and where it writes a device command it falls under the control-layer
  gate. Classify by whether the start drives equipment, not by manual-vs-automated.
- **Confirm / complete is the commit.** A confirm posted a WIP move and backflushed material to ERP - reversing
  it is a reversing production event plus an ERP counter goods movement (`sap-mm`), not an undo, so it
  belongs in the destructive row.
- **A downtime reason is a record entry, not a cosmetic label.** Assigning or splitting a reason before it locks
  is a reversible classification; retroactively editing a *locked* reason to move the OEE number is a
  performance-record integrity breach - destructive, because the number feeds reporting and loss decisions.
- **A hold is asymmetric - placing is protective, releasing is the gate.** Placing a hold is low-friction and
  reversible (when in doubt, hold). **Releasing** returns material to flow, belongs to the role that set it, and
  needs the reason resolved (the NC dispositioned) - do not lift a hold to hit a schedule.
- **A split NC disposition is several actions - gate each path.** One disposition can send part of a lot
  use-as-is, part to rework, part to scrap or return. Use-as-is / rework are committing; scrap / return are
  destructive. Do not gate the whole disposition at the lowest risk.
- **Recording a data-collection value is reversible until sign-off; editing it to pass is destructive.** An
  unsigned value is a correctable draft; once signed / e-signed the record is locked, and editing an out-of-spec
  or out-of-control value to make it pass is a data-integrity breach, not an edit.
- **An e-signature is a hard gate, not a field.** In a regulated setup a confirm or buyoff may require an
  attributed signature; the step cannot complete without it and it is permanent, so treat it as a blocking
  precondition on that write.
- **A released routing / production-definition edit is a fleet change, not a local edit.** Changing a released
  definition re-routes or re-consumes future orders and can hit in-flight orders at their next operation. Treat
  it as change-controlled - a pre-release draft is the only reversible kind.

Universal rules to teach: read the WIP state + current operation + holds + entity state + component availability
before any write and **re-read at execute** (another operator or the equipment may have moved, held, or consumed
since you read); never force a confirm past an out-of-spec value or a missing signature, edit a value to pass,
lift a hold, override entity qualification, or make a skip / out-of-sequence move to go faster; a hold or open
NC means stop; a signature is a compliance gate; the confirmation is a financial event; **and a device-mapped
attribute write is a physical command, not a data write.**

## Worked example (a work order, end to end)
A work order for **500 EA** of an assembly is released; operation **10** runs at entity **LINE-2**. (**Read**
first: order Released, op 10 Queued, no holds, LINE-2 Idle and available, components available; read the line's
`PV`s from Historian to confirm it is at rest.) You **start / move-in** at op 10 [write-reversible] (claims LINE-2, no
consumption yet), collect the required parameters against their spec limits (all in-spec), and **confirm** op 10
[write-committing] - which posts the WIP move, **backflushes** the op-10 BOM (say 500 of component lot A and 1000 of lot B)
as a goods issue to ERP (a real posting - roughly a $12,400 issue at standard cost, illustrative, not a status flip), writes
those lots into the as-built, and advances to op 20. At op 20 a quality
data-collection value reads **out of spec**: MES **auto-holds** the WIP and blocks confirm. You raise an **NC**;
the disposition is a **split**: **480 EA use-as-is** [write-committing] (released, confirm proceeds) and **20 EA scrap**
[destructive] (destroyed, order yield drops to 480). Forcing the confirm or editing the value to pass would have shipped
nonconforming units and left an audit entry of the edit. During op 20 the line stops for 12 minutes; you assign
the **downtime reason** (a changeover, planned) [write-reversible] so OEE reflects it correctly - not a padded reason to
protect the number. At the final operation you **complete** the order [write-committing]: the finished **480 EA** posts a
**finished-goods receipt to ERP**, and the as-built ties every finished unit to component lots A and B for recall.

**A control-layer variant (the AVEVA one).** Suppose op 20 is running hot and someone asks you to "just drop the
setpoint" on LINE-2 to bring it back in spec. That is a **write to a device-mapped `SP` attribute** - a physical
command down through the OI Server to the PLC [destructive, hard gate]. The safe path is: do **not** write the setpoint.
**Read** the live `PV` and the setpoint, confirm the out-of-spec condition, **hold** the WIP [write-reversible] so no
nonconforming unit advances, raise the NC, and hand the actual setpoint change to the **qualified operator / control
system** who owns LINE-2 (with a named approver, a re-read of the live device and interlock state, and confirmation
the line is safe) - never a blind MES-side setpoint write. The MES records and contains; the control system commands.

## Gotchas that bite (the real set - causal chains)
1. **A device-mapped attribute write actuates the physical line.** Writing a `SP`, an output, or a command bit
   on a System Platform object goes through the OI Server to the PLC / SCADA and moves real equipment - there is
   no undo for a physical action, and it can override an operator or bypass an interlock. It is the most
   destructive action here, not a data edit.
2. **You cannot tell an in-memory attribute from a device-mapped one by its value.** The same "set a field"
   gesture is harmless on an internal attribute and physically dangerous on one with an I/O reference; assume any
   `SP` / output / command / mode attribute is device-mapped until proven otherwise.
3. **Confirm / complete is the commit, not start.** Confirming an operation posts a WIP move and backflushes the
   operation BOM (goods issue to ERP) at standard quantities, and records data collection, in one transaction. A
   wrong BOM or standard qty silently mis-consumes and mis-records the build.
4. **Backflush consumes at standard, not actual.** If the operator used more or less than the standard, ERP
   on-hand and genealogy are wrong until corrected; over-consumption can drive an ERP component negative or block
   the confirm.
5. **The final operation's completion receives finished goods to ERP.** It is a financial hand-off, not an
   internal status flip; an ERP-side mismatch (closed period, order closed, missing components) fails the receipt
   and strands the finished order as complete-in-MES but not-received-in-ERP.
6. **Reversing a confirmed WIP move is an ERP-side counter-posting, not an MES-side undo.** It posts a reversing
   production event plus counter goods movements (`sap-mm`); both the confirm and its reversal stay in
   the trail forever, and a quantity already issued / consumed downstream cannot be restored.
7. **Scrapping destroys WIP and value and cuts order yield.** The scrapped quantity leaves the order; un-scrap is
   limited (often only before the order closes) and may not restore genealogy or operation position. It is a
   loss, not a correction - size it first.
8. **NC disposition decides release, not the NC record.** Logging an NC contains nothing on its own (though it
   can auto-hold the WIP); the disposition - use-as-is releases nonconforming stock, rework re-processes, scrap
   destroys it, return reverses the receipt - is the gate.
9. **A quality hold stops release but does not undo work done.** A held lot / order keeps its state; releasing it
   returns it to flow. Lifting a hold to hit a schedule bypasses the containment reason and can release stock an
   open NC has not dispositioned.
10. **Spec limits and control limits are different tests.** A value can pass the spec limit (the unit is good)
    yet violate a control limit (the process is drifting), or the reverse. Treating an SPC control-limit
    violation as a reject, or an out-of-spec unit as merely "process noise", makes the wrong call - read which
    limit fired.
11. **An out-of-spec / out-of-control value can auto-hold or block confirm.** Forcing the confirm, or editing the
    value to pass, is a data-integrity breach - the audit trail records who changed what and when, so the "fix"
    is itself evidence.
12. **An e-signature is a hard compliance gate.** In a regulated line the operation cannot confirm without the
    required signature; it is attributed to the signer, cannot be self-signed or applied on another's behalf, and
    once applied it is permanent.
13. **Genealogy / as-built is permanent and scopes recalls.** A wrong consumed lot mis-scopes a future recall;
    you cannot cleanly rewrite the history, only append a correction, and the original association stays.
14. **OEE is computed, so a reason code or reject count changes the number.** OEE = Availability x Performance x
    Quality; a mis-assigned downtime reason or a hidden reject silently moves the KPI. Editing a *locked* reason
    to improve OEE is a performance-record integrity issue, not a cleanup - it hides a real loss from the
    decisions OEE drives.
15. **Downtime attribution is a judgment that feeds money.** Mis-classifying an unplanned stop as planned, or a
    real loss as a micro-stop below threshold, understates the loss and mis-directs improvement spend; the
    reason code is a record entry, not a cosmetic label.
16. **Editing or backfilling AVEVA Historian archive data corrupts the process record.** Reads and trends are
    safe, but inserting or "correcting" archived tag values (a data flush / backfill) rewrites the process
    history and, in a regulated context, is a data-integrity violation - not housekeeping.
17. **A released routing / production-definition edit changes future and in-flight orders.** A released
    definition edit re-routes or re-consumes every new order and can hit an in-flight order at its next
    operation; it is change-controlled - a new version, not an in-place edit.
18. **A released work order authorizes build and consumption.** A released order with in-process WIP cannot be
    cleanly cancelled - the WIP must be scrapped or completed first, each its own posting.
19. **WIP in MES is the source of truth; ERP on-hand lags.** ERP inventory updates only when the confirmation
    posts; treating ERP on-hand as the shop-floor reality over-promises stock still in WIP, on hold, or under NC.
20. **An entity must be available and qualified to run an operation.** Confirming against a down, in-setup, or
    unqualified entity is blocked or, if overridden, confirms production on an uncertified resource - a
    compliance and quality risk.
21. **OMI / InTouch is a view and a control surface, not the record.** An operator command sent from an OMI
    graphic drives the device just like an attribute write; and an OMI number is a live view, not the MES system
    of record - do not act on it as if it were confirmed WIP.
22. **Automatic data collection from the platform still commits when it triggers a confirm.** A value or count
    posted from a connected device (via System Platform / OI Server) that drives a confirm backflushes exactly
    like a manual confirm - equipment-driven actions are not exempt from the gate.
23. **The audit / production-event log is append-only.** Every start, confirm, NC, hold, e-sign, and scrap
    captures who / what / when; a mistake is corrected by a forward transaction, never erased - deleting or
    re-signing a record is itself an audited event.
24. **Concurrent action on one order / entity conflicts.** Two operators, or an operator and machine automation,
    starting / confirming / holding the same order at once can reject a move or overwrite state; re-read the WIP's
    current operation and the entity state at execute - a stale read acts on the wrong operation or double-confirms.
25. **The MES order and the ERP order can drift.** If the ERP order quantity is cut or dates change but MES still
    shows the original, building or backflushing against the stale MES quantity over-produces or over-consumes,
    and the confirmation can fail against the changed ERP order. Re-sync and re-read the order on both sides.

(Deep detail: `references/wip-genealogy-and-confirmation.md`, `references/control-layer-oee-and-historian.md`.)

## Edge states & special cases
Each breaks naive "the operation passed, so the quantity is good and available" logic - key rule inline, full
behavior in the references.
- **The control-layer boundary** - reading a `PV` / Historian tag is safe; writing a device-mapped `SP` /
  command actuates the line. The whole hazard lives in this one line. Detail in
  `references/control-layer-oee-and-historian.md`.
- **A partially-posted confirm (MES vs ERP)** - the MES WIP move and backflush can post while the ERP goods
  issue / receipt fails (or the reverse, or the ERP leg is still async). This is a distinct mid-state, not a
  clean success or failure - read what actually posted on each side and reconcile only the missing leg; do not
  blindly re-confirm (it double-issues the components) or roll back.
- **OEE & downtime attribution** - OEE = Availability x Performance x Quality, computed from entity states,
  counts, and quality; reason-code assignment is a record entry that moves the number. Detail in
  `references/control-layer-oee-and-historian.md`.
- **SPC vs conformance** - spec limits judge the unit, control limits judge the process; an SPC signal (a run,
  a trend, a point beyond a control limit) is a stability alarm, not automatically a reject.
- **Rework / repair routes** - an order leaves the main routing to a rework operation and re-enters;
  re-consumption and re-inspection add to the record rather than replacing it, so total consumption grows.
- **Lot split / merge & genealogy branching** - splitting a lot creates children with inherited history; merging
  joins genealogies. A mistaken split / merge mis-attributes which units carry which component lots.
- **E-signature & regulated (Part 11) lines** - a required attributed sign-off gates confirm; signing is a hard
  gate. Detail in `references/wip-genealogy-and-confirmation.md`.
- **Machine integration via System Platform / OI Server** - connected equipment drives data collection, start,
  and confirm automatically; automated transactions commit and backflush exactly like manual ones, and the same
  channel can carry a device write.
- **OI Server / device connection lost mid-operation** - if MES cannot read live device values, data collection
  is incomplete; confirming on stale or missing device values posts wrong genealogy / quality data. Treat the
  device state as unknown, hold, and re-read once the connection is restored - do not confirm on a stale read.
- **Cross-plant / multi-site** - an order at another plant is governed by that plant's released production
  definition and confirms to that plant's ERP org; processing against the wrong plant's definition re-routes and
  re-consumes against that plant's BOM and posts to that plant's ERP org. Validate the definition and plant before acting.

## Recovery patterns (can it be undone, and what cannot)
Triage by severity first: a control-layer write that already actuated the line is an **emergency** (equipment /
person / product at risk) - act on it before anything else; a wrong downtime reason before lock is a routine
correction.

| Severity | Situation | Recovery path |
|---|---|---|
| **Emergency** | A device write was sent but the outcome is unknown (timeout / ambiguous response) | assume it **actuated** - verify the physical state directly (read the live device / Historian, or confirm with the operator) before any retry; a blind retry can double-actuate. Treat a comms failure as "possibly actuated," never as "nothing happened" |
| **Emergency** | A setpoint / command was written to the line | **not undoable** - the physical action happened. A safety-critical stop belongs to the plant safety system / qualified operator (E-stops are hardwired, not an MES write) - escalate; do not chase a bad device write with another MES device write. Product / equipment already affected cannot be restored. This is why the control-layer write is hard-gated up front, not recovered after |
| Routine | An operation was started but must back out (not confirmed) | cancel / undo the start - reversible, since it posted no WIP and consumed nothing |
| Urgent | An operation was confirmed with the wrong backflush | no clean MES undo - reversing the material / financial effect is a reversing production event plus an ERP counter goods movement (`sap-mm`). Prefer a forward correction (NC + disassembly / re-assembly); a reversal is valid only if no later operation advanced and the re-credited components were not re-consumed |
| Urgent | A confirm was reversed in ERP but a later operation already advanced | the later operation does not un-confirm; correct forward (rework or NC), do not expect a clean rollback across MES and ERP |
| Urgent | A confirm posted partially - the MES WIP move / backflush posted but the ERP goods issue / receipt failed (or is still async) | do not re-confirm (it double-issues the components) and do not blindly reverse - read what actually posted on each side, hold the WIP, and reconcile only the missing leg (`sap-mm`); treat the mid-state as authoritative until reconciled, not as a clean success or failure |
| Routine | A data-collection value was recorded wrong, before sign-off | re-record it - a correctable draft while unsigned; after sign-off / e-sign it is a controlled record and needs a corrective transaction |
| Urgent | WIP was auto-held on an out-of-spec / out-of-control value | resolve the reason (re-measure, or raise and disposition an NC), then release the hold; do not lift the hold to move faster |
| Routine | An NC was dispositioned use-as-is / rework | recoverable forward: rework re-processes; use-as-is is a decision on record, revisited only forward |
| Urgent | An NC was dispositioned scrap or return | not reversible - scrap destroyed the stock and value; return reversed the receipt and re-opened commitment |
| Urgent | WIP was scrapped in error | un-scrap only if still allowed (usually pre-order-close) and it may not restore genealogy or operation position; otherwise correct with a new build |
| Routine | A downtime reason was assigned wrong, before it locked | reassign / split it - a correctable classification while unlocked; after it locks, a change is a performance-record edit and, if done to alter OEE, a data-integrity issue |
| Routine | A locked downtime reason must genuinely be corrected | make the correction as a recorded, reasoned change (append the corrected classification with its justification), not a silent overwrite - and never to improve the number |
| Urgent | An e-signature was applied | cannot be un-signed; a correcting record / signature is appended and the original stays - handle as a deviation, not an edit |
| Urgent | A released production definition was edited and orders ran on it | you cannot un-apply it; create a corrected version going forward - orders already run carry the version they executed on |
| Urgent | A Historian archive value was edited in error | the edit is itself a recorded change; correcting is another recorded change, and the original archived context matters for the integrity investigation - do not "clean up" archived data |
| Urgent | An order completed but the ERP goods receipt failed / was rejected | the order is complete on the MES side; do not re-complete or blindly reverse. Read the confirmation / order status in ERP, hold the finished order, resolve the ERP-side reason (closed period, order closed, missing components - `sap-mm`), then re-trigger the receipt. Reversing the completion is a destructive last resort |
| Routine | A confirm was rejected by a concurrent action (another operator / the equipment acted first) | re-read the WIP's current operation and the entity state, resolve against the actual current state, then re-compose the confirm - do not blindly retry the stale move |
| Urgent | The MES order and the ERP order disagree (one closed, one active) | do not act on the stale side - reconcile order status first; completing or scrapping against an ERP-closed order can strand WIP or fail the confirmation |

Reversal is almost always a **new transaction**, not an undo: the original confirm, its ERP reversal, the
disposition, and every signature stay in the append-only record. What is truly gone is any quantity already
scrapped, returned, consumed, or received, any genealogy already built, and - most sharply - **any physical
action the control layer already took.**

## Guardrails
Pre-flight before any write (walk it, do not skip under pressure):
1. Read the **WIP state + current operation** (Queued / Running / Confirmed) and the **entity state** (is it
   available and qualified).
2. Read **holds + open NCs** on the order / lot - a hold or open NC means stop.
3. Read **component availability** in the system that owns it (ERP, or the warehouse where stock is staged -
   `sap-ewm` / `manhattan-wms`) - available in MES but unstaged still fails or drives
   negative the backflush.
4. Read **data collection + e-sign** status for the operation - a missing one blocks confirm.
5. Read **order status on both the MES and ERP side** (they can disagree). Before **releasing** an MES work
   order, confirm the ERP order **exists and is released** - releasing against a stale or absent ERP order
   authorizes build and consumption with no ERP backing.
6. Pin the action's identifiers: the work order, the operation, the entity, and - where required - the NC / hold
   reason code and the signature's meaning.
7. **Re-read at execute** - a machine or another operator may have moved, held, or consumed since you read.
- **The control layer is the sharpest line.** Reading a device attribute / Historian tag is a read; **writing a
  device-mapped attribute is a setpoint or command that physically actuates the line - hard gate, named approver
  who owns the equipment, a re-read of the live device and interlock state, and confirmation the line is safe.**
  The default is that the agent does not write setpoints or commands at all - MES records and coordinates; the
  control system and its qualified operators command. Never write past an interlock to go faster.
- Treat a confirm as a material + financial posting: know the operation BOM and whether it backflushes before you
  confirm, and size a scrap / NC-scrap / confirmation reversal - each is a loss or an ERP commitment change, not
  a correction.
- Never force a confirm past an out-of-spec / out-of-control value or a missing signature, edit a value to pass,
  lift a hold, override entity qualification, reclassify a locked downtime reason to move OEE, or make a skip /
  out-of-sequence move to go faster; a hold or open NC means stop.
- In a regulated line, an electronic signature is a hard gate - the operation cannot confirm without it; confirm
  the record is clean first.
- Genealogy / as-built is permanent and scopes recalls - verify the component lots before consume / produce /
  split / merge; a wrong association mis-scopes a future recall and cannot be cleanly rewritten.
- Do not edit or backfill AVEVA Historian archive data to "correct" a reading - it is the process record and a
  data-integrity boundary.
- For anything in the destructive row (control-layer setpoint / command write, scrap, NC scrap / return, confirm
  reversal, hold / qualification / limit override, out-of-sequence move, locked-reason edit to alter OEE,
  Historian archive edit, released-definition change): named approver, re-read, and log the reason.

## References (load on demand)
- `references/wip-genealogy-and-confirmation.md` - the work order / operation / WIP state machine, start vs
  confirm, backflush and the ERP confirmation hand-off (goods issue + finished-goods receipt), material
  consumption and as-built genealogy, lot split / merge, nonconformance and disposition, quality holds, quality
  data collection and spec vs control limits, and electronic signatures / Part 11.
- `references/control-layer-oee-and-historian.md` - the AVEVA System Platform (ArchestrA / Galaxy) and Historian
  stack under MES, object attributes and I/O references via OI Server / DAServer, why a setpoint / command write
  is destructive, interlocks, the entity / equipment state model, OEE (Availability x Performance x Quality),
  downtime events and reason codes and the performance-record integrity, and the Historian read vs archive-edit
  boundary.
