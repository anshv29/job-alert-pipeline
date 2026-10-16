import os
import tempfile
import types
import unittest
from unittest import mock

from jobalert import digest, filters, llm, pipeline
from tests.test_filters import use_preset


def fake_source(jobs):
    return types.SimpleNamespace(fetch=lambda company: iter([dict(j) for j in jobs]))


def job(i, title, company="Fake Bank", description="Summer 2027 program in investment banking. Intern."):
    return {"id": f"fake-{i}", "title": title, "company": company, "location": "Toronto",
            "url": f"https://example.com/job/{i}", "description": description, "posted": "2026-10-01"}


JOBS = [
    job(1, "2027 Summer Analyst, Investment Banking"),
    job(2, "Barista", description="coffee"),
    job(3, "Senior Vice President, Capital Markets 2027"),
]

ENV = {"EMAIL_ADDRESS": "sender@example.com", "EMAIL_APP_PASSWORD": "abcd efgh ijkl mnop",
       "RECIPIENT_EMAIL": "me@example.com", "ANTHROPIC_API_KEY": ""}


class PipelineBase(unittest.TestCase):
    def setUp(self):
        use_preset("finance")
        from jobalert.settings import get_settings

        s = get_settings()
        s["sources"] = {"greenhouse": True, "simplify": False}
        s["alerts"] = {"send_backlog_on_first_run": True}  # most tests exercise normal alerts
        s["companies"] = {k: [] for k in s["companies"]}
        s["companies"]["greenhouse"] = [{"name": "Fake Bank", "slug": "x"}]
        self.tmp = tempfile.TemporaryDirectory()
        self.old_cwd = os.getcwd()
        os.chdir(self.tmp.name)
        self.addCleanup(self.cleanup)

    def cleanup(self):
        os.chdir(self.old_cwd)
        self.tmp.cleanup()

    def run_pipeline(self, jobs, **kwargs):
        sent = []
        smtp = mock.MagicMock()
        smtp.__enter__.return_value.send_message.side_effect = lambda m: sent.append(m)
        connectors = (("greenhouse", fake_source(jobs)),)
        with mock.patch.dict(os.environ, ENV), mock.patch.object(pipeline, "CONNECTORS", connectors), \
                mock.patch("jobalert.emailer.smtplib.SMTP", return_value=smtp):
            result = pipeline.run(**kwargs)
        return result, sent


class PipelineTest(PipelineBase):
    def test_sends_one_email_once_without_api_key(self):
        result, sent = self.run_pipeline(JOBS)
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0]["To"], "me@example.com")
        self.assertIn("1 new job", sent[0]["Subject"])
        self.assertEqual([j["id"] for j in result["jobs"]], ["fake-1"])
        again, sent_again = self.run_pipeline(JOBS)
        self.assertEqual(sent_again, [])
        self.assertEqual(again["sent"], 0)

    def test_dry_run_sends_and_remembers_nothing(self):
        result, sent = self.run_pipeline(JOBS, dry_run=True)
        self.assertEqual(sent, [])
        self.assertEqual(len(result["jobs"]), 1)
        again, sent_again = self.run_pipeline(JOBS)
        self.assertEqual(len(sent_again), 1)

    def test_same_job_on_two_career_sites_is_one_alert(self):
        twin = dict(JOBS[0], id="fake-99", url="https://example.com/other")
        result, sent = self.run_pipeline([JOBS[0], twin])
        self.assertEqual(len(result["jobs"]), 1)

    def test_failed_email_does_not_lose_jobs(self):
        smtp = mock.MagicMock()
        smtp.__enter__.return_value.send_message.side_effect = OSError("network down")
        with mock.patch.dict(os.environ, ENV), mock.patch.object(pipeline, "CONNECTORS", (("greenhouse", fake_source(JOBS)),)), \
                mock.patch("jobalert.emailer.smtplib.SMTP", return_value=smtp):
            with self.assertRaises(OSError):
                pipeline.run()
        result, sent = self.run_pipeline(JOBS)
        self.assertEqual(len(sent), 1)

    def test_missing_secrets_gives_plain_message(self):
        with mock.patch.dict(os.environ, {"EMAIL_ADDRESS": "", "EMAIL_APP_PASSWORD": ""}):
            with self.assertRaises(SystemExit) as ctx:
                pipeline.run()
        self.assertIn("EMAIL_ADDRESS", str(ctx.exception))

    def test_with_api_key_ai_can_remove_jobs_and_errors_keep_them(self):
        def reply(text):
            client = mock.MagicMock()
            client.messages.create.return_value = types.SimpleNamespace(
                content=[types.SimpleNamespace(type="text", text=text)])
            return client

        env = dict(ENV, ANTHROPIC_API_KEY="sk-ant-test")
        with mock.patch.dict(os.environ, env):
            with mock.patch.object(llm, "_get_client", return_value=reply(
                    "ANSWER: NO\nREASON: not finance\nDOMAIN: None\nGRAD_RESTRICTION: none")):
                self.assertFalse(llm.passes_gate(llm.classify_job(JOBS[0])))
            with mock.patch.object(llm, "_get_client", return_value=reply(
                    "ANSWER: YES\nREASON: ib\nDOMAIN: Investment Banking\nGRAD_RESTRICTION: none")):
                c = llm.classify_job(JOBS[0])
                self.assertTrue(llm.passes_gate(c))
                self.assertEqual(c["domain"], "Investment Banking")
            broken = mock.MagicMock()
            broken.messages.create.side_effect = RuntimeError("out of credit")
            with mock.patch.object(llm, "_get_client", return_value=broken):
                self.assertTrue(llm.passes_gate(llm.classify_job(JOBS[0])))


