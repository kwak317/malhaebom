# Worklog — 연습기록의 비교·꼬리질문 접기/펼치기

- 일시: 2026-09-28 17:33
- 작업자/에이전트: Codex
- 관련 이슈/PR: 이번 변경은 로컬 작업만 수행. 기존 PR #96/#97/#99/#100은 수정·merge하지 않음.
- 관련 요구사항/결정: 사용자 연습기록 접기/펼치기 요청, [Spec](../specs/history-comparison-chat-folds.md)

## 1. 목적

기록 목록과 상세에서 비교/후속 대화를 기본 접고, 클릭하면 전체 내용을 아래로 펼친다. 앞으로 완료하는 대화를 실제 기록에 연결한다.

## 2. 작업 전 상태

- 대상: `proj2-3-complete-flow`, `codex/team-local-auth-18080`. 기존 다수 변경/미추적 파일을 보존하고 해당 파일만 수정했다.
- 기존 상세는 비교를 항상 펼쳤고 목록은 결과 보기/삭제만 제공했다. 면접 대화는 프로세스 메모리의 최근 12개/요약만 남아 과거 전체 채팅 조회가 불가능했다.
- 관련 backend 13개, frontend 5개 baseline 통과. 수정 전 파일을 workspace 밖 `output/history-folds-20260928/before`에 백업했다.

## 3. 수행 내용

- `HistoryConversationPanels`: native `details` 두 개, 비교 내용·전달력·1차 피드백 보존, 읽기 전용 코치/사용자 대화와 종료 요약 렌더링. 1차 단독에는 가짜 비교/대화를 표시하지 않는다.
- 완료 대화와 모델 문맥을 분리한다. 전체 대화는 종료 시 기존 2차 job JSONB archive에 저장하며 모델 입력은 기존 최근 12개/요약을 유지한다.
- 원래 result 키를 병합하고 완료/만료 시각은 수정하지 않는다. JWT/RLS와 소유자/2차/completed/만료 필터를 사용한다. 저장 전 원래 문맥/fingerprint를 재검사하고 조회 시 다시 검증한다. DB에서 revision과 job PATCH를 하나의 원자적 연산으로 잠그는 구조는 아니므로, 조회의 현재 fingerprint 검사로 오래된 대화 노출을 차단한다.
- 저장 실패 시 동일 종료 응답/기록을 캐시해 저장만 재시도한다. 일반 job polling에 archive를 넣지 않으며 새 코칭 문맥에도 넣지 않는다.
- 모바일 flex column + wrap으로 패널이 옆으로 밀리는 문제를 브라우저에서 발견해 모바일 nowrap/basis auto로 수정했다.

## 주요 판단과 이유

추가 테이블/원격 migration 없이 현재 JSONB와 삭제/만료 경계를 재사용한다. 세션당 최근 완료 대화 하나를 남긴다. 진행 중 대화 복원·장기 저장·다중 worker 공유는 구현하지 않았다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `backend/app/schemas/interview_chat.py` | 완료 기록/메시지 계약 |
| `backend/app/services/interview_chat.py` | 전체 transcript와 종료 저장/재시도 |
| `backend/app/services/practice_history.py` | 검증된 archive 조회 |
| `backend/app/services/persistent_analysis_jobs.py` | polling result에서 archive 제외 |
| `backend/app/main.py` | 저장/조회 실패 안내 |
| `backend/tests/test_interview_chat.py` | 장문 보존, 캐시 유실 후 조회, 저장 재시도, 변경/만료/삭제, polling 회귀 |
| `frontend/src/api/practiceHistory.ts`, `frontend/src/services/practiceHistoryMapper.ts` | 기록 DTO/mapper |
| `frontend/src/components/HistoryConversationPanels.tsx` | 공통 접기/펼치기 UI |
| `frontend/src/pages/HistoryPage.tsx`, `HistoryDetailPage.tsx` | 목록/상세 연결 |
| `frontend/src/styles/history-page.css` | 패널/채팅/모바일 배치 |
| 기존 mapper/목록/상세 테스트 3개 파일 | 데이터 전달, 독립 클릭, 1차/옛 기록, 결과 보기/삭제 유지 |
| `supabase/tests/history_chat_result_test.sql` | local transaction DB/RLS 8개 |
| `docs/specs/history-comparison-chat-folds.md` | 작업 전 계약 |
| `CURRENT_STATE`, `ARCHITECTURE`, `DECISIONS`, `CONSTRAINTS`, 기존 대화 Spec | 완료 대화 보관 경계 반영 |

