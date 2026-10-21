# Worklog — FastAPI mock 서버의 실제 HTTP 응답 확인

- 일시: 2026-09-28 08:54 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 요구사항/결정: D5 세로 슬라이스 및 사용자의 mock 활성화·실제 응답 요청

## 1. 목적

앞선 TestClient 검증에서 나아가 mock을 켠 실제 Uvicorn 서버에 계약 입력을 전송하고 HTTP 200 응답을 확보한다. 기존 사용 중인 서버와 미커밋 변경은 보존한다.

## 2. 작업 전 상태

- checkout: `codex/team-local-auth-18080`, commit `65aef86`, 기존 수정·미추적 파일이 있는 상태.
- API: `proj2-3-complete-flow-api-1`, 호스트 포트 `18000`, mock 비활성.
- 이미지: `sha256:ddf4e8a67231a0e3778c0a9e287025563e5ef5c0b5dd60d0f2b7f9a1a95fca63`.
- 실제 코칭 서비스가 구성되면 mock 환경변수보다 서비스가 우선한다.
- 기존 `DevelopmentAccessTokenVerifier`와 `COACHING_E2E_ENABLED`를 사용하면 개발용 mock 서버를 실제 로그인과 분리해 실행할 수 있다.

## 3. 수행 내용

1. 기존 서버와 동일한 이미지를 사용해 별도 `malhaebom-mock-20260928-085227` 컨테이너를 실행했다. 새 이미지 빌드·외부 pull은 하지 않았다.
2. `127.0.0.1:18001:8000`에만 공개하고 mock·테스트 인증을 켰다. 테스트 토큰은 새로 생성해 환경변수로만 전달했다.
3. 실 공급자 모델·자격증명은 비웠으며 기존 `.env`를 새 컨테이너에 전달하지 않았다. 읽기 전용 컨테이너와 `/tmp` tmpfs를 사용했다.
4. `uvicorn backend.main:app --host 0.0.0.0 --port 8000 --lifespan off`로 실행했다. 코칭 HTTP 확인에 불필요한 음성·TTS 시작 동작은 생략했다.
5. 호스트에서 실제 HTTP로 정상 요청 1건과 오류 요청 5건을 보냈다. 응답·헤더·검증 기록을 저장했다.
6. CLI `agent-browser`가 설치되어 있지 않아 CUA in-app browser로 `/docs`의 렌더링을 확인했다. 문서 제목·엔드포인트·입력/응답 스키마가 초기 접근성 트리에 표시되었으며 빈 화면·오류 overlay·수집된 console error가 없었다.
7. 재현 스크립트, 전체 응답, 상태 기록을 남겼다. 서버는 재확인용으로 계속 실행한다.

## 주요 판단과 이유

18000 서버를 변경하면 진행 중인 실제 코칭 흐름에 영향을 줄 수 있어 별도 포트에서 검증했다. 애플리케이션이나 인증 코드를 새로 만들지 않고 이미 있는 개발용 mock 인증 모드를 사용했다. 고정 예제의 출력이며 실제 사용자 답변 의미 분석으로 해석하지 않는다.

## 4. 변경 파일

| 파일 | 내용 |
| --- | --- |
| 이 Worklog | 활성화·HTTP 검증·범위 기록 |
| [결과 디렉터리](../../../output/api/fastapi-mock-http-20260928-085227/README.md) | 전체 요청/응답·오류 응답·실행 정보·검증 정보·재현 스크립트 |

애플리케이션 코드·Compose·기존 환경 파일은 변경하지 않았다. 작업 전 기록한 기존 파일 455개의 SHA-256과 Git 상태가 보존된 것을 확인했다.

## 5. 검증

```text
별도 mock 서버 GET /health: HTTP 200 / {"status":"ok"}
POST /api/agent 유효 입력: HTTP 200 / needs_more_info
응답 최상위 필드 9개 / Pydantic CoachingResponse 검증
문제 상황 met / 원인 판단 partial / 본인 행동 met
행동 선택 이유 not_observed / 결과 확인 not_observed
근거 4개 / 부족 항목 3개 / 확인 질문 1개 / 다음 행동 2개
인증 없음: 401
유효하지 않은 테스트 토큰: 401
없는 snapshot: 404
질문과 답변 문맥 불일치: 409
계약에 없는 answer_text: 422
```

