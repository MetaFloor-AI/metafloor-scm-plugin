---
name: ibm-maximo
description: "IBM Maximo (EAM / CMMS) - safe operation of asset management and maintenance in Maximo Application Suite (MAS) Manage or classic Maximo EAM 7.6: assets and locations, work orders and their status flow (WAPPR -> APPR -> INPRG -> COMP -> CLOSE), job plans, preventive maintenance (PM), spare-parts inventory in storerooms (reservations, issues, returns, transfers), purchasing (PR / PO / receipts / invoices), meters and condition monitoring, and service requests / tickets. Use when the maintenance or asset system is IBM Maximo (MAS Manage, Maximo Manage, or Maximo EAM) and the work touches a work order, approving or closing a WO, a job plan or PM schedule, issuing or reserving spare parts, a storeroom balance, a purchase requisition or PO receipt, a meter reading or condition-monitoring alarm, a rotating asset, or the user mentions WAPPR, APPR, INPRG, COMP, CLOSE, a work order status, reorder point, or a service request / ticket."
---

# IBM Maximo (EAM / CMMS) - operating it safely

IBM Maximo is the system of record for physical assets, their maintenance history, and the work done on
them - the modern product is Maximo Application Suite (MAS) with the **Manage** application; the classic
on-prem line is Maximo Asset Management / EAM 7.6. Alongside assets it runs the MRO storeroom (spare-parts
inventory), the purchasing of those parts, preventive-maintenance schedules, and meters. Two facts make it
dangerous. First, a **work order is a governed state machine**, and several transitions are not benign
flags: approving a WO reserves parts and can auto-generate spend, and closing one is a financial and history
**lock** that freezes actuals. Second, an **inventory issue or adjustment writes the storeroom book and a GL
account at the same time**, so a wrong issue mischarges an asset's cost and a wrong count posts a real loss.
This skill gives the judgment to classify each action so the harness can gate it, plus the edge states and
recovery paths that decide whether a mistake is fixable.

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
Maintenance / asset system is IBM Maximo (MAS Manage or classic EAM) and the work is assets, work orders,
PM, MRO inventory, or maintenance purchasing. When NOT:
- SAP Plant Maintenance (PM/EAM inside SAP: order types PM01/PM02, IW31/IW32, functional locations,
  equipment master) -> `sap-pm`.
- Infor EAM (formerly Datastream) -> `infor-eam`.
- ERP inventory **valuation**, movement types, GR/IR, financial period close -> `sap-mm` (Maximo
  MRO can interface to the ERP, but the ERP owns the valuation ledger, not Maximo).
- Warehouse execution (bins, waves, task-directed picking in a DC) -> a WMS skill; Maximo storerooms are MRO
  stores, not a distribution warehouse.

## Object & state model (reason about state, not nouns)
- **Asset** - the physical thing maintained; organized in a parent/child **hierarchy** at a **location**.
  Statuses: OPERATING, ACTIVE, INACTIVE (not usable), DECOMMISSIONED (retired). A **rotating asset** is
  serialized and also exists as an inventory item, so it moves between storeroom and location carrying its
  history (see edge states).
- **Location** - where assets sit; operating locations form systems/hierarchies. Has its own status and a GL
  account that maintenance cost rolls up to.
- **Work Order (WO)** - the central transactional record. Governed status flow:
  **WAPPR** (waiting on approval, draft) -> **APPR** (approved, committed) -> **INPRG** (in progress) ->
  **COMP** (complete, work done) -> **CLOSE** (locked). Side statuses: **WSCH** (waiting to be scheduled),
  **WMATL** (waiting on material), **WPCOND** (waiting on plant condition), **CAN** (cancelled). The flow is
  one-directional at the top: CLOSE is terminal, and each transition runs logic (reserve, post actuals, reset
  the PM), so a status is an action, not a label. A WO also carries a **work type / class** (PM preventive,
  CM corrective, EM emergency, or one spawned from a service request), which drives its approval routing and
  priority - an EM breakdown outranks a scheduled PM for the same scarce part. Details in
  `references/work-order-lifecycle.md`.
