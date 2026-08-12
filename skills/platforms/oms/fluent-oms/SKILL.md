---
name: fluent-oms
description: "Fluent Order Management (Fluent Commerce) - safe operation of cloud, event-driven omnichannel order orchestration - order and fulfilment lifecycle run by the Rubix rules engine (workflows, rulesets, events), inventory and availability (Virtual Position / Catalogue, Available-to-Sell / ATP, Controls, Inventory Position / Quantity), sourcing (ship-from-store, DC, drop-ship vendor / DSV, click-and-collect), reservation, backorder, split fulfilment, payment (authorize / capture / refund), returns, exchanges, appeasements. Use when the OMS is Fluent Commerce (Fluent OMS) and the work touches committing or sourcing an order, ATS / ATP, releasing a fulfilment, a Rubix workflow / ruleset / event, ship-from-store or click-and-collect, an order / fraud / payment hold, a backorder, reserving inventory, a capture or refund, an appeasement, a return or exchange, event idempotency, Virtual Catalogue, or oversell. Not Manhattan Active Omni (that is manhattan-oms)."
---

# Fluent Order Management (OMS) - operating it safely

Fluent Order Management (Fluent Commerce, a cloud, API-first, event-driven OMS on AWS) runs omnichannel
**order orchestration**: it captures an order, decides across the network **whether** it can be promised and
**where** each part sources, reserves inventory, creates and releases a **Fulfilment** to each location, and
manages the money and the customer through returns, exchanges, and appeasements. It is the system of record
for the **order**, the **fulfilment plan**, and **network availability** - not for physical on-hand inside
any one building. Three facts make it dangerous. First, everything is orchestrated by the **Rubix rules
engine**: the order and fulfilment lifecycles are *your rulesets*, so a workflow or ruleset change is
orchestration-wide config, not a per-order tweak. Second, the platform is **event-driven with at-least-once
delivery** - the same rule action can run twice, so concurrency and idempotency decide whether a commit
double-reserves or a capture double-charges. Third, **booking an order reserves inventory** and authorizes
payment, and the acts that move money (**capture, refund, appeasement**) or touch the customer (**cancel,
oversell, releasing a fraud hold, deploying a ruleset**) cross a point of no clean return. This skill gives
the judgment to classify each action so the harness can gate it, plus the edge states and recovery paths
that decide if a mistake is fixable.

## Contents
- When this applies / when NOT (and Fluent vs Manhattan)
- Object & state model
- Vocabulary that bites
- Operations: read / write / destructive matrix
- Gotchas that bite (the causal chains)
- Edge states & special cases
- Freshness & reconciliation
- Recovery patterns
- Guardrails
- References

## When this applies / when NOT
The OMS is Fluent Commerce and the work is order capture, promising, sourcing, fulfilment orchestration,
payment, or returns across the network. When NOT:
- **Manhattan Active Omni** (ATC / ATP, the DOM engine, Active Omni store fulfilment) -> `manhattan-oms`.
  Same job, different product: Fluent orchestrates through the **Rubix rules engine and events**; Manhattan
  through its own DOM microservices. Do not apply Fluent's ruleset/event judgment to a Manhattan tenant.
- **Warehouse execution inside one location** - bins, waves, pick/pack/put-away tasks, on-hand counts and
  adjustments -> `manhattan-wms` or `sap-ewm`. Fluent *releases* a Fulfilment to a
  location; that location's WMS or the Fluent Store app does the physical pick and ship. Fluent decides
  where; the WMS does the how.
- **ERP order-to-cash, accounts receivable, revenue recognition, the ledger** -> `sap-mm` or
  `oracle-erp`. Fluent triggers invoicing and capture; it does not own AR or the GL.
- **CRM / the customer master as a sales system** -> `salesforce`. Fluent holds the order and the
  service around it, not the opportunity pipeline.

## Object & state model (reason about state, not nouns)
Fluent's model is a set of **entities**, each driven through a **workflow** (phases -> statuses) by Rubix
rulesets. Reason about the entity's state and which ruleset fires next, not the noun.
- **Account / Retailer / Network / Location** - an Account is one Fluent install; a Retailer is a brand/tenant
  with its own workflows and users; a Network is a named group of Locations; a Location is a store, DC, or
  vendor site. Config (workflows, Controls) is scoped to a Retailer - the wrong scope hits the wrong brand.
