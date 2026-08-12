# Blue Yonder WMS - wave / waveless release, the task lifecycle, and the policy / MOCA layer

How stock gets committed and physically moved, and the two levers unique to Blue Yonder that change or
bypass those rules. The two moments that matter for gating are **release** (allocation commits on-hand) and
**task confirmation** (the physical move posts). Read when a workflow releases a wave or runs waveless flow,
allocates, confirms directed task work, or touches a policy or a MOCA command.

## Contents
- Release: wave vs waveless flow
- Allocation mechanics
- The task / directed-work state machine
- Short picks and re-allocation
- Nested ILPN / OLPN moves
- Cross-dock / flow-through
- Policies (poltype / polvalue)
- MOCA command layer

## Release: wave vs waveless flow
- **Wave (batch)** - order lines are grouped into a wave (from a **wave template**) that sits in `planned`
  until released. Release is a single committing act: it **allocates** on-hand to every line in the wave and
  **generates the task work** (pick, replen, pack). While the wave is `planned` you can still add, drop, or
  reprioritize lines. After release you cannot - the stock is reserved and the tasks exist. A large wave
  allocates greedily, so releasing it can consume stock a later, higher-priority order needed.
- **Waveless flow (continuous, cloud line)** - there is no `planned` holding state. Orders flow in and the
  engine allocates and creates work in real time against configured rules (priority, cut-off, capacity). No
  batch latency; the cost for gating is that **allocation commits the instant the order flows in**, so there
  is no wave to hold and reprioritize. Reprioritizing means de-allocating already-committed stock, which
  strands any work already started.
- Gating rule: **release / flow is committing** for both models. It reserves real on-hand and starves the
  available pool for everyone else. Read on-hand first and understand what the release will consume. Which
  model runs is set by policy and by the product line (legacy DLx is wave-only).

## Allocation mechanics
- Allocation binds a specific **location + LPN + inventory attributes** (lot, serial, expiry, catch weight)
  to an order line. A **hard allocation** commits that exact stock; the quantity is still physically present
  but no longer available to any other order.
- Allocation obeys the configured strategy (a **policy**): FEFO / FIFO by expiry, location priority (active
  before reserve), zone, unit of measure, and pick-type. If it cannot find matching available stock the line
  is **unallocated / back-ordered**, not silently filled from held, QC, or damaged stock.
- **De-allocation** releases the reservation back to available. If picking has already started, de-allocation
  frees the *book* reservation but the *physical* stock already pulled sits on a staging / OLPN and must be
  put away - it does not fly back to its home location.

## The task / directed-work state machine
Every task (pick, put-away, replenishment, cycle count, pack, load) is usually **RF-directed** and moves
through: `ready -> in progress -> confirmed`, with side exits `short` and `cancelled`.
- **ready** - work exists and is queued; nothing has moved. Assigning or re-assigning it to a user or zone is
  labor routing only, no inventory effect.
- **in progress** - a user has taken the task on the RF terminal; still no book change.
- **confirmed** - the physical move posts. A **pick** decrements the source location and puts the stock on
  the pick / OLPN. A **put-away** moves from receiving to the storage location. A **replenishment** moves
  from reserve to active. This is the write that changes on-hand and publishes to the host.
- **short** - the picker confirms less than allocated (stock not found). The shortfall triggers re-allocation
  or a back-order (below).
- **cancelled / force-closed** - cancelling a `ready` task is clean. **Force-closing an in-progress task
  posts the move as if done**, so the book believes stock moved that may not have. Treat force-close as a write.

## Short picks and re-allocation
A short is not a data glitch; it means the allocation reserved stock that was not physically on the shelf.
Sequence: picker confirms short -> the order line is partially filled -> the engine attempts **re-allocation**
from another location / LPN -> if none, the line **back-orders**. The real fix is upstream: on-hand was
overstated, usually by a missed adjustment or an uncounted loss, so a cycle count of the short location should
follow. Re-picking without re-counting repeats the short.

## Nested ILPN / OLPN moves
LPNs nest: pallet LPN -> case LPNs -> units. A move or status change on a **parent** cascades to every child
LPN and all its inventory in one action. Consequences:
- A mis-scanned parent move relocates every case on that pallet; downstream picks allocated to those cases now
  point to the wrong location and will short.
- Splitting a nested LPN (taking one case off a pallet) is its own move; the child gets its own location and
  the parent's contents change. Allocation must target the level (pallet vs case vs unit) that will actually
  be picked.
- ILPN vs OLPN: an **ILPN** is the inbound container (receive / put-away); an **OLPN** is the outbound
  shipping carton (pack / ship). They live in different halves of the flow, so an operation aimed at the wrong
  type routes a container down the wrong process.

## Cross-dock / flow-through
Cross-dock allocates **received** stock straight to an outbound order, skipping put-away to storage. The
receipt and the pick collapse: the goods-receipt posting and the allocation happen close together, and the
stock may never touch a storage location. The risk is timing - an outbound order allocated to inbound stock
that is delayed or short at receipt has no storage buffer to fall back on, so a receiving short becomes an
immediate outbound short.

## Policies (poltype / polvalue)
Blue Yonder WMS behavior is driven by **policies** - configuration rows (a policy type `poltype`, a value
`polvalue`, often keyed by warehouse / zone / item group). Policies decide allocation strategy, wave and
waveless rules, task direction and priority, replenishment triggers, count classes, and more.
- A policy is **warehouse-wide (or zone/group-wide) config, not per-order data**. Changing one re-shapes how
  every future wave allocates or how every RF task directs.
- The trap: tuning a policy to make one wave or one order behave the way you want silently changes the
  behavior for the next hundred. It is a change-control action - named approver, a lower-environment test, and
  a recorded reason - not a quick operational tweak.
- Reverting a policy restores *future* behavior; it does not retroactively fix waves, allocations, or tasks
  already run under the changed value. Those must be found and corrected individually.

## MOCA command layer
**MOCA** (Mapping Of Command Actions) is the command / scripting layer under every Blue Yonder WMS operation;
the RF screens and UI flows call sequences of MOCA commands, and those flows enforce validations (attribute
checks, status checks, balance checks) around the raw command.
- A **read-only MOCA query** (inspecting data) is a read and safe.
- A **hand-run MOCA command that writes** - moving inventory, adjusting on-hand, forcing or closing a task -
  runs the business logic **past** the RF-flow validations. It can post an unbalanced or unchecked move,
  skip the audit trail the directed flow would leave, and create a phantom or a loss.
- Treat any direct MOCA write that touches inventory, on-hand, or task state as **destructive**: it has no
  automatic offset, so a wrong write must be manually reconciled with a compensating adjustment or move.
