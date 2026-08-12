# Icertis - obligations, associations, renewals, termination

What happens after execution: how obligations and commitments are tracked, how amendments/renewals/SOWs
associate to a parent, how terms inherit down a family, and the renewal, expiry, and termination mechanics.
Read when a workflow manages obligations, amends or renews an agreement, or terminates one.

## Contents
- Obligations: creation, ownership, milestones, breach
- Commitments (financial obligations)
- Associations: the child-agreement types
- Master-child hierarchy and term inheritance
- Renewal, expiry, and auto-renewal
- Termination

## Obligations: creation, ownership, milestones, breach
- An **obligation** is a tracked post-signature commitment: a delivery, an SLA, a rebate, a payment term, a
  reporting duty. The rules engine creates obligations from the executed agreement's terms and attributes.
- Each obligation has an **owner**, a **due date or milestone**, and a **status**: open -> fulfilled, or
  breached if the date passes unmet. It does not self-fulfill; an owner must mark it done, ideally with evidence.
- **Reassigning the owner does not reset the due date.** The clock keeps running through a handoff, so a
  reassignment that drops the ball leaves the obligation unmonitored until it breaches.
- **Marking an obligation fulfilled without evidence** to clear an alert is a workaround: the alert is a
  symptom, the unmet duty is the exposure. A false "fulfilled" can release a downstream action (a payment, a
  closed milestone) that is its own recovery problem.
- At renewal, obligations may reset (see below); do not assume last term's obligations carry forward.

## Commitments (financial obligations)
- A **commitment** is a financial obligation: the contract value, a spend or revenue commitment, a
  take-or-pay floor, or a minimum-volume band. It drives spend/revenue tracking and penalty exposure.
- A wrong contract value mis-states the commitment. Understating it can hide a take-or-pay penalty;
  overstating it over-counts spend or revenue. The value attribute is a financial control, not a label.
- Buy-side commitments typically sync to the procurement suite (Ariba/Coupa) and the ERP; the PO and invoice
  live there, not here. This skill governs the commitment; `coupa` / `sap-ariba` and
  `sap-fi` handle the transaction and the ledger.

## Associations: the child-agreement types
An **association** is a child object bound to a parent agreement. The common types:
- **Amendment** - modifies an executed agreement. It does not replace the parent; the effective terms are the
  parent as changed. A binding instrument with its own approval and signature.
- **Renewal** - extends the agreement into a new term. Terms (price, volume, SLA) may change.
- **Extension** - a shorter prolongation of the current term, usually without re-opening terms.
- **Termination letter** - ends the agreement; a notice-bound legal act.
- **Change order** - adjusts scope/price on an operational agreement.
- **SOW (statement of work)** - a work order under a governing MSA; it inherits the MSA's terms.
Reading the parent without its associations, or a child without its parent, misses the live legal picture.

## Master-child hierarchy and term inheritance
- An **MSA (master agreement)** governs its children (SOWs, change orders). The child inherits the MSA's
  liability cap, penalties, governing law, and termination terms unless the child explicitly overrides them.
- Reasoning about what binds means reading the whole family. A SOW that looks low-risk on its own can carry
  the MSA's uncapped liability or a penalty clause; the obligation lives across the hierarchy.
- An amendment to the MSA can change terms for every child under it; size the blast radius before amending a master.

## Renewal, expiry, and auto-renewal
- **Expiration date** is an attribute that arms the renewal and expiry clocks. When the term ends without
  renewal, the agreement expires and its rights and obligations lapse.
- **Auto-renewal / evergreen** clauses renew the agreement for another term automatically **unless notice is
  given inside the notice window**, which counts back from expiration (commonly 60 or 90 days). Miss the
  window and the renewal is legally locked in; there is no system undo, only a negotiation or a termination.
- A **manual renewal** requires an affirmative renewal association before expiry; letting it lapse ends the
  contract rather than renewing it. Know which regime a contract is under - the failure modes are opposite.
- Track the **notice window**, not just the expiration date. The date the decision must be made is earlier
  than the expiration by the notice period.
- At renewal, re-read the renewed agreement's obligations. Pricing, volume commitments, and SLAs can reset;
  copying the prior term's obligations mis-tracks the new one.

## Termination
- Terminating an executed contract is a **notice-bound legal act**, not a delete. It is recorded as a
  termination association and leaves the original in the trail.
- **For convenience vs for cause** differ: convenience usually needs a longer notice and may carry a penalty;
  for cause needs a documented breach and a cure period. Terminating on the wrong basis, or without the
  contractual notice, can itself breach the contract you are ending.
- There is no clean un-terminate. Reinstatement (if the contract allows it) or a new agreement is the path,
  not an undo. Confirm the basis, the notice period, and any survival clauses before terminating.
