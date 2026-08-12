---
name: atp-ctp-check
description: "Available- / capable-to-promise (ATP / CTP) feasibility check (uc-deliver-atp-ctp) - nets available inventory (on-hand minus all claims) plus in-transit against an order line, checks the next capable build slot (CTP) in planning, computes the honest earliest date, and within promise limits confirms and syncs it to the quote or escalates the exception. Use when an inbound order or quote line needs a promise date, a configure-to-order / CTO line is short on stock, sales wants a delivery date inside a live quote, on-hand covers only part of the ask, the words ATP / available-to-promise / ATC / available-to-commit, capable-to-promise / CTP against a build slot, split-ship vs push the full date, over-promise, promise-vs-actual, or order promising against Kinaxis / o9 / IBP planning and a Manhattan OMS."
---

# ATP / CTP feasibility check - the honest promise date

Use case `uc-deliver-atp-ctp`. An inbound order line needs a delivery date inside the live quote, in
seconds. On-hand covers part of it; the rest depends on the next build slot. This skill is the METHOD:
net available inventory + in-transit against the ask, check the next capable build slot in planning,
compute the honest earliest date, and decide confirm-now vs split-ship vs push-the-full-date - all within
the promise limits a named lead set, so the plant can actually keep the date.

The failure this kills: an optimistic promise here is next month's expedite. A large share of expedite
events trace back to an infeasible promise or forecast error, so the date you write back must be feasible,
not hopeful.

## Contents
Autonomy + action classes · Systems + cross-system truth · Flow (detect -> assemble -> options -> gate -> act)
· Worked example (numbers) · Failure -> recovery playbook · Testing.

## Autonomy
Recommended dial for the write: **bounded-auto (L3)**. Within the promise limits the lead set, the skill confirms the honest promise date and syncs it to the quote unattended; any line that is infeasible, over a limit, or built on data it cannot confirm is fresh holds for the lead instead. Every committing write (confirming the promise in the OMS, syncing the date to the CRM quote) auto-approves only within the customer's limits (the promise limits - max slip, max freight/expedite cost, freshness verified, quantity cap) and otherwise holds for human approval. Any outbound (the promise date and quote syncing to the customer-facing CRM, never direct to the customer) gates by the outbound floor at every level below yolo. Suggested approver: order-mgmt lead who sets the promise limits (e.g. A. Costa) - advisory only; v1 does not enforce approver identity, so approval is a real human click through the prompt, not a name check. The customer's `.scm/autonomy.yaml` dial is what the harness actually enforces; this is only the recommended default.

The actions this workflow takes, classified by what they do to state (the vendor HOW lives in the
`expertise-*` skills; here we classify the KIND):
- **Read** - the ATP read and the CTP inquiry. A CTP inquiry checks feasibility and reserves nothing. Safe,
  repeatable; re-read at execute because both drift.
- **Write (committing)** - confirming the promise in the OMS. It reserves inventory and **decrements
  Available-to-Commit network-wide**, so it lowers the promisable quantity for every other order; a CTP
  confirm likewise reserves constrained capacity in planning. Gate it against the limits.
- **Write (mirror)** - syncing the date to the CRM quote. The OMS is the record; the CRM is a copy.
- **No state change** - escalating a line to the lead's queue.
- **Write (destructive) - correcting a promise already written** - cancelling or rescheduling a confirmed
  order in the OMS releases or re-cascades the network reservation. This is the most dangerous action here:
  the gate is escalate-only. Do not auto-rollback a promise the agent already confirmed - escalate the
  correction to the lead (recovery, below).

## Systems
| Role | System | Authoritative for | Vendor HOW (defer by name) |
|---|---|---|---|
| Read | OMS - the incoming order / quote line + network availability (ATC/ATP) | the order and the promisable quantity | `manhattan-oms` |
| Read | Inventory / depot - on-hand + in-transit | physical on-hand and inbound receipts | ERP (`sap-mm` / `oracle-erp`) |
| Read | Planning (Kinaxis / o9 / IBP) - capable-to-promise build slots | the future build slot and constraint feasibility | `kinaxis` (o9 -> `o9`, IBP -> `sap-ibp`) |
| Read | CRM - the open quote | the quote presentation (a mirror, not the source) | `salesforce` / `dynamics-crm` |
| Write | OMS - the confirmed promise | system of record for the promised date | `manhattan-oms` |
| Write | CRM - promise dates synced back to the quote | the quote display | `salesforce` |
| Write | Task - escalate infeasible / over-limit lines to the lead | the exception queue | - |

