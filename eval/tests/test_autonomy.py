"""Tests for core.autonomy — the customer-set autonomy dial.

The dial is L0..L5 = observe/suggest/gated/bounded-auto/auto/yolo, set per
(workflow x app). resolve() picks: exact (workflow,app) > workflow-wide >
default. Default default is gated (L2).

FAIL CLOSED: a missing or unparseable config resolves EVERYTHING to observe
(L0, reads-only) — a broken config must never widen autonomy. An unknown level
string (typo) resolves to observe for that scope too.
"""
import os
import tempfile
import unittest

from core import autonomy

CONFIG = """
default_level: gated

overrides:
  - workflow: replenishment-to-po
    app: coupa
    level: bounded-auto
    max_value: 10000
    max_qty: 500
    max_count: 5
  - workflow: replenishment-to-po
    app: sap
    level: gated
  - workflow: risk-watch
    level: observe
"""


class Base(unittest.TestCase):
    def cfg(self, text):
        fd, path = tempfile.mkstemp(suffix=".yaml")
        with os.fdopen(fd, "w") as f:
            f.write(text)
        self.addCleanup(os.remove, path)
        return autonomy.load(path)


class TestResolve(Base):
    def test_default_level_for_unknown_workflow(self):
        c = self.cfg(CONFIG)
        r = c.resolve("unknown-wf", "coupa")
        self.assertEqual(r.level, "gated")
        self.assertEqual(r.rank, 2)
        self.assertEqual(r.source, "default")

    def test_exact_workflow_app_override(self):
        r = self.cfg(CONFIG).resolve("replenishment-to-po", "coupa")
        self.assertEqual(r.level, "bounded-auto")
        self.assertEqual(r.rank, 3)
        self.assertEqual(r.limits.max_value, 10000)
        self.assertEqual(r.limits.max_qty, 500)
        self.assertEqual(r.limits.max_count, 5)

    def test_second_app_gets_its_own_level(self):
        r = self.cfg(CONFIG).resolve("replenishment-to-po", "sap")
        self.assertEqual(r.level, "gated")

    def test_workflow_wide_override_applies_to_any_app(self):
        r = self.cfg(CONFIG).resolve("risk-watch", "anything")
        self.assertEqual(r.level, "observe")

    def test_bounded_auto_without_limits_defaults_to_zero(self):
        c = self.cfg(
            "default_level: gated\n"
            "overrides:\n"
            "  - workflow: w\n"
            "    app: coupa\n"
            "    level: bounded-auto\n"
        )
        r = c.resolve("w", "coupa")
        self.assertEqual(r.limits.max_value, 0)  # nothing auto-allowed -> gate

    def test_level_alias_accepts_L_numbers(self):
        c = self.cfg("default_level: L3\n")
        self.assertEqual(c.resolve("x", "y").level, "bounded-auto")


class TestFailClosed(Base):
    def test_missing_file_resolves_observe(self):
        c = autonomy.load("/no/such/config.yaml")
        r = c.resolve("replenishment-to-po", "coupa")
        self.assertEqual(r.level, "observe")
        self.assertEqual(r.rank, 0)
        self.assertTrue(c.fell_back)

    def test_unknown_default_level_falls_to_observe(self):
        c = self.cfg("default_level: turbo\n")
        self.assertEqual(c.resolve("x", "y").level, "observe")

    def test_unknown_override_level_resolves_observe_for_that_scope(self):
        c = self.cfg(
            "default_level: gated\n"
            "overrides:\n"
            "  - workflow: w\n"
            "    app: coupa\n"
            "    level: ludicrous\n"
        )
        self.assertEqual(c.resolve("w", "coupa").level, "observe")
        # other scopes still get the (valid) default
        self.assertEqual(c.resolve("other", "sap").level, "gated")

    def test_quoted_values_are_accepted(self):
        # idiomatic YAML quotes must not silently fail the config closed (DX review)
        c = self.cfg('default_level: "gated"\n')
        self.assertFalse(c.fell_back)
        self.assertEqual(c.default_level, "gated")

    def test_quoted_override_level_and_app(self):
        c = self.cfg(
            "default_level: gated\n"
            "overrides:\n"
            "  - workflow: 'replen'\n"
            "    app: \"coupa\"\n"
            "    level: 'bounded-auto'\n"
        )
        self.assertEqual(c.resolve("replen", "coupa").level, "bounded-auto")

    def test_empty_config_uses_safe_default(self):
        c = self.cfg("# just a comment\n")
        # no default_level declared -> fall back to gated (the documented default)
        self.assertEqual(c.resolve("x", "y").level, "gated")


if __name__ == "__main__":
    unittest.main()
