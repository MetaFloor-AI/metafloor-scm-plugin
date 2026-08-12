# GEP SMART sourcing, awards, and N-way invoice matching

Read when a task publishes/awards a sourcing event or e-auction, applies a sourcing-optimization scenario,
or works an invoice match/exception. The rule under all of it: publishing is outbound, a scenario (or an AI
recommendation of one) is not an award, awarding commits, and an out-of-tolerance exception will not pay
until someone overrides it.

## Contents
- RFx types
- e-auction formats
- Sealed-bid / multi-envelope
- Sourcing optimization (scenarios + AI recommendation)
- Awards and split awards
- N-way matching and tolerances
- Exception / hold types
- Non-PO and contract-based invoices
- e-invoicing / tax compliance

## RFx types
- **RFI** (information) - gathers supplier capability/data; not a price commitment.
- **RFP** (proposal) - solicits scored proposals on weighted criteria.
- **RFQ** (quote) - solicits priced quotes for comparison.
Publishing any of these transmits requirements and quantities to invited suppliers and opens their response
window. That transmission is outbound and committing; un-publishing is messy and suppliers have already seen it.

## e-auction formats
Live, real-time competitive bidding, often across multiple lots:
- **Reverse auction** - suppliers bid the price down.
- **Forward / English** - ascending open bidding.
- **Dutch** - price moves until a supplier accepts.
- **Japanese** - a moving price with accept/decline at each level.
Once published, bids move in the open; you cannot quietly pull an auction back mid-flight without visible
consequence to the invited suppliers.

## Sealed-bid / multi-envelope
Technical and commercial envelopes open in stages by governance (common in public-sector/regulated sourcing).
A commercial bid value may not be readable until its envelope opens; reading or acting on an unopened envelope
violates the process and carries legal/regulatory exposure. Respect the envelope stage.

## Sourcing optimization (scenarios + AI recommendation)
GEP's sourcing optimization evaluates bids, constraints, and supplier data (cost, risk, performance,
quality) to compute allocation scenarios, including expressive/conditional bids and volume tiers. A MINERVA /
QUANTUM Intelligence agent may **recommend** a scenario. Key rule: **a scenario, and any AI recommendation of
one, is analysis - not an award.** Building and running what-if scenarios is read-class; "optimal scenario
found" is not "ordered". The commit is **applying/awarding** the chosen scenario through the award step.

## Awards and split awards
An **award** selects supplier(s), price, and quantity from an event - full to one supplier or **split** across
several under constraints. Each allocation in a split award feeds its own PO/contract; do not collapse a split
award into a single-supplier order. Awarding notifies the winner(s) and commits the sourcing outcome; an award
is not itself a contract or a PO - it feeds one, and each of those is a separate governed step with its own workflow.

## N-way matching and tolerances
GEP's **N-way matching** runs the invoice against PO + receipt + contract + tax:
- **2-way** (PO + invoice) or **3-way** (PO + receipt + invoice), per the client's config.
- Auto-assigns budget/cost center/account by configurable rule.
- The **Invoice N-Way Matching / Reconciliation Agent** can process a match **touchlessly** (no human) when
  it is within tolerance.
Tolerances are the client-configured variance bands under which a match auto-clears. Because tolerances,
rules, and touchless automation are configurable, verify them: a client set to zero/manual tolerance routes
every exception to a person, and a mis-configured rule or automation can auto-code and auto-pass an invoice
nobody reviewed. Raising a tolerance pre-authorizes every future variance up to that gap. A touchless-cleared
invoice was not human-reviewed - the tolerance/automation config is the only gate.

## Exception / hold types
When the match fails outside tolerance, the invoice is parked as an **exception/hold** (price, quantity,
receipt-missing, tax, additional-item, PO-amount). It will not pay until the exception is **released/overridden**
(committing/destructive) or the source is fixed. An out-of-tolerance override authorizes payment despite the
mismatch - route it to the named approver; fixing the source (receipt/price/tax) is the non-destructive path.
A **Fraud/Anomaly Detection Agent** flag is a separate stop: overriding it to push the invoice through is destructive.

## Amended PO over existing receipts (worked example)
A PO revised (price/qty) after receipts already posted throws match exceptions that are amendment
*artifacts*, and these can coexist with a real overbill on the same invoice. Distinguish them by date:
- PO line 10, 100 units at $10, revised to $12 on Mar 15.
- Receipt A posted Mar 10 (before the revision) for 60 units; receipt B posted Mar 20 (after) for 40 units.
- The invoice bills 100 units at $12. The variance on the 60 units received *before* the revision (billed at
  $12 vs the $10 in force when they were received) is an **amendment artifact** - acknowledge and proceed.
- But if the invoice also bills, say, 45 units against receipt B (which only received 40), the extra 5 units
  is a **real overbill**, not an artifact - route it to the named approver; do not clear it as an amendment.
Compare each line's receipt date to the PO revision effective date before deciding. Do not treat all
variances on an amended PO as one category, and do not override a real overbill as an artifact.

## Non-PO and contract-based invoices
A **non-PO** invoice has no PO leg; it matches a contract or nothing. The Matching Agent can auto-match it to
a contract, which is convenient but can grab the **wrong** contract and mis-net the spend. Treat a
non-PO/contract-based invoice as higher-risk: verify the matched contract and the auto-assigned coding before
releasing, and give it extra scrutiny because there is no committed order behind it.

## e-invoicing / tax compliance
The supplier's submitted invoice (portal PO-flip, cXML/EDI, or OCR capture) is its legal e-document. In a
country with an e-invoicing/tax mandate, a non-compliant invoice cannot be legally processed, and editing tax
on it can break the compliance record. Read the compliance status; have the supplier reissue a compliant
invoice rather than editing tax to force it. A closed accounting period is a wall - do not back-date a
receipt/invoice into it (`sap-fi`).
