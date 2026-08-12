#!/usr/bin/env python3
"""Show the resolved autonomy dial.

Reads the project's `.scm/autonomy.yaml` if present, else the plugin's shipped
`config/autonomy.default.yaml`, and prints the level+limits each configured (workflow,app)
resolves to. Run from the project directory. Used by the /scm-autonomy command.
"""
import os
import sys

PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)
sys.path.insert(0, PLUGIN_ROOT)

from core import autonomy, session  # noqa: E402

_NAMES = {0: "L0 observe", 1: "L1 suggest", 2: "L2 gated",
          3: "L3 bounded-auto", 4: "L4 auto", 5: "L5 yolo"}


def main() -> None:
    cwd = os.getcwd()
    scm = os.path.join(cwd, ".scm")
    project_cfg = os.path.join(scm, "autonomy.yaml")
    shipped_cfg = os.path.join(PLUGIN_ROOT, "config", "autonomy.default.yaml")
    path = project_cfg if os.path.exists(project_cfg) else shipped_cfg

    cfg = autonomy.load(path)
    active = session.active_workflow(scm)

    print(f"autonomy config : {path}")
    print(f"active workflow : {active or '(none set)'}")
    if cfg.fell_back:
        print("STATUS          : FAILED CLOSED -> everything resolves to L0 observe (reads only)")
        return
    print(f"default level   : {cfg.default_level}")

    print("\nconfigured (workflow x app):")
    if not cfg.overrides:
        print("  (none — all workflows use the default)")
    for o in cfg.overrides:
        wf = o.get("workflow", "?")
        app = o.get("app") or "*(any app)"
        r = cfg.resolve(wf, o.get("app") or "*")
        lim = ""
        if r.rank == 3:
            lim = f"  limits(value<= {r.limits.max_value}, qty<= {r.limits.max_qty}, count<= {r.limits.max_count})"
        print(f"  {wf:22} {app:12} -> {_NAMES.get(r.rank, r.level)}{lim}")


if __name__ == "__main__":
    main()
