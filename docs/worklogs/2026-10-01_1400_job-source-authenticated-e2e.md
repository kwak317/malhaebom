# Worklog — 로그인 사용자 공고 원문 분석 E2E

- 일시: 2026-10-01 14:00 KST
- 작업자/에이전트: 김재훈 / ChatGPT
- 관련 브랜치: `test/job-source-authenticated-e2e`
- 관련 요구사항/결정: 3조 강사 피드백의 공고 원문 분석 흐름 E2E 증거 확보

> 2026-10-06 문서 정리: 로컬 증거 원본을 별도 보존 파일로 옮겨 아래 증거 경로를 갱신했다. 당시 테스트 환경·결과는 변경하지 않았다.

## 1. 목적

강사 피드백에 남아 있던
`공고 선택 → 원문 조회 → 요구사항 추출 → 원문 quote 검증 → 요구사항 선택`
경로를 실제 로그인 사용자 문맥에서 실행하고, 민감값을 제외한 재현 가능한 증거를 저장소에 남긴다.

완료 조건:

- 실제 local Supabase 로그인 사용자 JWT로 인증한다.
- NCS 선택 뒤 실제 외부 공고 추천을 받는다.
- 추천 공고를 선택해 서버가 원문을 다시 조회·검증한다.
- LLM 요구사항 추출 결과가 서버 원문 quote 검증을 통과한다.
- 검토 공고가 로그인 사용자 목록에 저장됐음을 확인한다.
- 추출 요구사항 1~2개를 선택해 연습 세션 생성까지 연결한다.
- JWT, 사용자 ID, 공고 전체 URL/원문, 요구사항 원문/인용, 저장 UUID는 증거에 남기지 않는다.

## 2. 작업 전 상태

- 공고 원문 조회·요구사항 추출·quote 검증·저장 구현과 개별 테스트는 존재했다.
- `docs/project2-checkpoint-work-cards.md`의 강사 피드백 항목은 문서 정합성까지 해결됐지만 실제 로그인 사용자 E2E 증거가 없어 `[-]`였다.
- `backend/tests/run_job_source_e2e.py` 초안은 존재했지만 비대화형 실행 환경에서 JWT 전달 경로가 없어 완료되지 않은 상태였다.

## 3. 수행 내용

1. `run_job_source_e2e.py`에 Git ignored `.env.job-source-e2e` 토큰 파일 입력을 추가했다.
   - 파일은 group/other 권한이 있으면 거부하고 0600만 허용한다.
   - 환경변수 `JOB_SOURCE_E2E_ACCESS_TOKEN` / `D6_ACCESS_TOKEN` 우선순위는 유지한다.
2. 토큰 파일 경로의 환경변수 우선, 0600 파일 읽기, 0644 거부를 단위 테스트로 추가했다.
3. 실제 브라우저 로그인 세션에서 JWT를 받아 로컬 Compose API에 대해 E2E를 실행했다.
4. 외부 호출이 단일 실행 한도를 넘길 수 있어 Git ignored `local-results/`의 임시 launcher/poller로 실제 runner를 분리 실행했다. 이 helper와 raw 로컬 출력은 커밋 대상이 아니다.
5. 최종 redacted 결과를 `docs/evidence/job-source-analysis-local-e2e-2026-10-01.md`에 고정했다.
6. `CURRENT_STATE`와 강사 피드백 체크리스트를 실제 검증 결과에 맞춰 갱신했다.

## 주요 판단과 이유

- PlayMCP 인증 503은 공고 원문 분석 경로 자체의 실패와 구분했다. 저장소가 공식적으로 보존하는 `web` provider 복귀 경로를 사용해 원문 분석 E2E를 계속했다.
- 최종 실행은 브라우저 클릭 캡처가 아니라, 실제 브라우저 로그인 JWT로 프런트엔드와 동일한 API 호출 순서를 재현한 인증 사용자 E2E다. UI 클릭 검증으로 과장하지 않는다.
- endpoint에서 trace ID가 반환되지 않은 것은 별도 관측성 범위이며, 이번 공고 원문 분석 성공 조건에는 포함하지 않았다.
- 외부 공고 원문·JWT·사용자/저장 ID는 증거 artifact에 복제하지 않는다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `backend/tests/run_job_source_e2e.py` | 비대화형 0600 JWT 파일 입력 지원 |
| `backend/tests/test_job_source_e2e_runner.py` | JWT 입력 보안 규칙 3건 검증 |
| `docs/evidence/job-source-analysis-local-e2e-2026-10-01.md` | 로그인 사용자 E2E redacted 증거 |
| `docs/CURRENT_STATE.md` | 공고 원문 분석 E2E 현재 상태 추가 |
| `docs/project2-checkpoint-work-cards.md` | 강사 피드백 문제 해결력 항목 완료 반영 |
| `docs/worklogs/README.md` | Worklog 목록 추가 |
| 본 Worklog | 실행 과정·실패·복구·제한 기록 |

## 5. 검증

단위 테스트:

```text
backend/tests/test_job_source_e2e_runner.py
Ran 3 tests in 0.002s
OK
```

최종 로그인 사용자 E2E redacted 결과:

```text
auth=ok
ncs_option=skill-server
recommendation_count=3
selected_source_host=www.saramin.co.kr
source_review=ok
requirement_count=5
quote_validation_gate=passed
authenticated_job_list_contains_selected=true
selected_requirement_count=2
practice_session_created=true
```

세부 redacted JSON은
`docs/evidence/job-source-analysis-local-e2e-2026-10-01.md`를 따른다.

## 6. 발견한 문제 / 남은 리스크

- 첫 NCS 호출은 외부 API 503이었고 재시도에서 복구됐다.
- PlayMCP 인증은 실행 시점에 503이어서 이번 최종 성공 run은 `web` provider를 사용했다.
- API 재생성 뒤 기존 JWT가 401이 되어 브라우저 세션의 최신 JWT로 갱신해야 했다.
- 외부 검색 결과와 지연시간은 실행 시점에 따라 달라질 수 있다.

## 미확인 사항

- 동일 경로의 브라우저 클릭 영상/스크린샷은 이번 검증에 포함하지 않았다.
- PlayMCP 인증 자체의 복구 여부는 별도 과제다.
- 운영 배포 환경에서 동일 공고 원문 분석 E2E는 검증하지 않았다.

## 7. 다음 작업

1. 변경 diff와 PR size policy 확인
2. PR CI에서 backend 전체 테스트 확인
3. 필요 시 PlayMCP 인증 복구를 별도 작업으로 분리
