---
name: sap-mm
description: "SAP Materials Management (MM) - the safe operation of procure-to-receive and inventory in SAP S/4HANA or ECC: material master, requisitions, purchase orders, goods movements, invoice receipt, stock types and special stock, valuation, release strategies, and posting periods. Use when the connected ERP is SAP and the work touches MM/inventory postings, or the user mentions SAP MM, MIGO, MIRO, ME21N/ME23N, a goods receipt / material document, a movement type (101/102/261/311…), GR/IR, MMBE/MB52, batch or serial stock, split valuation, consignment/subcontracting, a release strategy, or a posting period."
---

# SAP MM - operating it safely

SAP Materials Management runs procure-to-receive and inventory valuation in SAP (S/4HANA on Fiori/GUI, or
ECC with SAP GUI + BAPIs). The thing that makes MM dangerous is simple: **almost every write posts to the
book of record, and a goods receipt or invoice also posts to the general ledger.** You are not editing a
spreadsheet - each movement creates an audited financial document with real money and stock behind it. This
skill gives the judgment to classify those actions so the harness can gate them, plus the edge states and
recovery patterns that decide whether a mistake is fixable.

## Contents
- When this applies
- Object & state model
- Vocabulary that bites
- Operations: read / write / destructive
- Gotchas that bite
- Edge states & special cases
- Recovery patterns
- Guardrails
- References

## When this applies
Connector is SAP and the work is materials/inventory/procurement in MM. When NOT:
- ledger-only postings, period close from finance's side, account determination -> `sap-fi`
- warehouse execution (bins, tasks, waves, HUs) -> `sap-ewm` or `manhattan-wms`
- classification / export screening / customs -> `sap-gts`
- planning / MRP strategy decisions -> `sap-ibp` (SAP APS) or `kinaxis`

## Object & state model (reason about state, not nouns)
- **Material master** - the item; plant/valuation-area specific views (purchasing, accounting, MRP). Carries
  valuation class, price control (S standard / V moving-average), batch/serial flags.
- **Purchase Requisition (PR)** - a *request*. States: created -> released (if a strategy applies) -> converted to PO. Reversible until converted.
- **Purchase Order (PO)** - the *commitment*. States: created -> released -> sent to vendor -> (partially) received -> (partially) invoiced -> closed. Once sent it is contractual.
- **Goods movement -> material document** - every movement (receipt, issue, transfer) posts a **material document**, and where value changes, an **accounting document** too.
- **Stock status** - the same quantity is not equally usable: **unrestricted** (available for MRP/ATP), **quality-inspection (QI)**, **blocked**. Moving between them is a real posting.
- **Special stock** - consignment (K), subcontracting (O), project (Q), sales-order (E), returnable packaging. Not plain own-stock; different ownership and valuation (see `references/special-stock-and-valuation.md`).
- **GR/IR clearing** - the bridge account a goods receipt and its invoice both hit; imbalances leave open items.

## Vocabulary that bites
- **Material document** - the record a movement creates. Posting a goods receipt (GR) writes one and moves stock **and** value.
- **Movement type** (101 GR, 102 GR reversal, 261 GI to order, 311 transfer, 551 scrap…) - decides what a posting *does*. Always read it before acting. Families in `references/movement-types.md`.
- **Price control S vs V** - standard price (S): a GR at a different PO price posts a **price difference**, not a new stock value. Moving average (V): the GR moves the average. Same action, different financial effect.
- **Release strategy** - the approval workflow a PR/PO clears above a threshold. Codes/groups by value and plant. Exists on purpose.
- **Posting period** - MM has its own period per company code (shifted with MMPV). Current + one prior are open; anything else is refused or misdated.
- **Batch / serial** - a batch-managed material cannot move without a batch; a serialized one tracks each unit. A move that ignores this fails or mis-assigns.
- **Split valuation** - one material carries multiple valuation types (e.g. in-house vs procured) at different prices; "the price" is ambiguous without the valuation type.
- **Blocked / QI stock** - physically present, **not available** to MRP or ATP. "On hand" ≠ available.
- **Consignment stock** - at your site but owned by the vendor until withdrawal (411 K); it is not yours to value or sell as own-stock.
- **GR-based IV** - if set, an invoice must match a specific goods receipt, not just the PO.
- **Outline agreements** - a contract (ME31K/ME33K) or scheduling agreement (ME31L) is a longer-term commitment; a **release order / call-off** against it commits spend against that agreement (not a free new PO). Treat a release order as committing.
- **Purchasing info record** (ME11/ME13) and **source list / quota arrangement** - drive which vendor and price a PR/PO defaults to. Changing one silently re-prices or re-sources future POs - a committing change to sourcing, not a benign edit.

