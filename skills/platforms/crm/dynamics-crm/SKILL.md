---
name: dynamics-crm
description: Microsoft Dynamics 365 Customer Engagement (CE / CRM - Sales, Customer Service, Field Service) on Dataverse - safe operation of accounts, contacts, leads, opportunities, quotes, orders, invoices, cases (incidents), activities, price lists, work orders, security roles, business units, and plug-in / workflow / Power Automate automation. Use when the connected CRM is Microsoft Dynamics 365 or Dataverse, or the user mentions Dynamics CE or CRM, a Sales / Customer Service / Field Service record, qualifying or disqualifying a lead, an opportunity stage or business process flow (BPF), closing an opportunity won or lost, activating a quote, a sales order or invoice, resolving a case or incident, statecode or statuscode, a work order, a plug-in or real-time vs background workflow or Power Automate flow, a security role or business unit or access team, column (field-level) security, a price list (pricelevel), merging or bulk-updating or bulk-deleting records, or exporting customer PII.
---

# Microsoft Dynamics 365 CE (CRM) - operating it safely

Dynamics 365 Customer Engagement runs the customer and deal record (Sales), the service record (Customer
Service), and field work (Field Service), all on **Dataverse** (the data platform, formerly CDS). In a
supply-chain context it holds account priority, the quote and the order intent, the demand signal an
opportunity carries, and field-service work orders. Three things make it dangerous. First, **almost any write
can fire hidden automation** - a plug-in, a real-time or background workflow, or a Power Automate cloud flow
wired to the same table can email the customer, create downstream rows, or call an external system when you
save. Second, **most lifecycle changes are not plain field writes** - qualifying a lead, closing an
opportunity, activating a quote, or resolving a case run dedicated platform messages with their own side
effects, so setting a status column by hand is the wrong move. Third, **the data is customer PII**, so reading
in-platform is safe but moving it off Dataverse is a sensitive egress event. This skill gives the judgment to
classify Dynamics actions so the harness can gate them, plus the edge states and recovery paths that decide
whether a mistake is fixable.

## Contents
- When this applies / when NOT
- Object & state model
- Vocabulary that bites
- Operations: read / write / destructive
- The automation caveat
- Gotchas that bite
- Edge states & special cases
- Reconciliation & freshness
- Recovery patterns
- Guardrails
- References

## When this applies / when NOT
Connector is Dynamics 365 CE / Dataverse and the work is CRM records, quotes/orders, cases, field-service
work orders, automation, or the security model. When NOT:
- The CRM is **Salesforce**, not Dynamics -> `salesforce`. The concepts rhyme but the security model
  (business units + security roles vs OWD + sharing rules), the state model (statecode/statuscode + platform
  messages vs a Stage picklist), and the automation pipeline differ; do not carry Salesforce habits over.
- **Dynamics 365 Finance & Operations** (the ERP - general ledger, procurement, AR/AP, inventory, production)
  -> `dynamics365-fo`. F&O is a different product on a different data store; CE holds the quote and
  the order *intent*, F&O fulfills and posts it.
- ERP order-to-cash fulfillment, the physical order, inventory and the revenue/AR posting behind an order ->
  `sap-mm` or `oracle-erp`. Do not improvise fulfillment or ledger actions from CE.
- Marketing sends, journeys, and consent (Customer Insights - Journeys, formerly Marketing) are a separate
  app; this skill covers the marketing **list** and campaign response *records* in core CRM, not the send engine.

## Object & state model (reason about state, not nouns)
Every Dataverse row carries two status columns: **statecode** (the coarse state - e.g. Active / Inactive) and
**statuscode** (the granular status reason inside that state). Reason about these, not about a free-text field.
- **Lead** - a raw prospect (person + company on one row). statecode Open -> Qualified or Disqualified.
  **Qualify** is a platform message that (by config) creates an Account + Contact + Opportunity and sets the
  lead Qualified and read-only. There is no clean un-qualify; you reactivate the lead and delete what qualify created.
- **Account** - the company/org row. The parent for contacts, opportunities, cases, and work orders.
- **Contact** - a person, usually tied to an Account. This is the PII surface (email, phone, address).
- **Opportunity** - the deal. It carries an **estimated value / est. close date** and a **Business Process
  Flow (BPF)** stage bar (e.g. Qualify -> Develop -> Propose -> Close). statecode Open -> Won or Lost, set by
  the **Win** or **Lose** message (not a field edit), which writes an **opportunityclose** activity. The BPF
  stage and statecode are two different things - see the BPF entry in vocabulary.
