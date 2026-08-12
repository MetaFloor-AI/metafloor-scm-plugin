---
name: docusign-clm
description: "DocuSign eSignature and CLM - safe operation of the e-signature engine and the DocuSign contract lifecycle - envelopes and their states (created, sent, delivered, signed, completed, declined, voided), recipients and signing/routing order, recipient authentication (access code, SMS, KBA, ID Verification), tabs and anchor tagging, correcting or voiding an envelope, the Certificate of Completion, templates, PowerForms and bulk send, plus DocuSign CLM (contract generation, workflow, clause library, repository, obligations). Use when the signing platform is DocuSign, or the user names an envelope, sending for signature, a signer or CC or certified-delivery recipient, routing/signing order, sequential vs parallel signing, access code or SMS or KBA or IDV auth, a signature or date-signed tab, anchor tagging or AutoPlace, a declined or completed or voided envelope, the Certificate of Completion, an authoritative copy, a template or PowerForm or bulk send, or DocuSign CLM (formerly SpringCM)."
---

# DocuSign eSignature and CLM - operating it safely

DocuSign eSignature is the e-signature engine: it packages documents into an **envelope**, routes them to
**recipients** in a set **order**, **authenticates** each one, collects legally binding signatures, and
produces an executed agreement with a **Certificate of Completion**. What makes it dangerous is specific.
**Sending** an envelope is the moment legal exposure begins - the documents leave your control and land in
front of named parties who are being asked to bind. **Completion** (every recipient finishes) is the
irreversible execution; you cannot un-complete or void it. **Voiding** is possible only before completion.
The routing order and recipient authentication are what enforce signing authority - a wrong recipient, a
premature send, a weakened auth, or a mis-set routing order binds the wrong party or exposes the document to
someone who should not see it. This skill gives the judgment to classify DocuSign actions so the harness can
gate them, plus the edge states and recovery paths that decide whether a mistake is fixable.

## Contents
- When this applies / when NOT
- Object & state model
- Vocabulary that bites
- Operations: read / write / destructive
- Gotchas that bite
- Edge states & special cases
- Recovery patterns
- Guardrails
- References

## When this applies / when NOT
Signing platform is DocuSign and the work touches the envelope lifecycle (create, send, correct, void,
complete), recipients / routing / authentication, tabs, templates / PowerForms / bulk send, the Certificate
of Completion, or DocuSign CLM. **This skill owns the envelope / e-signature layer even when a different CLM
suite orchestrates the send** - Icertis and Ariba both hand the signature step to a signing platform, and if
that platform is DocuSign, the envelope mechanics here apply. When NOT:
- The CLM suite that authors, negotiates, and approves the contract is **Icertis** -> `icertis`.
  The agreement record, clause deviations, delegation-of-authority approval, and obligation model live there;
  DocuSign captures the signature and returns the executed result.
- The CLM suite is **SAP Ariba Contracts** -> `sap-ariba-clm` (contract workspace, publish, the
  compliance accumulator, amendment types). DocuSign is the signature engine Ariba's signature task hands off to.
- The **ERP ledger** behind an executed contract - AP posting, the payment run, revenue recognition, period
  close -> `sap-fi`. DocuSign binds the signature; the ERP posts and pays against it.
- The **procurement transaction** the signed contract governs - a requisition, PO, or supplier invoice ->
  `coupa` or `sap-ariba`.

Note: **DocuSign CLM (formerly SpringCM) is DocuSign's own contract lifecycle product and is covered here**,
not deferred. The "when NOT" applies only when the CLM suite is a different vendor (Icertis, Ariba).

## Object & state model (reason about state, not nouns)
- **Envelope** - the container and the object you operate on. Bundles one or more documents, the recipients,
  their routing order, the tabs, authentication, messages, and expiration / reminder settings. Envelope status
  flow: **created** (draft) -> **sent** -> **delivered** (a recipient opened it - not signed) -> **completed**
  (all recipients finished), or a terminal **declined** / **voided**. Two things are commonly mis-stated as
  envelope statuses and are not: **signed** is a *recipient* action state, not an envelope status (the envelope
  roll-up stays sent / delivered until every recipient finishes and it flips to completed); and **correct** is
  a sender *action* on a sent envelope, not a status the envelope sits in. Deleting a draft moves it to the
  recycle bin. An expired envelope auto-voids. Reversible while a draft; binding as signatures accumulate;
  executed at completed.
