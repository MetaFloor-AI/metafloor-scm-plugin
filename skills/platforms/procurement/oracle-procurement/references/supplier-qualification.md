# Oracle Supplier Management and Qualification

The supplier model and the qualification machinery that gate who you can source, order, and pay. Read when a
workflow onboards a supplier, promotes it to spend authorized, or relies on a qualification/assessment. The
rule under all of it: registration, qualification, and spend authorization are three independent gates, and
each is its own approved governance act.

## Contents
- The supplier record and its statuses
- Registration flow
- Prospective vs spend authorized
- Supplier Qualification Management (SQM)
- Assessments and initiatives
- Expiration and hold/inactive

## The supplier record and its statuses
A supplier is a party with a profile: addresses, **supplier sites** (per Procurement BU, they carry the
purchasing/pay terms), business classifications (e.g. diversity), products-and-services categories, bank
accounts, and contacts. Independent status axes that matter:
- **Registration / creation status** - how the supplier came to exist (internal or via registration).
- **Spend authorization** - prospective vs spend authorized (below).
- **Active / inactive / on hold** - whether the supplier can transact at all right now.
Reading only one axis misleads: "the supplier exists" says nothing about whether it can be ordered.

## Registration flow
- **Internal** - a buyer creates the supplier directly.
- **Supplier Registration** - external self-service (the supplier submits its own registration) or internal
  (someone registers on the supplier's behalf). A registration request routes for **approval** by its rules.
- Approval of a registration can create the supplier as **prospective** or **spend authorized** depending on
  the flow and how it was invited. Approved does not automatically mean spend authorized - read the resulting
  status, do not assume.

## Prospective vs spend authorized
- **Prospective supplier** - can participate in sourcing (be invited to and respond to negotiations) and be
  qualified, but cannot receive a purchase order or be paid. This lets you evaluate a supplier before
  committing money to it.
- **Spend authorized** - cleared to be ordered and paid. Getting there is a **spend authorization** request
  that routes for approval (its own gate). Promoting a supplier to spend authorized is committing: it unblocks
  money moving to that party.
- Consequence: awarding a negotiation to a prospective supplier does not let you create the PO until it is
  promoted. Ordering or paying a prospective supplier is blocked by design; forcing around it sends spend to an
  unauthorized party.

## Supplier Qualification Management (SQM)
- **Qualification area** - a defined topic to evaluate a supplier on (financial viability, quality
  certification, compliance, capacity). It groups the questions and defines the outcome model.
- **Question / question category** - the items asked, with acceptable responses and optional scoring.
  Questions live in a bank and are reused across areas.
- **Qualification** - an evaluation of a specific supplier (or supplier site/contact) for one qualification
  area. It carries an **outcome** (e.g. qualified / a level / not qualified) and an **expiration date**.
  States: draft/initiated -> responses received -> evaluated -> approved (finalized). Finalizing a
  qualification sets a status that can unblock sourcing or ordering, so it is a committing governance act - do
  not self-qualify a supplier to clear your own path.
- Qualification is **per area**, so "qualified" is only meaningful with the area named. A supplier qualified
  for one category is not qualified for another.

## Assessments and initiatives
- **Assessment** - rolls several qualifications into an overall standing for a supplier (for a segment or
  category). It reflects the underlying qualifications; a stale assessment can hide an expired qualification
  beneath it.
- **Initiative** - the launch vehicle: it creates qualifications/assessments in bulk and sends questionnaires
  to suppliers (via the Supplier Portal) and to internal responders. An initiative touches many suppliers at
  once, so read its scope before launching.

## Expiration and hold/inactive
- **Expiration** - a qualification lapses at its expiration date. Past it the supplier is no longer qualified
  for that area, even if an older read said "qualified". Re-read live status before relying on it; re-qualify
  (a new evaluation) rather than trusting the stale outcome.
- **On hold / inactive** - a hold or an inactive status stops transactions with the supplier. It was set for a
  reason (missing/invalid banking, failed sanctions or compliance screening, a dispute). Lifting it is a
  governance act with its owner; swapping in a different supplier or forcing the order through defeats the
  control. Re-activating is a new, logged action and does not erase what happened while the supplier was held.
