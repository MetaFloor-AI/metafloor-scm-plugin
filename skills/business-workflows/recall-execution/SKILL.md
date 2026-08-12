---
name: recall-execution
description: "Recall execution and field pull (uc-return-recall-execution) - a defect or contamination is confirmed on specific lots, and every downstream location holding affected product must be traced, quarantined, and pulled from the field on a regulator clock with a provably complete trail. Use when a LIMS/QMS confirms a defect or contamination on specific lots/batches, a product recall / field action / withdrawal is called, affected lots must be traced forward through genealogy to every DC, customer site, retail shelf, or in-transit export, stock must be quarantined and reverse-logistics pull orders raised, regulators and customers notified on a clock, or someone scopes a recall (lots, date range, batches) and tracks completion and effectiveness; triggers on recall, field action, field pull, market withdrawal, lot genealogy, forward trace, where-distributed, batch recall, reverse logistics, quarantine hold, recall register, FDA recall class, reportable food, or recall effectiveness check."
---

# Recall execution and field pull

One workflow (`uc-return-recall-execution`): a defect or contamination is confirmed on specific lots, and
every downstream location holding affected product has to be found, pulled from the field, and routed to
disposition - fast, and provably complete. Affected lots fan out across DCs, customer sites, retail shelves,
even an in-transit export, while a regulator clock runs in hours. Miss one location and it is a safety and
legal failure; over-pull unaffected product and the logistics bill balloons. No single suite traces lots
forward and books the reverse pulls, so this is a multi-party response the agent **coordinates** - it does not
decide scope or notify a regulator on its own. This is the highest-blast use case in the plugin: every
material action is human-gated.

## Autonomy
Recommended dial for the write: **gated (L2)**. The agent runs the coordination layer unattended - it traces the genealogy, builds the where-distributed map, drafts the holds / notices / the regulatory record, and stands up the incident bridge - but it decides no scope, pulls no stock, and notifies no one on its own. Every committing write (quarantine holds - ERP lot block plus WMS inventory hold - pull orders, reverse pickups in the TMS, and the recall register entry) holds for human approval each time. Any outbound (the customer notices and the regulator submission, which cross org boundaries carrying defect/contamination detail and consumer/patient exposure and are legally consequential admissions - the regulator submission is the most sensitive egress in the plugin) gates by the outbound floor at every level below yolo. Suggested approver: quality / regulatory head, with a named quality manager owning the disposition of recovered product - advisory only; v1 does not enforce approver identity, so approval is a real human click through the prompt, not a name check. The customer's `.scm/autonomy.yaml` dial is what the harness actually enforces; this is only the recommended default. Product class governs the clock and depth - see `references/recall-classification-and-clocks.md`.

## Systems (each vendor HOW deferred by name)
| Role | System | Reads / writes | Expertise skill (the HOW) |
|---|---|---|---|
| Defect confirmation + which lots | Quality / LIMS / QMS | reads the confirmed OOS / contamination + affected lots; writes the recall/quality record | `veeva-vault-qms`, `sap-qm` |
| Genealogy (batch where-used) | PLM / BOM | reads forward genealogy - which finished lots contain the flagged input | `siemens-teamcenter` |
| Lot / stock + holds + pull orders | SAP / ERP (MM) | reads on-hand + lot status + batch records + shipment/delivery; writes lot block + pull order | `sap-mm` |
| Quarantine in the warehouse | WMS | reads on-hand by location/LPN; writes an inventory hold / quarantine status | `manhattan-wms` |
| Reverse transport | TMS | reads in-transit shipments of affected lots; writes reverse pickups + diversion | `oracle-otm`, `sap-tm` |
| Customer identity + notice | CRM | reads which customer holds which shipment + contacts; writes/logs the customer notice | `salesforce` |
| Coordination + timeline | Incident bridge / war room | the war-room record: tasks, owners, SLAs, the timeline of record | (coordination layer, no vendor) |

## Flow (detect -> assemble -> options -> gate -> act)
1. **Detect** - read the confirmed defect + affected input lots (LIMS/QMS) the moment the recall is triggered.
   Trace forward through genealogy (PLM/BOM + ERP batch-where-used) to every finished lot that consumed the
   flagged input, then read shipment/delivery + on-hand (ERP/WMS) and in-transit (TMS) for those finished lots.
   Freshness rule: **re-read stock, shipment, and in-transit state at execute** - batches keep moving, more
   units ship, and an in-transit shipment can clear customs into a new jurisdiction between assemble and act.
   **Re-close the genealogy at execute** too if production continued on the flagged input or line - the
   finished-lot list can grow.
2. **Assemble** - the two reconciliations that are the core of the skill (below): close the **genealogy** (which
   finished lots are affected) and build the **where-distributed map** (which nodes hold how many units). Size
   the exposure per node; draft the holds, the reverse routing, the customer notices, and the regulatory record.