## 5. 검증

- 격리 Docker, network none, backend/skills/질문 카탈로그 read-only mount: `python -m unittest discover -s tests` → **343 passed**.
- `cd frontend; npm test` → **99 passed (24 files)**.
- `npm run build` 및 `docker compose build api frontend` → TypeScript/Vite/Docker build 성공.
- local PostgreSQL `supabase_db_proj1-b-supabase-google-auth`에서 `psql -v ON_ERROR_STOP=1 < supabase/tests/history_chat_result_test.sql` → **8 passed**, ROLLBACK. pgtap은 transaction 안에서만 설치하고 함께 rollback했다. 테스트 사용자/행은 남지 않는다. 기존 정책/JSONB 동작의 증거이며 Hosted Supabase E2E 증거는 아니다.
- CUA 브라우저: 실제 `HistoryPage`/CSS, fixture API/auth만 연결. 기본 접힘, PC/390px 모바일 독립 펼침/접기, Enter, 17개 메시지 마지막 요약까지 페이지 스크롤 확인. 모바일 clientWidth=scrollWidth=390, maxHeight=none/overflowY=visible. console warn/error 없음.
- `docker compose up -d api frontend`: localhost:18000/18080 반영. runtime ID/해시/health는 아래 후속 확인에 기록.
- scoped diff 검토: 기존 사용자 변경 보존. 전체 `git diff --check`의 기존 PR template 공백 두 건은 이번 변경 밖이라 수정하지 않았다.

### 검증 환경 문제 및 수정

- 최초 전체 backend test는 frontend 카탈로그 mount 누락으로 1개 FileNotFoundError가 발생했다. 해당 read-only mount를 추가해 전체 통과했다.
- 최초 SQL test 환경은 pgtap 함수가 없었다. transaction 설치+search_path 적용 후 8개 통과, extension도 rollback했다.
- 최초 브라우저 harness의 전역 fetch mock은 자동화 이벤트를 방해했다. API 모듈 alias fixture로 분리해 실제 클릭/키보드 동작을 확인했다. 운영 코드에 mock/fixture는 포함하지 않았다.

## 6. 발견한 문제 / 남은 리스크

- 기존 미저장 대화는 복원 불가. 저장하지 않은 진행 중 대화/저장 실패 캐시는 프로세스 재시작에 유실될 수 있다.
- 같은 세션에서 새 대화를 완료하면 가장 최근 완료 대화로 교체한다. 기존 보관 기간은 연장하지 않는다.
- 실제 로그인 사용자·실모델 종료→DB 저장→브라우저 기록 조회 E2E는 미확인이다. 이번 DB 검증은 로컬 기존 정책 테스트, 브라우저는 합성 데이터 fixture 테스트다.

## 7. 다음 작업

현재 사용자 화면 새로고침 후 새 대화를 `연습 마치기`로 완료하면 기록에서 확인할 수 있다. PR/commit/push는 새 요청이 있을 때 진행한다.

### 로컬 runtime 후속 확인

- API `553fac03a22a`, frontend `ec37f9d41527` 모두 healthy. `/health` = ok, localhost:18080 HTTP 200.
- 변경한 API 파일 5개가 host와 container에서 SHA-256 일치. Frontend 새 JS/CSS build asset hash를 `output/history-folds-20260928/runtime-proof.json`에 기록했다.
- 변경 파일 scoped whitespace check 통과. commit/push/PR/merge 없음.

