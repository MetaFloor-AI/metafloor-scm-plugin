---
name: sap-pm
description: "SAP Plant Maintenance (PM / EAM inside SAP S/4HANA or ECC) - safe operation of maintenance execution across technical objects (functional locations, equipment), maintenance notifications (malfunction M2, request M1, activity M3), maintenance and work orders (order types PM01-PM04; status CRTD -> REL -> TECO -> CLSD), operations and components (stock reservations, non-stock purchase requisitions), time confirmations, goods issue to the order (261), measuring points and counters, task lists, PRTs, maintenance plans, and settlement. Use when the maintenance system is SAP PM and the work touches a PM/work order, releasing or TECO-ing or settling an order, a maintenance notification, issuing or reserving a spare, a confirmation, a functional location or equipment, a counter reading, a maintenance plan schedule, or the user mentions IW21/IW31/IW32/IW41/IW42/IW45, IL01/IE01, IP10/IP30, KO88, order type PM01-PM04, CRTD, REL, TECO, CLSD, movement 261, or a settlement rule."
---

# SAP PM (Plant Maintenance / EAM) - operating it safely

SAP Plant Maintenance is the EAM module **inside** SAP (S/4HANA on Fiori/GUI, or ECC with SAP GUI + BAPIs).
It is the system of record for technical objects, their maintenance history, and the work done on them, and
it is wired straight into the rest of SAP: a component goods issue moves **MM** stock and value, an external
operation raises an **MM** purchase requisition, and every order settles cost into **FI/CO**. Two facts make
it dangerous. First, the **maintenance order is a governed status network and a cost collector** - releasing
it opens goods issue, confirmation, and procurement; technically completing it closes reservations and open
requisitions; settling it posts real cost; closing it locks the record. Second, **a component issue and a
time confirmation each post inventory and cost at once**, so a wrong issue mischarges the wrong asset and
starves another order of a scarce spare. This skill gives the judgment to classify each action so the harness
can gate it, plus the edge states and recovery paths that decide whether a mistake is fixable.

## Contents
- When this applies / when NOT
- Object & state model
- Vocabulary that bites
- Operations: read / write / destructive matrix
- Gotchas that bite (the causal chains)
- Edge states & special cases
- Freshness & reconciliation
- Recovery patterns
- Guardrails
- References

## When this applies / when NOT
Maintenance / asset system is SAP PM (functional locations, equipment, maintenance notifications and orders,
order types PM01-PM04, IW31/IW32, IP30, measuring points). When NOT:
- IBM Maximo (MAS Manage / classic EAM; WAPPR/APPR status flow, storerooms) -> `ibm-maximo`.
- Infor EAM (formerly Datastream) -> `infor-eam`.
- ERP inventory **valuation**, movement-type mechanics, GR/IR, stock statuses, and the MM posting period the
  goods issue lands in -> `sap-mm` (PM consumes MM stock and raises MM requisitions, but MM owns the
  inventory ledger, not PM).
- The **FI/CO** ledger, cost-center accounting, asset accounting, and the finance period close that settlement
  posts into -> `sap-fi`.
- Calibration **inspection lots** and the quality result recording a calibration order triggers -> `sap-qm`.
- Warehouse execution (bins, tasks, waves, HUs) -> `sap-ewm`.

## Object & state model (reason about state, not nouns)
- **Functional location (FL)** - the *place* in the plant hierarchy (a system, a position), stable regardless of
  what sits in it. Created/changed/displayed via IL01/IL02/IL03. History and cost written against the FL roll up
  the structure.
- **Equipment (EQ)** - the *individual serialized object* that is **installed at** a functional location (and can
  be dismantled and reinstalled elsewhere). IE01/IE02/IE03. Equipment can be linked to a material + serial number
  (a serialized material master), so it lives in two worlds at once (see edge states). History follows the unit.
- **Maintenance BOM** - the spare-parts / assembly list for a technical object (IB01/IB11); proposes components
  onto an order. Editing it does not change orders already built.
- **Maintenance notification** - the *report / request* side (no cost, no execution). Types **M1** (maintenance
  request), **M2** (malfunction report, captures breakdown start/end), **M3** (activity report). IW21/IW22/IW23,
  lists IW28/IW29. Status: **OSNO** (outstanding) -> **NOPR** (in process) -> **NOCO** (completed). A notification
  can carry items (object part / damage / cause) and can be linked to an order.
