"""Verify an authenticated Agent response contract.

Required environment variables are the same as verify_d6_agent_mcp_runtime.py,
plus D6_SUPABASE_URL and D6_SUPABASE_SERVICE_ROLE_KEY for persistence lookup.
The script prints only redacted evidence suitable for a D6 worklog.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from urllib.parse import quote
from typing import Any


def persistence_matches_request(
    rows: list[dict[str, Any]],
    *,
    answer_revision_id: str,
    job_snapshot_id: str,
    previous_run_id: str | None,
    expected_status: str,
) -> bool:
    return any(
        row.get("answer_revision_id") == answer_revision_id
        and row.get("job_snapshot_id") == job_snapshot_id
        and row.get("id")
        and row.get("id") != previous_run_id
        and row.get("status") == expected_status
        for row in rows
    )


def fetch_persistence_rows(
    *,
    supabase_url: str,
    service_role_key: str,
    answer_revision_id: str,
    job_snapshot_id: str,
) -> list[dict[str, Any]]:
    query = (
        "answer_revision_id=eq."
        + quote(answer_revision_id, safe="")
        + "&job_snapshot_id=eq."
        + quote(job_snapshot_id, safe="")
        + "&select=id,answer_revision_id,job_snapshot_id,status"
        + "&order=created_at.desc&limit=1"
    )
    request = urllib.request.Request(
        f"{supabase_url.rstrip('/')}/rest/v1/coaching_runs?{query}",
        headers={
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
        },
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        body = json.loads(response.read().decode("utf-8"))
    return body if isinstance(body, list) else []


def main() -> int:
    base_url = os.environ["D6_API_BASE_URL"].rstrip("/")
    token = os.environ["D6_ACCESS_TOKEN"].strip()
    if not token or token.startswith("Bearer "):
        raise SystemExit("D6_ACCESS_TOKEN must be the raw JWT without 'Bearer '")

    payload = {
        "action": "analyze",
        "question_id": os.environ["D6_QUESTION_ID"],
        "answer_revision_id": os.environ["D6_ANSWER_REVISION_ID"],
        "job_snapshot_id": os.environ["D6_JOB_SNAPSHOT_ID"],
    }
    answer_revision_id = payload["answer_revision_id"]
    job_snapshot_id = payload["job_snapshot_id"]
    supabase_url = os.environ.get("D6_SUPABASE_URL", "").strip()
    service_role_key = os.environ.get("D6_SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not supabase_url or not service_role_key:
        raise SystemExit("D6_SUPABASE_URL and D6_SUPABASE_SERVICE_ROLE_KEY are required to verify coaching persistence")
    request = urllib.request.Request(
        f"{base_url}/api/agent",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    previous_rows = fetch_persistence_rows(
        supabase_url=supabase_url, service_role_key=service_role_key,
        answer_revision_id=answer_revision_id, job_snapshot_id=job_snapshot_id,
    )
    previous_run_id = str(previous_rows[0].get("id")) if previous_rows else None
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            status = response.status
            body: dict[str, Any] = json.loads(response.read().decode("utf-8"))
            trace_id = response.headers.get("X-Trace-Id")
    except urllib.error.HTTPError as error:
        status = error.code
        trace_id = error.headers.get("X-Trace-Id")
        try:
            body = json.loads(error.read().decode("utf-8"))
        except json.JSONDecodeError:
            body = {"status": "http_error"}
    except urllib.error.URLError as error:
        raise SystemExit(f"API host could not be reached: {error}") from error

    evidence = {
        "case_id": "d6-coaching-response-01",
        "http_status": status,
        "terminal_status": body.get("status"),
        "trace_id": trace_id,
        "response_contract": "CoachingResponse",
        "persistence_id": None,
        "persistence_status": None,
    }
    if status != 200:
        return 1
    if body.get("status") not in {"ok", "needs_more_info"}:
        raise SystemExit(
            "D6 coaching response is not a successful terminal status"
        )
    try:
        rows = fetch_persistence_rows(
            supabase_url=supabase_url,
            service_role_key=service_role_key,
            answer_revision_id=answer_revision_id,
            job_snapshot_id=job_snapshot_id,
        )
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as error:
        raise SystemExit(f"coaching persistence could not be verified: {error}") from error
    if not persistence_matches_request(
        rows,
        answer_revision_id=answer_revision_id,
        job_snapshot_id=job_snapshot_id,
        previous_run_id=previous_run_id,
        expected_status=str(body.get("status")),
    ):
        raise SystemExit("matching coaching_runs persistence row was not found")
    evidence["persistence_id"] = rows[0].get("id")
    evidence["persistence_status"] = rows[0].get("status")
    print(json.dumps(evidence, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