- **Job Plan** - a reusable template of tasks, planned labor, materials, services, and tools for a type of
  work. Applied to a WO or a PM. Job plans are **revisioned**, and a WO copies the plan at generation.
- **PM (Preventive Maintenance)** - a schedule that **auto-generates work orders** by time frequency or by
  meter. Carries a job plan. A **Master PM** cascades to many associated PMs.
- **Item / Inventory** - a spare part in the item catalog; its **balance lives per storeroom**, not globally.
  An item can be stocked, non-stocked, direct-issue, or special-order. Balance fields: **current balance**,
  **reserved** (hard), **available** = current - reserved.
- **Storeroom** - the stocking location (bins, balances, its own costing type and GL). Item availability is a
  storeroom-and-site question, never a single global number.
- **PR / PO** - purchase requisition (WAPPR -> APPR) becomes a purchase order (WAPPR -> APPR -> INPRG/sent ->
  RECEIVED -> CLOSE). Receipts increase inventory and post received-not-invoiced; invoices commit AP.
- **Meter** - a reading source on an asset/location: **continuous** (accumulates: hours, odometer),
  **gauge** (a level), or **characteristic** (a coded state). Readings drive meter-based PM due and
  condition-monitoring alarms.
- **Service Request (SR) / Ticket** - the request side (SR, incident, problem). An SR can spawn a WO; the two
  are linked but close independently.

## Vocabulary that bites
(Each term maps to its hazard; the full causal chain is in Gotchas below.)
- **Status flow** - Maximo statuses are governed and each transition runs logic (reservations, actuals, PM
  reset, cost rollup). Forcing or skipping a status bypasses that logic.
- **WAPPR vs APPR** - approving a WO commits it: it hard-reserves the material lines, becomes schedulable, and
  can auto-generate PRs for direct-issue / special-order items. Approval is a committing act, not a checkbox.
- **COMP vs CLOSE** - COMP means the work is done but the WO is still open for labor, material, and cost
  postings. CLOSE **locks** it: actuals freeze, cost rolls to the asset/location/GL, no further transactions.
- **Reservation (soft vs hard)** - a WO material line reserves stock. A **hard** reservation (a stocked line
  at approval, or a manual one) removes the quantity from available for everyone else; a **soft** reservation
  (non-stocked / direct-issue lines, or a pre-approval plan) does not decrement availability and instead
  drives a PR. Reserved is not issued.
- **Current balance vs available balance** - available = current - hard reserved. Current balance overstates
  what is free to issue; another WO's reservation can leave you short even when current "looks" fine.
- **Issue** - issuing a part deducts the storeroom balance **and** charges the WO's GL account. It is an
  inventory + financial event, not a pick note.
- **Reorder point (ROP)** - when available balance drops below ROP, the inventory reorder run auto-generates a
  PR/PO. Issuing scarce stock can silently trip a reorder (spend).
- **Rotating asset** - a serialized part that is both an inventory item and an asset record; issuing it moves
  the physical asset and its maintenance history, it does not just consume a quantity.
- **Direct issue / special order** - a WO material line charged straight to the WO on receipt of a PO, never
  entering storeroom balance. It is not stock available to other WOs.
- **Master PM** - a template PM; editing it cascades to every associated PM and thus to future WO generation.
- **Job plan revision** - a WO holds the revision it was generated from; editing the job plan later does not
  change already-open WOs.
- **Continuous meter / rollover** - a continuous meter accumulates; a reading below the last is read as a
  rollover or a correction, and it drives PM due, so a wrong reading shifts the schedule or trips an alarm.
- **GL account string** - every issue, labor, receipt, and WO defaults a GL account from the asset / location
  / storeroom; a wrong or blank string misposts cost, often to a suspense account.

## Operations: read / write / destructive
Classify every operation family by what it does to state. Kinds of action, not tool or API names.