- **Maintenance / work order** - the *execution + cost* object. Order types **PM01** (default corrective),
  **PM02** (often planned / project-related), **PM03** (often plan-generated / preventive), **PM04**
  (refurbishment of a rotable) - the exact meaning is config, PM01-PM04 are the SAP defaults. IW31 create, IW32
  change, IW33 display, lists IW38/IW39. System status network: **CRTD** (created) -> **REL** (released) ->
  **PCNF/CNF** (partly/fully confirmed) -> **TECO** (technically complete) -> **CLSD** (business complete,
  closed). Plus **NMAT** (missing material), **SETC** (settlement **rule** created - a rule exists, often
  auto-generated; it does **not** mean cost has settled), **DLFL** (deletion flag). Confirmation is not
  mandatory: an order with no confirmations can be TECO'd straight from **REL** - do not wait for a confirmation
  that will never come. Detail in `references/orders-and-status.md`.
- **Operation** - a step on the order, each with a work center, an **activity type** (its cost rate), planned
  work, and a **control key** that marks it internal (labor) or **externally processed** (a purchased service
  that raises a PR).
- **Component** - a material line on the order. A **stock** component creates an **MM reservation** against plant
  stock; a **non-stock** component raises a **purchase requisition**. Consumed by goods issue (movement **261**).
- **Measuring point / counter** - a measuring point records a condition; a **counter** accumulates (operating
  hours, mileage). Readings are **measurement documents** (IK11/IK13) and drive counter-based maintenance plans.
- **PRT (production resource/tool)** - a tool, gauge, test rig, calibration standard, or controlled document an
  operation needs. Assigned to operations; it has its own availability and can carry a usage cost, so it is a
  scheduled shared resource, not a free note.
- **Maintenance plan** - the scheduling object (single-cycle, strategy, or multiple-counter) that generates due
  orders/notifications via deadline monitoring (IP10 single, **IP30** mass). Detail in `references/notifications-and-planning.md`.
- **Settlement rule** - where the order's collected cost goes (cost center / WBS / order / asset). Settlement is
  KO88 (single) / KO8G (collective). Detail in `references/settlement-and-refurbishment.md`.

## Vocabulary that bites
(Each term maps to its hazard; the full causal chain is in Gotchas below.)
- **Functional location vs equipment** - the place vs the serialized object installed at it. A notification/order
  written against the FL and one written against the specific equipment book history to different objects.
- **Notification vs order** - the notification is the report (no cost, no execution); the order is the cost +
  execution object. Completing the notification (NOCO) is not doing or costing the work.
- **Release (REL)** - the gate that lets the order do anything real: print shop paper, issue components, confirm,
  and turn external operations / non-stock components into live purchase requisitions. Not a checkbox.
- **TECO (technical completion)** - closes open reservations and open PRs, drops capacity requirements, and sets
  the completion date - but does **not** close cost (costs still post). Reversible ("put in process"), but the
  closed reservations do not simply return.
- **CLSD / business completion** - the cost lock, set after settlement. No further postings. Terminal.
- **System status vs user status** - system statuses (CRTD/REL/TECO...) are set by events; a customer-defined
  **user status** can *forbid* release, goods issue, confirmation, or settlement even when the system status
  allows it. Reading only the system status misses a blocking user status.
- **Final confirmation** - a confirmation flagged "final" sets CNF and clears the operation's remaining planned
  work and open capacity. A partial leaves PCNF. "Final" too early closes the operation.
- **Reservation** - a stock component reserves MM plant stock and reduces MRP/ATP availability **before** any
  goods issue. Reserved is not issued, but it is already committed against the pool.
- **Non-stock component / external operation** - raises a **purchase requisition** at save/release; that PR
  routes into MM procurement and commits spend once converted and released. Not a planning note.
- **Movement 261 / 262** - these are MM **movement types**, not transactions: 261 is goods issue of a component
  **to the order** (MM stock down + order cost up), 262 reverses it. The issue is entered via MIGO or MB1A (or
  picked with MB26); backflush on confirmation posts 261 automatically. Know the movement type to read what a
  posting actually did.
- **Settlement rule / receiver** - the order is a cost collector; the rule says where cost lands. A missing or
  wrong rule strands or misposts cost.
- **Refurbishment order (PM04)** - repairs a rotable and settles to **material value**, not a cost center; it
  revalues the part back into stock.
- **Counter overflow** - a counter reading below the previous is read as an overflow/reversal; it drives plans,
  so a wrong reading shifts the schedule or trips a spurious call.
