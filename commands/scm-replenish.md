---
description: Run the DC stock-split deployment loop for a scarce SKU (read on-hand, size the shortfall, stage a gated allocation to the WMS wave).
argument-hint: "[SKU or item] [optional: location/plant]"
---

Start the **DC stock-split deployment** workflow.

1. First, mark this workflow active so the harness applies the right autonomy level. Run:
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scm_run.py" dc-stock-split`
2. Then load and follow the `dc-stock-split` skill (and `supply-chain-gating` + the
   expertise skill for the system you're reading/writing, e.g. `manhattan-wms`,
   `sap-ewm`) to handle: **$ARGUMENTS**.

Read the on-hand signal first, size the shortfall against available-to-deploy, rank nodes by
days-of-supply and priority, prepare the exact allocation with a diff + rollback + provenance, then
write it to the WMS wave through the connector's real write tool. The `PreToolUse` hook enforces the
dial — expect a read to pass, a gated write to pause for approval, and a small in-budget allocation
under bounded-auto to go through.

If no connector is configured, tell the user which connector this needs and stop — do not fabricate
data.
