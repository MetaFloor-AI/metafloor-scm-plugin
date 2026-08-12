# Inventory & sourcing (Fluent Order Management)

Read when a task turns on **whether** an order can be promised, **where** a fulfilment sources, or **how**
Fluent's inventory ledger moves. SKILL.md carries the judgment and the read/write/destructive matrix; this
file carries the mechanics.

## Contents
- The Inventory Quantity (IQ) ledger
- Stock on Hand, Virtual Positions, ATS and ATP
- Controls and Control Groups (the buffer)
- The inventory-feed re-baseline (the trap)
- Dynamic Sourcing (Fulfilment Options / Fulfilment Plan)
- Fulfilment types
- Backorder / pre-order promising

## The Inventory Quantity (IQ) ledger
Fluent does not store one on-hand number. An **Inventory Position** (a SKU at a Location) holds a **ledger** of
**Inventory Quantity (IQ)** records, each with a type and an ACTIVE/INACTIVE flag:

| IQ type | Meaning | Sign |
|---|---|---|
| **LAST_ON_HAND** | the physical count from the last inventory feed / count | positive baseline |
| **SOFT_RESERVE** | a cart-time hold during checkout | negative |
| **RESERVED** | a confirmed-order hold, written against a fulfilment at book | negative |
| **SALE** | stock picked/sold, replacing the RESERVED on pick confirm (negative because it represents stock departing the location, not revenue; RESERVED is likewise negative for claimed-but-unpicked stock) | negative |
| **RETURNED** | stock added back on a return disposition to sellable | positive |
| **CORRECTION / DELTA** | manual or reconciliation adjustments | either |

**Stock on Hand = sum of all ACTIVE IQ.** The lifecycle of one order's units:
- **Book** - an **ACTIVE RESERVED** IQ is written with a negative quantity against the fulfilment; on-hand
  drops by that amount. Example: LAST_ON_HAND 170, RESERVED -3 -> Stock on Hand 167.
- **Pick confirm** - the RESERVED IQ flips **INACTIVE** and an **ACTIVE SALE** IQ (negative) replaces it; the
  stock has moved from reserved to sold. Arithmetic: RESERVED -3 goes INACTIVE, SALE -3 goes ACTIVE ->
  Stock on Hand still 167 (same count, different composition).
- **Inventory feed / nightly sync** - LAST_ON_HAND updates to the new physical count, ACTIVE **SALE** IQ flip
  INACTIVE (already picked, now reflected in the count), and ACTIVE **RESERVED** IQ **stay ACTIVE** (unpicked
  fulfilments are still owed stock). This "reserved survives the feed" behavior is deliberate and is exactly
  why a naive full-replace of on-hand is dangerous (see the re-baseline trap below).
- **Cancel before pick** - the RESERVED -3 flips INACTIVE with nothing replacing it -> Stock on Hand returns
  to 170; the stock is available again. **Cancel after pick/ship** cannot un-sell the SALE - it is a refund +
  physical return.
- **SOFT_RESERVE cleanup** - a cart-time SOFT_RESERVE IQ flips INACTIVE on cart abandon / checkout expiry,
  releasing the held quantity back to availability. If this cleanup lags or is misconfigured the SOFT_RESERVE
  stays ACTIVE and ATS is understated network-wide (lost sales), so check for stale SOFT_RESERVE before
  concluding stock is short.

## Stock on Hand, Virtual Positions, ATS and ATP
Raw Stock on Hand is not what the channel promises against. Fluent computes **Available-to-Sell (ATS)** on a
**Virtual Position**, grouped into a **Virtual Catalogue** per channel/market:
- **Base virtual position** - ATS for one Location.
- **Aggregate virtual position** - ATS summed across all Locations in the network (the number a webshop shows).
- `ATS = Inventory Position stock on hand - Controls (buffers/exclusions) - open demand`.
- **ATP** is the date-aware view: it maps ATS plus scheduled future supply onto a promise date, so a line with
  zero current ATS can still promise a future date if inbound supply lands in the horizon (that is a backorder).
- **Eventually consistent** - IQ changes and order events publish to the Virtual Position with a lag, so two
  books inside that window can both pass and one oversells. Re-read ATS at book.

