---
name: sap-dm
description: "SAP Digital Manufacturing (DM / DMC, cloud MES; lineage SAP ME + SAP MII) - safe discrete and process shop-floor execution and the S/4HANA hand-off - production / process / shop orders, routings and operations, the Plant Operations Dashboard (POD), SFC (shop-floor-control) numbers and status, Start / Complete / Sign-off, data collection against limits, component assembly / backflush and as-built genealogy, nonconformance (NC) and holds, buyoff / e-signature, and order confirmation to ERP (labor activity + goods issue 261 + goods receipt 101). Use when the connected MES is SAP Digital Manufacturing, SAP DM, DMC, SAP ME, or SAP MII, or the user mentions a POD, an SFC number, a shop / production / process order, an operation Start / Complete / sign-off, a routing or production process, data collection, an NC / nonconformance disposition, a hold, a buyoff, assembly / component consumption or backflush, genealogy / as-built, or a production confirmation / goods receipt back to S/4HANA."
---

# SAP Digital Manufacturing - operating the shop floor safely

SAP Digital Manufacturing (SAP DM, formerly SAP Digital Manufacturing Cloud / DMC) is SAP's cloud MES: it
holds every unit of in-process material, drives it through a routing (or a process master recipe), records
what was consumed and measured, and hands the result back to ERP. Its lineage is **SAP ME** (Manufacturing
Execution, the SFC/POD execution engine) plus **SAP MII** (Manufacturing Integration and Intelligence, the
plant connectivity + analytics layer), reimagined in the cloud. What makes SAP DM different from the other MES
vendors, and what makes it dangerous, is the tight **S/4HANA seam**: **completing (signing off) an operation
does not just flip a status - it sends a production confirmation to ERP that posts labor activity, backflushes
the operation's components as a goods issue (movement type 261), and, at the final operation, receives the
finished goods (101).** That confirmation is an audited financial event with real money and stock behind it.
This skill classifies those actions so the harness can gate them, plus the edge states (SFC split/merge and
genealogy, buyoff/e-signature, NC disposition, the ERP reconciliation gap) and recovery paths that decide
whether a mistake is fixable.

## When this applies
Connector is SAP Digital Manufacturing (DM / DMC) or its lineage SAP ME / MII, and the work is shop-floor
execution. When NOT:
- a different MES: Siemens Opcenter / Camstar / SIMATIC IT -> `siemens-opcenter`
- a different MES: Rockwell FactoryTalk / PharmaSuite / FactoryTalk Batch -> `rockwell-factorytalk`
- the ERP side of the seam - inventory quantity/valuation, the goods movements (261/101) the confirmation
  posts, cancelling a confirmation, the production order in S/4 PP, posting periods, costing -> `sap-mm`
- warehouse staging / picking / the pickable stock behind a backflush -> `sap-ewm` or
  `manhattan-wms` (DM component availability is not the same as ERP/EWM pickable, staged stock)
- a formal quality management system - inspection lots, quality notifications, CAPA, results recording on the
  ERP/QM side -> `sap-qm`
- planning / MRP / scheduling that creates the order upstream -> `sap-ibp` or `kinaxis`

Seam with ERP/QM: SAP DM owns the WIP truth (where each SFC is, what operation it is at, what was consumed,
as-built genealogy) and dispositions defects at the point of manufacture; ERP (`sap-mm`) values the
inventory and books the goods issue and finished-goods receipt the confirmation triggers, and a formal QMS
(`sap-qm`) owns inspection lots and CAPA. DM contains and dispositions on the floor; the QMS/ERP is
the financial and compliance system of record downstream. The confirmation is the wire between them.

## Contents
- Object & state model
- Vocabulary that bites
- Operations: read / write / destructive
- Reclassification rules
- Worked example (an order, end to end)
- Gotchas that bite
- Edge states & special cases
- Recovery patterns
- Guardrails
- References

## Object & state model (reason about state, not nouns)
- **Order (production / process / shop order)** - authorizes building a quantity of a material; downloaded from
  S/4HANA (or ECC) as a production order (discrete) or process order (process industry). States: **Created /
  Released** (the floor may build and consume against it) -> **In Process** -> **Done / Completed** ->
  **Closed / TECO** (technically complete, ERP-side). Releasing binds material; completing posts finished
  quantity back to ERP. The order lives in ERP too - the two copies can disagree.
