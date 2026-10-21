import argparse
import json
import os
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

REPO_URL = "https://github.com/5Headers/team_project_backend"

# 임시 신입 백엔드 공고 기술스택
JOB_STACK = [
    "Java",
    "Spring Boot",
    "JPA",
    "MySQL",
    "Redis",
    "Docker",
    "AWS",
    "GitHub Actions",
]

DEFAULT_MODEL = "openai/gpt-5.6-terra"
FALLBACK_MODEL = "google/gemini-3.8-flash"
MODEL_CHAIN = (DEFAULT_MODEL, FALLBACK_MODEL)


FORBIDDEN_PHRASES = [
    "경험 없음",
    "합격",
    "채용 심사에서 불리",
    "불리하게 작용",
    "역량 부재",
]

SCHEMA = {
    "name": "github_job_fit",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "verified_technologies": {
                "type": "array",
                "items": {"type": "string"},
            },
            "job_stack_comparison": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "technology": {"type": "string"},
                        "status": {
                            "type": "string",
                            "enum": [
                                "verified_in_readme",
                                "not_verified_in_readme",
                            ],
                        },
                        "evidence_quote": {
                            "type": ["string", "null"],
                            "description": (
                                "확인됨이면 README에 있는 실제 연속 원문 인용. "
                                "미확인이면 null."
                            ),
                        },
                        "reason": {"type": "string"},
                    },
                    "required": [
                        "technology",
                        "status",
                        "evidence_quote",
                        "reason",
                    ],
                },
            },
            "recommended_skills": {
                "type": "array",
                "maxItems": 2,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "technology": {"type": "string"},
                        "reason": {"type": "string"},
                        "next_step": {"type": "string"},
                    },
                    "required": ["technology", "reason", "next_step"],
                },
            },
            "clarifying_question": {
                "type": ["string", "null"],
            },
        },
        "required": [
            "verified_technologies",
            "job_stack_comparison",
            "recommended_skills",
            "clarifying_question",
        ],
    },
}

def github_readme_url(repo_url: str) -> str:
    parsed = urlparse(repo_url)
    parts = parsed.path.strip("/").split("/")

    if parsed.netloc != "github.com" or len(parts) < 2:
        raise ValueError("GitHub 저장소 URL 형식이 아닙니다.")

    owner, repo = parts[:2]

    if len(parts) > 2 and parts[2:] != ["blob", "main", "README.md"]:
        raise ValueError("GitHub 저장소 또는 main 브랜치의 README URL만 허용합니다.")

    return f"https://api.github.com/repos/{owner}/{repo}/readme"


def fetch_readme(repo_url: str) -> str:
    request = urllib.request.Request(
        github_readme_url(repo_url),
        headers={"Accept": "application/vnd.github.raw+json"},
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise RuntimeError("README.md를 찾을 수 없습니다.") from error
        raise


def call_model(model: str, readme: str) -> tuple[dict, float, float | None]:
    api_key = os.environ["OPENROUTER_API_KEY"]

    prompt = f"""당신은 취업 준비생의 GitHub README 기술 근거를 검토한다.

규칙:
- README 본문에 명시된 내용만 근거로 사용한다.
- README에서 찾지 못한 기술은 경험 없음이 아니라
  "README 기준 미확인"으로만 표현한다.
- README 밖의 코드, 프로젝트 구조, 일반 지식으로 추론하지 않는다.
- verified_in_readme 상태에는 README에 있는 실제 연속 원문을 evidence_quote에 그대로 넣는다.
- not_verified_in_readme 상태에는 evidence_quote를 null로 넣는다.
- verified_technologies에는 공고 기술스택에 있는 기술만 넣는다.
- job_stack_comparison은 공고 기술스택 전체를 정확히 한 번씩 포함한다.
- recommended_skills는 공고에는 있지만 README에서 확인되지 않은 기술만
  최대 2개 추천한다.
- 추천마다 reason(추천 이유)과 next_step(학습 또는 README 보완 행동)을 쓴다.
- "경험 없음", "합격", "채용 심사에서 불리", "역량 부재" 표현을 사용하지 않는다.
- clarifying_question은 null 또는 물음표(?)로 끝나는 질문 한 개다.

임시 채용공고 기술스택:
{json.dumps(JOB_STACK, ensure_ascii=False)}

README:
{readme}
"""

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {
            "type": "json_schema",
            "json_schema": SCHEMA,
        },
        "provider": {"require_parameters": True},
    }

    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    started_at = time.perf_counter()

    with urllib.request.urlopen(request, timeout=60) as response:
        body = json.load(response)

    elapsed = time.perf_counter() - started_at
    content = body["choices"][0]["message"]["content"]
    cost = body.get("usage", {}).get("cost")

    return validate_result(json.loads(content), readme), elapsed, cost

