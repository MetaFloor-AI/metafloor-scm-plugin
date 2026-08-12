---
name: sap-qm
description: "SAP Quality Management (QM) - inspection and quality disposition in SAP S/4HANA or ECC: inspection lots and origins, inspection plans and master inspection characteristics, results recording, the usage decision (accept / reject / rework) and its stock postings out of quality-inspection stock, quality notifications for defects and complaints, and quality info records that release or block a procurement or sales source. Use when the connected ERP is SAP and the work touches quality inspection or disposition, or the user mentions SAP QM, an inspection lot, QA01/QA02/QA03, a usage decision (QA11/QA12/QA13), results recording (QE01/QE51N), an inspection plan (QP01/QP03), a master inspection characteristic (QS21), a quality notification (QM01/QM02), a quality info record (QI01/QI02), QI / quality-inspection stock, a UD code, accept/reject/scrap/return, a certificate of analysis (CoA), batch restricted vs unrestricted status, or skip-lot / dynamic modification."
---

# SAP QM - operating quality inspection safely

SAP Quality Management controls whether received, produced, or stored stock is fit to use, and it holds that
stock in an inspection state until someone decides. The thing that makes QM dangerous is simple: **the usage
decision is not a note, it is a stock posting.** Accepting a lot posts the quantity out of quality-inspection
stock into unrestricted use, which makes it available to MRP and ATP the instant you save; rejecting to scrap
destroys stock and value; returning it to the vendor reverses the receipt. On top of that, a usage decision
feeds the vendor score and the sampling history, and issuing a certificate of analysis certifies quality to a
customer. This skill classifies those actions so the harness can gate them, plus the edge states (sampling,
dynamic modification, batch linkage, recurring inspection) and recovery paths that decide whether a mistake
is fixable.

## When this applies
Connector is SAP and the work is quality inspection / disposition in QM. When NOT:
- lab data management, instruments, stability studies, a dedicated LIMS -> `labware` or `veeva-vault-qms`
- ERP stock valuation, movement types, GR/IR, the MM side of a goods receipt -> `sap-mm`
- the ledger side of a scrap loss or a variance account -> `sap-fi`
- warehouse execution (bins, tasks, waves, handling units) -> `sap-ewm`

Shared seam with MM: QM decides whether a goods receipt lands in **quality-inspection stock** and creates an
**inspection lot**; MM owns the movement types and the valuation behind those stock postings. QM disposes,
MM values. See `references/inspection-lot-lifecycle.md` and defer deep movement-type detail to `sap-mm`.

## Contents
- Object & state model
- Vocabulary that bites
- Operations: read / write / destructive
- Reclassification rules
- Gotchas that bite
- Edge states & special cases
- Recovery patterns
- Guardrails
- References

## Object & state model (reason about state, not nouns)
- **Inspection lot** (QA01/QA02/QA03) - the central object: a request to inspect a specific quantity of one
  material, created automatically at a trigger or manually. Its **origin** decides what triggered it and
  whether it holds stock: **01** goods receipt from a PO, **03** in-process during production, **04** goods
  issue, **05** other, **08** stock transfer, **09** recurring inspection of stored batches, plus SD delivery
  and returns origins; a manual lot with no reference document uses a general inspection type (89).
  Stock-relevant origins (01, 08, recurring) hold a quantity in quality-inspection stock; in-process (03)
  usually does not. Origins and status codes in `references/inspection-lot-lifecycle.md`.
- **Material master QM view** - the control object that decides whether QM applies at all: it activates the
  **inspection types** (mapping to origins) for a material + plant and switches on QM in procurement, a
  certificate requirement, and batch-status control. No active inspection type = no lot is ever created = the
  goods receipt goes straight to unrestricted. When reasoning about why a lot did or did not appear, check
  this object first.
