#!/usr/bin/env python3
"""같은 30건 평가셋으로 후보 모델의 정확도·비용·지연을 비교한다."""

from __future__ import annotations

import argparse
import json
import math
import multiprocessing
import os
import sys
import time
from collections import Counter
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
for import_path in (PROJECT_ROOT, BACKEND_ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from app.schemas.coaching import CoachingLLMOutput, CoachingResponse  # noqa: E402
from evals.environment import load_evaluation_env, resolve_provider_credentials  # noqa: E402
from evals.evaluation_records import (  # noqa: E402
    CONFIG_VERSION,
    GRADER_VERSION,
    MODELS,
    POLICY_VERSION,
    REQUEST_SETTINGS,
    consistency,
    digest,
    id_metrics,
    label_signature,
)
from evals.semantic_grader import (  # noqa: E402
    SemanticReview,
    evaluate_semantic,
    summarize_semantic,
)
from pydantic import ValidationError  # noqa: E402
from app.services.coaching_skill import (  # noqa: E402
    CoachingSkillError,
    SkillBundle,
    load_skill_bundle,
)
from app.services.coaching_prompt import (  # noqa: E402
    DEFAULT_COACHING_PROMPT_VERSION,
    build_coaching_system_prompt,
    build_contract_repair_user_prompt,
    prompt_sha256,
)
from evals.coaching_dataset import (  # noqa: E402
    CaseScore,
    CoachingEvaluationCase,
    dataset_summary,
    load_dataset,
    score_response,
)
from services.llm import OutputContractError, validate_and_build_response  # noqa: E402


@dataclass(frozen=True)
class CandidateConfig:
    label: str
    provider: str
    model: str
    input_usd_per_million: float = 0.0
    output_usd_per_million: float = 0.0

    @classmethod
    def parse(cls, value: str) -> "CandidateConfig":
        if "=" not in value or ":" not in value:
            raise ValueError(
                "candidate는 label=mock:expected 또는 label=openai:model-id 형식이어야 합니다"
            )
        label, target = value.split("=", 1)
        provider, model = target.split(":", 1)
        if (
            not label.strip()
            or provider not in {"mock", "openai", "ollama"}
            or not model.strip()
        ):
            raise ValueError(f"지원하지 않는 candidate: {value}")
        return cls(label=label.strip(), provider=provider, model=model.strip())


@dataclass
class CandidateAttempt:
    candidate: str
    case_id: str
    category: str
    run: int
    latency_ms: float
    cost_usd: float | None
    input_tokens: int | None
    output_tokens: int | None
    score: CaseScore | None
    failure_state: str | None
    failure_reason: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "candidate": self.candidate,
            "case_id": self.case_id,
            "category": self.category,
            "run": self.run,
            "latency_ms": round(self.latency_ms, 3),
            "cost_usd": round(self.cost_usd, 8) if self.cost_usd is not None else None,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "contract_valid": bool(self.score and self.score.contract_valid),
            "accuracy": round(self.score.accuracy, 6) if self.score else 0.0,
            "failure_state": self.failure_state,
            "failure_reason": self.failure_reason,
        }


class CandidateRunner:
    def generate(
        self, case: CoachingEvaluationCase
    ) -> tuple[dict[str, Any], int | None, int | None, float]:
        raise NotImplementedError


class HardProviderTimeoutError(TimeoutError):
    """Raised when the parent process terminates a stalled provider call."""


class IsolatedProviderError(RuntimeError):
    """Sanitized provider failure returned by an isolated child process."""

    def __init__(self, error_type: str) -> None:
        super().__init__(error_type)
        self.error_type = error_type


