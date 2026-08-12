---
description: Show which of your MCP connector tools the harness governs, and flag any it can't classify yet.
---

Help the user map their real MCP connector(s) so the harness governs them.

1. Show which connector tools the harness recognises (built-in defaults + the user's `.scm/connectors.json`):
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scm_connectors.py"`
2. Look at the MCP tools actually available in this session (their `mcp__<app>__<op>` names).
   For each SCM connector the user has, compare its real tool names against the registry output.
3. Flag every real tool that is **not** classified — those are `unknown` and the hook will gate them
   (and if the whole app prefix is unknown, its writes run **ungoverned**, which is worse). Tell the
   user exactly which tool names need mapping.
4. Offer to write/update `.scm/connectors.json` mapping their real tool names into
   read / write / destructive / outbound (see the script header for the format). Be careful:
   classify irreversible actions (cancel, delete, reverse, deactivate, block) as **destructive** so
   the floor fires.
5. **Confirm before writing.** Echo back each op with the class you assigned - especially every write and
   destructive - and have the user confirm. A write mis-classified as a `read` passes the gate silently and
   is not even audited; this confirmation is the one place that error gets caught. Then re-run step 1 to
   confirm nothing is left unclassified.

Do not guess a tool's class from its name alone if you can check its docs or behavior - a write
mis-classified as a read would slip past the gate.

Safety boundary to tell the user: the gate governs only `mcp__*` connector tools. A Bash/curl call, or a
tool on an app left unmapped, is **not** governed. Declaring an app (even with an empty op list) at least
makes its unrecognised ops fail closed instead of passing ungoverned.
