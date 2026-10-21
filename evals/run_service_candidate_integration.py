#!/usr/bin/env python3
"""Exercise final LLM candidates through the real FastAPI coaching runtime.

The command is dry-run by default. Pass --live to allow the six paid OpenRouter
requests (two models x three representative cases). Raw provider responses and
secrets are never written; only the validated API response and usage metadata
are stored below the gitignored local-results directory.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid5

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
for entry in (ROOT, BACKEND):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from fastapi.testclient import TestClient  # noqa: E402

from app.core.auth import AuthenticatedUser, InvalidAccessToken  # noqa: E402
from app.main import create_app  # noqa: E402
from app.schemas.coaching import (  # noqa: E402
    CoachingAnalyzeRequest,
    CoachingContextBundle,
    CoachingResponse,
    JobContext,
    JobRequirementContext,
    PracticeAttemptContext,
    QuestionContext,
)
from app.services.coaching_runtime import (  # noqa: E402
    McpLlmCoachingService,
    OpenAICompatibleJsonProvider,
)
from evals.coaching_dataset import load_dataset, score_response  # noqa: E402
from evals.environment import load_evaluation_env, resolve_provider_credentials  # noqa: E402


MODELS = (
    "google/gemini-3.5-flash-lite",
    "openai/gpt-5.6-luna",
)
DEFAULT_CASE_IDS = (
    "coach-normal-01",
    "coach-boundary-13",
    "coach-failure-30",
)
NAMESPACE = UUID("a6725819-ec79-42f2-bbd2-8b3afe1cbd57")
USER_ID = "service-integration-user"


class TokenVerifier:
    def verify_access_token(self, token: str) -> str:
        if token != "service-integration-token":
            raise InvalidAccessToken()
        return USER_ID


class FixedContextGateway:
    def __init__(self, context: CoachingContextBundle) -> None:
        self.context = context

    def load_context(self, user, request) -> CoachingContextBundle:
        if user.user_id != USER_ID:
            raise AssertionError("unexpected integration-test user")
        if request.answer_revision_id != self.context.practice_attempt.answer_revision_id:
            raise AssertionError("answer revision mismatch")
        if request.job_snapshot_id != self.context.job_context.job_snapshot_id:
            raise AssertionError("job snapshot mismatch")
        return self.context


class ObservationSink:
    def __init__(self) -> None:
        self.roots: list[object] = []
        self.generations: list[object] = []
        self.validations: list[object] = []

    def record(self, observation) -> None:
        self.roots.append(observation)

    def record_generation(self, observation) -> None:
        self.generations.append(observation)

    def record_validation(self, observation) -> None:
        self.validations.append(observation)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="실제 OpenRouter 호출 허용")
    parser.add_argument(
        "--dataset", type=Path, default=ROOT / "evals/dataset.v2.jsonl"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "local-results/service-candidate-integration",
    )
    parser.add_argument("--case-id", action="append", dest="case_ids")
    parser.add_argument("--model", action="append", dest="models")
    parser.add_argument("--timeout-seconds", type=float, default=25.0)
    parser.add_argument("--transport-attempts", type=int, default=2)
    parser.add_argument("--contract-attempts", type=int, default=2)
    parser.add_argument("--max-cost-usd", type=float, default=0.10)
    return parser.parse_args()


def stable_uuid(case_id: str, kind: str) -> UUID:
    return uuid5(NAMESPACE, f"{case_id}:{kind}")


def build_context(case) -> CoachingContextBundle:
    now = datetime.now(UTC)
    session_id = stable_uuid(case.id, "session")
    return CoachingContextBundle(
        question=QuestionContext(
            question_id="preset-04",
            text=case.question.text,
            question_type="project_problem_solving",
            active_criterion_ids=case.context.active_criterion_ids,
            criteria_version="problem-solving-v4-draft.3",
        ),
        practice_attempt=PracticeAttemptContext(
            answer_revision_id=stable_uuid(case.id, "answer"),
            user_id=USER_ID,
            practice_session_id=session_id,
            question_id="preset-04",
            answer_segments=case.context.answer_segments,
            delivery_metrics={key: None for key in case.context.allowed_delivery_metric_ids},
            confirmed_at=now,
            expires_at=now + timedelta(hours=1),
        ),
        job_context=JobContext(
            job_snapshot_id=stable_uuid(case.id, "job"),
            user_id=USER_ID,
            practice_session_id=session_id,
            source_url="https://example.invalid/reviewed-backend-role",
            captured_at=now,
            review_status="reviewed",
            requirements=[
                JobRequirementContext(
                    requirement_id=requirement_id,
                    text="백엔드 프로젝트의 문제 해결 경험을 근거와 함께 설명할 수 있다.",
                    category="duty",
                )
                for requirement_id in case.context.requirement_ids
            ],
            expires_at=now + timedelta(hours=1),
        ),
    )


def observation_dict(item: object) -> dict[str, object]:
    dumped = item.model_dump(mode="json")
    return {
        key: dumped.get(key)
        for key in (
            "contract_attempt",
            "transport_attempt",
            "outcome",
            "retry_reason",
            "will_retry",
            "latency_ms",
            "input_tokens",
            "output_tokens",
            "cost_usd",
            "valid",
            "error_count",
        )
        if key in dumped
    }


def run_case(*, model: str, case, key: str, base_url: str, args) -> dict[str, object]:
    context = build_context(case)
    sink = ObservationSink()
    provider = OpenAICompatibleJsonProvider(
        api_key=key,
        model_name=model,
        base_url=base_url,
        timeout_seconds=args.timeout_seconds,
        max_transport_attempts=args.transport_attempts,
        observation_sink=sink,
        prompt_version="coaching-output-v3-service-integration",
        skill_version="interview-coach-v4",
    )
    service = McpLlmCoachingService(
        FixedContextGateway(context),
        provider,
        max_attempts=args.contract_attempts,
        max_cost_usd=args.max_cost_usd,
        observation_sink=sink,
        prompt_version="coaching-output-v3-service-integration",
    )
    app = create_app(
        token_verifier=TokenVerifier(),
        coaching_service=service,
        coaching_observation_sink=sink,
        # The integration target is coaching. Avoid unrelated TTS warmup in lifespan.
        question_tts_service=object(),
        question_tts_stream_service=object(),
    )
    request = CoachingAnalyzeRequest(
        action="analyze",
        question_id="preset-04",
        answer_revision_id=context.practice_attempt.answer_revision_id,
        job_snapshot_id=context.job_context.job_snapshot_id,
    )
    started = time.perf_counter()
    with TestClient(app) as client:
        response = client.post(
            "/api/agent",
            headers={"Authorization": "Bearer service-integration-token"},
            json=request.model_dump(mode="json"),
        )
    elapsed_ms = (time.perf_counter() - started) * 1000
    record: dict[str, object] = {
        "model": model,
        "case_id": case.id,
        "category": case.category,
        "http_status": response.status_code,
        "elapsed_ms": round(elapsed_ms, 3),
        "contract_valid": False,
        "validator_passed": False,
        "generation_attempts": [observation_dict(item) for item in sink.generations],
        "validation_attempts": [observation_dict(item) for item in sink.validations],
    }
    if response.status_code != 200:
        detail = response.json().get("detail", {})
        record["failure"] = {
            key: detail.get(key) for key in ("state", "code", "retryable")
        }
        return record

    validated = CoachingResponse.model_validate(response.json())
    score = score_response(case, validated)
    criteria = validated.criterion_assessments
    record.update(
        {
            "contract_valid": True,
            "validator_passed": True,
            "required_fields": {
                "intent": bool(validated.intent_assessment.reason),
                "criteria": len(criteria) == len(case.context.active_criterion_ids),
                "needed_consistent": all(
                    (item.needed is None) == (item.assessment.value == "met")
                    for item in criteria
                ),
                "evidence_present_for_met_partial": all(
                    bool(item.evidence)
                    for item in criteria
                    if item.assessment.value in {"met", "partial"}
                ),
            },
            "score": score.model_dump(mode="json"),
            "response": validated.model_dump(mode="json"),
        }
    )
    return record


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * fraction + 0.5)))
    return round(ordered[index], 3)


def summarize(
    records: list[dict[str, object]], models: tuple[str, ...] | list[str] = MODELS
) -> list[dict[str, object]]:
    summaries = []
    for model in models:
        selected = [item for item in records if item["model"] == model]
        latencies = [float(item["elapsed_ms"]) for item in selected]
        generations = [attempt for item in selected for attempt in item["generation_attempts"]]
        costs = [float(item["cost_usd"]) for item in generations if item.get("cost_usd") is not None]
        summaries.append(
            {
                "model": model,
                "requests": len(selected),
                "http_success": sum(item["http_status"] == 200 for item in selected),
                "contract_valid": sum(bool(item["contract_valid"]) for item in selected),
                "validator_passed": sum(bool(item["validator_passed"]) for item in selected),
                "p50_ms": round(statistics.median(latencies), 3) if latencies else None,
                "p95_ms": percentile(latencies, 0.95),
                "known_cost_usd": round(sum(costs), 8),
                "unknown_cost_attempts": sum(item.get("cost_usd") is None for item in generations),
                "transport_retries": sum(bool(item.get("will_retry")) for item in generations),
                "contract_repairs": sum(
                    max(0, len(item["validation_attempts"]) - 1) for item in selected
                ),
            }
        )
    return summaries


def write_markdown(path: Path, result: dict[str, object]) -> None:
    lines = [
        "# Service candidate integration result",
        "",
        f"- created_at: `{result['created_at']}`",
        f"- cases: `{', '.join(result['case_ids'])}`",
        "- path: FastAPI `/api/agent` → `McpLlmCoachingService` → OpenRouter → Pydantic/reference validator",
        "",
        "| Model | HTTP | Contract | Validator | p50 / p95 | Known cost | Retries / repairs |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in result["summaries"]:
        lines.append(
            f"| {item['model']} | {item['http_success']}/{item['requests']} | "
            f"{item['contract_valid']}/{item['requests']} | {item['validator_passed']}/{item['requests']} | "
            f"{item['p50_ms']} / {item['p95_ms']} ms | ${item['known_cost_usd']:.8f} | "
            f"{item['transport_retries']} / {item['contract_repairs']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    models = tuple(args.models or MODELS)
    case_ids = tuple(args.case_ids or DEFAULT_CASE_IDS)
    plan = {
        "models": list(MODELS),
        "models": list(models),
        "case_ids": list(case_ids),
        "planned_user_requests": len(MODELS) * len(case_ids),
        "planned_user_requests": len(models) * len(case_ids),
        "max_provider_attempts_per_request": args.transport_attempts * args.contract_attempts,
        "network_calls": bool(args.live),
    }
    if not args.live:
        print(json.dumps(plan, ensure_ascii=False))
        return 0
    if not 1 <= args.transport_attempts <= 3 or args.contract_attempts < 1:
        raise ValueError("transport attempts는 1~3, contract attempts는 1 이상이어야 합니다")
    load_evaluation_env()
    key, base_url = resolve_provider_credentials(require_openrouter=True)
    cases_by_id = {case.id: case for case in load_dataset(args.dataset)}
    missing = sorted(set(case_ids) - set(cases_by_id))
    if missing:
        raise ValueError("dataset에 없는 case: " + ", ".join(missing))

    records = []
    for model in models:
        for case_id in case_ids:
            record = run_case(
                model=model,
                case=cases_by_id[case_id],
                key=key,
                base_url=base_url,
                args=args,
            )
            records.append(record)
            print(
                json.dumps(
                    {
                        "model": model,
                        "case_id": case_id,
                        "http_status": record["http_status"],
                        "validator_passed": record["validator_passed"],
                        "elapsed_ms": record["elapsed_ms"],
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )

    result = {
        **plan,
        "created_at": datetime.now(UTC).isoformat(),
        "dataset": str(args.dataset),
        "runtime_settings": {
            "timeout_seconds": args.timeout_seconds,
            "transport_attempts": args.transport_attempts,
            "contract_attempts": args.contract_attempts,
            "max_cost_usd": args.max_cost_usd,
            "temperature": "model_default",
            "provider_require_parameters": True,
        },
        "records": records,
        "summaries": summarize(records),
        "summaries": summarize(records, models=models),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_markdown(args.output_dir / "REPORT.md", result)
    print(json.dumps({"output_dir": str(args.output_dir), "summaries": result["summaries"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
