# Manhattan Active WM - wave / order-streaming release and the work lifecycle

How stock gets committed and physically moved. The two moments that matter for gating are **release**
(allocation commits on-hand) and **task confirmation** (the physical move posts). Read when a workflow
releases a wave or streams orders, allocates, or confirms pick / put-away / replenishment work.

## Contents
- Release: wave vs order streaming
- Allocation mechanics
- The work / task state machine
- Short picks and re-allocation
- Nested-LPN moves
- Cross-dock

## Release: wave vs order streaming
- **Wave (batch)** - order lines are grouped into a wave that sits in `planned` until released. Release is a
  single committing act: it **allocates** on-hand to every line in the wave and **generates the work** (pick,
  replen, pack). While the wave is `planned` you can still add, drop, or reprioritize lines. After release you
  cannot - the stock is reserved and the tasks exist. A large wave allocates greedily, so releasing it can
  consume stock a later, higher-priority order needed.
- **Order streaming (continuous)** - there is no `planned` holding state. Orders stream in and the engine
  allocates and creates work in real time against configured rules (priority, cut-off, capacity). The upside is
  no batch latency; the cost for gating is that **allocation commits the instant the order streams**, so there
  is no wave to hold and reprioritize. Reprioritizing means de-allocating already-committed stock, which
  strands any work already started.
- Gating rule: **release / stream is committing** for both models. It reserves real on-hand and starves the
  available pool for everyone else. Read on-hand first and understand what the release will consume.

## Allocation mechanics
- Allocation binds a specific **location + LPN + inventory attributes** (lot, serial, expiry) to an order line.
  A **hard allocation** commits that exact stock; the quantity is still physically present but no longer
  available to any other order.
- Allocation obeys strategy: FEFO / FIFO by expiry, location priority (active before reserve), zone, and unit
  of measure. If it cannot find matching available stock the line is **unallocated / back-ordered**, not
  silently filled from held or damaged stock.
- **De-allocation** releases the reservation back to available. If picking has already started, de-allocation
  frees the *book* reservation but the *physical* stock already pulled sits on a staging/pick LPN and must be
  put away - it does not fly back to its home location.

## The work / task state machine
Every task (pick, put-away, replenishment, cycle count, pack, load) moves through:
`ready -> in progress -> confirmed`, with side exits `short` and `cancelled`.
- **ready** - work exists and is queued; nothing has moved. Assigning or re-assigning it to a user or zone is
  labor routing only, no inventory effect.
- **in progress** - a user has taken the task; still no book change.
- **confirmed** - the physical move posts. A **pick** decrements the source location and puts the stock on the
  pick/stage LPN. A **put-away** moves from receiving to the storage location. A **replenishment** moves from
  reserve to active. This is the write that changes on-hand and publishes to the ERP.
- **short** - the picker confirms less than allocated (stock not found). The shortfall triggers re-allocation
  or a back-order (below).
- **cancelled / force-closed** - cancelling a `ready` task is clean. **Force-closing an in-progress task posts
  the move as if done**, so the book believes stock moved that may not have. Treat force-close as a write.

## Short picks and re-allocation
A short is not a data glitch; it means the allocation reserved stock that was not physically on the shelf.
Sequence: picker confirms short -> the order line is partially filled -> the engine attempts **re-allocation**
from another location/LPN -> if none, the line **back-orders**. The real fix is upstream: on-hand was
overstated, usually by a missed adjustment or an uncounted loss, so a cycle count of the short location should
follow. Re-picking without re-counting repeats the short.

## Nested-LPN moves
LPNs nest: pallet LPN -> case LPNs -> units. A move or status change on a **parent** cascades to every child
LPN and all their inventory in one action. Consequences:
- A mis-scanned parent move relocates every case on that pallet; downstream picks allocated to those cases now
  point to the wrong location and will short.
- Splitting a nested LPN (taking one case off a pallet) is its own move; the child gets its own location and
  the parent's contents change. Allocation must target the level (pallet vs case vs unit) that will actually be
  picked.

## Cross-dock
Cross-dock allocates **received** stock straight to an outbound order, skipping put-away to storage. The
receipt and the pick collapse: the goods-receipt posting and the allocation happen close together, and the
stock may never touch a storage location. The risk is timing - an outbound order allocated to inbound stock
that is delayed or short at receipt has no storage buffer to fall back on, so a receiving short becomes an
immediate outbound short.
