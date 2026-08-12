#!/usr/bin/env python3
"""Set the active workflow so the hook resolves the right autonomy level.

Writes .scm/session.json with a timestamp (so a stale marker expires and doesn't
keep applying an old workflow's dial). Run from the project dir:

    python3 scm_run.py <workflow-name>

Used by /scm-run and the per-workflow commands.
"""
import os
import sys

PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)
sys.path.insert(0, PLUGIN_ROOT)

from core import session  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print("usage: scm_run.py <workflow-name>")
        sys.exit(2)
    workflow = sys.argv[1].strip()
    scm = os.path.join(os.getcwd(), ".scm")
    session.set_active_workflow(scm, workflow)
    print(f"active workflow set: {workflow}  (.scm/session.json; expires after 30 min idle)")


if __name__ == "__main__":
    main()
