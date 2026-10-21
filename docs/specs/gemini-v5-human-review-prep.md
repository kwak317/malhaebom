# Gemini v5 사람 검토 양식 생성

## Why

- Gemini v5 4,096-token 30건은 출력 계약 30/30을 통과했지만 자동 label/evidence 불일치 7건이 남았다.
- 자동 점수만으로 코칭 이유·행동·질문·날조 안전성을 품질 통과로 표현할 수 없다.
- 검토자는 원본 결과를 직접 파싱하지 않고, 대상 사례와 기존 semantic rubric을 같은 형식으로 기록할 수 있어야 한다.

## Goal

- 지정한 `comparison.json`에서 Gemini 유효 응답 중 자동 label 또는 evidence 정확도가 1.0 미만인 사례만 선택한다.
- 검토자가 채울 `SemanticReview` 호환 JSON과 읽기용 Markdown을 `local-results/`에 만든다.
- raw 모델 응답과 사람 검토 기록은 Git에 커밋하지 않는다.

Out of Scope: LLM 재호출, 모델·Prompt·Skill 변경, 자동 점수 재정의, 사람 검토 결과의 임의 생성.

## What

**Happy Path**

1. 도구가 `comparison.json`을 읽는다.
2. 대상 candidate의 contract-valid attempt 중 label/evidence 불일치 사례를 선택한다.
3. attempt ID 키를 가진 빈 `SemanticReview` JSON과, 질문·답변·기대/실제 label·자동 불일치·semantic rubric을 포함한 Markdown을 생성한다.
4. 검토자는 JSON의 reviewer, rationale, scores, critical_failure를 작성한다.
5. 기존 runner의 `--semantic-reviews`로 해당 JSON을 사용한다.

**Edge Cases**

- candidate가 없으면 명확한 오류로 종료한다.
- contract-invalid 또는 metrics가 없는 attempt는 대상에서 제외한다.
- 자동 불일치 사례가 없으면 빈 JSON과 Markdown 요약을 생성한다.
- 같은 attempt ID가 중복되면 오류로 종료한다.

## How

- 새 CLI: `evals/build_gemini_v5_human_review.py`
- 입력: `--input <comparison.json>`, 선택: `--candidate gemini`, `--output-dir <local path>`
- 출력: `semantic-reviews.template.json`, `REVIEW.md`
- JSON 값은 기존 `evals.semantic_grader.SemanticReview` 스키마와 호환되는 빈 양식이다.
- Markdown은 synthetic 평가 입력과 해당 모델의 raw/validated output 중 검토에 필요한 정보만 기록한다.

## AC

- GIVEN 7개의 유효 자동 불일치 Gemini attempt WHEN 도구를 실행하면 THEN JSON과 Markdown에 정확히 7개 attempt ID가 포함된다.
- GIVEN contract-invalid attempt WHEN 도구를 실행하면 THEN 검토 양식에서 제외된다.
- GIVEN 생성 JSON에 사람이 유효한 `SemanticReview` 값을 채울 때 WHEN 기존 runner에 전달하면 THEN 별도 변환 없이 semantic 집계에 사용된다.
