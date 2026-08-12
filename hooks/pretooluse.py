#!/usr/bin/env python3
"""PreToolUse entrypoint for the scm-supply-chain plugin.

Claude Code invokes this on every MCP tool call (matched by hooks.json). It
reads the hook event from stdin, asks core.hook for an allow | ask | deny
decision, and writes the decision JSON to stdout (exit 0). All the logic — and
the fail-closed behaviour — lives in core/, which is unit-tested.
"""
import json
import os
import sys

PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)
sys.path.insert(0, PLUGIN_ROOT)

from core import hook  # noqa: E402


def main() -> None:
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict):
            event = {}
    except Exception:
        event = {}

    out = hook.evaluate(event, PLUGIN_ROOT)
    sys.stdout.write(json.dumps(out))
    sys.exit(0)


if __name__ == "__main__":
    main()