- **SFC (shop-floor-control number)** - the central tracked object: a quantity of the order's material moving
  through the routing (the SAP analogue of Opcenter's container or a Batch control recipe). It carries a
  **quantity**, an **overall status**, its **current operation**, and its **as-built genealogy**. Overall
  status: **New** -> **Active / In Queue** -> **On Hold** -> **Done** -> **Scrapped**. **Deleted** is distinct
  from Scrapped - it removes an SFC that has **not been executed** (no confirmation posted), whereas Scrapped
  destroys built WIP and cuts yield; do not treat Deleted as a reversible alternative to Scrapped once work has
  posted. An SFC may be **serialized** (one unit) or **quantity/batch** (a number that can be partially
  completed or split).
- **Operation & routing (production process)** - the ordered sequence of **operations** (discrete) or
  **phases** (process, against a master recipe) the SFC follows. Each operation carries required data
  collection, resources, components (BOM) to consume, and buyoff/sign-off rules. Out-of-sequence and skip moves
  are blocked unless explicitly overridden. Per-operation SFC state: **In Queue** -> **Active / In Work**
  (started) -> **Done at operation** (signed off, advanced). Detail in `references/sfc-routing-and-confirmation.md`.
- **POD (Plant Operations Dashboard)** - the operator's execution surface where actions happen: Start, Complete
  / Sign-off, Log NC, Assemble, collect data, Buyoff, Hold. It is a configurable screen (POD Designer), not a
  system of record - the SFC state it drives is.
- **Production process / routing + BOM version** - the executable, versioned definition of the build (operations,
  components, data collection, work instructions). Its own state runs **draft/new -> released/current ->
  archived**. Editing a **draft** is reversible; editing a **released/current** version changes behavior for
  every new order that uses it and can re-route in-flight SFCs at their next operation - a change-controlled
  fleet change.
- **Nonconformance (NC) + disposition** - a defect record logged against an SFC/operation with an NC code, and
  the disposition that resolves it. States: **Open** -> **Dispositioned** (use-as-is / rework route / scrap /
  return) -> **Closed**. Logging an NC can auto-hold the SFC; the disposition, not the record, decides release.
- **Hold** - a containment that stops an SFC (or a group) from processing, with a hold code/reason. States:
  **Active** -> **Released**. Placing is reversible; releasing is the gate. Detail in
  `references/nc-holds-buyoff-and-genealogy.md`.
- **Buyoff / e-signature** - a required, attributed sign-off at an operation (often by a specific role, with an
  electronic signature in a regulated/eDHR setup). The SFC cannot complete/advance past the operation without
  it; once applied it is permanent and cannot be self-signed or bypassed.
- **Confirmation** - the message SAP DM sends to ERP on sign-off/completion: labor activity (for costing),
  component goods issue (261 backflush), and, on final completion, finished-goods receipt (101). This is the
  financial hand-off - not internal to DM.

## Vocabulary that bites
- **SFC (shop-floor-control number)** - the tracked material unit, not an inventory row. It owns WIP state,
  current operation, and genealogy. "Process an SFC" means run an operation on it, not move it in a warehouse.
- **Sign-off / Complete** - the commit at an operation. Completing/signing off posts operation progress,
  **backflushes** the operation's BOM (261 goods issue to ERP), records the data collection, and advances the
  SFC. **Start** only begins the operation and claims the resource - it commits nothing. Confusing Start with
  Complete under-gates the real material + financial posting.
- **Backflush** - automatic consumption of BOM components at sign-off at **standard** quantities, with no
  explicit pick. It posts a goods issue to ERP and writes as-built in the same transaction; a wrong BOM or
  standard qty silently mis-consumes and mis-records genealogy.
- **Confirmation** - the production confirmation DM posts to S/4 on sign-off. It is the ERP event: activity +
  261 goods issue + (final) 101 goods receipt. Cancelling it is an ERP-side counter-document (`sap-mm`).
- **POD (Plant Operations Dashboard)** - the operator screen driving actions. It is configurable UI, not the
  record; the SFC/operation state it changes is what matters.
- **Assembly / component consumption** - adding a specific component (lot/serial) into the SFC as-built.
  Assembling ties the actual component to the SFC's genealogy and (with backflush) consumes it in ERP.
- **Genealogy / as-built** - the permanent record of which component lots/serials went into which SFC, by which
  resource/operator. It scopes recalls; you cannot cleanly rewrite it, only append a correction.
- **Nonconformance (NC) / disposition** - the defect record and the decision that resolves it. **Use-as-is**
  releases nonconforming stock, **rework** routes it to a repair operation, **scrap** destroys it, **return**
  reverses the receipt/commitment.
- **Buyoff** - a required sign-off gate at an operation (a role-based, attributed approval, e-signed where
  regulated). The SFC cannot advance without it; it is not an optional field.
- **Data collection (DC) + limits** - parameter values captured at an operation against min/max limits. An
  out-of-limit value can **auto-hold** the SFC or **block sign-off**; editing the value to pass is a
  data-integrity breach.
- **Scrap** - terminal removal of a quantity from the SFC/order; a yield loss with a value impact. "Un-scrap"
  is limited and may not restore genealogy or operation position.
- **Production process (routing + BOM)** - the executable, versioned build definition. Editing a released
  version re-routes or re-consumes future orders (and in-flight SFCs at their next operation).
- **DM Insights** - the analytics/OEE/KPI side (MII lineage). It reads the record; it does not execute. Do not
  confuse an Insights view with the executable SFC/operation state.

## Operations: read / write / destructive
Classify every operation family by what it does to state, to material, and to the ERP/compliance record. The
action-kinds below are the same whether the connector drives the POD, a DM API call, a process-order phase, or
a machine message via Plant Connectivity. The harness maps the customer's real connector onto these classes.
No tool names - kinds of action.

| Class | SAP DM operation families | Gate | Why |
|---|---|---|---|
| **Read** | display an SFC / order and its status and current operation; SFC history and **genealogy / as-built**; the routing / production process and operation details; data-collection results; the NC list and dispositions; the hold list; buyoff status; resource / work-center status; work instructions; **DM Insights / OEE / KPI dashboards**; the activity log / audit trail; the ERP order/confirmation status | always pass | no state change; read SFC state + current operation + holds + component availability before any write, re-read at execute |
| **Write (reversible)** | author or edit a production process (routing/BOM/DC/work instruction) **while draft/not-released**; create an SFC before its first Start; create/change an order before release; **delete an unexecuted SFC** (no confirmation posted - distinct from scrap, which destroys built WIP); **Start** an SFC at an operation **(manual Start only - an automated / machine-initiated Start commands equipment, is not cleanly cancellable, and is committing, not reversible)** - begins the operation, claims the resource, undoable while no sign-off has posted and no machine-side processing began, consumes nothing; **cancel / undo a Start** before any sign-off posted; **place a hold** on an SFC (protective containment, reversed by release); park in-progress data collection **before sign-off**; raise an NC record before disposition; **queue / move an SFC in queue** between operations per the routing (no sign-off) | gate one at a time | a draft, a claim, a containment, or a correctable record; no confirmation posted, no material consumed, no disposition made |
| **Write (committing)** | **Complete / Sign-off** an operation = post progress + **backflush** the operation BOM (261 to ERP) + record DC + advance the SFC; **assemble / consume** a component into an SFC (as-built + ERP goods issue); **complete the final operation** = post finished quantity + **finished-goods receipt (101) to ERP** + set the SFC Done; **disposition an NC** use-as-is / rework; **release an order to the floor** (the DM-side release that authorizes build/consumption - the ERP order must already be created and released/downloaded; do not build a stale or ERP-unreleased order); **release a hold** (returns the SFC to flow - the gated direction); **apply a buyoff / e-signature** at an operation; **partial sign-off** of part of an SFC quantity; **split an SFC** (rewrites quantity + branches genealogy); **release a production process version to current/effective** (change-control) | gate + human approve | binds material and the physical/financial world: consumes inventory in ERP, frees or contains stock, certifies a record, receives finished goods |
| **Destructive / irreversible** | **scrap** an SFC or quantity (WIP + value loss, cuts order yield); **NC disposition -> scrap or return** (destroys stock / reverses the receipt); **cancel the ERP confirmation** for an already-signed-off operation (a counter-document in S/4 that reverses the 261/101 - `sap-mm`; not a DM undo); **override a hold, a required data collection, an out-of-limit value, a buyoff, or resource qualification** to force a sign-off; **skip / out-of-sequence move** past a required operation; **modify or delete a signed record / buyoff after e-signature** (appending a corrective record is the permitted path; changing the original is the destructive act); **change or archive a released/current production process while SFCs are in flight**; **merge SFCs** irreversibly; **close / TECO an order with open WIP** | hard gate + named approver + re-read | permanent audit trail; destroys / re-routes material and genealogy; reverses an ERP financial posting; crosses a compliance boundary; cannot be cleanly undone |

**Process orders in the table above** - the classes are identical, but on a process order the commit is a
**phase completion** against the master recipe and it posts against a **determined batch** (a batch-specific
goods receipt and often batch-determined component consumption). Gate a phase confirmation exactly like a
discrete sign-off, but pin the phase and the batch, not just the operation.

## Reclassification rules (read this)
- **Start is reversible only when it is manual and posts nothing; an automated Start is committing.** A manual
  Start can be undone (cancel start) because it only claimed the operation and posted nothing. On a
  **machine-integrated line** a Start can command the equipment to begin physical processing, and a
  machine-initiated Start may not be cleanly cancellable - so gate an automated Start as committing, not as a
  reversible claim.
- **Sign-off/Complete is the commit.** A sign-off posted a confirmation and backflushed material to ERP -
  reversing it is an ERP-side counter-document (`sap-mm`), not an undo, so it belongs in the destructive row.
- **Recording a data-collection value is reversible until sign-off; editing it to pass is destructive.** An
  unsigned value is a correctable draft; once the operation is signed off (or the value e-signed) the record is
  locked, and editing an out-of-limit value to make it pass is a data-integrity breach, not an edit.
- **A completed operation is an ERP posting, not just an MES advance.** Even a "routine" sign-off at an operation
  with a BOM backflushes components (261) and posts activity for costing; the final operation also receives
  finished goods (101). Treat sign-off as a material + financial posting, not a navigation step.
- **A hold is asymmetric - placing is protective, releasing is the gate.** Placing an SFC hold is a low-friction,
  reversible containment: when in doubt, hold. **Releasing** returns the SFC to flow, belongs to the role that
  set it, and needs the reason resolved (the NC dispositioned) - do not lift a hold to hit a schedule.
- **A split NC disposition is several actions - gate each path.** One disposition can send part of an SFC
  use-as-is, part to a rework route, part to scrap or return. Use-as-is/rework are committing; scrap/return are
  destructive. Do not gate the whole disposition at the lowest risk. And a rework route is a **chain**: the
  disposition only gated sending the SFC to rework - each later step on the rework route (a re-sign-off that
  re-consumes, or a scrap if rework fails) is its own action and must be re-gated by its own class, never
  assumed safe by the original rework decision. In a regulated context (aerospace/pharma) a use-as-is (and
  often a scrap) disposition needs a **Material Review Board (MRB)** authority, not just any approver - name the
  right approver, not a generic human gate.
- **A released production-process edit is a fleet change, not a local edit.** Changing a released/current
  routing/BOM/DC re-routes or re-consumes every new order and can hit in-flight SFCs at their next operation.
  Treat it as destructive/change-controlled - a draft (not-yet-released) edit is the only reversible kind.
- **A buyoff / e-signature is a hard gate, not a field.** In a regulated/eDHR setup, an operation sign-off or a
  buyoff may require an attributed electronic signature; the operation cannot complete without it and it is
  permanent, so treat it as a blocking precondition on that write, never an optional edge case.
- **Cancelling a confirmation is an ERP action.** DM has no clean "un-sign-off". Reversing the material and
  financial effect of a signed-off operation is a confirmation cancellation in S/4 (`sap-mm`) that
  posts counter goods movements - a destructive cross-system act, and DM and ERP must both be reconciled after.

Universal rules to teach: read the SFC state + current operation + holds + open NCs + component availability
before any write and **re-read at execute** (another operator or a machine may have moved, held, or consumed
since you read); never force a sign-off past an out-of-limit value or missing buyoff, edit a value to pass,
lift a hold, override resource qualification, or make a skip/out-of-sequence move to go faster; a hold or open
NC means stop; a buyoff/e-signature is a compliance gate, not paperwork; the confirmation is a financial event.

## Worked example (an order, end to end)
A production order for **500 EA** of an assembly is released; a **quantity SFC of 500** enters at operation
**0010**. (**Read** first: order Released, SFC New at op 0010, no holds, components available.) You **Start**
the SFC at 0010 [write-reversible] (claims the resource, no consumption yet), collect the required parameters (all in limits),
apply the operation **buyoff** [write-committing], and **Sign-off** 0010 [write-committing] - which posts progress, **backflushes** the
op-0010 BOM (say 500 of component lot A and 1000 of lot B) as a **261 goods issue to ERP**, writes those lots
into the SFC as-built, and advances the SFC to 0020. (ERP now shows, against the order, a **261 goods issue**
of 500 of lot A and 1000 of lot B plus the op-0010 activity - the confirmation is visible on the S/4 side, not
just in DM.) At 0020 a data-collection value reads **out of limit**:
DM **auto-holds** the SFC and blocks sign-off. You raise an **NC**; the disposition is a **split**: **480 EA
use-as-is** [write-committing] (released, sign-off proceeds) and **20 EA scrap** [destructive] (destroyed, order yield drops to 480).
Forcing the sign-off or editing the value to pass would have confirmed nonconforming units and left an audit
entry of the edit. At the final operation you **complete** the SFC [write-committing]: the finished **480 EA** posts a **101
goods receipt to ERP**, the SFC goes **Done**, and the as-built ties every finished unit to component lots A
and B for recall.

**A destructive-recovery variant.** Suppose after the 0010 sign-off you find the wrong component lot was
backflushed, but the SFC has already been signed off at 0020 too. There is no clean DM undo: reversing the
0010 backflush is an ERP-side **confirmation cancellation** (`sap-mm`) that posts a counter 261, and
0020 does not un-sign-off; both the confirmation and its cancellation stay in the trail. The clean path is
forward: raise an NC, correct the as-built with an appended disassembly/assembly, and let the disposition
(rework to re-do the operation, or use-as-is if still conforming) decide - not a chain of confirmation
reversals that leaves DM and ERP inconsistent. Separately, if the SFC had **completed** but the **101 goods
receipt was rejected in ERP** (closed period, order TECO, missing components), do not re-complete or blindly
reverse - hold the finished SFC, resolve the ERP-side reason (`sap-mm`), and re-trigger the receipt.

**A process-order variant.** For a process order the same flow runs as **phase completions against the master
recipe**: the commit is the phase sign-off, the confirmation posts a **batch-determined** component goods issue
and a **batch-specific** finished-goods receipt (the produced batch), and batch management ties the produced
batch - not just the SFC - into ERP. Gate the phase confirmation exactly as the discrete sign-off above, but
pin the phase and the batch, and confirm the component batch determination before the backflush. Concretely:
completing **phase 0010** against the master recipe for batch **BR-2024-037** posts the batch-determined
component goods issue and, at the final phase, a **500 KG** finished-goods receipt as the **batch-managed
material BR-2024-037** - so the recall unit is the produced batch, not just the SFC.

## Gotchas that bite (the real set - causal chains)
1. **Sign-off/Complete is the commit, not Start.** Completing an operation posts a confirmation to ERP that
   backflushes the operation BOM (261 goods issue) at standard quantities, posts labor activity, and records
   data collection in one transaction - it consumes inventory and writes as-built at once. A wrong BOM or
   standard qty silently mis-consumes and mis-confirms.
2. **Backflush consumes at standard, not actual.** If the operator used more or less than the standard BOM
   quantity, ERP on-hand and genealogy are wrong until corrected; over-consumption can drive an ERP component
   negative or block the confirmation.
3. **The final operation's completion receives finished goods to ERP (101).** It is a financial hand-off, not
   an internal status flip; an ERP-side mismatch (closed period, order TECO/closed, missing components) fails
   the receipt and strands the finished SFC as Done-in-DM but not-received-in-ERP.
4. **The confirmation can succeed in DM but fail in ERP (or vice-versa).** The SFC shows Done while the ERP
   order shows the operation un-confirmed - a reconciliation gap. Do not re-complete or blindly reverse; find
   the ERP-side reason and re-trigger. Treat DM and ERP order status as a cross-system precondition, re-read both.
5. **Reversing a confirmation is an ERP-side cancel, not a DM undo.** Cancelling a confirmation in S/4 posts
   counter goods movements (reverses the 261/101), both the confirmation and its cancellation stay in the trail
   forever, and a quantity already issued/consumed downstream cannot be restored (`sap-mm`).
6. **Scrapping destroys WIP and value and cuts order yield.** The scrapped quantity leaves the order via a
   scrap confirmation; "un-scrap" is limited (often only before the order closes) and may not restore genealogy
   or operation position. It is a loss, not a correction - size it first.
7. **NC disposition decides release, not the NC record.** Logging an NC contains nothing on its own (though it
   can auto-hold the SFC); the disposition - use-as-is releases nonconforming stock, rework routes it to a
   repair operation, scrap destroys it, return reverses the receipt - is the gate.
8. **A hold stops processing but does not undo work already done.** A held SFC keeps its operation and resource
   state; releasing it returns it to flow. Lifting a hold to hit a schedule bypasses the containment reason and
   can release stock an open NC has not dispositioned.
9. **A buyoff / e-signature is a hard gate.** The SFC cannot complete/advance past the operation without the
   required buyoff; it is attributed to the signer (often role-restricted), cannot be self-signed, and once
   applied it is permanent and part of the record.
10. **An out-of-limit data-collection value can auto-hold or block sign-off.** Forcing the sign-off, or editing
    the value to pass, is a data-integrity breach - the audit trail records who changed what and when, so the
    "fix" is itself evidence.
11. **Assembly consumes a component into the as-built AND into ERP.** A wrong component lot/serial mis-records
    genealogy and mis-consumes stock; assembling the wrong lot mis-scopes a future recall even when the quantity
    is right.
12. **Genealogy / as-built is permanent and scopes recalls.** You cannot cleanly rewrite which components went
    into an SFC; a correction is a new disassembly/assembly transaction, and the original association stays.
13. **Editing a released production process changes future orders and in-flight SFCs.** A released routing/BOM/DC
    edit re-routes or re-consumes every new order and can hit an in-flight SFC at its next operation. It is
    change-controlled - a new version, not an in-place edit; a draft is the only freely editable state.
14. **SFC overall status and operation status are different.** An SFC can be Active overall but In Queue / In
    Work / Done at a given operation. "Where is the SFC" needs the operation-level state, not just the SFC
    status - acting on the wrong operation double-consumes or skips a step.
15. **A released order authorizes build and consumption.** A released order with in-process SFCs cannot be
    cleanly cancelled or TECO'd - the SFCs must be scrapped or completed first, each its own posting.
16. **WIP in DM is the source of truth; ERP on-hand lags.** ERP inventory updates only when the confirmation
    posts; treating ERP on-hand as the shop-floor reality over-promises stock still in WIP, on hold, or under NC.
17. **Backflush against short component stock blocks or drives negative.** If the component lacks quantity in
    S/4, the confirmation is rejected or posts negative inventory per config - either the line stalls or ERP
    inventory is wrong.
18. **A quantity SFC can be partially signed off or split.** Completing part of the quantity confirms only that
    portion; a split creates a child SFC and branches genealogy - a mistaken split mis-attributes which units
    carry which component lots.
19. **Serialized vs quantity/batch SFC changes the unit of action.** A serialized SFC is one unit; a quantity
    SFC carries a number, and scrap/complete/split act on a portion. Assuming one when it is the other mis-sizes
    the action.
20. **Rework routes re-consume material.** Routing an SFC to a rework/repair operation adds to consumption,
    activity, and genealogy; it does not replace the first pass, so total consumption and cycle time both grow.
21. **The activity log / eDHR audit trail is append-only.** Every Start, sign-off, NC, hold, buyoff, and scrap
    captures who/what/when; a mistake is corrected by a forward transaction, never erased - deleting or
    re-signing a record is itself an audited event.
22. **Automatic data collection / confirmation from machine integration still commits.** A value or completion
    posted from a connected machine (via Plant Connectivity) confirms and backflushes exactly like a manual
    sign-off - equipment-driven actions are not exempt from the gate.
23. **Process orders confirm phases; discrete orders confirm operations.** In process manufacturing the commit
    is a phase completion against the master recipe (with batch management and often a batch-determined
    component); assuming the discrete operation model mis-identifies the confirmation point and the batch effect.
24. **A resource must be available and qualified to run an operation.** Signing off against a down or
    unqualified resource is blocked or, if overridden, confirms production on an uncertified resource - a
    compliance and quality risk.
25. **Concurrent action on one SFC conflicts.** Two operators, or an operator and machine automation, starting
    / signing off / holding the same SFC at once can reject a move or overwrite state; re-read the SFC's current
    operation and status at execute - a stale read acts on the wrong operation or double-confirms.
26. **DM Insights is a read, not execution.** OEE/KPI/analytics dashboards (MII lineage) read the record; do
    not confuse an Insights view with the executable SFC/operation state or act on its aggregated numbers as if
    they were live WIP.
27. **A confirmation can post partially across the ERP legs.** The 261 component goods issue can succeed while
    the 101 finished-goods receipt fails (or the confirmation is still async/uncommitted in ERP) - DM shows the
    SFC advanced while ERP holds an inconsistent mid-state. Re-posting the whole confirmation double-issues the
    components; read what actually posted, then reconcile only the missing leg (`sap-mm`).
28. **DM and ERP order quantity/dates can drift.** If the ERP order quantity is cut or dates change but DM still
    shows the original, building or backflushing against the stale DM quantity over-produces or over-consumes,
    and the confirmation can fail against the changed ERP order. Re-sync and re-read the order on both sides at
    execute.

(Deep detail: `references/sfc-routing-and-confirmation.md`, `references/nc-holds-buyoff-and-genealogy.md`.)

## Edge states & special cases
Each breaks naive "the operation passed, so the quantity is good and available" logic - key rule inline, full
behavior in the references.
- **SFC split / merge & genealogy branching** - a split makes a child SFC with inherited history; a merge joins
  SFCs. Quantity and as-built both change. Detail in `references/sfc-routing-and-confirmation.md`.
- **Serialized vs quantity / batch SFC** - a serialized SFC is one unit; a quantity SFC carries a number and can
  be partially completed or split. Process batches are batch-managed and carry a determined batch.
- **Process orders & phases (process industry)** - a process order runs phases against a master recipe with
  batch management; the confirmation commits a phase and a batch, not a discrete operation. Detail in
  `references/sfc-routing-and-confirmation.md`.
- **Rework / repair routes** - an SFC leaves the main routing to a rework operation and re-enters; re-consumption
  and re-inspection add to the record rather than replacing it.
- **Buyoff & e-signature (regulated / eDHR)** - a required, attributed sign-off gates operation completion;
  signing is a hard gate. Detail in `references/nc-holds-buyoff-and-genealogy.md`.
- **Data collection & limits (auto-hold)** - an out-of-limit parameter can auto-hold the SFC or block sign-off;
  forcing past it or editing to pass is a data-integrity breach.
- **Machine integration / Plant Connectivity** - connected equipment drives data collection, Start, and sign-off
  automatically; automated transactions confirm and backflush exactly like manual ones.
- **Cross-plant / multi-site** - an SFC/order at another plant is governed by that plant's released production
  process and confirms to that plant's ERP org. Processing against the wrong plant's process re-routes and
  re-consumes against **that plant's BOM** and posts the confirmation (261/101) to **that plant's ERP org** -
  corrupting both the genealogy and the financial postings. Validate the version and plant before acting.
- **The S/4 confirmation hand-off & DM Insights** - the confirmation is the ERP wire (activity + 261 + 101);
  DM Insights is the read-only analytics view. Detail in `references/sfc-routing-and-confirmation.md`.

## Recovery patterns (can it be undone, and what cannot)

| Situation | Recovery path |
|---|---|
| An SFC is Started at an operation but must back out (not signed off) | cancel / undo the Start - reversible, since it posted no confirmation and consumed nothing |
| An operation was signed off with the wrong backflush, SFC still there | there is no clean DM undo - reversing the material/financial effect is an ERP-side confirmation cancellation (`sap-mm`, a counter 261). Prefer a forward correction (NC + disassembly/assembly); a confirmation cancel is valid only if no later operation advanced and the re-credited components were not re-consumed |
| A sign-off was reversed in ERP but a later operation already advanced | the later operation does not un-sign-off; correct forward (rework or NC), do not expect a clean rollback across DM and ERP |
| A data-collection value was recorded wrong, before sign-off | re-record it - a correctable draft while the operation is unsigned; after sign-off/e-sign it is a controlled record and needs a corrective transaction |
| An SFC is auto-held on an out-of-limit value | resolve the reason (re-measure, or raise and disposition an NC), then release the hold; do not lift the hold to move faster |
| An NC was dispositioned use-as-is / rework | recoverable forward: rework re-processes; use-as-is is a decision on record, revisited only forward |
| An NC was dispositioned scrap or return | not reversible - scrap destroyed the stock and value; return reversed the receipt and re-opened commitment |
| An SFC was scrapped in error | un-scrap only if still allowed (usually pre-order-close) and it may not restore genealogy or operation position; otherwise correct with a new build |
| A buyoff / e-signature was applied | cannot be un-signed; a correcting record/signature is appended and the original stays - handle as a deviation, not an edit |
| A released production process was edited and SFCs moved on it | you cannot un-apply it; create a corrected version going forward - orders/SFCs already run carry the version they executed on. For an SFC currently at an operation the new version changed or removed (a DC/buyoff added, a BOM component swapped, an operation deleted), hold it, verify its current operation still exists in the new version, and NC/disposition any that cannot proceed |
| An SFC completed but the ERP goods-receipt/confirmation failed | the SFC is Done on the DM side; do not re-complete or blindly reverse. First **read the confirmation/order status in ERP, compare it against the DM SFC state, and identify which legs (activity, 261, 101) posted**. Hold the finished SFC, resolve the ERP-side reason (closed period, order TECO, missing components, account assignment - `sap-mm`), then re-trigger the confirmation. If the ERP posting period is closed and cannot be reopened, resolution may need a manual goods receipt in S/4 after period handling (`sap-mm`), not just a DM re-trigger. Reversing the completion is a destructive last resort |
| The confirmation was rejected because a backflushed component is short in ERP/EWM | do not override or force the sign-off - stage/pick the component in ERP/EWM (`sap-ewm`) so the stock is pickable, then re-trigger the confirmation; forcing it drives negative inventory or leaves the backflush wrong |
| A confirmation posted partially - the 261 goods issue went through but the 101 goods receipt failed (or the confirmation is still async/uncommitted in ERP while DM shows the SFC advanced) | do not re-post the whole confirmation (it would double-issue the components). Read what actually posted in ERP first, hold the SFC, and reconcile only the missing leg - re-trigger the failed 101 (or let the async confirmation settle), correcting the specific posting on the ERP side (`sap-mm`), not the whole sign-off. Treat the mid-state as authoritative until reconciled, not as a clean success or a clean failure |
| The DM order and the ERP order disagree (one closed / TECO'd, one active) | do not act on the stale side - reconcile order status first. Completing or scrapping against an ERP-closed order can strand WIP or fail the confirmation; a released DM order whose ERP order was cancelled should be held, not built. Re-read both at execute |
| A split or merge was wrong | reverse only as a **narrow exception** and only after verifying the child/merged SFC has had no downstream processing - this is not general reversibility; once it moves, the genealogy branch stands and needs a correcting transaction |
| A sign-off was rejected by a concurrent action (another operator or a machine acted first) | re-read the SFC's current operation and status, resolve against the actual current state, then re-compose the sign-off - do not blindly retry the stale move |
| An SFC was processed against the wrong plant's production process after a transfer | it is now governed by the receiving plant's released version and ERP org; do not sign off against it - hold, correct the site/version assignment, and verify genealogy crossed intact before resuming |

Reversal is almost always a **new transaction**, not an undo: the original sign-off, its ERP cancellation, the
disposition, and every buyoff/signature stay in the append-only audit trail. What is truly gone is any quantity
already scrapped, returned, consumed, or received, and any genealogy already built.

## Guardrails
Pre-flight before any write (walk it, do not skip under pressure):
1. Read the **SFC overall status + current operation-level state** (In Queue / In Work / Done at op).
2. Read **holds + open NCs** on the SFC - a hold or open NC means stop.
3. Read **component availability** as pickable, staged stock in the system that owns it (ERP, or
   EWM/`sap-ewm` where the warehouse stages) - available in DM but unstaged in the warehouse still
   fails or drives negative the backflush.
4. Read **buyoff / required data collection** status for the operation - a missing one blocks sign-off.
5. Read **order status on both the DM and ERP side** (they can disagree - TECO, cancel, quantity drift).
6. Pin the action's identifiers: the SFC, the operation (and phase/batch on a process order), and - where
   required - the NC/hold reason code and the buyoff/signature's meaning.
7. **Re-read at execute** - a machine or another operator may have moved, held, or consumed since you read.
- Treat a sign-off as a material + financial posting: know the operation BOM and whether it backflushes before
  you complete, and size a scrap / NC-scrap / confirmation reversal - each is a loss or an ERP commitment change,
  not a correction.
- Never force a sign-off past an out-of-limit value or a missing buyoff, edit a value to pass, lift a hold,
  override resource qualification, or make a skip / out-of-sequence move to go faster; a hold or open NC means stop.
- In a regulated/eDHR line, a buyoff / electronic signature is a hard gate - the operation cannot complete
  without it; confirm the record is clean first.
- Genealogy / as-built is permanent and scopes recalls - verify the component lots/serials before assemble /
  consume / split / merge; a wrong association mis-scopes a future recall and cannot be cleanly rewritten.
- The confirmation is the ERP wire - do not reverse it from DM. Cancelling a confirmation is an ERP-side
  destructive act (`sap-mm`); reconcile DM and ERP order status after any cross-system change.
- For anything in the destructive row (scrap, NC scrap/return, confirmation cancel, hold/qualification/limit/
  buyoff override, out-of-sequence move, released-production-process change, merge, order close with WIP):
  named approver, re-read, and log the reason - and for an NC use-as-is/scrap in a regulated line the approver
  must hold **Material Review Board (MRB)** authority, not a generic sign-off.

## References (load on demand)
- `references/sfc-routing-and-confirmation.md` - the SFC lifecycle and status model, the operation/routing
  state machine, Start vs Sign-off, backflush and the S/4HANA confirmation hand-off (activity + 261 goods issue
  + 101 goods receipt), auto vs explicit component consumption, SFC split/merge and genealogy branching,
  serialized vs quantity/batch SFC, process orders and phases, the production-process version model, and order
  download / re-sync with ERP.
- `references/nc-holds-buyoff-and-genealogy.md` - nonconformance and disposition paths, holds and hold codes,
  data collection and limits, buyoff and electronic signatures / eDHR, as-built genealogy and recall scoping,
  work instructions, machine integration via Plant Connectivity, and DM Insights (the read).
