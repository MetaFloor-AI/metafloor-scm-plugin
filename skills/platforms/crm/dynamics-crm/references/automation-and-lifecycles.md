# Dynamics 365 CE - automation pipeline, lifecycles, and pricing

Why a single save can do far more than change one column, and how the sales/service/field-service lifecycle
transitions carry side effects. Read when an edit may fire automation, or a workflow touches a lifecycle
transition (qualify, win/lose, quote/order, case resolve, work-order post) or pricing.

## Contents
- The execution pipeline (what runs on a save)
- Sync vs async, and what rolls back
- Kinds of automation and their side effects
- Rollup and calculated columns (freshness)
- Sales lifecycle: lead -> opportunity -> quote -> order -> invoice
- Service lifecycle: case (incident) resolution
- Field Service: work order lifecycle
- Price lists and pricing

## The execution pipeline (what runs on a save)
A create/update/delete runs a fixed server-side event pipeline. Plug-ins register on a message (Create,
Update, Delete, Qualify, Win, etc.) at a **stage**:
1. **Pre-validation** - before the main transaction begins (security-independent; runs even outside the DB
   transaction). Used to cancel early.
2. **Pre-operation** - inside the transaction, before the row is written. Can alter the values about to save.
3. **Main operation** - the platform writes the row.
4. **Post-operation** - inside the transaction, after the write. Used to cascade to other rows.
Real-time (synchronous) workflows and business rules also evaluate around this. Then, after commit, the
**asynchronous** layer runs: async plug-ins, background workflows, and Power Automate cloud flows queued by the event.

## Sync vs async, and what rolls back
- **Synchronous** (pre/post plug-ins registered sync, real-time workflows): run *inside* the database
  transaction. If any throws, the entire save **rolls back**, including your field change. A call can "return"
  yet leave nothing persisted - re-read after any error to confirm what landed.
- **Asynchronous** (async plug-ins, background workflows, Power Automate cloud flows): run *after* commit.
  Their side effects - email sent, external callout to F&O or another SCM system, downstream row created - are
  **not rolled back** if a later step fails, and they can fire seconds or hours later.
- The practical rule: **you cannot tell from the column alone whether an edit is inert.** Classify a write by
  the *most committing* thing its registered automation does, not by the column you touched. If you cannot see
  the plug-in registrations or flow definitions, default the write up to committing.

## Kinds of automation and their side effects
| Mechanism | Fires on | Timing | Typical side effects |
|---|---|---|---|
| **Plug-in** | any registered message (create/update/delete/qualify/win/…) | sync or async | arbitrary code: cascading writes, external callouts, custom validation |
| **Real-time workflow** | create/update/assign/status change | sync | field updates, create rows, send email, block the save |
| **Background workflow** | same triggers | async | same effects, after commit, not rolled back |
| **Power Automate cloud flow** | Dataverse create/update/delete (connector) | async | callouts to any connected system (F&O, email, Teams, external SCM), create/update rows |
| **Business rule** | form + server | sync | set/clear columns, show error, block save |
| **Duplicate detection rule** | create/update | sync | warn or block a probable duplicate |

## Rollup and calculated columns (freshness)
- A **calculated column** computes on read from other columns on the same row - live, but only from that row.
- A **rollup column** aggregates child rows (sum/count/min/max). It recalculates on a **system job schedule
  (hourly by default) or on demand**, not the instant a child changes. Between runs it is **stale**.
- Consequence: a rollup total read right after editing a child can be wrong. Trigger a recalculation or compute
  from the child rows directly when the number gates a decision (e.g. account exposure, open pipeline).

## Sales lifecycle: lead -> opportunity -> quote -> order -> invoice
- **Qualify (lead)** - the Qualify message sets the lead Qualified (read-only) and, by config, creates an
  Account + Contact + Opportunity. One-way; no clean un-qualify. **Disqualify** sets the lead Inactive with a reason.
- **Opportunity** - carries a Business Process Flow stage bar (guidance) and statecode Open. **Win** and
  **Lose** are dedicated messages that set statecode Won/Lost and write an **opportunityclose** activity; they
  can fire order-creation and forecast/revenue automation. Do not close by writing statecode directly.
- **Quote** - built against a **price list**. statecode Draft -> **Active** (must activate before winning) ->
  **Won** (generates a Sales Order) / Closed. A **revision** closes the quote and creates a new revised quote.
- **Sales Order** - from a won quote (or created directly). Active -> **Fulfilled** or **Cancelled**; can
  convert to an **Invoice**. Post-fulfillment changes are a new order, not an edit.
- **Invoice** - Active -> **Paid** / Cancelled.
Each transition above is a committing write: it binds the deal, the order, or billing and can call downstream systems.

## Service lifecycle: case (incident) resolution
- A **case (incident)** is Active. **Resolve** runs the `CloseIncident` message: it writes an
  **incidentresolution** activity, can complete an **entitlement**/**SLA** milestone and stop the SLA clock,
  and often emails the customer. **Cancel** sets it Cancelled.
- You cannot "close" a case by writing statecode - use Resolve/Cancel. A resolved case can be **reactivated**,
  which restarts SLA/entitlement automation; the incidentresolution activity stays in history.

## Field Service: work order lifecycle
- A **work order (msdyn_workorder)**: **Unscheduled** -> **Scheduled** (a **bookable resource booking** commits
  a technician's time and appears on the schedule board) -> **In Progress** -> **Completed** -> **Posted** ->
  **Closed**.
- **Posting** a work order commits **product and service actuals** to inventory and billing - a committing
  inventory/financial event, not a status change. Correct a wrong post with an offsetting posting, not a delete.
- A **booking** commits a resource's schedule; cancelling/rescheduling re-notifies and can breach an agreement window.

## Price lists and pricing
- A **price list (pricelevel)** holds **price list items (productpricelevel)** - a product's price in that list
  (with currency and unit). A quote/order/invoice line references one price list, so **price is per list**.
- Changing a price list item re-prices every **future** line using that list; existing lines keep their
  captured price unless re-priced. Deactivating a price list, a product, or a price list item **breaks** quotes
  and orders that reference it and removes the product from new lines.
- **Discount lists** apply volume/amount discounts to lines. Multi-currency: a price list is per currency; the
  line's currency selects the matching list.

Gating note: because any save can cascade and lifecycle transitions carry side effects, classify a write by the
*most committing* thing it does. A qualify that spawns an opportunity, a win that creates an order, a case
resolve that stops an SLA clock, or a work-order post that hits inventory are committing, not reversible edits.
