---
description: Start a supply-chain workflow under its autonomy level (sets the active workflow the hook reads).
argument-hint: "<workflow-name> [notes]"
---

Start a workflow so the harness applies its per-(workflow × app) autonomy level.

1. Set the active workflow (with a timestamp so it expires when idle):
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scm_run.py" $ARGUMENTS`
   (use only the first token as the workflow name; the rest is your intent).
2. Load and follow that workflow's skill (e.g. `invoice-3way-match`) plus
   `supply-chain-gating` and the expertise skill for the system you're in (e.g. `sap-mm`,
   `coupa`). The hook now resolves the level for `(this workflow, app)` from the dial; run
   `/scm-autonomy` if you want to see what that will do.

Workflow names match the installed `workflows-*` skills. If you're not running a specific workflow,
don't set one — the default level (gated) applies.
