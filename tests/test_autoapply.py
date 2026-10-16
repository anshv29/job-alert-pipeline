import unittest

from autoapply import rules
from autoapply.ats import detect_ats
from jobalert.settings import get_settings
from tests.test_filters import use_preset

GOOD = {"error": False, "answer": True, "reason": "fits", "domain": "SWE", "grad_restriction": "none"}


class RulesTest(unittest.TestCase):
    def setUp(self):
        use_preset("tech")
        get_settings()["grad_year"] = 2029

    def job(self, **kw):
        return dict({"title": "Software Intern", "company": "Acme", "description": "Build things.", "has_full_text": True}, **kw)

    def test_eligible(self):
        r = rules.evaluate(self.job(), GOOD, "greenhouse")
        self.assertEqual(r["status"], "eligible")

    def test_blocklisted_company(self):
        r = rules.evaluate(self.job(company="Google"), GOOD, "greenhouse")
        self.assertEqual(r["status"], "filtered_out")

    def test_workday_goes_to_review(self):
        r = rules.evaluate(self.job(), GOOD, "workday")
        self.assertEqual(r["status"], "needs_review")

    def test_grad_year_before_yours_is_filtered_out(self):
        r = rules.evaluate(self.job(description="Open to students in the class of 2027."), GOOD, "greenhouse")
        self.assertEqual(r["status"], "filtered_out")

    def test_grad_year_equal_or_after_yours_is_fine(self):
        r = rules.evaluate(self.job(description="Class of 2029 or 2030 welcome."), GOOD, "greenhouse")
        self.assertEqual(r["status"], "eligible")

    def test_unwanted_domain_and_ai_failure(self):
        r = rules.evaluate(self.job(), dict(GOOD, domain="Finance"), "greenhouse")
        self.assertEqual(r["status"], "filtered_out")
        r = rules.evaluate(self.job(), {"error": True}, "greenhouse")
        self.assertEqual(r["status"], "needs_review")

    def test_finance_domains(self):
        use_preset("finance")
        r = rules.evaluate(self.job(), dict(GOOD, domain="Investment Banking"), "lever")
        self.assertEqual(r["status"], "eligible")

    def test_detect_ats(self):
        self.assertEqual(detect_ats("https://td.wd3.myworkdayjobs.com/en-US/x/job/y"), "workday")
        self.assertEqual(detect_ats("https://job-boards.greenhouse.io/a/jobs/1"), "greenhouse")


if __name__ == "__main__":
    unittest.main()
