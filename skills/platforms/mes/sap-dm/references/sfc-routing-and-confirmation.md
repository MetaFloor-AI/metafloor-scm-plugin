# SAP DM - SFC lifecycle, routing/operations, and the S/4HANA confirmation

How SAP Digital Manufacturing structures and runs production, and why "sign off the operation" is a material +
financial commit. Read when a task touches SFC states, the routing/operation flow, Start vs Sign-off,
backflush, the ERP confirmation, split/merge, process orders/phases, or order sync with ERP.

## Contents
- The order and where it comes from
- The SFC and its status model
- The routing / production process and operation states
- Start vs Sign-off (the commit)
- Backflush and the S/4HANA confirmation hand-off
- Auto vs explicit component consumption
- SFC split / merge and genealogy branching
- Serialized vs quantity / batch SFC
- Process orders and phases (process industry)
- The production-process version model
- Order download / re-sync with ERP
- Gating notes

## The order and where it comes from
The production/process order originates in **S/4HANA (or ECC) PP** and is downloaded to SAP DM through the
standard integration. DM does not own the order master - it owns execution against it. The order carries the
material, quantity, routing/BOM reference, and dates. Two copies exist (ERP and DM); they can drift, so order
status is a cross-system fact. Releasing the order lets the floor build and consume; completing it posts the
finished quantity back to ERP; **TECO / close is an ERP-side act** and closing with open WIP strands SFCs.

## The SFC and its status model
The **SFC (shop-floor-control number)** is the tracked unit - a quantity of the order's material moving through
the routing. It carries a quantity, an overall status, a current operation, and its as-built genealogy.

| SFC overall status | Meaning |
|---|---|
| **New** | created for the order, not yet started |
| **Active / In Queue** | in process on the routing (queued or in work at an operation) |
| **On Hold** | contained - cannot be processed until released |
| **Done** | completed the last operation; finished quantity confirmed to ERP |
| **Scrapped** | removed from the order (yield loss) |
| **Deleted** | removed before execution (no confirmation) |

Overall status is not the same as **operation-level status**: at any operation an SFC is **In Queue** ->
**Active / In Work** (Started) -> **Done at operation** (signed off, advanced). Reason about the operation-level
state, not just the overall status - "the SFC is Active" does not say which operation it sits at.

## The routing / production process and operation states
The **routing** (discrete) or **master recipe** (process) is the ordered sequence of **operations** (or
**phases**). Each operation carries: required **data collection**, **resource/work-center** requirements,
**components (BOM)** to consume, **work instructions**, and **buyoff/sign-off** rules. Movement is sequential;
**skip and out-of-sequence moves are blocked** unless explicitly overridden (a destructive override). An
operation may be a **queue -> start -> complete** step, and some operations are counting points where the
confirmation to ERP posts.

## Start vs Sign-off (the commit)
- **Start** claims the operation and its resource and marks the SFC In Work. It posts no confirmation and
  consumes nothing - reversible by cancel/undo start **while no sign-off posted and no machine-side processing
  began**. On an automated line a Start may command the machine, and a machine-initiated Start may not be cleanly
  cancellable.
- **Complete / Sign-off** is the commit. It posts operation progress, backflushes the operation BOM, records the
  data collection, applies any buyoff, and advances the SFC to the next operation. On the **final** operation it
  posts the finished-goods receipt and sets the SFC Done. Every sign-off with a BOM is a material posting to ERP.

## Backflush and the S/4HANA confirmation hand-off
On sign-off, SAP DM sends a **production confirmation** to S/4HANA. The confirmation posts, in one transaction:
- **Labor / machine activity** against the order - for order costing.
- **Component goods issue (movement type 261)** - the **backflush** of components flagged for backflush, at
  **standard** BOM quantity. Non-backflush components need an explicit goods issue (an assemble/consume action).
- On the **final** operation (or an operation flagged for auto goods receipt), a **finished-goods receipt
  (movement type 101)** - finished stock into ERP.

