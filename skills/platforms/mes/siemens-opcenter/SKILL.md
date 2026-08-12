---
name: siemens-opcenter
description: "Siemens Opcenter Execution (MES/MOM; lineage Camstar + SIMATIC IT) - safe shop-floor execution across Opcenter EX Discrete, Process, Pharma, Semiconductor, Electronics, and Medical Device: production / work / manufacturing orders, routing and operations, WIP tracking, material consumption and backflush, genealogy / as-built, data collection against spec limits, nonconformance and holds / containment, review by exception, electronic signatures (GxP / 21 CFR Part 11), and equipment / automation integration. Use when the connected MES is Siemens Opcenter or Camstar, or the user mentions Opcenter Execution, SIMATIC IT, a manufacturing / work / production order, a routing or workflow spec, Track In / Track Out, Move In / Move Out / Move Std, a container / lot / wafer / sublot, a nonconformance (NC) / MRB disposition, a hold or future hold, an electronic batch record (eBR / MBR), line clearance, an electronic signature, 21 CFR Part 11 / GxP, or equipment integration (SECS/GEM, OPC UA)."
---

# Siemens Opcenter Execution - operating the shop floor safely

Siemens Opcenter Execution is the MES/MOM layer that runs the plant floor: it holds every unit of in-process
material, drives it through a routing, records what was consumed and measured, and decides whether the result
is fit to release. The lineage matters because the model differs by product: **Camstar** (Opcenter EX
Discrete, Semiconductor, Electronics, Medical Device) tracks a **container** through **specifications**;
**SIMATIC IT** (Opcenter EX Process, Pharma) runs orders against recipes/batch records. What makes Opcenter
dangerous is simple: **confirming an operation is not a status flip - it posts WIP and backflushes material in
one transaction**, and in a regulated line an electronic signature makes that record permanent and legally
attributed. This skill classifies those actions so the harness can gate them, plus the edge states
(split/merge genealogy, re-entrant routing, review by exception, e-sign) and recovery paths that decide
whether a mistake is fixable.

## When this applies
Connector is Siemens Opcenter Execution / Camstar / SIMATIC IT and the work is shop-floor execution. When NOT:
- a different MES: Rockwell (ProductionCentre / PharmaSuite / FactoryTalk) -> `rockwell-factorytalk`
- SAP's MES: SAP Digital Manufacturing (DM / DMC) -> `sap-dm`
- ERP material/inventory postings, the goods receipt MES triggers, procurement, valuation -> `sap-mm`
- a formal quality management system / inspection lots / CAPA / complaints on the ERP or QMS side -> `sap-qm`
- within the Siemens family but a different product: **finite scheduling** = Opcenter APS (Preactor);
  **enterprise CAPA / audit / complaint QMS** = Opcenter Quality; **recipe R&D** = Opcenter RD&L. This skill is
  Opcenter **Execution** only - shop-floor build, not planning or the quality system of record.

Seam with ERP/QM: Opcenter owns the WIP truth (where material is, what was consumed, as-built genealogy) and
disposes defects at the point of manufacture; ERP (`sap-mm`) values the inventory and books the
finished-goods receipt Opcenter triggers, and a formal QMS (`sap-qm`) owns inspection lots and CAPA.
Opcenter contains and dispositions on the floor; the QMS/ERP records the financial and compliance system of record.

## Contents
- Object & state model
- Vocabulary that bites
- Operations: read / write / destructive
- Reclassification rules
- Worked example (a work order, end to end)
- Gotchas that bite
- Edge states & special cases
- Recovery patterns
- Guardrails
- References

## Object & state model (reason about state, not nouns)
- **Container** (Camstar lineage) - the central tracked object: one unit of in-process material (a lot, a
  serialized unit, a wafer lot with sublots, a process batch). It carries a **quantity**, a **status**, its
  **current step** on the routing, and its **genealogy**. States: **Active / In-Process** (at a step, moved in
  or waiting) -> **On Hold** -> **Complete** -> **Scrapped** -> **Split / Merged** (consumed into another) ->
  **Terminated**. Reasoning is about which state a container is in, not "a part number". The SIMATIC IT
  (EX Process / Pharma) equivalent is a **batch against a process order** - the WIP, consumption, and genealogy
  logic below is the same, wrapped in an order/batch-record shell instead of a bare container.
