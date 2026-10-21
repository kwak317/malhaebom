# Worklog — 후보 모델 30건 확장 평가

- 일시: 2026-09-21 10:20 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: #22, #32, PR #19
- 관련 요구사항/결정: `docs/experiments/2026-09-21_candidate-30case-extension.md`

## 1. 목적

사전 점검 단계였던 GPT-5 nano·Gemini 3.5 Flash·Qwen3 4B·EEVE Korean 2.8B Q4를 합성 30건으로 확장 측정한다.

## 2. 작업 전 상태

- API 두 후보와 로컬 두 후보는 한 건 사전 점검 결과만 있었다.
- Qwen3와 EEVE는 이미 서버 출력 계약을 위반한 기록이 있었다.

## 3. 수행 내용

1. 후보별 endpoint·출력 상한·timeout을 실험 문서에 기록했다.
2. Gemini 3.5 Flash와 GPT-5 nano를 30건씩 실행했다.
3. Qwen3와 EEVE를 30건씩 실행했으나 timeout 이후에도 Ollama 요청이 종료되지 않아 artifact를 만들지 못했다.
4. 해당 평가 Python 프로세스만 종료하고 timeout 문제를 Issue #32에 기록했다.

## 주요 판단과 이유

- 로컬 모델은 2K 문맥 제약 때문에 768 tokens·45초를 사용했다. API 모델과 지연·비용을 절대 비교하지 않는다.
- 멈춘 평가를 계속 두지 않고 정확히 식별한 프로세스만 종료했다. 결과 파일이 없으므로 로컬 30건 결과를 추정하거나 성공으로 기록하지 않았다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `docs/experiments/2026-09-21_candidate-30case-extension.md` | 실행 조건과 API·로컬 결과 상태 기록 |
| `docs/worklogs/2026-09-21_1020_candidate-30case-extension.md` | 수행·검증·미해결 사항 기록 |

## 5. 검증

```text
API 30건: local-results/api-candidate-30cases-20260921/comparison.md
Gemini 3.5 Flash: 계약 96.7%, 정확도 63.9%, p95 19.16초
GPT-5 nano: 계약 16.7%, 정확도 13.7%, p95 6.99초

로컬 30건: comparison.json 미생성
Ollama qwen3:4b GPU 실행 상태와 timeout 초과 확인
Issue #32 등록
```

## 6. 발견한 문제 / 남은 리스크

- Ollama OpenAI-compatible 요청의 timeout이 장시간 실행을 실제 종료시키지 못한다.
- API runner는 계약 위반 요청 비용을 0으로 덮어쓴다(Issue #22).

## 미확인 사항

- timeout/retry 수정 후 Qwen3·EEVE가 30건을 완주하는지 확인하지 않았다.
- 사람 검토와 별도 고유 100건 평가는 수행하지 않았다.

## 7. 다음 작업

- Issue #32를 해결한 후 로컬 후보 30건을 재실행한다.
- Terra와 Gemini 3.5 Flash를 별도 고유 100건·사람 검토로 비교한다.

## 8. PR #19 리뷰 반영

- `evals/run_model_comparison.py`의 병합 잔여 request 조립·중복 `base_url`을 제거하고, 현재 평가 기록 정책의 strict response format·provider routing을 복구했다.
- Windows 기본 cp949 인코딩으로 인한 평가 메타데이터 해시 오류를 피하도록 source 읽기에 UTF-8을 명시했다.
- `CURRENT_STATE.md`의 중복 평가 상태와 `EVAL_REPORT.md`의 중복 표·섹션을 하나의 최신 구조로 정리했다.
- 검증: `python -m unittest backend.tests.test_coaching_eval backend.tests.test_evaluation_records` 14개 통과, `python -m unittest discover -s backend/tests` 233개 통과.

## 9. 후속 리뷰 반영

- `OpenAICompatibleRunner.generate()`가 실제 요청에 후보별 `response_format`, GPT-5 `reasoning_effort`, `max_completion_tokens`를 포함하도록 수정했다. 최신 main의 OpenRouter routing 옵션과 temperature 미지정 정책은 유지했다.
- 실제 runner를 대체 클라이언트로 호출하는 회귀 테스트에서 위 요청 필드를 함께 검증한다.
- `EVAL_REPORT.md`는 최신 main 본문을 복원하고, 이 PR의 보조 30건 결과만 9절로 추가했다.
