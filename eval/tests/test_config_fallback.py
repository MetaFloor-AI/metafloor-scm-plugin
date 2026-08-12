"""Phase 0 (P0-A): a fresh install must never auto-approve real spend.

The bug the DX review found: the shipped `config/autonomy.yaml` (which contains a
`bounded-auto, max_value 10000` override) doubled as the RUNTIME FALLBACK. So a
brand-new user who set no dial and ran /scm-replenish auto-approved POs up to $10k.

Fix: the example config is `config/autonomy.example.yaml` (never a fallback). The
runtime fallback is `config/autonomy.default.yaml` — gated-only, no overrides — so
a fresh install asks on every write. Corrupt config still fails closed to L0.
"""
import os
import tempfile
import unittest

from core import hook, session

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def perm(out):
    return out["hookSpecificOutput"]["permissionDecision"]


class TestFreshInstallFallback(unittest.TestCase):
    def setUp(self):
        self.scm = os.path.join(tempfile.mkdtemp(), ".scm")  # no autonomy.yaml here

    def test_fresh_install_gates_the_replenishment_po(self):
        # active workflow set, NO project config, NO explicit config_path ->
        # must fall back to the gated-only default and ASK, not auto-approve.
        session.set_active_workflow(self.scm, "replenishment-to-po")
        out = hook.evaluate(
            {"tool_name": "mcp__coupa__create_purchase_order",
             "tool_input": {"total": 9000}, "cwd": os.path.dirname(self.scm)},
            REPO, scm_dir=self.scm,
        )
        self.assertEqual(perm(out), "ask")

    def test_example_config_is_not_the_runtime_fallback(self):
        path = hook._resolve_config_path(REPO, self.scm)
        self.assertNotIn("autonomy.example.yaml", path)
        self.assertTrue(path.endswith("autonomy.default.yaml"))

    def test_shipped_default_has_no_bounded_auto_override(self):
        from core import autonomy
        cfg = autonomy.load(os.path.join(REPO, "config", "autonomy.default.yaml"))
        self.assertFalse(cfg.fell_back)
        self.assertEqual(cfg.default_level, "gated")
        for o in cfg.overrides:
            self.assertNotEqual(o.get("level"), "bounded-auto")


if __name__ == "__main__":
    unittest.main()
