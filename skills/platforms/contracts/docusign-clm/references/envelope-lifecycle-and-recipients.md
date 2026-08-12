# DocuSign envelope lifecycle, recipients, authentication, tabs, and sending

Deep mechanics behind the SKILL.md matrix. Read when a workflow builds, routes, authenticates, corrects, or
voids an envelope. The judgment (what is committing vs destructive) lives in SKILL.md; this file is the how.

## Contents
- Envelope status values and transitions
- Recipient types and what each one does
- Routing / signing order mechanics
- Recipient authentication methods
- Tabs and anchor tagging
- Correcting a sent envelope
- Voiding, declining, expiring
- Templates, PowerForms, bulk send, signing groups

## Envelope status values and transitions
The envelope is a state machine. The statuses that decide what you may do:

| Status | Meaning | What you can still do |
|---|---|---|
| **created** | draft; not yet sent | edit anything, or delete; nothing is binding |
| **sent** | out to the current routing step; requests are delivered to recipients' inboxes | correct, void, resend / remind |
| **delivered** | a recipient has **opened** the envelope in the viewer (not signed, not "email delivered") | correct (subject to signature locks), void |
| **completed** | every recipient finished - the **executed agreement** | nothing; cannot un-complete or void; download the executed PDF + certificate |
| **declined** | a recipient refused; the envelope stopped | terminal; create a new envelope |
| **voided** | the sender stopped it before completion | terminal; create a new envelope |

Not envelope statuses (a common trap):
- **signed** is a **recipient** action state, not an envelope status. While recipients sign one by one, the
  envelope roll-up stays **sent** / **delivered** and only flips to **completed** when the last one finishes.
  Querying for an envelope in status "signed" gets nothing.
- **correct** is a sender **action**, not a status the envelope rests in - it stays sent / delivered during a
  correction.
- **deleted** is a draft moved to the recycle bin, not a queryable lifecycle status.

Recipient-level action states (more precise than the envelope roll-up): **created -> sent -> delivered ->
signed / completed**, or **declined**, or **auto-responded**. **Auto-responded means the recipient's email
bounced** - the envelope is stuck at that routing step and never progresses; "sent" alone does not confirm
reachability, so read the per-recipient states and correct the address (or re-route) to unstick it.

Notes that bite:
- **"delivered" is an open event, not an email-receipt event and not a signature.**
- An **expiration** timer (account-configured, often 60-120 days) moves a stuck envelope to **voided**
  automatically; reminders nudge recipients before then.
- **completed** is the only success terminal. Everything else terminal (declined, voided) means the deal did
  not execute through this envelope.

## Recipient types and what each one does
The recipient type is a routing and authority decision, not a label.

| Type | Action | Binds? | Use it for |
|---|---|---|---|
| **Signer** ("needs to sign") | applies signature / initial / field tabs | yes | the parties who must legally sign |
| **In-Person Signer** | a **host** launches a session; a walk-in signer signs on the host's device | yes (walk-in signer) | in-branch / at-desk signing; the host vouches for identity |
| **Carbon Copy (CC)** | receives a copy at their routing turn; no action | no | notify a stakeholder; keep a record recipient |
| **Certified Delivery** ("needs to view") | must receive and open; no signature | no | legal notice where proof of delivery matters |
| **Editor** ("allow to edit") | can edit **documents, tabs, recipients, and routing** before it reaches signers | no (but controls the binding content) | an internal party who finalizes the whole envelope mid-flight |
| **Agent** / **Specify Recipients** ("update recipients") | can add / change **downstream recipients** only - **cannot** alter document content | no | let one party name the actual signer downstream |
| **Intermediary** | a limited Agent that names the next recipient in the chain | no | route through a gatekeeper who picks the next hop |
| **Signing Group** | any one member of a named group may sign | yes (whoever signs) | "any authorized approver in group X" |
| **Seal** | an automated electronic seal, no human action | organizational seal | apply a corporate seal / automated stamp |
| **Witness** | signs to witness another recipient's signature | witness only | notarization / witnessed execution |
| **Notary** | notarizes the session (remote online notarization) | notarizes | jurisdictions requiring notarization |

Danger: an **Editor** can change the documents and tabs (the binding content) after you send; an **Agent /
Intermediary** can change **who** signs downstream. Placing an untrusted party in either role hands them
control over what binds or who binds it. A **Signing Group** means you do not control which specific person
binds - only that they are in the group.

## Routing / signing order mechanics
- Each recipient carries a **routing order** integer.
- **Ascending distinct integers -> sequential.** Recipient at order 1 acts, then order 2 is notified, and so on.
  This is how you gate: put the internal approver at order 1 and the counterparty at order 2 so nothing external
  happens until internal sign-off.