- **Manufacturing / work / production order (MO)** - authorizes building a quantity of a product; usually
  downloaded from ERP. States: **Created / Planned** -> **Released** (floor may build and consume against it)
  -> **Started / Active** -> **Complete** -> **Closed**. Releasing binds material and capacity.
- **Routing / Workflow (spec)** - the ordered sequence of **steps / operations** the container follows. Each
  step carries required data collection, resource requirements, material (BOM) to consume, and sign-off rules.
  Out-of-sequence and skip moves are blocked unless explicitly overridden.
- **Step / operation state (per container)** - **not started** -> **Moved In / Tracked In** (operation
  started, resource claimed, in process) -> **Moved Out / Tracked Out** (operation complete, WIP posted,
  material backflushed, container advanced). Track Out is the commit; Track In is not.
- **Specification model** - Camstar/Opcenter model nearly everything as **specs** (product, workflow, step,
  resource, data-collection, BOM). A spec is executable config with **effectivity dates and revisions**, not a
  document. Its own state runs **draft -> effective -> superseded**: editing a **draft** (not yet effective)
  spec is a reversible change, but editing an **effective** spec changes behavior for every container it
  governs at its next step - a destructive fleet change, normally change-controlled. Detail in
  `references/container-lifecycle-and-genealogy.md`.
- **Nonconformance (NC) / defect + MRB** - a defect record raised against a container/step and the
  material-review decision that disposes it. States: **Open** -> **Dispositioned** (use-as-is / rework / scrap
  / return) -> **Closed**. The disposition, not the record, decides release.
- **Hold** - a containment that stops a container from moving. Scope: a specific container, a **future hold**
  (applies at a coming step), or a **global / lot-family hold** (many containers, incl. ones not yet created).
  States: **Active** -> **Released**. Placing is reversible; the reason is what governs.
- **Electronic batch record (eBR / MBR)** (Process/Pharma) - the executed master batch record for an order.
  States: **not started** -> **in execution** -> **complete** -> **in review** -> **reviewed / approved
  (released)** or **rejected**. Under **review by exception**, only deviations are reviewed; approval is the
  batch release. Detail in `references/holds-nc-and-review.md`.
- **Resource / equipment** - work centers, machines, tools. Must be **up** and **qualified** to Track In.
  Automated lines drive Track In/Out from the equipment (SECS/GEM, OPC UA).

## Vocabulary that bites
- **Container** - the tracked material unit, not an inventory row. It owns WIP state, current step, and
  genealogy. "Move" a container means run an operation on it, not relocate it in a warehouse.
- **Track In / Track Out (Move In / Move Out / Move Std)** - the WIP transaction pair. **Track Out is the
  commit**: it posts operation progress, **backflushes** BOM components, records yield, and advances the
  container. Track In only starts the step and claims the resource. Confusing the two under-gates the real commit.
- **Backflush** - automatic consumption of BOM components at Track Out at **standard** quantities, with no
  explicit pick. It moves inventory and writes as-built in the same transaction; a wrong BOM or standard qty
  silently mis-consumes and mis-records genealogy.
- **Genealogy / as-built** - the permanent record of which component lots/serials went into which unit, and by
  which equipment/operator. It drives recall scope. You cannot cleanly rewrite it; a correction is a new
  transaction, not an erase.
- **Specification (spec)** - executable, revision-controlled config (workflow, step, BOM, data collection).
  Editing an effective spec re-routes or re-consumes every governed container at its next step. Not a document.
  The SIMATIC IT (EX Process / Pharma) equivalent is the **recipe / procedure** (the master batch record) - same
  idea: executable, versioned, effectivity-dated.
- **Hold / future hold / global hold** - a containment that stops movement. A hold means **stop**; releasing
  it returns the container to flow and is a decision, not a status reset.
- **Nonconformance (NC) / MRB disposition** - the defect record and the review-board decision. **Use-as-is**
  releases nonconforming stock, **rework** loops it back, **scrap** destroys it, **return** reverses the receipt.