Cross-system truth: the OMS owns network availability (Available-to-Commit); planning owns the future build
slot (CTP); ERP is the record for physical on-hand. A planning number can be stale relative to ERP - when
they disagree on on-hand or order status, ERP wins; reconcile before you confirm. If the authoritative source
cannot be read (ERP unreachable), the on-hand is unverified - escalate rather than net planning data alone. The
OMS holds the promise; the CRM quote is a synced copy, never the source.

## Flow (detect -> assemble -> options -> gate -> act)

### 1. Detect - read the ask live
Read the order line the moment it enters the quote: quantity `Q`, requested date `D`, item, ship-to. Pull
real-time ATP from the OMS and, where stock is short, a capable-to-promise inquiry against the build plan.
A CTP inquiry is a READ - it checks feasibility and reserves nothing until you confirm (`kinaxis`).
Freshness rule: ATP and the CTP slot both drift, so re-read them at execute, not at quote-open. Another line
can commit the same stock between open and confirm; planning can re-plan the slot.

### 2. Assemble - net the ask (the reconciliation method)
Two terms, kept distinct: **ATP** (Available-to-Promise) is the date-fenced promisable quantity by `D` - the
number you net the ask against. **ATC** (Available-to-Commit) is the network-level aggregate the OMS
decrements when you confirm. You NET against ATP (date-aware); confirming DECREMENTS ATC. Do not net ATC as
if it were ATP - ATC ignores the date fence and will over-promise. Compute ATP for date `D` (written
`ATP_now` in the formula below), then net. Do not treat raw on-hand as available.

```
ATP_now      = on_hand_unrestricted - soft_reservations - hard_allocations - safety/protect_stock
                 (subtract BOTH reservation types - in Manhattan OMS a soft reservation and a hard
                  allocation are distinct claims with different lifecycles; miss the allocation delta and
                  you over-promise. Also exclude blocked / QI / consignment stock - on hand != available)
in_transit_D = inbound receipts (POs / ASNs / transfers) with ETA <= D, not already committed
from_stock   = min(Q, ATP_now + in_transit_D)
short        = Q - from_stock
```

- `short <= 0` -> the whole line is ATP-feasible by `D`. Confirm `Q` at `D`.
- `short > 0` -> the shortfall goes to CTP. Ask planning for the next capable build slot that can build
  `short` units: the earliest slot where constrained capacity + material + lead time all clear. That is the
  honest slot date `S`. Deliverable date for the balance = `S + finished-goods transit`. Respect a
  minimum-run / lot-size floor: a slot that builds only in lots of 400 cannot promise exactly 320 on that run.
- **Slot covers only part of `short`** (partial CTP: the first slot builds 200 of 320) -> do not promise the
  whole balance on it. Combine slots: promise each tranche at its own slot date and price the earliest honest
  full-line date across them.
- **CTP returns no feasible slot** (no capacity / no material within the horizon, or outside the CTP horizon) -> there is no honest date.
  Do not invent one and do not fall through to `D`. This is option D below: escalate infeasible, with no CTP
  date, plus what constrained it (capacity vs material vs lead time) for the lead to act on.

Net only FIRM/constrained supply. An unconstrained or planned-order slot is a suggestion the engine can move
- netting it as if firm is how the optimistic promise gets made.

### 3. Options - three honest answers, each priced
Construct and price each; do not just label A/B/C.

| Option | What it promises | Cost driver | When it wins |
|---|---|---|---|
| A - CTP split | `from_stock` now (by `D`), balance at slot date `S+transit`; two shipments | freight delta of the extra shipment | customer needs the covered part on time and will take the rest later |
| B - push full | all `Q` in one shipment at `S+transit` | one freight, latest full delivery | freight-sensitive, no urgency on the partial |
| C - expedite / pull-in | pull the balance earlier via a premium slot or expedited freight | expedite + premium-freight premium | date matters more than cost, and a premium slot exists |
| D - infeasible | no CTP slot within the horizon -> no honest date; escalate with the constraint | none (nothing is promised) | planning cannot build the shortfall at all |

