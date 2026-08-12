---
name: salesforce
description: Salesforce CRM (Sales Cloud / Service Cloud) - safe operation of leads, accounts, contacts,
  opportunities (stage, close date, forecast), quotes and CPQ, orders, cases, activities, approval
  processes, Flow/trigger automation, price books, and the sharing model (org-wide defaults, role
  hierarchy, profiles/permission sets). Use when the connected CRM is Salesforce, or the user mentions
  Salesforce, Sales Cloud, Service Cloud, a lead or lead conversion, an account/contact/opportunity, an
  opportunity stage or close date, pipeline or forecast, a quote or CPQ, an order or order activation, a
  case (escalate/close), an approval process or a locked record, a Flow, Process Builder, workflow rule,
  Apex trigger, a validation rule, a roll-up summary, org-wide defaults (OWD) / role hierarchy / sharing
  rule / profile / permission set / field-level security, a price book, merging accounts or contacts, a
  mass update / mass delete / Data Loader, SOQL, or exporting customer PII.
---

# Salesforce - operating it safely

Salesforce runs the customer and deal record (Sales Cloud) and the service record (Service Cloud). In a
supply-chain context it holds account priority, the quote and the order intent, and the demand signal that
an opportunity stage represents. Two things make it dangerous. First, **almost any write can fire hidden
automation** - a Flow, workflow rule, or Apex trigger wired to the same field can email the customer, create
downstream records, or call an external system the moment you save. Second, **the data is customer PII**, so
reading is safe in-platform but moving it off Salesforce is a sensitive egress event. This skill gives the
judgment to classify Salesforce actions so the harness can gate them, plus the edge states and recovery
paths that decide whether a mistake is fixable.

## Contents
- When this applies / when NOT
- Object & state model
- Vocabulary that bites
- Operations: read / write / destructive
- Gotchas that bite
- Edge states & special cases
- Reconciliation & freshness
- Recovery patterns
- Guardrails
- References

## When this applies / when NOT
Connector is Salesforce and the work is CRM records, quotes/orders, cases, forecast, automation, or the
sharing model. When NOT:
- ERP order-to-cash: the physical order fulfillment, the AR/revenue posting, inventory and delivery behind an
  order -> `sap-mm` or `oracle-erp`. Salesforce carries the quote and the order *intent*;
  the ERP fulfills and posts it. Do not improvise fulfillment or ledger actions from here.
- The CRM is Microsoft Dynamics, not Salesforce -> `dynamics-crm`.
- Marketing Cloud / Pardot campaign sends, journeys, and consent are a separate system; this skill covers the
  Campaign and Campaign Member records inside core CRM, not the marketing platform.

## Object & state model (reason about state, not nouns)
- **Lead** - a raw prospect (person + company on one record). States: Open / Working / Nurturing -> Converted
  or Unqualified. **Conversion is one-way**: it creates an Account + Contact + (optionally) an Opportunity and
  marks the Lead converted and read-only. There is no standard un-convert.
- **Account** - the company/org record. Business accounts have child Contacts; a **Person Account** is a
  hybrid account+contact and behaves differently (see edge states).
- **Contact** - a person tied to an Account. This is the PII surface (email, phone, address).
- **Opportunity** - the deal. Carries a **Stage** (picklist) that maps to a **Probability** and a **Forecast
  Category**, plus a **Close Date** and Amount. Stages run e.g. Prospecting -> Qualification -> Proposal ->
  Negotiation -> Closed Won / Closed Lost. The stage is the demand/forecast signal, not a cosmetic label.
- **Quote / CPQ Quote** - a priced configuration with Quote Lines. In CPQ the **primary** quote can *sync* to
  the Opportunity (rewriting its amount and line items) and can generate an Order or Contract. See
  `references/automation-and-cpq.md`.
- **Order** - the post-sale commitment. States: **Draft -> Activated**. Activating locks Order Products and
  signals fulfillment; changes after activation go through a **reduction/amendment order**, not an edit.
- **Contract** - an agreement record; may auto-renew and drive entitlements.
- **Case** - a service ticket. States: New -> Working -> Escalated -> Closed (Closed can reopen). Closing or
  escalating fires **entitlement / SLA milestone** logic and often a customer notification.
