import json
import os
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE_URL = "https://openrouter.ai/api/v1"
MODELS = [
    #"google/gemini-3.5-flash-lite",
    # "openai/gpt-5.6-luna",
    # "google/gemini-3.8-flash",
    # "openai/gpt-5.6-terra",
    "~deepseek/deepseek-pro-latest",
]

# 2026-09-21 Final Four의 고정 30건 계약 평가 결과. 자유 질문의 품질 점수는 아니다.
BENCHMARK_SCORES = {
    "google/gemini-3.5-flash-lite": (30, 30, 3.41, 4.20, 0.10706534),
    "google/gemini-3.8-flash": (30, 30, 12.60, 21.28, 0.34932900),
    "openai/gpt-5.6-luna": (29, 30, 9.36, 13.77, 0.03914948),
    "openai/gpt-5.6-terra": (10, 30, 1.18, 8.29, 0.10570740),
}

question = """
당신은 신입 백엔드 개발자 면접 코치입니다.
아래 답변을 보고, 면접관이 추가로 확인할 질문을 한 개만 해주세요.
답변에 없는 사실이나 성과는 만들지 마세요.

답변:
주문 API의 응답 시간이 길어졌습니다. 로그와 APM을 확인해 상품 조회 쿼리가 반복 실행되는 것을 발견했습니다. 제가 조회 로직을 조정하고 필요한 인덱스를 추가한 뒤, 부하 테스트에서 평균 응답 시간이 1.8초에서 400ms로 줄어든 것을 확인했습니다..
"""

def benchmark_summary(model: str) -> str:
    score = BENCHMARK_SCORES.get(model)
    if score is None:
        return "not measured (Final Four 30건 평가 대상 아님)"

    contract_passed, total, p50_seconds, p95_seconds, cost_usd = score
    return (
        f"contract {contract_passed}/{total} | p50 {p50_seconds:.2f}s | "
        f"p95 {p95_seconds:.2f}s | cost ${cost_usd:.5f} / {total} calls"
    )

def run_probe(api_key: str) -> None:
    for model in MODELS:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": question}],
        }
        request = Request(
            f"{BASE_URL}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        started = time.perf_counter()
        try:
            with urlopen(request, timeout=60) as response:
                body = json.load(response)

            elapsed = time.perf_counter() - started
            answer = body["choices"][0]["message"]["content"]
            usage = body.get("usage", {})

            print(f"\n{'=' * 70}")
            print(f"MODEL: {model}")
            print(f"BENCHMARK: {benchmark_summary(model)}")
            print(f"LIVE: {elapsed:.2f}s | USAGE: {json.dumps(usage, ensure_ascii=False)}")
            print(f"\nANSWER:\n{answer}")
        except HTTPError as error:
            print(f"\nMODEL: {model}")
            print(f"HTTP {error.code}: {error.read().decode('utf-8', errors='replace')}")
        except Exception as error:
            print(f"\nMODEL: {model}")
            print(f"ERROR: {type(error).__name__}: {error}")


def main() -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY 환경 변수를 설정해 주세요.")
    run_probe(api_key)


if __name__ == "__main__":
    main()
