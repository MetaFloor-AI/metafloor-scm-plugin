---
name: infor-eam
description: "Infor EAM (enterprise asset management; ex-Datastream 7i, now HxGN EAM) - operate maintenance and assets safely: the Location/System/Position/Asset equipment hierarchy; work orders whose user status codes map to system statuses (Unfinished, Released, Completed, Closed); PM schedules (fixed vs floating, meter-based) and Routes; spare parts in Stores (reserve, issue, transfer, reorder); purchasing (requisition, PO, receipt); meters and condition monitoring. Use when the maintenance/asset system is Infor EAM / HxGN EAM (MP5) and work touches a work order, releasing/completing/closing a WO, a PM schedule or route, issuing or reserving parts, a store balance, a requisition or PO receipt, a meter reading or condition alarm, an asset installed in a position, or mentions Infor EAM, Datastream, HxGN EAM, work order status, R-Type, or reorder point. Not for SAP PM (sap-pm), IBM Maximo (ibm-maximo), Infor ERP (infor), or ERP valuation (sap-mm)."
---

# Infor EAM (EAM / CMMS) - operating it safely

Infor EAM is the system of record for physical assets, their maintenance history, and the work done on
them. The lineage matters for terminology: it began as **Datastream 7i** (and MP2 / MP5), was Infor EAM for
years, and after Hexagon's acquisition the same product ships as **HxGN EAM** - the objects and screens
are the same, so treat all three names as one system. Alongside the equipment register it runs the MRO
**Stores** (spare-parts inventory), the purchasing of those parts, PM schedules, and meters.

Three facts make it dangerous. First, a **work order is a governed state machine**, and its status is not a
label: each user-defined status code is pinned to a **system status** that runs logic - **releasing** a WO
reserves parts and can auto-raise requisitions, and **closing** one historizes it and locks actuals and cost.
Second, a **part issue or an inventory adjustment writes the store book and a cost account at the same time**,
so a wrong issue mischarges an asset and a wrong count posts a real loss. Third, the **equipment hierarchy has
four levels** (Location > System > Position > Asset) and cost and history roll **up** all of them, so "the
cost of this asset" depends on which level you read and a naive sum double-counts. This skill gives the
judgment to classify each action so the harness can gate it, plus the edge states and recovery paths that
decide whether a mistake is fixable.

## Most dangerous operations (triage first)
Before working the full matrix, recognize the handful that do the most damage:
- **Release a WO** - reserves parts and can auto-raise a requisition; spend and stock commitment start here, not at issue.
- **Issue or adjust a part** - writes the store book and a cost account together; an adjustment posts a real variance with no offsetting document.
- **Close a WO** - historizes and locks actuals and cost; reopening is not a normal transition.
- **Force a status, or a quick-close WO type** - can skip the reserve / complete / close logic and strand late cost.
- **Install / remove or re-point an asset** - moves the unit and re-points all future cost up a different branch of the hierarchy.

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
Maintenance / asset system is Infor EAM or HxGN EAM (any of the Datastream / MP5 / Infor EAM / HxGN lineage)
and the work is assets, work orders, PM, MRO stores inventory, or maintenance purchasing. When NOT:
- SAP Plant Maintenance (PM / EAM inside SAP: order types PM01/PM02, IW31/IW32, functional locations and the
  equipment master, task lists, PM notifications, settlement to a cost object) -> `sap-pm`.
- IBM Maximo (MAS Manage or classic EAM 7.6; WAPPR/APPR/INPRG/COMP/CLOSE, storerooms, job plans) ->
  `ibm-maximo`. Same problem domain, different object and status model - do not carry Maximo's
  status names or "job plan" wording into Infor EAM.
- Infor ERP finance, purchasing-for-goods, AP, and inventory **valuation** in M3 / LN / SyteLine ->
  `infor`. Infor EAM can interface to that ERP; the ERP owns the valuation ledger and AP.
- ERP inventory **valuation**, movement types, GR/IR, financial period close -> `sap-mm`.
- Warehouse execution (bins, waves, task-directed picking in a DC) -> a WMS skill; EAM Stores are MRO
  spares locations, not a distribution warehouse.