- **Task list** - reusable operations copied onto the order at creation; editing it later does not touch existing orders.

## Operations: read / write / destructive
Classify every operation family by what it does to state. Kinds of action, not tool or API names.

| Class | SAP PM operation families | Gate | Why |
|---|---|---|---|
| **Read** | display / list technical objects (IL03/IE03), BOM (IB03), notifications (IW23/IW28/IW29), orders and their operations / components / costs / status (IW33/IW38/IW39), confirmations (IW47/IW48), measurement documents (IK13), maintenance plan and schedule (IP03/IP24), component stock / ATP, settlement and cost reports | always pass | no state change; read order status (system **and** user), reservations, and component availability before every write, re-read at execute |
| **Write (reversible)** | create / change a **notification** and its status (IW21/IW22, OSNO -> NOPR -> NOCO) - it posts no cost and reserves nothing, but completing it (NOCO) does not do or cost the work; create / change an order while **CRTD**, before release - add or edit operations, components, planned work; create / change a maintenance plan, task list, or maintenance BOM before it is scheduled or copied; assign / change PRTs on operations before release; create / change the settlement rule **before any settlement run has executed** (changing it after a periodic settlement redirects where the remaining cost lands, which is committing); master-data edits to a technical object (IL02/IE02) that do **not** install or dismantle | gate one at a time | uncommitted planning; nothing reserved, issued, procured, or posted yet |
| **Write (committing)** | **release an order (CRTD -> REL)** = opens goods issue / confirm / procure and makes reservations and PRs live; **goods issue of a stock component (261)** = MM stock down + order cost up; **time confirmation (IW41/IW42)** = actual labor cost + optional component backflush + operation status; **the PR from a non-stock component or external operation** = committed spend to a vendor (then GR / invoice run through MM); **schedule / generate a maintenance plan (IP10 / IP30)** = creates real due orders/notifications with reservations and potential spend; **enter a measurement / counter reading** = drives plans and condition maintenance; **install / dismantle equipment** at a functional location = moves where cost and history accrue and can change which plans apply (serialized-material equipment also moves as MM stock - see edge states); **TECO** = closes open reservations and PRs and drops capacity (reversible, but not a clean undo) | gate + human approve | binds money, physical stock, availability, or the maintenance schedule; each is a costed or demand-creating event |
| **Destructive / irreversible** | **settle the order (KO88 / KO8G)** = posts collected cost to the receiver - committing while the period is open (reversible with a counter-posting that leaves a trail), but **destructive once the period closes** (no clean reversal); **business completion CLSD** = the lock, terminal, bars further postings; **reverse a confirmation (IW45)** = counter-document, permanent trail; **reverse a goods issue (262)** = counter-document, cannot restore a consumed part; **refurbishment settlement / revaluation of a rotable** = changes material value; **post into a closed CO/FI or MM period** (blocked or mis-dated); **set a deletion flag / archive an order or technical object**; **deactivate / scrap equipment**; **override a blocking user status** to force a transaction | hard gate + named approver + re-read | posts real cost / revalues stock, or crosses a point of no clean return |

**Reclassification rule (read this):** an order is only cleanly reversible while it is **CRTD**. Once **REL**,
its stock reservations are live, its PRs are firm, and it can carry confirmations and goods issues, so an edit
that changes components, operations, or scope - and equally the goods issue, confirmation, or settlement itself
- is a committing (or destructive) act, not a benign edit. Treat any change past REL as committing. Likewise, a
maintenance plan, strategy, or task list is reversible only **before** it has generated call objects or been
copied onto an order; editing one with **live calls** already out is high-blast (it reshapes every future call
across every assigned object, gotcha 17) - treat it as committing and re-read the existing calls.

