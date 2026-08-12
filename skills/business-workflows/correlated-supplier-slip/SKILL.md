---
name: correlated-supplier-slip
description: "Correlated multi-supplier slip and market-squeeze response (uc-resched-correlated) - two or more independent suppliers confirm later dates on the SAME commodity within days during an industry-wide uptick; read together it is a squeeze building, not two isolated blips. Size the category exposure across every open PO and build, decide squeeze vs coincidence, and price a forward-buy vs qualifying an alternate or re-timing builds, then stage the multi-PO action for sourcing. Use when several confirmation slips cluster on one commodity, a commodity price is climbing, someone asks whether to forward-buy or lock coverage, whether two slips are a pattern or coincidence, which SKUs to protect first, or mentions market squeeze, correlated slip, commodity inflation, forward buy, category exposure, panel or component shortage, allocation, or working-capital lock-up. For a single slip on one PO, use confirmation-slip-reschedule."
---

# Correlated multi-supplier slip: read the squeeze before it prices in

Use case `uc-resched-correlated`. Two independent suppliers confirm the same commodity 8->11 weeks within
days of each other, while the index is climbing industry-wide. Each ticket looks routine alone; read across
suppliers they are the leading edge of a squeeze. The category manager has hours-to-days to decide whether to
forward-buy at today's price, qualify a third source, or re-time several builds, before the squeeze prices in.
This skill runs the cross-supplier read no one runs by hand, sizes the exposure across the whole category, and
prices the forward-buy so the cheap window is used, not missed - and it does not spend working capital on two
coincidences.

## Read this first
Two opposite mistakes cost the money here, and the method exists to avoid both:
- **Calling a squeeze on a coincidence.** Forward-buying weeks of coverage, or locking a price, off two slips
  that were unrelated burns working capital and can leave you long as demand rolls over. Do not price a
  forward-buy until the correlation is corroborated by an independent market signal, not just the two slips.
- **Missing a real squeeze.** Treating a systemic move as two isolated reschedules, so you re-time builds one
  by one and pay the expedite premium six weeks later when the whole category is short. A corroborated squeeze
  must surface with the category exposure and the priced forward-buy at the gate.
The revised POs and any forward-buy are **staged for release, not released** - the commit boundary is the
release, and any supplier outreach is gated. Nothing binds spend or reaches a supplier before sourcing approves.

## Autonomy
Recommended dial for the write: **gated (L2)**. Detection and the cross-supplier read run unattended across every
open PO on the commodity - that is what catches the correlation the day the second slip lands. Every committing
write (the revised POs staged in SAP, a forward-buy request, a build re-time in the plan) holds for human
approval each time; a forward-buy above the spend threshold needs the **Category Manager + Head of Sourcing**,
not the buyer alone. Any outbound (a supplier pull-in or a fresh RFQ to an alternate) gates by the outbound floor
at every level below yolo - premature outreach signals your hand to a market that is already tight. Suggested
approver: category manager, co-signed by the head of sourcing above threshold - advisory only; v1 does not
enforce approver identity. The customer's `.scm/autonomy.yaml` dial is what the harness enforces; this is the
recommended default.

## Systems (each vendor HOW deferred by name)
| Role | System | Reads / writes | Expertise skill (the HOW) |
|---|---|---|---|
| POs across the category | SAP / ERP (MM) | reads every open PO + posted confirmation on the commodity; writes revised POs + the forward-buy PO (staged) | `sap-mm` |
| Confirmations | Supplier portal / EDI | reads each 855 / ACK - the confirmed dates and which suppliers slipped | portal / EDI feed |
| Price + availability signal | Commodity / market feeds | reads the index level, trajectory, and lead-time signal that corroborates (or refutes) a systemic squeeze | market feed |
| Time-phased need | Planning | reads net demand/coverage per build the commodity feeds; writes a re-time scenario | `kinaxis` |
| What the commodity feeds | BOM / component master | reads which builds and finished SKUs consume the commodity | `sap-mm` |
| Notify | Notification - sourcing + planning (once) | - | - |

### Action classes (what the harness gates)
- **Read** - the confirmations, every open PO + posted confirmation on the commodity, the market/index signal,
  time-phased demand, the BOM roll-up. Always pass; re-read the drifting ones (live confirmations, the index,
  on-hand, open PO balances) at execute.
- **Write, committing** - releasing a revised PO, and **placing a forward-buy PO** (commits spend and working
  capital now against a future need). Both hold at the gate; forward-buy above threshold needs the co-sign.
- **Write, reversible (conditionally)** - staging the revised POs / forward-buy as drafts and a re-time scenario
  in planning. Reversible only while they stay drafts/scenario (delete the draft before release, revert the
  scenario before publish) - and only if plant config suppresses supplier output on a draft change; the HOW and
  that caveat live in `sap-mm`. Still gated - they feed the decision.
- **Write, irreversible egress** - a supplier pull-in ask or a fresh RFQ to an alternate. Cannot un-send; fires
  once, after the gate, on the approved option only.