- **Quote** - a priced offer with quote line items against a **price list**. statecode Draft -> Active ->
  Won / Closed. A quote must be **activated** before it can be won; winning a quote generates a **Sales Order**.
- **Sales Order (salesorder)** - the post-sale commitment. Active -> Fulfilled or Cancelled (or on-hold).
  Converting a quote creates it; it can be converted to an **Invoice**. Changes after fulfillment are a new order.
- **Invoice** - the billing row; Active -> Paid / Cancelled.
- **Case (incident)** - a service ticket. statecode Active -> Resolved or Cancelled. **Resolve** is a message
  (`CloseIncident`) that writes an **incidentresolution** activity, checks entitlement/SLA, and can notify the
  customer; you cannot "close" a case with a plain status write. Resolved cases can be reactivated.
- **Activity** - email, phone call, appointment, task. Low blast unless a flow/workflow reacts; sending an
  **email** activity actually dispatches mail.
- **Work Order (msdyn_workorder, Field Service)** - Unscheduled -> Scheduled (a **bookable resource booking**
  commits a technician's time) -> In Progress -> Completed -> **Posted** (product/service actuals post to
  inventory and billing) -> Closed. Posting is committing; see `references/automation-and-lifecycles.md`.
- **Product / Price List (pricelevel) / Price List Item (productpricelevel)** - the product master, a price
  list, and a product's price *in one list*. A quote/order line references one price list; price is per list.

## Vocabulary that bites
- **Dataverse (formerly CDS)** - the platform under every CE app. Tables = entities, columns = fields/
  attributes, rows = records. An "environment" is one Dataverse instance (production or sandbox).
- **statecode vs statuscode** - statecode is the coarse state (Active/Inactive/Won/Lost/Resolved); statuscode
  is the status reason within it. Lifecycle transitions are driven by messages, not by writing these directly.
- **Business Process Flow (BPF)** - the guided stage bar on a form (its own Dataverse row). It drives the
  *sales stage* a rep sees, but it is **not** statecode - an opportunity can sit at BPF stage "Propose" while
  statecode is still Open. Do not read the BPF stage as the win/loss state, and do not treat advancing a stage
  as closing the deal.
- **Qualify / Disqualify (lead)** - qualify is a one-way message that spawns Account+Contact+Opportunity;
  disqualify sets the lead Inactive with a reason. Neither is a simple status toggle.
- **Win / Lose (opportunity)** - dedicated messages that close the deal and log an opportunityclose activity;
  they can fire order-creation and revenue automation. Treat as committing, not a field flip.
- **Security role + access level** - a role grants a privilege (Create/Read/Write/Delete/Append/AppendTo/
  Assign/Share) at an **access level depth**: None / User / Business Unit / Parent-Child BU / Organization. A
  user's effective access is the union of all their roles. This replaces Salesforce's OWD + profiles.
- **Business Unit (BU)** - the hierarchical org container that owns users and scopes BU-level access. Moving a
  user or record between BUs re-computes access. There is no direct Salesforce equivalent.
- **Owner (user or team) / Assign** - a row is owned by a user or a **team**; reassigning (the Assign message)
  changes who can see/edit it via the owner's BU and roles, and can fire assignment automation.
- **Team - owner team vs access team** - an owner team owns rows directly; an **access team** grants specific
  privileges on a single row without changing ownership. Different blast radius; know which one you are touching.
- **Column (field-level) security** - a **field security profile** hides/read-locks individual columns (e.g.
  a PII or margin field). A blank value may be masked, not empty - and it applies over the Web API too.
- **Plug-in / real-time (sync) vs background (async) workflow / Power Automate flow** - the automation layer.
  A synchronous plug-in or real-time workflow runs *inside* the save transaction and can block or roll it back;
  async ones run *after* commit and are not rolled back. Details: `references/automation-and-lifecycles.md`.
- **Rollup / calculated column** - a rollup column recalculates on a **schedule (hourly by default) or on
  demand**, not instantly on child change. It is stale between runs - do not treat it as a live total.
- **Merge (account/contact/lead)** - the loser is **deactivated** (set Inactive, marked merged), not
  hard-deleted; child rows reparent to the master and conflicting field values are lost. Not a clean undo.
