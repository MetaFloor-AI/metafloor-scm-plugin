# Manhattan Active TM - Freight Audit and Payment (FAP), settlement, parcel billing

FAP is the money-out side: it matches the carrier invoice to the load cost, audits it, approves it, and pays.
Approving/paying, self-billing, and a parcel manifest close all commit money or start carrier billing. Read
when a workflow audits, approves, pays, disputes, or reverses a freight charge, or closes a parcel manifest.

## Contents
- The match -> audit -> approve -> pay flow
- 3-way freight audit and tolerances
- Self-billing / auto-pay
- Accessorials
- Parcel manifesting and billing
- Reversal / credit recovery
- Periods

## The match -> audit -> approve -> pay flow
- **Match** ties the inbound carrier invoice (EDI 210) to the shipment/load it belongs to.
- **Audit** compares the invoice against the expected cost and flags variances (rate, accessorial, weight,
  duplicate). An invoice within tolerance can auto-approve; one outside tolerance drops to an exception queue.
- **Approve** authorizes payment; **pay/settle** posts the payment to AP/finance. Approving/paying is money
  out - approving an unmatched or over-tolerance invoice pays money that was not earned.
- The audit is the control. Do not approve or pay past an unresolved variance.

## 3-way freight audit and tolerances
- The audit reconciles three numbers: the **planned cost** (from optimization/rating), the **tendered/accepted
  cost** (what the carrier agreed to), and the **carrier invoice** (what they billed).
- A tolerance (absolute or %) decides auto-approve vs exception. Setting the tolerance too wide auto-pays real
  overcharges; too tight floods the exception queue. Loosening a tolerance to clear a backlog pays unaudited
  freight - it is a control change, not housekeeping.
- Common variance causes: a **re-weigh/re-measure** that changed the rate tier (base cost, not an accessorial),
  an unearned or duplicate **accessorial**, detention/demurrage, or a fuel-surcharge index mismatch.

## Self-billing / auto-pay
- Under **self-billing / auto-pay**, FAP generates the payment *from* the shipment/load cost with **no carrier
  invoice to match** - the load cost IS the payment basis.
- If the load cost is wrong (wrong rate, wrong lane/mode/date, un-reconciled reweigh), FAP pays the wrong
  amount automatically and nothing flags it. Trusting self-billing on an unverified cost pays a wrong number.
  Verify the load cost before enabling/relying on auto-pay for it.

## Accessorials
- **Accessorials** are charges on top of the base rate: fuel surcharge, detention, TONU, liftgate, layover,
  reconsignment. Each needs a basis - an accessorial approval that is unearned or unsupported overpays.
- An accessorial is distinct from a base-rate change: a reweigh that moves the rate tier changes the *base*,
  not an accessorial, and a flat accessorial tolerance will not catch it.

## Parcel manifesting and billing
- Parcel shipments **rate-shop** for least-cost carrier/service and finalize at the **manifest close** (end of
  day or on demand). The close **locks the rate, prints the compliant carrier label, and transmits the
  manifest** to the carrier - which usually initiates carrier billing.
- A manifest close is committing, not a print job. **Reversing after close** means voiding the shipment/label
  *with the carrier* (they already have the manifest), not a local delete.
- A **service change after the label prints** voids the label and re-rates; do not silently swap service on a
  manifested parcel.

## Reversal / credit recovery
- **Void / reverse a paid or approved invoice** - a financial reversal downstream in AP/ERP; coordinate with
  finance, do not treat as a delete. An overpayment is corrected by a **credit or adjustment** (a new
  settlement / credit memo), not by un-approving - the original approval stays in the trail.
- **Dispute** an invoice before payment rather than paying and clawing back; a dispute holds the exception,
  a payment reversal is a ledger move.
- **Financially closing/finalizing a load** locks its cost basis for settlement; correct via a settlement
  adjustment, not by reopening the load.

## Periods
- A closed finance/FAP posting period is a wall. A payment/settlement into a closed month errors or misstates
  it; never backdate or reopen a period to force a settlement through - that is a finance decision in the
  current open period.

Gating note: approve, pay, self-billing pay, and parcel manifest close are all committing (money out or
carrier billing). Voiding a paid invoice, reversing a settlement, or reversing a manifest after close is
destructive - a ledger/carrier reversal, not a local undo.
