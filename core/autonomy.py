"""The autonomy dial — customer-set, per (workflow x app).

Levels (rank): observe 0 · suggest 1 · gated 2 · bounded-auto 3 · auto 4 · yolo 5.
The agent does NOT choose the level; the customer sets it in config/autonomy.example.yaml
and the gate enforces it deterministically.

Config schema (a small YAML subset — comments + top-level scalars + an
``overrides:`` list of flat maps):

    default_level: gated
    overrides:
      - workflow: replenishment-to-po
        app: coupa
        level: bounded-auto
        max_value: 10000
        max_qty: 500
        max_count: 5
      - workflow: risk-watch        # no app -> applies to any app for this workflow
        level: observe

Resolution precedence: exact (workflow,app) > workflow-wide > default_level.

FAIL CLOSED: a missing/unparseable file resolves EVERYTHING to observe (L0). A
readable file with no ``default_level`` uses the documented default (gated). An
unknown level string resolves to observe for that scope.
"""
from __future__ import annotations

from dataclasses import dataclass, field

_RANK = {
    "observe": 0, "suggest": 1, "gated": 2,
    "bounded-auto": 3, "auto": 4, "yolo": 5,
}
_ALIAS = {f"l{r}": name for name, r in _RANK.items()}
_DOCUMENTED_DEFAULT = "gated"
_SAFE = "observe"


def _normalize(level) -> str | None:
    if not isinstance(level, str):
        return None
    key = level.strip().lower()
    key = _ALIAS.get(key, key)
    return key if key in _RANK else None


@dataclass
class Limits:
    max_value: int = 0
    max_qty: int = 0
    max_count: int = 0


@dataclass
class Resolution:
    level: str
    rank: int
    limits: Limits
    source: str  # "override" | "default" | "fail-closed"
    currency: str | None = None  # the budget currency; a write in another gates


@dataclass
class AutonomyConfig:
    default_level: str = _DOCUMENTED_DEFAULT
    overrides: list = field(default_factory=list)
    fell_back: bool = False

    def resolve(self, workflow: str, app: str) -> Resolution:
        if self.fell_back:
            return Resolution(_SAFE, 0, Limits(), "fail-closed")

        chosen, source = None, "default"
        # exact (workflow, app)
        for o in self.overrides:
            if o.get("workflow") == workflow and o.get("app") == app:
                chosen, source = o, "override"
                break
        # workflow-wide (no app on the override)
        if chosen is None:
            for o in self.overrides:
                if o.get("workflow") == workflow and not o.get("app"):
                    chosen, source = o, "override"
                    break

        raw_level = chosen.get("level") if chosen else self.default_level
        level = _normalize(raw_level)
        if level is None:
            return Resolution(_SAFE, 0, Limits(), "fail-closed")

        limits = Limits()
        currency = None
        if chosen:
            limits = Limits(
                max_value=_int(chosen.get("max_value")),
                max_qty=_int(chosen.get("max_qty")),
                max_count=_int(chosen.get("max_count")),
            )
            currency = chosen.get("currency") or None
        return Resolution(level, _RANK[level], limits, source, currency=currency)


def _int(v) -> int:
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return 0


def _unquote(s: str) -> str:
    """Strip one layer of surrounding matching quotes — idiomatic YAML that our
    subset must accept rather than silently fail closed."""
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    return s


def _parse(text: str) -> dict:
    top: dict = {}
    overrides: list = []
    cur = None
    in_overrides = False
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        if indent == 0:
            in_overrides = False
            cur = None
            key, _, val = stripped.partition(":")
            key, val = _unquote(key), _unquote(val)
            if key == "overrides" and val == "":
                in_overrides = True
                top["overrides"] = overrides
            else:
                top[key] = val
            continue
        if in_overrides:
            if stripped.startswith("-"):
                cur = {}
                overrides.append(cur)
                item = stripped[1:].strip()
                if item:
                    k, _, v = item.partition(":")
                    cur[_unquote(k)] = _unquote(v)
            elif cur is not None:
                k, _, v = stripped.partition(":")
                cur[_unquote(k)] = _unquote(v)
    return top


def load(path: str) -> AutonomyConfig:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = _parse(f.read())
    except (OSError, UnicodeDecodeError, ValueError):
        return AutonomyConfig(fell_back=True)

    default_level = _normalize(data.get("default_level", _DOCUMENTED_DEFAULT))
    if default_level is None:
        # a declared-but-invalid global default fails the whole config closed
        return AutonomyConfig(fell_back=True)

    overrides = data.get("overrides") or []
    if not isinstance(overrides, list):
        overrides = []
    return AutonomyConfig(default_level=default_level, overrides=overrides)


def default_path(plugin_root: str) -> str:
    import os
    return os.path.join(plugin_root, "config", "autonomy.default.yaml")