def should_use_fallback(error: Exception) -> bool:
    if isinstance(error, urllib.error.HTTPError):
        return error.code in {408, 429, 500, 502, 503, 504}

    return isinstance(
        error,
        (
            urllib.error.URLError,
            TimeoutError,
            json.JSONDecodeError,
            ValueError,  # 출력 계약 위반
        ),
    )


def call_with_fallback(
    readme: str,
) -> tuple[str, dict, float, float | None]:
    errors = []

    for model in MODEL_CHAIN:
        try:
            result, elapsed, cost = call_model(model, readme)
            return model, result, elapsed, cost

        except Exception as error:
            errors.append(f"{model}: {error}")

            if model == DEFAULT_MODEL and should_use_fallback(error):
                print(f"Terra 실패 → Gemini fallback 실행: {error}")
                continue

            raise RuntimeError(" | ".join(errors)) from error

    raise RuntimeError("모든 모델 호출이 실패했습니다.")

def validate_result(result: dict, readme: str) -> dict:
    if not isinstance(result, dict):
        raise ValueError("모델 결과는 JSON 객체여야 합니다.")

    comparisons = result.get("job_stack_comparison")
    if not isinstance(comparisons, list) or len(comparisons) != len(JOB_STACK):
        raise ValueError("공고 기술스택 전체 비교 결과가 필요합니다.")

    comparison_by_technology = {}

    for item in comparisons:
        technology = item.get("technology")
        status = item.get("status")
        quote = item.get("evidence_quote")
        reason = item.get("reason")

        if technology in comparison_by_technology or technology not in JOB_STACK:
            raise ValueError("공고에 없는 기술 또는 중복 기술이 있습니다.")

        if status not in {
            "verified_in_readme",
            "not_verified_in_readme",
        }:
            raise ValueError("허용되지 않은 기술 상태입니다.")

        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("기술 비교 이유가 비어 있습니다.")

        if status == "verified_in_readme":
            if not isinstance(quote, str) or not quote.strip():
                raise ValueError("확인된 기술에는 README 원문 인용이 필요합니다.")

            if quote not in readme:
                raise ValueError(
                    f"README에 없는 근거 인용입니다: {technology}"
                )

        if status == "not_verified_in_readme" and quote is not None:
            raise ValueError(
                f"미확인 기술의 evidence_quote는 null이어야 합니다: {technology}"
            )

        comparison_by_technology[technology] = item

    if set(comparison_by_technology) != set(JOB_STACK):
        raise ValueError("JOB_STACK 전체 기술을 정확히 포함해야 합니다.")

    verified = result.get("verified_technologies")
    expected_verified = {
        technology
        for technology, item in comparison_by_technology.items()
        if item["status"] == "verified_in_readme"
    }

    if (
        not isinstance(verified, list)
        or len(verified) != len(set(verified))
        or set(verified) != expected_verified
    ):
        raise ValueError(
            "verified_technologies는 확인된 공고 기술스택과 정확히 일치해야 합니다."
        )

    recommendations = result.get("recommended_skills")
    if not isinstance(recommendations, list) or len(recommendations) > 2:
        raise ValueError("보완 추천은 최대 2개여야 합니다.")

    recommended_technologies = set()

    for item in recommendations:
        technology = item.get("technology")

        if (
            technology in recommended_technologies
            or technology not in comparison_by_technology
            or comparison_by_technology[technology]["status"]
            != "not_verified_in_readme"
        ):
            raise ValueError(
                "추천 기술은 중복 없이 README 기준 미확인 기술만 가능해야 합니다."
            )

        if not all(
            isinstance(item.get(key), str) and item[key].strip()
            for key in ("reason", "next_step")
        ):
            raise ValueError("추천 기술의 이유와 다음 행동이 필요합니다.")

        recommended_technologies.add(technology)

    question = result.get("clarifying_question")

    if question is not None:
        if not isinstance(question, str) or not question.strip().endswith("?"):
            raise ValueError("추가 질문은 물음표로 끝나는 질문 한 개여야 합니다.")

        questioned_technologies = [
            technology
            for technology in JOB_STACK
            if technology.casefold() in question.casefold()
        ]
        unverified_technologies = {
            technology
            for technology, item in comparison_by_technology.items()
            if item["status"] == "not_verified_in_readme"
        }
        if (
            len(questioned_technologies) != 1
            or questioned_technologies[0] not in unverified_technologies
        ):
            raise ValueError("추가 질문은 README 기준 미확인 기술 하나만 대상으로 해야 합니다.")

    output_text = json.dumps(result, ensure_ascii=False)

    for phrase in FORBIDDEN_PHRASES:
        if phrase in output_text:
            raise ValueError(f"금지 표현이 포함됐습니다: {phrase}")

    return result

