"""Compose에서 frontend proxy → FastAPI mock → MCP 계약을 재현한다."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
for import_path in (PROJECT_ROOT, BACKEND_ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from app.schemas.coaching import CoachingAnalyzeRequest, CoachingResponse  # noqa: E402
from app.services.coaching_context import (  # noqa: E402
    DEMO_ANSWER_REVISION_ID,
    DEMO_JOB_SNAPSHOT_ID,
    DEMO_QUESTION_ID,
    build_demo_coaching_service,
)
from app.services.attempt_comparison import (  # noqa: E402
    DEMO_CURRENT_COACHING_RUN_ID,
    DEMO_PREVIOUS_COACHING_RUN_ID,
    build_demo_attempt_comparison_service,
)
from app.services.mcp_access import McpAccessTokenCodec  # noqa: E402
from mcp_server.server import (  # noqa: E402
    compare_attempts,
    configure_mcp_dependencies,
    get_job_context,
    get_practice_attempt,
    get_question,
)
from d6_evidence_utils import build_redacted_evidence  # noqa: E402


USER_ID = "compose-e2e-user"


def main() -> int:
    frontend_url = os.environ["COACHING_E2E_FRONTEND_URL"].rstrip("/")
    access_token = os.environ["COACHING_E2E_TOKEN"]
    mcp_secret = hashlib.sha256(f"mcp:{access_token}".encode("utf-8")).hexdigest()

    page = wait_for_frontend(f"{frontend_url}/demo/coaching")
    if 'id="root"' not in page:
        raise AssertionError("frontend 앱 root를 찾지 못했습니다")

    request_body = CoachingAnalyzeRequest(
        action="analyze",
        question_id=DEMO_QUESTION_ID,
        answer_revision_id=DEMO_ANSWER_REVISION_ID,
        job_snapshot_id=DEMO_JOB_SNAPSHOT_ID,
    )
    response = post_json(
        f"{frontend_url}/api/agent",
        request_body.model_dump(mode="json"),
        access_token,
    )
    validated = CoachingResponse.model_validate(response)
    if validated.status.value != "needs_more_info" or not validated.evidence:
        raise AssertionError("검증된 mock 코칭 응답을 받지 못했습니다")

    service = build_demo_coaching_service(USER_ID)
    comparison_service = build_demo_attempt_comparison_service(USER_ID)
    codec = McpAccessTokenCodec(mcp_secret)
    configure_mcp_dependencies(
        context_service=service.context_service,
        comparison_service=comparison_service,
        token_codec=codec,
    )
    try:
        context_token = codec.issue(user_id=USER_ID, request=request_body)
        question = get_question(context_token, DEMO_QUESTION_ID)
        attempt = get_practice_attempt(
            context_token,
            str(DEMO_ANSWER_REVISION_ID),
        )
        job = get_job_context(context_token, str(DEMO_JOB_SNAPSHOT_ID))
        comparison_token = codec.issue_comparison(
            user_id=USER_ID,
            previous_coaching_run_id=DEMO_PREVIOUS_COACHING_RUN_ID,
            current_coaching_run_id=DEMO_CURRENT_COACHING_RUN_ID,
        )
        comparison = compare_attempts(
            comparison_token,
            str(DEMO_PREVIOUS_COACHING_RUN_ID),
            str(DEMO_CURRENT_COACHING_RUN_ID),
        )
    finally:
        configure_mcp_dependencies(
            context_service=None,
            comparison_service=None,
            token_codec=None,
        )

    if question["question_id"] != DEMO_QUESTION_ID:
        raise AssertionError("MCP 질문 조회가 일치하지 않습니다")
    if not attempt["answer_segments"] or not job["requirements"]:
        raise AssertionError("MCP 답변·공고 문맥이 비어 있습니다")
    if not comparison["comparison"]["content_available"]:
        raise AssertionError("MCP 1차·2차 코칭 비교 결과가 비어 있습니다")

    print(
        json.dumps(
                {
                    "screen": "ok",
                    "api_proxy": "ok",
                    "mock_contract": validated.status.value,
                    "mcp_tools": [
                    "get_question",
                    "get_practice_attempt",
                    "get_job_context",
                    "compare_attempts",
                    ],
                    **build_redacted_evidence(
                        case_id="d6-normal-01",
                        http_status=200,
                        called_tools=[
                            "get_question",
                            "get_practice_attempt",
                            "get_job_context",
                            "compare_attempts",
                        ],
                        trace_id=None,
                        terminal_status=validated.status.value,
                    ),
                },
            ensure_ascii=False,
        )
    )
    return 0


def wait_for_frontend(url: str) -> str:
    last_error: Exception | None = None
    for _ in range(30):
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                return response.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError) as error:
            last_error = error
            time.sleep(1)
    raise RuntimeError(f"frontend 준비를 기다리다 실패했습니다: {last_error}")


def post_json(url: str, payload: dict[str, object], access_token: str) -> object:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