## Object & state model (reason about state, not nouns)
- **Equipment** - the register, in a four-level hierarchy: **Location** (site / area, top) > **System**
  (a functional grouping) > **Position** (a functional slot that stays put, e.g. "Pump P-101 seat") >
  **Asset** (the serialized physical unit that is installed into a position). Work and cost booked to an
  asset also roll **up** to its position, system, and location. Equipment carries a status (e.g. installed,
  in store, out of service, disposed). The **Position vs Asset** split is the core Infor EAM idea and the
  main difference from Maximo: the position holds the maintenance program and location; the asset carries its
  own history and can be **removed and re-installed** elsewhere, taking its history with it. Details in
  `references/work-order-and-equipment.md`.
- **Work Order (WO)** - the central transactional record. Status is a **user-defined code** that each site
  configures, but every code is bound to a fixed **system status** that drives the logic. The lifecycle in
  system-status terms: **Unfinished** (draft, editable) -> **Released (R)** (committed and schedulable) ->
  **Completed** (work done, still open for late cost) -> **Closed** (historized, locked). A WO also has a
  **work type / class** (PM preventive, CM corrective, EM emergency, and so on) that drives approval routing
  and priority - an EM breakdown outranks a scheduled PM for the same scarce part. A WO can carry **tasks /
  activities**, planned **trades / labour**, planned **parts**, and **tools**.