| Class | Maximo operation families | Gate | Why |
|---|---|---|---|
| **Read** | display / query assets, locations, hierarchy; work-order list and detail; PM schedules and job plans; inventory balances (item availability, storeroom current / available / reserved); PR / PO / receipt / invoice display; meter readings and history; failure history; work log; actuals and cost rollup; KPIs and reports | always pass | no state change; read WO status, reservations, and available balance before every write, re-read at execute |
| **Write (reversible)** | create / edit a WO while in **WAPPR** (draft) - but note a workflow / escalation rule can **auto-approve** certain types (often EM) on save, which immediately commits reservations and any PR, so verify the local routing before assuming creation is safe; add planned labor / materials / services / tasks before approval; create / edit a job plan or a single (non-master) PM definition; create or edit a PR before approval; create a service request; reassign labor or reschedule a WO (no stock or cost moved) | gate one at a time | uncommitted planning; low blast, nothing reserved or posted yet |
| **Write (committing)** | **approve a WO (WAPPR -> APPR)** = hard-reserves stocked material lines + makes schedulable (non-stocked / direct-issue / special-order lines take a soft reservation and drive a PR instead); **hard-reserve** inventory to a WO; **change a WO's priority or work type after APPR** (reshuffles scheduling, can reroute approval); **edit a Master PM** (cascades to every associated PM and reshapes future WO generation across the fleet); **issue** a part from a storeroom (deducts balance + charges WO GL); **report actual labor / tools** (charges cost); **approve a PR / PO** (commits spend to a vendor); **receive** against a PO (increases balance + posts received-not-invoiced); **transfer** stock between storerooms (in-transit); **return a part (RTN)** to a storeroom (a counter-transaction to an issue - it credits the WO and restores balance, it is not a clean reversal, and a consumed part cannot be returned); **generate WOs from a PM**; **enter a meter reading** (drives PM due + alarms); **complete a WO (INPRG -> COMP)** (resets the PM next-due, updates meters/warranty) | gate + human approve | binds money, physical stock, availability, or the maintenance schedule; each is a costed or demand-creating event |
| **Destructive / irreversible** | **CLOSE a WO** (freezes actuals, rolls cost, no further transactions, reopen is not a normal transition); **cancel a WO -> CAN** (releases reservations; config-dependent and typically barred once it has actuals); **inventory adjustment / physical-count reconciliation** (overwrites the book balance + posts a GL variance, no offset); **close a PO** (no further receipts); **approve / match an invoice** (commits AP liability); **decommission / retire an asset**; **delete or void a PM / job plan in use**; **correct or delete a meter reading** that already generated a PM or alarm; **post into a closed financial period** (blocked, or mis-dated); **force / override a status** (skips reservation and actuals logic) | hard gate + named approver + re-read | overwrites the book, posts a real loss / liability, or crosses a point of no clean return |

**Reclassification rule (read this):** editing a WO looks reversible only while it is in **WAPPR**. Once it
is **APPR**, its material lines are hard-reserved and it may carry actuals, so an edit that changes materials,
cost, or scope - and equally a change to **priority** (reshuffles the schedule and can displace breakdown
work) or **work type** (reroutes approval) - is a committing change, not a benign edit. Treat any change past
APPR as committing.

Universal rules to teach: read the WO status, its reservations, and the storeroom **available** balance
before every write, and **re-read available at issue** because balances drift (another issue, a reservation,
a count in flight). A hold, an INACTIVE asset, or a blocked status means **stop**. Never force a status to
skip the logic a transition runs. Never split a purchase or an adjustment to slip under an approval or
reorder threshold - it is the same act with extra steps and it is auditable. Never adjust a Maximo balance
purely to match the ERP; that writes a phantom loss or gain.

## Gotchas that bite (the causal chains)
Each is action -> hidden effect -> downstream consequence. The normative rule lives here; the vocabulary
list above only names the term.
1. **Approving a WO (WAPPR -> APPR) is not a rubber stamp.** It creates **hard reservations** for stocked
   material lines against storeroom balances, makes the WO schedulable, and for non-stocked / direct-issue /
   special-order lines takes a soft reservation and can **auto-generate a PR or PO** - so parts commitment and
   spend can start at approval, before any issue.
