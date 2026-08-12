# Classification and export licensing (e2open GTM)

Contents: Global Knowledge content model · the two schemes (HS vs ECCN/USML) · export-control tiers · license
determination · classify-up rule · deemed export / re-export / de-minimis · recovery.

Load when classifying a product or handling a license / legal-control block. Two separate schemes live here,
and both are driven by **Global Knowledge** content that carries effective dates.

## Global Knowledge content model
- The subscribed trade-content database: HS/HTS codes, duty rates, export controls, denied-party lists, and
  FTA rules for 160+ countries. Each content item carries an **effective date**.
- e2open refreshes it as a **managed feed**. A control, rate, or list can change with a refresh you did not
  trigger. Every determination is **bound to the content version behind it** - re-read the effective date at
  execute, because a stale version misclassifies, misprices duty, or misses a newly-added control.

## Two schemes - do not conflate
- **HS / HTS** - the commodity code for **duty and admissibility** (imports). Drives duty rate, PGA flags,
  and FTA eligibility. Says nothing about export control.
- **ECCN / USML** - the **export-control** code. A right HS with a wrong ECCN still ships a controlled item
  illegally. The two are maintained separately and confirmed separately.

Classification states: **proposed (draft) -> confirmed**. Confirming commits the code every future screen,
filing, and FTA qualification uses - a wrong confirmed code mis-declares and mis-screens each future shipment
until someone reclassifies. Changing an already-confirmed code re-prices duty and re-runs control on future
filings (destructive; see the reclassification rule in SKILL.md).

## Export control tiers
**Jurisdiction first.** Before classifying, decide the regime: is the item ITAR/USML (State/DDTC) or EAR/CCL
(Commerce/BIS)? This jurisdiction call is its own high-stakes determination - get it wrong and the whole
control path (list, license, checks) is wrong. When unclear, treat as ITAR and route to a human; a commodity
jurisdiction request (CJ) is the formal way to resolve it.
- **ITAR / USML** - defense articles, US State Dept (DDTC). Strictest; DDTC-licensed; **never auto-clear**.
- **EAR / CCL with an ECCN** - Commerce (BIS). A license may be required by destination, end use, and party.
- **EAR99** - the residual EAR bucket. **Not "uncontrolled":** still barred to embargoed destinations, denied
  parties, and prohibited end uses (WMD, certain military end uses).

## License determination
The intersection that decides the outcome: **ECCN x ultimate destination x end use x party**.
- Result is **No License Required (NLR)**, a **license exception**, or **license required**.
- A required license routes to the human **licensing officer**. The agent never auto-assigns a license, never
  clears a legal-control block, never proposes a control downgrade.
- License states: **required -> assigned -> depleted**. Each use draws down remaining value/quantity; a
  partial-cover assignment blocks the balance; an expired or exhausted license blocks the next shipment.
  Assigning the wrong license depletes the wrong authorization and mis-reports usage.

## When in doubt, classify up
If it is unclear whether an item is ITAR/USML vs EAR-controlled, or EAR-controlled vs EAR99, default to the
**stricter** control and route to a human. Never resolve the doubt toward the lower control to let a shipment clear.

## Edge cases that break "nothing shipped" logic
- **Deemed export** - releasing controlled technology or technical data to a **foreign national** is an export
  to that person's country, even with no goods moving. A "no goods" transaction can still need a license.
- **Re-export** - a US-origin item moving between two foreign countries stays under US jurisdiction; "it never
  left our country" logic misses it.
- **De-minimis** - a foreign-made item with more than the de-minimis US-controlled content stays subject to
  the EAR; "not made/shipped from the US" logic misses it.

## Recovery
A confirmed classification is corrected by a **new version**, applied going forward; historic filings keep the
code they were filed with. A depleted license value is restored only by **reversing the assignment** (a
controlled action), not by editing the remaining value.
