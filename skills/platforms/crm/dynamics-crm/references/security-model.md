# Dynamics 365 CE (Dataverse) - security model

How Dataverse decides who can see and change a row, and what a change to that model recalculates. Read when a
task touches ownership, visibility, a security-role or business-unit change, record sharing, or column access.
The point: access is computed from a business-unit hierarchy plus role privileges scoped by an access-level
depth, so a single role or BU change can move access for many rows at once - it is org-wide plumbing, not a
per-record switch. This is structurally different from Salesforce OWD + role hierarchy + sharing rules.

## Contents
- The access layers (how visibility is computed)
- Business units
- Security roles: privileges and access levels
- Owner: user vs team; owner team vs access team
- Record sharing (the scoped grant)
- Column (field-level) security
- What a change recalculates (blast radius)

## The access layers (how visibility is computed)
A user's effective access to a row is the widest grant from these, evaluated together:
1. **Security roles** - the union of every role assigned to the user (directly or via a team). A role grants
   privileges per table at an access-level depth. No privilege on a table = no access, regardless of anything else.
2. **Business unit** - the role's access level (User/BU/Parent-Child/Org) is measured relative to the owner's
   business unit, so where the row is owned matters as much as the role.
3. **Ownership** - a row is owned by a user or an owner team; the owner's BU anchors the depth calculation.
4. **Record shares** - explicit per-row grants (from Assign/Share) on top of the role model.
5. **Access team membership** - privileges granted on a single row through an access team.
Column (field) security then filters *which columns* of a visible row the user can read or edit.

## Business units
- A **business unit (BU)** is a hierarchical container that owns users and (indirectly) rows. Every environment
  has a root BU; child BUs form a tree.
- Access levels are measured against this tree: a **Business Unit** access level sees rows owned in the user's
  own BU; **Parent-Child** sees the user's BU and its descendants; **Organization** sees all.
- **Moving a user or a row to another BU re-computes access** - the user's BU-scoped roles now resolve against
  a different branch, so they gain and lose visibility in bulk. A BU move is an org-structure change, not an edit.

## Security roles: privileges and access levels
- A **privilege** is a verb on a table: Create, Read, Write, Delete, Append, AppendTo, Assign, Share (plus
  process/system privileges like Bulk Delete, Export to Excel).
- Each privilege is granted at an **access level (depth)**: **None** (no access), **User** (own + shared rows),
  **Business Unit**, **Parent-Child Business Unit**, **Organization** (all rows). Wider depth = broader reach.
- A user's effective privilege is the **maximum** depth across all their roles - roles only add access, never
  subtract. So adding a role can silently widen reach; there is no "deny" role.
- Consequence: widening a role from User to Business Unit or Organization on a table exposes every row at that
  depth to every user holding the role. That is an org-wide exposure, not a targeted grant.

## Owner: user vs team; owner team vs access team
- A row is **owned** by a user or an **owner team**. Ownership anchors the BU-depth calculation.
- **Owner team** - owns rows directly; members inherit the team's roles and access to team-owned rows.
- **Access team** - does **not** own rows; it grants a specific set of privileges on a *single* row to its
  members (via an access team template). Lower blast radius, scoped to the row.
- **Assign** (owner change) moves the row's BU anchor to the new owner's BU, recomputing who sees it, and can
  fire assignment automation. Reassigning across BUs is a visibility change, not a cosmetic field edit.

## Record sharing (the scoped grant)
- **Share** grants named privileges (Read/Write/Delete/Append/AppendTo/Assign/Share) on a single row to a user
  or team, on top of the role model. It is the reversible, scoped way to give one person access to one row.
- A share is additive and does not change ownership. A broad share (to a large team) leaks the row widely;
  **revoking a share does not recall what was already read or exported** while it was shared.
- Prefer a scoped share over widening a role or lowering a BU boundary when the need is one row for one person.

## Column (field-level) security
- A **field security profile** controls read / update / create on individual secured columns (e.g. a PII field,
  a margin, a bank detail), independent of table-level privileges.
- A secured column is **masked**, not absent: a blank value may be hidden by the profile, not empty. The mask
  applies over the **Web API** too, so an export run without the profile silently omits the column.
- Granting or widening a field security profile exposes previously masked data; treat it as a data-exposure change.

## What a change recalculates (blast radius)
| Change | Recalculates / affects | Risk |
|---|---|---|
| Widen a role's access level (User -> BU -> Org) | every row at that depth for every user with the role | broad data exposure |
| Add a role to a user or team | that user's / team members' access | silent widening; roles only add |
| Move a user to another BU | all rows the user's BU-scoped roles resolve against | bulk gain/loss of visibility |
| Move a row to another BU | who can see that row | different branch sees it |
| Assign (change owner) | that row's visibility, via the new owner's BU | different users see/lose it; automation may fire |
| Share / unshare a row | that one row | scoped; unshare does not recall prior reads/exports |
| Grant a field security profile | the secured columns for those users | previously masked PII/margin becomes visible |

Gating note: any security-role, access-level, or business-unit change is destructive-class by blast radius
(org-wide, recomputes access, exposes/hides data) - it needs a named approver and a re-read, and is not the
way to grant one person access for one task. A per-row **share** is the reversible, scoped alternative.
