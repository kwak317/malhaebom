# Worklog — D8 최소 흐름 재현 절차

- 일시: 2026-09-30 11:30 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: PR #124 (D8 최소 사용자 흐름 및 README 실행 절차)
- 관련 요구사항/결정: D8 최소 사용자 흐름 및 README 실행 절차

## 1. 목적

기존 구현의 공고 선택 → 녹음 → 분석 → 전사 revision 확정 → 코칭 호출 경로를 재확인하고, Mock 계약 E2E를 다른 팀원이 재현할 수 있도록 README에 기록한다.

## 2. 작업 전 상태

- `PracticePage`가 연습 세션·녹음·분석 흐름을 연결하고, `ResultPage`가 전사문을 `answer_revision`으로 확정한 뒤 `/api/agent`를 호출하는 구현과 프런트 테스트가 이미 존재했다.
- README에는 Mock Compose E2E 명령이 있었지만, D8 최소 사용자 흐름과 Mock 검증 범위가 별도 절로 명확히 정리되어 있지 않았다.
- 현재 D8 체크포인트의 운영 배포 URL·환경 차이는 검증 전 상태였다.

## 3. 수행 내용

- 병합된 D6 브랜치의 범위와 무관한 미추적 로컬 음성 생성 스크립트 2개 및 Supabase SQL 스니펫 1개를 제거했다.
- `origin/main`의 PR #122 병합 커밋에서 `feat/d8-minimum-user-flow` 브랜치를 만들었다.
- 프런트 단위 테스트와 production build를 실행했다.
- Docker Compose Mock E2E를 실행해 화면, Nginx proxy, FastAPI Mock 출력 계약, MCP 도구 목록을 확인했다.
- README에 Windows PowerShell 실행·정리 명령, 성공 출력 기준, 실제 운영 E2E와의 차이를 추가했다.
- 체크포인트 문서의 D8 README 항목을 실제 검증 범위에 맞게 부분 완료로 갱신했다.
- 로컬 Supabase 로그인 후 실제 브라우저에서 최소 흐름을 수행해, 프록시와 인증이 포함된 요청 단위를 확인했다. Langfuse trace 검증은 이번 범위에서 제외했다.

## 주요 판단과 이유

- 기존 `ResultPage`의 revision 저장 및 코칭 호출 경로가 이미 테스트되어 있어, D8 범위에서 동일 기능을 새로 구현하지 않았다.
- Mock E2E는 실제 사용자·Supabase·외부 LLM을 호출하지 않으므로 운영 E2E 완료로 표현하지 않았다.
- `--remove-orphans`는 실행 중이던 다른 `n8n` 컨테이너까지 정리할 위험이 있어 README의 종료 절차에서 제외했다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `README.md` | D8 최소 흐름의 Mock E2E 실행·성공 기준·한계를 추가 |
| `docs/project2-checkpoint-work-cards.md` | README 운영 구조 항목을 부분 완료 및 근거로 갱신 |
| `docs/worklogs/2026-09-30_1130_d8-minimum-flow-runbook.md` | 수행·검증·미확인 사항 기록 |

## 5. 검증

```text
frontend: npm test -- --run
결과: 24 files, 100 tests passed

frontend: npm run build
결과: exit 0; Vite production build 완료

docker compose -f docker-compose.yml -f docker-compose.e2e.yml up --build --abort-on-container-exit --exit-code-from coaching-e2e coaching-e2e
결과: API와 frontend health check 통과. coaching-e2e JSON에서 screen=ok, api_proxy=ok, mock_contract=needs_more_info, http_status=200, MCP 4개 도구 확인.

로컬 인증 브라우저 E2E (2026-09-30)
결과: `GET /api/job-postings` 200, `GET /api/ncs/backend-competencies` 200,
`POST /api/practice-sessions` 201, `POST /analysis-jobs` 202,
반복 `GET /analysis-jobs/{job_id}` 200, `POST /analysis-jobs/{job_id}/answer-revisions` 201.
코칭 결과 화면과 `/api/agent` 응답에서 `status=needs_more_info`를 확인했다.

환경 복구 확인
결과: `.env` 복원 뒤 frontend 컨테이너를 재빌드했고, Supabase 설정이 번들에 포함된 것을 확인했다.
재기동 뒤 frontend root와 API health가 200이었고, API의 로컬 직접 확인 포트는 `http://localhost:18000/health`였다.
```

## 6. 발견한 문제 / 남은 리스크

- Vite/esbuild는 샌드박스 환경에서 상위 디렉터리 읽기 권한 오류가 발생했다. 권한 환경에서 동일 테스트와 build는 통과했다.
- frontend production bundle 경고가 500 kB 초과로 표시됐다. 이번 D8 재현 절차 범위의 기능 오류가 아니므로 별도 성능 개선 작업으로 분리한다.

## 미확인 사항

- Vercel/Cloud Run 배포 URL, 운영 환경변수 및 CORS 설정
- Langfuse 운영 trace 및 Prompt production/rollback

## 7. 다음 작업

- 배포 환경이 준비되면 같은 사용자 흐름을 외부 URL에서 수행하고 D8/D9 체크포인트에 증거를 추가한다.
- README에 운영 URL과 로컬·운영 환경 차이를 실제 검증 후 추가한다.