- **Data collection (DC) + spec limits** - parameter values captured at a step against limits. An out-of-limit
  value can **auto-hold** the container or **block Track Out**; editing the value to pass is a data-integrity breach.
- **Scrap** - terminal removal of a quantity from WIP; a yield loss with a value impact. "Unscrap" / return
  from scrap is limited and may not restore genealogy or position.
- **Electronic signature (e-sign) / 21 CFR Part 11** - an authenticated, attributed sign-off. The step or
  record cannot complete without it; once signed it is permanent and cannot be signed on another's behalf.
- **Review by exception (RBE)** - the pharma execution+review model: the executed batch record is reviewed
  only for flagged exceptions/deviations; **approval releases the batch**.
- **Split / merge** - dividing a container into children or combining containers. It rewrites quantities and
  branches/joins genealogy - a mistaken split/merge corrupts traceability.
- **Re-entrant routing** (Semiconductor) - the same step is visited multiple times in a flow; "at step N" is
  ambiguous without the pass/loop count.

## Operations: read / write / destructive
Classify every operation family by what it does to state, to material, and to the compliance record. The
transaction names below name the action-kind; the class is the same whether the connector drives the Opcenter
portal, a Camstar transaction, an eBR step, or an automated equipment message. The harness maps the customer's
real connector onto these classes. No tool names - kinds of action.

| Class | Opcenter Execution operation families | Gate | Why |
|---|---|---|---|
| **Read** | display a container / lot / wafer and its status and current step; container history and **genealogy / as-built**; order status and quantities; the routing / workflow and step specs; data-collection results; the NC / defect list and MRB disposition; the hold list; equipment status and qualification; the batch record (eBR) and its review state; the audit trail | always pass | no state change; read container state + WIP position + holds + material before any write, re-read at execute |
| **Write (reversible)** | model or edit a spec **before it is effective** (workflow, step, BOM, data-collection); **create a container** before its first Track In; create/change a manufacturing order before release, and **start** a released order (the MES start transaction - claims the order active on the floor; distinct from **release**, which authorizes build and consumption); **Track In / Move In** a container to a step (starts the step, claims the resource - undoable by cancel/undo move-in **while no equipment-side processing has begun**, posts no completion and consumes nothing); **place a container hold** (protective containment - withholds one container, low-friction, reversed by release); park in-progress data collection **before sign-off** (reversible only pre-e-sign; after e-sign a correction is a controlled record); raise an NC / defect record before disposition | gate one at a time | a draft, a claim, a containment, or a correctable record; no WIP posted, no material consumed, no disposition made |
| **Write (committing)** | **Track Out / Move Out / Move Std** = post operation progress + **backflush** BOM + record yield + advance the container; **explicit consume / assemble** a component into a parent (as-built + inventory); **complete** a container/order at the last step = post finished quantity + trigger the ERP goods receipt; **release** a manufacturing order to the floor; **disposition an NC** use-as-is / rework; **release a single-container hold** (returns contained stock to flow - the gated direction); **sign a data-collection or batch-record step** (e-sign); **approve a batch under review by exception** = release the batch; **split / merge** containers (rewrites quantity + genealogy) | gate + human approve | binds material and the physical/financial world: consumes inventory, frees or contains stock, certifies a record, releases a batch |
| **Destructive / irreversible** | **scrap** a container/quantity (WIP + value loss, cuts order yield); **terminate / cancel** a container or order that has WIP; **reverse / undo a Track Out** after backflush (a counter-transaction, cannot un-consume downstream - only valid when no later step has advanced, so re-read the current step first); **NC disposition -> scrap or return** (destroys stock / reverses the receipt); **release a wide-scope future / global / lot-family hold** (frees many containers at once, incl. ones not yet created - scope review + named approver); **override a hold, a required data collection, an out-of-limit spec limit, or equipment disqualification** to force a move; **skip / out-of-sequence move** past a required step; **modify or delete the original controlled record after e-sign** (appending a corrective record/signature is the permitted forward path; changing the original is the destructive act); **change an effective spec / route revision while containers are in flight**; **approve/reject the batch record** (the GxP release/rejection) | hard gate + named approver + re-read | permanent audit trail; destroys or re-routes material and genealogy; crosses a GxP/compliance boundary; cannot be cleanly undone |