- **Solution (managed / unmanaged)** - the container customizations ship in. Deploying a solution can change
  forms, automation, and security across the environment - an org-wide change, not a record edit (treat as a
  deploy, see gotcha 24).

## Operations: read / write / destructive
Classify every operation family by what it does to state, to automation, and to customer data. Kinds of
action, not tool names. The automation caveat below cuts across every write row.

| Class | Dynamics 365 CE operation families | Gate | Why |
|---|---|---|---|
| **Read** | retrieve/query rows (Web API / FetchXML, views, charts, dashboards); view pipeline/forecast; open an account/contact/case/work order; audit history; security-role and BU config | always pass in-platform | no state change; read before every write and re-read at execute (but see the egress axis for PII leaving Dataverse) |
| **Write (reversible)** | create/update a row whose changed columns fire no committing automation; log a task/phone-call/appointment; create a **draft/unsent** email activity; add a note/annotation; build a **Draft** quote; advance a BPF stage without closing; **deactivate** (set statecode Inactive) a row with no cascade; reassign a **task/activity** (not record ownership - changing a record's owner is the committing **Assign**) | gate one at a time | uncommitted internal edit, cleanly settable back - **only if** no wired plug-in/flow makes it commit (verify first; **default-up rule: if the automation is unknown or unverifiable, classify up to committing**) |
| **Write (committing)** | **Qualify** a lead; **Win / Lose** an opportunity (moves the forecast/demand signal, can create an order); **activate** a quote; convert quote -> **Sales Order**; fulfill/convert an order or create an **Invoice**; create / **Resolve** / cancel / reactivate a **Case**; **Assign** (change owner); grant/revoke a record **share**; **book a resource** or **Post** a work order; **send** an email activity or a quote to the customer; edit a **dual-write / F&O-synced** row (commits to Dynamics 365 F&O); change/activate a **price list item** (re-prices future lines) | gate + human approve | binds the deal, the order, the schedule, the customer, or the price; fires automation that reaches the ledger / F&O / field crew / customer |
| **Destructive / irreversible** | **merge** accounts/contacts/leads; **bulk update / bulk delete / bulk assign** (a Bulk Delete job or mass update - fire automation per row, no all-or-nothing rollback across the set); **delete** a row that cascades to children (Parental relationship); change a **security role**, an **access level**, or a **business unit** (org-wide access swing); move a user/record across BUs; import a **solution** or deploy a plug-in/flow change; deactivate a user | hard gate + named approver + re-read | permanent loss, org-wide blast radius, or a bypassed control that cannot be cleanly undone |

**The egress axis (separate from read/write).** Reading contact, lead, and account PII is a safe *read*
in-platform. **Exporting, reporting off-platform, or bulk-extracting that PII** (emails, phones, addresses) to
another system or a human is a sensitive **egress** event - gate it on authorization even though it changes no
Dataverse state. Do not bulk-export customer rows to satisfy a convenience request.

**The lifecycle-message rule.** Qualify, Win, Lose, quote Activate, Resolve/Cancel case, order fulfill, and
work-order Post are **platform messages, not column writes**. Setting statecode/statuscode by hand to "close"
a record skips the message's side effects (the opportunityclose/incidentresolution activity, entitlement and
SLA checks, order/revenue automation) and leaves the record in an inconsistent, half-closed state. Use the
intended transition, and treat each as committing.

**Deactivate vs delete.** Deactivating a row (statecode Inactive) is a reversible write you can reactivate;
**deleting** is a hard remove that can cascade to children via a Parental relationship and is classically
permanent. Never substitute delete for deactivate just to "hide" a row.

**Dual-write / virtual tables.** Some CE rows are synced to Dynamics 365 F&O via **dual-write**, or are
virtual projections of an external store. Editing one commits to the far side (F&O or the external system), so
classify it as committing - or destructive if it triggers an F&O posting - not a plain write; reconcile the
F&O side first (`dynamics365-fo`). If that skill is unavailable, treat a dual-write-synced edit as
**destructive** (hard gate + named approver), because the blast radius reaches the ERP ledger.

**Custom tables.** Most deployments add custom tables (custom SCM records, integration logs) that carry their
own plug-ins, flows, BPFs, and relationship behavior. Default any write on a non-standard table **up to
committing** and verify its automation and cascade (Parental vs Referential) before downgrading - this is
where a "simple field edit" most often hides a cascade.

