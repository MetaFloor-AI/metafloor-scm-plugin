# Oracle OTM - rating, domains, automation agents

Three things that decide whether a read is even meaningful and whether a write happens without you: how a
rate is looked up, how data is partitioned, and how agents auto-execute. Read when a workflow rates a move,
crosses business units, or runs under an automation agent.

## Contents
- Rating: rate offering, rate record, accessorial, rate geo
- Domains and grants
- Automation agents and their commit risk

## Rating: rate offering, rate record, accessorial, rate geo
- **Rate offering** - the contract-level container for a service provider: general terms, service, mode,
  effective dates. One offering holds many rate records.
- **Rate record** - the cost for service between locations (origin -> destination), the actual price bulk
  plan reads to pick the least-cost SP.
- **Accessorial cost** - contingency charges (fuel, detention, stop-offs) attached to an offering or record.
- **Rate geo / rate zone** - how OTM resolves an origin/destination to a rated geography; a wrong geo match
  returns a wrong rate.
- **Rating is a read** - a rate inquiry prices a move and commits nothing. But a rate is meaningless without
  its lane + SP + effective-date window: rating the wrong lane/SP/date returns a plausible but wrong number
  that then anchors the tender. Re-rate at execute if the plan snapshot is old.
- **Re-weigh / re-measure can jump a rate tier.** Weight-break (CWT) and volume-break rates change the
  *base* cost when the actual weight/volume crosses a bracket - e.g. 10,000 lbs planned that re-weighs at
  12,500 lbs lands in a higher bracket. This is a base-cost shift, distinct from an accessorial add-on, and
  an invoice tolerance check on the total may not catch it.
- Changing a rate record/offering to make a tender "fit" is re-pricing the contract - a committing sourcing
  change, and gaming it to drop under an approval threshold is an audit violation, not optimization.

## Domains and grants
- OTM partitions every object (orders, rates, SPs, shipments) into a **domain** - a tenant / business-unit
  boundary. Reads and writes are domain-scoped.
- A **grant** is what lets one domain see another's data. Without the right grant, a cross-domain read sees
  the wrong data or nothing, and a write can land in the wrong domain.
- Practical rule: confirm the domain before reading a rate/SP/order or writing a shipment. Data that "looks
  missing" is often just in another domain; acting on it blind mis-plans against the wrong tenant's setup.

## Automation agents and their commit risk
- An **automation agent** is an event/condition-driven workflow: a **saved condition** (or lifecycle event)
  triggers a chain of **agent actions**. It is how OTM runs hands-free.
- Agent actions can **auto-secure-resources, auto-tender, retender, auto-approve an invoice, issue a
  voucher, or publish events** - i.e. an agent can perform any committing or destructive action with no
  human in the loop.
- Consequence: an agent that tenders IS committing freight spend + capacity; an agent that approves invoices
  IS paying money. The autonomy risk is that the commit is buried inside a rule that fires on an event.
- Rule to teach: treat any automation agent whose action tenders, books, secures resources, or approves as a
  committing actor. It must be gated the same as a human doing that action - not exempted because "the agent
  did it". If the harness cannot see inside the agent, the safe read is that a tender/approve agent commits.
- What gating an agent actually looks like in OTM: insert a **hold / human-confirmation agent action**
  before the commit step (so the chain pauses for approval), or **remove the auto-tender / auto-approve
  action** from the agent template so the commit is done by a person through the gate. Disabling the whole
  agent is the blunt version. "Gate the agent" is not abstract - it is one of these concrete edits.

Gating note: rating and domain reads are reads; editing a rate/offering or a routing preference is a
committing sourcing change; an automation agent is classified by *what its action does*, not by being an
agent - a tender/approve agent is committing, a cancel/void agent is destructive.
