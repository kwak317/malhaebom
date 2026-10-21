import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from tests.test_saramin_recommendation import posting_fixture
from app.services.saramin_recommendation import SaraminPostingVerifier

class JobSourceRejectionsTest(unittest.TestCase):
    def test_jobkorea_explicit_unspecified_experience_is_entry_level(self):
        import httpx
        today = datetime(2026, 10, 4, tzinfo=ZoneInfo("Asia/Seoul"))
        url, markup = posting_fixture("jobkorea", experience="무관", deadline="2026-11-01")
        verifier = SaraminPostingVerifier(httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, text=markup))))
        result, reason = verifier.verify_with_reason(url, today=today)
        self.assertEqual(reason, "verified")
        self.assertEqual(result[4], "경력무관")
        for experience in ("경력 3년", "신입 제외"):
            _, bad = posting_fixture("jobkorea", experience=experience, deadline="2026-11-01")
            verifier = SaraminPostingVerifier(httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, text=bad))))
            self.assertEqual(verifier.verify_with_reason(url, today=today), (None, "experience"))
        verifier = SaraminPostingVerifier(httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(403))))
        self.assertEqual(verifier.verify_with_reason(url, today=today), (None, "http_status"))
