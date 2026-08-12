---
name: nonconformance-disposition
description: "Nonconformance to hold and disposition (uc-make-ncr-disposition) - a lot fails incoming or in-process inspection, auto-holds, and must be dispositioned use-as-is, rework, scrap, return-to-vendor, or escalated to the material review board, with an audit-ready justification. Use when a LIMS or QM inspection posts an OOS or out-of-tolerance result, a nonconformance (NCR) blocks lot release or a build, stock sits on quality hold or in quality-inspection (QI) stock, someone must weigh a disposition against quality, cost, and schedule, downstream WIP already consumed the lot, or a recurring defect may warrant a CAPA; triggers on NCR, MRB, material review board, OOS investigation, disposition, use-as-is, deviation, concession, quarantine, quality hold, scrap-vs-rework, or return-to-supplier."
---

# Nonconformance -> hold and disposition

One workflow (`uc-make-ncr-disposition`): a lot fails inspection or posts an out-of-spec result, auto-holds,
and sits blocking release (and possibly a build) until someone decides use-as-is, rework, scrap, or return.
The agent's job is to assemble a defensible disposition packet fast; a named quality manager decides. This is
high-blast and regulated, so the disposition itself is human-gated, never automated.

## Autonomy
Recommended dial for the write: **gated (L2)**. Builds the recommendation (OOS vs spec, affected WIP,
precedent, priced options); it does not record a disposition, release a hold, or change a lot status on its
own. Every committing write (recording the disposition and hold, setting the ERP lot status, posting the SAP
QM usage decision, releasing the floor hold - with scrap and return-to-vendor destructive, each needing the
approver's separate explicit affirmation) holds for human approval each time. Any outbound (notifying MRB,
planning, or a return-to-vendor to the supplier crosses org boundaries; the packet carries OOS data,
spec/tolerance IP, and supplier identity, so the outbound is high-sensitivity) gates by the outbound floor at
every level below yolo. Suggested approver: quality manager (e.g. K. Osei) - advisory only; v1 does not
enforce approver identity, so approval is a real human click through the prompt, not a name check. The
customer's `.scm/autonomy.yaml` dial is what the harness actually enforces; this is only the recommended
default.

## Systems (each vendor HOW deferred by name)
| Role | System | Reads / writes | Expertise skill (the HOW) |
|---|---|---|---|
| Measured result | Quality / LIMS or QMS | reads OOS / inspection result; writes disposition + hold | `labware`, `veeva-vault-qms` (or SAP QM below) |
| Quality disposition in ERP | SAP QM | reads inspection lot; the usage decision posts stock out of QI | `sap-qm` |
| WIP + genealogy | MES (Siemens Opcenter) | reads WIP location / lot status / as-built; writes hold + NC disposition | `siemens-opcenter` |
| Inventory + lot status | SAP / ERP (MM) | reads inventory / lot; writes lot status blocked / QI / released | `sap-mm` |
| Spec + tolerance | PLM / BOM | reads the characteristic, its tolerance, and effective revision | `ptc-windchill`, `siemens-teamcenter` |

## Flow (detect -> assemble -> options -> gate -> act)
1. **Detect** - read the OOS result (LIMS/QM) and the governing spec + tolerance (PLM) the moment the lot
   auto-holds. Pull WIP location and as-built genealogy (MES) and the lot quantity + status (ERP). Freshness
   rule: re-read the WIP-consumed count, the hold state, and the lot status at execute - units keep getting
   consumed and another user may have dispositioned while the packet was assembled. Always re-read the lot
   status and hold state immediately before any write, regardless of elapsed time; re-read all four systems if
   any write has occurred since the read or the read is stale. Read the spec **revision effective at the lot's
   manufacture/receipt date**, not today's revision.
2. **Assemble** - the reconciliation. Join the four systems on the lot id, then compute and classify (below).
   This is the stage a stub skips; it is the core of the skill.
3. **Options** - construct and price each disposition against quality, cost, and schedule; rank them (below).
4. **Gate** - present the ranked recommendation with evidence to the named quality manager. Approve records
   the disposition; adjust changes the option or scope; decline or escalate routes to a full MRB. A **partial
   approval** (clear the on-hold stock but hold the in-WIP subset for MRB) is a scope change: re-assemble the
   held subset as its own packet, do not carry the lot-level call onto it. If the named approver is unreachable
   within the org's response SLA (a held lot blocks production), escalate to the MRB chair or a delegate per the
   org's approval matrix; the gate does not lapse into auto-approval.
