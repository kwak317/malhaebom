# Worklog — MCP 오류 프런트엔드 타입 계약 정합성

- 일시: 2026-10-01 10:30 KST
- 작업자/에이전트: SJeongHyeon / Codex
- 관련 이슈/PR: PR #142
- 관련 요구사항/결정: 서버·클라이언트 실패 상태 계약 정합성

## 1. 목적

MCP gateway 장애 시 서버가 반환하는 `mcp_error`를 프런트엔드 API 타입도 표현하게 해, 서버와 클라이언트의 실패 상태 계약을 맞춘다.

## 2. 작업 전 상태

서버 `CoachingFailureState`에는 `mcp_error`가 있고 PR #142의 API 회귀 테스트도 503 응답의 해당 상태를 검증했다. 반면 `frontend/src/api/coaching.ts`의 union type에는 이 값이 없어 TypeScript 계약이 불일치했다.

## 3. 수행 내용

- `CoachingFailureState` union에 `mcp_error`를 추가했다.
- `mcp_error`를 타입에 대입하는 컴파일 회귀 테스트를 추가했다.

## 주요 판단과 이유

- 상태값의 런타임 전달은 이미 서버 응답 body를 통해 동작하므로, UI 문구나 재시도 정책을 확장하지 않고 타입 계약만 최소 수정했다.
- 새 테스트는 기존 union에서 TypeScript build가 실패하는 것을 먼저 확인해 누락을 재현했다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `frontend/src/api/coaching.ts` | `mcp_error` 실패 상태 추가 |
| `frontend/src/api/coaching.test.ts` | MCP 오류 상태의 컴파일 회귀 테스트 추가 |
| `docs/worklogs/2026-10-01_1030_mcp-error-frontend-type.md` | 변경·검증 기록 |
| `docs/worklogs/README.md` | Worklog 목록 갱신 |

## 5. 검증

```text
npm --prefix frontend run build
수정 전: TS2322, "mcp_error"는 CoachingFailureState에 할당 불가

npm --prefix frontend test -- src/api/coaching.test.ts
수정 후: 5 passed

npm --prefix frontend run build
수정 후: success (기존 500 kB chunk-size warning만 출력)
```

초기 sandbox 실행은 Vite/esbuild가 상위 경로를 읽지 못해 시작 단계에서 실패했다. 같은 명령을 권한 확장 환경에서 재실행해 위 결과를 확인했다.

## 6. 발견한 문제 / 남은 리스크

- production build는 500 kB 초과 chunk 경고를 계속 출력한다. 이번 타입 계약 수정의 범위 밖이며 build는 성공했다.

## 미확인 사항

- 실제 MCP 장애 UI 흐름은 PR #142의 기존 logged-in Compose 검증 기록을 재실행하지 않았다. 이번 변경은 서버 응답을 프런트엔드 타입이 수용하게 하는 계약 수정이다.

## 7. 다음 작업

- PR #142에 수정 커밋을 push하고 CI 결과를 확인한 뒤 리뷰 스레드에 해결 내용을 남긴다.