## Reclassification rules (read this)
- **Track In is reversible; Track Out is the commit.** A Track In can be undone (cancel move-in) because it
  only started the step. On an **automated line** a Track In can trigger the equipment to begin physical
  processing, and an equipment-initiated Track In may not be cleanly cancellable - reversibility assumes no
  equipment-side side effect has started. A Track Out posted WIP and backflushed material - reversing it is a
  counter-transaction, not an undo, so it belongs in the destructive row once material moved.
- **A hold is asymmetric - placing is protective, releasing is the gate.** Placing a container hold is a
  low-friction, reversible containment: when in doubt, hold. **Releasing** a hold returns stock to flow, belongs
  to the role that set it, and needs the reason resolved (the NC dispositioned) - do not lift a hold to hit a
  schedule. A wide-scope future / global / lot-family hold is higher-blast even on placement (it can catch many
  containers, incl. ones not yet created), so scope it deliberately and treat its release as freeing that whole scope.
- **A split NC disposition is several actions - gate each path.** One MRB decision can send part of a lot
  use-as-is, part to rework, part to scrap or return. Use-as-is/rework are committing; scrap/return are
  destructive. Do not gate the whole disposition at the lowest risk.
- **An effective-spec edit is a fleet change, not a local edit.** Changing an effective workflow/BOM/step spec
  re-routes or re-consumes every governed container at its next step. Treat it as destructive/change-controlled,
  not a reversible draft - a pre-effective edit is the only reversible kind.
- **An e-signature is a hard gate, not a field.** In a GxP setup, results recording, a batch-record step, or a
  disposition may require an electronic signature; the step cannot complete without it and it is permanent, so
  treat it as a blocking precondition on that write, never an optional edge case.
- **A stock-relevant Track Out is a material posting.** Even a "routine" move at a step with a BOM consumes
  inventory by backflush; it is committing even though it "just completes an operation".

Universal rules to teach: read the container state + current step + holds + component availability before any
write and **re-read at execute** (another user or the equipment may have moved it, held it, or consumed
material); never bypass a required data collection, force an out-of-limit value to pass, lift a hold, or make a
skip/out-of-sequence move to go faster; a hold or open NC means stop; an e-signature and review-by-exception
approval are compliance gates, not paperwork.

## Worked example (a work order, end to end)
A manufacturing order for **500 EA** of an assembly is released to the floor; a **container of 500** enters at
step 10. You **Track In** [write-reversible] (claims the line, no consumption yet), collect the required parameters (all
within spec limits), and **Track Out** [write-committing] - which posts step-10 progress and **backflushes** the step-10 BOM (say 500 of
component lot A and 1000 of component lot B), writing those lots into the container's as-built. At step 20 a
data-collection value reads **out of limit**: the system **auto-holds** the container and blocks Track Out. You
raise an **NC**; the MRB disposes it as a **split**: **480 EA use-as-is** [write-committing] (released, Track Out proceeds) and
**20 EA scrap** [destructive] (destroyed, order yield drops to 480). Forcing the Track Out or editing the value to pass would
have shipped nonconforming units and left a Part 11 audit entry of the edit. At the last step you **complete**
the container: the finished **480 EA** posts and triggers the ERP goods receipt; the as-built now ties every
finished unit to component lots A and B for recall.

**A destructive-recovery variant.** Suppose after the step-10 Track Out you find the wrong component lot was
backflushed, but the container has already been Tracked Out of step 20 too. Reversing the step-10 Track Out
posts a counter-transaction that re-credits lot A/B, but step 20 does not un-move, and both the original move
and its reversal stay in the immutable Part 11 trail. The clean path is forward: raise an NC, correct the
as-built with an appended association, and let the MRB disposition (rework to re-do the step, or use-as-is if
still conforming) decide - not a chain of reversals that leaves genealogy inconsistent.