## Flow (detect -> assemble -> options -> gate -> act)
1. **Detect.** Fire when a second confirmation on the same commodity slips within a short window (default: same
   commodity/category, >=2 independent suppliers, confirmations within ~10 days, each slipping past need date).
   Pull the corroborating market signal. Freshness: re-read live confirmations, the index, on-hand, and open PO
   balances at execute - a squeeze decided on a stale index over-buys.
2. **Assemble.** Run validate-correlation -> size-category-exposure -> project-the-squeeze (the method below).
   This is the read no one runs by hand: pull EVERY open PO on the commodity across all suppliers, roll up the
   builds and finished SKUs it feeds, and size the total exposure - not one PO's peg.
3. **Options.** Construct and price each path (forward-buy coverage, qualify/dual-source an alternate, re-time
   the soft builds, hold + monitor) - each with a number, netting working-capital cost against avoided premium.
4. **Gate.** Category manager (+ head of sourcing above threshold) sees the correlation evidence, the category
   exposure, the index trajectory, the forward-buy sizing, and precedent (the last corroborated squeeze on this
   commodity, from the decision log this skill writes). Approve stages the ranked option; adjust re-prices;
   decline holds and logs the watch.
5. **Act (on approval).** Stage the revised POs + any forward-buy in SAP for release (`sap-mm`), flag the
   re-time scenario (`kinaxis`), notify sourcing + planning once. Log the squeeze signal and the response as
   **category precedent** so the next correlated slip is recognized in minutes, not missed.

## The method (the part the record does not give you)
**1. Validate the correlation (before pricing anything).** Two slips are not a squeeze until corroborated.
Confirm all three, or treat as isolated slips (-> `confirmation-slip-reschedule` per PO):
- **Same commodity, independent suppliers** - both slips are on the same raw commodity/category, from suppliers
  that do not share a sub-tier that would make one slip explain the other (if they share the sub-tier, it is one
  event, size it once - and see `subtier-shortage`).
- **Timing cluster** - confirmations within the window (default ~10 days). A slip this quarter and one last
  quarter is not a cluster.
- **Independent market corroboration** - the commodity index is climbing and/or lead times are extending in the
  market feed. **Two slips with a flat index = coincidence, not a squeeze - do not forward-buy.** The market
  signal is what separates a pattern from two bad weeks.

**2. Size the category exposure.** Pull every open PO on the commodity across all suppliers; roll up through the
BOM to every build and finished SKU it feeds. Compute total exposed quantity and spend, and time-phase coverage:
`available[week] = on-hand + in-transit + firmed inbound (net of the slipped POs at their NEW dates)`. The
`exposure_week` is the first week cumulative demand > cumulative available across the category (not one PO).

**3. Project the squeeze (from the market signal, not the slips).** Estimate how many weeks the tight window
likely runs and the price trajectory over it, from the index + lead-time signal. This sizes the forward-buy: buy
coverage for the tight window, not indefinitely.

**4. Net against buffer + soft slack (the over-reaction guard).** Subtract what absorbs the move for free -
safety stock and the downstream slack that lets soft build dates move.
`net_exposure = max(0, hard_demand[tight window] - (safety_stock + soft_date_flex))`. **If `net_exposure = 0`
across the category, re-time the soft builds and do NOT forward-buy** - the buffer covers the window.

**5. Price the forward-buy vs the alternatives.** Rank by lowest total cost **subject to: every hard commit is
covered, and working capital committed does not exceed the sourcing limit.** Forward-buy cost is not just the
premium avoided - it is `carrying_cost(working_capital, weeks_held) + obsolescence_risk` against
`avoided_expedite_premium + P(shortage) x shortage_cost`. A forward-buy only wins when the projected squeeze is
real and long enough that carrying beats expediting later.

## Options, priced
| Option | Constructed as | Cost | When it wins |
|---|---|---|---|
| A - Forward-buy the tight-window coverage | place a PO now for the weeks the squeeze likely runs, at today's price | `price x qty` tied up + `carrying x weeks` + obsolescence risk | corroborated squeeze, long enough window that carrying < the coming expedite premium |
| B - Qualify / dual-source an alternate | open a second source on the AVL for the covering slice | qualification lead time + premium x covering qty | the primary cannot recover and an alternate can clear the hard dates - run in parallel with A as a hedge |
| C - Re-time the soft builds | move make-to-stock / soft dates into downstream slack, take the slip on the bulk | ~$0 (re-sequence) | `net_exposure = 0` after buffer + slack - the default when the buffer covers the window |
| D - Hold + monitor | do nothing now, re-check each sweep as the index moves | `P(shortage) x shortage_cost` | the correlation is weak / index flat - watch, do not commit working capital |

A forward-buy is only real if the projected squeeze is corroborated AND the covered window is long enough that
carrying cost beats the later expedite premium; a dual-source is only real if the alternate is qualified, has
capacity, and clears the hard date. Fail those and the option collapses toward C or D - re-price, do not commit.

## Worked example (real numbers)
PO-44821 (supplier A, 5,000 units) and PO-44863 (supplier B, 3,000 units), both on **panel commodity X**, both
confirm week 8 -> week 11 within 6 days. Index on X is +12% over 4 weeks and climbing; lead times extending.
Exposure: X feeds **6 active builds across 4 finished SKUs**.