class FirstRunBaselineTest(PipelineBase):
    def setUp(self):
        super().setUp()
        from jobalert.settings import get_settings

        get_settings()["alerts"] = {}  # the default: do not email the backlog

    def test_first_run_sends_only_a_setup_email_then_alerts_new_jobs(self):
        result, sent = self.run_pipeline(JOBS)
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0]["Subject"], "Job alerts are set up and working")
        self.assertTrue(result["setup_email"])
        self.assertEqual(result["jobs"], [])
        body = sent[0].get_payload()[0].get_payload(decode=True).decode()
        self.assertNotIn("Summer Analyst", body)  # the backlog is not listed

        again, sent_again = self.run_pipeline(JOBS)  # nothing new
        self.assertEqual(sent_again, [])

        newer = JOBS + [job(7, "2027 Equity Research Summer Analyst")]
        later, sent_later = self.run_pipeline(newer)  # a posting that appears after setup
        self.assertEqual([j["id"] for j in later["jobs"]], ["fake-7"])
        self.assertEqual(len(sent_later), 1)
        self.assertIn("1 new job", sent_later[0]["Subject"])

    def test_setup_email_is_only_sent_once(self):
        self.run_pipeline(JOBS)
        _, sent = self.run_pipeline(JOBS)
        self.assertEqual(sent, [])

    def test_first_run_makes_no_ai_calls(self):
        client = mock.MagicMock()
        env = dict(ENV, ANTHROPIC_API_KEY="sk-ant-test")
        smtp = mock.MagicMock()
        with mock.patch.dict(os.environ, env), mock.patch.object(llm, "_get_client", return_value=client), \
                mock.patch.object(pipeline, "CONNECTORS", (("greenhouse", fake_source(JOBS)),)), \
                mock.patch("jobalert.emailer.smtplib.SMTP", return_value=smtp):
            pipeline.run()
        client.messages.create.assert_not_called()

    def test_dry_run_still_previews_matches_on_first_run(self):
        result, sent = self.run_pipeline(JOBS, dry_run=True)
        self.assertEqual(sent, [])
        self.assertEqual(len(result["jobs"]), 1)

    def test_failed_setup_email_retries_baseline_next_time(self):
        smtp = mock.MagicMock()
        smtp.__enter__.return_value.send_message.side_effect = OSError("down")
        with mock.patch.dict(os.environ, ENV), mock.patch.object(pipeline, "CONNECTORS", (("greenhouse", fake_source(JOBS)),)), \
                mock.patch("jobalert.emailer.smtplib.SMTP", return_value=smtp):
            with self.assertRaises(OSError):
                pipeline.run()
        _, sent = self.run_pipeline(JOBS)
        self.assertEqual(sent[0]["Subject"], "Job alerts are set up and working")


class DigestTest(unittest.TestCase):
    def setUp(self):
        use_preset("finance")

    def test_escapes_html_and_groups(self):
        subject, body = digest.build_email([job(1, "<script>x</script> Intern 2027", company="A & B")])
        self.assertNotIn("<script>", body)
        self.assertIn("A &amp; B", body)
        self.assertIn("1 new job ", subject)

    def test_chunks_large_lists(self):
        self.assertEqual(len(digest.chunk(list(range(250)))), 3)
        self.assertEqual(len(digest.chunk(list(range(100)))), 1)


if __name__ == "__main__":
    unittest.main()