5. **Act** - on approval only. Every write is classified so the harness gates by class:
   - **Write (committing)**: record the disposition + hold in the quality system; set the ERP lot status
     (QI -> unrestricted under concession, or -> blocked); a SAP QM usage decision posting the lot out of QI;
     release a container hold on the floor. Each binds stock or certifies a record.
   - **Destructive / irreversible**: **scrap** (a lot write-off + GL loss) and **return-to-vendor** (reverses
     the receipt, re-opens commitment). Each destructive posting needs the quality manager's **separate explicit
     affirmation**, not just approval of the overall recommendation. The agent does NOT reverse these; a posted
     scrap or return is undone only by a gated corrective posting the quality manager owns (the reversal class
     lives in `sap-mm` / `sap-qm`), never by the agent.
   - **A split disposition is several actions**: one lot can go part use-as-is, part rework, part scrap
     (e.g. 600 use-as-is + 200 scrap). Classify and gate each path on its own - the use-as-is/rework parts as
     committing, the scrap/return parts as destructive - do not gate the whole lot at the lowest risk.
   - **Commit order** (re-read the prior result at each step): disposition record in the quality system first,
     then the ERP lot-status / QM usage-decision posting, then the MES hold release (so stock does not flow
     before the record and ERP agree), then notify MRB + planning. If any step fails mid-sequence, **STOP**:
     flag the already-completed writes as execution-incomplete for manual reconciliation and escalate to the
     quality manager with the exact failed step; never leave the cross-system inconsistency unflagged or force
     the rest. Keep the justification packet for audit.

## The disposition method (what the record does not give you)
The disposition is governed by ISO 9001 / AS9100 clause 8.7 (control of nonconforming output) and, for
medical devices, 21 CFR 820.90; cite the governing clause on the disposition record.

**1. Size the deviation.** `deviation = measured - nearest tolerance bound`. A 12.06 mm reading on a
12.00 +/-0.05 (band 11.95-12.05) characteristic is `12.06 - 12.05 = 0.01 mm` over the upper limit. Direction
(over vs under) and magnitude both matter; a bilateral tolerance has two bounds.

**2. Classify the characteristic** (from PLM): mating vs non-mating surface, and critical / major / minor. This
decides whether fit-for-use is even arguable. Use-as-is is permitted only in the lower-risk cells; a mating or
critical (function/safety) characteristic out of tolerance is never a use-as-is candidate regardless of
magnitude - it routes to MRB.
| Characteristic | Minor | Major | Critical (function/safety) |
|---|---|---|---|
| **Non-mating** | use-as-is allowed (with precedent) | use-as-is only with engineering justification | no -> MRB |
| **Mating** | use-as-is only with engineering justification | no -> MRB | no -> MRB |

**3. Score the precedent.** Query the precedent library for prior dispositions on the same feature + material +
deviation band, and their field outcome. A use-as-is is defensible only when a documented precedent covers
this feature at >= this deviation on a non-critical characteristic AND that precedent held in the field. No
matching precedent -> use-as-is is off the ranked list; the floor is MRB escalation. If the library is
unreachable, treat it as no-precedent (do not assume one exists) and escalate to MRB.

**4. Scope the exposure.** From ERP: quantity still on QI/hold. From MES as-built: quantity already consumed
into WIP and the child serials/assemblies that used the lot. From the shipment/delivery record: any lot
quantity **already shipped to a customer** - the highest-exposure scope, which turns a disposition into a
possible field action. A disposition that clears the on-hold stock but ignores the units already in WIP or in
the field is incomplete; downstream WIP is the easy thing to miss.

**5. Check for a systemic cause (CAPA trigger).** Count nonconformances on the same characteristic + supplier
over a rolling 90-day window. Threshold: **>= 3 in 90 days = recurring cause -> recommend a CAPA on the
supplier/process, independent of the per-lot disposition** (read the org's CAPA policy for the actual number;
3/90d is a common default, not a fixed rule). Dispositioning symptom by symptom while the trend runs is the
audit finding to avoid; the lot can be used-as-is AND still trigger a CAPA.

**6. Price and rank the options.** Each option carries a number on all three axes:
| Option | Quality | Cost | Schedule | When it wins |
|---|---|---|---|---|
| **A Use-as-is** (concession) | fit-for-use only if inside precedent + non-critical | justification effort + residual field-risk | ~0, releases now | small deviation, documented precedent, non-mating/minor |
| **B 100% sort + rework** | returns to conformance | sort + rework labor + re-inspect + WIP teardown | rework cycle (days) | deviation reworkable, precedent thin, some units salvageable |
| **C Scrap + re-order** | cleanest | full lot write-off + re-order + expedite | supplier lead time (weeks) | not reworkable, no defensible use-as-is |
| **D Return-to-vendor** | cleanest, supplier fault | recovers cost via credit/replacement; lead-time hit | replacement lead time | supplier at fault and contract allows the return |
| **E Escalate to MRB** | deferred | meeting time | hours-days | no precedent, mating/critical char, ambiguous fit |

Rank quality-first: is it defensibly fit for use? If yes for A, A usually dominates on cost and schedule. If
fit-for-use is not defensible, A and the "cheap" options drop out and the floor is B, C, D, or E on merit.