Universal rules to teach: read before every write and **re-read at execute** (statecode, owner, BPF stage,
and share state all drift); an Inactive or locked row means stop; the security model (BU + roles) is an
org-wide wall, not a per-record toggle; treat customer PII leaving Dataverse as egress.

## The automation caveat (why "reversible" is conditional)
Every create/update/delete runs the environment's plug-ins, real-time and background workflows, Power Automate
cloud flows, and business rules registered on that table. A column you think is cosmetic may be the trigger a
flow is watching, so one save can cascade: field updates, new rows, outbound email, or an external callout
(often into F&O or another SCM system). The pipeline splits by timing and that decides reversibility:
- **Synchronous** plug-ins (pre-validation / pre-operation / post-operation) and **real-time workflows** run
  *inside* the database transaction. If one throws, the whole save - including your field change - **rolls
  back**, so a "successful" write can silently not persist. Re-read after any error.
- **Asynchronous** plug-ins, **background workflows**, and **Power Automate cloud flows** run *after* commit.
  Their side effects (email sent, external callout, downstream row created) are **not rolled back** and can
  fire seconds or hours later, so "nothing happened on save" does not mean nothing will happen.

**Default-up rule:** if you cannot verify what automation is registered on the table/column (no access to the
plug-in registration or flow definitions), classify the write as committing, not reversible. Order of
execution and workflow/flow detail: `references/automation-and-lifecycles.md`.

**The connector acts via the Web API, and API behavior differs from the UI.** A bulk/batch Web API call can
bypass a UI confirmation, some columns are read-only in the UI but writable via API, column security still
masks fields, and plug-ins/flows still run. Do not assume a UI safeguard applies to an API write; the blast
radius can be larger and less visible.

## Gotchas that bite (the real set, as causal chains)
1. **Setting statecode/statuscode by hand to close a record skips the transition's side effects.** Winning an
   opportunity or resolving a case by writing the status column omits the opportunityclose/incidentresolution
   activity, entitlement/SLA checks, and order/revenue automation, leaving a half-closed, inconsistent row.
2. **Winning an opportunity can fire committing automation** - order creation, revenue/forecast updates,
   downstream F&O or fulfillment callouts, partner notifications. It is not a status flip; it can commit the
   financial and physical world.
3. **Qualifying a lead is effectively one-way.** Qualify spawns an Account + Contact + Opportunity and marks
   the lead read-only. There is no clean un-qualify; recovery means reactivating the lead and deleting the
   created rows by hand, and the mapping is lost.
4. **The BPF stage is not the deal state.** An opportunity can be at BPF stage "Propose" while statecode is
   still Open, or Won while the BPF never reached "Close". Reading the stage bar as win/loss over-reports the
   pipeline; advancing a BPF stage does not close the deal.
5. **Any column update can fire a plug-in or flow.** A "cosmetic" edit may be the trigger a record-change flow
   watches - it can email the customer, spawn a row, or call an external system. Verify the wired automation
   before treating an edit as inert.
6. **A synchronous plug-in throwing rolls back your whole save.** The record is unchanged even though the call
   "returned" - confirm the write persisted, do not assume it landed.
7. **Async side effects are not rolled back.** A Power Automate flow, async plug-in, or background workflow
   that already sent mail, called F&O, or created a row is not undone if a later step fails - re-read and check
   for escaped side effects after any error on a committing save.
8. **A quote must be activated before it can be won, and winning it generates a Sales Order.** Skipping
   activation blocks the win; winning silently creates an order (and downstream fulfillment). Size the effect first.
9. **Resolving a case runs CloseIncident, not a status write.** It writes an incidentresolution activity, can
   complete an SLA/entitlement milestone and stop the clock, and often emails the customer; reactivating restarts that.
10. **Merge deactivates the loser, it does not delete it.** The subordinate row is set Inactive and marked
    merged, its children reparent to the master, and conflicting field values are lost. There is no unmerge -
    recovery means reactivating the loser and re-keying children by hand.
11. **Rollup and calculated columns are stale by default.** A rollup recalculates on a schedule (hourly) or on
    demand, not the instant a child changes - a rollup total read right after an edit can be wrong. Trigger a
    recalc or compute from the child rows if you need a live number.
12. **Deleting a row can cascade-delete its children.** A **Parental** relationship cascades delete (and
    assign/share/reparent) to child rows; a **Referential** one does not. Know the relationship behavior before
    deleting a parent account or order.
