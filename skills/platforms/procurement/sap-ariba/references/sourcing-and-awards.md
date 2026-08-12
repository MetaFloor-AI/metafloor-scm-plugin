# SAP Ariba - sourcing events and awards

The upstream half of source-to-pay: how a competitive event runs, what publishing transmits, and why an
award is a governed commitment - not a document you quietly generate. Read when a workflow creates, publishes,
or awards a sourcing event, or reads bids. The one rule under all of it: an event is a *process*, an award is
an *outcome*, and neither is a contract or a PO.

## Contents
- Event types (RFI / RFP / RFQ / auction)
- Event lifecycle and states
- What publishing / inviting transmits (outbound)
- Sealed-bid / multi-envelope events
- Awarding and award scenarios (split award)
- Gating summary

## Event types (RFI / RFP / RFQ / auction)
- **RFI** - request for information; gathers supplier capability, no price commitment expected. Lowest stakes.
- **RFP** - request for proposal; scored on price + non-price criteria (quality, terms, capability). The
  common strategic-sourcing event.
- **RFQ** - request for quotation; price-focused on a defined spec.
- **Reverse auction** - live, real-time competitive bidding where invited suppliers bid the price *down* over a
  timed window; rank/lead feedback is shown per the auction rules. Publishing opens live bidding; you cannot
  pause or pull it back mid-auction without visible consequence to the suppliers watching.
Each is built from an **event template** that carries the content (line items, questions, terms) and the
timing/visibility rules. The template choice sets the governance - do not pick a lighter template to dodge review.

## Event lifecycle and states
- **Draft** - being composed; content, invited suppliers, timing, and rules are all editable. Reversible prep.
- **Published** - open to the invited suppliers; the preview/bidding period is live. Requirements are now
  outside the company. Edits after publish (amendments, timing extensions) are visible changes, not silent fixes.
- **Pending selection** - bidding closed; responses are in and being evaluated.
- **Awarded / not awarded** - the outcome is chosen (or the event closes with no award).
- **Cancelled / paused** - a published event that is stopped; the invited suppliers are notified. Un-publishing
  is not a clean rollback - they have already seen the requirements and quantities.

## What publishing / inviting transmits (outbound)
Publishing an event or inviting suppliers transmits requirements, quantities, specifications, and terms to
external parties over SAP Business Network. That makes it an **outbound, committing** act, not an internal save:
- Suppliers see your demand signal and quantities - a competitive and information-exposure event.
- Timing rules (open/close, preview) start running; late changes are amendments that re-notify suppliers.
- For an auction, the live bidding process itself begins - real suppliers are now competing in real time.
Treat publish/invite like sending an order outside: gate it, and know that un-publishing is messy at best.

## Sealed-bid / multi-envelope events
Some events split a supplier's response into **envelopes** (e.g. a technical envelope and a commercial/price
envelope) opened in stages by governance, so evaluators cannot see price while scoring technical merit. A
commercial envelope may be **unopened** when you read the event - its bid values are not yet legitimately
visible. Do not read, infer, or act on an unopened envelope's contents; respect the opening stage.

## Awarding and award scenarios (split award)
- An **award** selects the winning supplier(s) and the pricing/quantities to give them. Awarding **commits the
  sourcing outcome** and notifies the supplier(s) - it is the money-adjacent decision, gate it like issuing a PO.
- An **award scenario** models an allocation before you commit: full award to one supplier, or a **split award**
  across several under constraints (capacity, min/max, risk, savings). Saving/comparing scenarios is reversible
  analysis; **executing** the award is the committing step.
- A **split award** allocates business across multiple suppliers; each allocation feeds its own PO or contract.
  Do not collapse a split award into a single-supplier order - that mis-allocates committed business.
- An award is **not** a contract and **not** a PO. Realizing it as a contract workspace or as a requisition->PO
  is a further governed step with its own approval. Rescinding an award after notification is a new, messy action
  the supplier may already rely on.

## Gating summary
- Read: view event content, invited suppliers, timing, responses within the allowed window, award scenarios.
  Reading an unopened sealed envelope is off-limits by governance, not by API.
- Write (reversible): create/edit an event in draft; save/compare award scenarios.
- Write (committing): publish an event / invite suppliers (outbound); open/close an auction; execute an award.
- Destructive: cancel/un-publish a published event mid-flight; rescind an award after notification. Both notify
  external suppliers and cannot be cleanly undone - hard gate + named approver.