## Controls and Control Groups (the buffer)
**Controls** hold stock back from ATS; **Control Groups** aggregate several Controls. Typical uses: a store
floor buffer (protect walk-in stock), a channel protection (reserve for a priority channel), an exclusion
(damaged / display / a location not enabled for online). Two rules:
- A Control lives on the **Virtual/availability** layer, not the physical ledger - lowering a Control does not
  create stock, it just exposes more of the same on-hand to promising, so it can oversell against the floor.
- A live Control change re-promises the whole network for that channel; treat it as committing, test first.

## The inventory-feed re-baseline (the trap)
An **Inventory Catalogue** feed re-baselines LAST_ON_HAND to the source system's physical count. The risks:
- **Double-counting reservations** - if the source feed already has reservations netted out of the number it
  sends, and Fluent then keeps its own ACTIVE RESERVED IQ, the same demand is subtracted twice and availability
  is understated (lost sales). If the feed *overstates* (a stale or pre-pick count), availability is overstated
  and the network oversells.
- **Timing** - a feed that lands mid-orchestration re-promises orders in flight; a big receipt or a big sale
  right before a book can leave ATS stale inside the publish window.
- **Wholesale replace vs delta** - a full-catalogue replace re-baselines every Position at once; a bad file
  moves the whole network. A delta feed touches only changed Positions.
Treat any feed load as a **committing change to promising**, not a data import. Fluent consumes the feed; it
does not own the physical count (that is the location's WMS / count process, `manhattan-wms` or
`sap-ewm`).

## Dynamic Sourcing (Fulfilment Options / Fulfilment Plan)
When an order books, the sourcing rules produce **Fulfilment Options** and a **Fulfilment Plan** - which
Location(s) source which lines, and one or more **Fulfilment** entities. The engine ranks candidate Locations
by the retailer's configured bias:
- **Inventory** - only Locations with ATS for the line qualify.
- **Proximity** - closer Location = lower cost + faster promise.
- **Cost / markdown** - shipping zone, handling cost, or "clear the oldest / highest-markdown stock first".
- **Sell-through / load balancing** - favor the store with the lowest sell-through or the fewest orders in
  progress, to spread labor.
- **Split minimization** - prefer one Location for the whole order over many partials (each split is another
  parcel and ship cost).
- **Capacity / type** - a Location at its per-day capacity, or not enabled for the fulfilment type, is dropped.

Output = a Fulfilment Plan (Locations) + a promise. **The sourcing logic is a ruleset**: editing it re-routes
**every future order**, so a sourcing change is a committing, fleet-wide act, deployed and tested like any
ruleset (see `orchestration-and-payments.md`), not a per-order setting. A line that no Location can source
sends its fulfilment to **Escalated** for manual handling.

## Fulfilment types
| Type | What happens | The trap |
|---|---|---|
| **DC / warehouse** | a distribution center picks/packs/ships via carrier | standard; the DC WMS executes |
| **Ship-from-store (SFS)** | a store picks and ships a web order via the Fluent Store app | draws down store selling stock; the location Control buffer protects the floor |
| **Click-and-collect (C&C)** | reserved at a store, customer collects; no carrier | reservation holds until collection or expiry, then must release back to ATS |
| **Curbside** | C&C variant, associate brings it out | same reservation/expiry mechanics as C&C |
| **Ship-to-store** | ship to a store, then customer collection | two legs; done at collection, not at carrier delivery |
| **Drop-ship vendor (DSV)** | a third-party vendor ships direct | Fluent loses pick/ship timing; the vendor's confirmation drives status; a cancel must beat the vendor's dispatch |

## Backorder / pre-order promising
- A **backorder** promises a line with no current ATS against **future** supply (inbound receipt / transfer)
  and a future promise date. If that supply slips, the promise breaks.
- The **payment authorization can expire** before a long backorder ships (issuer-dependent, commonly days), so
  a backorder that outruns the auth window must **re-authorize** before capture or it ships unpaid / fails to
  capture.
- A **pre-order** is a backorder against not-yet-received supply for a launch date; same auth-expiry risk,
  amplified by the longer lead time.