13. **A hard delete is permanent.** Unless the environment has the Recycle Bin feature enabled and you have
    confirmed it, a delete cannot be undone - assume it is permanent and plan recovery from a backup, not an undo.
14. **A bulk delete or mass update fires automation per row and has no all-or-nothing rollback across the set.**
    A run can partially succeed - failed rows stay unchanged while every succeeded row already fired its full
    plug-in/flow cascade, leaving the data half-changed. Read the job's error log and reconcile the succeeded
    subset before retrying only the failures.
15. **Changing a security role, an access level, or a business unit is an org-wide access swing.** Widening a
    role's depth from User to Business Unit or Organization exposes rows broadly; moving a user or record to
    another BU re-computes who can see it. It is not a per-record grant - route it to the admin.
16. **Column (field-level) security masks values, including over the API.** A blank margin or PII column may be
    hidden by a field security profile, not empty; a report or export run without the profile silently omits it.
17. **A record share is additive and easy to over-grant.** Sharing a row grants specific privileges on top of
    the security model; a broad share (to a large team) leaks a row widely, and revoking it later does not
    recall what was already read or exported.
18. **Owner change (Assign) re-computes access and can fire assignment automation.** Reassigning to a user in
    another BU moves the row's visibility; some users lose access, others gain it, and a wired flow may re-route it.
19. **Posting a Field Service work order commits actuals.** Post writes product/service usage to inventory and
    billing; it is not a status change but a committing inventory/financial event, and a booking commits a
    technician's schedule.
20. **A business rule or validation can silently reject or alter a save.** A server-side business rule can block
    the write or set another column; the update you sent may not be the state that persisted - confirm it.
21. **Changing a price list item re-prices future lines.** Editing a productpricelevel changes the price on
    every new quote/order line using that list; existing lines keep their captured price unless re-priced, and
    deactivating a price list or product breaks quotes that reference it.
22. **Reopening a closed opportunity or reactivating a resolved case is not a clean rewind.** It re-fires
    state-change automation, which can double-create orders or re-open SLA clocks; the earlier side effects
    (order already created, email already sent) are not undone by flipping the state back.
23. **Deactivating a user does not reassign their rows.** Their owned opportunities, cases, and work orders stay
    owned by a disabled user, drop out of queues, and any flows or workflows running as them can fail.
24. **Importing a solution changes the environment, not one record.** A managed/unmanaged solution import can
    alter forms, automation, security roles, and option sets across the environment - treat it as a deploy, not an edit.
25. **Exporting customer PII off Dataverse is an egress event.** Even though the read changes no state, moving
    contact/lead emails, phones, and addresses to another system or a human is sensitive and separately gated.

## Edge states & special cases
Each breaks a naive assumption. Deep security and automation mechanics:
`references/security-model.md`, `references/automation-and-lifecycles.md`.

| Edge state | Naive assumption | Actual behavior | Correct action |
|---|---|---|---|
| **BPF stage vs statecode** | the stage bar is the deal state | BPF stage and statecode are independent rows/columns | read statecode for won/lost; treat the stage bar as guidance only |
| **statuscode inside statecode** | one status field | statecode is coarse, statuscode is the reason within it, and valid transitions are constrained | read both; do not force a statuscode that its statecode disallows |
| **Owner team vs access team** | a team is a team | an owner team *owns* rows; an access team grants privileges on one row without owning | check which team type before assuming ownership or blast radius |
| **Business unit boundary** | roles alone decide access | access depth (User/BU/Parent-Child/Org) is relative to the owner's BU | reason about the owner's BU, not just the role name |
| **Rollup freshness** | a rollup is a live total | it recalculates on a schedule or on demand and is stale between runs | recompute or trigger the rollup before trusting it |
| **Sandbox vs production environment** | one environment | a sandbox is a separate Dataverse copy with different data and IDs | confirm which environment before any write |
| **Elastic/virtual or F&O dual-write table** | a normal Dataverse row | some rows are projections of, or synced to, F&O via dual-write | do not edit a synced row from CE without accounting for the F&O side |
| **Duplicate detection** | create always succeeds | a create can be blocked or warned as a duplicate | resolve via the intended row; a merge is the cleanup (destructive) |

## Reconciliation & freshness
- State drifts under you: statecode, owner, BPF stage, and share state all change. Re-read the live row at
  execute, not the value you cached.