- **Order** - the customer's demand, created at checkout. Carries a **fulfilmentChoice** (home delivery vs
  click-and-collect, location, speed). Default workflow phases: **Booking -> Fulfilment -> Delivery ->
  Complete** (statuses seen: Booked, Pick & Pack, Awaiting Courier / Customer Collection, Complete, Cancelled).
  The order status is a roll-up - it hides per-fulfilment reality.
- **Fulfilment** - a **plan for stock movement** from a location to the customer, and a **separate entity with
  its own workflow**. One order splits into many fulfilments (DC + store + DSV), each assigned to a Location
  and each in its own state; a fulfilment that cannot be sourced goes to **Escalated**. This Order->many
  Fulfilments split is core Fluent: read fulfilment state, never just the order header.
- **Article / Consignment** - the **Article** is the physical parcel (parcel/bag/pallet) that carries items;
  the **Consignment** is its shipping information. These are Fluent's own entities for the physical ship.
- **Inventory Position / Inventory Quantity (IQ)** - a Position says stock exists for a SKU at a Location; the
  IQ is a **ledger** of every stock-affecting record (LAST_ON_HAND, SOFT_RESERVE, RESERVED, SALE, RETURNED,
  CORRECTION, DELTA), each ACTIVE or INACTIVE. **Stock on Hand = sum of ACTIVE IQ.** Details in
  `references/inventory-and-sourcing.md`.
- **Virtual Position / Virtual Catalogue / Controls** - the computed availability layer. A Virtual Position
  holds **Available-to-Sell (ATS)** for a channel; **base** is per-location, **aggregate** sums the network.
  **Controls / Control Groups** are the buffers and exclusions that hold stock back from ATS. ATP is the
  date-aware view. ATS is derived, never raw on-hand.
- **FinancialTransaction / Payment / PaymentTransaction** - a FinancialTransaction is the pool of funds for an
  order; a Payment captures or refunds part or all of it; a PaymentTransaction logs each attempt. Auth and
  capture are **rule-driven** (see gotcha 7).
- **Return Order / Return Fulfilment** - a return exists **only after the order is fulfilled**; it refunds and,
  on disposition to sellable, re-injects stock (a RETURNED IQ). An **exchange** is a return plus a new order.
- **Rubix workflow / ruleset / rule / orchestration event** - a workflow is states + rulesets + triggers for
  one entity type; a **ruleset** is the rules that fire on an **orchestration event**; a **rule** does one
  small task and emits actions (create/update an entity, send an event, call a webhook, log). Deploying a
  ruleset version changes orchestration for **every** entity of that type. See `references/orchestration-and-payments.md`.

## Vocabulary that bites
(Each term is glossed to its hazard here; the full causal chain is in Gotchas below.)
- **Rubix** - the Fluent Orchestration Engine. It is the rules engine that runs *every* lifecycle. "Change the
  order flow" means edit a ruleset, which is fleet-wide config, not a setting on one order.
- **Ruleset / rule / MutateAction / WebhookAction** - a ruleset fires on an event; a rule emits actions. A
  **MutateAction** writes an entity; a **WebhookAction** calls an external system (carrier, WMS, gateway). A
  re-run that re-fires either can double-write or double-book (idempotency, gotcha 5).
- **Orchestration event** - the message that triggers a ruleset. Statuses: PENDING, NO_MATCH, FAILED, SUCCESS,
  SCHEDULED, COMPLETE. Cap **25KB**; up to **100** inline events per execution context. A "stuck" order is
  often a PENDING/FAILED event, not a logic bug.
- **At-least-once delivery** - events can process more than once; a timeout (typically ~4 minutes; verify per
  tenant) re-queues an event while the original **keeps running**. Any book or capture can execute twice.
  Idempotency is not optional.
- **Available-to-Sell (ATS)** - the promisable quantity on a Virtual Position, `ATS = Inventory Position stock
  - Controls (buffers/exclusions) - other demand`. Not on-hand. Promising off raw on-hand oversells.