Consequences:
- The confirmation is an **audited financial event** (stock + ledger via the goods movements and activity).
- It can **fail on the ERP side** (closed posting period, order TECO/closed, missing/short components, account
  assignment) while DM shows the SFC advanced/Done - a **reconciliation gap**. Do not re-complete or blindly
  reverse; resolve the ERP-side reason (`sap-mm`) and re-trigger.
- Reversing it is an **ERP-side confirmation cancellation** that posts counter goods movements (reverses the
  261/101). It is a counter-document, not a DM undo; both entries stay in the trail (`sap-mm`).

## Auto vs explicit component consumption
- **Backflush (auto)** - components flagged for backflush consume automatically at sign-off at standard qty, no
  pick. Fast, but wrong if actual usage differs from standard (over/under-consumption, negative ERP stock).
- **Explicit assemble / consume** - the operator adds a specific component lot/serial into the SFC (an
  **Assembly** action). This writes the exact as-built and posts the goods issue for that component. Use it
  where traceability of the specific lot/serial matters; a wrong lot mis-records genealogy and mis-consumes.

## SFC split / merge and genealogy branching
- **Split** - divide a quantity SFC into a child SFC (e.g. to scrap or rework part). The child inherits the
  parent's as-built up to the split; genealogy branches. A mistaken split mis-attributes which units carry which
  component lots.
- **Merge / combine** - join SFCs; genealogies join. Reversible only before further processing.
- Quantity math and genealogy both change on split/merge - never treat them as bookkeeping.

## Serialized vs quantity / batch SFC
- **Serialized** - one SFC = one unit (a serial number). Actions apply to that unit.
- **Quantity / batch** - one SFC = a quantity; **partial sign-off** confirms part of it, **scrap** removes part,
  **split** carves part into a child. Assuming a serialized model on a quantity SFC (or vice-versa) mis-sizes the
  action.

## Process orders and phases (process industry)
For process manufacturing, the order is a **process order** and the routing is a **master recipe** of
**operations -> phases**. Batch management applies: the SFC/order produces a **batch**, and components may be
**batch-determined**. The commit is a **phase completion** (with the batch effect) rather than a discrete
operation; the confirmation still flows to ERP (activity + component goods issue + finished goods receipt with
the produced batch). Assuming the discrete operation model on a process order mis-identifies the confirmation
point and misses the batch.

## The production-process version model
The **production process** (routing + BOM + data collection + work instructions) is **versioned** with a status:
**draft/new -> released/current -> archived**. Editing a **draft** is reversible and affects nothing yet.
Releasing a version makes it **effective** for new orders. Editing or archiving a **released/current** version is
a **change-controlled fleet change** - it re-routes or re-consumes every new order and can hit in-flight SFCs at
their next operation. A corrected build is a **new version**, not an in-place edit.

## Order download / re-sync with ERP
Orders download from ERP and re-sync on change (quantity, dates, status, BOM/routing). Acting on a **stale**
order is a hazard: an order **TECO'd or cancelled in ERP** but still Released in DM will **fail the
confirmation** or strand WIP; a quantity changed in ERP re-scopes the build. Re-read both DM and ERP order
status at execute; reconcile before completing or scrapping.

## Gating notes
- **Start** an SFC at an operation = reversible (claims the resource, no confirmation). Machine-initiated Start
  may not be cleanly cancellable.
- **Sign-off / Complete** an operation with a BOM = committing (261 backflush + activity to ERP). **Final**
  operation completion = committing (101 goods receipt + SFC Done).
- **Assemble / explicit consume** a component = committing (as-built + ERP goods issue).
- **Split** an SFC = committing (quantity + genealogy branch). **Merge** irreversibly = destructive.
- **Cancel a confirmation** (ERP side) = destructive (counter goods movements, permanent trail).
- Editing a **draft** production process = reversible; releasing to current, or editing/archiving a
  released/current version while SFCs are in flight = destructive/change-controlled.
- **Skip / out-of-sequence** move past a required operation = destructive (bypasses required DC/buyoff).
- **DM Insights / OEE** = read.