- Rollup and calculated columns are not live - they recalc on a schedule or on demand. A total you read may
  predate the child change you care about; recompute if the number gates a decision.
- A view or personal chart is not ground truth for what exists. Security roles and column security hide rows
  and columns from the running user, so "N rows" may be a filtered subset.
- Automation may still be running. Async plug-ins, background workflows, and Power Automate flows act after the
  save, sometimes much later, so a row can change moments or hours later; verify the end state.

## Recovery patterns (can it be undone, and what cannot)

| Action | Undoable? | How / what cannot be restored |
|---|---|---|
| **Row delete** | assume no | hard delete is permanent; if the Recycle Bin feature is confirmed enabled it needs an admin restore - do not rely on it as an undo; else restore from a backup |
| **Sync plug-in rolled back the save** | nothing persisted | the save (your field change included) was rolled back by a throwing plug-in - re-read to confirm nothing landed, then fix the cause or escalate before retrying |
| **Deactivate (statecode Inactive)** | yes | reactivate the row; the reversible alternative to deleting |
| **Lead qualify** | no clean un-qualify | reactivate the lead and delete the created account/contact/opportunity by hand; the mapping is lost |
| **Merge** | no unmerge | reactivate the deactivated loser and re-key children; conflicting field values are gone |
| **Win / Lose opportunity** | reopen sets it back to Open | reopening re-fires automation; an order/email already created is not undone |
| **Resolve / Cancel case** | reactivate | reactivating restarts SLA/entitlement automation; the incidentresolution activity stays in history |
| **Security role / access level / BU change** | yes, by re-setting config | access recompute is org-wide; rows exposed in the meantime may already have been read or exported |
| **Record share** | revoke the share | revoking does not recall what was already read/exported while shared |
| **Work order Post** | no simple undo | posted actuals hit inventory/billing; correct with an offsetting posting, not a delete |
| **Bulk update / delete partial failure** | no set-wide rollback | read the job error log, reconcile the succeeded subset (already fired automation per row), retry only the failed rows - do not re-run the whole job |
| **User deactivation** | reactivate if a license is free | rows are **not** auto-reassigned - explicitly reassign the disabled user's opportunities/cases/work orders (they drop out of queues and their flows fail) as a mandatory follow-up |

After an unintended cascade, the forensic tool is the **audit log** (per-table, shows old/new values on
audited columns) plus the plug-in trace log and the flow run history. Use them to reconstruct what fired and
what changed before deciding a recovery; none of them undo anything.

## Guardrails
- Read the row plus its wired automation, statecode/statuscode, BPF stage, owner, and share state before
  acting; re-read at execute.
- Use the intended lifecycle transition (Qualify, Win/Lose, Activate, Resolve) - never fake a close by writing
  statecode/statuscode directly; it skips the side effects and leaves an inconsistent record.
- Never change a security role, an access level, or a business unit to grant access for one task - it is an
  org-wide recompute, not a per-record grant. Route the access need to the admin; a scoped record share is the
  reversible alternative.
- Treat Qualify, Win/Lose, quote Activate, order fulfill, case Resolve, resource booking, and work-order Post
  as committing - each fires automation that reaches the ledger, F&O, the field crew, or the customer. Size the
  effect before saving.
- Exporting or bulk-reporting customer PII off Dataverse is an egress event; require authorization even though
  it changes no state.
- Confirm which environment you are in (sandbox vs production) before any write; a sandbox is a separate copy
  with different data and IDs.
- For anything in the destructive row (merge, bulk delete/update, cascade delete, role/BU change, solution
  import, user deactivation): named approver, re-read of live state, a logged reason, and prefer a reversible alternative.

## References (load on demand)
- `references/security-model.md` - how Dataverse computes access (business units, security roles and the
  privilege/access-level matrix, owner vs access teams, record sharing, column security) and what a change
  recalculates. Read when a task touches ownership, visibility, a role/BU change, or field access.
- `references/automation-and-lifecycles.md` - the plug-in execution pipeline (pre/post, sync vs async and the
  transaction), real-time vs background workflows, Power Automate cloud flows, business rules and rollup
  recalculation; plus the sales/service/field-service state-transition messages, quotes/orders/invoices, and
  price lists. Read when an edit may fire automation, or a workflow touches a lifecycle transition or pricing.
