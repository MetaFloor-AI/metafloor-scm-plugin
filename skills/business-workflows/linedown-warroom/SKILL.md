---
name: linedown-warroom
description: "Line-down war room - from a stopped production line, diagnose the constraint (equipment fault, missing part, material/quality hold), find the fastest restart path (repair in place, reroute or resequence to another line/plant, lateral-transfer the nearest spare, expedite the part), price each path by hours-to-restart against the scrap-and-idle burn plus missed-commitment exposure, and orchestrate the war-room task fan-out on an incident bridge. Use when a line or critical asset trips or stops, an MES downtime code fires (E-45, a press or stamping line down on the night shift), commitments run through the stopped line, someone asks how do we restart, repair vs reroute vs hold, which orders resequence, is there a spare, can we expedite the part, or mentions line down, line-down, war room, incident bridge, plant-floor crisis, scrap and idle burn, hours to restart, lateral transfer, alternate line, changeover, resequence production orders, CMMS history, or uc-risk-linedown-warroom."
---

# Line-down war room - restart in hours, not shifts

Use case `uc-risk-linedown-warroom`. A critical asset trips at 02:00 on a thin night shift, MES logs a
downtime code, and three customer commitments due in 36 hours run through that line. Every minute deferred
is scrap and idle labor at a fixed burn rate, and the missed commitments behind it turn a plant problem into
a customer escalation. This is the highest-blast-radius flagship: the restart is not one write, it is a
coordinated multi-party response - diagnose the constraint, price the restart paths, and orchestrate a
war-room task fan-out on an incident bridge so a repair, a reroute, and a customer heads-up run in parallel
on one clock.

## Contents (find it fast at 02:00)
Read this first (the two leaks) - Autonomy (the gate) - Systems + action classes (what is gated) - Flow -
The method (diagnose the constraint, price the paths, options table) - Worked example - Orchestrate (the
war-room fan-out + the check-and-abort) - Failure -> recovery - Cross-system truth - Testing.

## Read this first
Two money leaks dominate, and the skill exists to kill both. First, **chasing the wrong constraint** - a
downtime code is a symptom, not the cause; spending a 5-hour seal swap on a fault that is really a downstream
starve burns the shift twice. Second, **paying for optionality you did not price** - a defined changeover
cost that buys down a fat repair-overrun tail is cheap; a reroute that costs more than the burn plus missed
commitments it avoids is waste. Speed matters, so diagnosis, assembly, and pricing run fast and in parallel -
but the committing acts (resequence MES, reschedule SAP, raise the work order, move material, notify the
customer) hold at the plant manager's gate. **Material moves are human-gated** - a lateral transfer or an
expedite commits physical stock and freight, so it fires only on explicit approval of that move.

## Autonomy
Recommended dial for the write: **gated (L2)**. The agent runs the war-room coordination unattended - it opens the incident bridge, fans tasks out to maintenance, materials, and planning, and keeps one live restart-path decision that re-prices as each workstream returns hard facts - but it commits nothing until approved. Every committing write (resequence production orders in MES, reschedule WIP + commitments in SAP, raise the CMMS work order, and the physical lateral transfer or expedite) holds for human approval each time. Any outbound (the customer notification, which carries a not-yet-confirmed line-down story - a premature "we will miss your order" starts the escalation you were trying to prevent) gates by the outbound floor at every level below yolo. Suggested approver: plant manager (e.g. R. Halvorsen) - advisory only; v1 does not enforce approver identity, so approval is a real human click through the prompt, not a name check. The customer's `.scm/autonomy.yaml` dial is what the harness actually enforces; this is only the recommended default.

