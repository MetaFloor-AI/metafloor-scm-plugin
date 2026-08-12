"""Tests for core.audit — the hash-chained, tamper-evident audit log.

Every gated/executed action is appended as one JSON line, each carrying the
prior line's hash. Editing, reordering, or dropping any past line breaks the
chain, so `verify()` catches after-the-fact tampering. (Honest v1 limit: a
local file; true immutability needs a server sink.)
"""
import json
import os
import tempfile
import unittest

from core import audit


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "sub", "audit.jsonl")  # sub/ must be created

    def _lines(self):
        with open(self.path) as f:
            return [l for l in f.read().splitlines() if l.strip()]


class TestAppendAndVerify(Base):
    def test_append_creates_file_and_returns_record(self):
        rec = audit.append(self.path, {"tool": "create_po", "decision": "ask"})
        self.assertEqual(rec["tool"], "create_po")
        self.assertIn("hash", rec)
        self.assertIn("prev", rec)
        self.assertIn("ts", rec)
        self.assertTrue(os.path.exists(self.path))

    def test_first_record_links_to_genesis(self):
        rec = audit.append(self.path, {"a": 1})
        self.assertEqual(rec["prev"], audit.GENESIS)

    def test_chain_links_across_records(self):
        r1 = audit.append(self.path, {"a": 1})
        r2 = audit.append(self.path, {"a": 2})
        self.assertEqual(r2["prev"], r1["hash"])

    def test_verify_ok_on_clean_log(self):
        for i in range(4):
            audit.append(self.path, {"i": i})
        ok, idx, _ = audit.verify(self.path)
        self.assertTrue(ok)
        self.assertIsNone(idx)

    def test_verify_ok_on_missing_file(self):
        ok, idx, _ = audit.verify(os.path.join(self.dir, "nope.jsonl"))
        self.assertTrue(ok)


class TestTamperDetection(Base):
    def _seed(self, n=4):
        for i in range(n):
            audit.append(self.path, {"i": i, "amount": i * 100})

    def test_edited_payload_breaks_chain(self):
        self._seed()
        lines = self._lines()
        rec = json.loads(lines[1])
        rec["amount"] = 999999  # tamper without recomputing hash
        lines[1] = json.dumps(rec)
        with open(self.path, "w") as f:
            f.write("\n".join(lines) + "\n")
        ok, idx, reason = audit.verify(self.path)
        self.assertFalse(ok)
        self.assertEqual(idx, 1)

    def test_dropped_line_breaks_chain(self):
        self._seed()
        lines = self._lines()
        del lines[2]  # remove a record -> next prev no longer matches
        with open(self.path, "w") as f:
            f.write("\n".join(lines) + "\n")
        ok, idx, reason = audit.verify(self.path)
        self.assertFalse(ok)

    def test_forged_hash_breaks_chain(self):
        self._seed()
        lines = self._lines()
        rec = json.loads(lines[0])
        rec["hash"] = "f" * 64
        lines[0] = json.dumps(rec)
        with open(self.path, "w") as f:
            f.write("\n".join(lines) + "\n")
        ok, idx, reason = audit.verify(self.path)
        self.assertFalse(ok)
        self.assertEqual(idx, 0)


if __name__ == "__main__":
    unittest.main()
