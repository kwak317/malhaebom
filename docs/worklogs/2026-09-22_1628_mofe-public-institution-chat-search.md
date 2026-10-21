# 채팅 재정경제부 공공기관 채용정보 연동 작업 기록

- 일시: 2026-09-22 16:28 KST
- 작업자/에이전트: Codex
- 관련 요구사항/결정: 자연어 공고 검색은 LLM이 해석하고, 사용자는 LLM이 원문에서 추출·근거화한 요구사항만 선택한다.

## 목표

`백엔드 관련 공고` 같은 채팅을 LLM이 짧은 검색어로 해석하면 ALIO·인사혁신처 공공취업정보·재정경제부 공공기관 채용정보를 출처별로 함께 보여 준다. 재정경제부 공고를 선택하면 서버가 같은 공고 ID의 원문 필드를 다시 조회하고, LLM 요구사항 분석 → 사용자 요구사항 선택 → 기존 연습·코칭 흐름으로 이어진다.

## 구현

- `MOFE_PUBLIC_INSTITUTION_JOB_API_KEY`를 서버 서비스에서만 읽도록 `MofeRecruitmentService`를 추가했다.
- 제공자 `https://apis.data.go.kr/1051000/recruitment/list`를 호출할 때 발급키는 재인코딩하지 않고, 나머지 파라미터만 URL 인코딩했다. 키에 URL 인코딩 문자(`%`)가 있어도 `serviceKey`가 훼손되지 않는다.
- 목록 API가 직무 키워드를 안정적으로 서버 필터링하지 않으므로 최신 진행 공고 100건에서 제목·기관·근무지역·고용형태·채용구분·NCS·지원자격을 서버가 다시 필터링한다.
- `GET /api/mofe/recruitments`, `POST /api/mofe/recruitments/analyze`를 추가했다. 분석 요청은 브라우저가 보낸 기관명·제목을 신뢰하지 않고, 공고 ID로 공식 API를 재조회해 지원자격·우대사항·결격사유·전형절차를 LLM 분석 텍스트로 만든다.
- 제공자의 원문 URL이 HTTP인 경우 저장 가능한 HTTPS 출처는 [공식 데이터셋](https://www.data.go.kr/data/15125273/openapi.do)으로 고정한다. 분석 근거 자체는 서버가 재조회한 공공데이터 API 응답이다.
- Supabase `mofe_job` 원본, `review_mofe_recruitment` RPC와 RLS를 추가했다. 영구 로그인 사용자만 자기 검토 공고를 읽고 연습 세션을 만들 수 있다.
- `PracticePage` 채팅 결과에 `재정경제부 공공기관 채용정보` 카드 섹션을 추가했다. 다른 제공자 조회가 실패해도 해당 출처의 결과는 계속 표시하며, 분석 중에는 기존 카카오톡식 입력 중 효과를 공유한다.

## 적용 및 검증

- 로컬 Supabase DB에 `20260922163000_add_mofe_recruitment_practice_context.sql`을 적용하고 migration history를 기록했다.
- SQL 트랜잭션으로 공고 저장 후 다른 사용자 JWT claim에서 결과가 0건인지 확인했고, 트랜잭션은 `ROLLBACK`했다. RPC는 `SECURITY DEFINER`, `authenticated`만 실행 가능, `anon` 실행 불가임을 확인했다.
- 로컬 DB에는 pgTAP `plan()` 함수가 없어 `supabase/tests/mofe_recruitment_context_test.sql`은 자동 실행하지 못했다. 같은 핵심 권한 경계는 위 트랜잭션으로 수동 검증했다.
- API 컨테이너를 `docker compose up -d --build api`로 재기동했다.
- API 컨테이너 테스트: `test_mofe_recruitment`, `test_practice_setup`, `test_job_search_intent`, `test_alio_recruitment`, `test_public_employment_recruitment` 총 31개 통과.
- 프런트 테스트: `src/api/practiceSetup.test.ts`, `src/pages/PracticeSetupFlow.test.tsx` 총 20개 통과.
- `npm run build`의 TypeScript 검사와 Vite 프로덕션 빌드가 통과했다.
- 실행 중 API에서 실제 재정경제부 제공자를 조회해 `전력` 검색 8건과 선택 공고의 분석 텍스트·HTTPS 저장 URL을 확인했다.
- 프런트 컨테이너도 재빌드했고, `http://localhost:18080/practice`가 200·healthy이며 로그인 전 채팅 입력 화면이 렌더링되고 콘솔 오류가 없음을 확인했다.

## 남은 운영 유의사항

- 실제 로그인 계정으로 선택 공고를 저장하는 브라우저 E2E는 사용자의 개인 연습 컨텍스트를 만들 수 있어 자동으로 실행하지 않았다.
- 제공자의 진행 공고 범위는 최신 100건이므로, 오래된 공고까지 넓혀야 하면 공식 API에서 안정적인 기간·검색 조건을 추가 확인해야 한다.

## 후속 수정 — 16:29 KST

- 실제 브라우저에서 재정경제부 공고 분석이 503으로 실패한 것을 재현했다.
- 원인은 제공자가 `recrutPblntSn` 상세 조건을 무시하고 최신 10건만 반환하는 동작이었다. 첫 공고만 우연히 맞고, 그 아래 카드들은 서버 재조회에서 찾지 못했다.
- `get_analysis_source`가 해당 필터 대신 최신 진행 공고 100건을 다시 조회해 선택 공고 ID를 찾도록 수정했다. 브라우저의 제목·기관명은 여전히 분석 근거로 사용하지 않는다.
- API 컨테이너를 다시 재기동하고 관련 백엔드 테스트 16개를 통과시켰다. 실제 `개발` 검색의 첫 세 공고 ID(`305159`, `305158`, `305150`) 모두 분석 텍스트와 HTTPS 저장 출처를 다시 확보했다.
