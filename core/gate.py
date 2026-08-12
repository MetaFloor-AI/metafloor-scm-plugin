"""The gate — deterministic allow | ask | deny.

All inputs are code/config-derived (a tool classification + a resolved autonomy
level + session totals). The gate never consults the model's opinion, so no
prompt-injected "auto-approve" can move it. See the level table in the plan (sec4).

Design notes on the bounded-auto (L3) limits:
  - `max_value` is BOTH a per-action ceiling and the session budget: a write
    auto-approves only if `cumulative_value + this_value <= max_value`. This
    defends salami-slicing (many small writes summing past the cap).
  - `max_qty` is a per-action line ceiling.
  - `max_count` caps how many writes may auto-approve in one session.
  - If the value can't be read from the tool input, the gate CANNOT confirm it
    is within budget -> it fails closed to `ask`.
"""
from __future__ import annotations

from dataclasses import dataclass

from core import values


@dataclass
class Decision:
    action: str   # "allow" | "ask" | "deny"
    rule: str     # short machine tag of the rule that fired
    reason: str   # human-facing one-liner


def _allow(rule, reason):
    return Decision("allow", rule, reason)


def _ask(rule, reason):
    return Decision("ask", rule, reason)


def _deny(rule, reason):
    return Decision("deny", rule, reason)


def decide(cls, res, tool_input=None, cumulative_value=0.0, cumulative_count=0) -> Decision:
    # 1. Not ours to govern.
    if not cls.is_connector:
        return _allow("non-connector", "not a governed SCM connector tool")

    # 2. Reads always pass.
    if cls.kind == "read":
        return _allow("read", "read-only call")

    # 3. A tool on a known app we don't recognise -> fail closed (could be a read
    #    or a write; the harness can't tell, so it gates).
    if cls.kind == "unknown":
        return _deny(
            "unknown-tool",
            f"'{cls.app}' tool '{cls.op}' is unclassified, so the harness can't tell if it "
            f"reads or writes and gates it. Fix: classify it in .scm/connectors.json "
            f"(read/write/destructive/outbound) or run /scm-connectors.")

    # --- from here: a write | destructive | outbound call ---
    rank = res.rank

    # 4. L0 observe / L1 suggest: the agent proposes, a human executes.
    if rank <= 1:
        if res.source == "fail-closed":
            return _deny(
                "config:fail-closed",
                "autonomy config is missing or unreadable, so the harness failed closed to L0 "
                "(reads only, no writes). Fix: check .scm/autonomy.yaml for a bad level or "
                "malformed line, or run /scm-autonomy.")
        return _deny(f"{res.level}:writes-blocked",
                     f"autonomy '{res.level}' does not execute writes — propose it for a human to run")

    # 5. L5 yolo: no gates, but only against a simulator connector.
    if rank == 5:
        if cls.simulator:
            return _allow("yolo:simulator", "yolo level on a simulator — no gate")
        return _deny("yolo:real-connector-refused",
                     "yolo is dev/test only and refuses a real connector")

    # 6. L2 gated: every write pauses for approval.
    if rank == 2:
        return _ask("gated:approval-required", "gated autonomy — human approval required for this write")

    # --- L3 bounded-auto (3) or L4 auto (4) ---

    # Outbound sending data outside the company always gates below yolo.
    if cls.kind == "outbound":
        return _ask("floor:outbound", "outbound data-send — always gated for human approval")

    # Irreversible/destructive writes gate below L4 (a small cancel is still irreversible).
    if cls.kind == "destructive":
        if rank == 4:
            return _allow("auto:destructive", "auto autonomy executes in-workflow (audited after)")
        return _ask("floor:destructive", "irreversible/destructive write — gated regardless of size")

    # Plain write.
    if rank == 4:
        return _allow("auto", "auto autonomy executes in-workflow (audited after)")

    # rank == 3, bounded-auto: enforce the limits.
    lim = res.limits
    if cumulative_count + 1 > lim.max_count:
        return _ask("limit:count",
                    f"session write count {cumulative_count + 1} exceeds max_count {lim.max_count}")

    # Currency guard: a write in a currency other than the budget's gates —
    # magnitudes across currencies are not comparable (¥78,000 vs $78,000).
    if res.currency:
        cur = values.currency_of(tool_input, cls.currency_field)
        if cur and cur.upper() != res.currency.upper():
            return _ask("limit:currency",
                        f"write currency {cur} differs from budget currency {res.currency} — gated")

    value, qty = values.extract(tool_input, cls.value_fields, cls.qty_fields)
    if qty is not None and qty > lim.max_qty:
        return _ask("limit:qty", f"quantity {qty:g} exceeds max_qty {lim.max_qty}")

    if value is None:
        return _ask("limit:value-unknown",
                    "cannot read this write's value from its input — gated to be safe")
    if value > lim.max_value:
        return _ask("limit:value", f"value {value:g} exceeds max_value {lim.max_value}")
    if cumulative_value + value > lim.max_value:
        return _ask("limit:cumulative",
                    f"cumulative value {cumulative_value + value:g} exceeds budget {lim.max_value}")

    return _allow("bounded-auto:within-limits",
                  f"within bounded-auto limits (value {value:g}, budget {lim.max_value})")
