# Worklog — 로그인 연습 기록 응답 JSON 확인

- 일시: 2026-09-30 11:33 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 요구사항/결정: 구현 현황 문서의 `GET /practice-records` 응답을 실제 로그인 조회 근거로 교체

## 1. 목적

로그인된 로컬 브라우저에서 조회한 실제 API 응답 구조를 확인하고, 사용자 답변과 UUID를 가린 JSON을 문서에 기록한다.

## 2. 작업 전 상태

- `proj2-3-complete-flow` Compose의 API `18000`, 프런트엔드 `18080`이 healthy였다.
- 로그인된 Chrome의 연습 기록 화면에서 `GET /practice-records`가 HTTP 503을 반환했다.
- Network `Response`에는 `분석 작업 저장소 요청에 실패했습니다. (HTTP 400)`이 표시됐다.
- 로컬 DB에는 `coaching_runs.criteria_version` 컬럼이 없었고, 이를 추가하는 기존 migration `20260928065116_coaching_run_criteria_version.sql` 한 건이 미적용 상태였다.

## 3. 수행 내용

1. 기존 migration의 nullable 컬럼 추가 SQL을 검토하고 로컬 Supabase DB에 transaction으로 적용했다. 같은 transaction에서 `supabase_migrations.schema_migrations`에 version을 기록했다.
2. 같은 로그인 Chrome 화면에서 `다시 불러오기`를 눌러 `GET /practice-records` HTTP 200과 화면의 기록 1개 표시를 확인했다.
3. Network `Response`와 `Preview`에서 `records` 1개, `attempts` 1개, `content_analysis.criteria` 5개 및 필드 구조를 확인했다.
4. 루트 구현 현황 문서의 접근 로그 JSON을 실제 응답 구조 JSON으로 교체했다. UUID, 답변 원문, 답변 인용은 문서에서 가렸다.
5. 같은 문서의 저장소 구조 아래에 현재 코칭·공고 요구사항·README Skill의 적용 규칙 표를 추가하고 각 Skill 파일의 범위·인용 길이·금지 사항을 대조했다.

## 주요 판단과 이유

- migration은 기존 코드가 요구하는 nullable 컬럼만 추가하며 기존 행의 값을 추정해 채우지 않는다.
- 브라우저의 인증 토큰은 문서·파일에 복사하지 않았다.
- 현재 응답에는 답변이 1개라 `comparison` 필드가 없었다. 이를 임의로 추가하지 않았다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `../말해봄_개발기반_구현현황_NCS포함_20260929.md` | 실제 로그인 조회 응답을 비식별 JSON으로 반영하고 Skill별 규칙 표 추가 |
| `docs/worklogs/2026-09-30_1133_authenticated-practice-records-json.md` | 이번 검증 및 로컬 migration 적용 경위 기록 |

로컬 Supabase DB schema와 migration history가 변경됐다. 소스 코드와 기존 사용자 데이터 행은 변경하지 않았다.

## 5. 검증

```text
Compose 컨테이너 provenance: proj2-3-complete-flow/docker-compose.yml, API 18000, frontend 18080
GET /health: HTTP 200
로그인 Chrome의 GET /practice-records: migration 전 HTTP 503, 적용 후 HTTP 200
연습 기록 화면: 1개의 기록 표시
Network Response/Preview: records 1개, attempts 1개, criteria 5개
문서의 JSON 블록 4개 파싱 및 Skill 규칙 표 대조: 통과
coaching_runs.criteria_version 컬럼: 존재
supabase_migrations.schema_migrations 20260928065116: 존재
```

## 6. 발견한 문제 / 남은 리스크

- 로컬 DB migration이 빠져 있으면 현재 코드의 기록 조회가 HTTP 503으로 실패한다. 다른 DB 환경에도 같은 migration이 적용됐는지는 확인하지 않았다.

## 미확인 사항

- 운영 배포의 인증 기록 조회와 다른 사용자·2차 답변의 응답은 이번에 검증하지 않았다.

## 7. 다음 작업

- 배포 또는 새 로컬 DB 기동 시 pending migration 적용을 확인한다.