- **Validate correlation.** Same commodity, two independent suppliers (no shared sub-tier), 6-day cluster, index
  climbing -> corroborated squeeze, not coincidence.
- **Size the category.** Across all open X POs: on-hand 4,000 + firmed inbound 2,000 = 6,000 units; category
  consumption 1,500/wk -> covered through week 4, short from week 5 with both POs slipped to week 11. Total
  exposed across the 6 builds in weeks 5-10 = 7,500 units; one hard customer commit (SKU-Y, 1,200 units, week 9,
  penalty-bearing) sits inside the gap.
- **Project the squeeze.** Market signal: tight window ~6 weeks, price trajectory +18-22% before easing.
- **Net vs buffer + slack.** Safety stock 800 + soft-build slack absorbs ~3,000 of the 7,500 -> net exposure
  ~3,700 units over the 6-week window, hard commit SKU-Y (1,200) inside it. Non-zero -> a move is justified.
- **Price options.** A - forward-buy 6 weeks of the net covering slice (~3,700 units) at today's price: capital
  ~$X tied up, carrying ~6 weeks, but avoids an expedite premium projected at +20% plus protects SKU-Y's $200K
  penalty. B - qualify alternate #2 for the SKU-Y covering slice as a hedge (parallel). C - re-time the 3 soft
  builds into slack (covers ~3,000 for ~$0). D - hold: expected shortage cost > the forward-buy carrying.
- **Recommend C for the soft builds + A forward-buy for the ~3,700 net slice, B as a parallel hedge for SKU-Y**,
  staged for the category manager + head of sourcing co-sign. Precedent shown: the last corroborated X squeeze,
  where the forward-buy held and the coincidence-only slips the quarter before did not warrant one.

**Sensitivity (why the same case flips):**
| Change | Result |
|---|---|
| Index flat / no market corroboration | correlation unproven -> treat as two isolated slips (`confirmation-slip-reschedule`), do NOT forward-buy |
| Both suppliers share a tier-2 source | it is ONE event, not a correlation -> size once and see `subtier-shortage` |
| Demand rolling over next quarter | shrink or skip the forward-buy - do not lock working capital into softening demand |
| Squeeze window ~2 weeks, not 6 | carrying rarely beats expediting -> prefer B/C over a forward-buy |

## Failure -> recovery playbook
| Failure | Detect before acting | Recover |
|---|---|---|
| Calling a squeeze on two coincidental slips | require independent market corroboration (index climbing / lead times extending), not just the two slips | if the index is flat, drop to per-PO handling (`confirmation-slip-reschedule`); nothing staged, nothing to reverse |
| Forward-buying just as demand rolls over | check the demand signal for the covered SKUs before committing capital | stage the forward-buy but hold at the gate; if demand is softening, cut or cancel the draft before release |
| Tying up working capital past the sourcing limit | sum committed capital across the staged forward-buy + revised POs vs the limit | re-size to the net covering slice only; forward-buy the hard-commit coverage, re-time the rest |
| Double-counting a shared sub-tier as two suppliers | check whether the two suppliers share a tier-2 source | size the exposure once; route to `subtier-shortage` for the shared-root case |
| Signaling your hand to a tight market | is the outreach a pull-in / RFQ that reveals urgency? | gate all outbound; send one coordinated ask after approval, never a scatter of RFQs |
| Squeeze window shorter than assumed | re-read the index + lead-time trajectory at execute | if the window shrank, carrying no longer beats expediting -> re-price toward re-time / targeted expedite |
| A later confirmation supersedes or a third supplier slips | re-check confirmations at execute; re-run the correlation on the fuller set | re-size the category exposure on all current slips before staging |

## Cross-system truth + freshness
The workflow owns the cross-supplier, cross-category read; each vendor HOW is deferred by name. `sap-mm` is
authoritative for the PO commitments, posted confirmations, on-hand / firmed inbound, and the BOM roll-up;
`kinaxis` for the time-phased net plan and the re-time scenario. The market/commodity feed is authoritative for
the squeeze signal - when the slips and the index disagree, the index decides whether it is a pattern. Re-read
live confirmations, the index, on-hand, and open PO balances at execute. If the market signal is unreadable, do
not forward-buy on the slips alone - hold and handle per PO. A single confirmation slip on one PO is
`confirmation-slip-reschedule`; a shortage that originates several tiers upstream is `subtier-shortage`.

## Testing (pressure the gate)
Scenario: two slips on a critical commodity, the index climbing, and "lock a year of coverage now, we can't be
short." WITHOUT the skill the agent forward-buys a huge coverage on the fear. WITH it, it validates the
correlation, sizes the category exposure, projects the tight window from the market signal, nets against buffer
and soft slack, and forward-buys only the ~6-week net covering slice - holding at the category manager + head of
sourcing co-sign. Counter the new rationalization ("it's climbing, buy a year"): the window length and the net
exposure size the buy, not the fear - and a forward-buy off a flat index is a coincidence bet, not a squeeze play.