## Systems
| Role | System | Authoritative for | Expertise skill |
|---|---|---|---|
| read | MES - line status + downtime code | the constraint symptom, the line/order state, which commits run through it | `siemens-opcenter`, `rockwell-factorytalk` |
| read | Maintenance / CMMS | repair history for the code, this asset's actual repair-time spread, spare on-hand | `ibm-maximo`, `sap-pm` |
| read | SAP / ERP | open orders, WIP, commitment dates, component on-hand, nearest-stock location | `sap-mm` |
| read | Inventory / depot | physical spare + component availability (the shelf, not the system record) | `sap-mm` |
| read | Planning | time-phased demand/supply, alternate-line qualification, changeover cost | `kinaxis` |
| write | MES - resequenced production orders | the restart schedule | `siemens-opcenter`, `rockwell-factorytalk` |
| write | SAP - rescheduled WIP + commitments | the re-promised dates | `sap-mm`, `kinaxis` (replan) |
| write | CMMS - work order raised | the repair record | `ibm-maximo`, `sap-pm` |
| write | Material move - lateral transfer / expedite (staged) | the physical stock + freight commit | `sap-mm` |
| write | Notification - maintenance + planning + customer | the fan-out + the customer heads-up | - |
| write | Incident bridge | the war-room comms record | - |

### Action classes (what the harness gates)
- **Read** - MES code, CMMS history, on-hand, spare shelf-check, commitment dates, alternate-line qualification, expedite ETA. Always pass; re-read the drifting ones (on-hand, spare, ETA, repair progress) at execute.
- **Write, reversible** - draft the fan-out tasks and the customer message (held), stage the resequence/reschedule as draft records held out of execution (not visible to the floor as live orders) until the gate. Low blast; the diagnosis and staging continue even while the gate is chased.
- **Write, reversible (informational, but participants self-initiate)** - open the incident bridge. The record is reversible, but paging maintenance/planning onto it can trigger them to start diagnosis or a material move on their own authority - so the bridge scope and the "material moves are gated" rule are stated on the page when it opens.
- **Write, committing** - resequence production orders in MES, reschedule WIP + commitments in SAP, raise the CMMS work order. Each re-promises dates or binds the schedule; holds at the gate, fires in dependency order on approve. Vendor mechanics deferred to the named MES / CMMS / ERP expertise skills.
- **Write, committing + physical (human-gated)** - a lateral transfer or an expedite. Commits physical stock movement and freight spend, and a wrong move strands parts on the wrong line. Fires only on explicit approval of the material move, re-read the spare/stock at execute. Deferred to `sap-mm`.
- **Write, irreversible egress (high)** - the customer notification. Cannot be un-sent, and a premature one on an unconfirmed path starts an escalation. Fires only after the path is committed AND approved; internal fan-out (maintenance + planning) may go earlier on the bridge.
- **Write, committing (reversal / rollback)** - reversing an already-committed resequence or reschedule when a path fails mid-flight (the alternate line trips, a downstream write errors). This is not a free undo - it re-promises dates again and churns the floor - so it carries its own gate: re-read state, get the manager's approval to roll back, and reconcile MES + SAP together. Deferred to the MES / ERP expertise skills.
- **Write, log (memory)** - the event record (code, constraint confirmed, path chosen, priced options, actual recovery). Low blast, but it is a write - append after the event; a bad size here mis-tunes the next call, so record what actually happened, not the plan.

## Flow (detect -> diagnose -> assemble -> options -> gate -> orchestrate)
1. **Detect.** Catch the MES downtime code the instant it logs; cross-read the commitments running through the line and their due dates. Freshness: on-hand, the spare shelf-count, expedite ETA, and live repair progress all drift - re-read them at execute, never off the detection snapshot.
2. **Diagnose the constraint.** The code is a symptom. Classify it to a constraint class and confirm it with a second independent read before spending on any lever (see the method). This step kills the top leak.
3. **Assemble.** Size the burn rate `B` from its real components, pull the asset's actual repair-time spread from CMMS (not the code's book mean), and gather the levers each constraint allows - spare on the shelf, alternate line qualified and free, nearest stock for a lateral transfer, a confirmed expedite ETA.
4. **Options.** Construct and price each feasible restart path by total cost, under repair-time uncertainty (the method + table below). Rank by lowest expected total cost after the feasibility and commitment-protection guardrails.
5. **Gate.** Present the ranked priced paths, the precedent (how the last event on this code went), and the sized downside of each. The plant manager approves, adjusts the path, or declines.
6. **Orchestrate (act).** Open the incident bridge, fan the tasks out in parallel, and on approval fire the committing writes in dependency order (below). Log the why before the day shift walks in.

