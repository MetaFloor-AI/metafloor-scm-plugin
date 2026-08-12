# SAP MM movement types — what each posts

The movement type is the single most important field on a goods movement: it decides which stock, which
direction, and what accounting posts. Read it before acting. This lists the families that matter for
gating; the "+ / -" is stock effect, and "GL" flags a general-ledger posting.

## Contents
- Receipts (into stock)
- Issues (out of stock)
- Transfer postings (status/location, usually no value change)
- Reversals
- Scrap / loss
- Special-stock indicators

## Receipts (into stock) — committing, GL
- **101** — GR for a PO or production order. + unrestricted (or QI/blocked per setup). Posts stock + value + GR/IR. The everyday receipt.
- **103** — GR into **blocked** stock (GR blocked), then **105** releases to unrestricted. Two-step receipt; 103 alone does not make stock available.
- **501** — receipt **without** a PO. + stock with no GR/IR link. **Higher-risk than 101**: no PO
  commitment to match, no GR/IR, no vendor reference — nothing downstream reconciles it. Flag for extra scrutiny.
- **511** — receipt of free goods (no invoice expected).

## Issues (out of stock) — committing/destructive, GL
- **261** — goods issue to an order (consumes stock into a production/maintenance order). − stock; posts consumption.
- **201 / 221 / 241** — issue to cost center / project / asset. − stock; expense posting.
- **601** — goods issue for a delivery (outbound to customer). − stock; COGS.

## Transfer postings — usually no value change, but can free stock
- **311** — plant/storage-location transfer, stock-to-stock. Location changes, availability may change.
- **309** — material-to-material transfer.
- **321** — **QI -> unrestricted**. No physical change, but availability jumps (stock leaves inspection). A wrong 321 promises stock still under inspection.
- **343** — **blocked -> unrestricted**. Frees blocked stock; same hazard as 321.
- **344** — unrestricted -> blocked. Removes from availability.

## Reversals — destructive (counter-document, permanent)
- **102** — reversal of 101 (GR cancel). Posts a counter-document; both stay in the trail; re-values; cannot restore consumed qty.
- **262** — reversal of 261 (GI cancel).
- **106 / 122** — **122** = return delivery to vendor against the PO; reverses a receipt and can re-open commitment + downstream credit.

## Scrap / loss — destructive, GL
- **551** — scrapping from unrestricted (− stock, scrap expense). A loss, not a correction.
- **553 / 555** — scrapping from QI / blocked.

## Special-stock indicator (suffix on the movement)
Movements carry a special-stock indicator that changes ownership/valuation:
- **K** — consignment (vendor-owned until withdrawal; **411 K** = transfer consignment to own stock).
- **O** — subcontracting (components provided to the vendor).
- **E** — sales-order stock; **Q** — project stock.
See `special-stock-and-valuation.md` for how these value and when they become yours.

Gating note: receipts/issues/scrap = committing or destructive (GL). Transfer postings look benign but
321/343 change availability — treat as committing when they free stock into ATP.
