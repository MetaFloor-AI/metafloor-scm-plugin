# Ivalua configuration and the unified data model

Read when a task depends on the client's config, changes it, or touches a custom object/status. The rule
under all of it: Ivalua is configured no-code per client, so behavior is not implied by the object type -
read the live config, and treat a config change as a fleet-wide control change.

## Contents
- Why config is the first thing to check
- What is configurable (the surface)
- Default-up rules
- Config change = fleet-wide control change
- The unified data model and the Golden Record
- Multi-entity authority
- Intake Management

## Why config is the first thing to check
Ivalua's differentiator from Ariba/Coupa/JAGGAER is a **single code base + one unified data model**,
configured **no-code/low-code** for each client. That flexibility means there is no single "standard" flow:
one client's requisition clears in one step, another's runs budget + risk + export checks. You cannot infer
the approval chain, the matching tolerance, or even an object's status list from the object type. Read the
**live workflow, tolerance, and status config** for the object in front of you before you classify or act.

## What is configurable (the surface)
- **Orchestration workflows** - the approval chains: steps, order, routing rules (amount, commodity, cost
  object, supplier, entity), escalation, delegation. Client-defined; dynamic on the data.
- **Object lifecycles and statuses** - a client can add statuses and even object types beyond the defaults.
- **Forms and fields** - which fields exist, which are mandatory, which trigger a re-route when changed.
- **Validation rules** - blocking vs warning checks on a document (budget, contract, risk, hazmat).
- **Matching tolerances** - the price/quantity variance bands under which smart matching auto-clears.
- **Smart-matching rules** - how a non-PO invoice auto-matches to a contract/receipt and how it auto-assigns
  budget/cost center/account.
- **Catalog and search scope** - which hosted/punchout catalogs Search 360 spans.

## Default-up rules
- **Zero-step workflow is not a green light.** If a client configured no approval step for an object/amount,
  that is an ungated commit, not approval. Escalate to destructive-tier (named approver + re-read).
- **Unclassifiable = destructive-tier.** If a custom or client-configured object/status/action does not map
  to the read/write/destructive matrix, default it **up**. Defaulting up is safe; defaulting down sends money on a guess.

## Config change = fleet-wide control change
Editing a no-code workflow route, a tolerance band, a validation rule, or a lifecycle is **not** a setting
tweak. It re-gates every future transaction that flows through it: raising a tolerance auto-passes future
variances; removing a step un-gates future approvals; loosening a validation rule lets future documents
through. Treat any config edit as destructive-tier: named approver + a sample re-check of what the change now
lets through. A config change can also apply to **in-flight** objects - re-read an in-progress object's live
config before acting on it, do not rely on the state you read before the change.

Loosening a config rule to slip one specific transaction through is circumvention, the same violation as
force-approving - route it to the real approver instead.

## The unified data model and the Golden Record
Supplier, contract, spend, and transaction records share one model, so a change in one place ripples. The
**Golden Record** is the single master supplier profile the whole platform trusts. Editing or deactivating a
supplier's Golden Record status flows into sourcing eligibility, contract validity, and whether open
POs/invoices can process - it is never a local edit to one screen. Activating a supplier's Golden Record is a
governance write that can unblock spend across every module.

## Multi-entity authority
A deployment can hold several legal entities/business units, each with its own workflow, cost objects,
compliance rules, and tolerances. Authority in one entity does not carry to another: cross-entity coding on a
requisition re-routes it to *that* entity's workflow, and an approver in entity A cannot clear spend in
entity B. Coding across entities to reach a friendlier approver is circumvention.

## Intake Management
An **intake form** is the front-door request that spawns a downstream orchestration workflow (a requisition,
a sourcing event, a supplier onboarding). Submitting the intake form is usually **not** the commit; the
downstream object it creates is what commits. But a mis-configured intake can auto-create a committing object
with no human in between - verify what the intake is configured to spawn before treating it as a harmless form.
