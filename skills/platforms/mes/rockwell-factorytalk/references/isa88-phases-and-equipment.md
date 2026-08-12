# FactoryTalk Batch - ISA-88 procedural model, phases, and equipment

How FactoryTalk Batch and PharmaSuite structure and run production, and why "advance the phase" is a physical
commit. Read when a task touches recipes, phases, equipment arbitration/binding, or the phase recovery path.

## Contents
- The recipe / procedural hierarchy (ISA-88)
- Recipe types and the master-recipe lifecycle
- The phase state machine and command set
- Equipment / area model, arbitration, and binding
- Class-based vs instance-based recipes
- FactoryTalk Batch execution + PhaseManager / Logix
- FactoryTalk ProductionCentre (FTPC) - the discrete analogue
- FactoryTalk Historian (the read)
- Gating notes

## The recipe / procedural hierarchy (ISA-88)
FactoryTalk Batch and PharmaSuite follow the ISA-88 (S88) model. A recipe's **procedure** decomposes into:
- **Procedure** - the whole production sequence for a product.
- **Unit procedure** - the part of the procedure that runs on one **unit** (one vessel / reactor / line).
- **Operation** - a major processing activity within a unit procedure (charge, react, transfer, clean).
- **Phase** - the smallest procedural element that actually commands equipment (dose, agitate, heat, hold-at-
  temperature). **The phase is where physical action happens.** Everything above it is sequencing.

In **FTPC discrete** work the analogue is an **operation** on a **routing** (start / complete an operation at
a work center). The procedural depth differs, but the gating rule is identical: the element that runs
equipment and consumes material is the commit; the levels above it are navigation.

## Recipe types and the master-recipe lifecycle
S88 recipe types, general -> specific: **general recipe -> site recipe -> master recipe -> control recipe**.
Operationally the two that matter:
- **Master recipe (MBR)** - the approved, versioned template bound to a site's equipment class and material
  list. Lifecycle: **In Preparation** (draft, freely editable) -> **In Review** -> **Approved / Effective**
  (governs every new batch) -> **Retired / Obsolete**.
- **Control recipe** - the runtime instance created when an order is released: the master recipe copied and
  **bound** to a specific order, unit(s), and formula values. One control recipe = one batch.

Why it bites: editing an **effective** master recipe is a **fleet change** - it re-instantiates for every new
batch, and change control governs it. Editing a **control recipe** touches one batch. A pre-effective draft
is the only reversible recipe edit. Approving a recipe to effective is itself the change-control event.

## The phase state machine and command set
A phase (in FactoryTalk Batch and, at the controller, in PhaseManager) runs a state machine. Core states and
the transient states between them:

| State | Meaning |
|---|---|
| **Idle** | ready, not running |
| **Running** | executing its logic (transient: Restarting) |
| **Complete** | finished normally |
| **Holding / Held** | paused to a safe state on command or fault; **Held** is stable |
| **Restarting** | resuming from Held back toward Running |
| **Stopping / Stopped** | controlled shutdown; **Stopped** is terminal for the run |
| **Aborting / Aborted** | fast shutdown to a safe state; **Aborted** is terminal, product usually lost |
| **Pausing / Paused** | paused at the next safe step (lighter than Hold), resumed by Resume |

Command set: **Start**, **Hold**, **Restart**, **Stop**, **Abort**, **Reset**, **Pause / Resume**, plus mode
(**Automatic / Semi-automatic / Manual**). Key asymmetry:
- **Hold -> Restart** is the recoverable pause: the phase parks to a safe state, you fix the cause, Restart
  resumes it.
- **Stop** ends the run in a controlled way; **Abort** ends it fast. Both are **terminal** - from Stopped or
  Aborted you can only **Reset** to Idle, not Restart to Running. In-process material after an Abort is usually
  compromised and scrapped.
- **Reset** clears a Complete / Stopped / Aborted phase back to Idle so the equipment can be reused.

A **faulted** phase (equipment fault, out-of-limit, interlock) typically drives itself to **Held**; it must be
corrected and Restarted or Aborted. Forcing past a fault (manual mode, forced transition) bypasses the
interlock that fired and is auditable.