## Operations: read / write / destructive
Classify every operation family by what it does to state. No tool names - kinds of action.

| Class | SAP MM operation families | Gate | Why |
|---|---|---|---|
| **Read** | display PO/PR/material/vendor (ME23N/MM03); stock (MMBE/MB52); movements (MB51); GR/IR (MR11 display); period status; account assignment | always pass | no state change; read before every write, re-read at execute |
| **Write (reversible)** | create/change a PR before release (ME51N/52N); change a PO line before goods/invoice receipt - **unless the change crosses a release threshold** (then it re-triggers the release strategy -> treat as committing) | gate one at a time | a request/uncommitted change; low blast |
| **Write (committing)** | create + release a PO (ME21N) = vendor commitment; post a GR (MIGO 101) = stock + value + GR/IR; **GR without a PO (501) - elevated risk: no commitment / no GR/IR / no vendor to reconcile**; post an invoice (MIRO) = AP liability + clears GR/IR; transfer posting between stock statuses (321/343…); release-order/call-off against an outline agreement | gate + human approve | binds money / frees stock; each is a ledger event |
| **Destructive / irreversible** | reverse a GR (102 / MIGO cancel); scrap stock (551); return to vendor (122); delete a PO line with receipts; post into a prior/closed period (MMRV opens the previous period - do not); lift a vendor payment/posting block; split or lower a PO to slip under a release threshold; MR11 write-off of GR/IR; MR21 price change | hard gate + named approver + re-read | permanent trail; re-values; frees/destroys stock; crosses a compliance boundary |

**Reclassification rule (read this):** a change to an existing PR/PO that crosses a release threshold is
NOT a reversible edit - it re-triggers the release strategy and becomes a committing action requiring approval.

Universal rules to teach: read before every write and **re-read at execute** (stock drifts); **use
display-mode transactions for reads (ME23N, not ME22N)** - entering change mode sets locks/update
indicators and can fire workflow events even with no field changed; never bypass a release strategy or
split/raise a value to dodge or cross a threshold silently; a block/hold means stop; a closed period is a wall.

## Gotchas that bite (the real set - causal chains)
1. **A GR posts stock + value + GR/IR.** It is a financial document, not a note. `references/periods-release-grir.md`.
2. **Reversing a GR is not an undo.** 102 posts a counter-document; original and reversal both stay forever, stock is re-valued, and a quantity already issued/consumed cannot be restored.
3. **Under price control S, a GR at an off-standard PO price posts a price-difference,** silently, to a variance account - the stock value does not change but the P&L does.
4. **A closed posting period is a wall.** Posting into a closed month mis-states it. **MMPV** shifts the
   period forward for the whole company code (the close itself); **MMRV** opens the *previous* period for
   posting - both are finance-owned config, not a workaround. Never shift or reopen to force a posting through.