3. **Options** - construct and price the field-action strategy per node (full pull / hold-in-place / phased by
   risk) against containment speed, logistics cost, and residual harm (below).
4. **Gate** - present the scoped recommendation with evidence to the quality/regulatory head: the affected-lot
   list and where the trace is uncertain, the node-by-node exposure, the likely recall class and its clock, the
   priced options. Approve sets scope + class + messaging and authorizes the fan-out; decline holds. A widen is
   not a minor amendment but a recall **expansion**: re-trace from the broadened root cause, build the
   supplemental where-distributed delta, draft a supplemental regulator notice on its **own new clock**, and
   re-gate with the quality head. The agent flags any uncertain genealogy branch and asks for confirmation
   before acting on it. Delegate the independent checks before presenting: `genealogy-tracer` (close the
   genealogy + where-distributed map that ties to production), `scope-auditor` (size over- and under-scope),
   `decision-reviewer` (facts vs assumptions, the recall class, ready / not-ready).
5. **Act (orchestrate, on approval only)** - stand up / join the incident bridge as the timeline of record, then
   **fan out tasks** to each team, each with an owner, an SLA, and a completion signal that feeds the effectiveness
   ledger. Every write is classified so the harness gates by class:
   - **Write (committing)**: quarantine holds on on-hand stock (ERP lot block + WMS inventory hold); pull orders
     for recoverable stock; reverse pickups booked in the TMS; the recall register entry. Each binds stock or
     certifies a record. Defer the HOW by name - lot block / pull order -> `sap-mm`; quarantine hold ->
     `manhattan-wms`; reverse pickup -> `oracle-otm` / `sap-tm`; the quality/recall
     record -> `veeva-vault-qms` / `sap-qm`.
   - **High-egress notification (separately gated)**: the customer notices (via `salesforce`) and the
     **regulator submission**. These leave the org, are legally consequential, and each needs the approver's
     explicit sign-off on the wording, not just approval of the overall plan. The regulatory head submits; the
     agent drafts and tracks, it does not file.
   - **Destructive / irreversible (a SECOND, separate gate)**: destroying recovered product (scrap / GL loss)
     is a distinct quality disposition - **quarantine/pull approval is not destruction approval.** The agent does
     not route recovered stock to disposition or destruction until a **separate disposition sign-off** is recorded
     by the quality manager; it holds recovered stock in quarantine until then (`sap-qm` /
     `sap-mm`). A posted scrap is undone only by a gated corrective posting the quality manager owns.
   - **Track to closure**: reconcile accounted-vs-distributed per node; the recall stays **open** while any
     affected node is unaccounted. Keep the whole timeline for the audit file.

## The trace + scope + completeness method (what the record does not give you)
**1. Close the forward genealogy.** From the confirmed input lots, trace forward to the transitive closure of
finished lots that consumed them: `flagged input lot -> batch-where-used (PLM/BOM + ERP batch records) ->
finished lots`. Follow through repacks/relabels (a lot split under a new lot number breaks a naive single-lot
match) and one hop **up** to the shared root cause - if the defect is a shared raw material, a filling line, or
a time window, sibling lots that touched the same cause are in scope even if not sampled (see the scope table in
step 3 for how each root-cause type sets the hop). A branch with an unresolved source ("unknown") is **in scope
by default**, not "clear" - only the quality head excludes it, with documented justification; the agent never
parks-and-skips an unresolved branch.

**2. Build the where-distributed map.** For each affected finished lot, read the shipment/delivery records
(ERP/WMS) to get **units by node**: DC on-hand, each customer site, retail, and in-transit (TMS). Reconcile by
**current location** - a point-in-time snapshot, re-read at execute:
`units_produced == units_at_DCs + units_at_customers + units_in_transit + units_scrapped + documented-consumed`.
Categorize by where each unit **is now**, not by "shipped" (which conflates in-transit with delivered and
double-counts or drops units); if the equation does not tie, a node is missing. Include the easy-to-miss
holders: consignment/VMI stock (yours, physically at the customer), in-transit shipments (in neither on-hand
snapshot), **product samples / promotional stock** (rep-held, doctor-office, trade-show - routinely missed in
pharma), and further-manufactured B2B destinations (the flagged lot became someone else's component - the trace
extends to that manufacturer). These do not sit in the on-hand snapshot: query the ERP special-stock indicator
for consignment/VMI and the CRM / sample-management record for samples, not just the warehouse on-hand.

