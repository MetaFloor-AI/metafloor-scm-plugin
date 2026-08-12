# Korber WMS - wave / waveless release, the work-task lifecycle, and the Architect layer

How stock gets committed and physically moved, and the lever unique to Korber (ex-HighJump) that changes or
bypasses those rules. The two moments that matter for gating are **release** (allocation commits on-hand) and
**work / task confirmation** (the physical move posts). Read when a workflow releases a wave or runs waveless
flow, allocates, confirms directed work, or touches an **Architect** workflow or business rule.

## Contents
- Release: wave vs waveless / flow-through
- Allocation mechanics
- The work / task state machine
- Short picks and re-allocation
- Nested LPN moves
- Cross-dock / flow-through
- The Architect workflow / business-rules layer
- Config change-control and versioning

## Release: wave vs waveless / flow-through
- **Wave (batch)** - order lines are grouped into a wave (from a **wave template**) that sits in `planned`
  until released. Release is a single committing act: it **allocates** on-hand to every line in the wave and
  **creates the work** (pick, replen, pack). While the wave is `planned` you can still add, drop, or
  reprioritize lines. After release you cannot - the stock is reserved and the work exists. A large wave
  allocates greedily, so releasing it can consume stock a later, higher-priority order needed.
- **Waveless / flow-through (continuous)** - newer K.Motion deployments can allocate and create work as
  orders arrive, with no `planned` holding state. No batch latency; the cost for gating is that **allocation
  commits the instant the order flows in**, so there is no wave to hold and reprioritize. Reprioritizing
  means de-allocating already-committed stock, which strands any work already started.
- Which model runs is a configuration choice (and the older Warehouse Edge / ex-Accellos line is
  wave-centric). Do not assume waveless behavior without confirming it.
- Gating rule: **release / flow is committing** for both models. It reserves real on-hand and starves the
  available pool for everyone else. Read on-hand first and understand what the release will consume.

## Allocation mechanics
- Allocation binds a specific **location + LPN + inventory attributes** (lot, serial, expiry, catch weight)
  **+ owner** (in a 3PL / multi-client site) to an order line. A **hard allocation** commits that exact
  stock; the quantity is still physically present but no longer available to any other order.
- Allocation obeys the configured strategy (an Architect / setup rule): FEFO / FIFO by expiry, location
  priority (active before reserve), zone, unit of measure, pick-type, and owner. If it cannot find matching
  available stock the line is **unallocated / back-ordered**, not silently filled from held, QA, damaged, or
  another owner's stock.
- **De-allocation** releases the reservation back to available. If picking has already started, de-allocation
  frees the *book* reservation but the *physical* stock already pulled sits on a staging LPN and must be put
  away - it does not fly back to its home location.

## The work / task state machine
Every unit of work (pick, put-away, replenishment, cycle count, pack, load) is usually **RF-directed** and
moves through: `ready -> in progress -> confirmed`, with side exits `short` and `cancelled`.
- **ready** - work exists and is queued; nothing has moved. Assigning or re-assigning it to a user or zone is
  labor routing only, no inventory effect.
- **in progress** - a user has taken the work on the RF terminal; still no book change.
- **confirmed** - the physical move posts. A **pick** decrements the source location and puts the stock on
  the pick / ship LPN. A **put-away** moves from receiving to the storage location. A **replenishment** moves
  from reserve to active. This is the write that changes on-hand and posts to the host.
- **short** - the picker confirms less than allocated (stock not found). The shortfall triggers re-allocation
  or a back-order (below).
- **cancelled / force-closed** - cancelling a `ready` task is clean. **Force-closing an in-progress task
  posts the move as if done**, so the book believes stock moved that may not have. Treat force-close as a write.
- Korber holds a **soft lock** on the inventory record during a confirm; a concurrent operation on the same
  LPN / location can fail with a lock error. The lock does not hard-reserve the location against planning, so
  a stale read can still short. On a lock error, re-read state before retrying - never blind-retry (double-post).

## Short picks and re-allocation
A short is not a data glitch; it means the allocation reserved stock that was not physically on the shelf.
Sequence: picker confirms short -> the order line is partially filled -> the engine attempts **re-allocation**
from another location / LPN -> if none, the line **back-orders**. The real fix is upstream: on-hand was
overstated, usually by a missed adjustment or an uncounted loss, so a cycle count of the short location should
follow. Re-picking without re-counting repeats the short.

## Nested LPN moves
LPNs nest: pallet LPN -> case LPNs -> units, and Korber uses one generic LPN type (no ILPN / OLPN split). A
move or status change on a **parent** cascades to every child LPN and all its inventory in one action:
- A mis-scanned parent move relocates every case on that pallet; downstream picks allocated to those cases
  now point to the wrong location and will short.
- Splitting a nested LPN (taking one case off a pallet) is its own move; the child gets its own location and
  the parent's contents change. Allocation must target the level (pallet vs case vs unit) that will actually
  be picked.
- Voiding / consuming an LPN destroys its identity; its inventory must be re-established under a new LPN via
  receipt or adjustment.

## Cross-dock / flow-through
Cross-dock allocates **received** stock straight to an outbound order, skipping put-away to storage. The
receipt and the pick collapse: the goods-receipt posting and the allocation happen close together, and the
stock may never touch a storage location. The risk is timing - an outbound order allocated to inbound stock
that is delayed or short at receipt has no storage buffer to fall back on, so a receiving short becomes an
immediate outbound short.

## The Architect workflow / business-rules layer
Korber's ex-HighJump lineage makes the WMS **highly configurable through Architect**, the configuration
environment where business rules, workflow / screen steps, validations, labels, and integration maps are
defined. This is Korber's defining trait and its main hazard.
- Architect config is **warehouse-wide (or zone / client-wide), not per-order data**. It decides how work is
  created and directed, how allocation strategizes, what validations fire at receive / pick / ship, whether a
  step auto-confirms, and how the host integration maps a transaction.
- The consequence for classification: **the same-named operation can behave differently on two Korber sites.**
  A screen that is a benign read on one site can, by config, write or auto-confirm on another. Do not assume
  the standard behavior; read the configured rule before deciding read / write / destructive, and default to
  the more dangerous class when unsure.
- The trap: editing a rule to make one flow behave the way you want silently changes behavior for every
  future transaction that hits that rule. It is a change-control action - named approver, a lower-environment
  test, and a recorded reason - not a quick operational tweak.
- A **hand-run action that bypasses the configured workflow** (an admin utility, a direct data edit, or a
  step run outside the RF flow) skips the validations the workflow enforces and can post an unbalanced or
  unchecked move. Treat any such write to inventory, on-hand, or work state as destructive: it has no
  automatic offset, so a wrong write must be manually reconciled with a compensating adjustment or move.

## Config change-control and versioning
- Architect configurations are versioned and **promoted** between environments (development / test ->
  production). Change in a lower environment, test against representative data, then promote - do not edit
  production config live to fix a running flow.
- Reverting a rule restores only **future** behavior. Any receipts, waves, allocations, or tasks already run
  under the changed rule keep their result; find and correct each one individually - the revert does not
  retroactively fix them.
- Because behavior is customer-defined, a "standard HighJump / Korber" assumption from another site is not
  evidence about this site. Confirm the product (Warehouse Advantage vs Warehouse Edge) and the configured
  rule before acting.
