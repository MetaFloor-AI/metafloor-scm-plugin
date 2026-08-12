# Ivalua sourcing, awards, and invoice matching

Read when a task publishes/awards a sourcing event or eAuction, applies a Decision Center scenario, or works
an invoice match/exception. The rule under all of it: publishing is outbound, a scenario is not an award,
awarding commits, and an out-of-tolerance exception will not pay until someone overrides it.

## Contents
- RFx types
- eAuction formats
- Sealed-bid / multi-envelope
- Sourcing Decision Center (optimization + scenarios)
- Awards and split awards
- Smart matching and tolerances
- Exception / hold types
- Non-PO and contract-based invoices

## RFx types
- **RFI** (information) - gathers supplier capability/data; not a price commitment.
- **RFP** (proposal) - solicits scored proposals on weighted criteria.
- **RFQ** (quote) - solicits priced quotes for comparison.
Publishing any of these transmits requirements and quantities to invited suppliers and opens their response
window. That transmission is outbound and committing; un-publishing is messy and suppliers have already seen it.

## eAuction formats
Live, real-time competitive bidding, often across multiple lots:
- **Reverse auction** - suppliers bid the price down.
- **English** - ascending open bidding.
- **Dutch** - price moves until a supplier accepts.
- **Japanese** - a moving price with accept/decline at each level.
Once published, bids move in the open; you cannot quietly pull an auction back mid-flight without visible
consequence to the invited suppliers.

## Sealed-bid / multi-envelope
Technical and commercial envelopes open in stages by governance (common in public-sector/regulated sourcing).
A commercial bid value may not be readable until its envelope opens; reading or acting on an unopened envelope
violates the process. Respect the envelope stage.

## Sourcing Decision Center (optimization + scenarios)
Ivalua's optimization engine evaluates all bids, constraints, and supplier data (cost, risk, performance,
quality) to compute allocation scenarios, including expressive/conditional bids and volume tiers. Key rule:
**a scenario is analysis, not an award.** Building and running what-if scenarios is read-class; "optimal
scenario found" is not "ordered". The commit is **applying/awarding** the chosen scenario through the award step.

## Awards and split awards
An **award** selects supplier(s), price, and quantity from an event - full to one supplier or **split** across
several under constraints. Each allocation in a split award feeds its own PO/contract; do not collapse a split
award into a single-supplier order. Awarding notifies the winner(s) and commits the sourcing outcome; an award
is not itself a contract or a PO - it feeds one, and each of those is a separate governed step with its own workflow.

## Smart matching and tolerances
Ivalua's **smart matching** runs the invoice against PO + receipt + contract + tax:
- **2-way** (PO + invoice) or **3-way** (PO + receipt + invoice), per the client's config.
- Auto-assigns budget/cost center/account by configurable rule.
- Can **auto-match a non-PO invoice** to a contract or receipt.
Tolerances are the client-configured variance bands under which a match auto-clears with no human. Because
tolerances and rules are configurable, verify them: a client set to zero/manual tolerance routes every
exception to a person, and a mis-configured rule can auto-code and auto-pass an invoice nobody reviewed.
Raising a tolerance pre-authorizes every future variance up to that gap.

## Exception / hold types
When the match fails outside tolerance, the invoice is parked as an **exception/hold** (price, quantity,
receipt-missing, tax, additional-item, PO-amount). It will not pay until the exception is **released/overridden**
(committing/destructive) or the source is fixed. An out-of-tolerance override authorizes payment despite the
mismatch - route it to the named approver; fixing the source (receipt/price/tax) is the non-destructive path.

## Non-PO and contract-based invoices
A **non-PO** invoice has no PO leg; it matches a contract or nothing. Ivalua can auto-match it to a contract,
which is convenient but can grab the **wrong** contract and mis-net the spend. Treat a non-PO/contract-based
invoice as higher-risk: verify the matched contract and the auto-assigned coding before releasing, and give it
extra scrutiny because there is no committed order behind it.