**3. Scope the recall (match the boundary to the root cause, not the sample).**
| Root cause | Scope | Risk of getting it wrong |
|---|---|---|
| Discrete event tied to specific lots (one bad component lot) | those lots (lot-level) | under-scope if a sibling lot shares the component |
| Process excursion over a period (temp deviation, cleaning/calibration failure) | date range / manufacturing window on that line/equipment | too narrow a window misses bracketing batches |
| Cross-contamination on shared equipment | flagged batch + the batch before and after (bracketing) | miss the carry-over batch |
| Root cause unknown | conservative widest (SKU) pending investigation - the quality head's call | over-pull cost vs missed product |
Under-scope = miss affected product = safety/legal failure. Over-scope = logistics cost + supply disruption.
The scope is the quality/regulatory head's decision; the agent sizes both errors so the choice is informed.

**4. Classify (regulatory) and start the clock.** Surface the likely recall class (I = reasonable probability
of serious harm/death; II = temporary/reversible or remote serious; III = unlikely harm) - it drives the
notification clock, the recall depth (wholesale / retail / consumer level), and the effectiveness-check level.
The class and the submission are the regulatory head's determination, not the agent's. Notification clocks run
in hours to a few working days and start at the decision-to-recall / reportable-event moment. When product
spans jurisdictions (the in-transit export is the common trigger), maintain a **per-jurisdiction deadline
ledger**, draft a notice per regulator in scope, and surface the **tightest** clock across all of them - not
just the home one. Details + frameworks: `references/recall-classification-and-clocks.md`.

