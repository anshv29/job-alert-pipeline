import os
import unittest
from unittest import mock

from jobalert import filters, llm, pipeline
from jobalert.settings import load_settings


def use_preset(name):
    """Point the program at one preset for the duration of a test."""
    import jobalert.settings as s

    s._settings = load_settings(preset_override=name)
    filters._matcher = None


class FinancePresetTest(unittest.TestCase):
    def setUp(self):
        use_preset("finance")

    def test_finance_roles_pass(self):
        titles = [
            "2027 Summer Analyst, Investment Banking",
            "Summer 2027 Sales & Trading Internship",
            "Equity Research Summer Associate 2027",
            "2027 Asset Management Co-op",
            "Winter 2027 Risk Management Intern",
            "Wealth Management Summer Internship 2027",
            "Corporate Finance Intern (Summer 2027)",
            "Capital Markets Summer Analyst Program 2027",
            "Accounting Intern, Summer 2027",
            "Business Analyst Co-op, Summer 2027",
        ]
        for title in titles:
            self.assertTrue(filters.is_relevant(title, ""), title)

    def test_student_word_only_counts_in_title(self):
        self.assertTrue(filters.is_relevant("Student, Financial Analyst (Summer 2027)", ""))
        self.assertFalse(filters.is_relevant("Financial Analyst", "Summer 2027. Student loans are offered to staff."))

    def test_french_title(self):
        self.assertTrue(filters.is_relevant("Stagiaire en finance, été 2027", "finance 2027"))

    def test_rejects_wrong_year_senior_and_unrelated(self):
        self.assertFalse(filters.is_relevant("Summer 2025 Investment Banking Analyst", "intern"))
        self.assertFalse(filters.is_relevant("Senior Vice President, Capital Markets 2027", "intern"))
        self.assertFalse(filters.is_relevant("Barista Intern 2027", "coffee"))
        self.assertFalse(filters.is_relevant("International Equity Trader", "2027 desk"))

    def test_word_boundaries(self):
        self.assertFalse(filters.is_relevant("Cooperation Lead 2027", "bank"))


class LocationTest(unittest.TestCase):
    def test_exclude_locations(self):
        use_preset("finance")
        from jobalert.settings import get_settings

        get_settings()["exclude_locations"] = ["hong kong", "london"]
        self.assertTrue(filters.in_excluded_location({"location": "London, United Kingdom"}))
        self.assertFalse(filters.in_excluded_location({"location": "Toronto, Ontario"}))
        get_settings()["exclude_locations"] = []
        self.assertFalse(filters.in_excluded_location({"location": "London"}))


class TechPresetTest(unittest.TestCase):
    def setUp(self):
        use_preset("tech")

    def test_tech_roles(self):
        self.assertTrue(filters.is_relevant("Software Engineer Intern, Summer 2027", ""))
        self.assertTrue(filters.is_relevant("Machine Learning Intern 2027", ""))
        self.assertFalse(filters.is_relevant("Investment Banking Summer Analyst 2027", ""))


class NoApiKeyTest(unittest.TestCase):
    def setUp(self):
        use_preset("finance")

    def test_runs_without_key(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
            self.assertFalse(llm.enabled())
            self.assertIn("keyword filter only", llm.describe_mode())
            result = llm.classify_job({"title": "x", "description": "y"})
            self.assertTrue(result["error"])
            self.assertTrue(llm.passes_gate(result))  # keyword-only: never dropped by a missing AI


class ConfigTest(unittest.TestCase):
    def test_both_presets_load(self):
        for name in ("finance", "tech"):
            s = load_settings(preset_override=name)
            self.assertTrue(s["roles"])
            self.assertTrue(s["companies"]["workday"])


if __name__ == "__main__":
    unittest.main()
