# Orchestration & payments (Fluent Order Management)

Read when a task turns on **how** Fluent runs a lifecycle (the Rubix rules engine and events), on changing a
workflow / ruleset, or on **money** (authorize / capture / refund / appeasement). SKILL.md carries the
judgment and the read/write/destructive matrix; this file carries the mechanics.

## Contents
- The Rubix workflow framework (entity / workflow / state / ruleset / rule)
- Orchestration events (external / internal, statuses, limits, retry)
- Rule action kinds (Mutate / SendEvent / Webhook / Log)
- Ruleset versioning and deployment blast radius
- Idempotency and concurrency
- The payment lifecycle (FinancialTransaction / Payment / PaymentTransaction)
- Returns, exchanges, appeasements

## The Rubix workflow framework
**Rubix** is the Fluent Orchestration Engine. Every entity type (Order, Fulfilment, Inventory, Payment, Return,
...) has a **workflow**: a set of **phases -> states**, **rulesets**, **triggers**, and user actions. Nothing
in Fluent moves except through a ruleset firing on an event.
- **Workflow** - the state machine for one entity type, scoped to a **Retailer**. The default Order workflow:
  Booking -> Fulfilment -> Delivery -> Complete.
- **State / status** - where the entity sits (Booked, Pick & Pack, Awaiting Collection, Complete, Cancelled,
  Escalated). A transition moves it and usually raises an internal event.
- **Ruleset** - the ordered list of **rules** that run when a matching **orchestration event** arrives.
- **Rule** - the smallest unit; its `run` method does one small task and returns **actions**. Standard rules
  ship in the platform; custom rules are authored with the Rules SDK.

## Orchestration events
An **orchestration event** is the message that triggers a ruleset (its name matches a ruleset name; it targets
an entity and can carry attributes). Two kinds:
- **External event** - raised from outside a workflow (an API/Event-API call, a user action, an integration) to
  start a ruleset.
- **Internal event** - raised inside a workflow to run another ruleset, inline or **scheduled** (future-dated,
  e.g. "release the reservation at pickup expiry").

Event facts that bite:
- **Statuses**: PENDING, NO_MATCH, FAILED, SUCCESS, SCHEDULED, COMPLETE. A **PENDING** event has not been
  processed; **NO_MATCH** means no ruleset matched; **FAILED** means the ruleset erred. A "stuck" entity is
  often an event stuck here, not a logic bug - check event status first.
- **Size cap 25KB** - an oversized payload stays PENDING and never processes.
- **Inline cap 100** - a rule chain that fans out beyond 100 inline events per execution context breaks.
- **Execution timeout** - if execution exceeds the timeout (typically ~4 minutes; verify per tenant) the engine
  assumes failure and **re-queues** the event, but the original execution is **not terminated** and keeps
  running. That is the source of double-execution (see idempotency).
- **No exact-timing guarantee** - because the platform is distributed, an external event is not guaranteed to
  process at the instant it is raised.
- **Audit events** - Rubix emits audit events on the back of each orchestration event (snapshot, ruleSet, rule,
  ACTION, CUSTOM, exception), each linked via `sourceEvents`. This is the read trail for "what did the rules do".

## Rule action kinds
A rule returns actions; classify by blast radius, not by name:
- **MutateAction** - creates or updates an entity (write). A replayed mutate can double-write.
- **SendEventAction** - raises another event (inline, another workflow, or scheduled). Fans out orchestration.
- **WebhookAction** - calls an external endpoint (carrier, WMS, payment gateway). **This commits in the outside
  world** - a re-fire double-books unless the endpoint is idempotent.
- **LogAction** - writes a custom audit event (read-only trail).

These are the *kinds* of write Fluent performs internally; the harness maps the customer's real connector onto
this judgment. Do not treat action names as callable connector operations.

## Ruleset versioning and deployment blast radius
Workflows and rulesets are **versioned config** deployed to a Retailer. A deploy is Fluent's highest-blast
operation:
- A changed rule, state, or transition applies to **every** entity of that type - all future entities and every
  **in-flight** one.
- An in-flight entity mid-workflow can **strand** on a removed state, skip a step, or take a new path it was not
  designed for.
- A sourcing / Fulfilment-Options change re-routes every future order.
- Rollback is **not retroactive**: reverting to the prior version stops new damage, but entities that already
  transitioned under the bad version stay changed and need manual correction.

Rule: author and test in a **sandbox / non-live retailer**, deploy deliberately, and treat a live deploy as
destructive-tier config with a named approver. Editing config in the wrong Retailer or account-wide scope hits
the wrong brand.

## Idempotency and concurrency
Because delivery is **at-least-once** and the 4-minute timeout re-queues an event while the original still
runs, the same logical action can execute more than once. Consequences and the rule:
- A duplicated **book** double-writes the RESERVED IQ (double reservation).
- A duplicated **capture** charges twice.
- A duplicated **WebhookAction** double-books the carrier / WMS / gateway.
- **The rule:** never blind-retry a book or capture. Read the entity state, the event status, and (for money)
  the gateway state, and use that as the idempotency check before re-sending. A stable idempotency key on
  external calls is what turns at-least-once into effectively once.
- Concurrent events on the same entity race; rely on Fluent's entity versioning / event ordering rather than
  firing overlapping mutates, and re-read state at execute.

## The payment lifecycle
Fluent orchestrates payment through the workflow via a payment connector; it is not the processor. Entities:
- **FinancialTransaction** - a pool of funds available to pay for an order (one per tender).
- **Payment** - captures or refunds part or all of a FinancialTransaction.
- **PaymentTransaction** - the log of each attempt (authorize, capture, refund, void) and its gateway result.
- Monetary fields use `preciseAmount` (BigDecimal) - do not do money math in floats.

Flow (all **rule-driven**, so the exact points are whatever the retailer's payment ruleset says):
- **Authorization** - usually at booking; a hold on funds, not a charge. Auths **expire** (issuer-dependent,
  commonly days) - a long backorder/pre-order must re-authorize before capture.
- **Capture / settlement** - usually **fulfilment-driven** (on ship); money actually moves. A **partial**
  fulfilment captures only its shipped lines, so money can have moved before the order is fully shipped.
- **Void / auth reversal** - releases an unused hold; the clean path on a cancel **before** capture.
- **Refund** - a new Payment against the FinancialTransaction after capture; money out, fees may not return,
  some tenders refund on a different path. Not an undo.
- **Multi-tender** - one order across several FinancialTransactions (card + gift card + loyalty); each
  authorizes, captures, and **refunds on its own path**.
- **Gateway is the source of truth** for authorized / captured / refunded. On any ambiguity
  (authorized-not-captured, a timeout, a failed status update) reconcile from the gateway; never re-capture to
  "fix" a gap (double-charge). Capture / refund reconcile onward to the ERP / AR ledger
  (`sap-mm` / `oracle-erp`).

## Returns, exchanges, appeasements
- **Return Order / Return Fulfilment** - can exist **only after** the original order is fulfilled. A return
  refunds the customer and, on **disposition to sellable**, writes a RETURNED IQ that re-injects stock into
  ATS. Refunding before the unit is received and inspected pays out on damaged or never-returned goods.
- **Exchange** - a Return plus a new Order. An **advance exchange** ships the replacement before the original
  comes back, so it authorizes / captures a **second** time and risks the return never arriving - two financial
  events, gate it like a refund and track the outstanding return.
- **Appeasement / credit memo** - a goodwill concession; real money out, revenue down, auditable, and not
  clawable once issued. Splitting a large appeasement into smaller ones to slip under an approval threshold is
  the same act with extra steps.