- **Activity** - a Task or Event (calendar). Logging a call/meeting; low blast unless wired to automation.
- **Campaign / Campaign Member** - a marketing initiative and the leads/contacts linked to it (with a member
  status). In-scope as CRM records for association and reporting; the send/journey engine is out of scope
  (Marketing Cloud / Pardot). Adding members is a low-blast write unless a Flow reacts to member status.
- **Product2 / Price Book / PricebookEntry** - the product master, a price list, and a product's price *in a
  specific book*. A quote/opportunity line references one book; the price is per book, not global.
- **Approval process** - submitting a record for approval **locks it** (read-only) until approved, rejected,
  or recalled, then routes to the approver and can fire post-approval field updates/actions.

## Vocabulary that bites
- **Stage vs Probability vs Forecast Category** - Stage drives the forecast. Changing Stage moves the weighted
  pipeline number even if Amount never changed. Closed Won / Closed Lost are terminal-ish and fire automation.
- **Lead conversion** - one-way. Creates Account + Contact + Opportunity and archives the Lead. Not a status
  toggle; treat it as committing and irreversible-by-standard-means.
- **Org-Wide Defaults (OWD)** - the baseline record visibility per object: Private / Public Read Only / Public
  Read-Write. Everything else (role hierarchy, sharing rules, manual shares) only opens access *above* OWD.
- **Role hierarchy** - people above you in the role tree see records you own. Ownership + role decide who can
  see a record, so changing owner re-shares it up a different branch.
- **Profile vs Permission Set** - what a user *can do* (object/field create-read-edit-delete, admin rights).
  **Field-Level Security (FLS)** hides individual fields; a blank field may be hidden, not empty.
- **Flow / Process Builder / Workflow Rule / Apex Trigger** - automation that fires on a record change. One
  save can cascade: field updates, new records, outbound email, external callouts, scheduled/time-based paths.
- **Validation rule** - blocks a save if a condition fails. An edit that looks valid can be silently rejected;
  the record does not change and the write did not land.
- **Roll-up summary / formula field** - a parent field derived from children (sum/count/min/max). Editing or
  deleting a child recomputes the parent and any automation keyed on it.
- **Quote Sync (CPQ)** - the primary quote's lines sync onto the Opportunity. Editing the synced quote rewrites
  the Opportunity amount and products; re-syncing can overwrite opportunity line items.
- **Merge** - combining duplicate accounts/contacts/leads. The losing records are **deleted**, children
  re-parent to the master, and conflicting field values are lost unless kept. Destructive, no unmerge.
- **Master-detail vs lookup** - deleting a master **cascade-deletes** its detail records; a lookup does not.
  Know the relationship type before deleting a parent.
- **Recycle Bin** - deleted records recover for **15 days**, then hard-delete. Bulk API hardDelete and "empty
  bin" skip the window.
- **Queue** - a shared owner for leads/cases; records owned by a queue route differently than user-owned ones.

## Operations: read / write / destructive
Classify every operation family by what it does to state, to automation, and to customer data. Kinds of
action, not tool names. The automation caveat below cuts across all write rows.