## Equipment / area model, arbitration, and binding
The equipment model (built in the Equipment Editor) is **process cell -> unit -> equipment module -> control
module**. Runtime rules:
- A batch **acquires** a unit before running phases on it; the acquisition is **exclusive** so two batches do
  not run into the same vessel.
- **Arbitration** resolves contention when multiple batches request the same shared equipment (a shared header,
  a common transfer line, a CIP skid). It queues or blocks - it is a safety mechanism, not a scheduling
  nuisance. Forcing or overriding acquisition can cross-contaminate.
- A unit must be **available and qualified** (not down, not disqualified, clean per line clearance) to run a
  phase. Overriding qualification runs product through uncertified equipment.

## Class-based vs instance-based recipes
- **Instance-based** - the recipe names a specific unit; the batch always runs on that unit.
- **Class-based (unit-class)** - the recipe names a **unit class**; at runtime the batch **binds** to any
  qualified member of that class (whichever reactor is free). Where the batch actually runs is a **runtime
  fact**, not a recipe constant - always re-read the bound unit before acting on "the batch on R-201".

## FactoryTalk Batch execution + PhaseManager / Logix
- The **FactoryTalk Batch Server** executes the control recipe: it sequences unit procedures / operations /
  phases and issues phase commands.
- Each **equipment phase** lives in the **ControlLogix / CompactLogix** controller as a **PhaseManager** state
  machine (the PLC-level equivalent of the phase states above). The Batch Server commands it and reads its
  state over **FactoryTalk Live Data / OPC UA**.
- **eProcedure** handles manual / semi-automatic phases: operator prompts, manual data entry, and signatures
  that become part of the record.
- Consequence: a command from the Batch Server (or a client such as Batch View) **runs PLC logic on live
  equipment**. The MES action and the physical action are the same event - a command is not a simulation
  unless the area / phase is explicitly in **test mode**.

## FactoryTalk ProductionCentre (FTPC) - the discrete analogue
FTPC runs discrete / mixed-mode production as **operations on a routing** rather than S88 phases. The mapping:
- **Work order** (from ERP) -> a **routing** of **operations** at **work centers**; a **unit / serial / lot**
  is tracked through the routing.
- **Operation state**: **not started -> started -> complete**, with hold / pause available on an in-process
  operation as on a Batch phase. Start / complete an operation is the commit - it posts progress and consumes
  the operation's components (the FTPC equivalent of running a phase).
- **Work-center binding** - an operation runs at a qualified work center; the same available-and-qualified
  rule as unit acquisition applies.
- **Data collection, genealogy, nonconformance, and holds** work as in Batch / PharmaSuite. The gating rules
  are identical: the operation that runs equipment and consumes material is the commit; the levels above it
  (routing, order) are navigation. Nonconformance dispositions and holds follow the same reversible /
  committing / destructive split as deviations.

## FactoryTalk Historian (the read)
FactoryTalk Historian (OSIsoft PI lineage) archives time-series **tags / points** collected from controllers
and the MES. For an agent it is almost always a **read**, in two forms - a **current-value / snapshot read**
(the live tag value) and an **archived-history query** (values over a time range) - both safe. Two writes to
know: **tag / point configuration** (creating tags, changing collection / interface setup) is a **config
write**; and editing or **backfilling** archived values corrupts the process record and, in a GxP context, is
a data-integrity violation, not a cleanup. Treat archive edits / backfills as destructive.

## Gating notes
- Running / completing a phase or operation with a BOM = committing (equipment + material).
- **Hold / Pause** a phase = reversible (protective park to a safe / next-safe state). **Restart / Resume** =
  committing (resumes live equipment). **Stop** and **Abort** = destructive (terminal for the run - Reset to
  Idle only, never Restart; Abort usually loses product). **Reset** a terminal phase to Idle = reversible.
- Acquiring / binding a unit before the batch runs material = reversible (a reservation). Overriding
  arbitration or qualification = destructive.
- Editing an **In Preparation** recipe = reversible; approving to effective, or editing an **effective**
  recipe while batches are in flight = destructive / change-controlled.
- Historian reads / trends = read; archive edits / backfills = destructive.
