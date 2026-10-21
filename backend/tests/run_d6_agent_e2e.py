"""Run D6 Agent live cases from one explicit completed analysis job.

The runner appends immutable synthetic answer revisions to the selected analysis
job, then calls the authenticated /api/agent endpoint for each case. It never
prints the answer text, access token, revision id, job snapshot id, or user id.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from uuid import UUID

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.tests.run_d6_live_agent_e2e import (
    expected_result_for_case,
    is_expected_result,
)

INPUTS_PATH = Path(__file__).with_name("d6_agent_live_inputs.json")
DEFAULT_API_BASE_URL = "http://localhost:8000"


def detect_api_base_url(explicit: str = "") -> str:
    configured = explicit.strip() or os.getenv("D6_API_BASE_URL", "").strip()
    if configured:
        return configured.rstrip("/")

    try:
        result = subprocess.run(
            ["docker", "compose", "port", "api", "8000"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return DEFAULT_API_BASE_URL

    if result.returncode == 0:
        match = re.search(r":(\d+)\s*$", result.stdout.strip())
        if match:
            return f"http://localhost:{match.group(1)}"
    return DEFAULT_API_BASE_URL


def normalize_access_token(value: str) -> str:
    token = value.strip()
    if token.lower().startswith("authorization:"):
        token = token.split(":", 1)[1].strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    if len(token.split(".")) != 3:
        raise ValueError("access token does not look like a JWT")
    return token


def resolve_access_token() -> str:
    value = os.getenv("D6_ACCESS_TOKEN", "").strip()
    if not value:
        if not sys.stdin.isatty():
            raise SystemExit(
                "Set D6_ACCESS_TOKEN in non-interactive mode."
            )
        value = getpass.getpass(
            "Paste current local Supabase access token (hidden input): "
        )
    try:
        return normalize_access_token(value)
    except ValueError as error:
        raise SystemExit(str(error)) from error


def load_case_inputs(path: Path = INPUTS_PATH) -> list[dict[str, str]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError("D6 Agent live case inputs must be a list")

    cases: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("D6 Agent live case input must be an object")
        case_id = str(item.get("case_id", "")).strip()
        kind = str(item.get("kind", "")).strip()
        confirmed_text = str(item.get("confirmed_text", "")).strip()
        if not case_id or not kind or not confirmed_text:
            raise ValueError("D6 Agent live case requires case_id, kind, confirmed_text")
        cases.append(
            {
                "case_id": case_id,
                "kind": kind,
                "confirmed_text": confirmed_text,
            }
        )
    return cases


def request_json(
    *,
    base_url: str,
    token: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    timeout: int = 180,
) -> tuple[int, Any, str | None]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}",
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            parsed = json.loads(raw) if raw else None
            return response.status, parsed, response.headers.get("X-Trace-Id")
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            parsed = {"status": "http_error"}
        return error.code, parsed, error.headers.get("X-Trace-Id")
    except (urllib.error.URLError, TimeoutError):
        return 0, {"status": "network_error"}, None


def list_job_candidates(records_payload: Any) -> list[dict[str, Any]]:
    if not isinstance(records_payload, dict):
        return []
    records = records_payload.get("records")
    if not isinstance(records, list):
        return []

    candidates: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        attempts = record.get("attempts")
        if not isinstance(attempts, list):
            continue
        for attempt in attempts:
            if not isinstance(attempt, dict):
                continue
            job_id = attempt.get("job_id")
            if not isinstance(job_id, str) or not job_id:
                continue
            candidates.append(
                {
                    "analysis_job_id": job_id,
                    "practice_session_id": record.get("practice_session_id"),
                    "question_id": record.get("question_id"),
                    "attempt_no": attempt.get("attempt_no"),
                    "practiced_at": record.get("practiced_at"),
                }
            )
    return candidates


def fetch_job_candidates(
    *, base_url: str, token: str
) -> tuple[int, list[dict[str, Any]], str | None]:
    status, body, _ = request_json(
        base_url=base_url,
        token=token,
        method="GET",
        path="/practice-records",
        timeout=30,
    )
    if status == 200:
        return status, list_job_candidates(body), None
    if status == 401:
        return (
            status,
            [],
            "unauthorized: refresh the current local Supabase access token",
        )
    if status == 0:
        return status, [], "network_error: API is not reachable"
    return status, [], "failed to list completed practice jobs"


def format_job_candidate(index: int, candidate: dict[str, Any]) -> str:
    job_id = str(candidate.get("analysis_job_id", ""))
    short_job_id = f"{job_id[:8]}…" if len(job_id) > 8 else job_id
    return (
        f"[{index}] question={candidate.get('question_id')} "
        f"attempt={candidate.get('attempt_no')} "
        f"practiced_at={candidate.get('practiced_at')} job={short_job_id}"
    )


def select_job_candidate(
    candidates: list[dict[str, Any]], *, input_fn=None
) -> str:
    if not candidates:
        raise SystemExit(
            "No completed jobs found. Create one dedicated test practice first."
        )
    for index, candidate in enumerate(candidates, start=1):
        print(format_job_candidate(index, candidate))

    reader = input if input_fn is None else input_fn
    while True:
        raw = reader(
            "Select a dedicated test job number (synthetic revisions will be appended): "
        ).strip()
        if raw.isdigit() and 1 <= int(raw) <= len(candidates):
            selected = candidates[int(raw) - 1]
            return str(selected["analysis_job_id"])
        print(f"Enter a number from 1 to {len(candidates)}.")


def create_revision(
    *,
    base_url: str,
    token: str,
    analysis_job_id: str,
    confirmed_text: str,
) -> tuple[int, Any, str | None]:
    UUID(analysis_job_id)
    return request_json(
        base_url=base_url,
        token=token,
        method="POST",
        path=f"/analysis-jobs/{analysis_job_id}/answer-revisions",
        payload={"confirmed_text": confirmed_text},
        timeout=30,
    )


def run_case(
    *,
    base_url: str,
    token: str,
    analysis_job_id: str,
    case: dict[str, str],
) -> dict[str, Any]:
    revision_status, revision_body, _ = create_revision(
        base_url=base_url,
        token=token,
        analysis_job_id=analysis_job_id,
        confirmed_text=case["confirmed_text"],
    )
    if revision_status != 201 or not isinstance(revision_body, dict):
        return {
            "case_id": case["case_id"],
            "stage": "revision",
            "revision_http_status": revision_status,
            "passed": False,
        }

    question_id = revision_body.get("question_id")
    answer_revision_id = revision_body.get("answer_revision_id")
    job_snapshot_id = revision_body.get("job_snapshot_id")
    if not all(
        isinstance(value, str) and value
        for value in (question_id, answer_revision_id, job_snapshot_id)
    ):
        return {
            "case_id": case["case_id"],
            "stage": "revision_context",
            "revision_http_status": revision_status,
            "passed": False,
        }

    agent_status, agent_body, trace_id = request_json(
        base_url=base_url,
        token=token,
        method="POST",
        path="/api/agent",
        payload={
            "action": "analyze",
            "question_id": question_id,
            "answer_revision_id": answer_revision_id,
            "job_snapshot_id": job_snapshot_id,
        },
    )
    safe_body = agent_body if isinstance(agent_body, dict) else {}
    expected_http_status, expected_terminal_statuses = expected_result_for_case(
        case["case_id"]
    )
    passed = is_expected_result(
        agent_status,
        safe_body,
        expected_http_status=expected_http_status,
        expected_terminal_statuses=expected_terminal_statuses,
    )
    return {
        "case_id": case["case_id"],
        "stage": "agent",
        "revision_http_status": revision_status,
        "agent_http_status": agent_status,
        "terminal_status": safe_body.get("status"),
        "trace_id": trace_id,
        "passed": passed,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run synthetic D6 Agent cases against an authenticated live API."
    )
    parser.add_argument(
        "--case",
        choices=("all", "normal", "boundary", "injection"),
        default="all",
        help="Case to run. Defaults to all three Agent cases.",
    )
    parser.add_argument(
        "--analysis-job-id",
        default=os.getenv("D6_ANALYSIS_JOB_ID", ""),
        help="Explicit completed analysis job used to append immutable test revisions.",
    )
    parser.add_argument(
        "--list-jobs",
        action="store_true",
        help="List completed job candidates without showing transcript text.",
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Check API health and authentication without creating revisions.",
    )
    parser.add_argument(
        "--api-base-url",
        default="",
        help="Override API base URL. Otherwise env/compose/fallback detection is used.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    base_url = detect_api_base_url(args.api_base_url)

    health_status, _, _ = request_json(
        base_url=base_url,
        token="",
        method="GET",
        path="/health",
        timeout=5,
    )
    if health_status != 200:
        print(
            json.dumps(
                {
                    "api_base_url": base_url,
                    "health": "network_error" if health_status == 0 else "failed",
                    "http_status": health_status,
                },
                ensure_ascii=False,
            )
        )
        return 1

    token = resolve_access_token()

    analysis_job_id = str(args.analysis_job_id).strip()
    candidates: list[dict[str, Any]] = []
    status = 200
    error: str | None = None
    if args.list_jobs or args.doctor or not analysis_job_id:
        status, candidates, error = fetch_job_candidates(
            base_url=base_url, token=token
        )
        if status != 200:
            print(
                json.dumps(
                    {
                        "api_base_url": base_url,
                        "http_status": status,
                        "error": error,
                        "jobs": [],
                    },
                    ensure_ascii=False,
                )
            )
            return 1

    if args.doctor:
        print(
            json.dumps(
                {
                    "api_base_url": base_url,
                    "health": "ok",
                    "auth": "ok",
                    "candidate_jobs": len(candidates),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if args.list_jobs:
        print(
            json.dumps(
                {"api_base_url": base_url, "http_status": status, "jobs": candidates},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if not analysis_job_id:
        if not sys.stdin.isatty():
            print(
                json.dumps(
                    {
                        "api_base_url": base_url,
                        "error": "analysis job id required in non-interactive mode",
                        "candidate_jobs": len(candidates),
                    },
                    ensure_ascii=False,
                )
            )
            return 1
        print(json.dumps({"api_base_url": base_url, "health": "ok", "auth": "ok"}))
        analysis_job_id = select_job_candidate(candidates)
    try:
        UUID(analysis_job_id)
    except ValueError as error:
        raise SystemExit("analysis job id must be a UUID") from error

    cases = load_case_inputs()
    selected = cases if args.case == "all" else [
        case for case in cases if case["kind"] == args.case
    ]
    if not selected:
        raise SystemExit(f"no D6 Agent live case found for {args.case}")

    print(
        json.dumps(
            {
                "notice": "immutable synthetic revisions will be appended",
                "case_count": len(selected),
            },
            ensure_ascii=False,
        )
    )
    results = [
        run_case(
            base_url=base_url,
            token=token,
            analysis_job_id=analysis_job_id,
            case=case,
        )
        for case in selected
    ]
    for result in results:
        print(json.dumps(result, ensure_ascii=False))

    passed = sum(1 for result in results if result.get("passed") is True)
    print(
        json.dumps(
            {"summary": {"passed": passed, "total": len(results)}},
            ensure_ascii=False,
        )
    )
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