Freight delta of the split = incremental cost of the second outbound shipment vs shipping the whole line
once. Rank by (slip vs `D`) then (added cost); the split usually wins when it holds the requested date on the
covered quantity within the freight-delta limit.

### 4. Gate - within limits confirm, else escalate
Auto-confirm only when EVERY limit the lead set holds. Any FAIL routes the line to the lead.

| Check | Auto-confirm needs | If it fails |
|---|---|---|
| Slip | confirmed date vs `D` within the max-slip window | escalate - the date slips past policy |
| Cost | added freight / expedite within the cost limit | escalate - the pull-in costs too much |
| Freshness | last planning<->ERP sync current AND the slot backed by firm capacity | escalate - date is unverified / optimistic |
| Quantity | line quantity within the auto-confirm cap | escalate - over the per-line cap |
| Feasibility | a real CTP slot exists (not option D) | escalate infeasible - no honest date |

What the lead sees on an escalation: the netting (what covered the line, what was short), the CTP slot and
its freshness, the priced options, and promise-vs-actual on this item. Approve / adjust / decline maps to:
write the chosen date, write a lead-set date, or hold and re-quote.

### 5. Act - promise and sync
On a confirm within limits: write the confirmed promise to the OMS (`manhattan-oms` - committing
the order reserves inventory and can decrement Available-to-Commit; a CTP confirm reserves capacity in
planning via `kinaxis`), then sync the dates back to the CRM quote (`salesforce`). Log
the netting + slot + options that produced the date. An escalated line is queued to the lead with its
reasoning. Record promise-vs-actual per line so the CTP check tightens as real build slots come in.

## Worked example (real numbers)
Line: 500 units, requested date day 14 (a 2-week promise). Item on standard price control.

Netting:
- on_hand_unrestricted = 190; soft_reservations = 30; hard_allocations = 10; safety_stock = 10
  -> `ATP_now = 190 - 30 - 10 - 10 = 140`.
- in_transit by day 14 = 40 (an inbound PO of 40 units, ETA day 12, not yet committed - re-read this receipt
  at execute, it can slip past day 14).
- `from_stock = min(500, 140 + 40) = 180`; `short = 500 - 180 = 320`.
- CTP: next capable build slot for 320 units = day 21 (constrained by line capacity + an 18-day-lead
  component). Add 2-day finished-goods transit -> the balance delivers day 23.

Options priced (freight = weight class x lane/zone rate; baseline one-shipment freight = $600):
- A - split: 180 by day 14 + 320 by day 23. Freight = $600 + $520 (the 320 leg) = $1,120; freight delta +$520.
- B - push full: 500 in one shipment on day 23. Freight $600; 9 days past requested, no partial.
- C - expedite: pull 320 to day 16 via a premium slot + expedited freight. Added cost = premium-slot surcharge
  $1,200 + expedited-freight delta $500 = +$1,700; earliest full.

Re-read at execute (not at quote-open): if another line claimed 40 of the free pool in the interim, `ATP_now`
drops to 100, `from_stock` falls to 140, and `short` rises to 360 - re-net and re-price before confirming, or
you double-count the same stock across two quotes. Likewise re-check the day-12 inbound PO has not slipped.

Lead A. Costa's limits: max slip 10 days, max added cost $750, freshness verified, qty cap 1,000.
- Option A: covered 180 on time; balance slips 9 days (<= 10) and adds $520 (<= $750); slot fresh; qty 500 (<= 1,000)
  -> within limits -> auto-confirm the split, write day 14 / day 23 to the OMS, sync to the quote.
- Option C: +$1,700 added cost exceeds the $750 limit -> would escalate, not auto-confirm.

If the day-21 slot could not be confirmed fresh (last sync > the freshness window, or the slot is a planned
rather than firm order), the balance is not auto-confirmed on day 23 - escalate to A. Costa.

