# 로그인 사용자 공고 원문 분석 E2E 증거 — 2026-10-01

## 범위

로컬 Supabase에 실제 로그인한 사용자 세션의 access token을 사용해
`backend/tests/run_job_source_e2e.py`로 프런트엔드의 연습 준비 경로를 API 수준에서 재현했다.

검증 경로:

`인증 → NCS 선택 → 공고 추천 → 공고 선택 → 원문 재조회/검증 → LLM 요구사항 추출 → 원문 quote 검증 → private_job 저장 → 로그인 사용자 공고 목록 확인 → 요구사항 2개 선택 → 연습 세션 생성`

민감한 JWT, 사용자 ID, 공고 전체 URL, 공고 원문, 요구사항 원문/인용, 저장 UUID는 증거에 남기지 않는다.

## 최종 실행 환경

- 날짜: 2026-10-01
- API: `http://localhost:8000`
- 인증: local Supabase 실제 로그인 사용자 JWT
- NCS 선택: `skill-server`
- 공고 검색 provider: `web`
- 선택 공고 출처 host: `www.saramin.co.kr`
- 실행 브랜치: `test/job-source-authenticated-e2e`

PlayMCP 인증은 실행 시점에 503을 반환해 기존 복귀 경로인 `JOB_SEARCH_PROVIDER=web`으로 전환했다.
공고 원문 분석·근거 검증 자체의 E2E 목적은 provider 종류와 분리해 검증했다.

## 최종 redacted 결과

```json
{
  "api_base_url": "http://localhost:8000",
  "auth": "ok",
  "ncs_option": "skill-server",
  "recommendation_count": 3,
  "selected_source_host": "www.saramin.co.kr",
  "source_review": "ok",
  "requirement_count": 5,
  "quote_validation_gate": "passed",
  "authenticated_job_list_contains_selected": true,
  "selected_requirement_count": 2,
  "practice_session_created": true,
  "trace_ids_present": {
    "recommendation": false,
    "source_review": false,
    "practice_session": false
  }
}
```

## 판정

- 인증 사용자 API 호출 성공
- NCS `skill-server` 기준 추천 공고 3건 반환
- 선택한 사람인 공고를 서버가 원문에서 다시 검증
- 요구사항 5건 추출
- 각 요구사항의 `source_excerpt` 존재 및 서버 원문 quote 검증 gate 통과
- 검토 공고가 해당 로그인 사용자의 `private_job` 목록에 저장·조회됨
- 추출 요구사항 중 2개를 선택해 `preset-04` 연습 세션 생성 성공

따라서 강사 피드백의
**공고 선택 → 원문 조회 → 요구사항 추출 → 원문 quote 검증 → 요구사항 선택**
경로에 대한 로그인 사용자 E2E 증거를 확보했다.

## 실행 중 관찰한 실패와 복구

1. 첫 시도에서 외부 NCS API가 일시적으로 HTTP 503을 반환했다.
2. 재시도에서는 NCS 단계가 통과했지만 PlayMCP 인증이 HTTP 503을 반환했다.
3. 저장소에 보존된 기존 복귀 경로대로 `JOB_SEARCH_PROVIDER=web`으로 전환하고 API만 재생성했다.
4. API 재생성 뒤 기존 JWT가 HTTP 401이어서 브라우저 로그인 세션의 최신 JWT로 갱신했다.
5. 최종 실행은 위 redacted 결과와 같이 전체 경로를 통과했다.

## 제한

- 브라우저 로그인 세션의 실제 JWT를 사용했지만, 최종 증거는 브라우저 클릭 녹화가 아니라 프런트엔드와 동일한 API 경로를 재현하는 인증 E2E runner 결과다.
- 외부 공고 검색 결과와 개수는 실행 시점·provider 응답에 따라 달라질 수 있다.
- 해당 추천/원문검토/세션 생성 endpoint는 이번 출력에서 trace ID를 반환하지 않았으며, trace 존재 여부는 이 검증의 합격 조건으로 사용하지 않았다.
