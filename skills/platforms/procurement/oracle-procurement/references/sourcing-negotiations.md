# Oracle Sourcing - negotiations, evaluation, and awards

The competitive process that feeds a purchasing document. Read when a workflow touches an RFI/RFQ/auction,
a sealed two-stage event, a surrogate response, an amendment, or an award. The rule under all of it:
publishing is outbound to suppliers, awarding commits the outcome, and the sealed/approval controls exist to
keep the award defensible.

## Contents
- Negotiation types and styles
- The lifecycle and states
- Sealed and two-stage evaluation
- Responses, surrogate responses, controls
- Amendments and rounds
- Award analysis, split awards, and creating purchasing documents

## Negotiation types and styles
- **RFI (Request for Information)** - gathers supplier information/capability. Not intended to award directly
  to a PO; use it to shortlist, then run an RFQ/auction.
- **RFQ (Request for Quotation)** - structured price/terms request; the common path to an award.
- **Auction** - competitive, usually a reverse auction where price moves down in real time during the open
  window. Once published, activity is visible per the style; you cannot quietly pull it mid-event.
- **Negotiation style** - a template that turns capabilities on or off: two-stage evaluation, sealed
  responding, cost factors, price tiers/breaks, multi-attribute scoring, response rules. The style set at
  creation decides what the event can do; you do not bolt on a sealed stage after publish.
- **Outcome** - a negotiation can result in a **Standard PO**, a **Blanket Purchase Agreement**, or a
  **Contract Purchase Agreement**. The outcome type decides what Create Purchasing Documents generates.

## The lifecycle and states
Draft -> (Publish) Active -> Paused -> Closed (responding ended) -> Award in progress -> Award Approved ->
Completed (purchasing documents created). Off-path: Canceled.
- **Draft** - reversible prep; edit/delete freely.
- **Publish** - outbound: invites suppliers, sends requirements/quantities/terms, opens the response window.
  This is the committing information act. Prospective suppliers can be invited here.
- **Paused** - responding suspended; visible to invited suppliers.
- **Closed** - the response window ended; evaluation begins.
- **Award / Award Approved / Completed** - selection, its approval, and the generation of the purchasing
  document. Rescinding an award after supplier notification is a new, visible action.

## Sealed and two-stage evaluation
- **Sealed responding** - responses are not readable until the unlock/close point defined by the style.
  Reading or acting on a sealed response early taints the event.
- **Two-stage RFQ** - a technical stage and a commercial (price) stage. The commercial stage stays sealed
  until the technical evaluation is complete and the stage is explicitly unlocked. The point is to evaluate
  capability without price influencing it. Opening the commercial stage early, or exposing its values, breaks
  the sealed process and can force a re-run.
- Gating: opening a sealed stage early or exposing sealed responses is destructive - the exposure is
  permanent and the only clean recovery is to cancel and re-run.

## Responses, surrogate responses, controls
- **Response / bid** - a supplier's answer, keyed on the Supplier Portal. May include line prices,
  attributes, cost factors, and attachments.
- **Surrogate response** - the buyer keys a supplier's offline offer on their behalf. It binds a real offer
  into the evaluation and can be awarded, so a wrong or shaded surrogate response distorts the competition and
  leaves a buyer-entered trail. Treat it as a committing write, not data entry, and only enter what the
  supplier actually submitted.
- **Response controls / rules** - required attributes, allowed response types, minimum reductions (auctions).
  They enforce comparability; loosening them mid-event changes what counts as a valid bid.

## Amendments and rounds
- **Amend** an active negotiation to change requirements, lines, dates, or terms. Amending republishes a new
  round: prior responses may be invalidated and suppliers must re-acknowledge or re-respond. An amendment late
  in a live event resets supplier work and can shift the competitive field, so it is not a quiet correction.
- Re-read all responses after an amendment; do not compare a pre-amendment bid against a post-amendment one.

## Award analysis, split awards, and creating purchasing documents
- **Award analysis** - compare responses by price and scored attributes (and cost factors, which normalize
  landed cost beyond unit price). Multi-currency responses convert at the event's configured rate before
  comparison, so a raw price gap may be an FX difference.
- **Award decision** - award by line or full quantity, to one supplier or **split** across several under
  constraints (allocation percentages, min/max). A split award feeds a separate purchasing document per
  allocation; do not collapse it into one supplier.
- **Award approval** - the award routes through its own approval rules; that approval is the sign-off the
  award carries. Do not treat an unapproved award as final.
- **Create Purchasing Documents** - after award approval, generate the PO or agreement from the award. This
  is a distinct step from awarding; awarding selects and notifies, this creates and (on communication)
  transmits the order. A prospective winner must be spend authorized before the document can be created.
