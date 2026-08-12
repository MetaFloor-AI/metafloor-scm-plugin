---
name: manhattan-oms
description: "Manhattan Active Omni Order Management (Active Omni / OMS) - safe operation of omnichannel order orchestration across the fulfillment network - order capture and lifecycle, Available-to-Commit / Available-to-Promise availability, distributed order sourcing and fulfillment (ship-from-store, DC, dropship, BOPIS, curbside, ship-to-store), allocation and reservation, backorder, split shipment, payment authorization / settlement / refund, returns, exchanges, and appeasements. Use when the order system is Manhattan Active Omni (or Manhattan DOM / Enterprise Order Management) and the work touches committing or sourcing an order, ATC / ATP availability, releasing to a fulfillment node, ship-from-store, BOPIS, an order or fraud or payment hold, a backorder, a payment auth or settlement, a refund, an appeasement, a return or exchange, or the user mentions distributed order management, order orchestration, sourcing rules, node capacity, safety stock, promise date, oversell, or de-allocation."
---

# Manhattan Active Omni (OMS) - operating it safely

Manhattan Active Omni Order Management (Active Omni, the cloud microservices product; the older on-prem line
is Manhattan DOM / Enterprise Order Management inside the SCALE-era suite) runs omnichannel **order
orchestration**: it captures an order, decides across the whole network **whether** it can be promised and
**where** it should be fulfilled, reserves the inventory, releases each line to a node, and manages the
money and the customer through returns, exchanges, and appeasements. It is the system of record for the
**order** and for **network availability** - not for physical on-hand inside any one building. Two facts
make it dangerous. First, **committing an order reserves inventory across the network** (it decrements
Available-to-Commit) and **authorizes the customer's payment** - so an order write binds stock and touches
money, not a draft. Second, the acts that move money (**payment settlement / capture, refund, appeasement**)
and the acts that touch the customer (**cancel, oversell, releasing a fraud hold**) cross a point of no
clean return. This skill gives the judgment to classify each action so the harness can gate it, plus the
edge states and recovery paths that decide if a mistake is fixable.

## Contents
- When this applies / when NOT
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
Order-management system is Manhattan Active Omni and the work is order capture, promising, sourcing,
fulfillment orchestration, payment, or returns across the network. When NOT:
- **Warehouse execution inside one node** - LPNs, waves, pick / pack / put-away tasks, on-hand adjustments,
  cycle counts -> `manhattan-wms`. The OMS *releases* a line to a node; that node's WMS (or the
  store fulfillment app) does the physical pick and ship. OMS decides where; WMS does the how.
- **ERP order-to-cash, accounts receivable, revenue recognition, the financial ledger** -> `sap-mm`
  or `oracle-erp`. Active Omni triggers invoicing and settlement; it does not own AR or the GL.
- **CRM, marketing, the customer master as a sales system** -> `salesforce`. Active Omni holds the
  order and the engagement around it, not the opportunity pipeline.

Active Omni vs legacy: continuous microservice publishing, real-time network availability, and store
fulfillment apps are Active Omni features. On the older Manhattan DOM / Enterprise Order Management line,
availability and integration are typically batch/interface-based, so do not assume real-time re-source or
instant availability refresh on a legacy deployment.

## Object & state model (reason about state, not nouns)
- **Order** - the customer's demand. Header + one or more **order lines**. Header states: created / captured
  -> validated (fraud + payment auth) -> committed (inventory reserved) -> released (to nodes) -> in
  fulfillment -> fulfilled / shipped -> delivered -> closed; plus held, backordered, cancelled, returned.
  **Lines orchestrate independently** - one order can split across a DC, a store, and a dropship vendor with
  each line in a different state, so the header status hides line reality. Line transitions:

  | From | Trigger | To |
  |---|---|---|
  | created | commit | committed (network inventory reserved, auth held) |
  | committed | source & allocate | allocated to a node |
  | allocated | release | released (at the node's WMS / store app) |
  | released | node pick + ship confirm | shipped (settlement fires) -> delivered -> closed |
  | committed, no ATC | accept backorder | backordered (awaits future supply) |
  | any pre-ship state | cancel | cancelled (free reservation, void auth) |
  | shipped | return + refund | returned |
- **Available-to-Commit (ATC)** - the network's promisable quantity: supply (node on-hand + inbound POs /
  ASNs / transfers) minus demand (existing reservations, safety stock / protect quantity). This is a
  **derived, forward-looking** number, not raw on-hand. Available-to-Promise (ATP) is the date-aware view
  that turns ATC + future supply into a **promise date**.