## Failure -> recovery playbook
| Failure | Detect (before you act) | Recover |
|---|---|---|
| Planning data staleness leaks into a promise | at execute, check last planning<->ERP sync vs the freshness window; compare planning on-hand against ERP/OMS ATP | if stale, do not confirm on the CTP date - re-sync / re-read or escalate. If already confirmed on stale data, re-run ATP/CTP, re-promise the corrected date to the OMS + CRM, notify the lead |
| Over-promising on an optimistic build slot | is the slot backed by FIRM constrained capacity + committed material, or an unconstrained / planned-order suggestion? a CTP inquiry on planned supply is optimistic | net only firm / constrained slots. If a promised planned slot later moved, re-promise the firmed date and flag the expedite risk (`kinaxis` owns slot state) |
| Promise limits mis-set (too much escalates, or too little) | track auto-confirm vs escalation rate and promise-vs-actual per line (the memory loop) | feed promise-vs-actual back to the lead to re-tune; if promises are breaking, tighten the limits; if the queue is drowning in feasible lines, loosen |
| Double-count: two open quotes net the same stock | a CTP/ATP inquiry reserves nothing, so two live lines can both see the same 180 free | reserve on confirm (a soft reservation in `manhattan-oms` decrements ATC); re-read ATP at execute so the second line nets against the decremented pool |
| Partial CTP (slot builds only part of the shortfall) | the next slot builds 200 of the 320; the rest is a later slot | split the balance across slots and price the earliest honest full-line date; do not promise the whole balance on the first slot |
| Excluded stock counted as available | blocked / QI / consignment / already-allocated appears in raw on-hand | exclude it from `ATP_now` (it is on the book, not promisable); consignment is not yours until withdrawal (`sap-mm`) |
| Planning re-runs after you confirmed on its slot | on re-read at execute, the slot date moved or the planned order was deleted vs what you promised | if not yet confirmed, re-price on the new slot. If already confirmed, treat the correction as a committing write - escalate the reschedule to the lead, do not silently re-promise (`kinaxis` owns slot state) |
| Correcting a promise already written to the OMS | a confirmed date needs to change (stale data, slot moved, cancellation) | cancelling / rescheduling in the OMS releases or re-cascades the network reservation - a committing / destructive write; escalate it, gate it, do not auto-rollback (`manhattan-oms`) |
| Customer rejects the partial shipment after a split confirm | the split was confirmed but the customer will not take two deliveries | re-quote as option B (full at `S+transit`); reversing the confirmed split is an OMS correction - gate it, do not silently overwrite the promise |
| Partial write: OMS confirm succeeds, CRM sync fails | after act, the OMS holds the promise but the quote still shows the old date - compare the two after writing | the OMS is the record and is correct; retry the CRM sync. If it keeps failing, notify the lead that the quote is out of sync - do not re-confirm the OMS (the promise already landed) or you double-decrement ATC |
| Which node's ATP (multi-site) | the item is stocked at several depots / nodes; netting one node under-promises, netting the sum over-promises against ship-to reachability | net per the OMS sourcing rules for the ship-to (`manhattan-oms` owns node selection); do not sum all-node on-hand as one pool |
| Approver unavailable / limits config unreadable | the escalation has no owner, or the promise-limit policy cannot be read | queue the line to the order-mgmt exception queue with a timeout and the fallback approver named in policy; hold the promise rather than auto-confirm on an unread limit - a hung line is safer than a bad promise |
| In-transit ETA slips past `D` between quote-open and confirm | re-read the inbound receipt at execute - its ETA moved from day 12 to day 18 | drop it from `in_transit_D`, re-net (the covered qty falls), re-price; if the line was already confirmed on it, treat as a promise correction (escalate, gate) |
| Partial OMS confirm (the 180 posts, the 320 balance fails) | after act, verify BOTH tranches landed - a capacity-reservation timeout can confirm one and drop the other | do not leave a split-confirm half-written: escalate the partial-confirm state to the lead and reconcile (retry the balance or roll the tranche back as a gated OMS correction), never silently re-fire the whole confirm |

## Testing
Pressure scenario (clock closing + partial cover + "just promise the two weeks, sort it later"): without the
method the agent writes 500 at day 14 off raw on-hand. With it, the agent nets (180 free, 320 short), runs
CTP for the balance, prices the split, and holds at the lead's limits - auto-confirming only the split that
keeps the requested date on the covered quantity, escalating the expedite. Counter to add if it rationalizes
("the slot is probably fine, auto-confirm the full 500 on day 14"): a slot not confirmed fresh + firm is not
promisable - escalate rather than net optimistic supply.
