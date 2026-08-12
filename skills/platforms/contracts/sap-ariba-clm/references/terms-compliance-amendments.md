# SAP Ariba Contracts - terms, line items, compliance, hierarchy, amendments

The metadata and money side of a contract workspace: the Contract Terms fields and term types, the priced line
items and the compliance accumulator, the master/sub hierarchy and term inheritance, and the amendment types
with renewal, expiration, and termination mechanics. Read when a workflow sets terms/line items, amends, renews,
or terminates.

## Contents
- Contract Terms fields
- Term types and how a contract ends
- Contract line items and the compliance accumulator
- Contract hierarchy and term inheritance
- Amendment types and versioning
- Renewal, expiration, and termination

## Contract Terms fields
The Contract Terms document holds the metadata the rest of the system reads. The fields that arm a clock or a
control:
- **Contract type** - procurement (buy-side), sales (sell-side), or internal (no counterparty). Drives the
  template conditions, the approval chain, and which downstream system it syncs to.
- **Contract amount** - the value ceiling the compliance accumulator meters against. Understating it blocks valid
  releases; overstating it removes the ceiling that stops over-release. A control, not a label. Some localizations
  label this field Contract Value or Total Contract Value - the same control under a different name.
- **Effective date** - when the contract legally starts. Compliance and obligation windows key off this, not the
  publish or signature date. Back-dating it shifts every downstream clock.
- **Expiration date** - arms the expiration notifications and the renewal decision. A wrong date mis-times every
  alert.
- **Term type** - how the contract ends (below).
- **Hierarchy (parent)** - the master this workspace is a sub-agreement of, if any.
- **Supplier / customer, region, commodity** - read by the template conditions to select clauses and route
  approvals.

## Term types and how a contract ends
The **term type** on the Contract Terms decides the ending, and the failure modes are opposite - know which
regime a contract is under:
- **Fixed** - expires on the expiration date. Letting it lapse ends the contract.
- **Auto Renew** - renews for a set number of terms **unless notice is given inside the notice window**, which
  counts back from expiration. Miss the window and the renewal is legally locked in.
- **Evergreen** - renews indefinitely until someone terminates it. It does not expire on its own; the risk is a
  contract that keeps renewing unnoticed.
- **Perpetual** - no expiration. Term-type options are tenant-configured; some tenants expose Perpetual, others
  model an indefinite contract as Evergreen with no expiry date. Do not assert a value the tenant does not expose.
- Setting the wrong term type silently renews a contract you meant to expire, or expires one you meant to keep.
  Track the **notice window**, not just the expiration date - the decision date is earlier than the date on the
  contract by the notice period.

## Contract line items and the compliance accumulator
- **Contract line items** are the priced rows on a procurement contract (item, price, quantity, unit, terms).
- Publishing the workspace pushes the line items into **contract compliance** as the released contract that
  requisitions and POs can reference. The **accumulator** meters spend released against the contract up to the
  contract amount.
- Publish wrong prices, quantities, or a wrong contract amount and spend releases against wrong terms. The
  consumption of the accumulator (requisitions/POs releasing against it) lives in `sap-ariba`; the
  ceiling and the line-item terms are set here.
- A contract with no priced line items is text-only for compliance - the accumulator only meters when priced
  line items are published. If spend should be metered, the line items must be published, not just the agreement.
- **Standalone vs integrated** - the push of line items/compliance to the ERP happens only when Ariba Contracts
  is integrated with the back-end ERP. In a standalone deployment, publish activates the contract in Ariba but
  does not sync line items to an ERP. Confirm the integration before assuming a downstream push occurred.

## Contract hierarchy and term inheritance
- A workspace can be a **master** or a **sub-agreement** under a master. The sub inherits the master's terms -
  liability cap, penalties, governing law, termination terms - unless it explicitly overrides them.
- Reasoning about what binds means reading the whole family. A sub that looks low-risk on its own can carry the
  master's uncapped liability or a penalty clause; the obligation lives across the hierarchy.
- An amendment to the master can change terms for every sub under it. Size the blast radius before amending a
  master.

## Amendment types and versioning
A published workspace is not edited in place. Any change opens a new **version** (1.0 -> 1.1 -> 2.0) through an
**amendment**, and the amendment **type** sets what re-routes:
- **Administrative** - metadata or team changes that do not change contract terms; usually no re-signature. Do
  not use it to slip a real term or price change past re-approval and re-signature - that is circumvention.
- **Amendment** - changes the terms; re-routes approval and signature.
- **Renewal** - extends the expiration into a new term; terms (price, volume, SLA) can change, so re-read the
  renewed line items rather than assuming the prior term carries forward.
- **Termination** - ends the active contract (below).
- **Version history is permanent.** You cannot delete a version; a wrong publish is corrected by a new amendment,
  not by editing or removing a version. Both the original and the amendment stay in the trail.
- A **publish or ERP sync can fail** after the amendment publishes but before confirmation. Re-read the live
  status, version, and publish state before retrying; a blind retry can double-publish or double-push line items.
  The confirmed published record is the source of truth.

## Renewal, expiration, and termination
- **Expiration** - the expiration date arms the notifications and, for Fixed contracts, ends the term. Ariba
  fires expiration notifications to the owner at configured intervals ahead of the date.
- **Renewal** - Auto Renew and Evergreen renew automatically per the term type; a manual renewal requires an
  affirmative Renewal amendment before expiry. At renewal, re-read the renewed line items and terms - pricing,
  volume commitments, and SLAs can reset; copying the prior term mis-tracks the new one.
- **Auto-renewal notice window** - the window to give notice counts back from expiration. Miss it on an Auto
  Renew/Evergreen and the new term is legally in effect; recovery is a negotiation or a Termination, not a system
  undo.
- **Termination** - done through a Termination amendment; a notice-bound legal act, not a delete. It ends the
  contract and stops compliance releases, but the workspace and versions stay in the trail. Termination for
  convenience vs for cause differ (convenience usually needs a longer notice and may carry a penalty; for cause
  needs a documented breach and often a cure period). Terminating on the wrong basis or without the contractual
  notice can itself breach the contract you are ending. There is no clean un-terminate - reinstatement (if the
  contract allows) or a new workspace is the path.
- **In-flight spend is not unwound by termination or a line-item amendment.** Terminating a contract or amending
  its line items stops new releases against the compliance accumulator, but requisitions and POs already released
  (committed, received but not invoiced, or invoiced but not paid) continue their own lifecycle in the spend
  suite (`sap-ariba`) and the ERP. Size that in-flight exposure before terminating or re-pricing.
