# Kinaxis - ATP, CTP, constraints, netting

Why a promise date out of Kinaxis is only as trustworthy as the data behind it, and how a scenario edit to a
constraint or a sourcing rule quietly re-plans real coverage. Read when a task promises an order, checks
availability, overrides a constraint, or changes sourcing/substitution.

## Contents
- ATP vs CTP (what each actually checks)
- Constraint types
- How CTP builds a promise (and where it leaks)
- Netting, allocation, sourcing, substitution
- The freshness rule

## ATP vs CTP (what each actually checks)
- **ATP (available-to-promise)** - checks a date/quantity against **existing and already-planned supply**
  (on-hand plus scheduled receipts, netted against prior commitments). It does not create new supply.
- **CTP (capable-to-promise)** - goes further: it **simulates pulling constrained capacity and material** to
  see whether new supply could be built in time, and returns a promise date based on that simulation. It
  answers "could we make it", not just "do we have it".
- An **inquiry** (either ATP or CTP that only checks and reserves nothing) is a safe read. A **confirm** that
  reserves supply/capacity for the order is a committing action - it allocates constrained supply that other
  orders can no longer use.

## Constraint types
- **Capacity** - work centers, resources, shifts, tooling. Limits how much can be produced in a bucket.
- **Supply** - supplier capacity, material availability, allocation from a vendor.
- **Lead time** - procurement and manufacturing lead times that set the earliest a supply can arrive.
- These constraints drive **constrained planning** and every CTP result. Overriding one in a scenario (add a
  shift, shorten a lead time, raise a supplier limit) is a valid what-if - but it changes the plan's
  feasibility **on screen only**, not the real world. Commit that override and every promise built on it
  assumes capacity or supply you do not actually have.

## How CTP builds a promise (and where it leaks)
- CTP walks the bill of material and the sourcing/capacity model, consuming constrained supply and capacity as
  it goes, to find the earliest feasible completion date.
- The result is only as accurate as the constraint data feeding it. If capacity, supplier capability, material
  availability or lead times are **stale or wrong**, CTP returns a date the plant cannot actually hit.
- That date does not stay internal - it **leaks onto the customer order** as a delivery promise. A promise
  built on bad constraints becomes a missed commitment to the customer, and a promise already sent cannot be
  unsent; you can only re-promise with corrected data and manage the customer relationship.
- Practical rule: before trusting or confirming a CTP date, check that the constraint and supply data are
  current (last sync) and that no uncommitted constraint override is inflating feasibility.

## Netting, allocation, sourcing, substitution
- **Netting** - the engine nets demand against supply to compute projected on-hand and shortages. Firmed and
  released supply is protected; planned supply is re-derived each run.
- **Allocation** - how scarce supply is shared across competing demands, by priority/fair-share rules. A CTP
  confirm allocates supply away from that pool.
- **Sourcing** - which plant/vendor supplies which demand. Changing a sourcing rule in a scenario re-plans
  coverage; commit it and you have re-routed real orders to a different source.
- **Substitution** - allowing an alternate material/component to cover demand. Turning one on changes which
  supply nets against which demand - a silent re-plan of coverage.
- None of these change the read/write/destructive class by themselves, but each changes **what the plan
  means**. Change one inside a scenario (reversible), commit it (committing), and the coverage you re-planned
  becomes the coverage real orders release against.

## The freshness rule
Two staleness axes decide whether a promise or a commit is safe: freshness vs **ERP** (last inbound sync) and
freshness vs the scenario's own **parent** (has the baseline moved since you forked). Check both before you
confirm a promise or commit a plan - the analytics are correct math on whatever data is loaded, and stale
data makes correct math produce the wrong answer.
