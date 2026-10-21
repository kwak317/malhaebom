"""Verify the Agent's safe response when its MCP context gateway is unavailable.

Run only against a disposable local or staging API where ``MCP_SERVER_SCRIPT``
already points to a missing/unreachable MCP server. The script does not change
that setting and never prints credentials, IDs, or the user-facing message.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


CASE_ID = "d9-mcp-failure-01"
EXPECTED_STATUS = 503
EXPECTED_STATE = "mcp_error"
EXPECTED_CODE = "COACHING_MCP_UNAVAILABLE"


def build_evidence(
    *, status: int, payload: Any, trace_id: str | None
) -> dict[str, object]:
    detail = payload.get("detail", {}) if isinstance(payload, dict) else {}
    if not isinstance(detail, dict):
        detail = {}
    return {
        "case_id": CASE_ID,
        "http_status": status,
        "failure_state": detail.get("state"),
        "error_code": detail.get("code"),
        "retryable": detail.get("retryable"),
        "trace_id_present": bool(trace_id),
        "user_message_present": bool(detail.get("message")),
    }


def assert_expected_failure(evidence: dict[str, object]) -> None:
    if evidence["http_status"] != EXPECTED_STATUS:
        raise SystemExit(f"expected HTTP {EXPECTED_STATUS} for forced MCP failure")
    if evidence["failure_state"] != EXPECTED_STATE:
        raise SystemExit(f"expected failure_state={EXPECTED_STATE}")
    if evidence["error_code"] != EXPECTED_CODE:
        raise SystemExit(f"expected error_code={EXPECTED_CODE}")
    if evidence["retryable"] is not True:
        raise SystemExit("expected a retryable MCP failure")
    if evidence["user_message_present"] is not True:
        raise SystemExit("expected a safe user-facing failure message")


def main() -> int:
    base_url = os.environ["D9_API_BASE_URL"].rstrip("/")
    token = os.environ["D9_ACCESS_TOKEN"].strip()
    if not token or token.lower().startswith("bearer "):
        raise SystemExit("D9_ACCESS_TOKEN must be the raw JWT without 'Bearer '")

    payload = {
        "action": "analyze",
        "question_id": os.environ["D9_QUESTION_ID"],
        "answer_revision_id": os.environ["D9_ANSWER_REVISION_ID"],
        "job_snapshot_id": os.environ["D9_JOB_SNAPSHOT_ID"],
    }
    request = urllib.request.Request(
        f"{base_url}/api/agent",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            status = response.status
            response_payload = json.loads(response.read().decode("utf-8"))
            trace_id = response.headers.get("X-Trace-Id")
    except urllib.error.HTTPError as error:
        status = error.code
        trace_id = error.headers.get("X-Trace-Id")
        try:
            response_payload = json.loads(error.read().decode("utf-8"))
        except json.JSONDecodeError:
            response_payload = {}
    except urllib.error.URLError as error:
        raise SystemExit(f"API host could not be reached: {error}") from error

    evidence = build_evidence(
        status=status,
        payload=response_payload,
        trace_id=trace_id,
    )
    print(json.dumps(evidence, ensure_ascii=False))
    assert_expected_failure(evidence)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
