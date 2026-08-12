# SAP PM settlement and refurbishment

The maintenance order is a **cost collector**; settlement is how the collected cost leaves the order for a
receiver, and refurbishment is the special case where the receiver is a material value, not a cost center. The
hazard: settlement is a real CO/FI posting, period-bound, and a wrong or missing settlement rule strands or
misposts cost. Read when a workflow settles an order (KO88 / KO8G), sets or changes a settlement rule, works a
refurbishment (PM04) order, or reasons about where a maintenance cost lands.

## Contents
- Cost collection on the order
- The settlement rule and receivers
- Running settlement (KO88 / KO8G) and period dependence
- Refurbishment (PM04) valuation flow
- Sub-order rollup and the FI/CO and MM boundary

## Cost collection on the order
Cost accrues on the order from three sources, asynchronously:
- **Labor** - each time confirmation posts hours at the operation's **activity type** rate against the work
  center's cost center (a secondary CO posting).
- **Material** - each component goods issue (movement 261) posts the material's value from MM to the order.
- **External services / non-stock** - the vendor invoice for an externally-processed operation or a non-stock
  component posts to the order via the MM PO and invoice.
Because these post at different times, the order cost you read may not yet include an in-flight service invoice.
Do not settle assuming cost is final until the order's open PRs / POs are cleared.

## The settlement rule and receivers
The **settlement rule** (on the order header) says where the collected cost goes and in what proportion. SAP
often **auto-generates** the rule from the order-type settlement profile at order creation or release; the
default receiver (usually a cost center from the technical object or order type) can be wrong for the specific
order, so verify the rule and its receiver before settling rather than trusting the default. Common receivers:
- **Cost center** - the default for routine corrective / preventive maintenance (the maintenance is expensed).
- **WBS element / project** - for maintenance that belongs to a capital or shutdown project.
- **Asset** - when the work is capitalized (a betterment / major overhaul added to the asset's book value).
- **Order** - settling to another order (e.g. a superior order).
- **Material** - the refurbishment case (below).
A missing settlement rule strands cost on the order (it cannot fully settle or close); a wrong receiver posts
maintenance cost to the wrong cost object, which distorts both the maintenance budget and the receiver.

## Running settlement (KO88 / KO8G) and period dependence
- **KO88** settles one order; **KO8G** settles a batch (period-end collective run, often a background job).
- Settlement is not one event. A **periodic** (partial) settlement can run **each period before TECO** to move
  cost incurred so far, and a **final** settlement completes the order after TECO. So a single settlement run
  does **not** mean the order's cost is locked - more can accrue and settle until the order is business-completed.
  Do not treat the order as costed-and-done after one periodic settlement.
- Settlement is a **CO/FI posting** dated into a period. It requires the target period be **open**; a closed
  period blocks the settlement or forces the next open period.
- Reversing a settlement is possible **within the open period**; once the period closes, the settlement stands
  and any correction is a fresh posting in the current period, not an undo.
- Full settlement plus TECO lets the order be **business-completed (CLSD)**; CLSD then bars any further posting.

## Refurbishment (PM04) valuation flow
A **refurbishment order** repairs a **rotable** (a repairable spare that cycles between stock and use), and its
economics differ from a normal PM order:
1. The defective rotable is issued from stock into the order, usually at a **lower (damaged) valuation**.
2. Repair cost (labor, parts, external service) collects on the order like any other.
3. On completion the repaired part is **received back into stock** and the order **settles to the material**,
   **revaluing** the returned unit (its value rises by the repair cost, within the material's valuation rules).
Treating a PM04 like a PM01 (settling to a cost center) leaves the rotable mis-valued and the inventory wrong.
Split valuation is common on rotables (new vs refurbished value) - the valuation type matters -> `sap-mm`.

## Sub-order rollup and the FI/CO and MM boundary
- A **sub-order** settles up to its **superior order**; the superior cannot be fully settled / closed until its
  sub-orders are settled. Charge cost at the correct level or the per-asset rollup is wrong.
- The boundary: **PM** owns the order and the maintenance history, **MM** owns stock and valuation (the 261 value,
  the material master, the vendor PO/invoice), and **FI/CO** owns the cost centers, the settlement postings, asset
  accounting, and the period close. When the numbers disagree the gap is usually an in-flight posting between
  these ledgers - reconcile it, do not force one side to match. Cost-center accounting and the finance period
  close live in `sap-fi`; stock, valuation, and the MM period in `sap-mm`.