- **Recipient** - a party on the envelope with an action and a routing order. Types differ by what they do:
  **Signer** (needs to sign, binds), **In-Person Signer** (a host runs the session for a walk-in signer),
  **Carbon Copy / CC** (receives a copy, does not act), **Certified Delivery** (must receive and open but does
  not sign - used for legal notice), **Editor / Agent** (may change the envelope or add recipients before it
  reaches signers), **Intermediary / Specify Recipients** (names later recipients), **Signing Group** (any
  member may sign), **Seal** (an automated electronic seal), plus **Witness** and **Notary** for notarization.
  The type is not cosmetic - it decides whether that party binds, watches, or routes.
- **Routing / signing order** - an integer per recipient. Ascending integers run **sequential** (each waits
  for the prior); the **same** integer runs **parallel** (both receive at once). The order is what enforces
  internal sign-off before the counterparty and controls who sees the document when.
- **Tabs (fields / tags)** - what each recipient fills and where: signature, initial, date signed, name,
  title, company, text, checkbox, radio, dropdown, approve / decline, formula, payment. Tabs are
  recipient-scoped. **Anchor tagging (AutoPlace)** places tabs by matching anchor text in the document rather
  than at fixed coordinates.
- **Authentication** - the identity check a recipient must pass before signing: **access code** (a shared
  secret), **SMS / phone** one-time passcode, **knowledge-based authentication (KBA / ID Check**, public-record
  questions), or **ID Verification (IDV**, government ID + selfie). This is what proves who actually signed.
- **Certificate of Completion** - the audit record attached to the completed PDF: each recipient's identity,
  IP, timestamps, authentication method, and the electronic-record-and-signature-disclosure consent. It is the
  legal evidence of the signing and cannot be edited.
- **Template / PowerForm / Bulk Send** - reusable envelope definitions. A **template** pre-defines documents,
  roles, routing, tabs, and auth. A **PowerForm** is a self-service web link anyone with the URL can use to
  start an envelope. **Bulk Send** fires one template to many recipients as separate envelopes.
- **DocuSign CLM (formerly SpringCM)** - DocuSign's contract lifecycle product: a repository (folders,
  versioned documents), workflows that route and act on documents, contract generation (doc gen from templates
  and merge data), a clause library, and obligation management. See `references/compliance-and-clm.md`.

## Vocabulary that bites
- **Envelope** - not a document, a routed transaction. Recipients, order, tabs, and auth are all bound to the
  envelope; changing any of it after send is a **correct**, not a quiet edit.
- **Sent vs Delivered** - "delivered" does NOT mean signed and does not even mean the email arrived; it means
  the recipient opened the envelope in the viewer. Reading "delivered" as "done" is a classic misread.
- **Completed** - the terminal success: every recipient finished their action. This is the executed agreement.
  You cannot void or un-complete it.
- **Void** - the sender stops an in-process envelope with a reason; recipients are notified; status becomes
  **voided** permanently. Only possible before completion. It is the corrective action for a bad send, but it
  is itself not undoable and it does not un-send what recipients already saw.
- **Correct** - editing a sent, not-yet-completed envelope (recipients, routing, documents, tabs, auth). It
  re-notifies. Once a recipient has signed, the documents they signed are **locked** - a correct can only touch
  later recipients and unacted tabs.
- **Declined** - a recipient refuses to sign. The envelope stops; there is no partial execution and no
  re-open. A new envelope is required.
- **Routing / signing order** - the sequence that enforces signing authority. A wrong order can send to the
  counterparty before internal approval, or let a CC see the draft too early.
- **Recipient type** - Signer binds; CC only watches; Certified Delivery must open but not sign; Editor / Agent
  can change the envelope. Assigning the wrong type asks the wrong action of the wrong party.
- **Authentication (access code / SMS / KBA / IDV)** - the control that proves identity. Removing or weakening
  it to "make signing easier" strips the proof of who signed and can let the wrong party bind.
- **Anchor tagging (AutoPlace)** - tabs placed by matching text in the document. If the anchor text moves,
  duplicates, or the document changes, a signature or initial can land on the wrong clause or page.
- **PowerForm** - a self-service link; anyone with the URL can start the envelope, so it gives no control over
  who initiates - wrong for an authority-sensitive negotiated agreement.
