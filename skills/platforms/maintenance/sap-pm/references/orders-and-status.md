# SAP PM order - the status network and what each event runs

The maintenance order is a governed status network **and** a cost collector. The hazard is that each status
change is an **action**, not a label: it makes reservations and requisitions live, posts actuals, closes
demand, posts cost, or locks the record. Read when a workflow releases, confirms, TECOs, settles, closes, or
deletes an order, works a stock vs non-stock component, an internal vs external operation, a sub-order, or
installs / dismantles equipment.

## Contents
- The system status flow and what each transition does
- What you can do in each status
- User status vs system status
- Operations and control keys (internal vs external)
- Components (stock reservation vs non-stock PR)
- Sub-orders and cost rollup
- Equipment install / dismantle

## The system status flow and what each transition does
Happy path: **CRTD -> REL -> (PCNF -> CNF) -> TECO -> settle -> CLSD**. The confirmation stage is **optional**:
an order with no confirmations can be TECO'd directly from **REL**. Do not refuse a valid TECO-from-REL or wait
for a confirmation that will never post.

- **CRTD (created)** - the draft. Operations, components, planned work, and the settlement rule can be added and
  edited freely; nothing is issued, procured, confirmed, or posted. Stock components sit as **planned**
  reservations and non-stock / external lines as planned PRs, not yet firm. This is the only cleanly reversible state.
- **REL (released)** - committing. Release makes reservations firm, converts non-stock components and
  externally-processed operations into **live purchase requisitions**, permits printing the shop paper, goods
  issue (261), and time confirmation. Editing scope/components after REL is a committing change.
- **PCNF / CNF (partly / fully confirmed)** - confirmations (IW41/IW42) post here; each posts labor cost, can
  backflush components, and sets the operation status. A **final** confirmation sets CNF and clears the
  operation's remaining planned work and open capacity.
- **TECO (technically complete)** - closes open reservation quantity and open PRs, removes capacity requirements,
  sets the reference/completion date, and flows completion data to a linked notification. It does **not** close
  cost - late invoices and settlement still post. Reversible via "put in process", but the closed reservations /
  PRs do not simply reappear.
- **SETC (settlement rule created)** - a settlement rule **exists** on the order (often auto-generated). This is
  **not** the same as "settled": SETC can be set long before any settlement run, so it does not tell you cost has
  actually settled. To know whether cost is off the order, check the settlement documents and the order balance,
  not SETC.
- **CLSD (business complete / closed)** - the lock. Requires the order be settled with no open commitments; bars
  any further posting. Terminal in the normal flow.
- **NMAT (missing material)** - the availability check found a component short; a signal to stop, not a state to force past.
- **DLFL (deletion flag)** - marks the order for archiving; resettable before the archiving run, gone after it.

## What you can do in each status
The common agent question is "can I do X while the order is in status Y?". Quick guide (deployments tighten this
with authorizations and user statuses):

| Action | CRTD | REL | PCNF/CNF | TECO | CLSD |
|---|---|---|---|---|---|
| Edit operations / components / scope | yes | committing change | committing change | no (cost only) | no |
| Goods issue components (261) | no | yes | yes | reset TECO first | no |
| Time confirmation (IW41/IW42) | no | yes | yes | no (technically complete) | no |
| Post external-service invoice / cost | no | yes | yes | yes | no |
| Settle (KO88/KO8G) | no | usually at/after TECO | at/after TECO | yes | already settled |
| Move forward | release | confirm / TECO | TECO | close (CLSD) | terminal |

Independent of this table, an **order release strategy** or a required **e-signature** can block the "release"
column even when the status would allow it, and a **user status** set to forbid can block any cell; check those
gates before acting on the status alone.

"Committing change" means allowed but it is a committing action (reservations / PRs are live, cost may be
posted), so gate it. Past CLSD nothing costed is editable; the only path is revoking business completion (if no
open items) or a new corrective order. TECO closes open reservations, so a goods issue for an un-issued
component is not possible on a TECO'd order - the order must be reset ("put in process") first, which does not
cleanly restore the reservations it closed.

## User status vs system status
System statuses are set by events. A **user status** is customer-defined (a status profile on the order type)
and can carry a business-transaction control: **permitted**, **warning**, or **forbidden**. A user status set to
forbid can block release, goods issue, confirmation, or settlement even when the system status would allow it -
for example an order held pending a permit or a safety sign-off. Always read the user status alongside the
system status; acting on "REL" alone can violate a hold that was deliberately set.

Two further controls gate **independently** of the user status. An **order release strategy** (approval by value
/ order type, analogous to a PR/PO release) can hold the order's release until the named approver clears it. A
**digital signature** (e-signature, common in regulated industries such as pharma) can be mandated at release,
confirmation, or TECO. Neither appears as a user status, so an order can be technically releasable yet still
blocked; check for both before assuming a transaction will post.

## Operations and control keys (internal vs external)
- An **operation** is a step with a work center, an **activity type** (the cost rate), planned work, and a
  **control key**. The control key decides whether the operation is internal (in-house labor, confirmed and
  costed at the activity rate) or **externally processed** (a purchased service).
- An externally-processed operation raises a **purchase requisition** for the service at order save/release; that
  PR becomes a PO and the vendor invoice posts to the order as external cost. Treat it as committing spend.
- The confirmation of an internal operation posts labor at the activity type's rate against the work center's
  cost center; a final confirmation clears the operation's remaining capacity and planned work. Labor can be
  confirmed directly (IW41/IW42) or transferred from **CATS** (Cross-Application Time Sheet); a CATS transfer is
  a real confirmation that posts cost and can set CNF, not a draft timesheet.

## Components (stock reservation vs non-stock PR)
- A **stock component** creates an MM **reservation** against plant stock. On a released order the reservation is
  firm and reduces MRP/ATP availability before any physical issue. Goods issue is movement **261** (reverse 262).
- A **non-stock component** raises a **purchase requisition** for direct procurement; it never sits in plant
  stock and is charged to the order on receipt.
- The **material availability check** can set NMAT when a stock component is short. Backflush on confirmation
  issues stock components automatically (261) - a wrong confirmation silently consumes stock.
- Reserving or issuing a scarce spare starves competing orders; a breakdown order normally outranks a scheduled
  preventive order for the same part. Stock, valuation, movement types, and the MM period all live in `sap-mm`.

## Sub-orders and cost rollup
- An order can have **sub-orders** under a **superior order**; cost charged to a sub-order rolls up to the
  superior. The superior cannot be fully settled / closed until its sub-orders are handled.
- Charge labor and materials at the correct level; cost booked to the wrong sub-order distorts the per-asset and
  per-task cost history that reliability and budgeting read.

## Equipment install / dismantle
- **Equipment** is installed at a **functional location** and can be dismantled and reinstalled elsewhere.
  Installed, its maintenance history and cost accrue against that FL and the object's usage list records the
  period of installation.
- Equipment can be linked to a **material + serial number**, so it is both an EQ record and MM stock; a
  goods movement of the serialized material and an install/dismantle must stay consistent, or the asset and its
  stock diverge.
- Writing a notification or order against the FL vs the specific equipment books history to different objects;
  pick the object that owns the failure so reliability analysis is correct.
