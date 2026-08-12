---
description: Show the current autonomy dial — the level (and limits) each workflow x app resolves to.
---

Show the autonomy dial for this project.

Run:
`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scm_autonomy.py"`

Then explain the result in plain terms using the level table from the `supply-chain-gating` skill:
what each configured workflow×app will do on a write (block / ask / auto-within-limits / auto), and
call out the default and any fail-closed condition. If the user wants to change it, point them at
`config/autonomy.example.yaml` (or their project `.scm/autonomy.yaml`) and remind them the agent cannot set
its own level.