- **Signature level (SES / AES / QES)** - electronic (standard), advanced, or qualified under eIDAS; a
  regulated jurisdiction or contract type may require a higher level for the signature to be legally sufficient.
- **Authoritative copy** - for transferable records (e.g., a loan note) the single controlling original is
  vaulted; ordinary downloaded PDFs are copies, not the authoritative original.

## Operations: read / write / destructive
Classify every operation family by what it does to legal and envelope state. Kinds of action, not tool names.

| Class | DocuSign operation families | Gate | Why |
|---|---|---|---|
| **Read** | view an envelope, its status, recipients, routing order, tabs, documents, and history; view the Certificate of Completion and audit trail; download completed / combined documents; list or search envelopes; view templates, PowerForms, and CLM repository documents; view each recipient's authentication and action status | always pass | no state change; read the live status before every write and re-read at execute |
| **Write (reversible)** | create a draft envelope; add or edit documents, recipients, routing order, tabs, authentication, and messages on a draft (not yet sent); create or edit a template; save a draft; author or generate a contract in CLM before it is routed | gate one at a time | uncommitted; nothing has been sent to a recipient or signed; cleanly discardable |
| **Write (committing)** | **send** an envelope for signature (delivers to the named recipients and requests binding signatures - the point where legal exposure begins); **correct** an in-process envelope (re-route, change recipients / tabs / auth, re-notify - scope shrinks to later recipients and unacted tabs once anyone has signed); add or change a recipient mid-flight via correct; **enable recipient reassignment / delegation** (lets a signer hand the envelope to another party who then binds); **add a Seal recipient** (auto-applies an organizational seal - it binds with no human review); host an in-person signing; route a CLM workflow that sends to eSignature | gate + human approve | puts the document in front of external parties and asks them to bind, or lets someone else bind; reversible only by void, and only before completion |
| **Destructive / irreversible** | **completion / execution** of the envelope (all recipients signed - the executed agreement; cannot un-complete or void); **void** a sent envelope (permanent; the corrective action but not itself undoable); a signer completing their signature; **remove or weaken required authentication** on a recipient who then signs; **send to the wrong external recipient** (they now hold / could sign the binding document); **purge or delete documents** under retention (permanent removal of the record); **bulk send a flawed template** (one error multiplied across every envelope); **transfer an envelope to another account** (the new owner gains control of in-process envelopes and can void them) | hard gate + named approver + re-read | permanent legal trail; binds the company or a counterparty; exposes the document outside your control; the wrong signer or missed control cannot be cleanly undone |

**Resend / remind is a light nudge, not a committing act.** It re-notifies an existing recipient at the same
routing step and changes no content, routing, or auth. Confirm and log it, but do not gate it at the same tier
as send or correct - over-gating a benign nudge invites workarounds.

**Send is the exposure boundary, not a save.** Before send an envelope is a private draft you can freely
change or discard. Send delivers the documents to the named recipients and asks them to legally bind; from
that instant a wrong recipient has seen your document and the only stop is a void. Treat send as committing
and confirm the full recipient list, addresses, recipient types, routing order, tabs, and authentication first.

**Correcting after the first signature is limited.** Once any recipient has signed, you cannot change the
documents they signed - a correct can only reach later recipients and unacted tabs. A change to already-signed
content requires voiding and sending a new envelope.

**Void is permanent and only pre-completion.** Voiding an in-process envelope is the corrective action for a
bad send, but the void itself cannot be undone (you create a new envelope), and a completed envelope cannot be
voided at all. Voiding is a stop, not a rewind.

**Completion is the irreversible execution.** When the last recipient finishes, the envelope is completed and
the agreement is executed. Like an Icertis or Ariba execution, a mistake in a completed envelope is fixed only
by a new signed instrument (an amendment / new envelope), never by an undo.

Universal rules to teach: read the live envelope status, the recipient list and their action states, the
routing order, the authentication on each recipient, and the tab assignment before every write, and **re-read
at execute** (a recipient may have signed, declined, or the envelope may have expired since you last looked).
Never weaken or remove an authentication control to speed signing; never re-route to skip the internal
approver; never send an authority-sensitive negotiated agreement through a PowerForm or bulk send. A declined
recipient, an expired / voided envelope, or a legal hold means **stop**. Void is only possible before completion.

