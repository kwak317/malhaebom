"""Verify that the Agent response exposes MCP request/response evidence."""

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

    body = {
        "action": "analyze",
        "question_id": os.environ["D6_QUESTION_ID"],
        "answer_revision_id": os.environ["D6_ANSWER_REVISION_ID"],
        "job_snapshot_id": os.environ["D6_JOB_SNAPSHOT_ID"],
    }
    request = urllib.request.Request(
        f"{base_url}/api/agent",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    trace_id: str | None = None
    tool_names: list[str] = []
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            status = response.status
            response_body: dict[str, Any] = json.loads(response.read().decode("utf-8"))
            trace_id = response.headers.get("X-Trace-Id")
            tool_names = response.headers.get("X-MCP-Tools", "").split(",")
    except urllib.error.HTTPError as error:
        status = error.code
        try:
            response_body = json.loads(error.read().decode("utf-8"))
        except json.JSONDecodeError:
            response_body = {"status": "http_error"}
    except urllib.error.URLError as error:
        raise SystemExit(f"API host could not be reached: {error}") from error

    result = {
        "case_id": "d6-mcp-request-response-01",
        "http_status": status,
        "terminal_status": response_body.get("status"),
        "trace_id": trace_id,
        "mcp_tools": [name for name in tool_names if name],
    }
    print(json.dumps(result, ensure_ascii=False))
    if status != 200 or response_body.get("status") not in {"ok", "needs_more_info"}:
        raise SystemExit("Agent request did not return a successful coaching response")
    if not trace_id or result["mcp_tools"] != ["get_question", "get_practice_attempt", "get_job_context"]:
        raise SystemExit("Agent request did not expose the expected redacted MCP evidence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
