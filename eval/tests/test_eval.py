"""Regression lock for the P0 eval.

Two things must stay true: our engine decides every scenario safely and
correctly, and the scorer actually BITES (a reckless decision set is reported as
a safety failure, not rubber-stamped).
"""
import importlib.util
import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVAL = os.path.join(ROOT, "eval")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


run = _load("eval_run", os.path.join(EVAL, "run.py"))
score = _load("eval_score", os.path.join(EVAL, "score.py"))


class TestEval(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(EVAL, "scenarios.json")) as f:
            self.scenarios = json.load(f)["scenarios"]

    def test_engine_is_safe_and_correct_on_all_scenarios(self):
        rows = [score.score_one(sc, run.engine_decision(sc)) for sc in self.scenarios]
        s = score.summarize(rows)
        self.assertEqual(s["safe_pass"], s["n"], "a scenario was unsafe")
        self.assertEqual(s["fail"], 0, "a scenario was incorrect")
        self.assertEqual(s["correct_pass"], s["n"], "not every scenario was a clean PASS")

    def test_canonical_anchors_present(self):
        ids = {sc["id"] for sc in self.scenarios}
        self.assertIn("S4", ids)  # injection + big value
        self.assertIn("S9", ids)  # yolo on a real connector

    def test_scorer_bites_on_reckless_blue(self):
        # a BLUE that auto-approves the injection trap and the yolo-on-real case
        reckless = {sc["id"]: "allow" for sc in self.scenarios}
        rows = [score.score_one(sc, reckless[sc["id"]]) for sc in self.scenarios]
        s = score.summarize(rows)
        self.assertGreater(len(s["safety_failures"]), 0)
        failed_ids = {r["id"] for r in s["safety_failures"]}
        self.assertIn("S4", failed_ids)
        self.assertIn("S9", failed_ids)


if __name__ == "__main__":
    unittest.main()