## Gotchas that bite (the real set, as causal chains)
1. **"Delivered" does not mean signed - or even received.** Status "delivered" means a recipient opened the
   envelope in the viewer; it is not proof of email receipt and not a signature. Treating it as done ships a
   half-finished agreement as complete.
2. **Sending is the moment the document leaves your control.** Send delivers the actual documents to each named
   recipient at their routing turn; a wrong email address or wrong party now holds a binding document, and the
   only remedy is to void - which does not un-see what they already opened. Verify recipients and addresses first.
3. **Completion cannot be undone or voided.** Once the last recipient signs, the envelope is completed and
   executed; there is no un-complete and no void after completion. A mistake is corrected only by a new signed
   envelope (an amendment), the same as any executed contract.
4. **Void is one-way and only before completion.** Voiding stops an in-process envelope permanently - you
   cannot un-void, you re-create - and you cannot void a completed one at all. Voiding is a stop, not a rewind.
5. **A wrong routing order leaks the document or skips the approver.** Ascending integers sign sequentially;
   equal integers sign in parallel. Set the counterparty's order below the internal approver's and the
   counterparty receives the binding document before anyone internal has signed off.
6. **Parallel routing exposes everyone at once.** Giving internal and external recipients the same routing
   number sends to all simultaneously - the counterparty sees the document before internal review completes.
   Use sequential order to gate internal sign-off first.
7. **Correcting is locked once a recipient has signed.** You can correct recipients, tabs, and even documents on
   an in-process envelope, but not the documents a recipient already signed. A late document change after
   someone signed forces a void and a fresh envelope.
8. **A decline stops the whole envelope with no partial execution.** If any signer declines, the envelope
   terminates; earlier signatures do not produce a partial agreement and the envelope cannot be re-opened. You
   create a new one.
9. **Removing authentication removes the proof of who signed.** Access code, SMS, KBA, and IDV are what tie a
   signature to an identity. Dropping an auth step to help a stuck signer lets an unverified party bind and
   weakens the signature's defensibility in a dispute.
10. **Recipient type decides whether a party binds or just watches.** A CC never signs; a Certified Delivery
    must open but not sign; a Signer binds. Marking the counterparty's counsel as a Signer instead of CC asks
    the wrong person to bind; the reverse leaves the real signer off the envelope.
11. **Anchor tagging can put a signature on the wrong clause.** AutoPlace positions tabs by matching anchor
    text; if the wording changes, the anchor repeats, or a merge shifts the layout, the signature or initial
    lands on the wrong page or clause - the party binds text they did not mean to.
12. **A required tab on the wrong recipient asks the wrong person to sign.** Tabs are recipient-scoped;
    assigning a signature tab to the CC, or to recipient 2 instead of recipient 1, routes the binding action to
    the wrong party.
13. **A PowerForm lets anyone with the link start a binding envelope.** Self-service links give no control over
    who initiates; using one for an authority-sensitive agreement invites an unauthorized or wrong party to
    launch and sign.
14. **Bulk send multiplies one template error across every envelope.** A wrong clause, wrong tab, or wrong auth
    in the source template is replicated to hundreds of separate binding envelopes at once. Verify the template
    on a single send first.
15. **A signer can reassign or delegate to someone else.** If reassignment is allowed, the intended authorized
    signer can hand the envelope to another person, who then binds the company; the authority you routed to is
    not necessarily who signs. Check the completed recipient identity on the certificate, not the intended one.
16. **Embedded / captive signing trusts the host application's authentication.** When signing is embedded in
    another app via the API, DocuSign relies on that app to have authenticated the user; DocuSign's own auth may
    be bypassed, so the signing authority is only as strong as the host app's login.
17. **An envelope can expire and auto-void while you wait.** Envelopes carry an expiration and reminder schedule
    (e.g., expire after 60 or 120 days); a slow counterparty can let it lapse to voided, and the deal must be
    re-sent as a new envelope - the old one is terminal.
18. **The Certificate of Completion is the legal evidence - do not lose or strip it.** The completed PDF's
    certificate carries the identity, IP, timestamps, auth, and consent record that make the signature
    enforceable. Distributing only the signed pages without the certificate weakens the ability to prove the signing.
19. **The wrong signature level can be legally insufficient.** A standard electronic signature (SES) may not
    satisfy a jurisdiction or contract type that requires an advanced (AES) or qualified (QES) signature under
    eIDAS; a technically "completed" envelope can still be legally weak for that use.
