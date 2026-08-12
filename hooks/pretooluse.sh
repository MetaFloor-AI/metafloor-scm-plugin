#!/usr/bin/env bash
# PreToolUse launcher — fail CLOSED if no Python interpreter is available.
#
# The gate logic (hooks/pretooluse.py -> core/) is meticulously fail-closed, but it
# only runs if an interpreter launches. If python3/python is missing or not on PATH,
# a bare `python3 ...` hook would fail to start and the connector tool would proceed
# UNGOVERNED. This wrapper instead emits a `deny` decision so a missing interpreter
# blocks the action rather than letting it through.
ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"

if command -v python3 >/dev/null 2>&1; then
  exec python3 "$ROOT/hooks/pretooluse.py"
elif command -v python >/dev/null 2>&1; then
  exec python "$ROOT/hooks/pretooluse.py"
fi

# No interpreter found -> fail closed (deny), with a fix path.
printf '%s' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"MetaFloor gate could not run: no python3/python interpreter on PATH. Python 3 is a hard prerequisite for the safety gate. Install Python 3 (or add it to PATH), then retry."}}'