(The status-by-status "can I do X in status Y?" decision table lives in `references/orders-and-status.md` -
consult it when unsure whether a write is allowed in the order's current status.)

Universal rules to teach: read the order's **system and user status**, its reservations, and the component's
plant availability before every write, and **re-read availability at goods issue** because stock drifts
(another order's reservation, a concurrent issue, an IP30 run). A blocking user status, a missing-material
(NMAT) status, or a hold means **stop**. Never force or override a status to skip the reservation / cost logic
a transition runs. Never split a service PR or an order to slip under a release or approval threshold - it is
the same act with extra steps and it is auditable. A closed CO/FI or MM period is a wall.

## Gotchas that bite (the causal chains)
Each is action -> hidden effect -> downstream consequence. The normative rule lives here; the vocabulary list
above only names the term.
1. **Release (REL) is the gate, not a flag.** Releasing an order lets the shop paper print, permits goods issue
   of components (261), permits confirmations, and turns non-stock components and externally-processed operations
   into **live purchase requisitions** - so parts commitment and spend can start at release, before any physical work.
2. **A notification is not the order.** Completing a notification (NOCO) records that the report is handled; it
   posts no cost and confirms no work. The cost and execution live on the order, so TECO the order, not just NOCO
   the notification, or the cost side stays open - and closing the order does not auto-complete a linked notification.
3. **TECO closes open reservations and open purchase requisitions and drops capacity.** Technically completing an
   order deletes the still-open reservation quantity and open PRs for its components and removes its capacity load,
   so a part you still needed is no longer reserved and MRP no longer sees the demand. TECO is reversible ("put in
   process") but the closed reservations do not simply reappear as they were - re-check components after any reset.
4. **TECO is not the cost lock; CLSD is.** Costs still post to a TECO'd order (a late external-service invoice,
   the settlement itself). TECO closes the open **purchase requisition**, but a **PO already converted** from it
   stays open - the vendor can still deliver and invoice against that PO after TECO, posting more cost to the
   order. Only **business completion (CLSD)**, after settlement, bars further postings, and CLSD is terminal. Do
   not treat TECO as "done and closed".
5. **A component goods issue (261) is an inventory and a cost event.** It deducts MM plant unrestricted stock,
   reduces ATP for everyone, and charges the order (and thus its settlement receiver). Issuing to the wrong order
   mischarges the wrong asset's cost and cannot be un-issued, only reversed with 262.
6. **A reservation reduces availability before any goods issue.** A stock component on a released order reserves
   MM plant stock; MRP/ATP see it as committed. Reserving the last units of a scarce spare starves another order,
   often a higher-priority breakdown, even though nothing has physically moved yet.
7. **A non-stock component or an external operation raises a purchase requisition.** At order save/release the
   order generates a PR for the material or the external service; that PR routes into MM procurement and commits
   spend once converted to a PO and released. It is not a planning note - treat it as committing.
8. **A time confirmation posts actual cost and can backflush components.** IW41/IW42 posts labor at the activity
   type's rate against the work center's cost center, sets the operation status (PCNF/CNF), and if backflush is
   set it automatically issues the operation's components (261). A wrong confirmation misposts labor and silently
   consumes stock. Labor also arrives via **CATS** (Cross-Application Time Sheet) in many shops - a CATS transfer
   confirms the operation the same way, so time entered in CATS is a committing confirmation, not a timesheet draft.
9. **A final confirmation clears the remaining planned work and open capacity.** Flagging a confirmation "final"
   sets CNF and zeroes the operation's open requirements. Confirming final too early closes the operation and
   drops the rest of the planned work from capacity and cost expectations.
10. **Reversing a confirmation (IW45) is a counter-document, not an undo.** It reverses the labor posting and any
    automatic goods movements, but both the original and the reversal stay in history, and a part physically
    consumed by the work cannot be un-consumed.
11. **Settlement moves the order's collected cost to a receiver.** The order is a cost collector; KO88/KO8G posts
    the accumulated labor + material + service cost to the settlement receiver (cost center / WBS / asset). SAP
    often **auto-generates** the settlement rule from the order-type config, and its default receiver can be wrong
    for the specific order - verify the rule before settling. Settlement is not one-and-done: **periodic** (partial)
    settlement can run each period before TECO, and a **final** settlement completes it after, so one settlement
    run does not mean cost is locked. A wrong or missing rule strands cost on the order or posts it to the wrong
    receiver; reversing a settlement is a period-bound CO reversal, not a free undo.
12. **A refurbishment order (PM04) settles to material value, not a cost center.** It takes a defective rotable
    from stock (often at a lower value), collects the repair cost, and on receipt revalues the repaired part back
    into stock. Treating it like a normal PM01 (settle to cost center) mis-values the rotable and the inventory.
13. **A closed period is a wall for every costed PM action.** A goods issue, a confirmation, a settlement, or a
    late service invoice must land in an open CO/FI (and MM) period; a closed period blocks the posting or
    mis-dates it, which can block a settlement or a confirmation outright. Reopening a period is a finance decision,
    not a PM workaround.
14. **A blocking user status overrides the system status.** A customer-defined user status can forbid release,
    goods issue, confirmation, or settlement even when the system status (CRTD/REL) would allow it. Reading only
    "REL" and acting misses a user status set to hold the order. Check both before any write.
15. **Installing or dismantling equipment moves where history and cost accrue.** Equipment installed at a
    functional location books its history and cost to that FL; dismantling and reinstalling elsewhere changes the
    reference and can change which maintenance plans apply. A notification/order on the wrong object (FL vs the
    specific equipment) records history against the wrong asset.
16. **A counter reading drives counter-based plans and condition maintenance.** A measurement document advances
    the counter and can generate the next due call; a reading below the previous is read as an overflow/reversal,
    and a wrong reading shifts the whole counter-based schedule or trips a spurious call.
17. **Scheduling a maintenance plan (IP30) generates real due orders/notifications.** Deadline monitoring (the
    IP30 mass run) creates maintenance call objects - actual orders or notifications with reservations and potential
    spend. Editing the plan, its cycle, or its maintenance strategy shifts every future call across the fleet.
18. **A task list is copied onto the order at creation.** The order takes the task list's operations at the moment
    it is created (or the plan generates it); editing the task list afterward does not change orders already open -
    the fix must be made on the order itself.
19. **The material availability check gates, but it can be overridden.** An order can carry a missing-material
    (NMAT) status; releasing or confirming despite it commits work that will stall for parts, and forcing past the
    check promises a job the plant cannot supply.
20. **An order collects cost even without a technical object.** An order can reference a functional location, a
    piece of equipment, or neither (a general order); cost still collects and must settle somewhere. A missing
    technical-object reference loses the asset-level maintenance history and cost rollup.
21. **A sub-order rolls its cost to the superior order.** A superior order with sub-orders cannot be fully settled
    or closed until the sub-orders are handled; cost charged to the wrong level distorts the per-asset rollup.
22. **Breakdown data on a malfunction notification (M2) feeds reliability.** The malfunction start/end and
    breakdown indicator drive MTBF / MTTR and downtime analysis, and the **catalog codes** (object part / damage /
    cause) recorded on the notification feed failure analysis; wrong or missing times or codes corrupt the
    reliability and failure history that shapes the future preventive strategy.
23. **A PRT is a scheduled, shared resource, not a free note.** A calibration standard, test rig, or controlled
    document attached to an operation has its own availability and can carry usage cost; double-booking a PRT
    across overlapping orders stalls one of them, and using an out-of-calibration test PRT can invalidate the work.

## Edge states & special cases
Each breaks naive "raise an order, issue parts, confirm, close" logic. Key rule inline; deep mechanics in the references.
- **Refurbishment (PM04)** - rotable in from stock, repair cost collected, part revalued back into stock at
  settlement; settles to material value, not a cost center. See `references/settlement-and-refurbishment.md`.
- **Equipment install/dismantle and serialized-material equipment** - equipment linked to a material + serial number
  lives as both an EQ record and MM stock; installing/dismantling moves where cost and history accrue. See `references/orders-and-status.md`.
- **User status hold** - a user status set to "forbid" blocks a transaction the system status would permit; always
  read the user status, not just CRTD/REL.
- **External operations / non-stock components** - raise MM purchase requisitions; the vendor spend, GR, and
  invoice run through MM procurement, so a release-strategy threshold and a closed MM period both apply -> `sap-mm`.
- **Counter-based vs time-based plans** - a maintenance strategy carries packages (e.g. monthly / quarterly / annual
  cycles); a counter-based and a time-based plan on the same object can both come due and generate overlapping calls.
  See `references/notifications-and-planning.md`.
- **Calibration orders** - a calibration order links PM to QM and generates a **QM inspection lot**; the result
  recording and usage decision live in QM -> `sap-qm`.
- **Multi-plant / maintenance planning plant** - a technical object belongs to a maintenance planning plant; stock,
  work centers, and the settlement receiver are plant-scoped, so a read must not net availability or cost across plants.

## Freshness & reconciliation
Component availability and order cost are moving targets. Between the read that planned a goods issue and the
issue itself, another order's reservation, a concurrent issue, a GR, or an IP30 run can change plant
availability, so **re-read availability at goods issue**, not just at plan. The concurrent actor is often SAP
itself: the IP30 deadline-monitoring batch, MRP, and background settlement runs can create orders, fire
reservations, raise PRs, or post cost between your read and your write, so a state you read as stable can move
with no human involved. PM straddles three ledgers - **MM** holds stock and valuation, **FI/CO** holds cost and
settlement, and PM holds the operational order and maintenance history - and order cost lags: confirmations,
goods issues, and external-service invoices post asynchronously, so the order cost you read may not yet include
an in-flight vendor invoice. Do not settle assuming cost is final until the open PRs / POs for the order are
cleared. When PM and MM (or a mobile/CMMS confirmation app) disagree, the gap is almost always in-flight - a
goods issue, a confirmation, or an invoice not yet posted - so treat a delta as a transaction to reconcile, not
a number to force-match, and never adjust one side merely to equal the other.

## Recovery patterns (can it be undone, and what cannot)
A reversal (IW45, 262) is the **sanctioned SAP correction path**, not something to refuse - it posts a
counter-document and leaves both entries in the trail. Gate it (named approver, re-read), but do not block a
genuine correction; the destructive-tier caution is about the permanent trail and the un-restorable physical
consumption, not a bar on reversing at all.
- **Confirmation** - reverse with **IW45**, a counter-document under the same order/operation; both the confirmation
  and the reversal stay in the cost trail, and a part physically consumed by the work cannot be un-consumed.
- **Component goods issue (261)** - reverse with **262**, which restores MM stock and credits the order; both
  postings remain, and a part already consumed cannot be restored.
- **TECO** - reversible with "put in process", but re-opening does **not** cleanly restore the reservations and PRs
  TECO closed; re-check and re-create component demand as needed.
- **Settlement** - reverse the settlement run, but only within the **open** period; once the CO/FI period is closed
  the settlement stands and a correction is a new posting in the current period.
- **Business completion (CLSD)** - revoking business completion is possible only if there are no open items, and is
  best treated as terminal; the settled cost stays booked either way.
- **Deletion flag (DLFL)** - can be reset before the archiving / reorganization run; after archiving the order is
  gone. Setting DLFL does not delete the order - it cannot be archived while it has open commitments (open
  reservations, PRs, or unsettled cost), so a flagged order stays visible until those clear.
- **Wrong counter reading** - edit or reverse the measurement document, but any maintenance call it already generated
  remains and must be cancelled or worked separately.

## Guardrails
- Read the order's **system and user status**, its reservations, the component's plant availability, and the
  settlement rule before acting; re-read availability at goods issue because stock drifts. Confirm the CO/FI (and
  MM) period is open before any costed action - a goods issue, a confirmation, or a settlement.
- Confirm the acting user's SAP authorization (order type, plant, planner group) actually permits the transaction.
  A human approval does not substitute for the authorization the system itself enforces, and a **user status** set
  to forbid still blocks the act. Two more controls gate independently of user status: an **order release strategy**
  (approval by value / order type, like a PR release) can hold release, and a **digital signature** (common in
  regulated industries) can be required at release, confirmation, or TECO. Check for these before assuming a
  transaction will go through.
- Treat releasing an order as committing: it makes reservations and PRs live and opens goods issue and spend. Treat
  every goods issue, confirmation, PR, and settlement as a costed or demand-creating event.
- Before issuing a scarce spare, check competing reservations and the availability impact; a breakdown order
  outranks a scheduled preventive order for the same part. Never split a service PR or an order to dodge a release
  or approval threshold.
- Do not TECO an order until reservations and open PRs are truly no longer needed (TECO closes them), and do not
  settle until the order's open PRs / POs are cleared and cost is final. Do not CLSD until settled - CLSD is the lock.
- Never force or override the status network or a blocking user status to skip the reservation / cost logic a
  transition runs. For anything in the destructive row: named approver, re-read, and a logged reason.

## References (load on demand)
- `references/orders-and-status.md` - the full PM order status network (CRTD / REL / PCNF / CNF / TECO / CLSD /
  NMAT / SETC / DLFL) and what each event runs (reserve, procure, confirm, settle, lock), system vs user status,
  operations and control keys (internal vs externally-processed), stock vs non-stock components, sub-order rollup,
  and equipment install/dismantle.
- `references/notifications-and-planning.md` - notification types M1 / M2 / M3 and status (OSNO / NOPR / NOCO),
  items / tasks / activities and malfunction / breakdown data; maintenance plans (single-cycle / strategy /
  multiple-counter), maintenance items, task lists, strategies and packages, scheduling and IP30 deadline
  monitoring, and measuring points / counters / measurement documents.
- `references/settlement-and-refurbishment.md` - cost collection on the order, settlement rule and receivers
  (cost center / WBS / asset / order), KO88 / KO8G, period dependence, and the refurbishment (PM04) valuation and
  revaluation flow with its interaction with MM valuation and FI/CO.
