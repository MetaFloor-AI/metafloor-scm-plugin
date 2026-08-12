# Payments & returns (Manhattan Active Omni)

Read when a task moves money or reverses an order: authorization, settlement, refund, appeasement, a return
/ RMA, or an exchange. SKILL.md carries the read/write/destructive classification; this file carries the
lifecycle mechanics and the gateway reconciliation rules.

## Contents
- The payment lifecycle
- Authorization expiry and re-auth
- Multi-tender
- Tokenization and the gateway
- Fraud / manual review
- Returns / RMA and disposition
- Exchanges and advance exchange
- Appeasements
- What each act posts

## The payment lifecycle
| Stage | When | What it does | Class |
|---|---|---|---|
| **Authorization** | at commit | places a **hold** on the customer's funds; no money moves | committing |
| **Void / auth reversal** | cancel before settlement | releases the hold; no money moved | reversible (releases a hold) |
| **Settlement / capture** | at ship or invoice confirm (configurable); partial ship settles partially | **money actually moves** from the customer | destructive |
| **Refund** | on return / cancel-after-settle | money goes back as a **new** transaction | destructive |
| **Chargeback** | customer disputes | bank pulls funds back; fees apply | outside OMS control |

**Settlement timing is configured, not fixed.** A deployment can capture at ship-confirm or at
invoice-confirm, and a partial shipment settles only the lines that shipped. Never assume money has not moved
just because the order header is not fully shipped - read the settlement state per line.

The single most common error is treating **authorization as payment**. Auth only holds funds; if you never
settle, no money is collected; if you re-auth on top of a live auth, the customer's funds are held twice.

## Authorization expiry and re-auth
- A card authorization commonly **lapses in ~7 days**, but the window is issuer- and network-dependent
  (roughly 5 to 30 days) - **confirm it per deployment** rather than hard-coding 7 days.
- If an order ships after its auth expired and no **re-authorization** ran, settlement **fails** and the
  order can ship unpaid.
- Backorders, pre-orders, and long fulfillment leads must re-authorize before settling. A re-auth is a fresh
  hold that can **fail** if the customer's funds are no longer available - so a long-delayed order is a
  payment risk, not just a fulfillment delay.
- An **order modification after commit** (address change, quantity increase, ship-method change) can trigger
  a re-authorization mid-lifecycle - the amount or risk profile changed. That re-auth can fail, so a
  modification is a payment event, not just a data edit; re-read the payment state after modifying.

## Multi-tender
One order can pay across several tenders (card + gift card + loyalty points + store credit). Each tender
**authorizes, settles, and refunds on its own path**. Consequences:
- A refund is not a single reversal; it splits back across the original tenders by their rules (gift card
  portion to gift card, card portion to card).
- A partial refund must decide tender order; refunding all to card when part was gift card mis-states the
  books and can over-refund cash value.

## Tokenization and the gateway
- The OMS stores a **token**, not the raw card (PCI scope stays with the gateway / PSP). Every settlement or
  refund is a **round-trip** to the gateway.
- A gateway **timeout or outage** can leave a payment in an ambiguous **authorized-not-settled** or
  **settled-not-recorded** state. Reconcile from the **gateway** (the source of truth for
  authorized/settled/refunded); a **blind retry double-charges**.
- The gateway, the OMS, and the ERP / AR are three records that must reconcile; a timing gap is an in-flight
  transaction, not a discrepancy to force-match.

## Fraud / manual review
- An order can be parked in a **fraud / manual review** queue before it commits to fulfillment. It is not
  released while under review.
- A **fraud or payment hold means stop.** Releasing a flagged order to fulfillment ships to a likely
  chargeback. Clearing it means the **review passes**, not a manual override that pushes the order through.
- Recovery from a wrongly-released fraud order is the **chargeback / dispute** process, not an undo - the
  goods and money are already gone.

## Returns / RMA and disposition
- A **return order / RMA** authorizes a return, refunds the customer, and on **disposition to sellable**
  re-injects the unit into ATC.
- **Refund before inspection risk:** refunding on return creation (before the unit is received and
  inspected) can pay out on damaged, wrong, or never-returned goods. Gate the refund to receipt + inspection
  unless the business explicitly runs instant refunds.
- Disposition decides ATC impact: **sellable** adds back to available; **damaged / quarantine / scrap** does
  not. A wrong disposition either injects bad stock into promising or writes off good stock.

## Exchanges and advance exchange
- An **exchange = a return + a new order**. Two orders, linked.
- An **advance exchange** ships the replacement **before** the original returns. That means a **second**
  authorization / settlement and the standing risk the return never arrives - a real financial exposure, not
  a swap. Gate advance exchanges and track the outstanding return.

## Appeasements
- An **appeasement** is a goodwill credit, discount, or partial refund given to retain a customer. It is
  **real money out** and **reduces revenue**, it is auditable, and it **cannot be clawed back** once issued
  (reversing means re-billing the customer, rarely acceptable).
- Size it and gate it with an approver. **Splitting a large appeasement into smaller ones to slip under an
  approval threshold is the same act with extra steps** and it is auditable.

## What each act posts
- **Authorization** -> a funds hold at the gateway; no ledger movement.
- **Settlement / capture** -> money moves; the OMS drives **invoicing** and the ERP / AR posts the
  receivable and revenue.
- **Refund** -> a new gateway transaction out; the ERP posts the reversal / credit memo.
- **Appeasement** -> a concession posting that reduces revenue / adds a credit in AR.
- **Return disposition to sellable** -> re-injects the unit into ATC and posts the inventory add at the
  receiving node (its WMS records the physical receipt).
