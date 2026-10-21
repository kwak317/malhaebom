#!/usr/bin/env python3
"""같은 모델로 범용 면접 피드백과 말해봄 코칭을 나란히 기록한다.

기본 mock 모드는 외부 호출 없이 리포트 형식만 검증한다. ``--mode live``는
MODEL_API_KEY와 MODEL_API_BASE_URL을 사용하며, 합성 평가 입력만 전송한다.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
for import_path in (PROJECT_ROOT, BACKEND_ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from app.schemas.coaching import CoachingLLMOutput  # noqa: E402
from app.services.coaching_prompt import (  # noqa: E402
    DEFAULT_COACHING_PROMPT_VERSION,
    build_coaching_system_prompt,
    build_contract_repair_user_prompt,
)
from app.services.coaching_skill import load_skill_bundle  # noqa: E402
from evals.coaching_dataset import CoachingEvaluationCase, load_dataset  # noqa: E402
from evals.environment import load_evaluation_env, resolve_provider_credentials  # noqa: E402
from pydantic import ValidationError  # noqa: E402
from evals.run_model_comparison import (  # noqa: E402
    CandidateConfig,
    build_expected_output,
    build_response_format,
    reasoning_effort_for,
    select_cases,
)
from services.llm import OutputContractError, validate_and_build_response  # noqa: E402


GENERIC_SYSTEM_PROMPT = """당신은 한국어 면접 답변 코치입니다.
사용자의 질문과 답변만 보고, 개선에 도움이 되는 자연스러운 피드백을 한국어로 작성하세요.
답변에 없는 경험이나 성과를 사실처럼 만들지 마세요."""


def build_generic_user_prompt(case: CoachingEvaluationCase) -> dict[str, str]:
    """Keep the generic condition free of job, rubric, and server context."""

    return {
        "question": case.question.text,
        "answer": "\n".join(segment.text for segment in case.context.answer_segments),
    }


def resolve_case_ids(case_ids: list[str] | None) -> list[str]:
    """Use the sample case only when the caller did not name any case."""

    return case_ids or ["coach-normal-01"]


def _usage(payload: dict[str, Any]) -> dict[str, int | float | str | None]:
    usage = payload.get("usage") or {}
    choice = (payload.get("choices") or [{}])[0]
    return {
        "input_tokens": usage.get("prompt_tokens"),
        "output_tokens": usage.get("completion_tokens"),
        "cost_usd": usage.get("cost"),
        "finish_reason": choice.get("finish_reason"),
    }


def _request(
    client: Any,
    *,
    model: str,
    system_prompt: str,
    user_payload: object,
    max_completion_tokens: int,
    response_format: dict[str, Any] | None,
    ) -> tuple[object, dict[str, int | float | str | None], float]:
    request: dict[str, Any] = {
        "model": model,
        "max_completion_tokens": max_completion_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    user_payload
                    if isinstance(user_payload, str)
                    else json.dumps(user_payload, ensure_ascii=False)
                ),
            },
        ],
    }
    if response_format is not None:
        request["response_format"] = response_format
        request["extra_body"] = {"provider": {"require_parameters": True}}
        reasoning_effort = reasoning_effort_for(CandidateConfig("malhaebom", "openai", model))
        if reasoning_effort is not None:
            request["reasoning_effort"] = reasoning_effort

    started = time.perf_counter()
    completion = client.chat.completions.create(**request)
    latency_ms = round((time.perf_counter() - started) * 1000, 3)
    payload = completion.model_dump(mode="json")
    content = (payload.get("choices") or [{}])[0].get("message", {}).get("content")
    if response_format is None:
        return content or "", _usage(payload), latency_ms
    return _decode_structured_content(content), _usage(payload), latency_ms


def _decode_structured_content(content: object) -> object:
    """Decode one provider-added JSON string envelope around the required object."""

    if not isinstance(content, str) or not content:
        return None
    try:
        decoded = json.loads(content)
    except json.JSONDecodeError:
        return content
    if isinstance(decoded, str):
        try:
            return json.loads(decoded)
        except json.JSONDecodeError:
            return decoded
    return decoded


def _mock_case(case: CoachingEvaluationCase) -> dict[str, object]:
    answer = build_generic_user_prompt(case)["answer"]
    return {
        "case_id": case.id,
        "question": case.question.text,
        "answer": answer,
        "generic": {
            "output": "문제 상황과 본인 행동, 결과를 순서대로 조금 더 구체적으로 설명해 보세요.",
            "failure": None,
            "latency_ms": 0.0,
        },
        "malhaebom": {
            "output": build_expected_output(case),
            "failure": None,
            "latency_ms": 0.0,
            "contract_valid": True,
        },
    }


def _live_case(
    client: Any,
    case: CoachingEvaluationCase,
    *,
    model: str,
    system_prompt: str,
    max_completion_tokens: int,
) -> dict[str, object]:
    result: dict[str, object] = {
        "case_id": case.id,
        "question": case.question.text,
        "answer": build_generic_user_prompt(case)["answer"],
    }
    try:
        generic_output, generic_usage, generic_latency = _request(
            client,
            model=model,
            system_prompt=GENERIC_SYSTEM_PROMPT,
            user_payload=build_generic_user_prompt(case),
            max_completion_tokens=max_completion_tokens,
            response_format=None,
        )
        result["generic"] = {
            "output": generic_output,
            "failure": None,
            "latency_ms": generic_latency,
            **generic_usage,
        }
    except Exception as error:
        result["generic"] = {"output": None, "failure": type(error).__name__}

    malhaebom_output: object | None = None
    try:
        malhaebom_output, malhaebom_usage, malhaebom_latency = _request(
            client,
            model=model,
            system_prompt=system_prompt,
            user_payload={
                "question": case.question.model_dump(mode="json"),
                "server_context": case.context.model_dump(mode="json"),
            },
            max_completion_tokens=max_completion_tokens,
            response_format=build_response_format(CandidateConfig("malhaebom", "openai", model)),
        )
        repair_attempted = False
        try:
            CoachingLLMOutput.model_validate(malhaebom_output)
            validate_and_build_response(malhaebom_output, case.context)
        except (ValidationError, OutputContractError) as error:
            repair_attempted = True
            violations = (
                [
                    ".".join(str(part) for part in item["loc"])
                    + ": "
                    + item["msg"]
                    for item in error.errors()
                ]
                if isinstance(error, ValidationError)
                else error.violations
            )
            repair_prompt = build_contract_repair_user_prompt(
                json.dumps(
                    {
                        "question": case.question.model_dump(mode="json"),
                        "server_context": case.context.model_dump(mode="json"),
                    },
                    ensure_ascii=False,
                ),
                malhaebom_output,
                violations,
            )
            repaired_output, repaired_usage, repaired_latency = _request(
                client,
                model=model,
                system_prompt=system_prompt,
                user_payload=repair_prompt,
                max_completion_tokens=max_completion_tokens,
                response_format=build_response_format(
                    CandidateConfig("malhaebom", "openai", model)
                ),
            )
            malhaebom_output = repaired_output
            malhaebom_usage = repaired_usage
            malhaebom_latency += repaired_latency
            CoachingLLMOutput.model_validate(malhaebom_output)
            validate_and_build_response(malhaebom_output, case.context)
        result["malhaebom"] = {
            "output": malhaebom_output,
            "failure": None,
            "latency_ms": malhaebom_latency,
            "contract_valid": True,
            "repair_attempted": repair_attempted,
            **malhaebom_usage,
        }
    except ValidationError as error:
        result["malhaebom"] = {
            "output": malhaebom_output,
            "failure": type(error).__name__,
            "contract_valid": False,
            "validation_error_fields": [
                ".".join(str(part) for part in item["loc"])
                for item in error.errors()
            ],
        }
    except OutputContractError as error:
        result["malhaebom"] = {
            "output": malhaebom_output,
            "failure": type(error).__name__,
            "contract_valid": False,
            "validation_error_fields": error.violations,
        }
    except Exception as error:
        result["malhaebom"] = {
            "output": malhaebom_output,
            "failure": type(error).__name__,
            "contract_valid": False,
        }
    return result


def render_markdown_report(report: dict[str, object]) -> str:
    lines = [
        "# 범용 AI와 말해봄 비교",
        "",
        f"- 모델: `{report['model']}`",
        f"- 실행 모드: `{report['mode']}`",
        "- 공정성: 사례별로 모델 ID·질문·사용자 답변·max completion token은 동일합니다.",
        "- 차이: 범용 AI에는 질문·답변만, 말해봄에는 고정 Skill·서버 문맥·구조화 출력 계약을 제공합니다.",
        "- 주의: 범용 AI 응답은 정확도 점수로 환산하지 않습니다. 이는 일반 피드백과 프로젝트 경로의 질적 비교 자료입니다.",
        "",
    ]
    for case in report["cases"]:
        generic = case["generic"]
        malhaebom = case["malhaebom"]
        lines.extend(
            [
                f"## {case['case_id']}",
                "",
                "### 입력",
                "",
                f"- 질문: {case['question']}",
                f"- 답변: {case['answer']}",
                "",
                "### 범용 AI",
                "",
                str(generic["output"] or f"실패: {generic['failure']}"),
                *(
                    [f"- provider 종료 이유: `{generic['finish_reason']}`"]
                    if generic.get("finish_reason")
                    else []
                ),
                "",
                "### 말해봄",
                "",
                "```json",
                json.dumps(malhaebom["output"], ensure_ascii=False, indent=2)
                if malhaebom["output"] is not None
                else f"실패: {malhaebom['failure']}",
                "```",
                f"- 계약 검증: {'통과' if malhaebom.get('contract_valid') else '실패'}",
                *(
                    [f"- provider 종료 이유: `{malhaebom['finish_reason']}`"]
                    if malhaebom.get("finish_reason")
                    else []
                ),
                *(
                    [
                        "- 검증 실패 필드: "
                        + ", ".join(malhaebom["validation_error_fields"])
                    ]
                    if malhaebom.get("validation_error_fields")
                    else []
                ),
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("mock", "live"), default="mock")
    parser.add_argument("--model", default="google/gemini-3.5-flash-lite")
    parser.add_argument("--dataset", type=Path, default=PROJECT_ROOT / "evals" / "dataset.v2.jsonl")
    parser.add_argument("--case-id", action="append")
    parser.add_argument("--max-completion-tokens", type=int, default=2048)
    parser.add_argument("--skill-file", type=Path, default=PROJECT_ROOT / "skills" / "interview-coach" / "SKILL.md")
    parser.add_argument("--prompt-version", default=DEFAULT_COACHING_PROMPT_VERSION)
    parser.add_argument("--skill-version", default="interview-coach-v4")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "local-results" / "generic-vs-malhaebom")
    args = parser.parse_args()
    if args.max_completion_tokens < 1:
        parser.error("--max-completion-tokens는 1 이상이어야 합니다")

    cases = select_cases(load_dataset(args.dataset), resolve_case_ids(args.case_id))
    report: dict[str, object] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": args.mode,
        "model": args.model,
        "cases": [],
    }
    if args.mode == "mock":
        report["cases"] = [_mock_case(case) for case in cases]
    else:
        load_evaluation_env()
        api_key, base_url = resolve_provider_credentials(require_openrouter=False)
        from openai import OpenAI

        bundle = load_skill_bundle(args.skill_file)
        if args.skill_version != bundle.catalog.skill_version:
            parser.error("--skill-version이 criteria.json과 다릅니다")

        report["configuration"] = {
            "model": args.model,
            "prompt_version": args.prompt_version,
            "skill_version": args.skill_version,
            "criteria_version": bundle.catalog.criteria_version,
            "max_completion_tokens": args.max_completion_tokens,
            "dataset": str(args.dataset),
            "case_ids": [case.id for case in cases],
        }
        system_prompt = build_coaching_system_prompt(
            bundle.rules_text, args.prompt_version, args.skill_version
        )
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=45.0, max_retries=0)
        report["cases"] = [
            _live_case(client, case, model=args.model, system_prompt=system_prompt,
                       max_completion_tokens=args.max_completion_tokens)
            for case in cases
        ]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "comparison.json"
    markdown_path = args.output_dir / "comparison.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown_report(report) + "\n", encoding="utf-8")
    print(json_path)
    print(markdown_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