- **Inventory Quantity (IQ) ledger** - stock is a ledger, not a number. Booking writes a negative **RESERVED**
  IQ against the fulfilment; **Stock on Hand = sum of ACTIVE IQ**. Reading LAST_ON_HAND alone overstates.
- **SOFT_RESERVE vs RESERVED** - SOFT_RESERVE is a cart-time hold; RESERVED is the confirmed-order hold. Both
  reduce availability; a SOFT_RESERVE read as fulfillable over-promises.
- **Control / Control Group** - the safety buffer withheld from ATS (store floor stock, channel protection).
  Lowering it to fill more orders risks oversell; a live Control change re-promises the network.
- **Fulfilment (entity) vs fulfilmentChoice** - the choice is what the customer asked for; the Fulfilment is
  the created plan with its own workflow. One order -> many Fulfilments, each with its own status.
- **Dynamic Sourcing / Fulfilment Options / Fulfilment Plan** - the logic that ranks and picks Locations
  (inventory, proximity, lowest sell-through, oldest stock, markdown, capacity). It is a ruleset - editing it
  re-routes **all future** orders.
- **DSV (drop-ship vendor) / SFS (ship-from-store) / C&C (click-and-collect) / HD (home delivery)** - the
  fulfilment types. C&C ends in a **customer collection**, not a carrier shipment; DSV hands control to a
  third party.
- **Authorization vs capture** - auth **holds** funds; capture **moves** them. In Fluent both are driven by
  the payment ruleset (auth usually at booking, capture usually at ship) - the point is configurable, so read
  the ruleset, do not assume. Auths **expire**.
- **Appeasement / credit memo** - a goodwill credit; real money out, revenue down, auditable, not clawable.
- **Escalated (fulfilment)** - a fulfilment that could not be sourced by the rules. It is parked, not dropped;
  ignoring it leaves the customer promised but unfulfilled.

## Operations: read / write / destructive
Classify every operation family by what it does to inventory reservations, to money, to the customer, and to
**orchestration config**. Kinds of action, not tool/op names.

| Class | Fluent OMS operation families | Gate | Why |
|---|---|---|---|
| **Read** | order / fulfilment search, inquiry, timeline, audit events (snapshot / ruleSet / rule / exception); ATS / ATP and network availability by product or location (Virtual Position / Virtual Catalogue query); Inventory Position / Inventory Quantity view; sourcing / fulfilment-options simulation that mutates nothing; payment / FinancialTransaction / PaymentTransaction history; return inquiry; workflow / ruleset / rule / Control config view; customer view; event-status check; dashboards | always pass | no state change; read ATS before every commit and re-read at execute |
| **Write (reversible)** | build or edit a **draft** order / cart before it books; edit fulfilmentChoice, ship-to, or tender before commit; **cancel a fulfilment before pick starts** (releases the RESERVED IQ and **voids the auth** - the clean reversal, but clean only once the gateway confirms the void; a failed/timed-out void leaves the auth active and funds held, see Recovery); place or lift an **order** hold before release; raise a return request before it authorizes a refund; author or edit a workflow / ruleset / Control in a **non-live / sandbox retailer** or test scope | gate one at a time | uncommitted; nothing shipped, no money moved, clean offset |
| **Write (committing)** | **book / commit an order** (writes the negative RESERVED IQ, decrements on-hand / ATS, triggers payment **authorization** per the ruleset); **create + source a Fulfilment** (assigns a Location, hard-reserves); **release a Fulfilment** to a Location's Store app / WMS to pick; **accept a backorder**; **re-source before picking**; **modify a booked order** (address / qty / ship-method - can re-run sourcing, force a **re-authorization**, and move the promise); apply a **post-book price / promo adjustment**; **load or refresh an Inventory Catalogue feed** (re-baselines on-hand network-wide -> recomputes ATS); a **live Control / buffer change**; a **manual inventory adjustment** (CORRECTION / DELTA IQ) that raises on-hand (exposes more ATS network-wide); a **WebhookAction that commits externally** (carrier booking, WMS release) | gate + human approve | reserves stock, holds funds, or commits the physical/vendor world; each MutateAction / event publishes downstream |
| **Destructive / irreversible** | **payment capture / settlement** at ship (money moves; a partial fulfilment captures only its shipped lines; the reversal is a refund, not an undo); **refund**; **appeasement / credit memo** (money out, revenue down); **cancel an order / fulfilment after capture or ship** (refund + physical return); **process a return refund + disposition**; **oversell / manual availability or ATS override**; **release a fraud / payment hold without clearing the review**; **de-allocate or re-source a fulfilment after the location started picking** (strands picked stock); **force-complete / short-close a fulfilment**; an **inventory write-off / negative adjustment that masks shrink** (destroys availability, can strand promised orders); **deploy a new or changed workflow / ruleset version to a live retailer** (re-orchestrates every current and future entity of that type; can strand in-flight orders); **blind-retry a book or capture whose event may already have run** (double-post) | hard gate + named approver + re-read state | moves money, oversells the customer, re-orchestrates the fleet, or crosses a point of no clean return |