- **Standard Work Order** - a reusable template (tasks, trades, parts, tools) that a PM or a user applies; it
  is **copied onto the WO** at generation, so editing the standard later does not change already-open WOs.
  (Infor EAM's analog of a "job plan" - use the Infor term.) A **Maintenance Pattern** sequences several
  standard WOs across PM cycles.
- **PM Schedule** - auto-generates WOs by **time** (calendar) or by **meter**. A calendar schedule is either
  **fixed** (next due from the planned / **last start** date, so it does not slip) or **floating** (next due
  from the **last completion** date, so it slips with actual completion). A schedule can combine calendar and
  meter; whichever comes first triggers. See `references/pm-meters-purchasing.md`.
- **Route** - a single PM / WO that covers **many pieces of equipment** in one pass (an inspection round or
  lubrication loop); it generates child equipment lines / WOs for the route members. Completing the route
  covers the round, not one asset.
- **Part / Store** - a spare part lives in the catalogue; its **balance is per Store** (a stocking location)
  and per **organization**, never one global number. Balance fields: **on-hand**, **reserved**,
  **available** = on-hand - reserved. An item can be a stock part, a **direct / non-stock** part (bought
  straight to a WO), or a **rotating / repairable** part with a tracked condition.
- **Requisition / PO / Receipt** - a **purchase requisition (PR)** (raised by a user or auto-raised by
  reorder) becomes a **purchase order (PO)**, then a **receipt** increases store balance (or charges a WO for
  a direct part) and posts received-not-invoiced. Approving the PO commits spend.
- **Meter** - a reading source on equipment: **continuous** (accumulates: hours, odometer), or a gauge /
  characteristic reading. Readings drive meter-based PM due and **condition monitoring** limits.
- **Work Request / case** - the request side (a reported problem) that can spawn a WO; the two link but close
  independently.

## Vocabulary that bites
(Each term maps to its hazard; the full causal chain is in Gotchas below.)
- **System status (R-Type)** - the WO's user status code is cosmetic; the **system status** it is pinned to
  is what runs the logic (release reserves parts, close historizes). A custom code mapped to the wrong system
  status silently releases or closes. Reason about the system status, never the label.
- **Released vs Unfinished** - releasing a WO (moving it to a status whose system status is **R**) commits it:
  it **reserves** the planned stock parts against store balances, makes it schedulable and printable, and for
  non-stock / direct parts can **auto-raise a requisition**. Release is a committing act, not a checkbox. Some
  sites configure "quick" WOs that are **created directly in Released** - verify the local routing before
  assuming a new WO is a harmless draft.
- **Completed vs Closed** - **Completed** means the work is physically done but the WO is **still open** for
  late labour, parts, and cost. **Closed** historizes it: actuals freeze, cost rolls up the equipment
  hierarchy, and no further transaction is accepted. Close is the lock.
- **Reserved vs available** - available = on-hand - reserved. Reading on-hand and treating it as free
  over-promises; another WO's reservation can short you at issue time even when on-hand "looks" fine.
- **Issue** - issuing a part deducts the store balance **and** charges the WO's cost account. It is an
  inventory + financial event, not a pick note; issuing to the wrong WO mischarges the wrong asset.
- **Reorder point / min-max** - when available falls below the reorder point, an automatic **requisition**
  generates (to the **preferred supplier**, or a **store-to-store transfer** if a preferred store is set).
  Issuing scarce stock can silently trip a reorder (spend).
- **Position vs Asset** - a position is the fixed functional slot; an asset is the serialized unit installed
  in it. **Installing / removing** an asset moves the physical unit and its history between positions - it is
  not just a data edit, and cost booked while installed rolls to that position and up.
- **Fixed vs floating PM** - fixed schedules from the last **start** date (calendar does not slip); floating
  schedules from the last **completion** date (slips with completion). Completing a floating PM early or late
  shifts its whole future schedule.
- **Standard WO revision** - a WO copies the standard WO at generation; editing the standard later does not
  touch open WOs. Fix the WO itself.
- **Continuous meter / rollover** - a continuous meter accumulates; a reading **below** the last is read as a
  rollover (wrap or re-install), not a correction, and it drives PM due, so a wrong reading shifts the
  schedule or trips a condition alarm.
- **Organization scope** - Infor EAM is **organization**-scoped; parts balances, stores, and WOs belong to an
  org. A cross-org read must not net balances into one pool.
- **Cost / GL account default** - every issue, labour posting, and receipt defaults a cost account from the
  equipment / store; a wrong or blank string misposts, often to a suspense account.
- **Failure codes (problem / cause / remedy)** - the dependent three-level coding captured on a corrective WO
  at completion; it feeds MTBF / MTTR and PM decisions, so a missing cause or wrong code corrupts reliability
  analysis. Capture before close (a closed WO cannot take them). Detail in `references/work-order-and-equipment.md`.

## Operations: read / write / destructive
Classify every operation family by what it does to state. Kinds of action, not tool or screen names. The
class sets the **autonomy** the agent may take: **Read** -> act autonomously; **Write (reversible)** ->
propose and act one at a time; **Write (committing)** -> require explicit human confirmation before executing;
**Destructive / irreversible** -> hard stop, named approver, and a re-read before acting. Never execute a
committing or destructive action on your own authority.

| Class | Infor EAM operation families | Gate | Why |
|---|---|---|---|
| **Read** | display / query equipment (location / system / position / asset) and hierarchy; WO list and detail and status; PM schedules, routes, standard WOs; part balances (on-hand / available / reserved) per store; requisition / PO / receipt display; meter readings and history; condition-monitoring points; failure / maintenance history; cost rollup and KPIs | always pass | no state change; read WO status, reservations, and **available** balance before every write, re-read at execute |
| **Write (reversible)** | create / edit a WO while **Unfinished** (draft) - but a workflow rule can create some types (often EM / quick WOs) **directly in Released**, which immediately reserves parts and can raise a requisition, so verify routing first; add planned tasks / trades / parts / tools before release; create / edit a standard WO or a single PM schedule; create a requisition before approval; create a work request; reschedule or reassign labour with no stock or cost moved | gate one at a time | uncommitted planning; low blast, nothing reserved or posted yet |
| **Write (committing)** | **release a WO** (Unfinished -> Released) = reserve stock parts + make schedulable + auto-raise requisitions for non-stock / direct parts; **reserve** parts to a WO; **change a WO's priority or work type after release** (reshuffles scheduling, can reroute approval); **re-point a WO to different equipment** (moves all its cost to the new asset and up a different branch of the hierarchy); **edit a PM schedule / standard WO / route that is in use** (reshapes future WO generation across the fleet); **issue** a part from a store (deducts balance + charges the WO); **book actual labour / tools** (charges cost); **approve a requisition / PO** (commits spend to a supplier); **receive** against a PO (increases balance + posts received-not-invoiced); **transfer** parts store-to-store (in-transit); **return** a part to a store (a counter-transaction to an issue - it credits the WO and restores balance, it is not a clean reversal, and a consumed part cannot be returned); **generate WOs from a PM / route**; **enter a meter reading** (drives PM due + condition alarms); **install / remove an asset** into / from a position (moves the unit and its history); **cancel a WO that has no actuals** (releases its reservations back to available - freed parts can be grabbed by a lower-priority WO before a breakdown WO can reserve them; the WO can be recreated, so gate it but do not hard-stop it); **complete a WO** (Released -> Completed; resets the PM next-due, updates meters / warranty) | gate + human approve | binds money, physical stock, availability, the maintenance schedule, or the asset register; each is a costed or demand-creating event |
| **Destructive / irreversible** | **close a WO** (historizes it: freezes actuals, rolls cost up the hierarchy, no further transaction, reopen is not a normal transition); **cancel a WO that already has actuals** (typically barred; forcing it strands or orphans the posted actuals); **physical inventory / balance adjustment** (overwrites the store book + posts a variance, no offsetting document); **close a PO** (no further receipts); **approve / match a supplier invoice** (commits AP liability - but if AP is interfaced to an ERP, invoice matching happens there, not in EAM, and is out of scope here); **dispose / retire an asset**; **delete or void a PM / standard WO / route in use**; **correct or delete a meter reading** that already generated a PM or alarm; **post into a closed financial period** (blocked or mis-dated); **force a status** to one whose system status skips the reserve / complete / close logic (this includes a quirk of quick-close / auto-close WO types that skip the Completed window) | hard gate + named approver + re-read | overwrites the book, posts a real loss / liability, historizes, or crosses a point of no clean return |

**Reclassification rule (read this):** editing a WO is reversible only while it is **Unfinished**. Once
**Released**, its parts are reserved and it may carry actuals, so an edit to parts, cost, or scope - and
equally a change to **priority** (reshuffles the schedule and can displace breakdown work), **work type**
(reroutes approval), or the **equipment** the WO points at (re-attributes all its cost and rolls it up a
different branch) - is a committing change, not a benign edit. Treat any change past release as committing.

Universal rules to teach: **re-read the target object's status and balances immediately before every
committing or destructive write, not just at plan time** - another agent, a user, or an EAM background job
can release the WO, issue the same part, or move stock between your read and your write. In particular read
the WO status, its reservations, and the store **available** balance before every write, and re-read
available at issue because balances drift (another issue, a reservation, a count in flight). A hold, an out-of-service asset, or a blocked status means **stop**. Never map or force a status
whose system status skips the logic a transition runs. If a site's custom status code cannot be resolved to a
known system status, stop and ask - do not guess whether it releases, completes, or closes. Never split a purchase or an adjustment to slip under
an approval or reorder threshold - it is the same act with extra steps and it is auditable. Never adjust an
EAM balance purely to match the ERP; that writes a phantom loss or gain.

## Gotchas that bite (the causal chains)
Each is action -> hidden effect -> downstream consequence. The normative rule lives here; the vocabulary
list above only names the term.
1. **Releasing a WO is not a rubber stamp.** Moving a WO to a Released-system-status code creates
   **reservations** for its stock parts against store balances, makes it schedulable and printable, and for
   non-stock / direct parts can **auto-raise a requisition** - so parts commitment and spend can start at
   release, before any issue.
2. **Close historizes and is a wall.** Closing a WO freezes actuals, rolls cost up the equipment hierarchy,
   and blocks any further labour, parts, or cost posting. A charge that arrives after close has nowhere to go,
   and reopening is not a normal status transition. Do not close until every actual is in.
3. **The status code is cosmetic; the system status runs the logic.** Two sites can name the same system
   status differently, and a custom code mapped to the wrong system status silently releases or closes.
   Always resolve the system status (R-Type) behind the label before acting on it.
4. **Issuing a part deducts the store balance AND charges the WO's cost account.** It is a financial event,
   not a pick note; issuing to the wrong WO mischarges the wrong asset and cannot be un-issued, only returned.
   Issuing more than on-hand is either hard-blocked or (per config) drives the balance **negative**, which
   distorts availability and reorder logic; check on-hand covers the issue rather than relying on the post to
   stop you.
5. **Available is not on-hand.** available = on-hand - reserved. Reading on-hand overstates what is free;
   another WO's reservation can short you at issue time even when the number looked fine at plan.
6. **Issuing scarce stock trips the reorder point.** When available drops below reorder point an automatic
   requisition generates (to the preferred supplier, or a store-to-store transfer) - a silent spend trigger;
   and reserving the last units removes them from a higher-priority breakdown WO that then cannot get the part.
7. **An asset is not a position.** Installing or removing an asset moves the serialized unit and its history
   between positions; cost and PM belong partly to the position (the slot) and partly to the asset (the unit).
   Booking work to the wrong one, or treating a removed asset as still in place, corrupts both histories.
8. **Cost rolls up four levels, so "asset cost" is ambiguous.** Work booked to an asset also appears at its
   position, system, and location. Summing an asset and its parent as if independent double-counts; read the
   level you actually mean.
9. **A meter reading drives PM due and condition monitoring.** A wrong reading (or one below the last on a
   continuous meter, read as a rollover) can prematurely generate a PM WO or trip / suppress an alarm;
   correcting the reading later leaves the already-generated WO behind.
10. **Completing a floating PM shifts its whole schedule.** A floating PM's next due recalculates from the
    completion date, so completing early or late moves every future occurrence for that equipment. A fixed PM
    schedules from the start date and does not slip - confirm which type before reasoning about the next due.
11. **A standard WO is copied onto the WO at generation.** Editing the standard afterward does **not** update
    already-open WOs; the fix must be applied to the WO itself. A maintenance pattern edit reshapes only
    future cycles.
12. **Editing a PM / route in use cascades to future generation.** A change to a shared PM schedule, standard
    WO, or route flows to every future WO it generates across all its equipment - one edit can reschedule
    maintenance across a fleet or a whole round.
13. **Cancelling a WO is not always allowed and not free.** A WO with actuals cannot be cleanly cancelled;
    cancelling a released WO releases its reservations back to available, which can surprise a picker mid-job
    and free a part another job then grabs.
14. **A balance adjustment overwrites the store book directly.** A physical-inventory or on-hand adjust
    writes the balance under a reason code and posts a variance with no offsetting document - a mistaken count
    is a real loss or a phantom, corrected only by a further adjustment. Never adjust to match the ERP.
15. **Receiving against a PO is committing.** It increases inventory (or charges a WO for a direct part) and
    posts received-not-invoiced; over-receiving or receiving to the wrong store injects stock finance must
    reconcile. Received is not closed.
16. **A part return is a counter-transaction, not an undo.** It credits the WO and puts stock back, but both
    transactions stay in history and the cost trail shows both; a part physically consumed cannot be returned.
17. **A store-to-store transfer creates in-transit stock.** The quantity leaves the source at once but is not
    available at the destination until received there; counting it at both ends double-counts.
18. **Direct / non-stock parts never enter store balance.** They are charged straight to the WO on receipt;
    treating them as stock available to other WOs double-counts inventory already consumed by one job.
19. **A rotating / repairable part carries a condition.** Issuing or returning it moves a tracked unit
    (new / repairable / rebuilt), not a plain quantity; returning a failed unit to a good-stock bin
    overstates serviceable stock.
20. **Booking actual labour charges cost at the trade rate.** Reversing it needs a correcting labour
    transaction, and on a closed WO it cannot be posted at all - which is why late labour after close is
    stranded.
21. **Closing a PO locks it.** No further receipts against a closed PO; a partial delivery received after
    close is stranded and needs a new PO or a reopen if config allows.
22. **A route WO covers many equipment at once.** Completing or closing the route acts on the whole round;
    a fault found on one route member still needs its own corrective WO, and reserving parts for a route
    reserves for every member.
23. **Scheduled PM reservations compete with breakdown work.** Releasing a batch of PMs at once reserves
    spares that an emergency breakdown WO then cannot get; a breakdown normally outranks a scheduled PM for a
    scarce part.
24. **Failure codes captured at completion feed reliability analysis.** Completing a WO without problem /
    cause / remedy codes, or with wrong ones, corrupts the failure history that drives MTBF / MTTR and future
    PM decisions.
25. **The cost account defaults, and a wrong default misposts.** Issues, labour, and receipts inherit a cost
    string from the equipment / store; a wrong or blank string posts to the wrong asset or to a suspense
    account. Costing method (average / standard) also sets what an issue costs - "the cost" is ambiguous
    without it.
26. **Organization scope hides stock.** Balances, stores, and WOs are org-scoped; a read that nets across
    organizations treats separately-held stock as one pool, and a shortage in one org is not filled by
    another's balance without a transfer.
27. **A quick-close / auto-close WO type skips the Completed window.** Some sites configure work-order types
    (often emergency or quick WOs) to go straight from Released to Closed, or auto-close on completion. That
    historizes the WO immediately and leaves no open window for late labour or parts, so a cost that lands
    after the auto-close is stranded exactly as with a forced status. Recognize the WO type before assuming a
    completed WO is still open for actuals.
28. **Re-pointing a WO to different equipment re-attributes all its cost.** Changing the asset / position a
    released WO points at moves its labour, parts, and cost to the new equipment and rolls it up a different
    branch of the hierarchy; do it after actuals are booked and the maintenance history of both the old and
    new equipment is corrupted.
29. **A work request can duplicate demand.** A work request (the request side) can be approved into a WO
    automatically; approving it while a WO for the same problem is also raised manually creates two WOs, two
    reservations, and double the planned spend for one job. Check for an existing WO before converting a
    request, and remember the request and its WO close independently.

## Edge states & special cases
Each breaks naive "issue a quantity, do the work, close it" logic. Key rule inline; deep mechanics in the
references.
- **Position / asset install-remove** - dual structure (fixed position + movable serialized asset); installing
  or removing moves the unit and its history and re-points future cost. See `references/work-order-and-equipment.md`.
- **Cost roll-up across four levels** - asset -> position -> system -> location; never sum a level with its
  parents. See `references/work-order-and-equipment.md`.
- **Rotating / repairable parts** - a tracked condition (new / repairable / rebuilt); issuing / returning
  moves a unit, not a count. See `references/parts-and-stores.md`.
- **Direct / non-stock parts** - never touch store balance; charged to the WO on receipt. Correct to exclude
  from availability, wrong to count as stock.
- **Fixed vs floating vs meter PM** - three due-date engines on the same asset can overlap and generate more
  than one WO; when two schedules for the same asset both come due, merge the scope into one WO or cancel the
  redundant one before releasing, rather than releasing both and double-reserving parts. See
  `references/pm-meters-purchasing.md`.
- **Route WO** - one WO, many equipment; parts and completion act on the round, not a single asset.
- **Meter rollover** - a continuous meter that wraps or is re-installed reads lower than before; the PM
  due-calc must treat it as a rollover, not a reversal, or it never comes due.
- **Multi-organization** - stock, cost, and WOs are org-scoped; do not net across orgs as one pool.
- **Condition monitoring** - a reading past a limit generates a WO or an alarm automatically; a bad reading
  manufactures unneeded work or hides a real fault.
- **Closed financial period** - a costed transaction (an issue, a receipt, an adjustment, or the cost rollup
  at WO close) must land in an **open** period, in EAM's own periods or the interfaced ERP. A closed period
  blocks the posting, which can block a WO close or a receipt entirely, or mis-date it. Check the period is
  open before staging any costed action; reopening a period is a finance decision, not an agent workaround.
- **Safety / permit-to-work** - a WO can carry safety plans, hazards, permits, and lockout-tagout that must be
  satisfied before work starts, and safety or EM work types can add their own approval gates. Treating a
  safety- or permit-gated WO as routine skips a required gate; respect the safety attributes and routing.

## Freshness & reconciliation
Store balances and WO reservations are moving targets. Between the read that planned an issue and the issue
itself, another WO's release, a concurrent issue, a receipt, or a count can change the available balance, so
**re-read available at issue**, not just at plan. The concurrent actor is often Infor EAM itself: PM
generation, reorder runs, condition-monitoring alarms, and scheduled jobs can change a WO status, fire a
reservation, or raise a requisition between your read and your write, so a state you read as stable can move
with no human involved. Infor EAM commonly interfaces to an ERP (SAP, Oracle, or Infor's own M3 / LN) for
finance and sometimes procurement: the ERP holds valuation and AP, EAM holds the MRO operational balance and
the maintenance history. When the two disagree the gap is almost always in-flight - an issue, receipt, or
adjustment not yet interfaced, or interfaced but not yet posted - so treat a raw quantity delta as a
transaction to reconcile, never as a number to force-match. Integration is asynchronous and can queue or
error: a gap is not a true discrepancy until the sync window has passed, so wait and re-read before
concluding the two disagree. Never adjust the EAM balance just to make it equal the ERP; that writes a
phantom loss or gain into the maintenance book.

## Recovery patterns (can it be undone, and what cannot)
- **WO close** - reopening is **not** a standard status transition. If a re-open path is configured you can
  reopen, otherwise the fix is a new corrective WO; the historized actuals stay in the record either way. You
  cannot tell in advance whether re-open is configured, so do not assume it - if the transition is unavailable,
  go straight to a corrective WO.
- **Forced close that stranded actuals** - if a WO was forced or auto-closed before its labour / parts were
  booked, the closed WO cannot absorb them; the only recovery is a corrective WO that re-books the cost to the
  correct equipment. The stranded charge does not post itself later.
- **Issue** - reverse with a **return**, a counter-transaction under a reason code; both the issue and the
  return remain in the cost trail, and a part already physically consumed cannot be returned.
- **Inventory adjustment / count** - corrected only by a **further adjustment**; the variance already posted.
  There is no rollback, only an opposite write that also posts.
- **Actual labour** - reversed by a correcting labour transaction; impossible on a closed WO, so book labour
  before close.
- **WO cancel** - releases reservations cleanly, but a WO with actuals cannot be cancelled; use a new WO and
  let the actuals stand.
- **PO close** - reopen only if config allows, otherwise raise a new PO for the remaining receipt.
- **Meter reading** - a wrong reading is edited or deleted, but any PM WO or condition alarm it already
  generated remains and must be handled separately (cancel the spurious WO, clear the alarm).
- **PM schedule shift** - if a wrong completion date reset the next due on a floating PM, correct the PM's
  last-completion / last-meter, but WOs already generated remain and must be cancelled or worked.
- **Asset install / remove** - reversible by re-installing / removing, but each move is its own history event;
  the trail shows both, and cost already booked to a position stays at that position.

## Guardrails
- Read the WO status (resolve its **system status**, not the label), its reservations, the store
  **available** balance, and the target cost account before acting; re-read available at issue, because
  balances drift. Confirm the cost account resolves to a real account (not a blank that defaults to suspense)
  and that the financial period is open before staging any costed action.
- Confirm the acting user's Infor EAM security / organization authorization actually permits the status change
  or transaction. A human approval does not substitute for the privilege the system itself enforces. Release,
  close, balance adjustment, and PO approval are usually **separate** privileges / responsibilities - a user
  who can release a WO may not be authorized to close it or adjust a store balance; check the specific right.
- Remember the reclassification rule: any change past release (parts, scope, priority, work type, or the
  equipment the WO points at) is committing, not a benign edit.
- Do not close a WO until all labour, parts, and cost are posted. Close historizes and locks; reopening is not
  a normal transition.
- Treat releasing a WO as committing: it reserves parts and can auto-raise spend. Treat every issue, receipt,
  labour posting, and PO approval as a costed event.
- Before issuing or reserving a scarce part, check the reorder impact and competing reservations; a breakdown
  WO outranks a scheduled PM for the same part. Never split a purchase or an adjustment to dodge a threshold.
- Adjust a store balance only against a real physical count, with a reason code and a named approver, and
  never merely to match the ERP.
- Never force a status whose system status skips the reserve / complete / close logic. For anything in the
  destructive row: named approver, re-read, and a logged reason.

## References (load on demand)
- `references/work-order-and-equipment.md` - the four-level equipment hierarchy (Location / System / Position /
  Asset), asset install / remove and history, cost roll-up, the WO status-to-system-status model and what each
  transition runs (reserve, complete, historize), route WOs, WO tasks / hierarchy, and reopen mechanics.
- `references/parts-and-stores.md` - store balances (on-hand / available / reserved), reservation mechanics,
  issue / return / store-to-store transfer / receipt / adjustment transactions, costing methods, rotating /
  repairable and direct / non-stock parts, reorder / min-max / preferred store, and organization scope.
- `references/pm-meters-purchasing.md` - PM schedules (fixed / floating / meter), standard WOs and maintenance
  patterns, routes, meters (continuous / gauge / characteristic and rollover), condition monitoring, and the
  requisition / PO / receipt / invoice flow with its statuses.