- **Inspection lot status (the state machine):** **CRTD** created -> **REL** released (characteristics are
  available and results can be recorded) -> **INSP** in process -> usage decision made (status **UD**) ->
  stock postings done. A lot with stock still to post carries **SPRQ** (stock posting required) until the
  quantity leaves quality-inspection stock. A lot cannot be released without a valid inspection plan or a
  reason it needs none.
- **Inspection plan** (QP01/QP02/QP03) - the task list that says what to inspect: operations, each carrying
  **inspection characteristics**, a **sampling procedure**, and links to **catalogs**. Assigned by
  material + plant + usage; must be **released** (status) to be used by a lot.
- **Inspection characteristic** - what you measure or judge. **Quantitative** (a measured value with a
  tolerance range) or **qualitative** (an attribute valued against a coded catalog). **Required** vs
  optional. A reusable one is a **master inspection characteristic (MIC)** (QS21/QS22/QS23), referenced or
  copied into the plan.
- **Results recording** (QE01/QE02, worklist QE51N) - entering the measured values / attribute codes for a
  characteristic and **valuating** it accepted or rejected against the sample. Recording builds the record;
  it does not free stock and does not close the lot.
- **Usage decision (UD)** (QA11/QA12/QA13) - the disposition: a **UD code** from a **selected set** (catalog
  type 3) that carries an **accept (A) or reject (R)** quality score, plus the **stock postings** that move
  the lot quantity out of quality-inspection stock. Making the UD closes the lot for results and triggers
  follow-up (vendor evaluation, quality level, notifications, batch status).
- **Quality-inspection (QI) stock** - stock physically present but held in the inspection state: **on the
  books, invisible to MRP and ATP.** A goods receipt under active QM posts here instead of unrestricted. Only
  the UD stock posting moves it to unrestricted / blocked / scrap / sample / return.
- **Quality notification** (QM01/QM02/QM03) - the record of a quality problem: types **Q1** customer
  complaint, **Q2** complaint against vendor, **Q3** internal defect. Carries defect items, causes, tasks,
  and activities; status runs **OSNO** outstanding -> **NOPR** in process -> **NOCO** completed.
- **Quality info record** - a source-of-supply control. **Procurement** (QI01/QI02/QI03): per material +
  vendor, it **releases or blocks** ordering and goods receipt from that source, sets a release quantity/date
  and a certificate requirement. **Sales/SD**: per material + customer, it can block delivery on quality.
- **Certificate of analysis (CoA)** - a certificate profile (QC01) defines which characteristics print;
  outbound certificates certify a batch/delivery to a customer, inbound certificates from a vendor can be a
  receipt control. Issuing one is a certification, not a printout.
- **Batch linkage** - for batch-managed materials the UD can set the **batch status** (unrestricted vs
  restricted-use) and copy inspection results into the **batch classification** (batch valuation), which
  drives FEFO, grade, and customer-spec selection.

## Vocabulary that bites
- **Usage decision (UD)** - the disposition that both valuates the lot AND posts its stock. It is the one
  committing action almost every QM task ends in; treat it as a posting, not a status flag.
- **Quality-inspection (QI) stock** - present but not available; MRP and ATP ignore it. "Received" does not
  mean "available" until the UD releases it. Same stock status as MM's inspection stock.
- **Inspection origin / inspection type** - the origin (01 GR, 03 in-process, 09 recurring...) is the trigger
  class; the **inspection type** activated in the material master **QM view** is what actually switches
  inspection on for a material + plant. No active inspection type = no lot = the goods receipt goes straight
  to unrestricted with no QM control.
- **Selected set / UD code** - the plant-specific set of valuation codes offered at the UD; each code carries
  an accept (A) or reject (R) score. The wrong code silently mis-scores the vendor and the lot. Because the set
  is plant-specific, the same code can mean different things across plants - do not carry a UD code between plant contexts.
- **Sampling procedure / sample size** - you inspect a **sample**, but the UD dispositions the **whole lot**.
  Accepting on a passing sample releases every unit, including the uninspected ones.
