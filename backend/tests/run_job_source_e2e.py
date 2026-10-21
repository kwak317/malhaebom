"""Run the authenticated job-source review flow against a live local API.

The runner mirrors the frontend's setup path with one real Supabase access token:
NCS selection -> job recommendation -> selected job source review/requirement
extraction -> reviewed job listing -> practice-session creation.

It never prints the access token, source URL, requirement text/source excerpts,
user id, or persisted UUIDs.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.tests.run_d6_agent_e2e import (
    detect_api_base_url,
    normalize_access_token,
    request_json,
)


def supports_posix_token_file_permissions() -> bool:
    return os.name != "nt"


def resolve_access_token() -> str:
    value = (
        os.getenv("JOB_SOURCE_E2E_ACCESS_TOKEN", "").strip()
        or os.getenv("D6_ACCESS_TOKEN", "").strip()
    )
    if not value:
        token_file = REPO_ROOT / ".env.job-source-e2e"
        if token_file.exists():
            if not supports_posix_token_file_permissions():
                raise SystemExit(
                    "On Windows, set JOB_SOURCE_E2E_ACCESS_TOKEN or "
                    "D6_ACCESS_TOKEN as an environment variable; token-file "
                    "fallback requires POSIX permission checks."
                )
            if token_file.stat().st_mode & 0o077:
                raise SystemExit(
                    ".env.job-source-e2e must not be readable by group/others; "
                    "run chmod 600 .env.job-source-e2e."
                )
            for line in token_file.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                key, candidate = stripped.split("=", 1)
                if key.strip() in {"JOB_SOURCE_E2E_ACCESS_TOKEN", "D6_ACCESS_TOKEN"}:
                    value = candidate.strip().strip('"').strip("'")
                    if value:
                        break
    if not value:
        if not supports_posix_token_file_permissions():
            raise SystemExit(
                "On Windows, set JOB_SOURCE_E2E_ACCESS_TOKEN or "
                "D6_ACCESS_TOKEN as an environment variable; token-file "
                "fallback requires POSIX permission checks."
            )
        raise SystemExit(
            "Set JOB_SOURCE_E2E_ACCESS_TOKEN/D6_ACCESS_TOKEN, or create "
            ".env.job-source-e2e (chmod 600) with the current local Supabase "
            "access token."
        )
    try:
        return normalize_access_token(value)
    except ValueError as error:
        raise SystemExit(str(error)) from error


def require_status(
    actual: int,
    expected: int,
    step: str,
    payload: Any,
) -> None:
    if actual == expected:
        return
    detail = ""
    if isinstance(payload, dict) and isinstance(payload.get("detail"), str):
        detail = payload["detail"].strip()
    suffix = f": {detail[:200]}" if detail else ""
    raise SystemExit(f"{step} failed: HTTP {actual}{suffix}")


def select_ncs_id(payload: Any) -> str:
    if not isinstance(payload, dict) or not isinstance(payload.get("options"), list):
        raise SystemExit("NCS response has no options.")
    options = [item for item in payload["options"] if isinstance(item, dict)]
    for item in options:
        if item.get("id") == "skill-server":
            return "skill-server"
    for item in options:
        option_id = item.get("id")
        if isinstance(option_id, str) and option_id.strip():
            return option_id
    raise SystemExit("NCS response has no selectable option.")


def select_recommendation(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or not isinstance(payload.get("recommendations"), list):
        raise SystemExit("Recommendation response has no recommendations.")
    recommendations = [
        item for item in payload["recommendations"] if isinstance(item, dict)
    ]
    if not recommendations:
        raise SystemExit("Recommendation response is empty.")
    for item in recommendations:
        source_url = item.get("source_url")
        if isinstance(source_url, str) and source_url.startswith("https://"):
            return item
    raise SystemExit("No recommendation has a selectable HTTPS source URL.")


def validate_reviewed_job(payload: Any) -> tuple[str, list[dict[str, Any]]]:
    if not isinstance(payload, dict):
        raise SystemExit("Reviewed job response is not an object.")
    posting_id = payload.get("id")
    requirements = payload.get("requirements")
    if not isinstance(posting_id, str) or not posting_id:
        raise SystemExit("Reviewed job response has no id.")
    if payload.get("data_origin") != "private_job":
        raise SystemExit("Reviewed job was not persisted as private_job.")
    if not isinstance(requirements, list) or not requirements:
        raise SystemExit("Reviewed job has no extracted requirements.")
    parsed = [item for item in requirements if isinstance(item, dict)]
    if len(parsed) != len(requirements):
        raise SystemExit("Reviewed job requirements contain invalid entries.")
    for item in parsed:
        requirement_id = item.get("id")
        source_excerpt = item.get("source_excerpt")
        if not isinstance(requirement_id, str) or not requirement_id:
            raise SystemExit("Reviewed requirement has no id.")
        if not isinstance(source_excerpt, str) or not source_excerpt.strip():
            raise SystemExit("Reviewed requirement has no source excerpt.")
    return posting_id, parsed


def posting_visible_in_authenticated_list(payload: Any, posting_id: str) -> bool:
    if not isinstance(payload, dict) or not isinstance(payload.get("job_postings"), list):
        return False
    return any(
        isinstance(item, dict) and item.get("id") == posting_id
        for item in payload["job_postings"]
    )


def main() -> None:
    token = resolve_access_token()
    base_url = detect_api_base_url(os.getenv("JOB_SOURCE_E2E_API_BASE_URL", ""))

    health_status, _, _ = request_json(
        base_url=base_url,
        token="",
        method="GET",
        path="/health",
        timeout=10,
    )
    if health_status != 200:
        raise SystemExit(f"API health failed: HTTP {health_status}")

    ncs_status, ncs_body, _ = request_json(
        base_url=base_url,
        token=token,
        method="GET",
        path="/api/ncs/backend-competencies",
        timeout=60,
    )
    require_status(ncs_status, 200, "authenticated NCS lookup", ncs_body)
    ncs_id = select_ncs_id(ncs_body)

    recommendation_status, recommendation_body, recommendation_trace = request_json(
        base_url=base_url,
        token=token,
        method="POST",
        path="/api/job-search/recommendations",
        payload={"selected_ncs_ids": [ncs_id], "readme_analysis": None},
        timeout=180,
    )
    require_status(
        recommendation_status,
        200,
        "job recommendation",
        recommendation_body,
    )
    selected = select_recommendation(recommendation_body)
    source_url = str(selected["source_url"])
    recommendation_count = len(recommendation_body["recommendations"])

    review_status, review_body, review_trace = request_json(
        base_url=base_url,
        token=token,
        method="POST",
        path="/api/job-search/recommendations/analyze",
        payload={"source_url": source_url},
        timeout=180,
    )
    require_status(review_status, 201, "selected job source review", review_body)
    posting_id, requirements = validate_reviewed_job(review_body)

    list_status, list_body, _ = request_json(
        base_url=base_url,
        token=token,
        method="GET",
        path="/api/job-postings",
        timeout=60,
    )
    require_status(list_status, 200, "authenticated reviewed-job list", list_body)
    if not posting_visible_in_authenticated_list(list_body, posting_id):
        raise SystemExit("Reviewed job is not visible in the authenticated user's list.")

    selected_requirement_ids = [
        str(item["id"]) for item in requirements[: min(2, len(requirements))]
    ]
    session_status, session_body, session_trace = request_json(
        base_url=base_url,
        token=token,
        method="POST",
        path="/api/practice-sessions",
        payload={
            "job_posting_id": posting_id,
            "requirement_ids": selected_requirement_ids,
            "question_type": "preset",
            "question_id": "preset-04",
            "custom_question_text": None,
        },
        timeout=60,
    )
    require_status(session_status, 201, "practice-session creation", session_body)
    if not isinstance(session_body, dict) or not isinstance(
        session_body.get("practice_session_id"), str
    ):
        raise SystemExit("Practice-session response has no id.")

    source_host = urlparse(source_url).hostname or "unknown"
    print(
        json.dumps(
            {
                "api_base_url": base_url,
                "auth": "ok",
                "ncs_option": ncs_id,
                "recommendation_count": recommendation_count,
                "selected_source_host": source_host,
                "source_review": "ok",
                "requirement_count": len(requirements),
                "quote_validation_gate": "passed",
                "authenticated_job_list_contains_selected": True,
                "selected_requirement_count": len(selected_requirement_ids),
                "practice_session_created": True,
                "trace_ids_present": {
                    "recommendation": bool(recommendation_trace),
                    "source_review": bool(review_trace),
                    "practice_session": bool(session_trace),
                },
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