위 결과는 TestClient 대신 호스트 → Docker 공개 포트 → Uvicorn → FastAPI의 실제 HTTP 호출이다. 새 서버에서 실 코칭 서비스가 구성되지 않은 것과 테스트 인증 verifier 종류를 별도 Python 프로세스로 확인했다. `replay.py`의 재요청 응답이 저장 JSON과 일치했고, 현재 이미지의 `CoachingResponse`로 검증했다. 관련 코드 5개 파일의 로컬/이미지 SHA-256이 일치했다. 기존 API 컨테이너 ID·시작 시각·mock 설정은 같았고 API health와 프런트엔드는 각각 HTTP 200이었다.

## 6. 발견한 문제 / 남은 리스크

검증 결과를 콘솔에 요약하는 보조 코드가 기준 필드를 `label`로 읽어 `KeyError`를 냈다. 응답·오류 검증 파일은 이미 정상 저장되었고 API 문제는 아니었다. 실제 필드 `assessment`를 확인한 뒤 저장 JSON과 재현 스크립트로 검증을 마쳤다.

mock은 고정 개발 예제다. 실제 모델 품질과 도메인 판정자의 검토 결과를 증명하지 않는다.

## 미확인 사항

실제 사용자 로그인·DB 문맥 조회·LLM 호출·음성 모델 시작·브라우저 전체 코칭 흐름은 이 mock HTTP 검증 범위에 포함하지 않았다.

## 7. 다음 작업

계약 입력을 받아 mock 응답을 반환하는 실제 HTTP 검증을 완료했다. 필요 시 결과 디렉터리의 `replay.py`로 같은 서버에 다시 요청할 수 있다.

## 후속 요청 — 처리 순서 문서

- 사용자 요청에 따라 실행 화면 대신 처리 순서를 설명하는 `말해봄_D5_FastAPI_mock_입출력_흐름.md`를 프로젝트 루트에 작성했다.
- 계약 입력 4개 필드, 요청·인증 검사, mock 선택, 서버 문맥 확인, 고정 출력 생성, 출력 검증, JSON 반환의 7단계를 정리했다. 응답 발췌는 기존 실제 HTTP 응답 파일과 대조했다.
- 시연 화면을 준비하며 `output/api/mock-input-response-demo-20260928-0900/`에 HTML·CSS·JS·Python·README 초안을 생성했으나 사용자가 파일 설명으로 범위를 좁혀 브라우저 시연은 진행하지 않았다. 새로 띄운 18002 웹 서버는 확인한 프로세스에 SIGTERM을 보내 중단했다. 초안 파일은 삭제하지 않았다. 기존 18001 mock 컨테이너는 유지했다.
- 애플리케이션 코드나 기존 실행 설정을 변경하지 않았다.

## 후속 요청 — 계약 입력의 mock 호출 테스트 (09:06:59 KST)

- 기존 `replay.py`를 실제 실행해 JSON 입력을 `localhost:18001/api/agent`에 보내고 HTTP 200 응답을 받았다.
- 현재 컨테이너의 `CoachingAnalyzeRequest`와 `CoachingResponse`로 입력·응답 스키마를 검증했다. 반환 상태는 `needs_more_info`이며, 컨테이너 서버 로그의 POST 200 기록과 일치했다.
- 요청, 전체 응답, 검증 결과, 서버 로그, 설명을 [이번 결과](../../../output/api/fastapi-mock-test-20260928-090659/result.md)에 저장했다. 인증 토큰은 결과 파일에 저장하지 않았다.
- 기존 서버·환경·애플리케이션 코드는 변경하지 않았다. 추가 UI나 frontend/MCP 테스트를 실행하지 않았다.
