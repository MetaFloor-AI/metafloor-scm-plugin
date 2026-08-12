"""Tests for core.values — one shared money-value/quantity/currency extractor.

The Eng review found the value read was a global flat first-match lookup,
duplicated in gate.py and hook.py (so the audited value and the gated value
could diverge), and blind to nesting and currency. This module is the single
source: per-app candidate fields (dotted paths allowed) + a currency reader.
"""
import unittest

from core import values


class TestExtract(unittest.TestCase):
    def test_flat_fields(self):
        v, q = values.extract({"total": 5000, "quantity": 10}, ["total"], ["quantity"])
        self.assertEqual(v, 5000.0)
        self.assertEqual(q, 10.0)

    def test_dotted_path(self):
        v, _ = values.extract({"header": {"net_value": 7000}}, ["header.net_value"], [])
        self.assertEqual(v, 7000.0)

    def test_first_present_candidate_wins(self):
        v, _ = values.extract({"grand_total": 900}, ["total", "grand_total"], [])
        self.assertEqual(v, 900.0)

    def test_missing_is_none(self):
        v, q = values.extract({"note": "x"}, ["total"], ["quantity"])
        self.assertIsNone(v)
        self.assertIsNone(q)

    def test_non_numeric_is_none(self):
        v, _ = values.extract({"total": "not-a-number"}, ["total"], [])
        self.assertIsNone(v)

    def test_defaults_used_when_no_fields_given(self):
        v, q = values.extract({"amount": 42, "qty": 3})
        self.assertEqual(v, 42.0)
        self.assertEqual(q, 3.0)


class TestCurrency(unittest.TestCase):
    def test_reads_currency(self):
        self.assertEqual(values.currency_of({"currency": "JPY"}, "currency"), "JPY")

    def test_missing_currency_is_none(self):
        self.assertIsNone(values.currency_of({"total": 1}, "currency"))


if __name__ == "__main__":
    unittest.main()