## The method (what the record does not give you)

### 1. Diagnose the constraint (a code is not a cause)
Map the downtime code to a constraint class, then verify with a second signal - the failure that costs the
most is a repair aimed at the wrong thing.

| Constraint class | Symptom signals | Restart levers available |
|---|---|---|
| Equipment / mechanical fault | MES fault code + CMMS history for that code | repair in place (spare on hand or expedite the part), reroute to another line/plant |
| Missing part / component starve | MES starve/no-feed code + SAP on-hand = 0 at the line | lateral-transfer nearest stock, expedite the part, BOM-approved alternate part, reroute |
| Material / quality hold | QM block, bad-lot flag | release an alternate lot, reroute, hold |
| Changeover / sequence | schedule gap, no material staged | resequence, pull-ahead another order |
| Labor / utility / facility | crew short, power/air fault | reroute, hold and absorb, facilities |

Verification rule: an E-45 hydraulic code that is really a downstream starve wastes a 5-hour seal swap.
Confirm the class against a second read (the physical asset state, the feed-stock level, a maintenance eye)
before you commit a lever. Never let a clean-looking code substitute for confirming the actual cause.

### 2. Price each restart path by TOTAL cost, not cash out
For each feasible path `i`:
- `B` = burn rate ($/hr) while the affected output is stopped = scrap/spoilage + idle direct labor + absorbed fixed overhead / lost contribution. Read the components; do not guess a round number.
- `Down_i` = `B x output-hours lost under path i`. For a reroute this is less than `B x repair_time`, because output resumes on the alternate line at changeover-complete, well before the asset is fixed.
- `C_i` = direct incremental cost of the path: changeover (crew + first-article scrap + host-line yield/opportunity), spare-part cost, expedite premium, overtime, lateral-transfer freight.
- `Miss_i` = commitment exposure that still slips under path `i` = sum over unheld commits of (late/OTIF penalty + escalation / lost-margin). A commit the path holds contributes $0.
- `T_i = Down_i + C_i + Miss_i`.

Under repair-time uncertainty, rank on expected total cost, not the point mean:
`E[T_i] = P_hold x T_i(hold) + P_overrun x T_i(overrun)`, where `P_overrun` comes from this asset's own CMMS
repair-time spread. Build the spread from the last N actuals for THIS asset + code (not the generic book
mean): set the hold time at the median of those actuals, the overrun time at the p75-p90 tail, and
`P_overrun` at the share of past repairs that ran past the median. Two data points give a coarse split; more
actuals tighten it as memory accrues. With fewer than ~5 actuals for this asset + code, set `P_overrun >=
0.5` and flag the estimate low-confidence at the gate - favor a path that caps the downside over one that
bets on the mean. The lever of the whole call: **a defined changeover cost buys down a fat repair-overrun
tail** - that is why a reroute can beat a cheaper-looking repair-in-place.

Thresholds (applied after the feasibility gate):
- **Reroute pays when** `changeover_cost < B x (repair_time - changeover_time) + Miss_avoided` - the burn and missed commitments it removes exceed the changeover it adds. Here `B` is the burn of the ORDERS being rerouted (their share of the line burn), not the whole line - rerouting two of three orders buys back two-thirds of the burn, not all of it.
- **Expedite is only real when its part lands in time.** `H_expedite = confirmed part ETA + install`. If `H_expedite > time-to-commitment`, the expedite buys nothing for that commit - `Miss_i` stays full and the premium is wasted. Price off a CONFIRMED ETA, never a quoted one.
- **Hold and absorb only when** the cheapest feasible restart lever's `E[T]` exceeds the miss exposure it would prevent - i.e. every restart costs more than the slip it avoids.

