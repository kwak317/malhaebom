# Worklog — FastAPI mock 응답 확인

- 일시: 2026-09-28 08:45 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음. 요청 범위는 기존 엔드포인트 응답 확인이다.
- 관련 요구사항/결정: D5 세로 슬라이스의 계약 입력 → FastAPI → mock 응답 확인

## 1. 목적

기존 `POST /api/agent`가 받는 입력과 검증 후 반환하는 mock JSON을 실제 테스트 호출로 확인한다. 현재 실행 컨테이너의 설정과 mock 테스트 결과를 구분한다.

## 2. 작업 전 상태

- 실행 컨테이너: `proj2-3-complete-flow-api-1`, API `http://localhost:18000`.
- Compose working directory: `/Users/kkwakbab/Documents/ChatGPT/2차 프로젝트/proj2-3-complete-flow`.
- checkout commit: `65aef86`이며 기존 미커밋 변경이 있는 상태다.
- API 이미지: `sha256:ddf4e8a67231a0e3778c0a9e287025563e5ef5c0b5dd60d0f2b7f9a1a95fca63`.
- 실행 서버의 `COACHING_MOCK_ENABLED=false`. 설정된 코칭 모델은 `google/gemini-3.5-flash-lite`이며 실제 모델 호출은 이번 작업에서 실행하지 않았다.
- `GET /health`는 HTTP 200, `{"status":"ok"}`. live OpenAPI에 요청·응답 계약이 존재한다.
- `app/main.py`, `coaching_context.py`, `schemas/coaching.py`, `services/llm.py`, `test_coaching_api.py`의 로컬 파일과 컨테이너 파일 SHA-256 일치를 확인했다.

## 3. 수행 내용

1. 요청의 `action`, `question_id`, `answer_revision_id`, `job_snapshot_id` 계약과 `MockCoachingService`의 고정 데모 답변을 확인했다.
2. 실행 컨테이너에서 새 Python 프로세스를 사용했다. 그 프로세스의 코칭 모델 환경값을 비워 실 공급자 구성을 막고, 기존 테스트의 fixture 인증과 mock 설정을 사용했다. 실행 중인 API 프로세스의 설정은 변경하지 않았다.
3. 기존 `CoachingApiTest` 9개를 실행했다. 추가 TestClient 호출로 성공·오류 응답을 확인하고 실제 반환 JSON을 저장했다.
4. 외부 HTTP transport가 사용되면 실패하도록 검사한 상태에서 mock 테스트를 통과했다. LLM·MCP·DB에 실제 분석 요청을 보내지 않았다.
5. 실행 서버에는 인증 없는 합성 요청만 보내 HTTP 401을 확인했다.

## 주요 판단과 이유

mock은 서버에 고정된 로그인 오류·로그 확인·토큰 만료 코드 수정 답변의 개발 예제다. 임의 사용자 답변을 의미 분석한 결과가 아니며, 고정 평가셋의 품질·전문가 판정을 증명하지 않는다. 운영 API의 mock 설정을 켜거나 컨테이너를 재시작할 필요 없이 FastAPI TestClient로 현재 컨테이너 코드의 반환 계약을 확인했다.

## 4. 변경 파일

| 파일 | 내용 |
| --- | --- |
| 이 Worklog | 확인 환경·재현·검증·한계 기록 |
| [request.json](../../../output/api/fastapi-mock-20260928-084527/request.json) | 실제 사용한 합성 요청 본문 |
| [response.json](../../../output/api/fastapi-mock-20260928-084527/response.json) | HTTP 200 mock 반환 JSON 전체 |
| [verification.json](../../../output/api/fastapi-mock-20260928-084527/verification.json) | 테스트·오류 경로·실행 출처·파일 hash |

애플리케이션 코드·Compose·환경 파일은 수정하지 않았다.

## 5. 검증

실행 방식: `docker exec`의 별도 Python 프로세스에서 `COACHING_LLM_MODEL`, `COACHING_MODEL`, `COACHING_PROVIDER`를 빈 값으로 지정하고 기존 unittest 및 TestClient를 실행했다. 인증은 기존 `FakeVerifier`, 관측은 `RecordingObservationSink`를 사용했다.

```text
CoachingApiTest: Ran 9 tests / OK
mock 유효 요청: HTTP 200 / status=needs_more_info / model=mock-v1
필드: status, job_alignment, intent_assessment, criterion_assessments,
        evidence, gaps, clarifying_question, next_actions, example_answer
기준별 판정: C met / R partial / A met / D not_observed / V not_observed
evidence 4개 / gaps 3개 / 확인 질문 1개 / 다음 행동 2개
인증 없음: 401
없는 snapshot: 404
질문·문맥 불일치: 409
허용되지 않은 answer_text: 422
테스트에서 mock 비활성·실 공급자 없음: HTTP 200 / unavailable
실행 중인 localhost:18000에 인증 없는 요청: 401 / UNAUTHORIZED
외부 HTTP transport 호출: 없음
```

## 6. 발견한 문제 / 남은 리스크

mock의 기준별 결과는 고정 예제다. 형식·ID·인용 검증 통과를 실제 도메인 품질 평가로 해석하지 않는다.

## 미확인 사항

이번 작업에서 실 사용자 토큰, 운영 LLM 분석, 실제 MCP·DB 조회·저장, 배포 환경 및 브라우저 코칭 흐름은 재검증하지 않았다.

## 7. 다음 작업

mock의 전체 반환값과 계약 확인은 완료했다. 운영 코칭 응답 확인은 실제 인증된 문맥을 사용하는 별도 검증 범위다.
