# Salesforce - sharing model and security

How Salesforce decides who can see and change a record, and what a change to that model recalculates. Read
when a task touches record ownership, visibility, a sharing rule, an OWD change, or field access. The point:
sharing is computed from several layers stacked on a baseline, so a single change can move access for many
records at once - it is org-wide plumbing, not a per-record switch.

## Contents
- The access layers (how visibility is computed)
- Org-Wide Defaults (OWD) - the baseline
- Role hierarchy
- Sharing rules, manual shares, Apex sharing
- Teams and territories
- Profiles, permission sets, and field-level security
- What a change recalculates (blast radius)

## The access layers (how visibility is computed)
Access to a record is the *widest* grant from any of these, stacked bottom-up:
1. **Object permissions** (profile / permission set) - can this user touch this object at all (create, read,
   edit, delete)? No object permission means no access regardless of sharing.
2. **Org-Wide Defaults (OWD)** - the baseline record visibility for everyone.
3. **Role hierarchy** - grants managers access to records owned by people below them (if enabled for the object).
4. **Sharing rules** - open records to roles/groups by ownership or by criteria.
5. **Manual + Apex + team/territory shares** - one-off or programmatic grants on top.
Field-Level Security then filters *which fields* of a visible record the user can see or edit.

## Org-Wide Defaults (OWD) - the baseline
- Per object: **Private**, **Public Read Only**, or **Public Read/Write** (and Controlled by Parent for
  detail objects). This is the floor; the other layers only widen access above it, never below.
- **Private** means only the owner (and their role-hierarchy managers, and explicit shares) sees a record.
- Changing OWD triggers a **sharing recalculation across every record of that object** - it can take a while
  on large orgs and it exposes or hides data broadly. Lowering OWD (e.g. Private -> Public) is a data-exposure
  event; tightening it can cut off users who depended on the open default.

## Role hierarchy
- A tree of roles. People at a higher role implicitly see records owned by people below them, for objects
  where "Grant Access Using Hierarchies" is on.
- **Ownership + role together decide visibility.** Reassigning a record's owner moves it to a different branch
  of the tree, so a different set of managers now sees it and the previous branch may lose access.
- Restructuring the hierarchy (moving a role) recalculates sharing for all records under the moved branch.

## Sharing rules, manual shares, Apex sharing
- **Owner-based sharing rule** - records owned by role/group A are shared to role/group B.
- **Criteria-based sharing rule** - records matching a field condition are shared to a role/group.
- **Manual share** - a one-off grant on a single record (owner or admin).
- **Apex managed sharing** - programmatic shares maintained by code; deleting the code or the share can revoke
  access silently.
- Deleting or editing a sharing rule recalculates access for all records it touched - a broad rule change is a
  mass visibility change, not a local edit.

## Teams and territories
- **Account/Opportunity/Case teams** - named users granted access to a specific record with a role and access
  level, independent of ownership.
- **Enterprise Territory Management** - territories grant access to accounts (and their opportunities) by
  assignment rules; a record can be visible through a territory even when ownership would not grant it.
- Implication: ownership is not the only access path. Do not infer "only the owner can see this" from the owner field.

## Profiles, permission sets, and field-level security
- **Profile** - the base set of permissions a user has (object CRUD, admin rights, defaults). One profile per user.
- **Permission set / permission set group** - additive grants layered on the profile (extra objects, fields,
  system permissions) without changing the profile. The modern way to grant capability to a subset of users.
- **Field-Level Security (FLS)** - controls visibility/edit of individual fields per profile/permission set. A
  field can be readable to one profile and hidden to another. A blank field in a view or export may be **hidden
  by FLS, not empty** - and a report run by a restricted user silently omits masked fields.
- "View All" / "Modify All" object permissions and the "View All Data" / "Modify All Data" system permissions
  override sharing entirely; a user with them sees/edits everything on that object regardless of OWD. Treat
  granting them as a high-blast change.

## What a change recalculates (blast radius)
| Change | Recalculates | Risk |
|---|---|---|
| Lower OWD (Private -> Public) | all records of the object | broad data exposure; may already be read/exported before you revert |
| Raise OWD (Public -> Private) | all records of the object | users lose access they relied on; queues/reports go empty |
| Edit/delete a sharing rule | all records the rule touched | mass visibility swing |
| Move a role in the hierarchy | all records under that branch | managers gain/lose access in bulk |
| Reassign a record owner | that record | different branch sees it; assignment automation may fire |
| Grant View All / Modify All | every record of the object for that user/group | bypasses sharing entirely |

Gating note: any OWD, role-hierarchy, or sharing-rule change is destructive-class by blast radius (org-wide,
recalculates, exposes/hides data) - it needs a named approver and a re-read, and is not the way to grant one
person access for one task. A per-record manual share is the reversible, scoped alternative.
