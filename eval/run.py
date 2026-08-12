#!/usr/bin/env python3
"""P0 eval runner — BLUE decides, the deterministic scorer scores, print a board.

Default BLUE is our own engine (gate.decide over each scenario's `call`), so the
board measures whether the engine's decisions match the independently-authored
oracles across the scenario spread — including the injection/pressure traps that
prove the engine never reads tool text.

  python3 eval/run.py                 # BLUE = the engine
  python3 eval/run.py --blue FILE     # BLUE = a recorded set {id: "allow|ask|deny"}
                                      # (e.g. a model's decisions, or a sabotage test)

Exits non-zero if ANY scenario is a safety failure.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import gate  # noqa: E402
from core.registry import Classification  # noqa: E402
from core.autonomy import Resolution, Limits  # noqa: E402
import score as scorer  # noqa: E402

_RANK = {"observe": 0, "suggest": 1, "gated": 2, "bounded-auto": 3, "auto": 4, "yolo": 5}


def engine_decision(sc: dict) -> str:
    # Two scenario forms:
    #  - "tool" + "tool_input": the push-down path — run through registry.classify
    #    and the per-app value/currency extraction (tests what breadth changes).
    #  - "call": {kind, op, ...}: a pre-labeled classification (level-table cases).
    if "tool" in sc:
        from core import registry
        reg = registry.load_registry(None)
        if sc.get("connectors"):
            for app, spec in sc["connectors"].items():
                reg[app] = registry._merge_app(reg.get(app, registry.AppTools()), spec)
        cls = registry.classify(sc["tool"], reg=reg)
        tool_input = sc.get("tool_input", {})
    else:
        call = sc["call"]
        cls = Classification(
            is_connector=True, app=sc.get("app"), op=call.get("op"),
            kind=call["kind"], simulator=call.get("simulator", False),
        )
        tool_input = call.get("input", {})

    lim = sc.get("limits", {})
    res = Resolution(
        sc["dial"], _RANK[sc["dial"]],
        Limits(max_value=lim.get("max_value", 0), max_qty=lim.get("max_qty", 0),
               max_count=lim.get("max_count", 0)),
        "eval", currency=sc.get("currency"),
    )
    d = gate.decide(cls, res, tool_input,
                    cumulative_value=sc.get("cumulative_value", 0.0),
                    cumulative_count=sc.get("cumulative_count", 0))
    return d.action


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--blue", help="JSON file of {scenario_id: allow|ask|deny}")
    ap.add_argument("--scenarios", default=os.path.join(os.path.dirname(__file__), "scenarios.json"))
    ap.add_argument("--max-over-gate", type=int, default=None,
                    help="fail (exit 1) if more than N scenarios are over-gated")
    args = ap.parse_args()

    with open(args.scenarios, encoding="utf-8") as f:
        scenarios = json.load(f)["scenarios"]

    blue_map = None
    if args.blue:
        with open(args.blue, encoding="utf-8") as f:
            blue_map = json.load(f)

    rows = []
    for sc in scenarios:
        blue = blue_map[sc["id"]] if blue_map else engine_decision(sc)
        rows.append(scorer.score_one(sc, blue))

    label = f"recorded ({os.path.basename(args.blue)})" if args.blue else "engine"
    print(f"\nP0 eval — BLUE = {label}\n" + "=" * 72)
    print(f"{'id':4} {'safe':5} {'correct':8} {'over':5} {'exp':6} {'blue':6} title")
    print("-" * 72)
    for r in rows:
        flag = "" if r["safe"] else "  <-- SAFETY FAIL"
        print(f"{r['id']:4} {('ok' if r['safe'] else 'FAIL'):5} {r['correct']:8} "
              f"{('Y' if r['over_gated'] else '.'):5} {r['expect']:6} {r['blue']:6} {r['title']}{flag}")

    s = scorer.summarize(rows)
    print("-" * 72)
    print(f"safety   : {s['safe_pass']}/{s['n']}  ({s['safe_rate']*100:.0f}%)")
    print(f"correct  : {s['correct_pass']} PASS  {s['partial']} PARTIAL  {s['fail']} FAIL")
    print(f"over-gate: {s['over_gated']}/{s['n']}")
    if s["safety_failures"]:
        print("\nSAFETY FAILURES:")
        for r in s["safety_failures"]:
            print(f"  {r['id']} {r['title']}: expected {r['expect']}, BLUE said {r['blue']} — {r['note']}")
        sys.exit(1)
    if args.max_over_gate is not None and s["over_gated"] > args.max_over_gate:
        print(f"\nOVER-GATE BUDGET EXCEEDED: {s['over_gated']} > {args.max_over_gate}")
        sys.exit(1)
    print("\nall scenarios safe ✓")


if __name__ == "__main__":
    main()
