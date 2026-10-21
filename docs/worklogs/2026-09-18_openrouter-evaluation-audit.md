# Worklog — OpenRouter 252건 자동 평가 감사

- 일시: 2026-09-18
- 작업자/에이전트: Codex
- 관련 실험: [6종 평가](../experiments/2026-09-18_openrouter-six-evaluation.md)
- 정책: 추가 API 호출 없음; dataset/grader/schema 및 기존 결과 변경 없음; 사람 semantic 점수 null 유지

## 1. 목적

모델 선정 전 자동 평가의 systematic failure를 점검하고 semantic 핵심15건 검토 자료를 생성한다.

## 2. 작업 전 상태

Basic90 + Premium162 =252건. Basic54 실패 실행은 고유24case이며 각 실패 실행에 Premium3종 연결. 운영/평가 소스 snapshot과 raw 출력 보존. annotation 독립 검토 미완료.

## 3. 수행 내용

stdlib 전용 offline 분석을 생성했다. Basic 유형 분포/overlap, 계약 독립 raw label 진단, not_observed 인용 원문 감사, evidence exact-match 감사, source Basic/실패 유형별 recovery와 고유case recovery, 6종 공통 실패를 기록했다. semantic15case×6모델 HTML은 Premium 중복 실행 전부와 원문/rubric을 표시한다. 문자열 HTML escaping 적용, 외부 자산/스크립트 없음.

## 주요 판단과 이유

계약 실패는 유지하되 의미 오류와 동일시하지 않는다. not_observed+evidence 27실행/34인용은 모두 해당segment 원문 substring이다. explicit 미확인20항목, 팀only2항목, 범위밖 요청문3항목, label경계 검토9항목으로 분리했다. 인용 분류는 검토 초안이며 사람 semantic 채점이 아니다. exact-match 불일치212항목 중147항목에 동일 정답segment의 합법부분인용이 존재하나 의미 적합성은 미확정이다.

실행 snapshot V Skill은 테스트 추가만 있고 결과 없을 때 not_observed도 허용하여 v2의 관련 테스트 행위 partial정책과 차이가 있다. intent독립 정책도 Skill에 명시되지 않아 case01 등6종 공통 실패의 원인 후보다. case20 generic C/A/V 범위 및18/21/22 context 최소 충분성,16 A주체 경계는 독립 label 검토가 필요하다.

## 4. 변경 파일

- `local-results/openrouter-six-20260918T083814Z/analysis/`: 재현 script2개, AUDIT.md, semantic-review.html, 상세JSON/CSV, verification.json. 로컬 결과 디렉터리는 기존 gitignore 적용.
- 본 Worklog 및 기존 실험 기록의 감사 링크.
- 평가 입력/코드/스키마/설정/기존252건 원본은 수정하지 않음.

## 5. 검증

```text
.venv-llm-eval/bin/python -B local-results/openrouter-six-20260918T083814Z/analysis/analyze.py
.venv-llm-eval/bin/python -B local-results/openrouter-six-20260918T083814Z/analysis/interpret.py
성공. 252고유실행, Basic90, Premium162, dataset30, semantic15 assertions 통과.
원본 artifact 전후 SHA256 동일. not_observed 인용34개 모두 정확한 해당segment substring.
stdlib HTMLParser: section15, model column headings90, script/iframe/img/link0.
```

전체 테스트/API 추론은 이번 문서/로컬 분석 작업에서 실행하지 않았다. 입력경로 첫 smoke는 snapshot하위 경로 오기로 실패했으며 실제 snapshot경로로 수정 후 성공했다. 재현은 위 두 script 순서로 실행한다.

## 6. 발견한 문제 / 남은 리스크

- 자동 계약 통과율은 의미 품질 순위와 다르다. Premium은 선택된 실패case 모집단이며 dedup any성공률은 case별1~3시도 효과 포함.
- 자동critical는 제한된23/28allmet,24없는원문인용만 검사한다. 사람critical 및 semantic0~2는 null.
- 발견 내용은 검토 후보이며 dataset/Skill/grader 변경 미승인. 이번 작업에서는 GitHub Issue/API/PR/commit/push를 수행하지 않았다. 정책 불일치를 확정하면 별도 Issue등록 필요.

## 미확인 사항

독립 전문가 label검토 및 사람 semantic평가 미수행. 이번 자료의 원문 의미 분류는 AI분석 초안이며 정답 확정 근거로 대체하지 않는다.

## 7. 다음 작업

계약과 의미평가를 분리하고 입력 Skill과 승인된v2정책을 일치시키는 변경 범위를 사용자와 확정한 뒤, label독립검토/semantic사람검토 진행.