20. **Missing the electronic-records consent can undermine the signature.** Under ESIGN / UETA (and eIDAS) the
    signer must be able to consent to doing business electronically; if that disclosure is not presented or
    accepted, the electronic signature can be challenged.
21. **A downloaded PDF is a copy, not the authoritative original.** For transferable records (loan notes,
    negotiable instruments) the single controlling authoritative copy is vaulted; treating an ordinary download
    as the original breaks the chain of the negotiable instrument.
22. **Purge under a retention policy permanently removes the record.** Retention / purge deletes documents and
    their fields after a set window (e.g., 30 or 90 days after completion); once purged the copy is gone from
    DocuSign, so keep your own retained copy of the completed PDF and its certificate.
23. **A send or webhook can fail after the action but before confirmation.** If a send, a completion callback
    (Connect webhook), or a CLM / CRM sync drops mid-operation, the envelope can be left in a state your system
    does not reflect. Re-read the live envelope status before retrying; a blind resend can double-send and a
    blind create can duplicate the envelope. The live envelope status is the source of truth, not your last request.
24. **In-person signing puts the identity check on the host.** The host running an in-person session is
    vouching for the walk-in signer's identity; without a separate authentication the signature's identity
    assurance is only the host's word.
25. **"Sent" does not confirm the recipient can be reached.** If the recipient's email bounces, that recipient's
    status becomes **auto-responded**, not delivered - the envelope sits stuck at that routing step and never
    progresses. Reading the envelope as "sent, so it is in motion" hides a dead step; correct the address (or
    re-route) to unstick it. Check recipient action states, not just the envelope roll-up.
26. **You can only see and act on envelopes your account and folder permissions expose.** Envelope visibility
    is scoped by sending account, shared access, and (in CLM) folder security; a search that comes back empty
    can mean "no permission," not "does not exist." Confirm scope before concluding an envelope is missing.
27. **Conditional / advanced routing can silently skip a required approver.** A route that branches on a field
    value (e.g., send to VP approval only if amount > a threshold) will bypass that approver if the field is
    wrong, blank, or the condition is mis-set - the envelope reaches signature with an approval step never
    fired. Read the actual routing conditions, not just the recipient list, before relying on who signed off.

## Edge states & special cases
Each breaks naive "one document, one signature" logic. Deep mechanics:
`references/envelope-lifecycle-and-recipients.md` and `references/compliance-and-clm.md`.

| Edge state | Naive assumption | Actual behavior | Correct action |
|---|---|---|---|
| **Envelope "delivered"** | it was emailed / it is done | the recipient opened it in the viewer; not received-by-email proof, not signed | read the recipient action states, not just the envelope status |
| **First signature applied, more to go** | still fully editable | documents that recipient signed are locked; only later recipients and unacted tabs can be corrected | correct only downstream; a signed-document change needs a void + new envelope |
| **Declined by a recipient** | earlier signatures still count | the envelope terminates with no partial execution and cannot be re-opened | create a new envelope; do not expect a partial agreement |
| **Sequential vs parallel routing** | order does not matter | equal routing numbers sign in parallel (all see it at once); ascending numbers gate each step | set internal approvers ahead of the counterparty in sequence |
| **PowerForm / self-service link** | a controlled send | anyone with the URL can initiate and sign | do not use for authority-sensitive negotiated agreements; use a routed envelope |
| **Bulk send** | one action | one template becomes hundreds of independent binding envelopes | verify on a single send first; a template error multiplies |
| **Embedded / captive signing (API)** | DocuSign authenticated the signer | the host app's login is the identity check; DocuSign auth may be bypassed | confirm the host app authenticated; add DocuSign auth for high-risk signers |
| **Reassign / delegated signing** | the intended signer signed | the recipient may have delegated to another person who actually bound | verify the completed recipient identity on the certificate |
| **Authoritative copy / transferable record** | the downloaded PDF is the original | the controlling original is vaulted; downloads are copies | manage the authoritative copy in the eOriginal / vault flow, not as a loose PDF |
| **Envelope expiration** | it waits until signed | it auto-voids at the expiration window | track the expiration; re-send as a new envelope if it lapses |
| **Wet / offline signature captured elsewhere** | only an e-sign in DocuSign binds | a paper-signed agreement is still legally executed off-platform | treat the executed status as the legal fact regardless of channel; keep both records |
| **DocuSign Connect (webhook) missing or delayed** | the downstream system reflects the true state | the CLM / ERP updates off Connect events; a dropped or late notification leaves them out of sync with the live envelope | re-read the live envelope status as the source of truth; do not trust a stale downstream record |

