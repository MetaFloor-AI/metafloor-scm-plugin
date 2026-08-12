"""Tests for core.session — the .scm/ working state.

- session.json: which workflow is active (a command/skill sets it). It EXPIRES:
  a stale marker must not keep applying an old workflow's dial to unrelated work.
- state.json: cumulative blast-radius, namespaced per (workflow, app) so two
  workflows running in one Claude session don't leak budget into each other
  (the Eng review's concurrent-workflow bug).

FAIL CLOSED: a corrupt state file returns an effectively-infinite cumulative so
L3 gates rather than under-counting.
"""
import math
import os
import tempfile
import unittest

from core import session


class Base(unittest.TestCase):
    def setUp(self):
        self.scm = os.path.join(tempfile.mkdtemp(), ".scm")


class TestActiveWorkflow(Base):
    def test_roundtrip_fresh(self):
        session.set_active_workflow(self.scm, "replenishment-to-po", now=1000.0)
        self.assertEqual(session.active_workflow(self.scm, now=1000.0), "replenishment-to-po")

    def test_missing_is_none(self):
        self.assertIsNone(session.active_workflow(self.scm))

    def test_corrupt_session_is_none(self):
        os.makedirs(self.scm)
        with open(os.path.join(self.scm, "session.json"), "w") as f:
            f.write("{ not json")
        self.assertIsNone(session.active_workflow(self.scm))

    def test_stale_marker_expires(self):
        session.set_active_workflow(self.scm, "replenishment-to-po", now=1000.0)
        # far in the future, past the TTL -> the stale workflow no longer applies
        self.assertIsNone(session.active_workflow(self.scm, now=1000.0 + 10**6))


class TestCumulativeNamespacing(Base):
    def test_missing_state_is_zero(self):
        self.assertEqual(session.get_cumulative(self.scm, "wf", "coupa"), (0.0, 0))

    def test_accumulates_per_key(self):
        session.record_commit(self.scm, "wf", "coupa", 5000, count=1)
        session.record_commit(self.scm, "wf", "coupa", 2500, count=1)
        self.assertEqual(session.get_cumulative(self.scm, "wf", "coupa"), (7500, 2))

    def test_budgets_do_not_leak_across_workflow_or_app(self):
        session.record_commit(self.scm, "replen", "coupa", 8000)
        session.record_commit(self.scm, "risk", "sap", 3000)
        self.assertEqual(session.get_cumulative(self.scm, "replen", "coupa")[0], 8000)
        self.assertEqual(session.get_cumulative(self.scm, "risk", "sap")[0], 3000)
        # different app under the same workflow is isolated
        self.assertEqual(session.get_cumulative(self.scm, "replen", "sap"), (0.0, 0))

    def test_reset_clears_all(self):
        session.record_commit(self.scm, "wf", "coupa", 5000)
        session.reset(self.scm)
        self.assertEqual(session.get_cumulative(self.scm, "wf", "coupa"), (0.0, 0))

    def test_corrupt_state_fails_closed_to_infinite(self):
        os.makedirs(self.scm)
        with open(os.path.join(self.scm, "state.json"), "w") as f:
            f.write("garbage{")
        value, _ = session.get_cumulative(self.scm, "wf", "coupa")
        self.assertTrue(math.isinf(value))


if __name__ == "__main__":
    unittest.main()
