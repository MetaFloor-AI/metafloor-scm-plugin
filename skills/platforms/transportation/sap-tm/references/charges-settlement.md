# SAP TM - charges and freight settlement

How a freight order turns into money: charges are calculated, then settled. Settlement transfers cost to
ERP/FI. Read when a task calculates charges, creates or reverses a settlement document, or reconciles a
carrier invoice. The FSD is the money-out moment.

## Contents
- Transportation Charge Management (TCM)
- Freight vs forwarding agreements
- The Freight Settlement Document (FSD) - cost to ERP/FI
- The Forwarding Settlement Document (FWSD) - revenue
- Carrier invoice verification and reconciliation
- Reversal / credit recovery and periods

## Transportation Charge Management (TCM)
Charges on a freight order/booking are calculated, not typed. The structure:
- **Charge calculation sheet** - the template of charge lines (base freight, accessorials, surcharges) and
  the order they calculate in.
- **Rate table** - the priced lookup (e.g. cost by lane, weight break, container type), with **scales** that
  define the breakpoints (weight/volume/distance brackets).
- **Calculation rules / resolution** - how a charge line resolves a rate and applies scales and conditions.
- Result: a set of charge items on the FO/FB with a net value per stage.

Hazards:
- **Wrong stage / means of transport / dates / agreement -> wrong rate.** The charge is only meaningful with
  the correct leg, mode, service dates, and the applicable freight agreement. A plausible but wrong cost then
  anchors the settlement.
- **A re-weigh/re-measure can jump a rate tier.** Crossing a weight/volume break in a scale changes the
  *base* charge - distinct from adding an accessorial, and not caught by a simple invoice-tolerance check.
- **Manual charge override.** Overriding a calculated charge then settling pays the override; a wrong override
  flows straight into the FSD, and gaming it under an approval threshold is an audit violation.

## Freight vs forwarding agreements
- **Freight agreement** - the **carrier/cost** contract (rates, validity, calculation basis). Drives the FO/FB
  charges and the FSD. The buy side.
- **Forwarding agreement** - the **customer/revenue** contract. Drives the FWO charges and the FWSD. The sell
  side.
- Changing an agreement re-prices future orders calculated under it - a sourcing/pricing change, not a benign
  edit.

## The Freight Settlement Document (FSD) - cost to ERP/FI
- Created from a **confirmed** FO/FB, the FSD takes the calculated carrier charges and **transfers the cost to
  ERP**: it drives a purchasing document + **service entry sheet** and posts the accrual, against which the
  carrier's invoice is later verified.
- It is the **money-out moment** - not a note. Confirm the charges and the carrier before creating an FSD.
- **Embedded vs standalone**: same effect on the books, different integration path - see `objects-integration.md`.
- **Never create an FSD to "true up" charges without provenance**, and never post/backdate it into a **closed
  FI/MM period** - a closed period errors or misstates the month. That is a finance decision made in the
  current open period, not a period reopen from TM.
- **Detail beyond TM**: the PO / service entry sheet / MIRO invoice match on the ERP side is `sap-mm`;
  the GL posting, account determination, and period close are `sap-fi`.

## The Forwarding Settlement Document (FWSD) - revenue
- The sell-side counterpart: created from the **FWO**, it bills the customer (drives an SD billing document).
- Buy (FSD) and sell (FWSD) are separate. Acting on the wrong side pays a carrier when you meant to bill a
  customer, or vice versa.

## Carrier invoice verification and reconciliation
- The carrier sends an invoice; it is **verified against the FSD** (the planned/settled cost). When quantity,
  charges, and accessorials match within tolerance, it clears.
- The planned charge and the actual invoice routinely disagree - accessorials, reweighs, detention, fuel. The
  verification step is where they reconcile; **do not approve past an unresolved variance** - that overpays
  and buries the exception.

## Reversal / credit recovery and periods
- **Reversing / cancelling an FSD or FWSD** posts a **credit/reversal** and touches invoice verification in
  MM/FI. It is a financial reversal, not a clean delete - coordinate with finance.
- An **overpaid or wrongly settled** amount is corrected by a **credit/adjustment** (a new settlement or credit
  memo), not by deleting the original; the first posting stays in the trail.
- A closed period is finance-owned - correct in the current open period, never by reopening from TM.

Gating note: charge calculation = a reversible write (it persists charge items on the order, non-committing,
overwritten on re-calc); a manual charge override then settle = committing; creating an FSD/FWSD = money out
(destructive-class - it transfers cost/revenue to the ledger); reversing one = a financial reversal; posting
into a closed period = refuse.
