import json
import unittest
import urllib.error
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from evals import run_github_job_fit_comparison as runner


README = "Java 17\nSpring Boot 3.3+\nMySQL 8.0+\nspring-boot-starter-data-redis"


def valid_result() -> dict:
    verified = {"Java": "Java 17", "Spring Boot": "Spring Boot 3.3+", "MySQL": "MySQL 8.0+", "Redis": "spring-boot-starter-data-redis"}
    return {
        "verified_technologies": list(verified),
        "job_stack_comparison": [
            {"technology": tech, "status": "verified_in_readme" if tech in verified else "not_verified_in_readme", "evidence_quote": verified.get(tech), "reason": "README 원문에 명시됨" if tech in verified else "README 기준 미확인"}
            for tech in runner.JOB_STACK
        ],
        "recommended_skills": [{"technology": "Docker", "reason": "README 기준 미확인", "next_step": "Docker 실행 절차를 문서화하세요."}],
        "clarifying_question": "Docker를 어떤 방식으로 사용했나요?",
    }


class GithubJobFitFallbackTests(unittest.TestCase):
    def test_default_run_does_not_make_network_calls(self) -> None:
        with patch("sys.argv", ["runner.py"]), patch.object(runner, "fetch_readme") as fetch_readme:
            with redirect_stdout(StringIO()) as output:
                runner.main()
        fetch_readme.assert_not_called()
        planned = json.loads(output.getvalue())
        self.assertEqual(planned["default_model"], runner.DEFAULT_MODEL)
        self.assertEqual(planned["fallback_model"], runner.FALLBACK_MODEL)

    def test_uses_gemini_when_terra_rate_limited(self) -> None:
        rate_limit = urllib.error.HTTPError("https://example.test", 429, "Too Many Requests", {}, None)
        with patch.object(runner, "call_model", side_effect=[rate_limit, (valid_result(), 1.0, 0.01)]):
            model, result, elapsed, cost = runner.call_with_fallback(README)
        self.assertEqual(model, runner.FALLBACK_MODEL)
        self.assertEqual(result["verified_technologies"], ["Java", "Spring Boot", "MySQL", "Redis"])
        self.assertEqual((elapsed, cost), (1.0, 0.01))

    def test_does_not_fallback_for_unauthorized_error(self) -> None:
        unauthorized = urllib.error.HTTPError("https://example.test", 401, "Unauthorized", {}, None)
        with patch.object(runner, "call_model", side_effect=unauthorized):
            with self.assertRaises(RuntimeError):
                runner.call_with_fallback(README)

    def test_does_not_fallback_for_forbidden_error(self) -> None:
        forbidden = urllib.error.HTTPError("https://example.test", 403, "Forbidden", {}, None)
        with patch.object(runner, "call_model", side_effect=forbidden) as call_model:
            with self.assertRaises(RuntimeError):
                runner.call_with_fallback(README)
        self.assertEqual(call_model.call_count, 1)

    def test_rejects_quote_not_in_readme(self) -> None:
        result = valid_result()
        result["job_stack_comparison"][0]["evidence_quote"] = "Java 21"
        with self.assertRaises(ValueError):
            runner.validate_result(result, README)

    def test_format_uses_evidence_quote(self) -> None:
        output = runner.format_result(valid_result(), elapsed=1.2, cost=0.001)
        self.assertIn("근거 인용: Java 17", output)


if __name__ == "__main__":
    unittest.main()
