# AVEVA MES - the control layer, OEE, and Historian

The AVEVA-specific surface under MES: the System Platform / ArchestrA stack that data collection runs on, why a
device-mapped attribute write is the most destructive action in the whole skill, and how OEE and downtime feed
the performance record. Read when a task touches a device attribute / setpoint / command, a Historian tag, the
entity / equipment state, OEE, or a downtime reason code.

## Contents
- The stack under MES (System Platform, Galaxy, Historian, OI Server)
- Attributes and I/O references
- Why a setpoint / command write is destructive
- Interlocks
- The entity / equipment state model
- OEE (Availability x Performance x Quality)
- Downtime events and reason codes
- The performance-record integrity issue
- AVEVA Historian - read vs archive edit
- Gating notes

## The stack under MES (System Platform, Galaxy, Historian, OI Server)
AVEVA MES data collection typically runs on top of the AVEVA supervisory / SCADA stack:
- **AVEVA System Platform (ArchestrA)** - the supervisory application platform. The application is a set of
  **automation objects** (from **templates**) with **attributes**, held in a **Galaxy** (the object namespace /
  repository). This is where live plant values live at runtime.
- **OI Server (Operations Integration server; formerly DAServer)** - the driver layer that connects System
  Platform to physical devices (PLCs, SCADA, instruments). An object attribute with an **I/O reference** reads
  and writes device points through the OI Server.
- **AVEVA Historian (ex-Wonderware Historian / IndustrialSQL Server / InSQL)** - the time-series store archiving
  attribute / tag values over time.
- **InTouch HMI / OMI (Operations Management Interface)** - the operator visualization and control surface that
  renders the objects and can send operator commands.

For MES, this stack is normally a **source of read data** (current values and history for data collection).
The danger is that the same connection can **write**.

## Attributes and I/O references
- An **attribute** is a named value on an automation object - e.g. a **`PV`** (process value, a measured input),
  a **`SP`** (setpoint, a control target), an output, or a command / mode bit.
- An attribute may be **in-memory** (internal to the supervisory app, harmless to write) **or carry an I/O
  reference** to a device point through the OI Server (writing it drives the physical device).
- **You cannot reliably tell the two apart from the value alone.** A `PV` is usually an input (read), but a
  `SP`, an output, or a command / mode attribute is very likely device-mapped. The definitive check is the
  attribute's **I/O reference** in the Galaxy object configuration (is it bound to an OI Server item); when you
  cannot inspect that, treat any such attribute as device-mapped until proven otherwise.

## Why a setpoint / command write is destructive
The full hazard framing and the hard gate are in SKILL.md ("The control-layer write"). The mechanism, in short:
a write to a device-mapped attribute goes System Platform -> OI Server -> PLC / SCADA and **physically actuates
the line** (changes a temperature / pressure / speed / level target, starts or stops a motor, opens or closes a
valve, downloads a recipe value set). It has **no undo**, it can bypass an interlock or override an operator, and
by default the MES agent does not do it - MES records and coordinates; the control system and its qualified
operators command. The safe way for an agent to touch the control layer is to **read** (current attribute values
and Historian trends) - that confirms a condition (e.g. a line running hot) without commanding anything.

## Interlocks
An **interlock** is a control-system condition that prevents an action (a valve will not open unless upstream
pressure is safe; a motor will not start unless a guard is closed). Interlocks live in the PLC / control logic,
not in MES. A device write can attempt to act **past** an interlock; overriding or defeating one to force a move
is destructive and a safety concern - never do it to go faster.

## The entity / equipment state model
The plant is modeled as a hierarchy of **entities** (site -> area -> line -> cell -> unit / machine). An entity
carries an operating state that OEE is computed from:

| State | Meaning |
|---|---|
| **Running** | producing at rate |
| **Idle** | up but not producing |
| **Setup / Changeover** | being changed over (often a planned loss) |
| **Down (unplanned)** | stopped by a fault / breakdown (an availability loss) |
| **Planned Down** | stopped for a planned reason (maintenance, no demand, break) |
| **Blocked** | cannot output - the downstream entity is full |
| **Starved** | cannot run - the upstream entity is not feeding it |

An entity must be **available and qualified** to run an operation; confirming against a down, in-setup, or
unqualified entity is blocked, or if overridden confirms production on an uncertified resource.

## OEE (Availability x Performance x Quality)
**OEE = Availability x Performance x Quality:**
- **Availability** = run time / planned production time (lost to unplanned down and setup).
- **Performance** = (ideal cycle time x total count) / run time (lost to slow cycles and micro-stops).
- **Quality** = good count / total count (lost to rejects and rework).

Because OEE is **computed** from entity states, cycle counts, and quality, any change to a downtime reason, a
reject count, or a cycle figure moves the number. The **six big losses** (breakdowns, setup / adjustment, small
stops, reduced speed, startup rejects, production rejects) map onto the three OEE factors.

## Downtime events and reason codes
- A **downtime event** is an interval of stoppage on an entity, classified with a **reason code** (and often a
  category / fault code): planned vs unplanned, which of the six big losses, and the specific cause.
- Assigning or splitting a reason **before it locks** is a reversible classification. It is a genuine judgment -
  mis-classifying an unplanned breakdown as planned, or a real loss as a micro-stop below the tracking
  threshold, understates the loss and mis-directs improvement spend.

## The performance-record integrity issue
- The downtime reason and the reject count are **record entries that feed OEE and loss reporting**, not cosmetic
  labels. Reclassifying a **locked** reason retroactively to improve the OEE number hides a real loss from the
  decisions OEE drives - it is a **data-integrity breach of the performance record**, not housekeeping.
- If a locked reason genuinely must be corrected, make it a recorded, reasoned change (append the corrected
  classification with its justification), never a silent overwrite, and never to move the number.

## AVEVA Historian - read vs archive edit
- AVEVA Historian archives time-series **tags / points** from the control layer and MES. For an agent it is
  almost always a **read**, in two forms: a **current-value / snapshot read** (the live value) and an
  **archived-history query** (values over a time range) - both safe.
- Two writes to know: **tag configuration** (creating tags, changing collection setup) is a **committing** config
  change - it alters what is recorded downstream (OEE, quality, regulatory data) and the history it did not
  collect cannot be recovered, so it is not a low-risk edit; and
  **editing or backfilling archived values** (a manual insert / "data flush") corrupts the process record and,
  in a regulated context, is a **data-integrity violation** - not a cleanup. Treat archive edits / backfills as
  destructive.

## Gating notes
- Read an attribute current value / Historian tag / trend = **read** (the default way to touch the control layer).
- **Write a device-mapped attribute (setpoint / output / command / mode) = destructive, hard gate** - it
  physically actuates the line, has no undo, and by default the agent should not do it. Downloading a recipe /
  setpoint set to the line = destructive (a batch of device writes).
- Override / defeat an interlock to force a move = destructive and a safety concern.
- Assign / split a downtime reason before lock = reversible; **lock / commit** a reason that feeds OEE =
  committing; **retroactively edit a locked reason to alter OEE** = destructive (performance-record integrity).
- Historian read / trend = read; tag / collection config = committing (alters the downstream record); archive
  edit / backfill = destructive.
