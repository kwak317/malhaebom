"""Run D6 against a real authenticated Agent API, without storing answer text."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from uuid import UUID


CASES_PATH = Path(__file__).with_name("d6_evidence_cases.json")


def build_request(*, question_id: str, answer_revision_id: str, job_snapshot_id: str) -> dict[str, str]:
    UUID(answer_revision_id)
    UUID(job_snapshot_id)
    if not question_id.strip():
        raise ValueError("D6_QUESTION_ID is required")
    return {
        "action": "analyze",
        "question_id": question_id,
        "answer_revision_id": answer_revision_id,
        "job_snapshot_id": job_snapshot_id,
    }


def redact_result(*, case_id: str, http_status: int, body: dict[str, Any], trace_id: str | None) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "http_status": http_status,
        "terminal_status": body.get("status"),
        "trace_id": trace_id,
    }


def is_expected_result(
    http_status: int,
    body: dict[str, Any],
    *,
    expected_http_status: int,
    expected_terminal_statuses: list[str],
) -> bool:
    return (
        http_status == expected_http_status
        and body.get("status") in expected_terminal_statuses
    )


def case_id_from_env() -> str:
    return os.getenv("D6_CASE_ID", "d6-normal-live-01").strip() or "d6-normal-live-01"


def expected_result_for_case(case_id: str) -> tuple[int, list[str]]:
    parts = case_id.split("-")
    if len(parts) < 3 or parts[0] != "d6":
        raise ValueError(f"unsupported D6_CASE_ID: {case_id}")
    kind = parts[1]
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    for case in cases:
        if case.get("kind") == kind:
            return int(case["expected_http_status"]), list(case["expected_terminal_statuses"])
    raise ValueError(f"unsupported D6 case kind: {kind}")


def post_agent(base_url: str, token: str, payload: dict[str, str]) -> tuple[int, dict[str, Any], str | None]:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/agent",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return response.status, json.loads(response.read().decode("utf-8")), response.headers.get("X-Trace-Id")
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {"status": "http_error"}
        return error.code, body, error.headers.get("X-Trace-Id")


def main() -> int:
    base_url = os.environ["D6_API_BASE_URL"]
    token = os.environ["D6_ACCESS_TOKEN"].strip()
    if not token or token.startswith("Bearer "):
        raise SystemExit("D6_ACCESS_TOKEN must contain the raw token without 'Bearer '")

    payload = build_request(
        question_id=os.environ["D6_QUESTION_ID"],
        answer_revision_id=os.environ["D6_ANSWER_REVISION_ID"],
        job_snapshot_id=os.environ["D6_JOB_SNAPSHOT_ID"],
    )
    case_id = case_id_from_env()
    expected_http_status, expected_terminal_statuses = expected_result_for_case(case_id)
    explicit_terminal_status = os.getenv("D6_EXPECTED_TERMINAL_STATUS", "").strip()
    if explicit_terminal_status:
        expected_terminal_statuses = [explicit_terminal_status]

    status, body, trace_id = post_agent(base_url, token, payload)
    print(json.dumps(
        redact_result(
            case_id=case_id,
            http_status=status,
            body=body,
            trace_id=trace_id,
        ),
        ensure_ascii=False,
    ))
    return 0 if is_expected_result(
        status,
        body,
        expected_http_status=expected_http_status,
        expected_terminal_statuses=expected_terminal_statuses,
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
