# SAP IBP - planning operators and application jobs

The operators are the engines that write key figures in bulk. What decides the blast radius is not the
operator, it is the **target version** (baseline vs sandbox) and whether a **snapshot** was taken first.
Read when a workflow runs a copy, forecast, S&OP supply, inventory, snapshot, or Response run, or schedules
one as an application job.

## Contents
- How operators are run (interactive vs application jobs)
- Copy operator
- Statistical forecasting (Demand)
- S&OP supply operator (heuristic / optimizer)
- Inventory Optimization (IO)
- Snapshot operator
- Forecast error / accuracy
- Response (order-based) operators
- Application jobs and scheduling

## How operators are run
Operators run interactively (from the Excel add-in ribbon or a Fiori app) or as **application jobs**
scheduled/queued in the *Application Jobs* app with a job template (operator + planning filter + target
version + parameters). A job writes the whole selected scope in its target version. A bad template does not
misfire once; it re-runs on schedule and re-applies the overwrite every cycle.

## Copy operator - overwrite, not merge
Copies a source key figure into a target key figure/version for the selected scope. It **replaces** the
target cells entirely. Common uses: copy actuals into a version to seed it, copy statistical forecast into
consensus demand, copy a backup version back into the baseline (a restore). Because it overwrites, any
planner override made in the target after the source was last set is lost. Copying **into the baseline** is
committing; copying into the baseline with no prior snapshot is destructive.

## Statistical forecasting (Demand)
Runs the forecast models defined in *Manage Forecast Models* against history and writes the statistical
forecast KF for the selected scope. It replaces the output KF; manual forecast overrides in scope are wiped
unless held in a separate override KF or protected by a lock. Demand sensing produces a separate short-term
sensed forecast KF from recent orders/shipments. Reads history (actuals); writes forecast.

## S&OP supply operator (heuristic / optimizer)
Time-series supply planning from consensus demand. Three modes, very different results:
- **Unconstrained heuristic** - explodes demand through the supply chain ignoring capacity; shows what
  would be needed. Projected stock can go implausibly high.
- **Constrained (finite) heuristic** - respects resource/supply capacity using priority/quota rules;
  unmet demand appears as shortage.
- **Optimizer** - cost-based; minimizes total cost and may drop, delay, or re-source supply, so it can
  leave demand unmet by design.
Writes supply, production, transport, and projected-stock KFs. Running a different mode into the baseline
than the plan was built on silently changes the committed supply picture.

## Inventory Optimization (IO)
Multi-echelon (MEIO) computation of **recommended** safety stock / target inventory across the network,
balancing service level against holding cost and lead-time/demand variability. It writes recommendation
KFs; it moves no physical stock and creates no orders. Its output is only acted on when a supply run plans
to it. Do not read IO output as on-hand.

## Snapshot operator
Freezes the current values of a key figure into a snapshot KF stamped with a time/version. This is the
backup and accuracy-comparison lever: take a snapshot before any baseline-writing run so a "before" exists,
and compare later actuals against the snapshot to measure plan quality. No snapshot before an overwrite =
no restore path.

## Forecast error / accuracy
Computes error/accuracy measures (MAPE and similar) by comparing a forecast KF against actuals or a prior
snapshot over a lag. Read-only analytics; it writes only the error KFs. Editing past periods corrupts the
comparison.

## Response (order-based) operators
A separate order-level engine (not time-series):
- **Constrained Forecast Run / order-based planning run** - plans at order granularity against finite
  supply.
- **Deployment** - allocates available supply to demands/locations, producing stock-transfer/deployment
  proposals.
- **Confirmation / gating** - confirms order quantities/dates against the gating (limiting) factor.
Confirmations and deployment bind toward real customer commitments; re-running reshuffles allocations and
can de-confirm a promise already communicated. Releasing these to execution creates real orders/STRs.

## Application jobs and scheduling
Gating notes: an interactive operator into a **sandbox** version is reversible; the same operator into the
**baseline** is committing, and destructive if no snapshot exists. A **scheduled** job that targets the
baseline is a standing committing/destructive action - review its template (operator, target version,
filter) before enabling, because it repeats. Data-integration jobs (import/export) are covered in
`planning-area-and-key-figures.md`.
