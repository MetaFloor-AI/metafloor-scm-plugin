# Blue Yonder TMS - rating and freight settlement (audit & payment)

How a load's cost is computed and how the carrier gets paid. Read when a task rates/re-rates a load, works a
freight invoice, or approves settlement. Rating commits nothing; approving a settlement pays money out.

## Contents
- Rating - what makes up the cost
- Rate tiers, weight/class breaks, accessorials, FSC
- Freight audit and payment (the 3-way match)
- Self-invoice / auto-pay
- Recovery - credits, adjustments, periods

## Rating - what makes up the cost
- Rating computes a load's cost from **rate tables** under a carrier contract for the **lane + mode + service
  + effective date**, plus **accessorials** and **fuel surcharge (FSC)**.
- Rating is a **read of the cost basis** - it persists a rate on the load but commits nothing; a re-rate
  overwrites it. It is only current for the rate's effective-date window and the current mode/weight/lane.
- A rate is meaningless without lane + carrier + mode + effective date. Rating the wrong lane/mode/date returns
  a plausible but wrong cost that then anchors the tender and the settlement - the error propagates silently.

## Rate tiers, weight/class breaks, accessorials, FSC
- **Weight / class breaks** - LTL rating uses freight class and CWT (per-hundredweight) brackets; a load can
  fall into a different bracket at a weight threshold. A **re-weigh/re-measure at execute can jump the load
  into a different tier**, changing the **base** cost - not an accessorial add-on, and not caught by an
  invoice-tolerance check on the base rate.
- **Accessorials** - detention, layover, lumper, stop-off, redelivery, etc. They add to the payable **without**
  changing the base rate. Approving accessorials without provenance overpays.
- **Fuel surcharge (FSC)** - a separate, index-driven charge on top of the base. A wrong FSC basis mis-prices
  the whole load.
- Mode changes the whole model: TL (per-mile/flat), LTL (class + CWT), parcel (zone/weight), ocean/rail
  (per-container/allocation). Rating the wrong mode returns the wrong number.

## Freight audit and payment (the 3-way match)
Freight Audit and Payment (FAP) / freight settlement reconciles what you agreed to pay with what the carrier
billed, before money leaves.
- The carrier invoice arrives (**EDI 210**). The audit **matches** it to the load's rated/expected cost
  within a **tolerance** (absolute or %).
- **Passed** (within tolerance) -> ready to approve/pay. **Failed / over-tolerance** -> an **exception** that
  must be resolved (accept the carrier's charge with provenance, dispute it, or correct the rate) before pay.
- **Approving the settlement / releasing payment is money out** to AP/the carrier - a ledger event, not a
  note. Approving an unaudited or over-tolerance invoice pays money that was not earned.
- Approving past an unresolved over-tolerance variance overpays **and** buries the exception - the variance is
  where accessorials, reweighs, and detention surface; resolve it, do not approve through it.
- The audit must match the invoice against the **rate effective on the shipment/service date**, not today's
  rate. A contracted rate can expire or be superseded between the tender and the arrival of the 210 - matching
  on the current rate instead of the shipment-date rate manufactures a false variance (or hides a real one).
- Blue Yonder posts the approved payable to **AP/ERP**. A settlement posted/backdated into a **closed finance
  period** misstates it - that is a finance decision in the current open period, not a workaround.

## Self-invoice / auto-pay
- **Self-invoicing / auto-pay** generates the payable **from the load's rated cost** with no carrier invoice
  to match (common for contracted lanes / ERS-style settlement).
- The rated cost **IS** the payment basis. If the rate is wrong (wrong lane/mode/date, wrong tier, a bad
  accessorial), Blue Yonder pays the wrong amount automatically and nothing flags it. Verify the rate before
  trusting self-invoice for a load.
- An **auto-audit** that auto-approves within tolerance is a committing actor - a wrong rate flows straight to
  payment. Gate it or verify the rate provenance.
- A **re-rate while self-invoice/auto-pay is active** silently changes the payment basis for the imminent
  auto-pay. Do not treat that re-rate as a benign refresh - it is committing (money) while auto-pay is live.

## Recovery - credits, adjustments, periods
- **Void / reverse an issued payment or settlement** - a financial reversal downstream in AP/ERP; coordinate
  with finance, do not treat it as a delete from the TMS.
- **Overpaid / wrongly approved** - corrected by a credit or adjustment (a new/adjusting settlement), not by
  un-approving; the original approval stays in the trail.
- **Cost changed after settlement** - re-rating the load does **not** rewrite an already-posted payable; a
  corrected cost needs a new or adjusting settlement, or the books and the plan disagree.
- **Closed period** - finance-owned; correct in the current open period, do not reopen from the TMS.

Gating note (aligned to the SKILL.md matrix): rate / re-rate a load = **Write (reversible)** (non-committing,
overwritten on re-rate) - **except** a re-rate while self-invoice/auto-pay is active, which changes the payment
basis and is **committing**. Approve settlement / release payment, override a failed audit, approve
over-tolerance, void/reverse a payment, post into a closed period = **Destructive** (money out / ledger move).
