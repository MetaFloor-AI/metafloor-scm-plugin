"""Governed-app allowlist + registry-integrity (structural safety findings).

The fail-open the review found: an app-key absent from the registry classifies as
`non_connector` and the gate ALLOWS it (registry.py:classify -> gate.py:44). The
fix is two-part and this file guards both:

  1. Ship the FULL canonical set so the 20 governed apps are known out of the box.
     A dropped manifest silently regresses that app to fail-open, so we assert the
     whole set is present (test_full_canonical_set_present).
  2. A customer declares aliased / unshipped connectors in `.scm/connectors.json`;
     the merge makes them governed, so an unclassified write on them fails CLOSED
     to the gate rather than being allowed.

Plus the two test-integrity gaps the review flagged:
  - the per-app `value_fields` mapping must be LOAD-BEARING (S15 greened on a stub);
  - non-SCM MCP tools (GitHub/Slack) must stay passthrough (the allowlist must not
    over-gate them).
"""
import json
import os
import tempfile
import unittest

from core import gate, registry
from core.registry import Classification
from core.autonomy import Resolution, Limits

_RANK = {"observe": 0, "suggest": 1, "gated": 2, "bounded-auto": 3, "auto": 4, "yolo": 5}

# the 20 apps that ship a canonical manifest — each is a governed SCM connector
_SHIPPED = {
    "anaplan", "ariba", "blueyonder", "coupa", "dynamics365", "fourkites", "infor",
    "ivalua", "jaggaer", "kinaxis", "manhattan", "o9", "oracle", "otm", "project44",
    "salesforce", "sap-ewm", "sap-ibp", "sap", "sap-tm",
}


def res(level, max_value=0, max_qty=0, max_count=0, currency=None):
    return Resolution(level, _RANK[level],
                      Limits(max_value=max_value, max_qty=max_qty, max_count=max_count),
                      "override", currency=currency)


def _scm_with_connectors(mapping):
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "connectors.json"), "w", encoding="utf-8") as f:
        json.dump(mapping, f)
    return d


class TestFullCanonicalSet(unittest.TestCase):
    def test_full_canonical_set_present(self):
        # A dropped manifest = a governed app silently back to fail-open. Guard it.
        missing = _SHIPPED - set(registry.DEFAULT_REGISTRY)
        self.assertEqual(missing, set(), f"governed apps missing a manifest: {missing}")

    def test_basename_equals_app_key(self):
        # the loader keys by filename; a manifest whose `app` disagrees is skipped,
        # so every loaded key must round-trip to its own classification.
        for app in _SHIPPED:
            c = registry.classify(f"mcp__{app}__definitely_not_a_real_op")
            self.assertTrue(c.is_connector, f"{app} did not load as a governed app")


class TestGovernedAppAllowlist(unittest.TestCase):
    def test_declared_alias_write_is_gated_not_allowed(self):
        # a customer's real Coupa server is named `coupa-prod` (not the canonical
        # `coupa`). Declaring it makes it governed -> its write gates, not allows.
        scm = _scm_with_connectors(
            {"coupa-prod": {"writes": ["create_purchase_order"], "currency_field": "currency"}})
        reg = registry.load_registry(scm)
        c = registry.classify("mcp__coupa-prod__create_purchase_order", reg)
        self.assertTrue(c.is_connector)
        self.assertEqual(c.kind, "write")
        self.assertEqual(gate.decide(c, res("gated")).action, "ask")

    def test_declared_app_unclassified_op_fails_closed(self):
        # declaring an app governed (even with only reads) fail-closes any op that
        # is not classified: a write we did not enumerate -> unknown -> deny.
        scm = _scm_with_connectors({"coupa-prod": {"reads": ["get_purchase_order"]}})
        reg = registry.load_registry(scm)
        c = registry.classify("mcp__coupa-prod__create_purchase_order", reg)
        self.assertEqual(c.kind, "unknown")
        self.assertEqual(gate.decide(c, res("bounded-auto", max_value=10**9)).action, "deny")

    def test_undeclared_unshipped_app_is_the_documented_residual(self):
        # HONEST BOUNDARY: an SCM connector that is neither shipped nor declared is
        # indistinguishable from any other MCP server, so it passes. This is the one
        # residual fail-open, surfaced loudly by /scm-connectors at first run — it is
        # asserted here so it stays a known, tested boundary, not a silent surprise.
        c = registry.classify("mcp__acmescm__create_shipment")
        self.assertFalse(c.is_connector)
        self.assertEqual(gate.decide(c, res("gated")).action, "allow")


class TestNonScmPassthrough(unittest.TestCase):
    def test_github_and_slack_writes_pass(self):
        # the allowlist must NOT over-gate non-SCM tools already in use.
        for name in ("mcp__github__create_issue", "mcp__slack__post_message"):
            c = registry.classify(name)
            self.assertFalse(c.is_connector, f"{name} should be non_connector")
            self.assertEqual(gate.decide(c, res("gated")).action, "allow")


class TestValueFieldIsLoadBearing(unittest.TestCase):
    """S15 greened on a stub because `net_value` is already a default and the
    currency guard short-circuits first. This proves a per-app value_fields
    mapping actually flips the decision, so a wrong manifest cannot pass silently."""

    def _cls(self, value_fields):
        return Classification(is_connector=True, app="acme", op="create_order",
                              kind="write", value_fields=value_fields, currency_field="currency")

    def test_custom_value_field_flips_allow_to_ask(self):
        # true value lives ONLY in a non-default field; a small default field decoys.
        payload = {"amount": 50, "contract_value": 999_999, "currency": "USD"}
        limits = dict(max_value=10_000, max_qty=10**9, max_count=99)

        with_field = gate.decide(self._cls(["contract_value"]),
                                 res("bounded-auto", **limits), tool_input=payload)
        without = gate.decide(self._cls(None),
                              res("bounded-auto", **limits), tool_input=payload)

        self.assertEqual(with_field.action, "ask")   # reads the real 999,999 -> over budget
        self.assertEqual(without.action, "allow")     # decoyed by amount=50 -> "within budget"


if __name__ == "__main__":
    unittest.main()