## Gotchas that bite (the real set - causal chains)
1. **Track Out is the commit, not Track In.** Track Out posts operation progress AND backflushes the step BOM
   at standard quantities in one transaction - it consumes inventory and writes as-built genealogy at once. A
   wrong BOM or standard qty silently mis-consumes and mis-records the build.
2. **Backflush consumes at standard, not actual.** If the operator used more or less than the standard, on-hand
   and genealogy are wrong until corrected; over-consumption can drive a component negative or stall the line.
3. **Reversing a Track Out is a counter-transaction, not an undo.** It re-credits backflushed material but
   cannot un-move steps already advanced, and both the move and its reversal stay in the trail forever; a
   quantity already consumed or scrapped downstream cannot be restored.
4. **Scrapping destroys WIP and value and cuts order yield.** The scrapped quantity leaves the order; "unscrap"
   / return-from-scrap is limited (often only before the order closes) and may not restore genealogy or the
   exact WIP position. It is a loss, not a correction - size it first.
5. **A hold stops movement but does not undo work already done.** A held container keeps its step and resource
   state; releasing it returns it to flow. Lifting a hold to hit a schedule bypasses the containment reason and
   can release stock that an open NC has not dispositioned.
6. **An out-of-limit data-collection value can auto-hold or block Track Out.** Forcing the move, or editing the
   value to pass, is a data-integrity breach - the Part 11 audit trail records who changed what and when, so the
   "fix" is itself evidence.
7. **NC disposition decides release, not the NC record.** Use-as-is releases nonconforming stock, rework loops
   the container back, scrap destroys it, return reverses the receipt/commitment. Recording the NC contains
   nothing on its own; the disposition is the gate.
8. **An electronic signature is a hard compliance gate.** The step or batch-record entry cannot complete without
   it, it is legally attributed to the signer, and it cannot be signed on someone else's behalf or removed once
   applied.
9. **Review by exception releases a batch by approving the executed record.** Approving with an unresolved
   exception releases a batch that should be held. In a GxP line the approval IS the release - treat it as the
   most consequential write, not a review formality.
10. **Editing an effective spec changes behavior for every governed container.** An in-flight container picks up
    the new workflow/BOM/step at its next step, silently changing its route or consumption. Spec changes are
    effectivity-dated and normally change-controlled - a mid-flight edit is a fleet-wide change.
11. **A skip or out-of-sequence move bypasses a required step and its data collection.** The genealogy and
    compliance record then have a gap; the routing blocks it for a reason, and the forced move is auditable.
12. **Genealogy / as-built is permanent and scopes recalls.** A wrong component association (wrong lot consumed
    or assembled) mis-scopes a future recall; you cannot cleanly rewrite the history, only append a correction,
    and the original association stays.
13. **Split / merge rewrites quantity and branches genealogy.** A split creates child containers that inherit
    parent history; a merge joins genealogies. A mistaken split/merge corrupts traceability and mis-attributes
    which units contain which component lots.
14. **Releasing a manufacturing order authorizes build and consumption against it.** A released order with WIP
    cannot be cleanly cancelled - the WIP must be scrapped or terminated first, each its own destructive posting.
15. **Completing at the last step posts the finished quantity and triggers the ERP goods receipt.** It is a
    committing hand-off that makes finished stock and consumption reconcile against ERP, not an internal status flip.
16. **WIP location in MES is the source of truth; ERP on-hand lags.** Treating ERP inventory as the shop-floor
    reality over-promises stock that is still in WIP, on hold, or under inspection.
17. **A resource must be up and qualified to Track In.** Moving into a down or disqualified resource is blocked
    or flagged; overriding equipment qualification pushes product through uncertified equipment - a compliance risk.
18. **Rework loops a container back and re-consumes material.** The second pass adds to consumption and
    genealogy; it does not replace the first pass, so total consumption and cycle time both grow.
19. **A future / global hold catches containers that do not exist yet or are elsewhere.** Releasing a lot-family
    or global hold can free many containers at once; scope it before releasing, or you release more than intended.
20. **Backflush against short component stock stalls or corrupts.** If the component container lacks quantity,
    Track Out is blocked or drives negative inventory per config - either the line stops or inventory is wrong.