def format_result(result: dict, elapsed: float, cost: float | None) -> str:
    verified = ", ".join(result["verified_technologies"]) or "없음"

    missing = [
        item["technology"]
        for item in result["job_stack_comparison"]
        if item["status"] == "not_verified_in_readme"
    ]

    lines = [
        f"응답 시간: {elapsed:.2f}초",
        f"비용: ${cost:.6f}" if isinstance(cost, (int, float)) else "비용: 제공되지 않음",
        f"확인됨: {verified}",
        f"README 기준 미확인: {', '.join(missing) or '없음'}",
        "",
        "기술별 비교",
        "-" * 70,
    ]

    for item in result["job_stack_comparison"]:
        status = (
            "확인됨"
            if item["status"] == "verified_in_readme"
            else "README 기준 미확인"
        )

        lines.append(f"- {item['technology']} · {status}")
        quote = item["evidence_quote"]
        lines.append(f"  근거 인용: {quote}" if quote else f"  이유: {item['reason']}")

    lines.extend(["", "보완 추천 기술"])

    if not result["recommended_skills"]:
        lines.append("- 없음")
    else:
        for index, item in enumerate(result["recommended_skills"], start=1):
            lines.append(f"{index}. {item['technology']}")
            lines.append(f"   이유: {item['reason']}")
            lines.append(f"   다음: {item['next_step']}")

    lines.extend([
        "",
        "추가 질문 1개",
        result["clarifying_question"] or "없음",
    ])

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="모델별 반복 횟수. 기본값: 3",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="GitHub와 OpenRouter에 실제 요청을 보냅니다.",
    )
    args = parser.parse_args()

    if args.runs < 1:
        raise ValueError("--runs는 1 이상이어야 합니다.")

    if not args.live:
        print(
            json.dumps(
                {
                    "network_calls": False,
                    "default_model": DEFAULT_MODEL,
                    "fallback_model": FALLBACK_MODEL,
                    "planned_primary_calls": args.runs,
                    "maximum_model_calls": args.runs * len(MODEL_CHAIN),
                },
                ensure_ascii=False,
            )
        )
        return

    readme = fetch_readme(REPO_URL)
    summaries = {
        model: {"uses": 0, "latencies": [], "costs": []}
        for model in MODEL_CHAIN
    }

    for run_number in range(1, args.runs + 1):
        print(f"\n[실행 {run_number}/{args.runs}]")
        try:
            used_model, result, elapsed, cost = call_with_fallback(readme)
            print(f"실제 사용 모델: {used_model}")
            print(format_result(result, elapsed, cost))
            summaries[used_model]["uses"] += 1
            summaries[used_model]["latencies"].append(elapsed)
            if isinstance(cost, (int, float)):
                summaries[used_model]["costs"].append(cost)
        except Exception as error:
            print(f"실패: {error}")

    print(f"\n{'=' * 80}\nFallback 실행 요약")
    for model in MODEL_CHAIN:
        summary = summaries[model]
        latencies = summary["latencies"]
        costs = summary["costs"]
        average_latency = sum(latencies) / len(latencies) if latencies else None
        print(f"{model}\n  실제 사용: {summary['uses']}/{args.runs}")
        print(f"  평균 응답 시간: {average_latency:.2f}초" if average_latency is not None else "  평균 응답 시간: 사용되지 않음")
        print(f"  총 비용: ${sum(costs):.6f}" if costs else "  총 비용: 제공되지 않음")


if __name__ == "__main__":
    main()
