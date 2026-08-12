# SAP Ariba Contracts - workspace, authoring, clauses, tasks, approvals

How a contract moves from request to a published, signed workspace: the lifecycle and statuses, how the main
agreement is assembled from the template and the clause library, what makes something a deviation, how tasks
and approvals enforce authority, and how signature and publish differ. Read when a workflow creates a
workspace, authors, deviates, routes an approval, sends for signature, or publishes.

## Contents
- The workspace lifecycle and statuses
- Templates and how a workspace is built
- Authoring: the clause library and assembly
- Deviations, fallback, and conditional clauses
- Tasks and approval routing
- Signature and publish - the two committing acts

## The workspace lifecycle and statuses
The contract workspace (CW) is a project container. Its status:
- **Draft** - being authored. Terms, line items, the main agreement, and tasks are editable. Reversible; nothing
  is metered, signed, or pushed downstream.
- **Published** - active. A version is stamped (1.0), the expiration/renewal clocks are armed, and the priced
  line items are pushed into contract compliance and, if integrated, the ERP. A published workspace cannot be
  edited in place.
- **Amending** - a new-version draft opened by an amendment (see `terms-compliance-amendments.md`). The prior
  published version stays live until the amendment re-publishes.
- **Expired** - the term ended without renewal; rights and compliance releases lapse.
- **Closed** - ended and archived; kept in the trail.
- **On Hold** - paused for a dispute, legal review, or compliance check. Do not publish, amend, or sign around a
  hold; it protects the state it was placed to protect.

A **Contract Request** precedes the workspace: a requester submits intake, and on its approval a workspace is
created from the chosen template. The request is a draft ask - reversible until the workspace exists.

## Templates and how a workspace is built
- A **contract template** is a pre-approved blueprint. It defines the documents the workspace starts with (the
  contract terms, the main agreement, ancillary docs), the **tasks** (review/approval/negotiation/signature/
  notification), the **team** roles, the **conditions**, and the starting **clauses**.
- Choosing a template is a routing decision: it sets the approval chain, the clauses, and the required documents.
  The wrong template bakes the wrong workflow into the workspace from creation.
- **Conditions** on the template read the contract terms (contract type, region, amount, commodity) and decide
  which conditional clauses, documents, and tasks apply. Changing a term re-evaluates the conditions.

## Authoring: the clause library and assembly
- The **main agreement** is the legal contract, assembled in Microsoft Word from the template plus the clause
  library through the Ariba Word add-in. This assembled document is what gets signed.
- The **clause library** is the central store of approved clauses. Each clause has a standard version and may
  have **fallback** alternates and **conditional** variants, plus attributes (risk, region, contract type).
- Because assembly reads the terms and conditions, changing a term attribute mid-authoring can swap clauses in or
  out of the assembled document. Re-assemble and re-review after a term change - it is not a cosmetic edit.

## Deviations, fallback, and conditional clauses
- A **deviation** is any departure from the standard clause-library language: editing a standard clause's words,
  deleting a required clause, or inserting a clause that is not in the library.
- The **deviation report** flags every deviation in the assembled main agreement. Publishing with unreviewed
  deviations ships un-vetted legal language into a binding contract; the depth of the deviation (a light wording
  change vs a struck liability cap) can set a higher approval tier.
- A **fallback clause** is a pre-approved alternate the library offers when the counterparty rejects the standard
  clause. A shallow fallback may clear automatically; a deep one may still route approval. A fallback is a
  pre-approved option, not a way around the review it carries.
- A **conditional clause** is included or dropped by the template's conditions. Change the driving term and the
  clause set changes.
- **Uploaded third-party paper** (the counterparty's document) has no library clauses, so every term is
  effectively a deviation. It needs a clause-by-clause risk review, not the template/clause-library fast path.

## Tasks and approval routing
- Tasks are the workflow units inside the workspace, defined by the template with **conditions** and
  **dependencies**:
  - **Review task** - a read/comment step; completing it does not bind.
  - **Approval task** - routes to approvers, serial or parallel; each approves or denies. A denial sends the
    workspace back for rework.
  - **Negotiation task** - manages the redline exchange and versions with the counterparty.
  - **Signature task** - sends the main agreement for e-signature (DocuSign) or records a manual signature.
  - **Notification / to-do task** - alerts or a manual step; no binding effect.
- **Approval is per version.** A material change after an approval task completes (a late redline, a clause edit,
  a term crossing an authority tier) invalidates that approval and must re-route. Publishing the edited version
  pushes terms nobody approved.
- **All required approval tasks must complete before the workspace is approved.** In a parallel approval, some
  lanes approving while others are still pending is not approval - do not proceed on one lane's completion. Read
  the whole approval state, not a single task's status.
- **Signature authority.** Who may approve or sign at what value or risk is set by the approval rules and the
  signature-authority policy. Approving within authority is committing (the chain is the named-approver gate);
  overriding the chain, or approving/signing above authority, is destructive - it removes the gate.
- **Splitting a contract across workspaces** to keep each under an approval or signature-authority threshold is
  circumvention. The authority check is on the whole commitment; two half-size workspaces to dodge it is auditable.
- Re-read the approval and signature state at execute - an in-flight redline or a re-evaluated condition can have
  re-routed the workspace since the last read.

## Signature and publish - the two committing acts
- **Signature** legally executes the main agreement. Through the **DocuSign integration**, the signature task
  sends the document and records the signed result; the envelope routing, signer authentication, signing order,
  and voiding a sent envelope belong to the signing platform -> `docusign-clm`. A manual/offline
  signature (paper-signed, uploaded, task completed) still legally binds.
- **Publish** is the Ariba act that activates the workspace: it stamps a version, arms the expiration and renewal
  clocks, and pushes the line items into contract compliance and (if integrated) the ERP.
- They are **separate**, and configurations differ on the order (some sign the assembled document then publish;
  some publish the version snapshot then sign it). A signed-but-unpublished contract is not active in the system;
  a published-but-unsigned contract is active but not legally executed. The safety rule is a match, not a fixed
  sequence: the version published into compliance must be the version that was agreed and signed. Never activate
  (publish) an unsigned or un-agreed contract into compliance, and confirm both states are the same agreed version.