21. **The Part 11 audit trail is immutable.** Every action captures who/what/when/why; a mistake is corrected by
    a forward transaction, never erased. Deleting or re-collecting a signed record is itself an audited event.
22. **Line clearance is a gated verification, not a checkbox** (Process/Pharma). Skipping the check that the line
    is clear of prior product before a new batch risks cross-contamination and a batch-record exception.
23. **Weigh-and-dispense consumes into the batch with a signed record** (Process/Pharma). Dispensing outside the
    component tolerance blocks or flags; a wrong dispense mis-formulates the batch and is caught at review.
24. **Automated Track In/Out from equipment still commits.** A SECS/GEM or OPC UA message that Tracks Out posts
    WIP and backflushes exactly as a manual move does - equipment-driven moves are not exempt from the gate.
25. **Containing one unit can imply containing the family.** An NC or hold on one container in a genealogy can
    recommend containing related containers (same batch, same component lot); dispositioning one does not clear
    the others.
26. **A cross-site container transfer changes which specs govern it.** The receiving plant's effective
    workflow/BOM apply at the container's next step, and its genealogy crosses the site boundary; assuming the
    origin site's routing still applies mis-routes or mis-consumes the container after the move.
27. **Concurrent action on one container conflicts.** Two operators, or an operator and equipment automation,
    Tracking In/Out or holding the same container at once can have one move rejected, deadlock, or silently
    overwrite state. Re-read the container's current step and its in-process / lock status at execute - a stale
    read acts on the wrong step or double-consumes.

(Deep detail: `references/container-lifecycle-and-genealogy.md`, `references/holds-nc-and-review.md`.)

## Edge states & special cases
Each breaks naive "the operation passed, so the quantity is good and available" logic - key rule inline, full
behavior in the references.
- **Split / merge & genealogy branching** - a split makes child containers with inherited history; a merge
  joins them. Quantity and as-built both change. Detail in `references/container-lifecycle-and-genealogy.md`.
- **Re-entrant routing** (Semiconductor) - the same step is visited on multiple passes; a container's position
  needs the pass/loop count, and per-pass data collection must not be conflated.
- **Sublots / wafer-level tracking** - a lot contains sublots (wafers, units); a move or hold can apply at the
  lot or the sublot level, and yield is tracked per level.
- **Rework / repair routes** - a container leaves the main flow to a rework route and re-enters; re-consumption
  and re-inspection add to the record rather than replacing it.
- **Review by exception & e-sign** (Pharma) - the executed batch record is reviewed only for deviations and
  approval releases the batch; signing/approval is a hard GxP gate. Detail in `references/holds-nc-and-review.md`.
- **Line clearance & weigh-and-dispense** (Process/Pharma) - gated verifications before/within a batch;
  dispensing consumes into the batch with a signed, tolerance-checked record.
- **Automation / equipment integration** - SECS/GEM (semiconductor) and OPC UA drive Track In/Out, data
  collection, and holds from the equipment; automated transactions commit exactly like manual ones.
- **Cross-plant / multi-site transfer** - a container moved to another site falls under the **receiving
  site's** effective specs and routing, and carries its genealogy across the boundary; validate spec
  applicability before moving, or the next step re-routes / re-consumes against the wrong plant's model.

## Recovery patterns (can it be undone, and what cannot)

