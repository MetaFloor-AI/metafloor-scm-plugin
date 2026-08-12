# Coupa - approval-chain routing and contract-backed pricing

How Coupa decides who must approve a requisition/invoice and how a contract governs price. Read when a
workflow re-routes approvals, hits a delegate or escalation, or touches a contract-priced line.

## Contents
- What routes an approval chain
- Delegation, escalation, force-approve
- Contract-backed pricing: block vs flag, the amendment path

## What routes an approval chain
- Coupa builds the chain from **approval rules** evaluated against the document. The main inputs: **amount**
  (approval-by-amount tiers), **account coding** (cost center, GL account, project), **commodity** (UNSPSC
  category), supplier, and **budget** status.
- Because coding drives routing, changing a line's cost center, account, or commodity re-evaluates the rules
  and can send the document to a **different** set of approvers. An edit to coding is an approval re-route.
- Approval-by-amount checks **total** spend on the document. Splitting one need into two smaller documents to
  drop each below a tier is circumvention, and it is auditable; it does not change the required authority.
- A chain is sequential: each approver in turn. Adding an approver or a watcher does not advance the chain;
  only an approve/reject/return decision moves it. A comment is not an approval.
- Re-read the approval state at execute. An in-flight edit, a delegation change, or a new rule can have
  re-routed the document since the last read.

## Delegation, escalation, force-approve
- **Delegation** - an approver hands their authority to a delegate (often out-of-office). The delegate approves
  in the original approver's name; it is a real authority transfer. An expired or mis-set delegation can stall
  the chain or route to the wrong person.
- **Escalation** - a pending approval past its SLA can escalate to the next authority. Escalation is a routing
  event, not an approval; the spend is still not committed until someone actually approves.
- **Force-approve / approve on behalf** - an admin with permission pushes the approval through, skipping the
  intended approvers. It is recorded (who forced it, when), but it bypasses the control. Treat it as an authority
  action requiring an explicit named approver and a logged reason, never a way to clear a queue.

## Contract-backed pricing: block vs flag, the amendment path
- A catalog line **backed by a contract** carries the contracted price and terms. The contract, not the
  requisition, is the source of truth for that price.
- Editing the price on a contract-backed line breaks compliance. Depending on configuration Coupa either
  **blocks** the change or **flags** it as off-contract for review; do not assume a flag means it was allowed.
- The correct way to change a contracted price is a **contract amendment**, which has its own approval and
  effective date. Overriding the price on the requisition line is not the amendment path and leaves a
  non-compliant, off-contract commitment.
- Contract compliance also covers quantity and term limits; a requisition that exceeds the contracted commitment
  can be blocked or flagged the same way. Check the contract state before pushing an off-contract line through.
