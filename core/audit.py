"""Hash-chained, tamper-evident audit log.

Each action is one JSON line. Every line carries the previous line's hash in
`prev`, and its own `hash` over its contents (excluding `hash`). Editing,
reordering, or deleting any past line breaks the chain — `verify()` reports the
first bad index. The hook writes the audit entry BEFORE it commits an action.

Honest v1 limit: a local file is tamper-EVIDENT, not tamper-PROOF; true
immutability needs an append-only server sink (roadmap).
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone

GENESIS = "0" * 64


def _compute(record_without_hash: dict) -> str:
    payload = json.dumps(record_without_hash, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_lines(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [l for l in f.read().splitlines() if l.strip()]
    except FileNotFoundError:
        return []


def tip(path: str) -> str:
    """Hash of the last record, or GENESIS for an empty/missing log."""
    lines = _read_lines(path)
    if not lines:
        return GENESIS
    try:
        return json.loads(lines[-1]).get("hash", GENESIS)
    except json.JSONDecodeError:
        return GENESIS


def append(path: str, entry: dict, ts: str | None = None) -> dict:
    """Append `entry` as a chained record; returns the full stored record."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    record = dict(entry)
    record["ts"] = ts or _now_iso()
    record["prev"] = tip(path)
    record["hash"] = _compute(record)  # record has no 'hash' yet
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def verify(path: str):
    """Return (ok, first_bad_index|None, reason|None)."""
    prev = GENESIS
    for i, line in enumerate(_read_lines(path)):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            return False, i, "unparseable"
        stored = record.pop("hash", None)
        if record.get("prev") != prev:
            return False, i, "broken-link"
        if _compute(record) != stored:
            return False, i, "bad-hash"
        prev = stored
    return True, None, None