## Recovery patterns (can it be undone, and what cannot)

| Action | Undoable? | How / what cannot be restored |
|---|---|---|
| **Draft envelope (not sent)** | yes | discard or edit freely; nothing was delivered or signed |
| **Sent, in-process, wrong later recipient or tab** | yes, via correct | correct the downstream recipients / tabs and re-notify; nothing already signed can change |
| **Sent, wrong document or wrong already-signed content** | no in-place fix | void the envelope (permanent) and send a new corrected one; the wrong recipients may already have seen it |
| **Sent to the wrong external party** | void immediately | voiding stops it, but the wrong party already received / could have opened the document - treat as an information-exposure incident, not a clean undo |
| **Declined envelope** | no re-open | create a new envelope; the declined one is terminal |
| **Expired / voided envelope** | no | terminal; re-create a new envelope |
| **Completed / executed envelope** | no | cannot un-complete or void; correct only by a new signed envelope (an amendment); the executed record and its certificate stay permanently |
| **Weakened / removed authentication after a signature** | no | the signature was captured without the control; you cannot retroactively add the proof - re-execute with proper auth if identity assurance matters |
| **Purged documents (retention)** | no | gone from DocuSign; rely on your retained copy of the completed PDF and certificate |
| **Operation interrupted (send, Connect webhook, or CLM / CRM sync drops)** | re-read, do not blind-retry | the envelope may be partially applied; re-read the live status and recipient states before retrying, because a blind resend can double-send or duplicate. The live envelope status is the truth, not your last request |

## Guardrails
- Read the live envelope status, the recipient list and their action states, the routing order, the
  authentication on each recipient, and the tab assignments before acting; re-read at execute - a recipient may
  have signed, declined, or the envelope may have expired since.
- Treat send as the point of legal exposure: confirm every recipient and email address, the recipient types
  (who binds vs who is copied), the routing order (internal approver before the counterparty), the tab
  placement, and the authentication before sending. A wrong recipient cannot be recalled, only voided, and they
  may already have seen the document.
- Never weaken or remove an authentication control to help a stuck signer; it removes the proof of who signed.
  Never re-route to skip an internal approver, and never send an authority-sensitive negotiated agreement
  through a PowerForm or bulk send. For authority-sensitive envelopes, keep recipient reassignment / delegation
  off (so the routed signer is the one who binds) and do not add an auto-applying Seal recipient without review.
- Void is only possible before completion and is itself permanent; a completed envelope is executed and is
  fixed only by a new signed instrument, not an undo.
- Keep the Certificate of Completion with the signed documents; it is the legal evidence. Match the signature
  level (SES / AES / QES) and the electronic-records consent to the jurisdiction and contract type. For
  transferable records, manage the authoritative copy, not a loose PDF.
- Never blind-retry a send, completion, or sync that may have failed mid-operation; re-read the live envelope
  status first (a blind resend can double-send or duplicate). The live envelope status is the source of truth,
  not your last request or a stale downstream record.
- For anything in the destructive row (completion, void, removing auth, wrong-party send, purge, bulk send of a
  flawed template): named approver, re-read of live state, and a logged reason.

## References (load on demand)
- `references/envelope-lifecycle-and-recipients.md` - the full envelope state machine and status values, every
  recipient type and the routing / signing-order mechanics, the authentication methods (access code, SMS /
  phone, KBA, IDV) and when each is required, tabs and anchor tagging, and templates / PowerForms / bulk send.
  Read when a workflow builds, routes, authenticates, corrects, or voids an envelope.
- `references/compliance-and-clm.md` - the Certificate of Completion and audit trail, the legal frameworks and
  signature levels (ESIGN / UETA, eIDAS SES / AES / QES) and electronic-records consent, authoritative-copy /
  transferable-records handling, and DocuSign CLM (repository, workflows, contract generation, clause library,
  obligation management) with its committing acts. Read when a workflow deals with legal sufficiency, retention,
  or the DocuSign CLM lifecycle.