def _isolated_provider_worker(
    connection: Any,
    config: CandidateConfig,
    system_prompt: str,
    api_key: str,
    base_url: str,
    timeout_seconds: float,
    max_completion_tokens: int,
    case_payload: dict[str, Any],
    user_prompt: str,
) -> None:
    """Execute one provider request and return only sanitized failure metadata."""
    runner: OpenAICompatibleRunner | None = None
    try:
        runner = OpenAICompatibleRunner(
            config,
            system_prompt=system_prompt,
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            max_completion_tokens=max_completion_tokens,
            isolate_calls=False,
        )
        result = runner._generate_with_user_prompt(
            CoachingEvaluationCase.model_validate(case_payload),
            user_prompt,
        )
        connection.send(("ok", result, runner.last_record))
    except BaseException as error:
        connection.send(
            (
                "error",
                type(error).__name__,
                runner.last_record if runner is not None else {},
            )
        )
    finally:
        connection.close()


def _terminate_process(process: multiprocessing.Process) -> None:
    process.terminate()
    process.join(timeout=1)
    if process.is_alive():
        process.kill()
        process.join(timeout=1)


def build_coaching_response_format() -> dict[str, Any]:
    """OpenAI-compatible 서버에 코칭 출력 계약을 강제한다."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "malhaebom_coaching",
            "strict": True,
            "schema": CoachingLLMOutput.model_json_schema(),
        },
    }


class MockCandidateRunner(CandidateRunner):
    def __init__(self, mode: str) -> None:
        if mode not in {"expected", "degraded"}:
            raise ValueError("mock candidate는 expected 또는 degraded만 지원합니다")
        self.mode = mode

    def generate(
        self, case: CoachingEvaluationCase
    ) -> tuple[dict[str, Any], int | None, int | None, float]:
        raw_output = build_expected_output(case)
        if self.mode == "degraded":
            sequence = int(case.id.rsplit("-", 1)[-1])
            if sequence % 4 == 0:
                raw_output["criterion_assessments"] = raw_output[
                    "criterion_assessments"
                ][:-1]
            elif sequence % 3 == 0:
                raw_output["intent_assessment"]["label"] = "off_topic"
        return raw_output, 0, 0, 0.0


class OpenAICompatibleRunner(CandidateRunner):
    def __init__(
        self,
        config: CandidateConfig,
        *,
        system_prompt: str,
        api_key: str,
        base_url: str,
        timeout_seconds: float,
        max_completion_tokens: int,
        isolate_calls: bool = True,
    ) -> None:
        from openai import OpenAI

        self.config = config
        self.system_prompt = system_prompt
        self.api_key = api_key
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.max_completion_tokens = max_completion_tokens
        self.isolate_calls = isolate_calls
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
            max_retries=0,
        )

    def generate(
        self, case: CoachingEvaluationCase
    ) -> tuple[dict[str, Any], int | None, int | None, float]:
        return self._generate_with_user_prompt(case, self._base_user_prompt(case))

    def generate_repair(
        self,
        case: CoachingEvaluationCase,
        *,
        previous_output: object,
        violations: list[str],
    ) -> tuple[dict[str, Any], int | None, int | None, float]:
        return self._generate_with_user_prompt(
            case,
            build_contract_repair_user_prompt(
                self._base_user_prompt(case),
                previous_output,
                violations,
            ),
        )

    @staticmethod
    def _base_user_prompt(case: CoachingEvaluationCase) -> str:
        return json.dumps(
            {
                "question": case.question.model_dump(mode="json"),
                "server_context": case.context.model_dump(mode="json"),
            },
            ensure_ascii=False,
        )

    def _generate_with_user_prompt(
        self,
        case: CoachingEvaluationCase,
        user_prompt: str,
    ) -> tuple[dict[str, Any], int | None, int | None, float]:
        if getattr(self, "isolate_calls", False):
            return self._generate_isolated(case, user_prompt)
        return self._generate_direct(case, user_prompt)

    def _generate_isolated(
        self,
        case: CoachingEvaluationCase,
        user_prompt: str | None = None,
    ) -> tuple[dict[str, Any], int | None, int | None, float]:
        user_prompt = user_prompt or self._base_user_prompt(case)
        context = multiprocessing.get_context("spawn")
        parent_connection, child_connection = context.Pipe(duplex=False)
        process = context.Process(
            target=_isolated_provider_worker,
            args=(
                child_connection,
                self.config,
                self.system_prompt,
                self.api_key,
                self.base_url,
                self.timeout_seconds,
                self.max_completion_tokens,
                case.model_dump(mode="json"),
                user_prompt,
            ),
        )
        process.start()
        child_connection.close()
        try:
            if not parent_connection.poll(self.timeout_seconds):
                _terminate_process(process)
                self.last_record = {}
                raise HardProviderTimeoutError()
            try:
                message = parent_connection.recv()
            except EOFError as error:
                raise IsolatedProviderError("ChildProcessExit") from error
        finally:
            parent_connection.close()
            if process.is_alive():
                _terminate_process(process)
            else:
                process.join(timeout=1)

        status, payload, self.last_record = message
        if status == "error":
            raise IsolatedProviderError(payload)
        return payload

    def _generate_direct(
        self,
        case: CoachingEvaluationCase,
        user_prompt: str,
    ) -> tuple[dict[str, Any], int | None, int | None, float]:
        self.last_record = {}
        request: dict[str, Any] = {
            "model": self.config.model,
            "max_completion_tokens": self.max_completion_tokens,
            "response_format": build_response_format(self.config),
            "extra_body": {"provider": {"require_parameters": True}},
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        reasoning_effort = reasoning_effort_for(self.config)
        if reasoning_effort is not None:
            request["reasoning_effort"] = reasoning_effort
        completion = self.client.chat.completions.create(**request)
        payload = completion.model_dump(mode="json")
        usage = payload.get("usage") or {}
        self.last_record = {"usage": usage,
                            "generation_id": payload.get("id"), "provider": payload.get("provider"),
                            "returned_model": payload.get("model"),
                            "cost_source": "usage.cost" if usage.get("cost") is not None else "unknown"}
        content = completion.choices[0].message.content if completion.choices else None
        if completion.choices:
            self.last_record["finish_reason"] = completion.choices[0].finish_reason
        self.last_record["raw_output"] = content
        # Capture accounting before parsing, including empty or malformed completions.
        raw_output = json.loads(content) if content else None
        if not isinstance(raw_output, dict):
            raise ValueError("모델 응답은 JSON 객체여야 합니다")
        return raw_output, usage.get("prompt_tokens"), usage.get("completion_tokens"), usage.get("cost")


def build_response_format(config: CandidateConfig) -> dict[str, Any]:
    # OpenRouter's OpenAI-compatible endpoint accepts the same strict JSON
    # Schema request for Gemini and other providers.  Sending only
    # ``json_object`` leaves the model free to change list/object shapes and
    # omit fields required by CoachingLLMOutput; the server validator then
    # rejects every otherwise parseable response.
    if config.provider in {"openai", "ollama"}:
        schema = CoachingLLMOutput.model_json_schema()
        if config.provider == "openai":
            schema = strict_json_schema(schema)
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "coaching_output",
                "schema": schema,
                "strict": config.provider == "openai",
            },
        }
    return {"type": "json_object"}


def reasoning_effort_for(config: CandidateConfig) -> str | None:
    if config.provider == "openai" and config.model.startswith("openai/gpt-5"):
        return "minimal"
    return None


def strict_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """OpenAI strict 모드가 요구하는 모든 object property의 required 선언을 보장한다."""

    normalized = deepcopy(schema)

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            properties = node.get("properties")
            if isinstance(properties, dict):
                node["required"] = list(properties)
                node["additionalProperties"] = False
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(normalized)
    return normalized


def select_cases(
    cases: list[CoachingEvaluationCase], case_ids: list[str] | None
) -> list[CoachingEvaluationCase]:
    if not case_ids:
        return cases
    requested = set(case_ids)
    selected = [case for case in cases if case.id in requested]
    missing = [case_id for case_id in case_ids if case_id not in {case.id for case in selected}]
    if missing:
        raise ValueError("없는 case_id입니다: " + ", ".join(missing))
    return selected


def build_expected_output(case: CoachingEvaluationCase) -> dict[str, Any]:
    expected = case.expected

    def evidence_for(target_type: str, target_id: str) -> list[dict[str, str]]:
        return [
            {"segment_id": item.segment_id, "quote": item.quote}
            for item in expected.evidence
            if item.target_type == target_type and item.target_id == target_id
        ]

    job_alignment = [
        {
            "requirement_id": requirement_id,
            "label": label.value,
            "reason": "합성 평가셋의 답변 근거와 직무 요구사항을 대조했습니다.",
            "evidence": evidence_for("job_alignment", requirement_id),
        }
        for requirement_id, label in expected.job_alignment.items()
    ]
    criterion_assessments = []
    missing_targets: list[str] = []
    for criterion_id, assessment in expected.criterion_assessments.items():
        is_met = assessment.value == "met"
        if not is_met:
            missing_targets.append(criterion_id)
        criterion_assessments.append(
            {
                "criterion_id": criterion_id,
                "assessment": assessment.value,
                "reason": "합성 평가셋의 기대 기준 판정입니다.",
                "evidence": evidence_for("criterion_assessment", criterion_id),
                "needed": None if is_met else f"{criterion_id}의 구체적인 근거",
            }
        )

    action_targets = missing_targets[:2] or [case.context.active_criterion_ids[0]]
    return {
        "job_alignment": job_alignment,
        "intent_assessment": {
            "label": expected.intent_label.value,
            "reason": "질문 의도와 답변 범위를 비교했습니다.",
        },
        "criterion_assessments": criterion_assessments,
        "clarifying_question": (
            None
            if not missing_targets
            else "빠진 판단 근거와 확인 결과를 구체적으로 설명해 주시겠어요?"
        ),
        "next_actions": [
            {
                "target_type": "criterion",
                "target_id": target_id,
                "action": f"{target_id} 근거를 한 문장으로 보완해 보세요.",
            }
            for target_id in action_targets
        ],
        # 기존 평가셋의 사람 판정을 바꾸지 않고 새 출력 계약만 검증한다.
        "example_answer": _build_contract_example(case),
    }


def _build_contract_example(case: CoachingEvaluationCase) -> str:
    selected: list[str] = []
    for segment in case.context.answer_segments[:3]:
        candidate = " ".join([*selected, segment.text])
        if len(candidate) > 500:
            break
        selected.append(segment.text)
    example = " ".join(selected)
    if not any("가" <= char <= "힣" for char in example):
        return "[사람 검토 예시 답변이 아직 없는 계약 검증 사례]"
    return example


def run_comparison(
    cases: list[CoachingEvaluationCase],
    candidates: list[tuple[CandidateConfig, CandidateRunner]],
    *,
    repeats: int = 1,
    configuration: dict[str, str] | None = None,
    max_calls: int = 1,
    parent_links: dict[str, str] | None = None,
    semantic_reviews: dict[str, dict] | None = None,
) -> dict[str, object]:
    max_attempts: int = max_calls
    if repeats < 1 or max_attempts < 1:
        raise ValueError("repeats/max_calls must be positive")
    if len({config.label for config, _ in candidates}) != len(candidates):
        raise ValueError("candidate labels must be unique")
    reviews = {key: SemanticReview.model_validate(value) for key, value in (semantic_reviews or {}).items()}
    possible_ids = {f"{config.label}:{case.id}:{run}:{call}"
                    for config, _ in candidates for case in cases
                    for run in range(1, repeats + 1) for call in range(1, max_calls + 1)}
    if set(reviews) - possible_ids:
        raise ValueError("검토 결과의 attempt ID가 평가 설정과 다릅니다")
    attempts: list[CandidateAttempt] = []
    records = []
    for config, runner in candidates:
        for run_number in range(1, repeats + 1):
            for case in cases:
                execution_id = f"{config.label}:{case.id}:{run_number}"
                repair_previous_output: object = None
                repair_violations: list[str] = []
                for call in range(1, max_attempts + 1):
                    started = time.perf_counter()
                    raw_output = score = response = None
                    input_tokens = output_tokens = cost = None
                    schema_valid = validator_valid = None
                    failure_state = failure_reason = None
                    # Provider adapters expose accounting even when generate raises.
                    runner.last_record = {}
                    try:
                        if (
                            call > 1
                            and hasattr(runner, "generate_repair")
                            and repair_violations
                        ):
                            raw_output, input_tokens, output_tokens, cost = (
                                runner.generate_repair(
                                    case,
                                    previous_output=repair_previous_output,
                                    violations=repair_violations,
                                )
                            )
                        else:
                            raw_output, input_tokens, output_tokens, cost = runner.generate(case)
                        CoachingLLMOutput.model_validate(raw_output)
                        schema_valid = True
                        response = validate_and_build_response(raw_output, case.context)
                        validator_valid = True
                        score = score_response(case, response)
                    except ValidationError as error:
                        schema_valid = False
                        failure_state = "schema_violation"
                        failure_reason = "Pydantic output schema rejected response"
                        repair_violations = [
                            (
                                ".".join(str(part) for part in item["loc"])
                                + ": "
                                + item["msg"]
                            )
                            for item in error.errors()
                        ]
                    except OutputContractError as error:
                        validator_valid = False
                        failure_state = "validator_violation"
                        failure_reason = str(error)
                        repair_violations = list(error.violations)
                    except Exception as error:
                        failure_state = _provider_failure_state(error)
                        failure_reason = type(error).__name__  # Never persist credentials from SDK errors.
                        repair_violations = [
                            "이전 출력이 유효한 JSON 객체로 파싱되지 않았습니다."
                        ]
                    captured = runner.last_record
                    usage = captured.get("usage", {})
                    input_tokens = usage.get("prompt_tokens", input_tokens)
                    output_tokens = usage.get("completion_tokens", output_tokens)
                    cost = usage.get("cost", cost)
                    attempt = CandidateAttempt(config.label, case.id, case.category, run_number,
                        (time.perf_counter() - started) * 1000, cost, input_tokens, output_tokens,
                        score, failure_state, failure_reason)
                    attempts.append(attempt)
                    record = attempt.as_dict()
                    record.update(captured)
                    record.update({"execution_id": execution_id, "attempt_id": f"{execution_id}:{call}",
                        "call": call, "model": config.model, "model_version": config.model,
                        "tier": MODELS.get(config.model, "mock" if config.provider == "mock" else "custom"),
                        "parent_basic_execution_id": (parent_links or {}).get(execution_id),
                        "request_settings": REQUEST_SETTINGS if config.provider != "mock" else {},
                        "cost_usd": cost, "cost_source": captured.get("cost_source",
                            "mock" if config.provider == "mock" else "unknown"),
                        "raw_output": captured.get("raw_output", raw_output),
                        "parsed_output": raw_output, "parse_valid": isinstance(raw_output, dict), "schema_valid": schema_valid,
                        "validator_valid": validator_valid,
                        "validated_output": response.model_dump(mode="json") if response else None,
                        "labels": label_signature(response, case.exclude_job_alignment_and_status) if response else None,
                        "semantic_evaluation": evaluate_semantic(case, raw_output, reviews.get(f"{execution_id}:{call}")),
                        "metrics": {"label_accuracy": score.judgement_correct / score.judgement_total if score else None,
                            "evidence_accuracy": score.evidence_correct / score.evidence_total
                                if score and score.evidence_total else None,
                            "ids": id_metrics(raw_output, case.context)},
                        "score": score.model_dump() if score else None})
                    if score:
                        score.semantic_evaluation = record["semantic_evaluation"]
                        record["score"] = score.model_dump()
                    records.append(record)
                    if failure_state is None:
                        break
                    repair_previous_output = captured.get("raw_output", raw_output)
    unused_reviews = set(reviews) - {r["attempt_id"] for r in records}
    if unused_reviews:
        raise ValueError("실행되지 않은 재시도에 검토 결과가 연결되어 있습니다")
    report = {"generated_at": datetime.now(UTC).isoformat(),
        "versions": {"dataset_sha256": digest([c.model_dump(mode="json") for c in cases]),
            "dataset_version": sorted({c.dataset_version for c in cases}),
                "grader": GRADER_VERSION, "policy": POLICY_VERSION, "grader_sha256": digest([(PROJECT_ROOT / "evals" / name).read_text(encoding="utf-8")
                for name in ("coaching_dataset.py", "evaluation_records.py", "semantic_grader.py")]),
            "config": CONFIG_VERSION, "config_sha256": digest({"candidates": [asdict(c) for c, _ in candidates],
                "settings": REQUEST_SETTINGS, "repeats": repeats, "max_calls": max_calls}),
            "schema_sha256": digest(CoachingLLMOutput.model_json_schema()),
                "schema_implementation_sha256": digest((PROJECT_ROOT / "backend/app/schemas/coaching.py").read_text(encoding="utf-8"))},
        "model_configs": [{**asdict(c), "tier": MODELS.get(c.model, "custom"),
                           "request_settings": REQUEST_SETTINGS} for c, _ in candidates],
        "dataset": {"cases": len(cases), "distribution": dataset_summary(cases), "repeats": repeats},
        "candidates": _summarize_attempts(attempts), "attempts": records}
    for label, summary in report["candidates"].items():
        selected = [r for r in records if r["candidate"] == label]
        final = {r["execution_id"]: r for r in selected}
        summary["semantic_quality"] = summarize_semantic([r["semantic_evaluation"] for r in final.values()])
        call_quality = summarize_semantic([r["semantic_evaluation"] for r in selected])
        summary["critical_failure_by_call"] = {key: call_quality[key] for key in
            ("critical_failure_reviewed", "critical_failure_count", "critical_failure_rate")}
        summary["executions"] = len(final)
        summary["final_contract_rate"] = sum(r["contract_valid"] for r in final.values()) / len(final)
        summary["metrics"] = {key: _mean([r["metrics"][key] for r in final.values()])
                              for key in ("label_accuracy", "evidence_accuracy")}
        dimensions = {key for r in final.values() if r["score"] for key in r["score"]["label_results"]}
        summary["label_accuracy_by_dimension"] = {
            key: _mean([int(r["score"]["label_results"][key]) for r in final.values()
                        if r["score"] and key in r["score"]["label_results"]]) for key in sorted(dimensions)}
        summary["id_reference_accuracy"] = _mean([r["metrics"]["ids"]["accuracy"]
                                                   for r in final.values() if r["metrics"]["ids"]])
        summary["consistency_by_case"] = {case.id: consistency([r for r in final.values() if r["case_id"] == case.id])
                                           for case in cases}
    if configuration is not None:
        report["configuration"] = configuration
    return report


def _mean(values):
    known = [v for v in values if v is not None]
    return sum(known) / len(known) if known else None


def _provider_failure_state(error: Exception) -> str:
    name = (
        error.error_type.lower()
        if isinstance(error, IsolatedProviderError)
        else type(error).__name__.lower()
    )
    if "timeout" in name:
        return "timeout"
    if "ratelimit" in name or "rate_limit" in name:
        return "rate_limited"
    if "jsondecodeerror" in name or "valueerror" in name:
        return "schema_violation"
    if isinstance(error, (json.JSONDecodeError, ValueError)):
        return "schema_violation"
    return "provider_error"


def _summarize_attempts(
    attempts: list[CandidateAttempt],
) -> dict[str, dict[str, object]]:
    summaries: dict[str, dict[str, object]] = {}
    for candidate in sorted({item.candidate for item in attempts}):
        selected = [item for item in attempts if item.candidate == candidate]
        latencies = sorted(item.latency_ms for item in selected)
        valid = [item for item in selected if item.score is not None]
        failures = Counter(
            item.failure_state for item in selected if item.failure_state is not None
        )
        summaries[candidate] = {
            "attempts": len(selected),
            "contract_rate": round(len(valid) / len(selected), 6),
            "accuracy": round(
                sum(item.score.accuracy for item in valid) / len(selected), 6
            ),
            "cost_usd": round(sum(item.cost_usd or 0 for item in selected), 8),
            "unknown_cost_calls": sum(item.cost_usd is None for item in selected),
            "p50_ms": round(_percentile(latencies, 0.50), 3),
            "p95_ms": round(_percentile(latencies, 0.95), 3),
            "failures": dict(sorted(failures.items())),
        }
    return summaries


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    index = max(0, math.ceil(len(values) * quantile) - 1)
    return values[index]


def build_system_prompt(skill_text: str, prompt_version: str, skill_version: str) -> str:
    return build_coaching_system_prompt(skill_text, prompt_version, skill_version)


def write_report(report: dict[str, object], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "comparison.json"
    markdown_path = output_dir / "comparison.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    candidates = report["candidates"]
    lines = [
        "# 모델 비교 결과",
        "",
        f"- 생성 시각: {report['generated_at']}",
        f"- 평가셋: {report['dataset']['cases']}건 × {report['dataset']['repeats']}회",
    ]
    configuration = report.get("configuration")
    if isinstance(configuration, dict):
        lines.extend(
            [
                f"- Prompt 버전: `{configuration['prompt_version']}`",
                f"- Prompt SHA-256: `{configuration['prompt_sha256']}`",
                f"- Skill 버전: `{configuration['skill_version']}`",
                f"- 기준 버전: `{configuration['criteria_version']}`",
                f"- Skill 묶음 SHA-256: `{configuration['skill_bundle_sha256']}`",
            ]
        )
    lines.extend(
        [
            "",
            "| 후보 | 계약 준수율 | 정확도 | Label | Evidence | ID | 알려진 비용(USD) | 비용 미확인 호출 | p50(ms) | p95(ms) | 실패 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for label, summary in candidates.items():
        lines.append(
            "| {label} | {contract:.1%} | {accuracy:.1%} | {labels} | {evidence} | {ids} | {cost:.6f} | {unknown} | "
            "{p50:.1f} | {p95:.1f} | {failures} |".format(
                label=label,
                contract=summary["contract_rate"],
                accuracy=summary["accuracy"],
                labels=summary["metrics"]["label_accuracy"],
                evidence=summary["metrics"]["evidence_accuracy"],
                ids=summary["id_reference_accuracy"],
                unknown=summary["unknown_cost_calls"],
                cost=summary["cost_usd"],
                p50=summary["p50_ms"],
                p95=summary["p95_ms"],
                failures=json.dumps(summary["failures"], ensure_ascii=False),
            )
        )
    lines.extend(
        [
            "",
            "> 정확도는 기대 status·의도·공고·기준 판정과 필수 근거의 규칙 기반 일치율입니다.",
            "> 비용은 usage.cost 우선이며 unknown_cost_calls가 있으면 합계는 알려진 비용만 포함합니다.",
            "",
        ]
    )
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, markdown_path


def parse_prices(values: list[str]) -> dict[str, tuple[float, float]]:
    prices: dict[str, tuple[float, float]] = {}
    for value in values:
        try:
            label, raw_prices = value.split("=", 1)
            input_price, output_price = raw_prices.split(",", 1)
            prices[label] = (float(input_price), float(output_price))
        except ValueError as error:
            raise ValueError(
                "price는 label=input_usd_per_million,output_usd_per_million 형식입니다"
            ) from error
    return prices


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=PROJECT_ROOT / "evals" / "dataset.v2.jsonl",
    )
    parser.add_argument("--candidate", action="append", default=[])
    parser.add_argument("--six-models", action="store_true")
    parser.add_argument("--max-calls", type=int, default=1)
    parser.add_argument("--semantic-reviews", type=Path, help="attempt ID별 사람 검토 JSON")
    parser.add_argument("--price", action="append", default=[])
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=float, default=45.0)
    parser.add_argument("--case-id", action="append")
    parser.add_argument("--max-completion-tokens", type=int, default=2048)
    parser.add_argument(
        "--skill-file", type=Path, default=PROJECT_ROOT / "skills" / "interview-coach" / "SKILL.md"
    )
    parser.add_argument(
        "--prompt-version", default=DEFAULT_COACHING_PROMPT_VERSION
    )
    parser.add_argument("--skill-version", default="interview-coach-v4")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT
        / "local-results"
        / f"model-comparison-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
    )
    args = parser.parse_args()
    load_evaluation_env()

    if args.six_models:
        args.candidate.extend(f"{model}=openai:{model}" for model in MODELS)
    if args.max_calls < 1:
        parser.error("max-calls must be positive")
    if len(args.candidate) < 2:
        parser.error("비교할 candidate를 두 개 이상 지정하세요")
    if args.repeats < 1:
        parser.error("repeats는 1 이상이어야 합니다")
    if args.max_completion_tokens < 1:
        parser.error("--max-completion-tokens는 1 이상이어야 합니다")
    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds는 0보다 커야 합니다")

    cases = load_dataset(args.dataset)
    if len(cases) < 30:
        parser.error("평가셋은 30건 이상이어야 합니다")

    try:
        cases = select_cases(cases, args.case_id)
    except ValueError as error:
        parser.error(str(error))

    prices = parse_prices(args.price)
    configs: list[CandidateConfig] = []
    for raw_candidate in args.candidate:
        config = CandidateConfig.parse(raw_candidate)
        input_price, output_price = prices.get(config.label, (0.0, 0.0))
        configs.append(
            CandidateConfig(
                label=config.label,
                provider=config.provider,
                model=config.model,
                input_usd_per_million=input_price,
                output_usd_per_million=output_price,
            )
        )

    try:
        skill_bundle: SkillBundle = load_skill_bundle(args.skill_file)
    except CoachingSkillError as error:
        parser.error(str(error))
    if args.skill_version != skill_bundle.catalog.skill_version:
        parser.error(
            "--skill-version이 criteria.json과 다릅니다: "
            f"{args.skill_version} != {skill_bundle.catalog.skill_version}"
        )
    for case in cases:
        unknown_ids = sorted(
            set(case.context.active_criterion_ids) - skill_bundle.criterion_ids
        )
        if unknown_ids:
            parser.error(
                f"{case.id}가 Skill에 없는 criterion id를 사용합니다: "
                + ", ".join(unknown_ids)
            )
    system_prompt = build_system_prompt(
        skill_bundle.rules_text,
        args.prompt_version,
        args.skill_version,
    )
    runners: list[tuple[CandidateConfig, CandidateRunner]] = []
    for config in configs:
        if config.provider == "mock":
            runner: CandidateRunner = MockCandidateRunner(config.model)
        else:
            try:
                api_key, base_url = resolve_provider_credentials(require_openrouter=args.six_models)
            except ValueError as error:
                parser.error(str(error))
            runner = OpenAICompatibleRunner(
                config,
                system_prompt=system_prompt,
                api_key=api_key,
                base_url=base_url,
                timeout_seconds=args.timeout_seconds,
                max_completion_tokens=args.max_completion_tokens,
            )
        runners.append((config, runner))

    report = run_comparison(
        cases,
        runners,
        repeats=args.repeats,
        max_calls=args.max_calls,
        semantic_reviews=json.loads(args.semantic_reviews.read_text()) if args.semantic_reviews else None,
        configuration={
            "prompt_version": args.prompt_version,
            "skill_version": skill_bundle.catalog.skill_version,
            "criteria_version": skill_bundle.catalog.criteria_version,
            "skill_bundle_sha256": skill_bundle.sha256,
            "prompt_sha256": prompt_sha256(system_prompt),
        },
    )
    json_path, markdown_path = write_report(report, args.output_dir)
    print(json_path)
    print(markdown_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
