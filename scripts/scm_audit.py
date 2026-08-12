#!/usr/bin/env python3
"""Show and verify the audit log.

Reads the project's `.scm/audit.jsonl`, prints a compact table of gated/executed
actions, and verifies the hash chain is intact (tamper-evident). Run from the
project directory. Used by the /scm-audit command. Exits non-zero if the chain
is broken.
"""
import json
import os
import sys

PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)
sys.path.insert(0, PLUGIN_ROOT)

from core import audit  # noqa: E402


def main() -> None:
    scm = os.path.join(os.getcwd(), ".scm")
    path = os.path.join(scm, "audit.jsonl")
    if not os.path.exists(path):
        print(f"no audit log yet at {path}")
        return

    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    print(f"audit log : {path}   ({len(rows)} entries)\n")
    print(f"{'#':>3}  {'decision':8}  {'app':6}  {'op':26}  {'level':13}  rule")
    print("-" * 78)
    for i, r in enumerate(rows):
        print(f"{i:>3}  {r.get('decision',''):8}  {r.get('app',''):6}  "
              f"{(r.get('op') or ''):26}  {r.get('level',''):13}  {r.get('rule','')}")

    ok, idx, reason = audit.verify(path)
    print()
    if ok:
        print("chain integrity : OK (tamper-evident hash chain intact)")
    else:
        print(f"chain integrity : BROKEN at entry {idx} ({reason}) — the log was altered")
        sys.exit(1)


if __name__ == "__main__":
    main()
