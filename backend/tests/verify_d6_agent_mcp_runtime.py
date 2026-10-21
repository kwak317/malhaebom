"""Verify an authenticated Agent request and print redacted runtime evidence.

Required environment variables:
  D6_API_BASE_URL, D6_ACCESS_TOKEN, D6_QUESTION_ID,
  D6_ANSWER_REVISION_ID, D6_JOB_SNAPSHOT_ID
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


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
    request = urllib.request.Request(
        f"{base_url}/api/agent",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
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
        reason = getattr(error, "reason", error)
        raise SystemExit(
            "API host could not be resolved or reached. "
            "Set D6_API_BASE_URL to a real URL such as "
            "https://api.example.com (do not include < or >). "
            f"Underlying error: {reason}"
        ) from error

    evidence = {
        "case_id": "d6-agent-mcp-runtime-01",
        "http_status": status,
        "terminal_status": body.get("status"),
        "trace_id": trace_id,
        "response_contract": "CoachingResponse",
    }
    if status == 422:
        detail = body.get("detail")
        if isinstance(detail, list):
            evidence["validation_errors"] = [
                {
                    "field": item.get("loc", []),
                    "type": item.get("type"),
                    "message": item.get("msg"),
                }
                for item in detail
                if isinstance(item, dict)
            ]
        elif isinstance(detail, dict):
            evidence["validation_errors"] = {
                "state": detail.get("state"),
                "code": detail.get("code"),
                "message": detail.get("message"),
            }
    if status >= 400 and "error" not in evidence:
        detail = body.get("detail")
        if isinstance(detail, dict):
            evidence["error"] = {
                "state": detail.get("state"),
                "code": detail.get("code"),
                "message": detail.get("message"),
            }
        elif isinstance(detail, str):
            evidence["error"] = {"message": detail}
        elif body.get("message") or body.get("code"):
            evidence["error"] = {
                "code": body.get("code"),
                "message": body.get("message"),
            }
    print(json.dumps(evidence, ensure_ascii=False))
    if status != 200:
        return 1
    if body.get("status") not in {"ok", "needs_more_info"}:
        raise SystemExit("HTTP 200 but no successful coaching terminal status")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