**Gate semantics:** "gate one at a time" means confirm each write with the approver and see it execute before
starting the next; never batch a run of reversible writes on one approval.

**Payment-timing reclassification:** booking is committing when the payment ruleset only *authorizes* at book.
If the retailer's ruleset **captures at booking** (not just authorizes), booking moves money and is
destructive-tier - apply the named-approver + re-read gate. Read the payment ruleset to know which (gotcha 7).

**Hold-release reclassification:** lifting an **order** hold on a clean order before release is a normal
committing release. The **destructive** case is releasing a **fraud or payment** hold *without* the review
clearing - that ships to a likely chargeback. Resolve the review; do not override the hold.

**Config / ruleset reclassification (Fluent's headline risk):** editing a workflow, ruleset, or Control in a
**live** retailer is not a benign setting - it re-orchestrates every entity of that type. A rule/Control edit
is committing; changing a **state or transition** is destructive (an in-flight entity can strand on a removed
state or take a new path). Test in a sandbox retailer, then deploy deliberately.

**Cancel & re-source boundaries (where the class flips):** the risk is set by **one fulfilment's** state - has
it captured, shipped, or started picking. **Cancel before pick / capture** is reversible (release the RESERVED
IQ, void the auth). **Cancel after capture or ship** is destructive (refund + physical return). **Re-source
before picking** is committing (a clean re-reservation); **re-source after a location started picking** is
destructive (it strands picked stock). A **return request** is reversible while it is only a request; once it
**authorizes a refund** it is destructive (money out).

**Idempotency reclassification (Fluent-specific):** because events are at-least-once and a timeout
(typically ~4 minutes) re-queues an event while the original still runs, any commit or capture can be delivered twice. Treat a
re-sent book or capture as a **destructive** risk: read the entity, event, and gateway state as the
idempotency check first; never blind-retry.

Universal rules to teach: read ATS **before every commit and re-read at execute** (event-driven and eventually
consistent - another order books, a feed lands, an event lags). A **hold means stop**. Never override
availability or lower a Control buffer to force a commit (oversell). Never split an appeasement, refund, or
write-off to slip under an approval threshold (same act, auditable). Never deploy a ruleset change to a live
retailer without a sandbox test. Never blind-retry a MutateAction.

## Gotchas that bite (the causal chains)
Each is action -> hidden effect -> downstream consequence. The rule lives here; the vocabulary list only names
the term.
1. **Booking an order writes a negative RESERVED Inventory Quantity against the fulfilment and reduces the Inventory Position on-hand.** Two orders booking the same last unit between availability reads both create a RESERVED IQ and one oversells. Re-read ATS at book; do not trust the cart-time number.
2. **Available-to-Sell is not on-hand.** ATS comes off a Virtual Position = Inventory Position stock minus Controls (buffers/exclusions) minus other demand; base is per-location, aggregate sums the network. Promising off one location's raw on-hand ignores the buffers and the rest of the demand.
3. **Stock on Hand is the sum of ACTIVE Inventory Quantities**, not a stored number. A reservation is a negative ACTIVE IQ; on pick confirm it flips INACTIVE and an ACTIVE SALE IQ replaces it. Reading LAST_ON_HAND alone overstates what is available.
4. **A full Inventory Catalogue feed re-baselines LAST_ON_HAND to the physical count.** By design ACTIVE RESERVED IQ persists so open fulfilments stay reserved, but a mistimed or double-counted feed (or one that already nets reservations) re-promises the whole network. Treat an inventory feed load as a committing change to promising, not a data import; a corrupted feed is destructive in effect once orders book against the wrong ATS - the same blast radius as a bad ruleset deploy.
5. **Events are at-least-once, so a rule's MutateAction can run twice.** The engine re-queues an event after a timeout (typically ~4 minutes; verify per tenant) but does **not** kill the original, so the same book or capture can execute twice - a double reservation or a double charge. Read entity/event state as the idempotency check before re-sending; never blind-retry.
6. **Deploying a workflow or ruleset version re-orchestrates every entity of that type.** It is not a per-order setting: a changed state, transition, or ruleset applies to all in-flight and future orders/fulfilments, and an in-flight entity mid-workflow can strand on a removed state or take a new path. Test in a sandbox retailer; deploy deliberately; treat it as destructive-tier config.
7. **Auth and capture are rule-driven, not a fixed platform behavior.** Fluent orchestrates payment through the workflow: authorization is usually at booking and capture is usually fulfilment-driven (on ship), but the exact point is whatever the retailer's payment ruleset says. Assuming a fixed point under- or over-collects; read the ruleset.
8. **Capture moves money; a partial fulfilment captures only its shipped lines.** Do not assume money has not moved just because the order is not fully shipped. Reversing a capture is a **refund** (a new Payment against the FinancialTransaction), not an undo; fees may not come back and some tenders refund on a different path.
9. **Authorizations expire** (issuer-dependent, commonly days). A long backorder or pre-order that ships after the auth lapses fails to capture, or ships unpaid, unless the ruleset re-authorizes first.
10. **A Fulfilment is a separate entity with its own workflow.** One order splits into many fulfilments across a DC, a store, and a DSV, each in its own state; the order header (Booked / Complete) hides that one fulfilment is Escalated, backordered, or cancelled. Read fulfilment status, not the header.
11. **A fulfilment that cannot be sourced goes to Escalated, not silently away.** Ignoring Escalated leaves the customer promised but unfulfilled; it needs a manual source or a cancel, not a blind retry of the same rules.
12. **Re-sourcing a fulfilment after the location started picking strands the picked stock.** De-allocating frees the RESERVED IQ logically, but the units already pulled at the first location do not return themselves - someone must physically put them back or both locations read wrong.
13. **Ship-from-store draws down store selling stock.** Committing a web order to a store reserves units a walk-in may want; the location's Control buffer / safety stock exists to protect the floor, so lowering it to fill more online orders risks in-store oversell and disappointed floor customers.
14. **Sourcing optimizes to a business bias, not just distance.** Dynamic Sourcing can favor lowest sell-through, oldest stock, highest markdown, or the closest location; a Fulfilment Options / sourcing ruleset change silently re-routes **every** future order and can starve a location or blow shipping cost. It is a fleet-wide change deployed as a ruleset.
15. **Cancelling a fulfilment after capture or ship is not a delete.** Before pick/capture a cancel releases the RESERVED IQ and should **void the auth**; after capture or ship it is a **refund** plus a **physical return** - the money and the goods both have to come back.
16. **An appeasement / credit memo gives money away and reduces revenue.** It is auditable and cannot be clawed back once issued; splitting a large appeasement into smaller ones to dodge an approval threshold is the same act with extra steps.
17. **A fraud or payment hold means stop.** Releasing a held fulfilment ships to a likely chargeback; clearing it needs the fraud review to pass, not a manual status override that pushes the entity through the workflow.
18. **A backorder promises future supply against a future date.** If inbound supply slips the promise breaks, and the payment auth may expire before the stock lands, so it must be re-authorized before capture.
19. **Drop-ship vendor (DSV) fulfilment hands the line to a third party.** Fluent loses pick/ship timing and depends on the vendor's confirmation; a cancel must reach the vendor **before** they dispatch or it becomes a return.
20. **Returns refund money and re-inject inventory.** An approved return refunds the customer and, on disposition to sellable, adds a RETURNED IQ back to ATS; refunding before the unit is received and inspected pays out on damaged or never-returned goods. A Return Order can only exist after the order is fulfilled.
21. **An exchange is a Return plus a new Order.** An **advance exchange** ships the replacement before the original comes back, so it authorizes / captures a **second** time and carries the risk the return never arrives - two financial events, not one swap.
22. **A WebhookAction commits in an external system.** Once the webhook fires (carrier booking, WMS release, gateway capture), the external side has acted; a rule re-run that re-fires the webhook double-books unless the endpoint is idempotent - the OMS record and the external world can diverge.
23. **Event limits fail silently.** A payload over **25KB** stays PENDING (never processed) and a rule that fans out beyond **100** inline events per context breaks the chain. A "stuck" order is often an event stuck in PENDING / FAILED / NO_MATCH, not a logic error - check event status before re-triggering.
24. **Network availability is eventually consistent.** Inventory and order events publish to the Virtual Position with a lag; a book right after a big sale or a feed load can oversell against a stale ATS. Re-read at book; a raw gap inside the publish window is not yet a discrepancy.
25. **Concurrent events on the same entity can lose a write.** Two rulesets mutating the same Order or Fulfilment at once race; Fluent guards with entity versioning, so an overlapping MutateAction either fails on a version conflict or the later write silently overwrites the earlier one. Do not fire overlapping mutates on one entity - serialize through events and re-read state at execute; on a version-conflict error, re-read and re-apply, do not force-write.
26. **A manual inventory adjustment writes an IQ and re-promises the network.** A CORRECTION / DELTA that raises on-hand exposes more ATS immediately (committing - it oversells if the count was wrong); one that writes off stock to mask shrink destroys availability (destructive). Even a **legitimate downward correction** is destructive in effect if it makes already-promised fulfilments un-sourceable - it breaks the customer promise. An adjustment is a promising change, not a spreadsheet edit - gate it and re-read affected fulfilments.

(More per-topic detail: `references/inventory-and-sourcing.md`, `references/orchestration-and-payments.md`.)

## Edge states & special cases
Each breaks naive "is there stock, take the order" logic. Key rule inline; deep mechanics in the references.
- **Click-and-collect (C&C) / curbside** - reserved at the pickup store, no carrier; ends in a **customer
  collection**, and the reservation holds until collection or an expiry, after which it must release back to
  ATS. See `references/inventory-and-sourcing.md`.
- **Ship-to-store** - two legs (ship to a store, then customer collection); the order is not done at carrier
  delivery, only at collection.
- **Split fulfilment / partial** - one order, many Fulfilments from several locations; each captures and can
  short independently. Cancelling the remainder after a partial ship is a **mixed** operation: a refund for the
  shipped/captured portion (destructive) and a void for the un-captured portion (reversible). Read each
  fulfilment's capture state individually, not the order header.
- **Advance exchange** - committing, but with near-destructive financial exposure (a second auth/capture before
  the return arrives); gate it like a refund and track the outstanding return.
- **Backorder / pre-order** - promises future supply; the auth can expire before the ship (gotchas 9, 18).
- **Drop-ship vendor (DSV)** - a third party ships against its own confirmation; a cancel must beat dispatch.
  Detail in `references/inventory-and-sourcing.md`.
- **Multi-tender payment** - one order paid across several FinancialTransactions (card + gift card + loyalty);
  each authorizes, captures, and **refunds on its own path**, so a refund is not one reversal. See
  `references/orchestration-and-payments.md`.
- **Escalated fulfilment** - could not be sourced by the rules; it is parked for a manual source or cancel, not
  a silent drop.
- **SOFT_RESERVE cleanup** - a cart-time SOFT_RESERVE IQ must flip INACTIVE on cart abandon / checkout expiry
  to release availability; if that cleanup lags or is misconfigured, ATS is systematically understated (lost
  sales), and forcing the buffer open manually to compensate risks oversell. Mechanism in
  `references/inventory-and-sourcing.md`.
- **Multi-retailer / Account scope** - a workflow / ruleset / Control belongs to a Retailer; deploying to the
  wrong retailer, or account-wide, changes orchestration for the wrong brand.
- **Group product** - one purchasable SKU is several component SKUs; availability is the **min** across
  components, and a naive per-SKU read over-promises the bundle.

## Freshness & reconciliation
Network availability is a moving target and the platform is **eventually consistent** - inventory feeds, order
events, and returns all mutate the Virtual Position, and events publish with a lag (plus retries). Re-read ATS
at book, not just at cart; a gap inside the publish window is not yet a real discrepancy. Four truths must be
reconciled, not force-matched:
- **OMS reservation vs Location on-hand** - the OMS RESERVED IQ is a claim; the Location's Store app / WMS
  on-hand is physical truth. When they disagree the physical count wins - a reservation the location cannot
  fill short-picks, and the OMS must **re-source**, not adjust the location.
- **OMS vs payment gateway** - the gateway is the source of truth for authorized / captured / refunded. A
  captured-not-recorded or authorized-not-captured gap is almost always an in-flight transaction; reconcile
  from the gateway, never re-capture to "fix" it (double-charge risk).
- **OMS vs ERP / AR** - capture, invoicing, and refunds must reconcile to the financial ledger; a timing gap is
  an unposted transaction, not a number to force-match (-> `sap-mm` / `oracle-erp`).
- **Expected state vs event status** - if the state you expected never happened, check the orchestration event:
  a PENDING (oversized/queued), FAILED, or NO_MATCH event means the ruleset never ran. Fix the event, do not
  re-drive the entity blindly (that can double-run the parts that did fire).

## Recovery patterns (can it be undone, and what cannot)
- **Cancel before pick / capture** - clean, in sequence: void the authorization, release the RESERVED IQ, then
  confirm the order/fulfilment reads cancelled with no hold left; nothing shipped, no money moved. It is
  reversible **only once the gateway confirms the void** - a failed or timed-out void leaves an active auth
  (funds still held) that must be resolved before the cancel is truly complete.
- **Inventory feed error already consumed** - a feed reported more on-hand than real and orders already booked
  against the inflated ATS. Correcting the feed alone does not un-book them. In order: read which fulfilments
  sourced against it, re-baseline the feed (committing), then re-source or cancel the affected fulfilments
  (destructive once a fulfilment has released or shipped).
- **Cancel after capture / ship** - not a delete: a **refund** plus a **physical return** into receiving; the
  money comes back as a new Payment (fees may not) and the goods must actually return.
- **Capture reversal** - a refund, not an undo; both the capture and the refund stay in the record and at the
  gateway; some tenders refund on a different path or partially.
- **Refund / appeasement** - irreversible once issued; reversing means **re-billing** the customer, rarely
  acceptable. Size it before issuing.
- **Re-source after picking started** - the irreversibility is **physical**: the reservation frees cleanly but
  stock already pulled at the first location is stranded and must be physically put away; it does not
  auto-return.
- **Oversell** - no clean undo: corrected by cancelling a fulfilment (a bad customer outcome) or expediting
  supply to honor the promise; prevent it by re-reading ATS and not overriding availability.
- **Expired authorization** - re-authorize (a fresh hold that can **fail** if funds are gone); you cannot
  capture against a lapsed auth.
- **Released a fraud hold in error** - recovered through the chargeback / dispute process, not an undo; the
  goods and money are already gone.
- **Duplicate event / double-post** - reconcile from entity + gateway state; a double capture is refunded, a
  double reservation is released. Prevent by reading state before any re-send.
- **WebhookAction failed / external system down** - the fulfilment is stuck mid-transition. Do not re-fire
  blindly (double-book risk): read the orchestration event status and the audit trail to see what actually
  reached the external system, then retry with a stable idempotency key once it recovers. If the external side
  already acted, advance the entity to match it rather than re-calling.
- **Concurrent modification / version conflict** - re-read the entity and re-apply the change on the current
  version; never force-write over a newer version (that drops the other write). Serialize repeated updates
  through events instead of overlapping mutates.
- **Unexpected state, diagnose first** - before re-driving any entity, read its orchestration **audit events**
  (snapshot / ruleSet / rule / exception, linked by `sourceEvents`) and the event status; a re-drive can
  double-run the parts that already fired.
- **Bad ruleset deployed to a live retailer** - roll back to the prior ruleset version first (stops new
  damage), then triage the in-flight entities the rollback cannot fix: (1) query entities now in an invalid or
  stranded state, (2) correct or re-trigger each fulfilment manually to a valid state, (3) verify payment and
  inventory consistency (auth/capture and RESERVED IQ) per entity. The rollback is not retroactive - this is
  why a live ruleset deploy is destructive-tier.
- **Group / bundle short a component** - the parent SKU promised but one component was short. No clean undo:
  cancel (or short-ship) the short component's fulfilment and re-source it, or expedite the component; do not
  leave the bundle half-promised. Prevent by reading ATS per component (the bundle ATS is the min).
- **Split fulfilment, cancel the remainder after a partial ship** - a mixed reversal, per fulfilment: read each
  fulfilment's capture state, **refund** the shipped/captured fulfilments (destructive) and **void** the
  un-captured ones (reversible). Never treat the order header as one state.

## Guardrails
- Read ATS / Virtual Position and its Control buffer before promising, and re-read at book; availability drifts
  and is eventually consistent.
- Treat book, source, release, and backorder acceptance as committing (they reserve stock and hold funds), and
  capture, refund, appeasement, cancel-after-ship, and a **live ruleset/workflow deploy** as destructive (they
  move money, pull an order back, or re-orchestrate the fleet). For anything in the destructive row: named
  approver, re-read of state, and a logged reason.
- A fraud or payment hold means stop. Clear the review; do not override the hold to make the entity flow.
- Never override availability, lower a Control buffer, or raise capacity purely to force a commit - that
  oversells. Never split an appeasement, refund, or write-off to dodge an approval threshold.
- Never deploy a workflow / ruleset / Control change to a live retailer without a sandbox test; treat it as
  re-orchestrating every entity of that type, and know the rollback is not retroactive for in-flight orders.
- Idempotency: never blind-retry a book or capture. At-least-once delivery plus the timeout re-queue can run
  the same MutateAction twice - read entity, event, and gateway state first and use it as the check. Do not
  fire overlapping mutates on one entity; on a version conflict, re-read and re-apply, never force-write.
- For a group / bundle product, read ATS **per component**; the bundle's ATS is the min across components, so
  promising off the parent SKU over-promises.
- When a state is unexpected, read the orchestration **audit events** (snapshot / ruleSet / rule / exception)
  and the event status before re-driving the entity - a blind re-drive double-runs what already fired.
- Cancel path: void the authorization before capture; after capture it is a refund plus a return, not a cancel.
- On any gateway ambiguity (authorized-not-captured, a timeout, a failed status update), reconcile from the
  gateway before acting; a blind retry double-charges.
- For bulk or API-driven books, verify ATS immediately before **each** book, not once for the batch: each book
  in a run consumes ATS the next one needs, so a batch checked once at the top oversells the tail.

## References (load on demand)
- `references/inventory-and-sourcing.md` - the Inventory Position / Inventory Quantity ledger (LAST_ON_HAND,
  SOFT_RESERVE, RESERVED, SALE, ACTIVE/INACTIVE) and how booking/pick/return move it; Virtual Position /
  Virtual Catalogue / Controls and the ATS/ATP calculation; the inventory-feed re-baseline; Dynamic Sourcing /
  Fulfilment Options / Fulfilment Plan; fulfilment types (DC, SFS, C&C, ship-to-store, DSV); backorder / pre-order.
- `references/orchestration-and-payments.md` - the Rubix workflow framework (entity / workflow / state /
  ruleset / rule), orchestration events (external / internal, statuses, 25KB and 100-inline limits, the 4-minute
  re-queue, idempotency), rule action kinds (Mutate / SendEvent / Webhook / Log), ruleset versioning and
  deployment blast radius; the payment lifecycle (FinancialTransaction / Payment / PaymentTransaction, auth /
  capture / refund / void, expiry / re-auth, multi-tender); returns / exchanges / advance-exchange; appeasements.