- **Dynamic modification / quality level** - inspection severity (tightened / normal / reduced / **skip**)
  auto-adjusts from quality history, tracked on the **quality level**. At a skip stage no characteristics are
  created and stock can pass to unrestricted with no inspection.
- **Catalog / code group / selected set** - coded valuations: catalog type 3 = usage decisions, defect-type
  catalogs feed notifications. A "selected set" is the plant subset actually offered.
- **Quality info record (procurement)** - the release/block gate on a material + vendor source. If QM in
  procurement is active and there is no released info record, a PO or GR for that source is blocked.
- **Certificate of analysis (CoA)** - an outbound certificate is a quality claim to the customer; a required
  inbound certificate can hold a receipt until it arrives.
- **Batch status (restricted / unrestricted)** - a restricted batch is excluded from unrestricted ATP even
  though it exists; the UD often sets this. Distinct from the QI stock state.
- **Recurring inspection (origin 09)** - stored batches are re-inspected after a shelf-life interval; the
  system creates fresh lots for stock already in the warehouse.

## Operations: read / write / destructive
Classify every operation family by what it does to state and to stock. The tcodes name the action-kind; the
class is the same whether the connector drives the GUI transaction or a BAPI/RFC. The harness maps the
customer's real connector onto these classes. No tool names below - kinds of action.

| Class | SAP QM operation families | Gate | Why |
|---|---|---|---|
| **Read** | display an inspection lot (QA03), results (QE03), a usage decision (QA13); the lot worklist (QA32 in display, QA33); display an inspection plan / MIC (QP03/QS23); a notification (QM03) and its list; a quality info record (QI03); a quality level, a certificate, a batch's status/classification; vendor quality score | always pass | no state change; read the lot state + stock + batch before any write, re-read at execute |
| **Write (reversible)** | create/change an inspection plan or MIC before it drives a lot (QP01/QP02, QS21/QS22); create/change a sampling procedure or dynamic-modification rule; **manually release a lot** (CRTD -> REL) so results can be recorded; record or re-record characteristic results and valuate them **before the UD** (QE01/QE51N); create/change a quality notification and add items/tasks (QM01/QM02) before release/completion | gate one at a time | a draft or a correctable record; no stock moves and the lot is not yet disposed; low blast |
| **Write (committing)** | **record the usage decision (QA11)** = valuate the lot + post its stock out of QI; the **UD stock posting to unrestricted** = frees the quantity to MRP/ATP; **UD to blocked** or **to sample usage**; release a **quality info record** so a source may be ordered/received (QI02); **block / hold a source or restrict a batch** to withhold stock (halts procurement / excludes from ATP, but reversible by release); create a **manual stock-relevant inspection lot** (QA01) that moves stock into QI; **issue/send a certificate of analysis** to a customer; **set a batch to unrestricted** on the strength of the UD; **complete a quality notification** (NOCO) - note this can release the holds it drove, so treat it as more than a status flip | gate + human approve | binds the physical world or money: frees or withholds stock, certifies quality, opens a source, closes a disposition |
| **Destructive / irreversible** | **UD reject -> scrap** the lot quantity (a loss + GL expense); **UD reject -> return to vendor** (reverses the receipt, re-opens commitment, may trigger a vendor complaint/credit); **change a UD after stock is posted** (QA12); **cancel an inspection lot** that already has a UD or posted stock; **lift a quality block / release a blocked source** to push a receipt through; **force a skip** (dynamic modification) so uninspected stock goes to unrestricted; delete/archive results or lots | hard gate + named approver + re-read | permanent trail; destroys or re-routes stock; crosses a quality/compliance boundary; cannot be cleanly undone |

## Reclassification rules (read this)
- **Recording a result is reversible; the usage decision is not.** Re-recording a characteristic before the UD
  is a correctable draft. Once the UD posts, the valuation and the stock movement are on the record.
- **A UD is reversible only while the stock is still there.** Changing a UD (QA12) that moved stock to
  unrestricted can move it back only if the quantity has not been consumed, picked, or shipped. Scrap and
  return are not reversible at all.
