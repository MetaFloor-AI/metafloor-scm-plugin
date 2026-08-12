# JAGGAER Sourcing, awards, and the ASO

Read when a task publishes/runs an event, reads bids, runs an optimization scenario, or awards. The rule
under all of it: an event is a *process*, an award is a *commitment*, and the ASO produces *scenarios*, not orders.

## Contents
- RFx types
- Auction types (live)
- Sealed-bid / two-envelope
- Event lifecycle + states
- The Advanced Sourcing Optimizer (ASO)
- Awards and split awards

## RFx types (build from an event template)
- **RFI** - request for information. Qualifying/scoping; not priced to award. Lowest blast.
- **RFP** - request for proposal. Scored on price + non-price criteria (weighted). Feeds an award.
- **RFQ** - request for quote. Price-focused for defined line items.
All are outbound once **published**: requirements, quantities, attachments, and terms go to invited suppliers
over the JSN. Publishing is committing (external exposure), even though no money moves yet.

## Auction types (live, real-time)
- **Reverse (English) auction** - price descends as suppliers underbid each other; buyer-side lowest wins.
- **Japanese auction** - the system announces a price; suppliers accept or decline to stay in; price moves each round.
- Ranked / rank-only variants show a supplier its rank, not competitors' prices.
Once a live auction is published you cannot quietly pull it back mid-event - bids and rank are visible to the
invited suppliers, so pausing/cancelling has a visible consequence. Treat open/close of an auction as committing.

## Sealed-bid / two-envelope
Common in public-sector and higher-ed sourcing (JAGGAER's SciQuest heritage). Bids arrive in envelopes that
open in a governed sequence: the **technical** envelope is evaluated first; the **commercial** (price) envelope
stays sealed until the technical stage completes or a formal bid opening. A commercial value may not be
readable yet. Reading or acting on an unopened envelope violates the process and can void the event - respect
the stage.

## Event lifecycle + states
draft -> published (bidding live) -> bidding closed (pending evaluation) -> awarded / not awarded / cancelled.
- **draft** - reversible prep; edit/delete freely.
- **published** - outbound and live; no clean undo (suppliers have seen it); you extend or amend, not un-publish.
- **bidding closed** - responses locked for evaluation; envelope rules still apply.
- **awarded** - the committing outcome (below).

## The Advanced Sourcing Optimizer (ASO)
Optimization-based sourcing (BravoSolution heritage). Suppliers submit **expressive / conditional bids**:
volume tiers, bundles, discounts conditional on total award, capacity limits, alternates. The ASO solves for
the optimal allocation under business constraints (number of suppliers, min/max split, incumbency, sustainability).
- **Building + running scenarios is analysis (read-class).** A scenario is a *what-if*, not a decision. You can
  run many scenarios, change constraints, and compare total cost - nothing is committed.
- **Applying/awarding a scenario is the committing act.** Only when you push a scenario through the award step
  does it select suppliers and notify them. Do not treat "optimal scenario computed" as "awarded".

## Awards and split awards
- An **award** selects supplier(s), price, and quantity from the event and **notifies the winner(s)**. It feeds a
  contract or a PO; it is **not** itself a contract or a PO.
- A **split award** allocates the business across several suppliers under constraints; each allocation feeds its
  own PO/contract. Do not collapse a split award into a single-supplier order.
- Rescinding an award after notification is a new, high-blast action the supplier may already rely on; re-award
  is a fresh selection, not an edit.