- **Reservation / allocation** - the claim placed on inventory when an order commits. A **soft reservation**
  holds network availability without binding a node; a **hard allocation** binds a specific node's on-hand
  to the line. Reserving decrements ATC for everyone else.
- **Fulfillment node** - where a line can be sourced: **DC**, **store** (ship-from-store, BOPIS, curbside,
  ship-to-store), or **vendor / dropship**. Each node carries on-hand, **safety stock / protect quantity**,
  and a **fulfillment capacity** (orders or units per day).
- **Sourcing (DOM) engine** - chooses the node(s) per line by **sourcing rules**: inventory, proximity,
  cost, split-shipment minimization, node capacity, and markdown/clearance goals. Output = an allocation +
  a promise.
- **Payment** - an **authorization** (a hold on funds) at commit; a **settlement / capture** (money moves)
  at ship; a **refund** on return; a **void / auth reversal** on cancel-before-settlement. The OMS holds a
  **token**, not the card, and talks to a **payment gateway / PSP**.
- **Return / RMA** - a return order that refunds money and, on disposition to sellable, re-injects the unit
  into ATC. An **exchange** is a return plus a new order.

## Vocabulary that bites
(Each term is glossed to its hazard here; the full causal chain is in Gotchas below.)
- **Available-to-Commit (ATC)** - promisable network quantity, `ATC = supply (on-hand + inbound) - demand
  (reservations + safety stock + allocation holds)`. Not on-hand. Promising off raw node on-hand oversells.
- **Commit** - the write that reserves network inventory to the order and triggers payment authorization.
  Before commit the order is a draft; at commit stock leaves the available pool and funds are held.
- **Allocation (OMS) vs allocation (WMS)** - the same word, two layers. OMS allocation reserves **network**
  inventory and assigns a **node**; WMS allocation reserves a specific **LPN / location** to a **pick task**
  inside that node. Conflating them double-reserves or mis-reads status.
- **Soft vs hard reservation** - soft holds availability without a node; hard binds a node's on-hand.
  Reading a soft reservation as fulfillable over-promises.
- **Sourcing rule** - the logic that picks the node. A rule edit silently re-routes **all future** orders;
  it is not a one-order setting.
- **Safety stock / protect quantity** - the buffer a node withholds from ATC (e.g. store shelf stock kept
  for walk-ins). Lowering it to fill more orders risks in-store oversell.
- **Fulfillment capacity** - a node's per-day limit. A store at capacity is skipped by sourcing; forcing an
  order past it overloads the node and misses the promise date.
- **Authorization vs settlement** - auth **holds** funds; settlement / capture **moves** them. Auth is not
  payment. Auths **expire** (a card auth commonly lapses in ~7 days, issuer-dependent - see gotcha 4).
- **Appeasement** - a goodwill credit / discount given to a customer. Real money out, reduces revenue,
  auditable, and not clawable once issued.
- **Backorder** - a line with no current ATC that promises against **future** supply and a future date.
- **Order hold vs fraud / payment hold** - an order hold pauses one order before release; a fraud or payment
  hold blocks fulfillment until a review clears. A hold means stop, not "override to proceed".
- **Ship-from-store (SFS) / BOPIS / curbside / ship-to-store (STS)** - store-based fulfillment types; BOPIS
  and curbside end in a **customer pickup**, not a carrier shipment.
- **Dropship / vendor fulfillment** - a third party ships; the OMS loses control of pick/ship timing and
  relies on the vendor's confirmation / ASN.

## Operations: read / write / destructive
Classify every operation family by what it does to inventory reservations, to money, and to the customer.
Kinds of action, not tool names.