- **Withholding is asymmetric from releasing.** Setting a quality-info-record block (holding a source), or
  restricting a batch, only holds stock and is reversible by releasing it - committing, because it halts
  procurement or excludes stock from ATP, but recoverable. **Lifting** a quality block, or setting a batch to
  unrestricted to push stock through, is the committing/destructive direction and belongs to the person who
  set the hold. The mechanical field change is the same; the direction decides the class.
- **A split UD is several actions, gate each path.** A usage decision can send part of the lot to unrestricted,
  part to blocked, part to scrap or return. Classify each path on its own: the unrestricted/blocked parts are
  committing, the scrap/return parts are destructive. Do not gate the whole UD at the lowest risk.
- **Forcing a skip is a master-data change, not a transaction.** Overriding dynamic modification or setting the
  quality level to skip is a config/master change with no counter-document; it silently lets uninspected stock
  reach unrestricted, so it carries a destructive blast radius even though it "just changes a setting".
- **A stock-relevant manual lot is a stock movement.** Creating a lot for a stock-relevant origin (QA01) posts
  the quantity into QI, so it is committing even though it "just creates a lot".
- **A required digital signature is a hard gate, not a field.** In a regulated (GxP) setup, results recording
  and/or the UD may need an electronic signature; the step cannot complete without it, so treat it as a
  blocking precondition on those writes, not an optional edge case.

Universal rules to teach: read the lot status + QI stock + batch status before any write and **re-read at
execute** (another user may have recorded results, posted the UD, or moved the stock); never bypass a required
inspection, never force a skip or lift a quality block to release stock faster; a required characteristic that
is not recorded blocks the UD for a reason; a block/hold means stop.

## Worked example (a GR inspection, end to end)
A PO goods receipt of **1000 EA** of a QM-active material posts to **quality-inspection stock**, and origin-01
lot is created (status CRTD -> REL). MRP/ATP see **0 available**, not 1000. The sampling procedure sets a
**sample of 80 EA**; you record and valuate the characteristics (QE51N) on those 80. All pass, so at the UD
(QA11) you pick an **accept code** and post the disposition: **920 EA to unrestricted** (now visible to
MRP/ATP), **80 EA to sample usage** (consumed by inspection). The vendor score ticks up, the quality level
moves toward reduced inspection, and (batch-managed) the batch is set unrestricted. If instead 12 of the 80
failed, an accept is wrong: a reject code sends the lot to blocked, scrap, or return - and none of the 1000
EA reaches ATP. If you post only 600 to unrestricted and leave 400 undecided, the lot stays **SPRQ** with 400
still in QI.

## Gotchas that bite (the real set - causal chains)
1. **A goods receipt under active QM posts to quality-inspection stock, not unrestricted.** The quantity is on
   the books but invisible to MRP and ATP until the UD releases it; treating the GR quantity as available over-promises.
2. **The usage decision is a stock posting, not a note.** UD accept posts the lot quantity QI -> unrestricted,
   which makes it available to MRP/ATP the instant you save. It also closes the lot for further results.
3. **UD reject -> scrap destroys stock and value irreversibly** and hits a scrap expense. It is a loss, not a
   correction; size it before posting. Ledger effect is MM/FI - see `sap-mm`.
4. **UD reject -> return to vendor reverses the receipt.** It re-opens the PO commitment, can trigger a vendor
   credit and a Q2 complaint, and is its own posting, not a move to blocked.
5. **Changing a UD (QA12) is a new posting, not an undo.** The original UD and its stock movement stay in the
   trail; you can only move stock back if it is still physically there; consumed, scrapped, or shipped
   quantity cannot be restored.
6. **The UD updates the vendor evaluation and the quality level.** The accept/reject score feeds vendor
   scoring and the dynamic-modification history, so a wrong UD code silently skews future sampling severity
   (tightened / reduced) and the vendor's quality rating.
