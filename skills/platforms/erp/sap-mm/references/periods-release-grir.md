# SAP MM — posting periods, release strategy, GR/IR

The three control mechanisms that decide whether a write is allowed, who must approve it, and how it clears.
Read when a workflow posts (period), commits spend (release), or resolves an invoice (GR/IR).

## Contents
- Posting periods (MMPV) — the wall
- Release strategy — the approval gate
- GR/IR clearing — how a receipt and its invoice reconcile

## Posting periods (MMPV) — the wall
- MM keeps its own posting period per company code. **MMPV** shifts the period forward (the actual close);
  **MMRV** controls whether the **previous** period stays open for postings. Normally the current and (via
  MMRV) one previous period are open; everything else is closed. Do not confuse the two: MMPV closes/advances,
  MMRV re-opens the prior period — both are finance-owned config, not an agent workaround.
- Posting into a closed period is **refused**, or (mis-configured) shoved into a different open period —
  silently mis-stating the wrong month.
- Period close is finance's hard monthly/quarterly boundary. **Never** post into, back-date into, or reopen a
  closed period from MM. If a correction is needed for a closed month, it is a finance decision, made in the
  current open period — not an MMPV/MMRV change to force the posting through.
- Practical rule: at execute time, check the posting date lands in an open period before staging any GR/invoice.

## Release strategy — the approval gate
- PRs and POs above configured thresholds require **release** before they take effect. Controlled by a
  **release group**, **release codes** (the approver roles), and a **release strategy** keyed on value, plant,
  document type, material group.
- A PO is not a commitment to the vendor until released and sent. A PR is not convertible until released.
- **Never bypass a release**, and **never split a PO or lower its value to drop under a threshold** — that is
  the same authority violation with extra steps, and it is auditable.
- When a workflow issues/changes a PO, treat crossing a release threshold as a committing action that routes
  to the named approver, not something to engineer around.

## GR/IR clearing — how a receipt and its invoice reconcile
- **GR** debits stock (or consumption) and credits the **GR/IR clearing** account.
- **IR** (invoice receipt) debits GR/IR and credits the vendor. When quantity and price match, GR/IR nets to zero.
- A **quantity or price mismatch leaves an open item** on GR/IR — the classic 3-way-match exception
  (`invoice-3way-match` works exactly this gap).
- **GR-based invoice verification**: if the PO has it set, an invoice must match a **specific** goods receipt,
  not just the PO total — matching against the PO alone will mis-reconcile.
- **MR11** clears residual GR/IR balances — but it is a **write-off with P&L impact**, not housekeeping. It is
  a destructive action: it resolves the imbalance by booking the difference, so it needs review, not a reflex.

Gating note: a posting-period check is a precondition on every GR/IR posting; a release-threshold crossing is
a committing action requiring the named approver; an MR11 write-off is destructive.
