"""Working state under .scm/ — active workflow + cumulative blast-radius.

session.json  -> {"workflow": <name>, "ts": <epoch>}. Which workflow is active,
                 set by the command/skill that starts it, read by the hook to
                 resolve the per-workflow autonomy level. It EXPIRES after
                 ACTIVE_TTL so a stale marker doesn't keep applying an old
                 workflow's dial to unrelated later work.
state.json    -> {"<workflow>|<app>": {"value": float, "count": int}, ...}. The
                 running session total, NAMESPACED per (workflow, app), so two
                 workflows in one Claude session don't leak budget into each
                 other. bounded-auto (L3) checks the relevant key.

FAIL CLOSED: an unreadable state file returns an infinite cumulative so L3 gates
instead of under-counting. An unreadable/stale session file returns no active
workflow (the hook then uses the default level, which is gated).
"""
from __future__ import annotations

import json
import os
import time

ACTIVE_TTL = 30 * 60  # a workflow marker older than 30 min no longer applies


def _p(scm_dir: str, name: str) -> str:
    return os.path.join(scm_dir, name)


def _load(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def set_active_workflow(scm_dir: str, workflow: str, now: float | None = None) -> None:
    os.makedirs(scm_dir, exist_ok=True)
    ts = time.time() if now is None else now
    with open(_p(scm_dir, "session.json"), "w", encoding="utf-8") as f:
        json.dump({"workflow": workflow, "ts": ts}, f)


def active_workflow(scm_dir: str, now: float | None = None, ttl_seconds: float = ACTIVE_TTL):
    """Active workflow, or None if missing, corrupt, or older than the TTL."""
    try:
        data = _load(_p(scm_dir, "session.json"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    workflow = data.get("workflow")
    if not workflow:
        return None
    ts = data.get("ts")
    if ts is not None:
        current = time.time() if now is None else now
        try:
            if current - float(ts) > ttl_seconds:
                return None
        except (TypeError, ValueError):
            return None
    return workflow


def clear_active_workflow(scm_dir: str) -> None:
    try:
        os.remove(_p(scm_dir, "session.json"))
    except OSError:
        pass


def _key(workflow: str, app: str) -> str:
    return f"{workflow}|{app}"


def _load_state(scm_dir: str):
    """Return (state_dict, corrupt: bool). Missing -> ({}, False)."""
    path = _p(scm_dir, "state.json")
    if not os.path.exists(path):
        return {}, False
    try:
        data = _load(path)
        if not isinstance(data, dict):
            return {}, True
        return data, False
    except (json.JSONDecodeError, OSError):
        return {}, True


def get_cumulative(scm_dir: str, workflow: str, app: str):
    """(value, count) for this (workflow, app). Missing -> (0,0). Corrupt -> (inf, inf)."""
    state, corrupt = _load_state(scm_dir)
    if corrupt:
        return float("inf"), float("inf")
    entry = state.get(_key(workflow, app)) or {}
    try:
        return float(entry.get("value", 0.0)), int(entry.get("count", 0))
    except (TypeError, ValueError):
        return float("inf"), float("inf")


def record_commit(scm_dir: str, workflow: str, app: str, value: float, count: int = 1):
    """Add to the (workflow, app) running total; returns the new (value, count)."""
    state, corrupt = _load_state(scm_dir)
    if corrupt:
        state = {}  # recover from a corrupt file on next write
    key = _key(workflow, app)
    entry = state.get(key) or {}
    try:
        cur_value = float(entry.get("value", 0.0))
        cur_count = int(entry.get("count", 0))
    except (TypeError, ValueError):
        cur_value, cur_count = 0.0, 0
    new_value = cur_value + float(value or 0.0)
    new_count = cur_count + int(count)
    state[key] = {"value": new_value, "count": new_count}
    os.makedirs(scm_dir, exist_ok=True)
    with open(_p(scm_dir, "state.json"), "w", encoding="utf-8") as f:
        json.dump(state, f)
    return new_value, new_count


def reset(scm_dir: str) -> None:
    os.makedirs(scm_dir, exist_ok=True)
    with open(_p(scm_dir, "state.json"), "w", encoding="utf-8") as f:
        json.dump({}, f)