7. **Recording results completes nothing.** The lot stays open and the stock stays in QI until the UD.
   "The inspection passed" does not release the stock; only the usage decision does.
8. **A required characteristic that is not recorded blocks the UD** (or forces a reject). Skipping a required
   characteristic prevents closing the lot cleanly; do not valuate around it.
9. **You inspect a sample but dispose the whole lot.** Accepting on a passing sample releases every unit in the
   lot, including the ones never measured. A sample failure can reject stock that was individually fine.
10. **Dynamic modification can skip inspection entirely.** After a good history the stage may be **skip**: no
    characteristics are created, and stock can pass straight to unrestricted with no results recorded. Assuming
    every receipt is inspected is wrong.
11. **No active inspection type in the material master QM view = no QM control at all.** The goods receipt goes
    straight to unrestricted with no lot; activating or deactivating an inspection type changes GR behavior for
    every future receipt of that material + plant. Activating QM mid-stream is a go-live surprise: open POs and
    scheduled receipts that used to land in unrestricted will suddenly create inspection lots and hold stock in QI.
12. **QM in procurement active + no released quality info record = the PO or GR is blocked.** A missing or
    blocked info record stops procurement for that material + vendor; releasing it is a committing sourcing control.
13. **The UD can be made while the stock posting is still open (SPRQ).** A partial or deferred stock posting
    leaves the quantity in limbo - the lot shows "stock posting required" and ATP is not updated until the
    posting completes. A UD alone does not guarantee the stock moved.
14. **Issuing a certificate of analysis certifies quality to the customer.** If a characteristic failed or the
    batch classification is wrong, the CoA is a false claim; the certificate profile controls what is printed,
    so a wrong profile can omit a failing characteristic.
15. **The UD can set the batch status.** For batch-managed materials, accept sets the batch to unrestricted;
    reject can leave it restricted or blocked. A restricted batch is excluded from unrestricted ATP even though
    it exists on hand.
16. **Inspection results copied into the batch classification drive downstream selection.** A wrong measured
    value written to the batch class mis-grades the batch (shelf-life, potency, grade), so FEFO and
    customer-spec picking select the wrong stock later.
17. **One goods receipt can create several inspection lots** (partial GRs, multiple materials/batches).
    Disposing one lot does not free another's stock; check every open lot for the receipt.
18. **Blocking a source or lifting a quality block is high-blast.** Blocking a quality info record halts all
    procurement for that material + vendor; lifting a quality block to push a receipt through is a compliance
    violation, not a shortcut.
19. **Recurring inspection (origin 09) re-tests stored stock.** Batches past a shelf-life interval get new
    lots; ignoring the open recurring lot ships stock that is due for re-inspection or already expired.
20. **In-process inspection (origin 03) does not post stock the way a GR lot does.** Its UD confirms production
    quality but usually moves no inventory; do not expect a QI-to-unrestricted posting from an in-process lot.
21. **A regulated setup may require a digital signature at results recording or the UD.** You cannot complete
    the step without it; treat the signature as a hard audit gate, not an optional field.
22. **Completing a quality notification (NOCO) closes the disposition.** Outstanding tasks and activities
    (8D / CAPA) should be done first; completing early closes the record and can release the holds it drove.

(Deep detail: `references/inspection-lot-lifecycle.md`, `references/notifications-and-info-records.md`.)

## Edge states & special cases
Each breaks naive "the inspection passed, so the stock is good and available" logic - the key rule inline,
full behavior in the references.
- **Sampling vs the lot** - a passing sample releases the whole lot; an accept is a decision about every unit,
  not just the measured ones. Detail in `references/inspection-lot-lifecycle.md`.
- **Dynamic modification / skip lots** - severity moves with quality history; a skip stage means no inspection
  and auto-release. The quality level carries the current stage per material + plant.
- **Recurring inspection (09)** - stored batches are re-inspected on an interval; open recurring lots gate
  stock that is already in the warehouse.
- **In-process (03) vs stock-relevant (01/08)** - in-process lots confirm production quality without an
  inventory posting; only stock-relevant lots hold and move QI stock.