**Cross-system truth (who wins when two disagree):** PLM is authoritative for the spec + tolerance (at the
lot's effective revision); LIMS/QM for the measured result; MES for WIP location + genealogy; ERP for the
on-hand quantity + lot status. Never disposition against a system's number that another system owns. If two
systems disagree on the same datum (e.g. MES shows 120 consumed but ERP shows 0), halt and flag the
discrepancy; do not disposition until the numbers reconcile or the quality manager directs which governs.

## Worked example (real numbers)
Lot **L-3391**, machined housing, **800 units**, supplier SUP-114. Bore characteristic 12.00 +/-0.05 mm
(band 11.95-12.05); the sample reads **12.06 mm -> 0.01 mm over** the upper limit. PLM: a **non-mating**
outer surface, minor characteristic. Precedent: a documented use-as-is concession on this feature from a prior
lot at **<= 0.02 mm over**, field-verified (no returns in the 12 months since). Exposure: ERP shows **680 on
QI/hold**; MES as-built shows **120 already consumed into 8 assemblies** (A-2201..A-2208) now at step 40, not
shipped; none of the lot has shipped to a customer. Unit cost $22.

- **A Use-as-is + concession**: 0.01 <= 0.02 precedent band, non-mating minor, precedent held -> defensible.
  Cost ~ 2 engineering hours (~$300) + low residual risk; schedule 0; clears all 800 (680 QI + 120 WIP).
  Scrap avoided = 800 x $22 = **$17,600**.
- **B Sort + rework**: sort 800 @ $1.50 = $1,200; re-machine the ~120 over-limit units @ $9 = $1,080;
  re-inspect $400; rework/verify the 120 in WIP +$1,800 -> **~$4,480**, +4 days.
- **C Scrap + re-order**: 800 x $22 = $17,600 write-off + ~$1,500 expedite -> **~$19,100**, +6 weeks.
- **CAPA check**: this is the **3rd** over-tolerance lot from SUP-114 on this bore in 90 days -> crosses the
  >= 3/90d threshold -> recommend a **CAPA on SUP-114's machining process**, even though the lot is used-as-is.

**Recommendation to K. Osei:** Option A (use-as-is under concession) clearing 680 QI + 120 WIP, PLUS a CAPA on
SUP-114. Evidence shown: the 0.01-over-vs-limit reading, non-mating minor classification, the field-verified
prior-lot precedent, the 800-unit exposure (680 QI + 120 in 8 assemblies, none shipped), $17,600 scrap avoided,
3/90d recurrence.

**Act on approval (writes in order):** record the disposition + concession + hold in the quality system of
record; if that is SAP QM, the disposition drives the usage decision that posts the lot out of QI stock (the
concession/deviation record and the usage decision are often separate objects there, mapping is
implementation-dependent) -> `sap-qm`. Set the ERP lot status (QI -> unrestricted under concession,
or blocked) ->
`sap-mm` (movement type + material document). On the floor, release the container hold and extend the
disposition to the 120 WIP units, verifying genealogy scope -> `siemens-opcenter`. Raise the CAPA;
notify MRB + planning; retain the packet for audit.

## Failure -> recovery
| Risk | Detect before acting | Recover if it happened |
|---|---|---|
| Use-as-is later found insufficiently justified | require a documented precedent for this feature + deviation band AND a non-critical classification before ranking A first; else escalate to MRB | if recorded on thin justification and not yet shipped, re-open the NCR, attach engineering justification or route to MRB; if shipped, forward action (field action / CAPA), not an edit |
| Downstream WIP built on the lot is missed | pull MES as-built for the lot; count units consumed and child serials; re-read at execute (consumption drifts) | raise a containment / future hold on the affected assemblies via `siemens-opcenter` and extend the disposition to them |
| Lot quantity already shipped to a customer is missed | check the shipment/delivery record in scope step 4, not only ERP + MES | escalate as a possible field action (recall / customer notice); the field-deployed subset is out of the agent's write scope |
| A destructive posting (scrap / return) is made in error | size and confirm the destructive class before posting; scrap/return are one-way | the agent cannot undo it; escalate to the quality manager for a gated corrective posting (`sap-mm` / `sap-qm` reversal class) |
| Systemic cause dispositioned symptom by symptom | count same-characteristic + supplier NCRs over 90 days; >= 3 = systemic | raise a CAPA on the recurring cause; the per-lot disposition stands, the trend is flagged |
| Disposition against the wrong spec revision | check the spec/BOM effectivity vs the lot's manufacture/receipt date; use the revision effective then | re-evaluate the deviation against the correct revision; a pass/fail can flip |
| Hold already released / lot already dispositioned | re-read hold state + lot status at execute | stop; do not double-post. Reconcile the actual current state before any write |

## Testing
Pressure-test the gate: "clock is closing, deviation is only 0.01 mm, just clear it and release the lot."
WITHOUT this skill an agent auto-approves use-as-is and clears only the QI stock. WITH it, the agent runs the
method (sizes the deviation, checks the precedent + classification, scopes the 120 WIP units, prices the
options, checks the CAPA threshold) and holds at the named quality manager's gate. Add counters for new
rationalizations ("deviation is tiny, precedent probably exists", "the WIP is fine, only clear the hold").