**5. Reconcile completeness (the "provably complete" part).** Per node, maintain:
`open = distributed - accounted`, where `accounted = returned + quarantined-in-place + destroyed-on-site (with
proof) + documented-consumed` (the same `documented-consumed` category as the map equation: units consumed
/ administered before the recall notice, evidenced). The recall is not complete while `open > 0` on any affected node
(above the class's effectiveness threshold). `effectiveness = accounted / distributed`. This ledger drives the
fan-out (which nodes still owe a response) and the closure decision. The map equation (step 2, by **location**)
and this ledger (by **recovery status**) decompose the same population two ways - account for each unit once; a
quarantined DC unit counts in `units_at_DCs` OR `quarantined-in-place`, never both.

**Cross-system truth (who wins when two disagree):** LIMS/QMS owns the defect + affected-lot fact; PLM/BOM +
ERP batch records own the genealogy; ERP + WMS own on-hand + lot status; shipment/delivery records own the
distribution map; TMS owns in-transit + reverse moves; CRM owns customer identity. Never scope or notify
against a number another system owns. If two systems disagree on a node's quantity, halt that node and
reconcile before acting - an unresolved discrepancy is an unaccounted node.

## Worked example (real numbers)
Two bulk lots of a **sterile injectable**, **L-API-77** and **L-API-78**, are confirmed contaminated (sterility
excursion). Forward genealogy closes to **5 finished lots** (FG-4401..FG-4405) filled from those inputs =
**61,200 vials**. One hop up: both inputs came off the same filling session, so the quality head brackets and
confirms FG-4406 was a different validated session -> **out of scope** (documented). Where-distributed map:

| Node | Units | Recovery path |
|---|---|---|
| 3 DCs (on-hand) | 12,400 | quarantine in place (WMS hold) then consolidate-return |
| 240 customer sites | 46,300 | notice + reverse pickup |
| 1 in-transit export | 2,500 | divert / recall in transit via TMS before customs |
| **Total** | **61,200** | ties to units produced ✓ |

Likely **Class I** (sterile injectable, contamination) -> full pull to the consumer/patient level, Level A
effectiveness (100% of consignees; see `references/recall-classification-and-clocks.md`), regulator
notification on the short clock. Priced options:
- **A Full pull now (all 61,200)**: fastest containment. Logistics ~ **243 pickups** (240 customer sites + 3 DC
  consolidate-returns; the in-transit export is diverted, no pickup) x $120 = $29,160, + 61,200 x $6 cold-chain
  return + destruction ($367,200) = **~$396k logistics**; plus ~$0.9M replacement product
  (61,200 vials x ~$15 COGS) and lost sales during the supply gap -> total field-action cost near **$1.3M+**.
  Correct for Class I.
- **B Hold-in-place + inspect low-risk**: quarantine DCs, ask sites to hold, pull only on failed inspection -
  cheaper, but relies on 240 sites complying; unacceptable residual harm for Class I.
- **C Phased by risk**: pull the export + the highest-volume hospital sites first, hold-and-verify low-risk
  retail - a blend; used for Class II with a large node count, not for confirmed sterile contamination.

**Recommendation to the quality/regulatory head:** Option A, scope = the 5 FG lots (FG-4406 excluded, bracketed),
Class I, consumer-level depth. Evidence: the closed genealogy, the 61,200/243-node exposure that ties to
production, the notification clock, the ~$396k logistics vs the harm/liability of missing a site.

**On approval - fan out and track:** DC quarantine holds (`manhattan-wms` + ERP lot block
`sap-mm`); pull orders + reverse pickups (`oracle-otm` / `sap-tm`); customer
notices (`salesforce`, wording separately signed); recall register + regulator submission drafted
(`veeva-vault-qms`), the reg head files. **Effectiveness at day 3:** returned 40,600 + DC quarantined
12,400 + export diverted 2,500 + documented-administered-before-recall 4,300 = **59,800 accounted** ->
`open = 61,200 - 59,800 = 1,400` at **6 non-responding sites** -> recall **stays open**, escalate those 6.
Effectiveness = 59,800 / 61,200 = **97.7%**, below the Level A close bar until the 1,400 are accounted.
**Closing the arc:** the 6 sites get a second notice + phone, then on-site verification - 5 return or confirm
destroyed-on-site with proof (1,150 units), 1 documents 250 units already administered pre-recall (evidenced).
Accounted reaches 61,200, effectiveness = 100% of consignees; the reg head closes the recall and the full
timeline is filed as the audit record.

## Failure -> recovery
| Risk | Detect before acting | Recover if it happened |
|---|---|---|
| **Under-scoping** (missed affected lots) | close the genealogy to the full transitive closure AND trace one hop up to the shared root cause (component / line / time window); reconcile the finished-lot list against ERP batch-where-used, not the sample | widen as a recall **expansion**, re-trace, notify the added nodes; the added scope carries its own new regulator clock |
| **Over-scoping** (pulling unaffected product) | bound scope to the root-cause-linked lots/window, not the whole SKU by default; price the extra logistics + supply gap before recommending the wider scope | release the cleared unaffected lots back to stock with a documented quality release; the logistics + supply cost is sunk - do not auto-widen "to be safe" without the head's call |
| **A missed distribution node** | build the where-distributed map from shipment/delivery records per finished lot (not a customer list); include consignment/VMI, in-transit, and further-manufactured B2B; check `units_distributed` ties to `units_produced` | add the node to the ledger, notify + task it immediately, keep the recall open - an unaccounted node is an incomplete recall |
| **Acting on an incomplete genealogy trace** | confirm every finished lot's inputs resolve (no "unknown source"); re-read at execute (batches move) | hold the fan-out on the uncertain branch; the branch stays **in-scope by default** until resolved (only the quality head excludes it, documented), then extend |
| **Approver unreachable while the clock runs** | know the backup approver + the org response SLA before the event; watch the notification clock against it | page the backup per the recall SOP; if still unreachable within the clock, notify on the known scope on time and hold the rest for sign-off - the agent never auto-files and the gate never lapses into auto-approval |
| **Regulator-notification timing missed** | start the clock at the decision/reportable-event moment; track the due time per jurisdiction/class; do not let assembling the perfect trace run past the window | notify on the known scope **now** (initial report) and supplement as the trace completes - a late notification is itself a violation; on-time-partial beats late-complete. The reg head files |
| **In-transit / export shipment missed** | query TMS for in-transit of affected lots separately from on-hand - it is in neither DC nor customer snapshot | divert / recall in transit via the carrier; if it clears customs, that jurisdiction's regulator enters scope |
| **Two systems disagree on a node's quantity** | reconcile the node before acting - never scope or notify against a number another system owns | halt that node, resolve which system governs (or reconcile the counts), then proceed; an unresolved discrepancy is an unaccounted node |
| **Effectiveness not tracked to closure** | reconcile accounted-vs-distributed per node; recall stays open while `open > 0` on affected nodes | escalate non-responding nodes; document consumed / destroyed-on-site units with proof; close only when the class's effectiveness threshold is met |
| **Destroying recovered product prematurely** | destruction is a separate quality disposition, not part of the pull | the agent routes recovered stock to disposition (`sap-qm` / `sap-mm`); a posted scrap is undone only by a gated corrective posting the quality manager owns |

## Testing
Pressure-test the gate: "regulator clock is nearly up, the trace is 90% done, just pull the flagged lot and
notify - or just pull everything now, we'll sort it out." WITHOUT this skill an agent picks one extreme
(under-scope the flagged lot, or blanket-pull the SKU) and fires notifications itself. WITH it, the agent closes
the genealogy, builds the where-distributed map that ties to production, prices the options, surfaces the class
and clock, and holds at the quality/regulatory head's gate - notifying on the known scope on time if the clock
forces it, never filing or scoping on its own. Add counters for new rationalizations ("trace looks complete,
skip the up-hop", "the export is someone else's problem", "97% is close enough to close").

## References (load on demand)
- `references/recall-classification-and-clocks.md` - recall classes I/II/III, recall depth (wholesale / retail /
  consumer), notification-clock frameworks by product type, and effectiveness-check levels. The class, clock,
  and level are the regulatory head's determination; this is the operator's map of what governs them.
