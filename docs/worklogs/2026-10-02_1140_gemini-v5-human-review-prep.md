# Worklog — Gemini v5 자동 불일치 사람 검토 양식

- 일시: 2026-10-02 11:40
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음 (PR 생성 예정)
- 관련 요구사항/결정: D4 평가의 사람 semantic 점수와 자동 label/evidence 점수를 구분한다.

## 1. 목적

Gemini v5 4,096-token 실제 30건에서 계약 유효하지만 자동 label/evidence가 불일치한 응답만
사람이 원문과 semantic rubric으로 검토할 수 있는 local 양식을 만든다.

## 2. 작업 전 상태

30건의 계약은 30/30이고 provider failure는 없었지만, 자동 label/evidence 불일치 7건은
사람 semantic/critical 검토가 없었다. 기존 `--semantic-reviews` 입력은 유효한 review JSON을
받을 수 있으나, 사람이 원본 결과에서 대상을 고르는 절차는 문서화되어 있지 않았다.

## 3. 수행 내용

1. `comparison.json`에서 지정 candidate의 contract-valid attempt 중 label 또는 evidence 정확도가
   1.0 미만인 항목만 고르는 CLI를 추가했다.
2. `SemanticReview` 필드를 비워 둔 JSON template과 원문 입력·모델 출력·rubric을 담은 Markdown을
   `local-results/`에 생성하도록 했다.
3. contract-invalid, 완전 일치, 다른 candidate와 중복 attempt ID의 경계를 단위 테스트로 고정했다.
4. 현재 Gemini v5 30건 결과로 실행해 정확히 7개 검토 대상을 생성했다.

## 주요 판단과 이유

- 사람이 아직 입력하지 않은 빈 review는 유효한 `SemanticReview`로 위장하지 않는다. 실수로
  미검토를 통과 또는 0점으로 집계하지 않기 위해서다.
- raw 응답과 review 원문은 민감한 평가 산출물이므로 Git이 아닌 `local-results/`에만 둔다.
- 완료 JSON을 기존 runner에 연결하면 새 모델 호출이 발생한다. 이번 PR은 호출·비용·기존
  `comparison.json`을 변경하지 않는 양식 준비까지만 다룬다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `evals/build_gemini_v5_human_review.py` | Gemini 자동 불일치 검토 양식 CLI |
| `backend/tests/test_gemini_v5_human_review.py` | 대상 선택과 오류 경계 테스트 |
| `docs/specs/gemini-v5-human-review-prep.md` | Why·Goal·What·How·AC Spec |
| `evals/README.md` | 실행·작성·재호출 경계 문서화 |
| `docs/CURRENT_STATE.md` | 검토 준비와 미검토 상태 기록 |
| `docs/project2-checkpoint-work-cards.md` | D12 사람 검토 남은 항목 연결 |

## 5. 검증

```text
$env:PYTHONPATH='backend;backend\\tests;.'
.\\.venv\\Scripts\\python.exe -m unittest backend.tests.test_gemini_v5_human_review
Ran 2 tests ... OK

.\\.venv\\Scripts\\python.exe -B evals\\build_gemini_v5_human_review.py \
  --input local-results\\gemini-v5-4096-live-30\\comparison.json \
  --candidate gemini \
  --output-dir local-results\\gemini-v5-4096-human-review
REVIEW.md에 검토 대상 7건을 확인
```

## 6. 발견한 문제 / 남은 리스크

- 기존 runner는 `--semantic-reviews`를 적용할 때 모델을 다시 호출한다. 저장된 결과에 사람
  점수만 오프라인으로 합산하는 별도 작업은 이번 범위에 포함하지 않았다.
- 단일 검토자 결과는 검토자 간 일치도를 제공하지 않는다.

## 미확인 사항

- 7개 항목의 실제 사람 semantic/critical 판정은 아직 수행하지 않았다.
- 완료 review JSON으로 재실행한 Gemini의 비용·latency·계약 결과는 아직 없다.

## 7. 다음 작업

- 검토자가 local `REVIEW.md`와 JSON template의 7개 항목을 작성한다.
- 재호출 비용을 승인한 경우에만 작성한 JSON을 `--semantic-reviews`로 사용해 동일 설정을 재실행하고,
  semantic 결과와 한계를 별도 실험 기록에 남긴다.
