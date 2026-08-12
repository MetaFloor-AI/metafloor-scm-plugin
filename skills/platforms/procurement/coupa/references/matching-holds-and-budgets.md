# Coupa - matching, AP holds, and budgets

The three mechanisms that decide whether a Coupa invoice pays and whether spend is allowed. Read when a
workflow reconciles an invoice against a PO/receipt, resolves a hold, or hits a budget check.

## Contents
- Matching: 2-way / 3-way / 4-way and tolerance
- AP hold types and how each clears
- Budgets: hard block vs soft warning, period scoping

## Matching: 2-way / 3-way / 4-way and tolerance
- **2-way** - invoice vs PO (price and quantity on the order). Used where no receipt is expected (some
  services, blanket spend). Nothing confirms the goods actually arrived.
- **3-way** - invoice vs PO vs **receipt**. The default for goods. The receipt is the physical-control leg:
  no receipt, no pass. This is why a wrong or premature receipt can let an invoice pay for goods not delivered.
- **4-way** - adds an inspection/quality confirmation on top of 3-way, for regulated or quality-gated buys.
- **Tolerance** - the allowed variance (price per unit, line total, quantity, tax) below which a match clears
  with no human. Within tolerance, an invoice can auto-approve; outside, it raises an exception -> hold.
- Raising a tolerance is not a config convenience: it pre-authorizes every future invoice to pass up to that
  variance with no reviewer. Treat a tolerance change as a committing control change.
- At execute, re-check the match state. A receipt posted or reversed after the invoice arrived changes whether
  the same invoice now matches; the earlier read goes stale.

## AP hold types and how each clears
A hold parks an invoice so it cannot export or pay. Clearing it is what authorizes payment, so every clear is
a committing-to-destructive action, not housekeeping.

| Hold | Set because | The clean fix | The override (destructive) |
|---|---|---|---|
| **Price hold** | invoice unit price > PO price beyond tolerance | supplier corrects, or PO is amended to the agreed price | approve the variance and release, paying the higher price |
| **Quantity hold** | invoice qty > received (or ordered) qty | post the missing receipt, or supplier corrects the invoice | release, paying for unreceived quantity |
| **Receipt hold** | 3-way match, no receipt yet exists | post the receipt when goods actually arrive | force through with no receipt |
| **Tax hold** | tax on the invoice fails the expected/compliance rule | supplier reissues a compliant invoice | override, risking a non-compliant tax record |
| **Match / tolerance hold** | totals outside configured tolerance | reconcile the line, correct the source | raise tolerance or approve the exception |

Rules: prefer the clean fix (correct the source document or post the real receipt) over the override. An
override pays despite the flag and is auditable; it needs the named approver and a logged reason. A supplier
hold is different: it blocks the supplier entirely, and no invoice for that supplier should be forced through
while banking or compliance screening is unresolved.

## Budgets: hard block vs soft warning, period scoping
- A budget is a spend limit scoped to a **period** (month, quarter, year) and a segment (cost center, account,
  project). The requisition/PO consumes it based on the commitment date.
- **Hard block** - if the requisition would exceed budget, submission is **refused**. This is a wall; the fix
  is a budget adjustment (its own approval) or reducing the spend, not an override reflex.
- **Soft warning** - the requisition shows a warning but **proceeds once acknowledged**. It does not stop the
  spend. The two look nearly identical on screen, so never assume a warning behaved like a block.
- Period scoping bites: spend posts against the period of the PO / need-by date, not the date you are working.
  A commitment logged to the wrong period overstates one month's remaining budget and understates another.
- A budget adjustment is a new entry, not an edit of consumed budget. You cannot un-consume a budget without
  cancelling the underlying requisition/PO that consumed it.
