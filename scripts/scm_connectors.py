#!/usr/bin/env python3
"""Show the connector registry the hook will use (built-in defaults + your .scm/connectors.json).

Run from your project dir. Prints, per app, which tool ops are classified
read/write/destructive/outbound. Two cases when a tool is NOT listed: an
unrecognised OP on a listed (governed) app classifies as `unknown` and the hook
GATES it; a tool on an app that is not listed at all classifies as `non_connector`
and PASSES ungoverned. Map your real connector in `.scm/connectors.json` so its
app is governed and its ops are classified:

    {
      "coupa": { "reads": ["po_fetch"], "writes": ["po_create"],
                 "destructive": ["po_cancel"], "outbound": ["email_supplier"] }
    }

Used by the /scm-connectors command.
"""
import os
import sys

PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)
sys.path.insert(0, PLUGIN_ROOT)

from core import registry  # noqa: E402


def main() -> None:
    scm = os.path.join(os.getcwd(), ".scm")
    reg = registry.load_registry(scm)
    overrides = os.path.join(scm, "connectors.json")

    print(f"connector registry (built-in defaults + {'your ' + overrides if os.path.exists(overrides) else 'no overrides'})\n")
    for app in sorted(reg):
        t = reg[app]
        sim = " [simulator]" if t.simulator else ""
        print(f"■ {app}{sim}")
        for label, ops in (("read", t.reads), ("write", t.writes),
                           ("destructive", t.destructive), ("outbound", t.outbound)):
            if ops:
                print(f"    {label:11}: {', '.join(sorted(ops))}")
    print("\nHow an unlisted tool is treated (the safety boundary):")
    print("  - an unrecognised OP on a listed app -> `unknown`       -> the hook GATES it (safe)")
    print("  - a tool on an app NOT listed above  -> `non_connector` -> PASSES ungoverned")
    print("So a real SCM connector the plugin does not recognise (a different vendor, or a")
    print("server whose app name is not one above) is NOT governed until you map it. Add its")
    print(f"app + exact tool names to {overrides} (see this file's header), then re-run /scm-connectors.")


if __name__ == "__main__":
    main()
