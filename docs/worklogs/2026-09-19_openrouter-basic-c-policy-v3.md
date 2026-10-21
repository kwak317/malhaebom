# Worklog — C 판정 기준 확정 및 Basic 전체 재평가

- 일시: 2026-09-19
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 요구사항/결정: `docs/DECISIONS.md`, `docs/specs/coaching-evaluation-ops.md`

## 1. 목적

C 최소 판정 기준을 Skill과 평가셋에 일치시키고, 관련 회귀 검증 후 Basic 3종×dataset v2 30건을
새 기준으로 다시 평가한다. 기존 결과와 분리하고 Premium은 호출하지 않는다.

## 2. 작업 전 상태

정책 재검증 27회에서 case14/18/20/21/22의 C가 세 모델 공통 실패였다. 후속 검토에서
case14/18/21/22는 partial, case20은 met이 C 정의와 일관된 것으로 확정됐다.

## 3. 수행 내용

- Skill, criteria, 평가 문서에 C met/partial/not_observed 기준과 독립 판정 원칙을 명시했다.
- dataset v2의 case14/18/21/22 C를 partial로 변경하고 case20 met을 재확인했다.
- 평가 버전 및 관련 회귀 기대값을 갱신했다.
- `.venv-llm-eval`에서 Basic 3종×30건 90개 요청을 실행하고 case/run별 raw 결과를 저장했다.
- 오프라인 보고서로 계약, label, evidence/ID, latency, token/cache/reasoning, 비용과 실패 유형을 집계했다.

## 주요 판단과 이유

C에는 원인, 개인 행동, 검증 결과, 질문의 직무 적합성을 섞지 않는다. Qwen case29는 요청이 약 12분간
반환되지 않아 재호출하면 중복 비용이 생길 수 있으므로 중단하고 인프라 timeout으로 기록했다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `skills/SKILL.md`, `skills/problem-solving.md`, `skills/criteria.json` | C 판정 기준 명시 |
| `evals/dataset.v2.jsonl` | 지정 4건 C partial 반영, case20 met 유지 |
| `evals/evaluation_records.py`, `evals/run_model_comparison.py` | 정책/prompt 버전 갱신 |
| `backend/app/services/coaching_observability.py` | prompt 기본 버전 갱신 |
| `backend/tests/test_coaching_eval_v2.py` | C 기대값 회귀 테스트 갱신 |
| `docs/specs/coaching-evaluation-ops.md`, `evals/README.md`, `docs/DECISIONS.md` | 평가 정책 문서화 |
| `docs/experiments/2026-09-19_openrouter-basic-c-policy-v3.md` | 실행 조건과 결과 기록 |
| `local-results/openrouter-basic-full-c-policy-20260919/` | 별도 raw/집계/검증 결과 |

## 5. 검증

```text
focused evaluation tests: 12 passed
policy alignment tests: 9 passed
final focused regression (eval v2 + policy alignment + evaluation records): 22 passed
backend full suite: 226 passed in 2.169s
Python 3.12 mock: dataset 30 expected accuracy=1, contract valid=30
git diff --check: passed (API 실행 전)
offline result verification: 90 unique attempts, Premium 0, retry 0,
source hashes unchanged, semantic scores null
```

실제 평가 결과는 Qwen 계약24/30·품질14/15/인프라1, DeepSeek 계약30/30·품질23/7/0,
Gemini 계약30/30·품질25/5/0이다. 비용 확인89건 합계는 $0.5464719216이고 timeout1건은 미확인이다.

## 6. 발견한 문제 / 남은 리스크

- Qwen case29에서 SDK 60초 설정이 전체 요청 종료를 보장하지 않아 driver watchdog이 필요하다.
- 실행 당시 prompt label은 `coaching-output-v2`이나 prompt 본문과 snapshot에는 새 C 정책이 들어 있다.
- 자동 critical 검사는 3개 case/모델, 총 9회 범위이며 전체 hallucination 판정이 아니다.

## 미확인 사항

- 사람 semantic 0~2 평가는 모두 null이다.
- 한 모델·case당 1회여서 consistency는 측정하지 않았다.
- timeout 응답이 없으므로 Qwen case29 provider/token/cost/generation ID는 알 수 없다.

## 7. 다음 작업

- Premium 호출 전 Basic failure set과 사람 semantic 검토 범위를 확정한다.
- runner에 전체 요청 watchdog을 구현해 SDK timeout 무효 상황을 방지한다.
