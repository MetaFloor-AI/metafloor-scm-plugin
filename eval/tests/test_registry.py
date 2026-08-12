"""Tests for core.registry — classifying a connector tool call.

The PreToolUse hook only gets a tool name + input. The registry (maintained per
app pack) is how the plugin knows whether a call is a read, a write, a
destructive/irreversible write, or an outbound data-send. Anything on a known
app that we DON'T recognise is `unknown` — the gate will fail that closed.
Tools on apps we have no pack for are `non_connector` — not ours to govern.
"""
import json
import os
import tempfile
import unittest

from core import registry


class TestClassify(unittest.TestCase):
    def test_read_tool(self):
        c = registry.classify("mcp__coupa__list_purchase_orders")
        self.assertEqual(c.app, "coupa")
        self.assertEqual(c.op, "list_purchase_orders")
        self.assertEqual(c.kind, "read")
        self.assertTrue(c.is_connector)

    def test_write_tool(self):
        c = registry.classify("mcp__coupa__create_purchase_order")
        self.assertEqual(c.kind, "write")

    def test_destructive_tool(self):
        c = registry.classify("mcp__coupa__cancel_purchase_order")
        self.assertEqual(c.kind, "destructive")

    def test_outbound_tool(self):
        c = registry.classify("mcp__coupa__email_supplier")
        self.assertEqual(c.kind, "outbound")

    def test_sap_pack_present(self):
        self.assertEqual(registry.classify("mcp__sap__get_material_stock").kind, "read")
        self.assertEqual(registry.classify("mcp__sap__create_purchase_order").kind, "write")

    def test_unknown_op_on_known_app_is_unknown(self):
        # a write-capable connector op we don't recognise -> gate must fail closed
        c = registry.classify("mcp__coupa__frobnicate_widgets")
        self.assertEqual(c.kind, "unknown")
        self.assertTrue(c.is_connector)

    def test_tool_on_unknown_app_is_non_connector(self):
        c = registry.classify("mcp__github__create_issue")
        self.assertEqual(c.kind, "non_connector")
        self.assertFalse(c.is_connector)

    def test_plain_tool_is_non_connector(self):
        for name in ("Read", "Bash", "Edit"):
            self.assertEqual(registry.classify(name).kind, "non_connector")

    def test_malformed_mcp_name_is_non_connector(self):
        self.assertEqual(registry.classify("mcp__coupa").kind, "non_connector")

    def test_real_connectors_are_not_simulators(self):
        self.assertFalse(registry.classify("mcp__coupa__create_purchase_order").simulator)
        self.assertFalse(registry.classify("mcp__sap__create_purchase_order").simulator)

    def test_injected_registry_can_mark_a_simulator(self):
        sim = {
            "coupa_sim": registry.AppTools(
                simulator=True,
                reads={"get_stock"},
                writes={"create_purchase_order"},
                destructive=set(),
                outbound=set(),
            )
        }
        c = registry.classify("mcp__coupa_sim__create_purchase_order", reg=sim)
        self.assertTrue(c.simulator)
        self.assertEqual(c.kind, "write")


class TestManifestsAndInvariants(unittest.TestCase):
    def test_default_registry_loaded_from_json_manifests(self):
        # coupa + sap come from registry/*.json now, not a hardcoded dict
        self.assertIn("coupa", registry.DEFAULT_REGISTRY)
        self.assertIn("sap", registry.DEFAULT_REGISTRY)

    def test_no_op_appears_in_two_classes(self):
        for app, t in registry.DEFAULT_REGISTRY.items():
            sets = [t.reads, t.writes, t.destructive, t.outbound]
            for i in range(len(sets)):
                for j in range(i + 1, len(sets)):
                    overlap = sets[i] & sets[j]
                    self.assertEqual(overlap, set(), f"{app}: op in two classes: {overlap}")

    def test_domain_irreversible_ops_classified_destructive(self):
        # Domain call (2026-08-12): physical/financial commits must hit the destructive
        # floor (gate below L4), not auto-approve as plain writes under bounded-auto.
        self.assertEqual(registry.classify("mcp__manhattan__ship_order").kind, "destructive")
        self.assertEqual(registry.classify("mcp__otm__issue_voucher").kind, "destructive")
        self.assertEqual(registry.classify("mcp__otm__settle_freight").kind, "destructive")

    def test_destructive_named_ops_are_classified_destructive(self):
        # the exact Eng finding: cancel/delete/reverse/... must NOT sit in `writes`
        # (else the destructive floor never fires under bounded-auto)
        DANGER = ("cancel", "delete", "reverse", "deactivate", "block", "void", "close", "remove")
        for app, t in registry.DEFAULT_REGISTRY.items():
            for op in t.writes:
                self.assertFalse(
                    any(w in op for w in DANGER),
                    f"{app}.{op} looks destructive but is in `writes` — floor would be bypassed",
                )


class TestCustomerOverride(unittest.TestCase):
    def _connectors(self, obj):
        scm = os.path.join(tempfile.mkdtemp(), ".scm")
        os.makedirs(scm)
        with open(os.path.join(scm, "connectors.json"), "w") as f:
            json.dump(obj, f)
        return scm

    def test_maps_a_real_connector_with_different_prefix(self):
        # customer's real server is 'coupa-prod' with vendor tool names
        scm = self._connectors({
            "coupa-prod": {"reads": ["fetch_po"], "writes": ["po_create"],
                           "destructive": ["po_cancel"], "outbound": []}
        })
        reg = registry.load_registry(scm)
        self.assertEqual(registry.classify("mcp__coupa-prod__po_create", reg=reg).kind, "write")
        self.assertEqual(registry.classify("mcp__coupa-prod__po_cancel", reg=reg).kind, "destructive")
        self.assertEqual(registry.classify("mcp__coupa-prod__fetch_po", reg=reg).kind, "read")

    def test_extends_a_known_app_with_a_real_read_name(self):
        # a real Coupa read whose name isn't canonical was denied; mapping fixes it
        self.assertEqual(registry.classify("mcp__coupa__po_fetch").kind, "unknown")
        scm = self._connectors({"coupa": {"reads": ["po_fetch"]}})
        reg = registry.load_registry(scm)
        self.assertEqual(registry.classify("mcp__coupa__po_fetch", reg=reg).kind, "read")

    def test_missing_connectors_file_returns_canonical(self):
        reg = registry.load_registry(os.path.join(tempfile.mkdtemp(), ".scm"))
        self.assertEqual(registry.classify("mcp__coupa__create_purchase_order", reg=reg).kind, "write")

    def test_corrupt_connectors_file_does_not_crash_and_stays_canonical(self):
        scm = os.path.join(tempfile.mkdtemp(), ".scm")
        os.makedirs(scm)
        with open(os.path.join(scm, "connectors.json"), "w") as f:
            f.write("{ not json")
        reg = registry.load_registry(scm)  # must not raise
        self.assertEqual(registry.classify("mcp__coupa__po_fetch", reg=reg).kind, "unknown")


if __name__ == "__main__":
    unittest.main()