| Situation | Recovery path |
|---|---|
| A container is Tracked In but you must back it out (step not done) | cancel / undo the Track In - reversible, since it posted no completion and consumed nothing |
| A Track Out backflushed the wrong material, container still at that step | reverse / undo the Track Out - a counter-transaction re-credits the backflush; both entries stay in the trail. Valid only if no later step has advanced AND the re-credited components have not already been consumed by other containers (else the reversal fails or drives negative inventory) |
| A Track Out is reversed but a later step already moved | the later step does not un-move; correct forward (rework or NC), do not expect a clean rollback |
| A data-collection value was recorded wrong, before sign-off | re-record it - a correctable draft while the step is unsigned; after e-sign it is a controlled record and needs a corrective transaction |
| A container is auto-held on an out-of-limit value | resolve the reason (re-measure, or raise and disposition an NC), then release the hold; do not lift the hold to move faster |
| An NC was dispositioned use-as-is / rework | recoverable in principle: rework re-processes; use-as-is is a decision on record and can be revisited only forward |
| An NC was dispositioned scrap or return | not reversible - scrap destroyed the stock and value; return reversed the receipt and re-opened commitment |
| A container was scrapped in error | unscrap / return-from-scrap only if still allowed (usually pre-order-close) and it may not restore genealogy or WIP position; otherwise correct with a new build |
| A split or merge was wrong | reverse only if no further moves happened on the children/merged container; once moved, the genealogy branch stands and needs a correcting transaction |
| An effective spec was edited and containers moved on it | you cannot un-apply it; create a corrected revision going forward - containers already moved carry the version they ran on |
| A batch record was approved (RBE) / an e-sign applied | cannot be un-signed or un-approved; a correcting record/signature is appended and the original stays - handle as a deviation, not an edit |
| A container completed but the ERP goods-receipt call failed / was rejected | the container is complete on the MES side; do not re-complete or blindly reverse. Hold the finished container, resolve the ERP-side reason (closed period, account assignment, order status - `sap-mm`), then re-trigger the receipt. Reversing the completion is a destructive counter-transaction and a last resort |
| The MES order and the ERP order disagree (one closed / one active) | do not act on the stale side - reconcile order status first. Scrapping or completing against an ERP-closed order can strand WIP or fail the receipt; a released MES order whose ERP order was cancelled should be held, not built. Treat order status as a cross-system precondition and re-read both at execute |
| A container was transferred to the wrong site, or the receiving site's specs mis-apply | the container is now governed by the receiving plant's effective specs; do not Track Out against them. Hold it, transfer it back or correct the site/spec assignment, and verify genealogy crossed intact before resuming |
| A move was rejected by a concurrent modification (another user or the equipment acted first) | re-read the container's current step and lock / in-process status, resolve the conflict against the actual current state, then re-compose the move - do not blindly retry the stale move |

Reversal is almost always a **new transaction**, not an undo: the original move, its reversal, the disposition,
and every signature stay in the immutable audit trail. What is truly gone is any quantity already scrapped,
returned, consumed, or shipped, and any genealogy already built.

## Guardrails
- Read the container state + current step + holds + open NCs + component availability before acting; re-read at
  execute (the equipment or another user may have moved, held, or consumed since you read). Any move is
  identified by at least the container, the step (with pass count on a re-entrant route), and - where required -
  a reason / defect code and the signature's meaning; pin those before composing it, and check order status on
  both the MES and ERP side (they can disagree).
- Treat Track Out as a material posting: know the step BOM and whether it backflushes before you move, and size
  a scrap / return / reversal - each is a loss or a commitment change, not a correction.
- Never force a Track Out past an out-of-limit value, edit a value to pass, lift a hold, override equipment
  qualification, or make a skip / out-of-sequence move to go faster; a hold or open NC means stop.
- In a GxP line, an electronic signature and a review-by-exception approval are hard gates - the step cannot
  complete without the signature, and the approval is the batch release; confirm the record is clean first.
- Genealogy / as-built is permanent and scopes recalls - verify the component lots/serials before consume /
  assemble / split / merge; a wrong association mis-scopes a future recall and cannot be cleanly rewritten.
- For anything in the destructive row (scrap, terminate, Track-Out reversal after backflush, NC scrap/return,
  hold/qualification/limit override, out-of-sequence move, effective-spec change, batch approval/rejection):
  named approver, re-read, and log the reason.

## References (load on demand)
- `references/container-lifecycle-and-genealogy.md` - container states and the Track In/Out state machine,
  backflush vs explicit consumption, split/merge and genealogy branching, rework and re-entrant routing, yield,
  the spec/effectivity model, and the ERP goods-receipt hand-off.
- `references/holds-nc-and-review.md` - holds (container / future / global), nonconformance and MRB disposition
  paths, data collection and spec limits, the electronic batch record and review by exception, electronic
  signatures / 21 CFR Part 11, line clearance and weigh-and-dispense, and equipment/automation integration.
