"""PreToolUse adapter — turns a hook event into an allow | ask | deny decision.

Flow for a governed connector tool:
  classify -> resolve autonomy level (active workflow + app) -> gate.decide
  -> audit the decision -> on auto-allow, add to the cumulative session total.

Reads and non-connector tools pass straight through (no audit noise). Any
internal error on a governed tool fails closed to `deny`; a non-connector tool
is never blocked by our errors.
"""
from __future__ import annotations

import os

from core import registry, autonomy, gate, session, audit, values


def _output(permission: str, reason: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": permission,
            "permissionDecisionReason": reason,
        }
    }


def _resolve_config_path(plugin_root: str, scm_dir: str) -> str:
    """Customer config in the project wins; else the shipped GATED-ONLY default.

    The runtime fallback is `config/autonomy.default.yaml` (gated, no overrides) so
    a fresh install never auto-approves. It is deliberately NOT the example config
    (`config/autonomy.example.yaml`), which carries bounded-auto limits. If even the
    default is missing, autonomy.load fails closed to L0.
    """
    project = os.path.join(scm_dir, "autonomy.yaml")
    if os.path.exists(project):
        return project
    return os.path.join(plugin_root, "config", "autonomy.default.yaml")


def evaluate(event: dict, plugin_root: str, *, config_path: str | None = None,
             scm_dir: str | None = None) -> dict:
    tool_name = (event or {}).get("tool_name")
    tool_input = (event or {}).get("tool_input") or {}
    cwd = (event or {}).get("cwd") or os.getcwd()
    scm_dir = scm_dir or os.path.join(cwd, ".scm")

    # Merge the customer's .scm/connectors.json over the canonical registry so a
    # real connector whose tool names differ is still governed.
    reg = registry.load_registry(scm_dir)
    cls = registry.classify(tool_name, reg=reg)

    # Not ours to govern — never block the user's other tools.
    if not cls.is_connector:
        return _output("allow", "not a governed SCM connector tool")

    try:
        cfg_path = config_path or _resolve_config_path(plugin_root, scm_dir)
        cfg = autonomy.load(cfg_path)
        workflow = session.active_workflow(scm_dir) or ""
        res = cfg.resolve(workflow, cls.app)
        cum_value, cum_count = session.get_cumulative(scm_dir, workflow, cls.app)

        decision = gate.decide(cls, res, tool_input, cum_value, cum_count)

        # Same extractor the gate used -> the audited value can't diverge from
        # the gated value.
        wrote_value = values.extract(tool_input, cls.value_fields, cls.qty_fields)[0] or 0.0

        # Reads are allowed above by classification; here it's a governed
        # write/destructive/outbound/unknown — audit every such decision.
        if cls.kind != "read":
            audit.append(os.path.join(scm_dir, "audit.jsonl"), {
                "tool": tool_name, "app": cls.app, "op": cls.op, "kind": cls.kind,
                "workflow": workflow or None, "level": res.level,
                "decision": decision.action, "rule": decision.rule,
                "reason": decision.reason, "value": wrote_value,
            })

        # Auto-allowed writes commit now -> grow the session blast-radius total.
        if decision.action == "allow" and cls.kind in ("write", "destructive", "outbound"):
            session.record_commit(scm_dir, workflow, cls.app, wrote_value, count=1)

        return _output(decision.action, decision.reason)

    except Exception as e:  # fail closed for anything governed
        return _output(
            "deny",
            f"gate internal error ({type(e).__name__}) — denied for safety. Check that .scm/ is "
            f"writable (the audit log) and .scm/autonomy.yaml is valid, or run /scm-autonomy; "
            f"see .scm/audit.jsonl for the last recorded decisions.")