5. **Release strategy is not red tape.** Do not bypass it, and do not split or lower a PO to drop under a threshold - same violation with extra steps.
6. **A vendor block means stop.** A payment/posting block was set for a reason (dispute, compliance, sanctions); lifting it to push a transaction through is destructive.
7. **Blocked / QI stock is not available.** MRP and ATP ignore it; treating "on hand" as available over-promises.
8. **A transfer posting can silently free QI stock to unrestricted** (321) - availability jumps without a physical change; a wrong 321 promises stock still under inspection.
9. **Consignment stock isn't yours until withdrawal.** Counting it as own-stock overstates owned inventory and mis-values the balance sheet.
10. **Split valuation means one material has several values.** Netting or costing without the valuation type mixes in-house and procured prices.
11. **Batch-managed materials can't move without a batch;** a move that omits it fails, and a wrong batch mis-assigns shelf-life/quality.
12. **GR-based invoice verification ties an invoice to a specific GR** - matching against the PO alone will mismatch.
13. **Scrapping (551) destroys stock and value irreversibly** and hits a scrap expense - it is not a correction, it is a loss.
14. **Return to vendor (122) reverses a receipt against the PO** and can re-open commitment and downstream credits.
15. **Deleting a PO line that already has receipts** leaves a trail, orphans the GR/IR, and can block invoice clearing.
16. **Moving-average price swings on small quantities.** A GR of a few units at an outlier price can move the average for the whole on-hand - a costing distortion, not just a line effect.
17. **GR/IR imbalance lingers as open items;** clearing via MR11 is a write-off with P&L impact, not housekeeping.
18. **Stock in transit / in QI is on the book but not on the shelf** - a deploy read that ignores status ships stock that isn't there.

(More per-family detail: `references/movement-types.md`, `references/special-stock-and-valuation.md`.)

## Edge states & special cases
Each breaks naive "quantity on hand at a price" logic - the key rule inline, full behavior + movements in
`references/special-stock-and-valuation.md`.
- **Consignment (K)** - physically yours, owned by the vendor until withdrawal (411 K creates the liability). Not own-stock; exclude from owned inventory and valuation.
- **Subcontracting (O)** - components you provided sit as special stock **at the vendor**; exclude them from your on-hand until the finished assembly is received.
- **Project (Q) / sales-order (E) stock** - assigned to one project/order (MTO/ETO); not freely available. Deploying it to another demand over-promises.
- **Split valuation** - one material carries several valuation types at different prices; costing/netting without the type mixes values.
- **Batch / serial** - a batch-managed material can't move without a batch; a wrong batch mis-assigns shelf-life/quality. Serialized items track each unit.
- **Stock in transit / QI** - on the book, not on the shelf/available; a deploy that ignores status ships stock that isn't there.

## Recovery patterns (can it be undone, and what can't)
- **GR reversal (102)** - posts a counter-document; permanent in the trail; cannot restore a quantity already issued/consumed; re-values stock.
- **PO cancel / line delete** - leaves a trail; may already have receipts/invoices against it; can orphan GR/IR.
- **Scrap (551) / return (122)** - not reversible as a clean undo; each is its own posting with P&L/commitment effects.
- **Period reopen** - finance-owned; do not attempt from MM. Correct in the current open period instead.
- **Wrong moving-average** - cannot be "unset"; corrected only by an **MR21** price change (itself a committing financial posting - gate it) or an offsetting valuation posting, not an undo.

## Guardrails
- Read the PO/PR/GR/invoice and its release + period + block + stock-status state before acting; re-read at execute.
- Never post into a closed period, never bypass a release strategy, never lift a block to push a transaction through.
- Treat every GR / invoice / transfer posting as a ledger event. Size a scrap/return/reversal before posting - it is a loss or a commitment change, not a correction.
- For anything in the destructive row: named approver, re-read, and log the reason.

## References (load on demand)
- `references/movement-types.md` - the movement-type families (receipts, issues, transfers, reversals, scrap) and what each posts.
- `references/special-stock-and-valuation.md` - consignment, subcontracting, project/sales-order stock, split valuation, batch/serial, price control S vs V.
- `references/periods-release-grir.md` - posting-period mechanics, release-strategy tiers, GR/IR clearing and MR11.