## 후속 수정 — 결과 보기 진입 후에만 표시 (2026-09-28 17:37)

- 사용자 요청: “결과보기 눌러서 들어가야 볼수있게 해줘”.
- `HistoryPage`의 패널 호출/import를 제거하고 `HistoryResultPage`에 추가했다. 상세 화면의 패널과 기존 요약/결과 상세보기/목록 복귀/삭제를 유지한다. 서버·저장 계약은 수정하지 않았다.
- 기존 목록 테스트를 실제 목록→결과 component 전환을 검사하도록 수정했다. 목록에서 패널/답변/대화가 없고 결과 보기 후 두 패널이 기본 닫힘이며 독립적으로 펼쳐진다. 목록 복귀 시 다시 없음을 검증했다.
- 관련 frontend 테스트 3개 통과, scoped whitespace check 및 Docker의 TypeScript/Vite production build 성공. 전체 backend/frontend suite는 이 후속 수정에서 다시 실행하지 않았다.
- fixture API/auth 브라우저에서 목록 미표시→결과 보기→닫힌 패널→대화 펼침→목록 복귀와 PC/390px 결과 배치를 확인했다. console warn/error 없음. 운영 로그인 E2E는 수행하지 않았다.
- frontend만 `docker compose up -d --no-deps frontend`로 재빌드·적용했다. API `553fac03a22a`는 유지한다. 컨테이너 상태는 `output/history-folds-20260928/result-entry-proof.json`에 기록한다.
- Spec/CURRENT_STATE/ARCHITECTURE를 현재 진입 경로로 수정하고 DECISIONS에 후속 판단을 추가했다. 수정 전 파일은 `output/history-folds-20260928/result-entry-before`에 보존했다. commit/push/PR/merge 없음.

## 후속 수정 — 1차 답변 카드 배경 (2026-09-28 17:39)

- 사용자 스크린샷에 맞춰 비교 영역의 1차 답변 배경을 2차와 같은 연보라색 카드로 변경했다.
- `history-page.css`의 `.history-fold-content .history-transcript` 한 줄만 수정했다. 현재 공통 테마의 2차 배경 `#f0eeff`를 사용하며 기존 여백/둥근 모서리/내용을 유지한다. 다른 화면과 저장 경로는 수정하지 않았다.
- Spec/CURRENT_STATE에 색상 기준을 반영하고 수정 전 파일은 `output/history-folds-20260928/first-answer-card-before`에 보존했다.
- 실제 구성요소/합성 기록 브라우저에서 두 답변 모두 background `rgb(240, 238, 255)`, radius `10px`, padding `16px` 일치 및 모바일 화면을 확인했다. 증거: `output/history-folds-20260928/first-answer-card.png`.
- TypeScript/Vite/Docker frontend build 및 scoped whitespace check 통과. CSS 변경이라 신규 테스트/전체 회귀 테스트는 추가·재실행하지 않았다. frontend만 재빌드·반영하고 API를 유지했다. commit/push/PR/merge 없음.

현재 container 상태:

```text
1405d8016800 proj2-3-complete-flow-frontend-1 Up 18 seconds (healthy)
553fac03a22a proj2-3-complete-flow-api-1 Up 7 minutes (healthy)
```

## 2026-09-30 PR 분리 확인

- 이 PR은 결과·상세 화면의 접기/펼치기 UI와 응답 매핑만 포함한다. 완료 대화 저장·조회 API는 별도 PR #130이다.
- 최신 `main` 기준 관련 프런트엔드 테스트 7개와 production build가 통과했다. 실제 로그인 사용자 화면의 대화 기록 표시 E2E는 두 PR 병합 후 확인해야 한다.
