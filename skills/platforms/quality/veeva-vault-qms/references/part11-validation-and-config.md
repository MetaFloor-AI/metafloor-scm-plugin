# Veeva Vault QMS - Part 11, validation, config vs data, and document linkage

The controls that make Vault a validated GxP system and decide what an operator may and may not do. Read when
a task involves an e-signature, the audit trail, a configuration change, sandbox-to-production, record access,
or a linked controlled document.

## Contents
- Electronic signatures (21 CFR Part 11 / Annex 11)
- The immutable audit trail and ALCOA+
- Configuration vs data (and why it matters in production)
- Sandbox to production migration
- Roles, dynamic access control, atomic security
- Controlled-document (QualityDocs) linkage and version binding

## Electronic signatures (21 CFR Part 11 / Annex 11)
- Completing a signed workflow task captures the **signer's credentials**, a **signature meaning** (from a
  controlled picklist - Approved / Reviewed / Completed), and a **timestamp**, and **links** the signature to
  the specific record and version (Part 11 §11.70 signature-to-record linking; §11.50 signature manifestation).
- A signature is **permanent and attributable**: it cannot be removed or edited, and it appears on the
  record's audit trail and (for documents) the rendered signature page.
- **You never sign on another user's behalf and never share credentials.** The signature must be the act of
  the actual person; delegation routes the task, but the recorded signer is whoever signs. A wrong signer is
  not erasable - only correctable forward with a new signature or a documented correction.
- Treat a required signature as a **hard gate**: the step cannot complete without it, and forcing past it is a
  data-integrity violation, not a shortcut.

## The immutable audit trail and ALCOA+
- Vault records a **system-generated, immutable audit trail** of every field change, state change, and
  signature: **user + timestamp + old value + new value (+ change reason where required)**. Separate object,
  document, system (configuration), and login audit trails exist.
- It **cannot be edited or deleted**. A mistake is corrected by a **new entry** (a further edit, a corrective
  record, a follow-up report) - never by erasing the original. Every prior value stays visible to an inspector.
- **ALCOA+** is the data-integrity standard the trail supports: Attributable, Legible, Contemporaneous,
  Original, Accurate (+ Complete, Consistent, Enduring, Available). A placeholder change reason or a required
  field filled with junk to clear a gate violates Accurate/Attributable and is itself a finding.

## Configuration vs data (and why it matters in production)
- A **data** action creates or edits a **record** (a deviation, a CAPA field, a disposition) - normal operator
  work, gated per the read/write/destructive matrix.
- A **configuration** action changes **how the system behaves**: lifecycles, states and state types,
  workflows, object types, fields, picklist values, security/roles, page layouts. In a validated production
  vault this is a **computer-system change**.
- A production config change must go through the customer's **change control and validation**: assessed,
  built and tested in a **sandbox**, and migrated via a configuration package - **not hand-edited in
  production**. An unqualified prod config change breaks the validated state and is an inspection finding.
- An operator/agent acting on records **does not touch Admin configuration in production**. If a task seems to
  need a config change, that is a change-control request to the vault owner, not an action to perform.

## Sandbox to production migration
- **Sandbox** and **production** are separate vaults. Config is **built and tested in sandbox**, then migrated
  to production; **record data does not copy** between them.
- Migration uses a **configuration migration package (VPK)** or **Vault Compare/Deploy** (component-level
  metadata, MDL). This path is what keeps the production change traceable and validated.
- Consequence: a behavior confirmed in sandbox is **not** live until deployed; and records created while
  testing in sandbox are throwaway. Never report a sandbox result as a production state.

## Roles, dynamic access control, atomic security
- **Record roles** (Owner, Editor, Viewer, Approver, Coordinator) are assigned per record and drive **Dynamic
  Access Control (DAC)**: visibility and permissions follow **role on the record**, not a single global grant.
- Not being in a role on a record means you **cannot see or act on it** - "the record isn't there" is usually
  a sharing/role gap. Adding a user to a role changes who can act and is **logged**.
- **Atomic / field-level security** can gate an individual **field** or a specific **state-change action** for
  a role, even when the record is visible. A blocked required field or an unavailable state action is a
  permissions issue; the fix is the correct role, not another way in.

## Controlled-document (QualityDocs) linkage and version binding
- QMS records **reference** controlled documents (SOPs, specs, forms) managed as **documents** in QualityDocs,
  whose lifecycle runs **Draft -> In Review -> Approved -> Effective -> Periodic Review -> Superseded/Obsolete**.
  "Steady state" is **Effective**.
- A reference **binds to a version**. "The SOP" (latest Effective) and "SOP v3.0" (a pinned version) can
  diverge after a new publish; an implementation or verification pointed at the wrong version checks stale
  content. Read which the reference resolves to.
- Making a document **Effective** is a committing publish: it **supersedes** the prior version, can trigger
  **training assignments** and **periodic-review** clocks, and makes the old version non-current. References to
  the superseded version may need updating.
- **Obsoleting/retiring** an Effective document that open events still reference **breaks those links**;
  referential integrity and validation-state rules generally block it while referenced. In validated
  production, controlled documents and GxP records are **not deletable** by design - only voided/obsoleted
  through the defined path.
