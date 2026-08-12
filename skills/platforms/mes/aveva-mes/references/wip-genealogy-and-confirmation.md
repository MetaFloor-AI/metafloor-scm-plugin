# AVEVA MES - WIP, genealogy, confirmation, and quality

How AVEVA MES (Operations and Quality) structures production and why confirming an operation is a material and
financial commit. Read when a task touches the work order / operation / WIP state machine, backflush and the ERP
hand-off, lot genealogy, quality data collection, or electronic signatures.

## Contents
- The production model (work order -> operation -> WIP)
- Start vs confirm - the commit
- Backflush and the ERP confirmation hand-off
- Material consumption and as-built genealogy
- Lot split / merge
- Nonconformance and disposition
- Quality holds
- Quality data collection - spec vs control limits
- Electronic signatures (21 CFR Part 11)
- Gating notes

## The production model (work order -> operation -> WIP)
- A **work order (production order)** authorizes building a quantity of an **item**; it is usually downloaded
  from ERP and exists on both sides. States: **Created / Released -> In Process / Running -> Completed ->
  Closed** (ERP-side).
- The work order runs through a **routing** of **operations**, each performed **at an entity** (a modeled piece
  of equipment). Each operation carries required data collection, resources, the BOM to consume, and sign-off
  rules.
- **WIP** is the tracked quantity moving through the operations. Per-operation WIP state: **Queued -> Running /
  In Work** (started, entity claimed) **-> Confirmed / Complete** (WIP posted, material consumed, advanced).
- Out-of-sequence and skip moves are blocked unless explicitly overridden - an override is a destructive act,
  because the genealogy and data-collection record then have a gap.

## Start vs confirm - the commit
- **Start / move-in** begins the operation and claims the entity. Classify it by **what it does, not who
  triggered it**: a start that only claims the entity and posts nothing is reversible (cancel / undo before
  confirm), whether a person or MES queue logic initiated it; a start that issues a start-command to the
  equipment / PLC (common on a machine-integrated line, but a manual start can do it too) begins physical
  processing, may not be cleanly cancellable, and is committing - and where it writes a device command it falls
  under the control-layer gate.
- **Confirm / complete / move-out** is the commit. In one transaction it posts the produced WIP quantity,
  **backflushes** the operation BOM, records the operation's data collection, and advances the WIP to the next
  operation. This is the action that moves inventory and writes the permanent record.

## Backflush and the ERP confirmation hand-off
- **Backflush** consumes the operation's BOM components automatically at confirm, at **standard** quantities,
  with no explicit pick. If the operator used more or less than standard, ERP on-hand and genealogy are wrong
  until corrected; over-consumption can drive an ERP component negative or block the confirm.
- The confirmation is the **ERP hand-off**: the component consumption posts as a **goods issue** to ERP, and the
  **final operation's completion posts a finished-goods receipt** to ERP. These are audited financial postings,
  not internal status flips.
- **Reversing a confirmation is an ERP-side counter-posting**, not an MES undo: it posts a reversing production
  event plus counter goods movements (`sap-mm`). Both the confirm and its reversal stay in the trail,
  and a quantity already issued / consumed downstream cannot be restored. A confirm can also succeed in MES but
  fail in ERP (or the reverse) - a reconciliation gap; read both sides, do not blindly re-post (re-posting
  double-issues the components).

## Material consumption and as-built genealogy
- Consuming a material lot at an operation ties the **actual lot and quantity** to the produced lot as the
  permanent **as-built genealogy** (backward trace: what went in; forward trace: where it went).
- Genealogy **scopes recalls**. A wrong consumed lot mis-scopes a future recall even when the quantity is right.
- You cannot cleanly rewrite genealogy - a correction is a new disassembly / re-assembly transaction, and the
  original association stays in the record.

## Lot split / merge
- **Splitting** a lot creates child lots that inherit the parent's genealogy; **merging** joins genealogies.
  Quantity and as-built both change.
- A mistaken split / merge mis-attributes which units carry which component lots - reverse only if the
  child / merged lot has had no downstream processing; once it moves, the branch stands and needs a correcting
  transaction.

## Nonconformance and disposition
- A **nonconformance (NC)** is a defect record logged against a WIP / lot / operation with a code. Logging it
  can **auto-hold** the WIP. The record contains nothing on its own - the **disposition** is the gate.
- Disposition paths: **use-as-is** (releases nonconforming stock - committing), **rework** (routes to a repair
  operation and re-processes - committing, and each later rework step is its own action to re-gate),
  **scrap** (destroys stock and cuts yield - destructive), **return** (reverses the receipt / commitment -
  destructive).
- A single disposition can **split** across a quantity (part use-as-is, part rework, part scrap). Gate each
  path by its own class, not the whole disposition at the lowest risk.

## Quality holds
- A **hold** stops a lot / WIP / order from advancing, being consumed, or shipping. States: **Active ->
  Released**.
- A hold is **asymmetric**: placing it is a low-friction, reversible containment (when in doubt, hold);
  **releasing** it returns material to flow, belongs to the role that set it, and needs the reason resolved
  (the NC dispositioned). Do not lift a hold to hit a schedule.

## Quality data collection - spec vs control limits
- Data collection captures parameter values at an operation against two different kinds of limit:
  - **Specification limit** - conformance: is *this unit* good or bad? An out-of-spec value can **auto-hold**
    the WIP or **block confirm**.
  - **Control limit (SPC)** - process stability: is the *process* drifting? An SPC signal (a point beyond a
    control limit, a run, a trend per Western-Electric-style rules) is a **stability alarm**, not automatically
    a reject.
- A value can be **in-spec but out-of-control** (make the units, but the process is drifting - investigate) or
  **out-of-spec but in-control** (a bad unit from a stable process). Read which limit fired before deciding.
- Editing a captured out-of-spec / out-of-control value to make it pass is a **data-integrity breach** - the
  audit trail records the edit, so the "fix" is itself evidence.

## Electronic signatures (21 CFR Part 11)
- In a regulated setup (pharma, food / beverage), an operation confirm or a buyoff can require an **attributed
  electronic signature** with a meaning (performed by / verified by / approved by).
- The step **cannot confirm without it** - a blocking precondition, not an optional field. Once applied it is
  **permanent**: it cannot be removed, cannot be signed on another's behalf, and a correction is an appended
  record / signature, never an edit of the original.

## Gating notes
- Start / move-in that only claims the entity = reversible; a start that commands equipment = committing (a
  device command falls under the control-layer gate).
- Confirm / complete (WIP + backflush + ERP goods issue) = committing; final-operation completion (finished-goods
  receipt) = committing.
- Consume / produce a lot into genealogy = committing.
- Reverse a confirmation = destructive (ERP counter-posting, not an undo).
- Place a hold = reversible; release a hold = committing (the gated direction).
- Raise an NC = reversible; disposition use-as-is / rework = committing; disposition scrap / return = destructive.
- Record a data value before sign-off = reversible; edit an out-of-spec value to pass, or edit a signed value =
  destructive (data-integrity).
- Any electronic signature = a hard gate on the write it belongs to.
- Scrap, skip / out-of-sequence move, released-definition edit while orders in flight = destructive.
