"""One shared extractor for a write's money value, quantity, and currency.

Used by BOTH the gate (to decide) and the hook (to audit), so the audited value
and the gated value can never diverge. Candidate fields are per-app (from the
registry manifest) and may be dotted paths into nested payloads. Unreadable ->
None, which the gate treats as fail-closed (it gates rather than guess).

v1 limit: no line-item summation (`lines[].qty*price`) yet — a connector that
carries value only as a line array reads as None and gates. That is safe (asks),
just conservative; add a per-op sum rule to the manifest when such a connector lands.
"""
from __future__ import annotations

_DEFAULT_VALUE_FIELDS = ("value", "amount", "total", "total_value", "net_value", "grand_total")
_DEFAULT_QTY_FIELDS = ("quantity", "qty", "order_qty", "units")


def _dig(obj, path: str):
    """Follow a dotted path into nested dicts; None if any hop is missing."""
    cur = obj
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _first_number(tool_input, fields):
    if not isinstance(tool_input, dict):
        return None
    for f in fields:
        raw = _dig(tool_input, f) if "." in f else tool_input.get(f)
        if raw is None:
            continue
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None
    return None


def extract(tool_input, value_fields=None, qty_fields=None):
    """Return (value, qty) as floats, or None where unreadable."""
    vf = value_fields or _DEFAULT_VALUE_FIELDS
    qf = qty_fields or _DEFAULT_QTY_FIELDS
    return _first_number(tool_input, vf), _first_number(tool_input, qf)


def currency_of(tool_input, currency_field=None):
    field = currency_field or "currency"
    if not isinstance(tool_input, dict):
        return None
    raw = _dig(tool_input, field) if "." in field else tool_input.get(field)
    return raw if isinstance(raw, str) and raw else None
