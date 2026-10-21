# Worklog — 민간 추천 공고 선택과 코칭 연결

- 일시: 2026-09-23 17:32 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 Spec: [백엔드 공고 후보 추천](../specs/saramin-backend-recommendations.md)

## 1. 목적

공고 검색의 후보 확인 시간을 줄이고, 추천 카드에서 공고를 선택해 원문 기반 요구사항 검토와 기존 1차·2차 답변 비교까지 진행할 수 있게 한다.

## 2. 작업 전 상태

- 검색 결과 카드에는 원문 링크만 있고 검토 공고로 선택하는 경로가 없었다. `다시 검색`이 카드와 붙어 보였다.
- 기본 검색의 인용 URL 해석과 공고 원문 확인이 후보별 순차 대기로 이어졌다. 기본 결과가 0건이어도 보완 native 검색을 마친 뒤 Exa를 호출했다.
- 검토된 ALIO·공공 공고에는 요구사항 선택과 코칭 세션 흐름이 이미 있었다.

## 3. 수행 내용과 판단

- 검색 경유 URL 해석과 후보 원문 검증을 각각 최대 6개 병렬 요청으로 바꿨다. 기본 검색이 0건이면 Exa를 먼저 시도한 뒤 부족할 때 보완 native 검색을 수행한다. 각 후보의 URL·마감·신입·역량 겹침 검증은 유지한다.
- 카드마다 `공고 선택`을 추가하고 `다시 검색`을 카드 목록 아래 별도 영역에 배치했다. 선택 중 중복 요청을 막고 분석 실패를 화면에 표시한다.
- 선택 시 서버가 개별 공고 원문을 다시 확인한다. 원문 상세가 충분한 경우 기존 AI 요구사항 분석기의 인용 검증을 거쳐 1~5개 요구사항만 저장한다. 이미 저장된 사용자 공고는 현재 원문 상태를 확인한 뒤 재사용한다.
- `private_job` 데이터 출처, 사용자 소유 RLS, 민간 공고 저장 RPC, 기존 세션 생성 허용 범위를 추가했다. 프런트엔드는 검토 결과를 기존 요구사항 1~2개 선택, 질문, 녹음·코칭, 재녹음·비교 경로에 전달한다. 서버 전용 키는 브라우저로 전달하지 않는다.
- 분석 모델이 설정되지 않은 경우에도 503 안내가 반환되도록 미설정 서비스의 `source_text` 호출 계약을 맞췄다.

## 4. 변경 파일

| 영역 | 파일 |
| --- | --- |
| 추천·검토 API | `backend/app/services/saramin_recommendation.py`, `backend/app/schemas/saramin_recommendation.py`, `backend/app/main.py`, `backend/app/services/alio_requirement_analysis.py` |
| 검토 공고 저장 | `backend/app/services/practice_setup.py`, `backend/app/services/supabase_practice_setup.py`, `backend/app/schemas/practice_setup.py`, `supabase/migrations/20260923082228_private_job_review.sql` |
| 화면 | `frontend/src/pages/PracticePage.tsx`, `frontend/src/api/practiceSetup.ts`, `frontend/src/styles/practice-page.css` |
| 검증 | `backend/tests/test_saramin_recommendation.py`, `backend/tests/test_practice_setup.py`, `backend/tests/test_alio_requirement_analysis.py`, `frontend/src/pages/PracticeSetupFlow.test.tsx`, `frontend/src/api/practiceSetup.test.ts`, `supabase/tests/private_job_review_test.sql` |
| 문서 | `docs/specs/saramin-backend-recommendations.md`, `docs/ARCHITECTURE.md`, `docs/CURRENT_STATE.md`, 이 Worklog |

## 5. 검증

- 백엔드 전체 격리 실행: 287개 통과. 추가한 미설정 분석 서비스 회귀 테스트 포함 파일 8개 통과.
- 프런트엔드 전체: 78개 통과, production build 통과. 추천 카드 선택 → 요구사항 선택 → 질문·연습 세션 진입을 컴포넌트 테스트로 확인했다.
- 로컬 Supabase migration `20260923082228` 적용을 확인했고, pgTAP 8개 통과. 사용자별 조회·세션 권한과 RPC 실행 역할을 검증했다.
- Compose `api`·`frontend` 이미지를 재빌드했으며 두 서비스가 healthy다. `http://localhost:18080/`과 API `/health`가 200, OpenAPI에 새 검토 경로가 표시된다.

## 6. 발견한 문제 / 미확인 사항

- 새 브라우저는 로그아웃 상태여서 추천 카드의 실제 클릭부터 음성 2차 비교까지 운영 E2E는 수행하지 않았다. 실제 외부 공고의 본문 형태, 모델 인용 품질과 검색 소요 시간은 호출 시점에 따라 달라진다.
- 이번 테스트는 로컬 Supabase에만 migration을 적용했다. 공유 Hosted Supabase에는 별도 적용이 필요하다.
- 기존 작업 트리에 많은 사용자 변경이 이미 있었다. 그 파일들을 초기화하거나 별도 문제를 수정하지 않았다.

## 7. 다음 작업

- 로그인한 로컬 화면에서 실제 후보 한 건을 선택해 원문 검토·요구사항 선택과 1차·2차 비교까지 확인한다.
- 공유 Hosted Supabase에서 이 흐름을 사용할 경우 migration 적용 상태를 확인한다.
