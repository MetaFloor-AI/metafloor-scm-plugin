# Icertis - lifecycle, authoring, deviations, approvals

How an agreement moves from request to execution, how it is assembled from templates and the clause library,
what makes something a deviation, and how the approval chain enforces authority. Read when a workflow authors,
negotiates, deviates from standard language, routes an approval, or sends a contract for signature.

## Contents
- The lifecycle states
- Authoring: templates, clause library, the rules engine
- Deviations and fallback positions
- Negotiation and version control
- Approval routing, DoA, and the signature-authority matrix
- Execution channels

## The lifecycle states
Statuses are configured per contract type, but the shape is consistent:
- **Request / intake** - a typed ask (buy-side, sell-side, corporate). A draft; nothing binds. Reversible.
- **In authoring** - the agreement is assembled from a template and the clause library. Still a draft.
- **Under negotiation** - versions and redlines exchanged with the counterparty. Multiple versions coexist;
  only one is the current agreed draft.
- **Pending approval** - routed to approvers by the rules (value, deviations, contract type, DoA tier).
- **Approved** - approval is for this exact version. A later edit invalidates it.
- **Out for signature** - sent to the signing platform; not yet binding.
- **Executed / in effect** - signed. Legally binding. The record of truth is the executed agreement plus its
  extracted attributes and obligations.
- **Amended / renewed / expired / terminated** - post-execution states, each reached by its own action
  (see `obligations-associations-renewals.md`).

## Authoring: templates, clause library, the rules engine
- A **template** is a pre-approved skeleton with standard clauses and embedded rules. Authoring from it is
  the governed fast path: the clauses already carry approval, so a clean template contract may need little or
  no deviation review.
- The **clause library** is the central store of approved clauses. Each clause has a preferred/standard
  version and one or more fallback/alternate positions, plus attributes (risk level, region, contract type).
- The **rules engine** reads the agreement's attributes and decides which clauses apply, which approvals
  route, which obligations get created, and which alerts arm. Because rules read attributes, changing an
  attribute mid-authoring (contract type, region, value) re-evaluates the rules and can swap clauses or
  re-route approval. It is not a cosmetic field change.

## Deviations and fallback positions
- A **deviation** is any departure from approved template or clause-library language: editing a standard
  clause's words, deleting a required clause, or inserting a clause that is not in the library.
- A deviation is detected and routed to a **deviation approval** by the rules. The depth of the deviation
  (a light wording change vs a struck liability cap) can set a higher approval tier.
- A **fallback position** is a pre-approved alternate the library offers when the counterparty rejects the
  standard clause. Using a fallback is governed: a shallow fallback may auto-clear, a deep one may still need
  approval. A fallback is a pre-approved option, not a way around the approval it carries.
- **Third-party paper** (the counterparty's template) has no library clauses, so every term is effectively a
  deviation. It needs clause extraction and a clause-by-clause risk review, not the template fast path.

## Negotiation and version control
- Redlining happens in Word (Icertis for Word / the Word experience) or in the counterparty's document, with
  versions tracked against the agreement. Many versions coexist during negotiation.
- Only one version is the current agreed draft. Executing or sending the wrong version binds the company to
  un-agreed terms, so confirm the final agreed version before approval and again before signature.
- A material change after approval re-opens the approval: approval is per version, and the changed version is
  unapproved until it re-routes.

## Approval routing, DoA, and the signature-authority matrix
- The approval chain is built by the rules from the agreement's attributes: **value tier**, **deviations and
  their depth**, **contract type**, **region/legal entity**, and **risk**.
- **Delegation of Authority (DoA) / signature-authority matrix** defines who may approve or sign at what value
  or risk. The workflow enforces it: an agreement above a tier routes to the authorized approver, and a signer
  must be within their authority.
- Approving within your DoA is committing (the chain and matrix are the named-approver gate). Overriding the
  chain, or approving/signing above your DoA, is destructive - it removes the gate.
- Splitting a contract's value across pieces to keep each under a DoA or approval tier is circumvention. The
  authority check is on the whole commitment; two half-size agreements to dodge it is auditable.
- Re-read the approval state at execute. An in-flight redline, a delegation change, or a re-evaluated rule can
  have re-routed the agreement since the last read.

## Execution channels
- **E-signature** through the integrated signing platform is the usual channel; Icertis orchestrates the send
  and records the executed result. The envelope mechanics (routing, authentication, signing order, voiding an
  envelope) belong to the signing platform, not here -> `docusign-clm`.
- **Offline / wet-signature** execution (a paper-signed contract uploaded and marked executed) still legally
  binds. The recorded executed status is the legal fact regardless of channel; do not treat an offline
  execution as less binding than an e-signed one.
