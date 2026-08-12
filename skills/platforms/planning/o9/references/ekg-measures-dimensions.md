# o9 - the EKG, measures, dimensions, and rules

The data model that makes o9 different from a relational planning tool, and the places where "read a
measure, write a measure" is wrong. Read when a task edits measures, spreads a value across levels, touches
master data, or relies on a driver/rule.

## Contents
- The Enterprise Knowledge Graph (nodes, edges, propagation)
- Dimensions and levels
- Measures: input vs computed, storage grain
- Aggregation / disaggregation and the spreading basis
- IBPL rules and driver-based planning
- Version-independent / shared measures

## The Enterprise Knowledge Graph (nodes, edges, propagation)
The EKG (the "Digital Brain") represents the enterprise as a graph: **nodes** are dimension members (an item,
a location, a customer, a supplier), **edges** are relationships (item sourced-from location, location
ships-to customer, item substitutes-for item), and **measures** are values stored against grains of the
graph. The point of the graph is **propagation**: an edit to a driver measure or a rule flows along the edges
and re-derives every dependent measure automatically. That is o9's strength (concurrent, connected planning)
and its hazard - a change has non-local effects on measures you did not see on the grid. Before editing a
driver, know the dependency chain it feeds.

## Dimensions and levels
- A **dimension** is a master-data axis: Item, Location, Customer, Channel, Supplier, Time. Each has
  **levels** forming a hierarchy (Item -> Product Family -> Category; Location -> DC -> Region).
- Planning happens at a grain defined by a combination of dimension levels (e.g. Item x Location x Week).
- **Valid combinations (assortment)** decide which item-location-customer cells actually get planned. Adding a
  combination creates new cells; removing one drops the stored measure data for it.
- Dimension edits are **shared master data**, not scoped to your version or scenario. Adding/removing a member
  or changing a hierarchy changes what everyone plans and can invalidate stored data - admin/config territory.

## Measures: input vs computed, storage grain
- A **measure** is a value at a grain (Demand Forecast, Consensus Demand, Booked Orders, Supply, Projected
  Inventory, Safety Stock, Target Inventory).
- **Input (editable) measures** hold data you or a solver write. **Computed (rule-driven) measures** are
  derived by an IBPL rule from other measures and **cannot be edited** - a "set" either fails or edits an
  input underneath. Know which kind a cell is before writing.
- A measure is stored/computed at a specific **base grain**. A view may show it aggregated above that grain;
  what you type at the aggregate level is not stored there - it spreads down (below).

## Aggregation / disaggregation and the spreading basis
- Editing a stored measure **above its base grain** disaggregates the value down to detail by a **spreading
  basis** - usually another measure (historical share, a proportion measure).
- If the basis is **empty or zero**, o9 spreads the value **evenly**, or lands it nowhere. Either way it is a
  silent mis-distribution across the leaf cells - o9's single most common quiet error.
- Verify the basis measure has data at the target grain before editing above base level. When precision
  matters, edit at the base grain directly.
- Aggregation up is a sum/derivation defined by the rule; reading an aggregated number and assuming it is
  editable at that level is the inverse trap.

## IBPL rules and driver-based planning
- **IBPL** is o9's rule/expression language. It defines computed measures, the graph logic that derives and
  spreads values, and the drivers behind a plan.
- **Driver-based planning**: dependent measures are computed from **driver** measures via rules. You get the
  number you want by changing the driver, not by typing over the computed result.
- A **rule change** re-derives every dependent measure across the graph, for **all versions and planners**. It
  can silently restate committed plans. It is config with graph-wide blast radius - never a fix for one number
  under time pressure, and not reversible by "editing it back" without re-validating every dependent.

## Version-independent / shared measures
- Some measures (actuals, sales/stock history, many master-style reference measures) are **one copy shared by
  all versions**. Editing one in "my scenario version" is not sandboxed - it corrupts the shared history and
  the forecast seed every version reads.
- Before editing what looks like a historical or reference measure, check whether it is version-independent.
  If it is, treat the edit as committing/destructive on shared data, not a local sandbox change.
