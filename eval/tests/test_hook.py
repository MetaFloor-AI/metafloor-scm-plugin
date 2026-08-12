"""Tests for core.hook — the PreToolUse adapter that ties the pieces together.

evaluate(event, plugin_root) -> the hook output dict with a permissionDecision
of allow | ask | deny. It classifies the tool, resolves the autonomy level for
the active workflow+app, runs the gate, writes an audit line for governed
writes, and increments the cumulative session total on auto-allow.

FAIL CLOSED: any internal error on a governed connector tool -> deny.
"""
import os
import tempfile
import unittest
from unittest import mock

from core import hook, session, audit

CONFIG = """
default_level: gated
overrides:
  - workflow: replen
    app: coupa
    level: bounded-auto
    max_value: 10000
    max_qty: 500
    max_count: 3
  - workflow: watch
    app: coupa
    level: observe
"""


def perm(out):
    return out["hookSpecificOutput"]["permissionDecision"]


class Base(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.scm = os.path.join(self.root, ".scm")
        self.cfg = os.path.join(self.root, "autonomy.yaml")
        with open(self.cfg, "w") as f:
            f.write(CONFIG)

    def ev(self, tool_name, tool_input=None):
        return {"tool_name": tool_name, "tool_input": tool_input or {}, "cwd": self.root}

    def go(self, tool_name, tool_input=None):
        return hook.evaluate(self.ev(tool_name, tool_input), self.root,
                             config_path=self.cfg, scm_dir=self.scm)


class TestDecisions(Base):
    def test_read_allowed_and_not_audited(self):
        out = self.go("mcp__coupa__list_purchase_orders")
        self.assertEqual(perm(out), "allow")
        ok, _, _ = audit.verify(os.path.join(self.scm, "audit.jsonl"))
        self.assertTrue(ok)
        self.assertFalse(os.path.exists(os.path.join(self.scm, "audit.jsonl")))

    def test_default_gated_write_asks_and_audits(self):
        # no active workflow -> default level (gated)
        out = self.go("mcp__coupa__create_purchase_order", {"total": 500})
        self.assertEqual(perm(out), "ask")
        self.assertTrue(os.path.exists(os.path.join(self.scm, "audit.jsonl")))

    def test_observe_workflow_denies_write(self):
        session.set_active_workflow(self.scm, "watch")
        out = self.go("mcp__coupa__create_purchase_order", {"total": 500})
        self.assertEqual(perm(out), "deny")

    def test_bounded_auto_within_limits_allows_and_counts(self):
        session.set_active_workflow(self.scm, "replen")
        out = self.go("mcp__coupa__create_purchase_order", {"total": 4000, "quantity": 10})
        self.assertEqual(perm(out), "allow")
        value, count = session.get_cumulative(self.scm, "replen", "coupa")
        self.assertEqual(value, 4000)
        self.assertEqual(count, 1)

    def test_bounded_auto_salami_gates_after_budget(self):
        session.set_active_workflow(self.scm, "replen")
        self.assertEqual(perm(self.go("mcp__coupa__create_purchase_order", {"total": 7000})), "allow")
        # cumulative now 7000; another 5000 exceeds 10000 budget -> ask
        self.assertEqual(perm(self.go("mcp__coupa__create_purchase_order", {"total": 5000})), "ask")

    def test_destructive_gates_under_bounded_auto(self):
        session.set_active_workflow(self.scm, "replen")
        out = self.go("mcp__coupa__cancel_purchase_order", {"po": "PO-1"})
        self.assertEqual(perm(out), "ask")

    def test_non_connector_tool_passthrough_allow(self):
        self.assertEqual(perm(self.go("Bash", {"command": "ls"})), "allow")
        self.assertEqual(perm(self.go("mcp__github__create_issue")), "allow")

    def test_unknown_connector_op_denied(self):
        out = self.go("mcp__coupa__wipe_everything", {})
        self.assertEqual(perm(out), "deny")


class TestConnectorOverride(Base):
    def test_customer_mapped_connector_is_governed(self):
        # a real server named 'coupa-prod' with vendor tool names — unmapped it
        # would be non_connector -> ungoverned ALLOW. Mapped, it must be governed.
        import json
        os.makedirs(self.scm, exist_ok=True)
        with open(os.path.join(self.scm, "connectors.json"), "w") as f:
            json.dump({"coupa-prod": {"writes": ["po_create"]}}, f)
        out = hook.evaluate(
            {"tool_name": "mcp__coupa-prod__po_create", "tool_input": {"total": 500},
             "cwd": self.root}, self.root, config_path=self.cfg, scm_dir=self.scm)
        self.assertEqual(perm(out), "ask")  # gated default, governed


class TestGovernedStubAndResiduals(Base):
    """The fail-open fix (declare-to-govern) and the honest residuals it does NOT close.

    These lock in the exact boundary behavior documented in the README safety table, so a
    silent regression trips a test.
    """

    def _connectors(self, obj):
        import json
        os.makedirs(self.scm, exist_ok=True)
        with open(os.path.join(self.scm, "connectors.json"), "w") as f:
            json.dump(obj, f)

    def test_unmapped_app_passes_ungoverned(self):
        # The documented residual: an app with no shipped registry and no declaration is
        # NOT ours to govern -> allow. This is why /scm-connectors surfaces unmapped apps.
        out = self.go("mcp__veeva__approve_capa", {})
        self.assertEqual(perm(out), "allow")

    def test_empty_stub_declaration_makes_unknown_ops_fail_closed(self):
        # The fix: declaring an app with an empty op map makes it KNOWN, so any op we don't
        # recognise classifies unknown -> deny (not the ungoverned allow above).
        self._connectors({"veeva": {}})
        out = self.go("mcp__veeva__approve_capa", {})
        self.assertEqual(perm(out), "deny")

    def test_reads_only_stub_allows_declared_reads_and_gates_the_rest(self):
        self._connectors({"veeva": {"reads": ["get_quality_event"]}})
        self.assertEqual(perm(self.go("mcp__veeva__get_quality_event")), "allow")
        self.assertEqual(perm(self.go("mcp__veeva__approve_capa")), "deny")

    def test_write_misdeclared_as_read_passes_silently(self):
        # HONEST RESIDUAL (eng F4): the customer classifies their own ops. A write they place
        # in `reads` is trusted and passes as a read (reads classify before writes, and the
        # union-merge can't downgrade it). /scm-connectors guards this at SETUP, not runtime.
        # Documented on purpose so any change to the behavior fails this test.
        self._connectors({"coupa": {"reads": ["create_purchase_order"]}})
        out = self.go("mcp__coupa__create_purchase_order", {"total": 999999})
        self.assertEqual(perm(out), "allow")


class TestFailClosed(Base):
    def test_internal_error_on_governed_tool_denies(self):
        with mock.patch("core.hook.gate.decide", side_effect=RuntimeError("boom")):
            out = self.go("mcp__coupa__create_purchase_order", {"total": 1})
        self.assertEqual(perm(out), "deny")

    def test_error_on_non_connector_tool_still_allows(self):
        # a bug in our logic must not block the user's unrelated tools
        with mock.patch("core.hook.gate.decide", side_effect=RuntimeError("boom")):
            out = self.go("Bash", {"command": "ls"})
        self.assertEqual(perm(out), "allow")


if __name__ == "__main__":
    unittest.main()
