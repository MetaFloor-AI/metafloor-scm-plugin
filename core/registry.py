"""Per-app tool registry — classify a connector tool call.

The PreToolUse hook sees only `tool_name` + `tool_input`, never MCP annotations
like readOnlyHint/destructiveHint. So the plugin keeps its own registry, one
entry per app pack, naming which of that connector's tools are reads, writes,
irreversible/destructive writes, or outbound data-sends.

The canonical registry is DATA, not code. It ships centrally, one file per
governed app, at `core/registries/<app>.json` — the filename stem IS the app key.
Expertise skills stay prose-only; the machine tool classification lives here. All
manifests load at import into DEFAULT_REGISTRY. A customer extends it (adds their
real connector's ops) via `.scm/connectors.json`, unioned over the canonical set
(additive only — a stricter class wins because destructive/outbound classify
before writes, but a canonical `read` cannot be downgraded, so canonical reads
must stay conservative) — real connector tool names rarely match the canonical guesses, and a
governed app the customer declares there becomes known even without a shipped
manifest (an unclassified write on a known app fails closed to gate, not allow).
Use `load_registry(scm_dir)` to get the merged view.

An app-key absent from the merged registry is NOT governed: it classifies as
`non_connector` and passes (so non-SCM MCP tools like GitHub/Slack are untouched).
That is why shipping the full canonical set matters — a governed SCM connector
with no manifest and no customer declaration is the one residual fail-open, which
`/scm-connectors` surfaces loudly at first run.

Classification kinds:
  read          — safe, never gated
  write         — a mutating call (reversible-ish)
  destructive   — irreversible/hard-to-reverse write (cancel, delete, reverse)
  outbound      — sends data outside the company (email, RFQ, export)
  unknown       — a tool on a KNOWN app we don't recognise -> gate fails it closed
  non_connector — not an SCM app we govern (plain tools, other MCP servers)

Tool-name shape is Claude Code's MCP convention: ``mcp__<app>__<op>``.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

_PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REGISTRY_DIR = os.path.join(_PLUGIN_ROOT, "core", "registries")


@dataclass
class AppTools:
    simulator: bool = False
    reads: set = field(default_factory=set)
    writes: set = field(default_factory=set)
    destructive: set = field(default_factory=set)
    outbound: set = field(default_factory=set)
    # where this connector carries a write's money value / quantity / currency
    # (candidate fields, dotted paths allowed). Empty -> the shared defaults.
    value_fields: list = field(default_factory=list)
    qty_fields: list = field(default_factory=list)
    currency_field: str | None = None


@dataclass
class Classification:
    is_connector: bool
    app: str | None
    op: str | None
    kind: str  # read | write | destructive | outbound | unknown | non_connector
    simulator: bool = False
    value_fields: list | None = None
    qty_fields: list | None = None
    currency_field: str | None = None


def _app_from_spec(spec: dict) -> AppTools:
    return AppTools(
        simulator=bool(spec.get("simulator", False)),
        reads=set(spec.get("reads", [])),
        writes=set(spec.get("writes", [])),
        destructive=set(spec.get("destructive", [])),
        outbound=set(spec.get("outbound", [])),
        value_fields=list(spec.get("value_fields", [])),
        qty_fields=list(spec.get("qty_fields", [])),
        currency_field=spec.get("currency_field"),
    )


def _load_manifests(registry_dir: str) -> dict:
    """Scan core/registries/<app>.json — one manifest per governed app.

    The filename stem is the canonical app key. A manifest whose internal `app`
    disagrees with its filename is skipped: the filename is the key, and a
    mismatch is a packaging bug we refuse to load silently (the lint asserts it).
    """
    reg: dict = {}
    try:
        names = sorted(os.listdir(registry_dir))
    except OSError:
        return reg
    for name in names:
        if not name.endswith(".json"):
            continue
        path = os.path.join(registry_dir, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                spec = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        app = name[: -len(".json")]
        if spec.get("app") and spec["app"] != app:
            continue  # basename must match the app key
        reg[app] = _app_from_spec(spec)
    return reg


# Canonical registry, loaded from core/registries/<app>.json at import.
DEFAULT_REGISTRY: dict = _load_manifests(_REGISTRY_DIR)


def _clone(reg: dict) -> dict:
    return {
        app: AppTools(t.simulator, set(t.reads), set(t.writes), set(t.destructive),
                      set(t.outbound), list(t.value_fields), list(t.qty_fields),
                      t.currency_field)
        for app, t in reg.items()
    }


def _merge_app(base: AppTools, spec: dict) -> AppTools:
    if "simulator" in spec:
        base.simulator = bool(spec["simulator"])
    base.reads |= set(spec.get("reads", []))
    base.writes |= set(spec.get("writes", []))
    base.destructive |= set(spec.get("destructive", []))
    base.outbound |= set(spec.get("outbound", []))
    if spec.get("value_fields"):
        base.value_fields = list(spec["value_fields"]) + base.value_fields
    if spec.get("qty_fields"):
        base.qty_fields = list(spec["qty_fields"]) + base.qty_fields
    if spec.get("currency_field"):
        base.currency_field = spec["currency_field"]
    return base


def load_registry(scm_dir: str | None = None) -> dict:
    """Canonical registry merged with the customer's `.scm/connectors.json`.

    The customer file maps their real connector(s) — a new app key, or extra ops
    on a known app — into classes. A missing or corrupt file leaves the canonical
    set unchanged (unknown real ops then fail closed to deny, which is safe).
    """
    reg = _clone(DEFAULT_REGISTRY)
    if not scm_dir:
        return reg
    path = os.path.join(scm_dir, "connectors.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return reg
    if not isinstance(data, dict):
        return reg
    for app, spec in data.items():
        if not isinstance(spec, dict):
            continue
        reg[app] = _merge_app(reg.get(app, AppTools()), spec)
    return reg


def _split(tool_name: str):
    """Return (app, op) for an ``mcp__app__op`` name, else (None, None)."""
    if not isinstance(tool_name, str) or not tool_name.startswith("mcp__"):
        return None, None
    parts = tool_name.split("__")
    if len(parts) < 3 or not parts[1] or not parts[2]:
        return None, None
    app = parts[1]
    op = "__".join(parts[2:])  # tolerate ops that themselves contain "__"
    return app, op


def classify(tool_name: str, reg: dict | None = None) -> Classification:
    reg = DEFAULT_REGISTRY if reg is None else reg
    app, op = _split(tool_name)
    if app is None or app not in reg:
        return Classification(is_connector=False, app=None, op=None, kind="non_connector")

    tools = reg[app]
    if op in tools.reads:
        kind = "read"
    elif op in tools.destructive:
        kind = "destructive"
    elif op in tools.outbound:
        kind = "outbound"
    elif op in tools.writes:
        kind = "write"
    else:
        kind = "unknown"
    return Classification(
        is_connector=True, app=app, op=op, kind=kind, simulator=tools.simulator,
        value_fields=tools.value_fields or None,
        qty_fields=tools.qty_fields or None,
        currency_field=tools.currency_field,
    )
