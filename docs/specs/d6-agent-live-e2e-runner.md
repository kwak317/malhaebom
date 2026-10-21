# D6 Agent live E2E runner 자동화

## Why

- **페르소나**: D6 Agent 운영 검증을 반복하는 팀원
- **문제**: API host port, JWT, analysis job UUID를 수동으로 맞추고 normal / boundary / injection을 UI에서 반복 실행해야 한다.
- **측정 지표**: local 로그인 세션에서 한 runner로 API 확인 → 인증 → job 선택 → 3 case 실행까지 재현한다.

## Goal

- Compose API host port 자동 감지
- JWT 환경변수가 없으면 대화형 숨김 입력
- completed job 후보를 민감정보 없이 표시하고 사용자가 번호로 선택
- health/network/auth 실패를 traceback이나 빈 job 목록으로 오인하지 않게 구분
- 선택 job에 normal / boundary / injection synthetic revision을 만들고 기존 D6 정책으로 판정
- **Out of Scope**: 브라우저 저장소 자동 credential 추출, 최신 job 무확인 자동 선택, WAV/STT/VAD 및 새 practice session 생성

## What

**Happy Path**

1. local frontend 로그인
2. runner 실행
3. compose API port 및 `/health` 확인
4. JWT 숨김 입력 또는 `D6_ACCESS_TOKEN` 사용
5. `/practice-records`에서 completed job 후보 조회
6. 사용자가 테스트용 job 선택
7. 세 synthetic revision 생성 후 `/api/agent` 호출
8. redacted case 결과와 pass/total 출력

**Edge Cases**

| 상황 | 처리 |
|---|---|
| compose port 조회 불가 | 명시 URL / env / localhost:8000 fallback |
| JWT 없음 | 대화형 숨김 입력, 비대화형은 env 요구 |
| API timeout/연결 실패 | redacted `network_error` |
| 401 | job 0건이 아닌 인증 실패로 종료 |
| completed job 0건 | mutation 없이 종료 |
| 여러 job | 자동 최신 선택 금지, 번호 선택 |
| revision/Agent 실패 | 단계와 status만 redacted 결과에 기록 |

## How

- 기존 `run_d6_live_agent_e2e.py`와 `d6_evidence_cases.json`의 case 정책을 재사용한다.
- API URL 우선순위: `--api-base-url` → `D6_API_BASE_URL` → `docker compose port api 8000` → `http://localhost:8000`.
- token은 `D6_ACCESS_TOKEN` 우선, 없으면 대화형 `getpass` 입력을 사용한다.
- job 후보에는 transcript/feedback을 포함하지 않는다.
- 답변 원문, JWT, answer revision ID, job snapshot ID, user ID를 출력하지 않는다.
- synthetic revision이 최신 revision이 될 수 있으므로 job 선택은 사용자에게 남긴다.
- DevTools JWT copy snippet과 전체 재현 절차는 `docs/dev/d6-agent-e2e.md`를 따른다.

## AC

**AC-01 · 환경 자동 감지**
- GIVEN: compose API가 host 18000 → container 8000
- WHEN: URL env 없이 실행
- THEN: `http://localhost:18000`과 `/health`를 사용한다.

**AC-02 · 인증과 오류 구분**
- GIVEN: env token이 없거나 만료됨
- WHEN: 대화형 입력 또는 job 조회
- THEN: token은 숨김 입력하며 401/network 오류를 redacted 상태로 구분한다.

**AC-03 · 안전한 job 선택**
- GIVEN: completed job 후보가 여러 개
- WHEN: analysis job ID 없이 실행
- THEN: 비민감 metadata를 번호로 표시하고 사용자가 선택한 job에만 revision을 추가한다.

**AC-04 · 세 case 실행**
- GIVEN: 유효 token과 테스트용 completed job
- WHEN: 실행
- THEN: normal/boundary/injection을 순서대로 실행하고 기존 정책으로 pass/total을 반환한다.
