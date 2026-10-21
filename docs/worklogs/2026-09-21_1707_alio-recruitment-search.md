# Worklog — ALIO 공고 검색

- 일시: 2026-09-21 17:07 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 요구사항/결정: `docs/specs/alio-recruitment-search.md`, 검토 완료 공고만 연습 세션에 저장하는 기존 계약 유지

## 1. 목적

공고 선택 화면에서 로그인 사용자가 ALIO 진행 공고를 제목 키워드로 검색하고 원문 출처를 확인하게 한다. 인증키는 FastAPI 서버만 사용하며 브라우저에 노출하지 않는다.

## 2. 작업 전 상태

- 공고 선택 화면은 Supabase의 `reviewed`·활성 공고만 표시하고 `create_practice_session`으로 공고와 요구사항 1~2개를 고정했다.
- 로컬 `.env`에는 `ALIO_API_KEY`가 설정되어 있었지만, 활용신청 화면의 정식 호출 URL과 인증키 파라미터명은 확인되지 않았다.
- ALIO 공개 채용 조회 URL `https://opendata.alio.go.kr/new/odaApiMng/recrutInquiryAjaxList.do`는 `recrutPbancTtl`, `ongoingYn=Y`, 페이지 파라미터로 목록을 반환했다.

## 3. 수행 내용

- 검색 요구사항·오류 경로·검토 경계를 기능 Spec으로 먼저 작성했다.
- FastAPI에 인증 필요 `GET /api/alio/recruitments`를 추가하고, `ALIO_API_KEY`를 서버 POST 요청에만 포함하는 ALIO adapter를 구현했다.
- 외부 응답을 공고 ID·기관명·제목·날짜·근무지·고용/경력 구분·HTTP(S) 원문 URL로 정규화했다.
- 공고 선택 화면에 키워드 검색, 결과 목록, 원문 링크, 검토 전 자료 안내를 추가했다.
- 검색 결과는 DB에 저장하거나 연습 세션에 사용하지 않아 기존 검토 공고/요구사항 선택 계약을 보존했다.
- `.env.example`, 현재 구조·상태 문서를 갱신했다.

## 주요 판단과 이유

- ALIO 검색 결과를 바로 연습 세션에 넣지 않았다. 프로젝트의 검토 완료 공고·요구사항 1~2개 고정 원칙을 유지하고, 자동 수집·검토·스냅샷 저장은 별도 기능으로 남긴다.
- 기본으로 공개 목록 URL과 `authKey` 파라미터를 사용하되, 활용신청 후 받은 명세가 다를 때는 `ALIO_RECRUITMENT_API_URL`, `ALIO_API_KEY_PARAM`으로 코드 변경 없이 서버 설정만 바꾼다.
- 공개 목록 URL이 키 없이도 응답하므로 현재 키의 유효성 자체는 검증하지 않았다. 실제 명세의 인증 요구 URL로 전환한 뒤 별도 확인이 필요하다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `backend/app/schemas/alio_recruitment.py` | ALIO 검색 응답 계약 추가 |
| `backend/app/services/alio_recruitment.py` | 서버 전용 키 사용·응답 정규화·오류 처리 adapter 추가 |
| `backend/app/main.py` | 인증 필요 검색 API와 서비스 초기화 추가 |
| `backend/tests/test_alio_recruitment.py` | 서버 키 전달·URL 안전성·인증·입력 검증 테스트 추가 |
| `frontend/src/api/practiceSetup.ts` | ALIO 검색 클라이언트와 응답 검증 추가 |
| `frontend/src/api/practiceSetup.test.ts` | 프런트 API 요청 테스트 추가 |
| `frontend/src/pages/PracticePage.tsx` | 검색 폼·결과·원문 링크·검토 안내 추가 |
| `frontend/src/pages/PracticeSetupFlow.test.tsx` | 검색 결과 표시 테스트 추가 |
| `frontend/src/styles/practice-page.css` | 검색 UI 스타일 추가 |
| `.env.example` | ALIO 키·URL·키 파라미터 예시 추가 |
| `docs/specs/alio-recruitment-search.md` | 기능 Spec 추가 |
| `docs/ARCHITECTURE.md`, `docs/CURRENT_STATE.md` | 현재 API·데이터 경계 기록 |

## 5. 검증

```text
frontend: npm run test -- --run src/api/practiceSetup.test.ts src/pages/PracticeSetupFlow.test.tsx
결과: 2 files, 5 tests passed

frontend: npm run build
결과: TypeScript 검사와 Vite production build 통과

backend: docker compose run --rm --no-deps api python -m unittest backend/tests/test_alio_recruitment.py backend/tests/test_practice_setup.py
결과: 10 tests passed

backend live adapter: docker compose exec -T api python -c '...search(query="정보통신")...'
결과: alio_total_count=1, normalized_results=1. 인증키 값은 출력하지 않음.

local UI: http://localhost:18080/practice
결과: 프런트 화면과 로그인 전 공고 선택 안내를 브라우저에서 확인.
```

## 6. 발견한 문제 / 남은 리스크

- `API_PORT=8000`은 다른 로컬 `sentiment-api` 컨테이너와 충돌했다. 현재 말해봄 Compose는 파일 수정 없이 실행 시점의 `API_PORT=18000 WEB_PORT=18080` override로 정상 기동했다.
- `agent-browser` 실행 파일이 현재 환경에 없어 해당 스킬 CLI 검증은 실행하지 못했고, 대체 브라우저에서 로컬 화면 로드를 확인했다.

## 미확인 사항

- ALIO 활용신청 화면의 정식 호출 URL·정확한 키 파라미터명과 그 키의 유효성. 공개 조회 URL은 키 없이도 응답한다.
- 실제 로그인한 브라우저에서 검색 폼으로 호출하는 E2E. 프런트 컴포넌트 테스트는 통과했으나, 로컬 브라우저에 로그인 세션이 없어 로그인 후 UI 상호작용은 수행하지 않았다.

## 7. 다음 작업

- ALIO 활용신청 화면에서 제공된 정식 목록 URL과 인증키 파라미터명을 확인해 `.env`의 `ALIO_RECRUITMENT_API_URL`, `ALIO_API_KEY_PARAM`에 반영한다.
- 필요 시 별도 Spec으로 `검색 → 공고 가져오기 → 요구사항 검토/수정 → reviewed 전환` 관리 흐름을 구현한다.