- **Batch linkage** - the UD sets batch status and can write results into the batch classification; a
  restricted batch is excluded from ATP, and a mis-written class value mis-selects stock later. See `references/notifications-and-info-records.md`.
- **Quality info record + certificate requirement** - QM in procurement can require a released info record and
  an inbound certificate before a receipt is allowed; source inspection can even create a lot at the vendor.
- **Digital signature (regulated)** - results recording and/or the UD may require an electronic signature; the
  step cannot complete without it.

## Recovery patterns (can it be undone, and what cannot)

| Situation | Recovery path |
|---|---|
| A lot is stuck in CRTD and will not release | no valid inspection plan was found: assign/release a plan for the material + plant, correct the inspection type, or use a no-plan inspection type (89) - then release |
| A lot is UD-made but stuck in SPRQ (stock still in QI) | complete the deferred/partial stock posting for the remaining quantity; ATP does not update until the QI quantity is fully posted out - the UD alone did not move it |
| A characteristic was recorded wrong, before the UD | re-record and re-valuate it (QE02) - a correctable draft while the lot is pre-UD |
| A UD was made with the wrong code, stock still in place | change the UD (QA12); it posts a new movement and moves stock back only if it is still there |
| UD released stock to unrestricted that is partly picked/consumed | QA12 can move back only the quantity still in unrestricted (released 1000, 400 already picked -> only 600 returns to QI); the picked/consumed 400 is gone |
| UD released stock to unrestricted that has already been fully consumed/shipped | cannot restore it; correct forward (new inspection / notification), not by reversing the UD |
| UD scrapped the lot | not reversible; the stock and value are gone (a new GR/adjustment is a separate posting) |
| UD returned the lot to the vendor | not a clean undo; it reversed the receipt and re-opened commitment - handle as a fresh receipt/complaint |
| A stock-relevant inspection lot was created in error | cancel it only if no UD/stock posting yet; once stock posted, reverse the posting first, then cancel |
| A certificate of analysis was already sent to the customer | cannot unsend; issue a corrected certificate and notify - a recall, not an edit |
| A quality notification was completed too early (NOCO) | reopen/reset the notification status if allowed; the completion and any released holds are logged |

Reversal is almost always a **new posting**, not an undo: the original UD, the original stock movement, and
the certificate all stay in the trail. What is truly gone is any quantity already scrapped, returned,
consumed, or shipped.

## Guardrails
- Read the inspection lot status + QI stock + batch status + quality-info-record state before acting; re-read
  at execute (results, the UD, or the stock may have changed).
- **QI stock state and batch status are two independent availability gates.** Stock is only freely usable when
  both are clear: a batch can be past its UD and out of QI yet still be **restricted**, so it stays out of
  unrestricted ATP. Check both before treating stock as available - a UD check alone over-promises.
- Never bypass a required inspection, force a skip, or lift a quality block to release stock faster; a
  required characteristic that is not recorded blocks the UD for a reason.
- Treat the usage decision as a stock posting: know whether it frees ATP (unrestricted), withholds it
  (blocked), or destroys it (scrap/return) before you post, and size a scrap or return - it is a loss or a
  commitment change, not a correction.
- Issuing a certificate of analysis is a certification to the customer; confirm the characteristics passed and
  the batch data is right first.
- For anything in the destructive row (scrap, return, UD change after posting, source block/unblock, batch
  restriction, forced skip): named approver, re-read, and log the reason.

## References (load on demand)
- `references/inspection-lot-lifecycle.md` - inspection origins and status codes, the results-recording ->
  usage-decision -> stock-posting flow, UD dispositions and where each posts, sampling, dynamic modification
  and the quality level.
- `references/notifications-and-info-records.md` - quality notifications (types, items, tasks, statuses, 8D),
  quality info records (procurement and SD), certificates of analysis (inbound/outbound), source inspection,
  and batch status/classification linkage.