| Class | Salesforce operation families | Gate | Why |
|---|---|---|---|
| **Read** | view/query records (SOQL, list views, reports, dashboards); view pipeline/forecast; view case/account/contact; approval history; sharing settings; field history | always pass in-platform | no state change; read before every write and re-read at execute (but see the egress axis for PII leaving the platform) |
| **Write (reversible)** | create/edit a record whose changed fields fire no committing automation; log a Task/Event; add a note/comment; build a **draft** quote; reassign a task | gate one at a time | uncommitted internal edit, cleanly settable back - *only if* no wired Flow/trigger makes it commit (verify first; if automation is unknown or unverifiable, classify up to committing) |
| **Write (committing)** | change an Opportunity Stage or Close Date (moves the forecast/demand signal; Closed Won can trigger orders/fulfillment); **convert a Lead**; submit a record for approval (locks it); approve/reject a step; create or **activate an Order**; create/escalate/**close a Case**; sync a CPQ quote / generate an order or contract from a quote; change an owner (re-shares, fires assignment); send an email or a quote to the customer; change/activate a **PricebookEntry** (re-prices future lines) | gate + human approve | binds the deal, the order, the customer, or the price; fires automation that reaches the ledger/fulfillment/customer |
| **Destructive / irreversible** | **merge** accounts/contacts/leads; **mass update / mass delete / mass transfer** (require all-or-none, or a mandatory post-run reconciliation of the succeeded subset); delete a master record with detail children (cascade); hard-delete / empty Recycle Bin; deactivate a user; lower OWD, change the role hierarchy, or delete a sharing rule (org-wide sharing recalculation, which can be deferred/asynchronous); deploy/activate a Flow or trigger change; recall or admin-unlock a record under approval | hard gate + named approver + re-read | permanent loss, org-wide blast radius, or a bypassed control that cannot be cleanly undone |

**The egress axis (separate from read/write).** Reading contacts, leads, and account PII is a safe *read*
in-platform. **Exporting, reporting off-platform, or bulk-extracting that PII** (emails, phones, addresses)
to another system or a human is a sensitive **egress** event - gate it on authorization even though it
changes no Salesforce state. Do not bulk-export customer records to satisfy a convenience request.

**The automation caveat (why "reversible" is conditional).** Every DML write runs the org's triggers, flows,
workflow rules, and validation rules. A field you think is cosmetic may be wired to a record-triggered Flow
that emails the customer, creates a downstream record, or calls an external system. So a "reversible" edit is
only reversible if no committing automation is attached - **read the record's wired automation before assuming
an edit is inert**, and re-read state after, because scheduled/time-based paths can fire later. **Default-up
rule:** if you cannot verify what automation is wired to the object/field (no access to the Flow/trigger
metadata), classify the write as committing, not reversible. Order-of-execution detail:
`references/automation-and-cpq.md`.

**Custom objects follow the same rules.** Most orgs carry custom objects (custom supply-chain records,
integration logs) with their own triggers, validation, and sharing. The read/write/destructive classification
applies unchanged; before acting, discover the object's relationship type (master-detail vs lookup, which
decides cascade delete) and its wired automation - do not assume a custom object is inert.

**API vs UI differ, and the connector acts via API.** The same action can behave differently through the API:
a partial-success bulk call can bypass the all-or-nothing UI save, Bulk API hardDelete skips the Recycle Bin
(no 15-day recovery), some fields are read-only in the UI but writable via API, and triggers/flows still run.
Do not assume a UI safeguard applies to an API write; the blast radius can be larger and less visible.

**Record locks beyond approval.** A record can be locked and reject edits for reasons other than an approval
process: a **converted Lead** is locked, an Opportunity with a **synced CPQ quote** locks its lines, and some
CPQ operations lock records mid-process. A cryptic "cannot edit" error usually means one of these; find the
lock source before retrying, do not force past it.

**Prohibited circumvention (patterns to block, not operations to perform):** admin-unlocking or recalling a
record to edit it past its approval; lowering OWD or adding a broad sharing rule to grab access for one task;
splitting or re-coding a record only to route around an approver; exporting PII under a routine-report
pretext. These are audit-flagged workarounds; if a request amounts to one, stop and route to the real owner.

Universal rules to teach: read before every write and **re-read at execute** (stage, owner, approval,
sharing, and match state all drift); a locked (in-approval) record means stop; the sharing model is an
org-wide wall, not a per-record toggle; treat customer PII leaving the platform as egress.

## Gotchas that bite (the real set, as causal chains)
1. **Changing an Opportunity Stage moves the forecast even if Amount is unchanged.** Stage maps to Probability
   and Forecast Category, so a stage bump silently inflates the weighted pipeline and the demand signal downstream.
2. **Setting an Opportunity to Closed Won can fire committing automation** - order creation, revenue
   recognition, fulfillment/provisioning, partner notifications. It is not just a status flip; it can commit
   the financial and physical world.
3. **Lead conversion is one-way.** Convert creates an Account + Contact + Opportunity and marks the Lead
   read-only. There is no standard un-convert; recovery means deleting the created records by hand and the
   field mapping is lost.
4. **Any field update fires triggers and flows.** A "cosmetic" edit can be wired to a record-triggered Flow
   that emails the customer, spawns a task, or calls an external system. Verify the wired automation before
   treating an edit as inert.
5. **A validation rule can silently reject the save.** An update that looks valid fails because a rule needs
   another field; the record is unchanged and the write did not land - confirm it persisted.
6. **Submitting for approval locks the record.** Once submitted it (and often related records) is read-only
   until approved, rejected, or recalled. Further edits are blocked, not merely discouraged. Create and submit
   are two deliberate steps: creating is a reversible write, but submitting locks the record immediately, so do
   not create-and-submit in one motion if the record still needs edits.
7. **Merging accounts/contacts/leads is destructive.** The losers are deleted, their children re-parent to the
   master, and conflicting field values are lost unless kept. There is no unmerge.
8. **Deleting a master record cascade-deletes its detail children.** Deleting an Account can remove related
   detail records via master-detail; a lookup relationship does not cascade. Know the relationship first.
9. **Deleted records recover for only 15 days.** Undelete works within the Recycle Bin window; after that, or
   after a Bulk API hardDelete / empty-bin, recovery needs a backup, not an undo.
10. **Changing OWD or the role hierarchy recalculates sharing for every record.** Lowering OWD to Public
    exposes data broadly; tightening it hides records users relied on. It is an org-wide blast, not a per-record
    edit - and the recalculation can be **deferred/asynchronous**, so visibility does not change the instant you
    save. Do not act on the new access model until the recalculation has finished; the old access may still hold.
11. **Changing a record's owner re-shares it.** Ownership plus role hierarchy drive visibility, so a
    reassignment moves the record up a different branch; some users lose access, others gain it, and it can fire assignment rules.
12. **Field-Level Security hides fields per profile.** A field is blank in your view because FLS masks it, not
    because it is empty; a report can silently omit a field a different profile would see.
13. **Roll-up summary fields recompute from children.** Editing or deleting an opportunity line or a child case
    changes the parent total/count and any automation keyed on it; a mass child change ripples into parent totals.
14. **CPQ Quote Sync rewrites the Opportunity.** Editing the synced primary quote's lines overwrites the
    Opportunity's amount and products; unsyncing and re-syncing can clobber opportunity line items.
15. **A PricebookEntry sets a product's price per book.** Changing it re-prices every future quote/opportunity
    line using that book; deactivating a price book or product breaks quotes that reference it.
16. **Order activation is committing.** Draft -> Activated locks Order Products and signals fulfillment;
    post-activation changes go through a reduction/amendment order, not an edit of the activated order.
17. **Case escalation and closure fire SLA/entitlement milestones and customer emails.** Closing a case can
    complete a milestone, stop an SLA clock, and notify the customer; reopening restarts that automation.
18. **Mass and bulk operations fire automation per record and can hit governor limits mid-run.** Two failure
    modes: with all-or-none on, a limit hit **rolls the whole batch back** (no partial data, but wasted work);
    with all-or-none off, it **partially succeeds** - the failed records stay unchanged while every succeeded
    record already fired its full automation cascade, leaving the data half-changed. Know which mode is set,
    read the per-record error report, and reconcile the succeeded subset before retrying only the failures.
19. **Data Loader / Bulk API is not a quiet backdoor.** It still runs triggers, flows, validation, and
    workflow - just at volume with less visibility, so the blast radius is larger, not smaller.
20. **Deactivating a user does not reassign their records.** Their owned opportunities/cases/leads stay owned by
    an inactive user, drop out of active queues, and any flows or scheduled jobs running as them can fail.
21. **Recalling or admin-unlocking a record under approval bypasses the control.** The record becomes editable
    outside the intended review; it is an authority action, not a shortcut.
22. **Reopening a Closed Won/Lost opportunity is not a clean rewind.** It fires stage-change automation again,
    which can double-create orders or re-open the forecast; the earlier side effects are not undone by resetting the stage.
23. **Exporting customer PII off-platform is an egress event.** Even though the read changes no state, moving
    contact/lead emails, phones, and addresses to another system or a human is sensitive and separately gated.
24. **A single-record save is atomic for synchronous automation, but async side effects are not rolled back.**
    If a Flow or trigger throws mid-cascade, the whole synchronous transaction rolls back (the field change too)
    - so a "successful" write can silently not persist. But outbound email, external callouts, and scheduled/
    async paths already fired are not undone by that rollback. After any error on a committing save, re-read the
    record to confirm what actually persisted and check for side effects that escaped the rollback.
25. **Stage transitions can be constrained.** Validation rules commonly block backward moves or skips (e.g.
    Prospecting straight to Closed Won). Do not assume an arbitrary stage jump is allowed; and Closed Won/Lost
    are effectively terminal (reopening re-fires automation, gotcha #22).

## Edge states & special cases
Each breaks a naive assumption. Deep sharing and CPQ mechanics: `references/sharing-and-security.md`,
`references/automation-and-cpq.md`.

| Edge state | Naive assumption | Actual behavior | Correct action |
|---|---|---|---|
| **Person Account** | account has separate contacts | account and contact are one hybrid record (and share behavior across both) | do not look for a child Contact; treat the person record as both; expect merge and SOQL to behave differently than business accounts |
| **Record types** | one stage/picklist set exists | picklist values, layout, and process differ per record type | check the record type before assuming a stage or field is available |
| **Multi-currency org** | Amount is directly comparable | Amount is in the record's currency, converted at a dated rate | compare in a common currency; a flagged variance can be an FX difference |
| **Queue-owned record** | a user owns it | a queue (shared) owns the lead/case until someone accepts it | route by queue assignment, not user ownership |
| **Territory / team selling** | owner is the only access path | teams and territories grant additional access | do not infer visibility from ownership alone |
| **Sandbox vs production** | one org | a sandbox is a separate copy; data and IDs differ | confirm which org you are acting in before any write |
| **Duplicate / matching rules** | create always succeeds | a create can be blocked or allowed-with-warning as a duplicate | resolve via the intended record; a merge is the cleanup (destructive) |

## Reconciliation & freshness
- State drifts under you: stage, owner, approval lock, and sharing all change. Re-read the live record at
  execute, not the value you cached.
- A report or list view is not ground truth for what exists. Sharing and FLS can hide rows and fields from the
  running user, so "N records" may be a filtered subset.
- Automation may still be running. Async, scheduled, and time-based paths act after the save, so a record can
  change moments or days later; verify the end state rather than trusting the save moment.

## Recovery patterns (can it be undone, and what cannot)

| Action | Undoable? | How / what cannot be restored |
|---|---|---|
| **Record delete** | yes, for 15 days | undelete from the Recycle Bin; after the window or a hardDelete, restore from a backup, not an undo |
| **Lead conversion** | no standard un-convert | delete the created Account/Contact/Opportunity by hand and recreate the Lead; the mapping is lost |
| **Merge** | no unmerge | restore the losing records from backup and re-key children; conflicting field values are gone |
| **OWD / role / sharing change** | yes, by re-setting config | recalculation is org-wide and takes time; data exposed in the meantime may already have been read or exported |
| **Approval lock** | recall or admin-unlock | both bypass the intended review; treat as an authority action, not routine |
| **Order activation** | no edit of an activated order | correct through a reduction/amendment order |
| **Wrong stage / forecast** | reset the field | resetting does not undo automation that already fired (order created, email sent) |
| **User deactivation** | reactivate if a license is free | records still owned by the (once) inactive user are not auto-reassigned; reassign them explicitly |

After an unintended cascade, the forensic tools are **Field History Tracking** (per-object, shows old/new
values on tracked fields) and the **Setup Audit Trail** (config changes: OWD, sharing, automation, profiles).
Use them to reconstruct what fired and what changed before deciding a recovery; neither undoes anything.

## Guardrails
- Read the record plus its wired automation, approval lock, sharing, and stage state before acting; re-read at execute.
- Never lower OWD, change the role hierarchy, or delete a sharing rule to grant access for one task - it is an
  org-wide recalculation, not a per-record grant. Route the access need to the admin.
- A record under approval is locked for a reason; do not admin-unlock or recall it to push an edit through.
- Treat a stage change to Closed Won, a lead conversion, an order activation, and a case close as committing -
  each fires automation that reaches the ledger, fulfillment, or the customer. Size the effect before saving.
- Exporting or bulk-reporting customer PII off-platform is an egress event; require authorization even though
  it changes no Salesforce state.
- Confirm which org you are in (sandbox vs production) before any write; a sandbox is a separate copy with
  different data and IDs, and acting in the wrong one is a silent error.
- For anything in the destructive row (merge, mass delete, cascade delete, user deactivation, automation
  deploy, sharing change): named approver, re-read of live state, a logged reason, and prefer a reversible alternative.

## References (load on demand)
- `references/sharing-and-security.md` - how record access is computed (OWD, role hierarchy, sharing rules,
  manual/Apex shares, teams/territories) and what a change recalculates; profiles vs permission sets and
  field-level security. Read when a task touches ownership, visibility, or a sharing/OWD change.
- `references/automation-and-cpq.md` - the order of execution for validation, workflow, Flow, and Apex
  triggers and their side effects; CPQ configuration, pricing, quote sync, and approvals; price book mechanics.
  Read when an edit may fire automation, or a workflow touches CPQ quotes, orders-from-quotes, or pricing.