- **Equal integers -> parallel.** Two recipients at order 1 both receive the envelope at the same time. Useful
  when order does not matter internally; dangerous when it puts the counterparty in the same step as an internal
  reviewer, exposing the document before review.
- CCs and Certified Delivery recipients also have a routing order - a CC at order 1 sees the document before any
  signer acts, which may be premature.
- **Conditional / advanced routing** can branch the path on a field value; a mis-set condition can skip a
  required approver. Read the actual routing before assuming who signs when.

## Recipient authentication methods
Authentication is what proves the signer is who the envelope says. It is per-recipient and stackable.

| Method | What it checks | Strength / cost | Typical use |
|---|---|---|---|
| **Access Code** | a shared secret the sender communicates out of band | weak-medium; only as good as the channel it was shared on | a light identity check between known parties |
| **SMS / Phone (one-time passcode)** | possession of a phone number | medium | confirm the signer controls a known number |
| **Knowledge-Based Authentication (KBA / "ID Check")** | public-record quiz (former addresses, accounts) | medium-strong; US-centric | regulated flows that mandate KBA (some are legally required) |
| **ID Verification (IDV)** | government photo ID + liveness / selfie match | strong | high-value or eIDAS / regulated identity assurance |

Rules:
- **Removing or lowering auth to unstick a signer is a control bypass**, not a convenience. It reclassifies the
  send to destructive because it lets an unverified party bind.
- Some contract types or jurisdictions **require** a specific method (e.g., KBA for certain US filings, IDV for
  eIDAS advanced / qualified). Dropping it can make the signature legally insufficient - see
  `compliance-and-clm.md`.
- **Embedded / captive signing** through the API can bypass DocuSign's auth entirely because the host app is
  trusted to have authenticated the user; the signing authority is then only as strong as that app's login.

## Tabs and anchor tagging
- **Tabs** are the fields a recipient fills: signature, initial, date signed, name, title, company, text,
  checkbox, radio, dropdown, approve / decline, formula, payment, and note. Each tab is **assigned to a specific
  recipient**; a tab on the wrong recipient asks the wrong person to fill or sign it.
- **Fixed-position tabs** sit at page coordinates. If the document paginates differently than expected, they
  drift.
- **Anchor tagging (AutoPlace)** positions tabs by matching **anchor text** in the document (e.g., place a
  signature tab wherever the string `\s1\` appears). Failure modes:
  - the anchor string appears **more than once** -> duplicate tabs on unintended spots;
  - the document wording or a merge field **changed** -> the anchor moved or vanished, so the tab lands on the
    wrong clause / page or does not appear;
  - a scanned / flattened PDF has **no searchable text** -> anchors do not match at all.
- **Required vs optional** and **locked vs editable** tabs decide whether the recipient must act and whether they
  can change a pre-filled value. A pre-filled value left editable can be altered by the signer.

## Correcting a sent envelope
- **Correct** re-opens a sent, not-yet-completed envelope to change recipients, routing order, documents, tabs,
  authentication, email subject / body, or expiration, then re-notifies.
- **Signature lock:** once a recipient has signed, the documents and tabs they acted on are frozen. A correct can
  only change **later** recipients and **unacted** tabs. To change something an earlier signer already signed you
  must **void and re-send** a new envelope.
- Correcting **resets the current step's notification** and can restart the routing from the corrected point; a
  recipient who was mid-review is re-notified.

## Voiding, declining, expiring
- **Void** - sender-initiated stop before completion. Requires a reason, notifies recipients, status ->
  **voided**, permanent. You cannot void a **completed** envelope, and you cannot un-void; you re-create.
- **Decline** - recipient-initiated refusal. The envelope terminates for everyone; there is no partial
  execution and no re-open. Earlier signatures do not survive into a new deal.
- **Expire** - the envelope's expiration timer lapses -> auto-void. Reminders fire on a schedule before it.
  A lapsed deal must be re-sent as a new envelope.

## Templates, PowerForms, bulk send, signing groups
- **Template** - a saved envelope blueprint: documents, recipient **roles**, routing, tabs, and auth. Reused by
  filling in the role's real name / email. A template error (wrong tab, wrong auth, wrong routing) is inherited
  by every envelope built from it.
- **PowerForm** - a **self-service** hosted link built from a template; **anyone with the URL** can open it and
  start an envelope. There is no control over who initiates, so it is wrong for authority-sensitive negotiated
  agreements; it fits high-volume, low-risk, self-initiated forms.
- **Bulk Send** - one template fired to a list as **separate** envelopes (one per recipient). Scales to
  thousands, and multiplies any template defect across all of them. Verify the template on a single send first.
- **Signing Group** - a named set where any member may sign; you gain flexibility but lose control over which
  specific individual binds. Confirm on the certificate who actually signed.
