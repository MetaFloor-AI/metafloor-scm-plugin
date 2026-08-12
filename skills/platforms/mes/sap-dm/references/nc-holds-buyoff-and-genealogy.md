# SAP DM - nonconformance, holds, buyoff/e-signature, and genealogy

The containment, disposition, sign-off, and traceability machinery of SAP Digital Manufacturing. Read when a
task touches an NC, a hold, a buyoff/electronic signature, data collection limits, as-built genealogy, machine
integration, or the DM Insights read.

## Contents
- Nonconformance (NC) and disposition paths
- Holds and hold codes
- Data collection and limits
- Buyoff and electronic signatures (eDHR)
- As-built genealogy and recall scoping
- Work instructions
- Machine integration (Plant Connectivity)
- DM Insights (the read)
- Gating notes

## Nonconformance (NC) and disposition paths
An **NC** is a defect record logged against an SFC (and usually an operation) with an **NC code** (a coded
defect reason). Logging an NC records the defect and can **auto-hold** the SFC, but it contains nothing on its
own - the **disposition** decides what happens:

| Disposition | Effect | Class |
|---|---|---|
| **Use-as-is** | releases the nonconforming quantity to continue | Write (committing) |
| **Rework** | routes the SFC to a rework/repair operation; re-consumes material and re-inspects | Write (committing) |
| **Scrap** | destroys the quantity; cuts order yield; posts a scrap confirmation | Destructive |
| **Return** | reverses the receipt/commitment for the quantity | Destructive |

A single NC disposition can **split** a quantity across paths (part use-as-is, part rework, part scrap) - gate
each path by its own class, never the whole disposition at the lowest risk. The NC and its disposition are
recorded permanently in the SFC history.

## Holds and hold codes
A **hold** stops an SFC (or a group of SFCs) from being processed, with a **hold code / reason**. States:
**Active -> Released**. Key properties:
- **Placing is protective and reversible** - low friction, "when in doubt, hold".
- **Releasing is the gate** - it returns the SFC to flow, belongs to the role that set it, and needs the reason
  resolved (the NC dispositioned, the value re-measured). Do not lift a hold to hit a schedule.
- Holds can be **automatic** (an out-of-limit data collection or a logged NC auto-holds the SFC) or manual.
- A hold does **not** undo work already done - the SFC keeps its operation and resource state.

## Data collection and limits
**Data collection (DC)** captures parameter values at an operation (dimensions, torque, temperature, test
results) against **min/max limits** or a target. Behavior:
- A value **in limits** records and lets sign-off proceed.
- A value **out of limits** can **auto-hold** the SFC or **block sign-off** per the DC definition.
- **Editing a recorded value to pass** is a data-integrity breach - the append-only audit trail records the
  original, the edit, who, and when; the "fix" is itself evidence.
- Some DC is a prerequisite for sign-off; a required parameter not collected blocks completion.

## Buyoff and electronic signatures (eDHR)
A **buyoff** is a required, attributed sign-off at an operation - a quality/verification approval, often
restricted to a specific **role/user**, and in a regulated/eDHR (electronic device history record) setup backed
by an **electronic signature** with a meaning (performed / verified / approved by). Properties:
- The SFC **cannot complete/advance** past the operation without the required buyoff.
- It is **attributed and audited**; it cannot be **self-signed** where segregation of duties applies, and it
  cannot be signed on another's behalf.
- Once applied it is **permanent** - a correction is an appended record/signature, never an erase of the original.
- Buyoffs may be **partial** (per unit/quantity) or full; a partial buyoff gates only its portion.

Treat a buyoff/e-signature as a **blocking precondition** on the sign-off write, not an optional edge case.

## As-built genealogy and recall scoping
**Genealogy / as-built** is the permanent record of which component lots/serials (and which resource/operator)
went into which SFC, built by backflush and by explicit assembly. It is the basis for **recall scoping**
(where-used / where-consumed). Rules:
- A **wrong component association** (wrong lot/serial consumed or assembled) mis-scopes a future recall.
- You **cannot cleanly rewrite** genealogy; a correction is a new disassembly/assembly transaction, and the
  original association stays in the record.
- Split/merge **branches/joins** genealogy - verify lineage after either.
- Verify the component lots/serials **before** assemble / consume / split / merge, not after.

## Work instructions
Work instructions (documents, images, steps) display at an operation to guide the operator. Viewing them is a
**read**; their authoring lives in the production-process version model (a draft edit is reversible, a
released-version change is change-controlled).

## Machine integration (Plant Connectivity)
Connected equipment integrates via **SAP Plant Connectivity (PCo)** and the DM machine/automation layer (MII
lineage). It can drive **automatic data collection**, **Start**, and **sign-off** from the machine. Consequence:
an automated Start/sign-off/DC **commits exactly like a manual one** - an equipment message that signs off an
operation confirms and backflushes to ERP just as an operator would. Automated actions are **not exempt** from
the gate; treat a machine-driven sign-off as the same committing posting.

## DM Insights (the read)
**SAP Digital Manufacturing Insights** is the analytics/OEE/KPI capability (MII lineage) - it reads the
execution record and aggregates it (OEE, throughput, scrap/yield, downtime). For an agent it is almost always a
**read**. Do not confuse an Insights aggregate with live WIP or the executable SFC/operation state; acting on an
aggregated number as if it were current, gate-able state is an error. Configuration of Insights models/tags is a
config write, not execution.

## Gating notes
- **Log NC** = reversible (a record; may auto-hold). **Disposition NC**: use-as-is / rework = committing; scrap
  / return = destructive.
- **Place a hold** = reversible (protective). **Release a hold** = committing (the gated direction).
- **Data collection** in limits = write (recorded); **editing a value to pass** an out-of-limit or forcing
  sign-off past it = destructive (data-integrity breach).
- **Buyoff / e-signature** = committing and a hard gate; **modifying/deleting a signed buyoff** = destructive.
- **View genealogy / work instructions / DM Insights** = read; **wrong assembly** that mis-records as-built =
  committing with permanent traceability effect.
- **Automatic (machine-driven) Start/sign-off/DC** = the same class as the manual action it performs.
