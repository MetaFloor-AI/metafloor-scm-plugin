"""Tests for core.gate — the deterministic decision engine.

Given a tool classification (from registry) and a resolved autonomy level (from
the dial), decide allow | ask | deny. The gate NEVER reads the model's opinion;
its inputs are all code/config-derived. Contract:

  reads / non-connector      -> allow
  unknown connector tool     -> deny (fail closed)
  writes, by level:
    L0 observe / L1 suggest  -> deny  (agent proposes, human executes)
    L2 gated                 -> ask
    L3 bounded-auto          -> allow within $/qty/count + cumulative cap; else ask
    L4 auto                  -> allow (audit after)
    L5 yolo                  -> allow on a simulator; deny on a real connector
  floors (below L4):
    destructive write        -> ask   (irreversible, even if tiny)
    outbound-with-data       -> ask   (gates through L4 too; only yolo/sim allows)
"""
import unittest

from core import gate
from core.registry import Classification
from core.autonomy import Resolution, Limits

_RANK = {"observe": 0, "suggest": 1, "gated": 2, "bounded-auto": 3, "auto": 4, "yolo": 5}


def cls(kind, simulator=False, app="coupa", currency_field="currency"):
    is_conn = kind not in ("non_connector",)
    return Classification(is_connector=is_conn, app=app, op="op", kind=kind,
                          simulator=simulator, currency_field=currency_field)


def res(level, max_value=0, max_qty=0, max_count=0, currency=None):
    return Resolution(level, _RANK[level],
                      Limits(max_value=max_value, max_qty=max_qty, max_count=max_count),
                      "override", currency=currency)


class TestReadsAndUnknown(unittest.TestCase):
    def test_read_allowed_at_lowest_level(self):
        self.assertEqual(gate.decide(cls("read"), res("observe")).action, "allow")

    def test_non_connector_passes_through(self):
        self.assertEqual(gate.decide(cls("non_connector"), res("gated")).action, "allow")

    def test_unknown_tool_denied_even_at_yolo(self):
        d = gate.decide(cls("unknown", simulator=True), res("yolo"))
        self.assertEqual(d.action, "deny")


class TestLevelTableForPlainWrites(unittest.TestCase):
    def test_observe_denies_write(self):
        self.assertEqual(gate.decide(cls("write"), res("observe")).action, "deny")

    def test_suggest_denies_write(self):
        self.assertEqual(gate.decide(cls("write"), res("suggest")).action, "deny")

    def test_gated_asks(self):
        self.assertEqual(gate.decide(cls("write"), res("gated")).action, "ask")

    def test_auto_allows(self):
        self.assertEqual(gate.decide(cls("write"), res("auto")).action, "allow")

    def test_yolo_allows_on_simulator(self):
        d = gate.decide(cls("write", simulator=True), res("yolo"))
        self.assertEqual(d.action, "allow")

    def test_yolo_refuses_real_connector(self):
        d = gate.decide(cls("write", simulator=False), res("yolo"))
        self.assertEqual(d.action, "deny")
        self.assertIn("real", d.reason.lower())


class TestFloors(unittest.TestCase):
    def test_destructive_gates_at_bounded_auto(self):
        d = gate.decide(cls("destructive"), res("bounded-auto", max_value=10**9))
        self.assertEqual(d.action, "ask")
        self.assertIn("destructive", d.rule)

    def test_destructive_allowed_at_auto(self):
        # L4 is explicit high-trust: executes freely in-workflow
        self.assertEqual(gate.decide(cls("destructive"), res("auto")).action, "allow")

    def test_outbound_gates_even_at_auto(self):
        d = gate.decide(cls("outbound"), res("auto"))
        self.assertEqual(d.action, "ask")
        self.assertIn("outbound", d.rule)

    def test_outbound_allowed_only_on_yolo_simulator(self):
        self.assertEqual(
            gate.decide(cls("outbound", simulator=True), res("yolo")).action, "allow")


class TestBoundedAuto(unittest.TestCase):
    def test_within_limits_allows(self):
        d = gate.decide(cls("write"), res("bounded-auto", max_value=10000, max_qty=500, max_count=5),
                        tool_input={"total": 5000, "quantity": 100})
        self.assertEqual(d.action, "allow")

    def test_over_value_asks(self):
        d = gate.decide(cls("write"), res("bounded-auto", max_value=10000, max_qty=500, max_count=5),
                        tool_input={"total": 20000, "quantity": 100})
        self.assertEqual(d.action, "ask")
        self.assertIn("value", d.rule)

    def test_over_qty_asks(self):
        d = gate.decide(cls("write"), res("bounded-auto", max_value=10000, max_qty=500, max_count=5),
                        tool_input={"total": 100, "quantity": 999})
        self.assertEqual(d.action, "ask")
        self.assertIn("qty", d.rule)

    def test_cumulative_value_salami_asks(self):
        # single write small, but session total pushes over the budget
        d = gate.decide(cls("write"), res("bounded-auto", max_value=10000, max_qty=500, max_count=99),
                        tool_input={"total": 5000, "quantity": 10}, cumulative_value=8000)
        self.assertEqual(d.action, "ask")
        self.assertIn("cumulative", d.rule)

    def test_over_count_asks(self):
        d = gate.decide(cls("write"), res("bounded-auto", max_value=10**9, max_qty=10**9, max_count=3),
                        tool_input={"total": 1, "quantity": 1}, cumulative_count=3)
        self.assertEqual(d.action, "ask")
        self.assertIn("count", d.rule)

    def test_currency_mismatch_gates(self):
        d = gate.decide(cls("write"), res("bounded-auto", max_value=10**9, max_qty=10**9, max_count=9, currency="USD"),
                        tool_input={"total": 500, "currency": "JPY"})
        self.assertEqual(d.action, "ask")
        self.assertIn("currency", d.rule)

    def test_matching_currency_allows(self):
        d = gate.decide(cls("write"), res("bounded-auto", max_value=10000, max_qty=500, max_count=9, currency="USD"),
                        tool_input={"total": 500, "currency": "USD"})
        self.assertEqual(d.action, "allow")

    def test_unknown_value_fails_closed_to_ask(self):
        # can't confirm the value from the input -> must not auto
        d = gate.decide(cls("write"), res("bounded-auto", max_value=10000, max_qty=500, max_count=5),
                        tool_input={"note": "no value field here"})
        self.assertEqual(d.action, "ask")


if __name__ == "__main__":
    unittest.main()