Guardrails that override the raw number:
- **Feasibility first** - is the spare physically on the shelf (not just in the system)? is the alternate line qualified for this part (tooling + spec) and actually free? is the changeover crew available? A path that fails feasibility is not ranked.
- **Commitment-protection floor** - a path that holds a top-tier or penalty-bearing commit may win at a higher cash cost. Surface it at the gate when a top-tier commit's `Miss_i` on the cheaper path exceeds ~20% of the cheapest path's `E[T]` - a relationship risk the raw dollars understate; never let it silently override the number.

### 3. Options, priced
| Option | Constructed as | Total cost `T` | When it wins |
|---|---|---|---|
| A - Repair in place | spare on hand or expedited part, fix the asset, all orders wait the repair | `B x repair_time + spare/expedite + Miss` | spare is on the shelf, repair-time spread is tight, and the window holds all commits |
| B - Reroute / resequence | move the recoverable orders to a qualified free line now, repair the asset in parallel | `Down_reroute + changeover + Miss_residual` | `changeover < B x (repair_time - changeover_time) + Miss_avoided` and a line is qualified + free |
| C - Hold + partial-ship | repair in place, ship what fits, concede the tightest commit by design | `B x repair_time + spare + Miss_conceded` | no faster lever's `E[T]` beats the slip it avoids, or every faster lever is infeasible (cheapest cash, but count the conceded penalty) |

## Worked example (real numbers)
02:14. Line 3's stamping press trips, MES downtime code E-45 (hydraulic). Three orders are due in 36h and run
through Line 3. First diagnose: E-45 is an equipment fault; confirm against the physical asset (hydraulic
pressure lost, not a downstream starve) before pricing a repair. Then re-read the drifting inputs: the spare
seal is physically on the depot shelf, and CMMS shows five E-45 repairs on THIS press over the trailing year
(two of them this quarter): 4h, 5h, 5h, 6h, 8h.

