# Worklog — ALIO 원문 검토 기반 1차 답변 조건

- 일시: 2026-09-21 17:42 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 요구사항/결정: `docs/specs/alio-reviewed-practice-context.md`, 검토된 요구사항만 1차 답변 세션에 연결

## 1. 목적

ALIO 검색 결과를 바로 연습에 사용하지 않고, 사용자가 원문을 확인해 요구사항과 근거를 검토 완료한 뒤 1~2개를 선택해 1차 답변을 시작하게 한다.

## 2. 작업 전 상태

- 공고 선택 화면은 ALIO 검색·원문 링크 표시와 기존 demo/reviewed 공고 선택을 각각 제공했다.
- ALIO 검색 결과는 검토 전 자료였고, 사용자가 확인한 요구사항을 구조화해 저장하는 API·DB 계약은 없었다.
- `create_practice_session`은 reviewed·active 공고의 요구사항 1~2개를 고정했지만, ALIO 검토자 소유권은 구분하지 않았다.

## 3. 수행 내용

- ALIO 원문 검토의 입력·소유권·비범위·인수 조건을 기능 Spec으로 먼저 작성했다.
- `job_postings`에 `reviewed_by_user_id`, `job_requirements`에 `source_excerpt`, `data_origin='alio'`를 추가했다.
- `review_alio_recruitment` RPC가 비익명 로그인, 입력 길이, 1~5개 요구사항·근거, HTTP(S) 원문 URL을 검증하고 검토자 소유 레코드를 원자적으로 만든다.
- RLS와 `create_practice_session`을 확장해 ALIO 공고는 검토자만 읽고 세션을 만들 수 있게 했다.
- FastAPI `POST /api/alio/recruitments/review`와 Supabase adapter를 추가했다. 브라우저에는 ALIO API key를 보내지 않는다.
- 검색 결과별 `검토하기`, 요구사항·원문 근거 입력, 저장 후 즉시 공고·요구사항 선택, 질문 화면의 선택 요구사항 맥락 표시를 추가했다.
- 검토 시작 시 검색 결과·기존 공고 목록을 숨기고 전용 검토 화면으로 전환했다. 이중 스크롤을 없애고, 요구사항·원문 근거를 넓은 세로 입력 카드로 배치했다.
- 실사용 검색에서 ALIO 원문 링크가 기관 외부 채용 사이트일 수 있음을 확인해, `alio.go.kr` 도메인 제한 대신 HTTP(S) 링크 형식만 검증하도록 조정했다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `supabase/migrations/20260921082822_add_alio_reviewed_practice_context.sql` | 소유자·원문 근거·RLS·ALIO 검토 RPC 추가 |
| `supabase/migrations/20260921083440_fix_alio_review_requirement_ordinality.sql` | RPC 요구사항 순번 SQL 별칭 충돌 수정 |
| `supabase/migrations/20260921083730_allow_alio_linked_source_url.sql` | ALIO가 가리킨 외부 기관 HTTP(S) 원문 링크 허용 |
| `supabase/tests/alio_review_context_test.sql` | 검토 저장·근거 보존·소유자 차단·세션 생성 DB 테스트 |
| `backend/app/schemas/alio_recruitment.py` | 검토 요청 계약과 URL·입력 검증 |
| `backend/app/services/practice_setup.py`, `supabase_practice_setup.py`, `main.py` | 검토 완료 API와 Supabase RPC adapter |
| `backend/tests/test_practice_setup.py` | API·repository 검토 저장 테스트 |
| `frontend/src/api/practiceSetup.ts`, `PracticePage.tsx` | 검토 API client, 입력/선택/질문 맥락 UI |
| `frontend/src/pages/PracticeSetupFlow.test.tsx`, `frontend/src/api/practiceSetup.test.ts` | 화면·HTTP 계약 테스트 |
| `frontend/src/styles/practice-page.css` | 검토 입력 UI 스타일 |
| `docs/specs/alio-reviewed-practice-context.md` | 기능 계약 |

## 5. 검증

```text
Supabase local migration: npx --no-install supabase migration up --local
결과: 3개 ALIO 검토 관련 migration 적용

Supabase pgTAP: npx --no-install supabase test db --local supabase/tests/practice_setup_rls_test.sql supabase/tests/alio_review_context_test.sql
결과: 2 files, 30 tests passed

backend: docker compose run --rm --no-deps api python -m unittest backend/tests/test_alio_recruitment.py backend/tests/test_practice_setup.py
결과: 13 tests passed

frontend: npm run test -- --run src/api/practiceSetup.test.ts src/pages/PracticeSetupFlow.test.tsx
결과: 2 files, 7 tests passed

frontend: npm run build
결과: TypeScript 검사와 Vite production build 통과

local browser: http://127.0.0.1:18080/practice
결과: 로그인 세션으로 `개발` 검색 6건, 기관 외부 원문 링크, 검토 요구사항·근거 입력 화면 표시를 확인
```

## 6. 발견한 문제 / 남은 리스크

- 최초 RPC는 요구사항 순번 삽입에서 PL/pgSQL record 변수와 SQL 별칭을 같은 이름으로 사용해 실패했다. 후속 migration에서 별칭을 분리했고 pgTAP으로 재현·수정 확인했다.
- ALIO 목록 응답의 원문 URL은 기관 채용 사이트일 수 있다. API가 반환한 링크라는 연쇄를 서버가 다시 조회·서명해 보장하지는 않으므로, 현재 경계는 사용자가 원문을 열고 근거를 수동 입력하는 개인 검토다.
- 팀 공용 검토자 역할, 다단계 승인, 외부 공고 원문 자동 수집·추출은 이번 범위에 포함하지 않았다.

## 7. 미확인 사항

- 실제 공고 원문을 사용자가 읽고 검토 완료를 제출한 뒤의 브라우저 E2E는, 임의의 개인 검토 공고를 만들지 않기 위해 자동 제출하지 않았다.
- 검토 완료 요구사항을 넣은 뒤의 LLM 내용 코칭·전사 확인·재답변 비교의 의미 품질은 이번 변경 범위 밖이다.

## 8. 다음 작업

- 사용자가 실제 공고 원문을 검토해 저장한 뒤, 그 공고의 1차 답변 → 전사 확인 → C/R/A/D/V·공고 관련성 코칭 → 같은 질문 재답변·비교를 별도 E2E로 확인한다.