2. **CLOSE is a wall.** Closing a WO freezes actuals, rolls cost to the asset / location / GL, and blocks any
   further labor, material, or cost posting. A charge that arrives after close has nowhere to go, and
   reopening is not a normal status transition (it needs a configured re-open path or a new corrective WO).
   Do not close until every actual is in.
3. **Issuing a part deducts the storeroom balance AND charges the WO's GL account.** It is a financial event,
   not a pick note; issuing to the wrong WO mischarges cost to the wrong asset and cannot be un-issued, only
   returned.
4. **Available is not current balance.** available = current - hard reserved. Reading current balance
   overstates what is free; another WO's hard reservation can short you at issue time even when the number
   looked fine at plan.
5. **Issuing scarce stock trips the reorder point.** When available drops below ROP the next reorder run
   auto-generates a PR/PO - a silent spend trigger; and hard-reserving the last units removes them from a
   higher-priority breakdown WO that then cannot get the part.
6. **A rotating asset is both an item and an asset.** Issuing it from a storeroom physically moves the
   serialized asset to the WO / location and its maintenance history travels with the unit; treating it as a
   plain consumable loses the asset linkage and its history.
7. **A meter reading drives PM due and condition-monitoring alarms.** A wrong reading (or one below the last
   on a continuous meter, read as a rollover) can prematurely generate a PM work order or trip / suppress an
   alarm; correcting the reading later leaves the already-generated WO behind.
8. **Completing a WO resets its PM schedule.** COMP on a PM-generated WO recalculates the PM's next due from
   the completion date (or last meter), so completing early or late shifts the whole future schedule for that
   asset.
9. **Editing a Master PM cascades.** A change to a master PM flows to every associated PM and thus to all
   future WO generation - one edit can reschedule maintenance across a fleet.
10. **A job plan is copied onto the WO at generation.** Editing the job plan afterward does **not** update
    already-open WOs; the fix must be applied to the WO itself. The WO holds the plan revision it was born
    from.
11. **Cancelling a WO (-> CAN) is not always allowed and is not free.** A WO with actuals cannot be cleanly
    cancelled; cancelling an approved WO releases its hard reservations back to available, which can surprise
    a picker mid-job and free a part another job then grabs.
12. **An inventory adjustment overwrites the book directly.** A physical-count reconciliation or current-
    balance adjust writes the storeroom balance under a reason code and posts a GL variance with no offsetting
    document - a mistaken count is a real loss or a phantom, corrected only by a further adjustment.
13. **Receiving against a PO is committing.** It increases inventory and posts received-not-invoiced;
    over-receiving or receiving to the wrong storeroom injects stock finance must reconcile. RECEIVED is not
    CLOSE.
14. **An issue return (RTN) is a counter-transaction, not an undo.** It credits the WO and puts stock back,
    but both transactions stay in history and the cost trail shows both; a part physically consumed cannot be
    returned.
15. **Reporting actual labor charges cost at the craft rate.** Reversing it needs a negative / correcting
    labor transaction, and on a closed WO it cannot be posted at all - which is why late labor after CLOSE is
    stranded.
16. **Closing a PO locks it.** No further receipts against a closed PO; a partial delivery received after PO
    close is stranded and needs a new PO or a reopen (if config allows).
17. **A storeroom transfer creates in-transit stock.** The quantity leaves the source storeroom immediately
    but is not available at the destination until received there; counting it at both ends double-counts.
18. **Forcing or skipping a status bypasses the transition logic.** Each status change runs reservations,
    actuals, and rollup; a forced jump (e.g. straight to CLOSE) can leave orphaned reservations or unposted
    costs behind.