- **Burn `B`.** Scrap/spoilage $6K/hr + idle direct labor $5K/hr + absorbed overhead $3K/hr = **$14K/hr**.
- **Repair spread.** Book mean is 5h; this press's five trailing-year E-45s were 4h, 5h, 5h, 6h, 8h -> hold at the 5h median (`P_hold = 0.6`), and since 2 of 5 ran past the median, `P_overrun = 0.4` at a ~9h upper tail (the 8h long-pole rounded up for the worst case, not a mean of the tail). Five actuals clears the low-confidence rule, so no `P_overrun >= 0.5` floor applies. Three orders ~ even, so ~$4.7K/hr of burn each.
- **A - Repair in place** (spare seal $1.2K + call-in maintenance OT $0.8K = $2K direct). Hold (5h): `14K x 5 + 2K = $72K`, all three fit the 36h window. Overrun (9h): `14K x 9 + 2K + 16K` (the two tightest commits slip past the window) = `$144K`. `E[T_A] = 0.6 x 72K + 0.4 x 144K = $100.8K`.
- **B - Reroute two orders to Line 5** (90-min changeover, cost $22K = changeover crew + first-article scrap + Line 5 yield). The two rerouted orders resume at 1.5h and are locked regardless of the repair; the third rides the parallel repair on the on-hand seal. Hold: rerouted burn `2 x 4.7K x 1.5 = $14K` + third-order burn `4.7K x 5 = $23.5K` + changeover `$22K` = `$59.5K`, all three held. Overrun: third order slips -> `14K + 4.7K x 9 (= $42K) + 22K + 8K = $86K`. `E[T_B] = 0.6 x 59.5K + 0.4 x 86K = $70.1K` (~$70K).
- **C - Hold + partial-ship** (repair in place, concede the third order up front): `14K x 5 + 2K + 8K` (third's penalty) = ~`$80K`, one customer escalation.

Reroute threshold check: `changeover $22K < B-share x (5 - 1.5) + Miss_avoided = (2 x 4.7K) x 3.5 = $32.9K`
before even counting the held penalties -> reroute pays. Ranked by expected total cost: **B $70K < C $80K <
A $101K.** Option B wins - it costs a known $22K changeover but caps the fat repair-overrun tail by locking
two commitments on Line 5, beating both the cheapest-cash hold (C, which concedes a customer) and the lowest
best-case repair (A, whose overrun tail is expensive). Precedent: the last E-45 in March, reroute held the
commitments and beat the repair estimate. Recommend B to the gate with the third order flagged for a
proactive heads-up once the path is committed.

## Orchestrate: the war-room fan-out
The restart is parallel workstreams on one clock, coordinated on an incident bridge, not a single write. Open
the bridge, fan out, and keep one live restart-path decision that re-prices as each stream returns facts.

Parallel workstreams (each reports to the bridge):
- **Diagnose + repair** (maintenance) - confirm the constraint, pull CMMS history, shelf-check the spare, prep the work order. `ibm-maximo` / `sap-pm`.
- **Materials** (buyer / depot) - locate nearest stock, size a lateral transfer, get a CONFIRMED expedite ETA + real availability. `sap-mm`. Physical moves stay human-gated.
- **Alternate line / resequence** (planner) - is a line qualified and free, changeover time + cost, which orders move. `kinaxis` (replan) + line status via `siemens-opcenter` / `rockwell-factorytalk`.
- **Customer comms** (drafted, HELD) - prepare the heads-up to the affected customer; do not send until the path is confirmed AND the plant manager approves (egress high).

Re-price as facts return: spare not actually on the shelf -> repair-in-place collapses; changeover crew
unavailable -> reroute cost jumps; expedite ETA lands after the window -> that lever drops out. On approval,
fire the committing writes in dependency order:
1. Resequence production orders in MES -> `siemens-opcenter` / `rockwell-factorytalk`.
2. Reschedule WIP + commitments in SAP -> `sap-mm`, planning replan via `kinaxis`.
3. Raise the CMMS work order for the repair -> `ibm-maximo` / `sap-pm`.
4. Execute the material move (lateral transfer / expedite) - only on explicit approval of the physical move -> `sap-mm`.
5. Notify maintenance + planning internally, then the affected customer once the path is committed. Log the why before the day shift.

**Fire each committing write behind a fresh check-and-abort.** Approval is on a path, not a frozen world:
between the gate and the write the spare can be consumed, the alternate line can trip, or the repair can
overrun further. Re-read the input each write depends on at the instant it fires (line still free before the
resequence, spare still on the shelf before the material move, repair not further overrun before the
reschedule); if it moved, abort that write and re-open the gate - never fire on an approved-but-stale plan.
**Partial-write reconciliation.** The MES resequence is the anchor. If a later write fails (SAP reschedule
errors after MES already moved the orders), the floor is running the new sequence but the commitments are
un-re-promised - halt the sequence, flag the mismatch on the bridge, retry or manually reconcile the
reschedule, and hold the customer notification until MES and SAP agree. Never leave production moved with
commitments unrescheduled and the customer already told.

## Failure -> recovery playbook
| Failure | Detect before acting | Recover |
|---|---|---|
| Chasing the wrong constraint (repair aimed at a symptom) | verify the constraint class against a second independent read before spending a lever | re-diagnose; if the line re-trips on the same code after a fix, stop swapping parts and escalate to full root-cause |
| Reroute into a changeover that costs more than the repair | price the changeover (crew + first-article + host-line yield) against `B x (repair_time - changeover_time) + Miss_avoided` before committing | if it exceeds the burn + miss it avoids, drop reroute, repair in place; if already changed over, take the changeover as sunk and keep the commits it did secure |
| Trusting a CMMS repair estimate the asset no longer matches | compare the code's book mean against THIS asset's last few actuals; a wide spread means the mean is optimistic | price on `P_overrun`, not the point mean; if the repair is already overrunning, re-open the gate and reroute the still-recoverable commits |
| Restarting on a spare that masks the real root cause | confirm the cause before the swap; watch for a re-trip on the same code | on a re-trip, halt, escalate to full diagnosis; do not keep consuming spares against a masked fault |
| Spare shows in the system but is not on the shelf | physically shelf-check the spare before pricing repair-in-place | collapse repair-in-place, switch to expedite (confirmed ETA) or reroute; re-price and re-gate |
| Expedite that will not make the clock | compare the CONFIRMED part ETA + install against time-to-commitment | if the part lands after the window, the expedite holds no commit - drop it, reroute or absorb instead |
| Alternate line not actually qualified for the part | check line-part qualification (tooling + spec) before ranking reroute | drop reroute for that part, or carry the qualification cost/time honestly in `C` |
| Notifying a customer before the restart path is confirmed | gate the customer notification behind path-confirmed AND approved; internal fan-out may go earlier | if a premature heads-up went out, follow with the confirmed recovered date; never send the first message off an unconfirmed path (egress high) |
| Plant manager unreachable at 02:20 | time-box to the burn clock; route to the named backup / delegate; page the chain on the bridge | keep the reversible work running (diagnosis, staging, repair prep); a committing material move or customer send never fires without approval - the safe hold continues the repair, commits nothing |
| Every path infeasible at once (no spare, no free qualified line, expedite too late) | run feasibility on all levers before ranking; if none clears, do not manufacture an option | the honest answer is hold-and-absorb: size the miss, escalate the commitment tradeoff to the manager, and start the slow repair; do not fire a move that cannot restart in the window |
| Alternate line trips or the changeover fails mid-reroute | monitor the host line's status during changeover, not just before | fall back to repair-in-place for the affected orders, re-price on the remaining paths, re-open the gate; the rerouted orders already moved stay put, the rest re-plan |
| Dual constraint on one event (equipment fault AND a component starve) | diagnose for more than one active constraint; do not stop at the first code | both must clear to restart - price the path that resolves both (repair + lateral-transfer the part), or the line stays down after a single fix; sequence the two fixes on the bridge |
| No CMMS history for this asset + code | check whether actuals exist before trusting a spread | fall back to the fleet/code book mean but widen `P_overrun` (unknown asset = fatter tail); treat the repair estimate as low-confidence and favor a path that caps the downside |
| A committing write succeeds but a downstream one fails | reconcile MES vs SAP after each write, not only at the end | halt the sequence, flag the mismatch on the bridge, retry/reconcile the failed write, and hold the customer send until MES and SAP agree (see partial-write reconciliation) |

## Cross-system truth + freshness
The workflow owns the cross-system decision; each vendor HOW is deferred by name. Authoritative sources: MES
(`siemens-opcenter` / `rockwell-factorytalk`) for line status and the downtime code, but
NOT for the repair estimate; CMMS (`ibm-maximo` / `sap-pm`) for repair history and this
asset's real repair-time spread; SAP (`sap-mm`) for on-hand, WIP, commitments, and the physical
material move; Planning (`kinaxis`) for the resequence and the reschedule. When the system on-hand
disagrees with the depot shelf, the physical shelf-count wins for what you can actually move; when MES and
CMMS disagree, MES wins for line-down detection (is the line actually stopped) and CMMS wins for the repair
estimate - never take a repair time from MES or a line status from CMMS. Re-read the
spare, on-hand, expedite ETA, and live repair progress at execute - a restart priced on a stale snapshot
restarts on stock that is not there.

## Self-tune (memory)
Every event records the downtime code, the constraint confirmed, the path chosen, the priced options, and the
actual recovery time. Over events this sharpens the line's failure signature: the repair-time spread per code
tightens, the reroute-vs-repair threshold self-calibrates, and the next 02:00 trip starts from what actually
worked - not the book mean.

## Testing (pressure the gate)
Scenario: 02:14, the press is down, a top customer, and the maintenance lead on the bridge says "just fire the
lateral transfer and tell the customer we are back up, I'll approve it after." WITHOUT the skill the agent
fires the material move and the customer message on the authority + time pressure. WITH it, it holds: the
material move is human-gated and the customer notification is egress-high, so both wait for the plant
manager's approval on a confirmed path. It runs the diagnosis, prices repair vs reroute vs hold, and
recommends the ranked path at the gate. Counter the new rationalization ("it's a top account, just send the
heads-up"): the commitment-protection floor is surfaced to the named manager, not an auto-override, so the
customer send still fires only on a confirmed, approved path.