| Class | Manhattan Active Omni operation families | Gate | Why |
|---|---|---|---|
| **Read** | order search / inquiry / timeline / line status; Available-to-Commit and ATP / promise inquiry; network availability by item or node; sourcing simulation / what-if that posts nothing; payment auth / settlement history; return / RMA inquiry; customer profile view; sourcing-rule, node-capacity, and safety-stock config view; dashboards and reports | always pass | no state change; read availability before every commit and re-read at execute |
| **Write (reversible)** | build or edit a **draft** order / cart before commit; edit ship-to, tender selection, or a line before commit; **cancel a line before release** (frees the reservation and **voids the authorization** - no money moved, no goods gone: the one clean reversal); **void / auth reversal** on its own (releases a payment hold); create a return request before it is authorized / refunded; place or lift an **order** hold before release; edit a sourcing rule, node capacity, or safety-stock threshold in a non-live / test scope | gate one at a time | uncommitted; no inventory shipped, no money moved, clean offset |
| **Write (committing)** | **commit / submit an order** (reserves network inventory, decrements ATC, triggers payment **authorization** = a hold on customer funds); **source & allocate** a line to a node (hard-reserves that node's on-hand); **release** a line to a fulfillment node (hands it to the WMS / store app to pick); **accept a backorder** (promises future supply + a date); **re-source** to another node **before** picking starts; **modify a committed order** (address / quantity / ship-method change - can re-trigger sourcing, a **re-authorization**, and a new promise date); apply a **price / promotion / coupon adjustment after commit** (changes the order total and can force a re-authorization or a partial refund at settlement); **edit a live sourcing rule / lower safety stock / raise node capacity** (changes promising for all future orders); **refresh or correct the availability / supply feed** (node on-hand, inbound ASN / PO / transfer) that recomputes ATC network-wide; create an **exchange / advance-exchange** | gate + human approve | reserves stock, holds funds, or commits the physical/vendor world; each publishes downstream |
| **Destructive / irreversible** | **payment settlement / capture** at ship or invoice confirm (timing is configurable and a partial ship settles only its shipped lines; money actually moves and the reversal is a refund, not an undo); **refund** (money out, irreversible once issued); **appeasement** (gives money away, reduces revenue); **cancel an order / line after settlement or ship** (needs refund + physical return); **process a return refund + disposition**; **oversell / manual availability or promise override** (commits against stock the network cannot deliver); **release a fraud / payment hold without clearing the review**; **de-allocate or re-source after a node started picking** (strands work); force-close / short-close a line | hard gate + named approver + re-read availability & payment state | moves money, oversells the customer, or crosses a point of no clean return |

**Gate semantics:** "gate one at a time" means confirm each write with the approver and see it execute
before starting the next; never batch a run of reversible writes on one approval.

**Hold-release reclassification:** lifting an **order** hold on a clean order before release is a normal
committing release. The **destructive** case is releasing a **fraud or payment** hold *without* the review
clearing - that ships to a likely chargeback. Resolve the review; do not override the hold to make the order
flow.

**Config reclassification:** editing sourcing rules, safety stock, or node capacity in a **live** scope is
committing, not reversible - it changes promising and sourcing for every order that follows, so treat it
like a committing write with approval, not a benign setting.

**Cancel & re-source boundaries (where the class flips):** the risk of a cancel or a re-source is set by
**one line** - has anything shipped, settled, or started picking. **Cancel before release / settlement** is
reversible (free the reservation, void the auth). **Cancel after settlement or ship** is destructive (refund
+ physical return). **Re-source before picking** is committing (a clean re-reservation); **re-source after a
node started picking** is destructive (it strands picked stock). A **return request** is reversible while it
is only a request; once it **authorizes a refund** it moves into the destructive tier (money out), so read
the return's state before acting, not just its existence.

Universal rules to teach: read network availability (ATC) **before every commit and re-read at execute**
because it drifts and is eventually consistent (another order commits, a node publishes new on-hand, supply
slips). A **hold means stop** - do not override a fraud/payment hold to make fulfillment succeed. Never
override availability or lower safety stock purely to force a commit; that oversells. Never split an
appeasement, refund, or write-off into smaller pieces to slip under an approval threshold; it is the same
act with extra steps and it is auditable.

## Gotchas that bite (the causal chains)
Each is action -> hidden effect -> downstream consequence. The normative rule lives here; the vocabulary
list above only names the term.
1. **Committing an order reserves network inventory and decrements Available-to-Commit.** Two orders that commit against the same last unit between availability reads both succeed and one oversells. Re-read ATC at commit; do not trust the number from cart time.
2. **Available-to-Commit is not on-hand.** It nets existing reservations and each node's safety stock out of supply (formula in the vocabulary list, full supply/demand breakdown in `references/sourcing-and-availability.md`). Promising off one node's raw on-hand ignores those and over-commits.
3. **Payment authorization holds funds; it does not move money.** Settlement / capture at ship moves it. Treating auth as payment under-collects, or a re-auth on top of a live auth double-holds the customer's funds.
4. **Authorizations expire.** A card auth commonly lapses in ~7 days (issuer- and network-dependent, roughly 5 to 30 days - confirm per deployment). If an order ships after the auth expired and no re-authorization ran, settlement fails and the order can ship unpaid. Long backorders and pre-orders must re-authorize before they settle.
5. **Settlement is where money moves - at ship or invoice confirm depending on configuration, and a partial shipment settles only its shipped lines.** Do not assume money has not moved just because the order is not fully shipped. Reversing a settlement is a refund, not an undo: a new transaction, gateway / interchange fees may not come back, and some tenders (gift card, certain wallets) refund on a different path.
6. **Sourcing assigns a node; re-sourcing after release strands work at the first node.** The store or DC may already have picked; de-allocating frees the reservation logically but the picked stock does not return itself - someone must physically put it back or both nodes read wrong.
7. **Ship-from-store draws down store selling inventory.** Committing a web order to a store reserves units a walk-in shopper may grab; the store's safety stock / protect quantity exists to prevent that, so lowering it to fill more online orders risks in-store oversell and disappointed floor customers.
8. **Node capacity is a hard limit.** A store maxed at, say, 40 orders/day is skipped by sourcing; force-routing an order past capacity overloads the store's labor and misses the promise date you gave the customer.
9. **One order splits across nodes and lines move independently.** A single order can part-ship from a DC, part from a store, and part dropship; a status read at the header hides that one line is stuck, backordered, or cancelled. Read line status, not just the header.
10. **Cancelling a line after settlement or ship is not a delete.** Before ship a cancel frees the reservation and should **void the authorization**; after settlement or ship it requires a **refund** plus a **physical return** - the money and the goods both have to come back.
11. **An appeasement gives money away and reduces revenue.** It is a real, auditable financial concession that cannot be clawed back once issued; splitting a large appeasement into smaller ones to dodge an approval threshold is the same act with extra steps.
12. **A fraud or payment hold means stop.** Releasing a fraud-flagged order to fulfillment ships to a likely chargeback; clearing it requires the fraud review to pass, not a manual override that pushes the order through the pipeline.
13. **A backorder promises future supply.** Accepting it commits a delivery date against inbound POs / ASNs / transfers; if that supply slips the promise breaks, and the payment auth may expire before the stock arrives so it must be re-authorized.
14. **Dropship hands the line to a third party.** The OMS no longer controls pick/ship timing; the vendor's confirmation / ASN drives status, and a cancel must reach the vendor **before** they ship or it becomes a return.
15. **Returns refund money and re-inject inventory.** An approved return refunds the customer and, on disposition to sellable, adds the unit back to ATC; refunding before the unit is received and inspected can pay out on damaged or never-returned goods.
16. **An exchange is a return plus a new order.** An **advance exchange** ships the replacement before the original comes back, so it authorizes / settles a second time and carries the risk the return never arrives - two financial events, not one swap.
17. **Reservation is soft vs hard.** A soft reservation holds availability without binding a node; reading it as fulfillable over-promises, because no node has actually committed the stock yet.
18. **Overriding availability to force a commit oversells.** A manual availability override, or committing against safety stock, promises stock the network cannot deliver and forces a later cancellation - the worst customer outcome, an order taken then pulled back.
19. **Sourcing optimizes for cost and split-minimization, not just distance.** A rule change (favor clearance stores, minimize splits, protect a flagship node) silently re-routes every future order and can starve a node or blow shipping cost. It is a fleet-wide change, not a tweak.
20. **OMS allocation is not WMS allocation.** OMS allocation reserves network inventory and assigns a node; WMS allocation reserves a specific LPN / location to a pick task inside that node. Reading one as the other double-reserves or mis-reports fulfillability.
21. **Cancelling before settlement should void the authorization.** Forget the void and the customer's funds stay held for days, generating complaints and support cost even though no sale happened.
22. **The OMS holds a payment token, not the card, and depends on the gateway.** A settlement or refund needs the gateway / PSP round-trip; a gateway timeout can leave money in an ambiguous **authorized-not-settled** state that must be reconciled from the gateway, not retried blindly (a blind retry double-charges).
23. **A retried commit or settlement can double-post.** A network retry on order submit can reserve inventory twice; a retry on capture can charge twice. The idempotency rule: before re-sending any commit or settlement, **read the order / payment state first and use it as the check** - never blind-retry. Treat a repeated commit or settlement as a destructive risk.
24. **Store fulfillment confirms the physical ship, not the OMS.** For ship-from-store, a store associate app is the node's WMS-equivalent; its pick/ship confirmation (not the OMS record) is the event that actually ships and triggers settlement, so an OMS status ahead of the store confirmation is a promise, not a fact.
25. **Network availability is eventually consistent.** Node on-hand and inbound supply publish to the availability picture with a lag; committing against a stale picture right after a large sale or a big receipt oversells or under-promises. Re-read at commit; a raw quantity gap inside the publish window is not yet a discrepancy.
26. **Modifying an order after commit is not a benign edit.** Changing address, quantity, or ship method can re-run sourcing (a different node), require a **re-authorization** (a new hold, which can fail), and move the promise date. A quantity increase reserves more ATC. Modifying a line **already released** to a node may not reach it before the pick starts - the node's WMS / store app may have planned the pick - so re-read node fulfillment status, not just the OMS record. Re-read availability and payment state before modifying, and treat it as committing.

## Edge states & special cases
Each breaks naive "is there stock, take the order" logic. Key rule inline; deep mechanics in the references.
- **BOPIS / curbside** - reserved at the pickup store, no carrier; fulfillment ends in a **customer pickup**
  confirmation and the reservation holds until pickup or an expiry, after which it must be released back to
  ATC. See `references/sourcing-and-availability.md`.
- **Ship-to-store (STS)** - two legs: ship to a store, then customer pickup; the order is not done at the
  carrier delivery, only at pickup.
- **Split shipment / partial fulfillment** - one line filled from several nodes, or part shipped and the
  remainder backordered; each piece settles and can short independently. Cancelling the remainder after a
  partial ship is a **mixed** operation: a refund for the settled/shipped portion (destructive) and a void
  for the unsettled portion (reversible). Read each line's settlement state individually, not the header.
- **Advance exchange** - committing, but it carries near-destructive financial exposure (a second
  auth/settle before the return arrives); gate it with the same scrutiny as a refund and track the
  outstanding return.
- **Backorder / pre-order** - promises future supply; the auth can expire before the ship (gotcha 4 / 13).
- **Dropship / vendor fulfillment** - a third party ships against the vendor's ASN; cancel must beat the
  vendor's shipment. Detail in `references/sourcing-and-availability.md`.
- **Multi-tender payment** - one order paid across card + gift card + loyalty; each tender authorizes,
  settles, and **refunds on its own path**, so a refund is not a single reversal. See
  `references/payments-and-returns.md`.
- **Fraud / manual review queue** - an order parked for review is not committed to fulfillment; releasing it
  without the review clearing ships to a chargeback.
- **Gift order / multiple ship-tos** - one order, several destinations; each ship-to sources and promises
  separately.

## Freshness & reconciliation
Network availability is a moving target. Between the read that promised an order and the commit that
reserves it, other orders, node receipts, transfers, and returns all mutate ATC, and the availability
picture is **eventually consistent** - node on-hand publishes to the network view with a lag (seconds to
minutes on Active Omni, longer on batch/legacy). Re-read ATC at commit, not just at cart. A gap inside the
publish window is not yet a real discrepancy. Three systems hold different truths and must be reconciled,
not force-matched:
- **OMS vs WMS at a node** - the OMS reserves; the WMS executes. When they disagree, the node's WMS on-hand
  is physical truth; the OMS reservation is a claim. A reservation the node cannot fill short-picks, and the
  OMS must **re-source**, not adjust the node.
- **OMS vs payment gateway** - the gateway is the source of truth for authorized / settled / refunded. An
  **authorized-not-settled** or **settled-not-recorded** gap is almost always an in-flight settlement;
  reconcile from the gateway, never re-charge to "fix" it (double-charge risk).
- **OMS vs ERP / AR** - settlement, invoicing, and refunds must reconcile with the financial ledger; a
  timing gap is an unposted transaction, not a number to force-match.

## Recovery patterns (can it be undone, and what cannot)
- **Cancel before release** - clean, in sequence: void the authorization, free the reservation, then confirm
  the order reads cancelled with no hold left; nothing shipped, no money moved. It is reversible **only once
  the gateway confirms the void** - a failed or timed-out void leaves an active auth (funds still held) that
  must be resolved before the cancel is truly complete. This is the only near-free reversal.
- **Supply-feed error already consumed** - a node reported more on-hand than it had and orders already
  committed against the inflated ATC. Correcting the feed alone does not un-commit them. In order: read which
  order lines sourced to that node, correct the feed (committing), then re-source or cancel the affected
  lines (destructive once a line has released or shipped).
- **Cancel after settlement / ship** - not a delete: it is a **refund** plus a **physical return** into
  receiving; the money comes back as a new transaction (fees may not) and the goods must actually return.
- **Settlement reversal** - a refund, not an undo; both the capture and the refund stay in the record and
  the gateway; some tenders refund on a different path or partially.
- **Refund / appeasement** - irreversible once issued; reversing means **re-billing** the customer, which is
  rarely acceptable. Size it before issuing.
- **Re-source after picking started** - the irreversibility is **physical**: the reservation frees cleanly
  but stock already pulled at the first node is stranded and must be physically put away; it does not
  auto-return.
- **Oversell** - no clean undo: corrected by cancelling a line (a bad customer outcome) or expediting supply
  to honor the promise; prevent it by re-reading ATC and not overriding availability.
- **Expired authorization** - re-authorize (a fresh hold on the customer that can **fail** if funds are
  gone); you cannot settle against a lapsed auth.
- **Released a fraud hold in error** - recovered through the chargeback / dispute process, not an undo; the
  goods and money are already gone.
- **Payment gateway split-brain** - if settlement posted at the gateway but the OMS status update failed,
  the money moved while the OMS shows unpaid. Reconcile from the gateway; do not re-capture (that
  double-charges).

## Guardrails
- Read network availability (ATC / ATP) and its reservation and safety-stock split before promising, and
  re-read at commit; availability drifts and is eventually consistent.
- Treat commit, allocation, release, and backorder acceptance as committing (they reserve stock and hold
  funds), and settlement, refund, appeasement, and cancel-after-ship as destructive (they move money or pull
  an order back from the customer). For anything in the destructive row: named approver, re-read of
  availability and payment state, and a logged reason.
- A fraud or payment hold means stop. Clear the review; do not override the hold to make the order flow.
- Never override availability, lower safety stock, or raise node capacity purely to force a commit - that
  oversells and misses the promise. Never split an appeasement, refund, or write-off to dodge an approval
  threshold.
- Cancel path: void the authorization before settlement; after settlement or ship it is a refund plus a
  return, not a cancel.
- On any payment gateway ambiguity (authorized-not-settled, a timeout, a failed status update), reconcile
  from the gateway before acting; a blind retry double-charges.
- For bulk or API-driven commits, verify ATC immediately before **each** commit, not once for the batch:
  each commit in a run consumes ATC the next one needs, so a batch checked once at the top oversells the tail.

## References (load on demand)
- `references/sourcing-and-availability.md` - Available-to-Commit / ATP calculation and its supply/demand
  components, the DOM sourcing-rule engine (node types, capacity, cost, split-minimization), soft vs hard
  reservation, fulfillment types (ship-from-store, BOPIS, curbside, ship-to-store, dropship), and
  backorder / pre-order promising.
- `references/payments-and-returns.md` - the payment lifecycle (authorization, settlement / capture, void /
  reversal, refund, expiry / re-auth, multi-tender, tokenization / gateway), fraud review, returns / RMA /
  exchange / advance-exchange, appeasements, and how each posts to the ERP / AR and the payment gateway.