19. **Scheduled PM reservations compete with breakdown work.** Approving a batch of PMs at once hard-reserves
    spares that an emergency breakdown WO then cannot get; a breakdown normally outranks a scheduled PM for a
    scarce part.
20. **Failure codes captured at close feed reliability analysis.** Closing a WO without problem / cause /
    remedy codes, or with wrong ones, corrupts the failure history that drives MTBF / MTTR and future PM
    decisions.
21. **Direct-issue and special-order lines never enter storeroom balance.** They are charged straight to the
    WO on receipt; treating them as stock available to other WOs double-counts inventory that was already
    consumed by one job.
22. **The GL account defaults, and a wrong default misposts.** Issues, labor, and receipts inherit a GL
    string from the WO / asset / storeroom; a wrong or blank string posts cost to the wrong asset or to a
    suspense / clearing account.
23. **Costing type sets the issue cost.** Under average / LIFO / FIFO costing each receipt moves the cost, so
    an issue's value depends on receipt timing; under standard cost an off-standard receipt posts a variance.
    "The cost" is ambiguous without the storeroom's costing type.
24. **Work-order hierarchy rolls cost up.** A parent WO with child task WOs cannot close until children are
    complete, and cost charged to the wrong level distorts the rollup for the asset.
25. **An SR and its WO close independently.** Closing the work order does not auto-close the linked service
    request; the requester side can stay open, and vice versa.

## Edge states & special cases
Each breaks naive "issue a quantity, do the work, close it" logic. Key rule inline; deep mechanics in the
references.
- **Rotating assets** - dual identity (inventory item + asset record); issuing / returning moves the
  serialized unit and its history, not just a count. See `references/inventory-and-storerooms.md`.
- **Direct-issue / special-order items** - never touch storeroom balance; charged to the WO on receipt.
  Excluding them from availability reads is correct; counting them as stock is not.
- **Master PM / PM hierarchy** - one master cascades to many; a meter-based PM and a time-based PM on the same
  asset can both come due and generate overlapping WOs. See `references/pm-meters-and-purchasing.md`.
- **Meter rollover** - a continuous meter that wraps (or is re-installed) reads lower than before; the PM
  due-calc must treat it as a rollover, not a reversal, or it never comes due.
- **Work-order hierarchy (parent / task)** - costs roll up; the parent closes only when children complete;
  charge to the correct level. See `references/work-order-lifecycle.md`.
- **Multi-site / multi-org** - Maximo is organization- and site-scoped; an item's balance, its GL, and even
  the WO belong to a site. A cross-site read must not net balances across sites as one pool.
- **In-transit internal transfer** - stock between storerooms is at neither balance until the destination
  receives it; do not promise it at the source or count it at the destination early.
- **Condition monitoring** - a meter reading past an alarm limit generates a WO or an alarm automatically; a
  bad reading manufactures unneeded work or hides a real fault.
- **Closed financial period** - a costed transaction (an issue, a receipt, an adjustment, or the cost rollup
  at WO close) must land in an **open** GL period, in Maximo's own financial periods or the interfaced ERP.
  A closed period blocks the posting, which can block a WO close or a receipt entirely, or mis-date it into
  another open period. Check the period is open before staging any costed action; reopening a period is a
  finance decision, not an agent workaround.
- **Safety plan / lockout-tagout (LOTO)** - a WO can carry a safety plan, hazards, precautions, and LOTO
  procedures that must be satisfied before work starts, and safety or EM (emergency) work types often add
  their own approval gates. Treating a safety-planned or EM WO as a routine CM skips a required gate; respect
  the safety attributes and routing, do not approve or progress past them to save a step.

## Freshness & reconciliation
Storeroom balances and WO reservations are moving targets. Between the read that planned an issue and the
issue itself, another WO's approval, a concurrent issue, a receipt, or a count can change the available
balance, so **re-read available at issue**, not just at plan. The concurrent actor is often Maximo itself:
its workflow / escalation engine, cron tasks, PM generation, and condition-monitoring alarms can change a WO
status, fire a reservation, or create a PR between your read and your write, so a state you read as stable
can move with no human involved. Maximo commonly interfaces to an ERP (SAP,
Oracle) for finance and sometimes for procurement: the ERP holds valuation and AP, Maximo holds the MRO
operational balance and the maintenance history. When the two disagree the gap is almost always in-flight -
an issue, receipt, or adjustment not yet interfaced, or interfaced but not yet posted - so treat a raw
quantity delta as a transaction to reconcile, never as a number to force-match. Integration is asynchronous
and can queue or error: a gap is not a true discrepancy until the sync window has passed, so wait and re-read
before concluding the two disagree. Never adjust the Maximo balance just to make it equal the ERP; that
writes a phantom loss or gain into the maintenance book.

## Recovery patterns (can it be undone, and what cannot)
- **WO CLOSE** - reopening is **not** a standard status transition. If a re-open-closed-WO option is
  configured you can reopen, otherwise the fix is a new corrective WO; the frozen actuals stay in history
  either way.
- **Issue** - reverse with a **return (RTN)**, a counter-transaction under a reason code; both the issue and
  the return remain in the cost trail, and a part already physically consumed cannot be returned.
- **Inventory adjustment / count** - corrected only by a **further adjustment**; the variance already posted
  to the GL. There is no rollback, only an opposite write that also posts.
- **Actual labor** - reversed by a negative / correcting labor transaction; impossible on a closed WO, so
  post labor before CLOSE.
- **WO cancel** - releases hard reservations cleanly, but a WO with actuals cannot be cancelled; use a new WO
  and let the actuals stand.
- **PO close** - reopen only if config allows, otherwise raise a new PO for the remaining receipt; the closed
  PO stays closed.
- **Meter reading** - a wrong reading is edited or deleted, but any PM WO or condition-monitoring alarm it
  already generated remains and must be handled separately (cancel the spurious WO, clear the alarm).
- **PM schedule shift** - if a wrong completion date reset the next-due, correct the PM's last-completion or
  last-meter, but WOs already generated remain and must be cancelled or completed on their own.

## Guardrails
- Read the WO status, its reservations, the storeroom **available** balance, and the target GL account before
  acting; re-read available at issue, because balances drift. Confirm the GL account resolves to a real
  account, not a blank that defaults to a suspense / clearing account, and that the financial period is open
  before staging any costed action.
- Confirm the acting user's Maximo security group and site authorization actually permit the status change or
  transaction. A human approval does not substitute for the privilege the system itself enforces.
- Do not close a WO until all labor, material, and cost are posted. CLOSE is a financial and history lock, not
  a "done" flag, and reopening is not a normal transition.
- Treat approving a WO as committing: it hard-reserves parts and can auto-generate spend. Treat every issue,
  receipt, labor posting, and PO approval as a costed event.
- Before issuing a scarce part, check the reorder impact and competing reservations; a breakdown WO outranks a
  scheduled PM for the same part. Never split a purchase or an adjustment to dodge a threshold.
- Adjust a storeroom balance only against a real physical count, with a reason code and a named approver, and
  never merely to match the ERP.
- Never force or override the governed status flow to skip the reservation and actuals logic. For anything in
  the destructive row: named approver, re-read, and a logged reason.

## References (load on demand)
- `references/work-order-lifecycle.md` - the full WO status flow and what each transition runs (reserve, post
  actuals, PM reset, cost rollup), side statuses (WSCH / WMATL / WPCOND / CAN), WO hierarchy and tasks, and
  the reopen mechanics.
- `references/inventory-and-storerooms.md` - storeroom balances (current / available / reserved),
  reservation types, issue / return / transfer / receipt / adjustment transactions, reorder, costing types,
  and rotating / direct-issue / special-order items with their GL accounts.
- `references/pm-meters-and-purchasing.md` - PM frequency, meter-based PM and Master PM cascade, job-plan
  revisioning, meters (continuous / gauge / characteristic and rollover), condition monitoring, and the
  PR / PO / receipt / invoice flow with its statuses.
