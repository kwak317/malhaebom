# Worklog — 공통 JSON provider를 OpenAI SDK로 전환

- 일시: 2026-09-28 15:01
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음. GitHub 작업 금지 요청 유지.
- 관련 요구사항/결정: `docs/specs/openai-sdk-provider.md`, `docs/DECISIONS.md`.

## 1. 목적

사용자가 LLM 호출을 OpenAI SDK 또는 LangChain으로 변경할 수 있는지 요청했다. 기존 단순 서버 문맥 조회·JSON 검증 구조에 맞춰 이미 설치된 OpenAI SDK를 선택했다. 모델·키·프롬프트·출력 계약·웹검색 전용 호출은 유지하며 GitHub 작업은 하지 않는다.

## 2. 작업 전 상태

공통 provider가 `httpx.Client.post`로 JSON을 전송했고 OpenAI SDK는 의존성에 이미 선언되어 있었다. 변경 전 관련 테스트 9개가 통과했다. 기존 작업의 큰 미커밋 변경을 보존하기 위해 현재 파일과 해시 manifest를 별도 백업했다.

## 3. 수행 내용

Spec 작성 → 현재 파일/이미지 백업 → 공통 provider와 transport 테스트 전환 → 전체 회귀 테스트 → 로컬 API 반영 → 실제 SDK 응답 확인 → 문서 및 변경 범위 검토.

## 주요 판단과 이유

추가 체인이 필요하지 않아 OpenAI SDK만 사용했다. `max_retries=0`으로 SDK의 숨은 추가 요청을 방지하고 기존 서버 repair 정책을 유지한다. 공급자 전용 옵션은 `extra_body`로 전달한다.

## 4. 변경 파일

- `backend/app/services/coaching_runtime.py`: `OpenAI` client와 `chat.completions.create`, OpenRouter `extra_body`, 오류 매핑. SDK 자동 재시도 0회.
- `backend/tests/test_coaching_runtime.py`: 실제 SDK + MockTransport로 전송 JSON·인증·토큰 한도·HTTP/연결/타임아웃 오류·잘못된 응답·서버 repair를 확인한다.
- `docs/specs/openai-sdk-provider.md`, `docs/CURRENT_STATE.md`, `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, 이 Worklog.

## 5. 검증

```bash
docker run --rm --network none -v "$PWD:/app:ro" --entrypoint python proj2-3-complete-flow-api -m unittest discover -s backend/tests -v
docker compose build api
docker compose up -d --no-deps api
docker exec proj2-3-complete-flow-api-1 python /tmp/verify_live_sdk.py
```

- 변경 전 관련 테스트 9개 통과. 전환 후 관련 테스트 13개 통과 후 SDK 경유 서버 repair 회귀 테스트를 추가했다. 최종 전체 backend **320개 통과**(11.406초). 격리 Docker 실행으로 실제 계정 환경변수의 간섭을 제외했다.
- 기존 선언 `openai>=1.60,<2`, 실행 SDK 1.109.1. 새 의존성이나 LangChain을 추가하지 않았다.
- API Compose build와 API만 재생성 성공. `http://localhost:18000/health` 200, `http://localhost:18080/practice` 200, 인증 없는 두 agent POST 401. 두 컨테이너 healthy.
- API 이미지: `sha256:84d85e241e687b63cd166da80d332807722e9bde4dcfcbaada93e6ceb1484df5`. frontend는 기존 이미지 `sha256:44b5ba81fffd10228079eab5007f02118e62d5fd731eeb6fdb4b142d702df228` 그대로다.
- 호스트/실행 컨테이너 `coaching_runtime.py` SHA256: `64fb8f7e6103cc77e340e3e113e9addaa686e1b80416d30e29ed75ad1e5520ff` 일치.
- 실행 컨테이너의 실제 `google/gemini-3.5-flash-lite`로 SDK 호출: `/api/agent` 1건 status=ok, `/api/agent/chat` start·message·finish 3건 active·active·finished. 총 4건 HTTP 200, Pydantic/API 계약 검증 통과.
- 실시간 확인은 API TestClient·테스트 인증과 합성 문맥을 사용했다. 사용자 DB에 쓰거나 관측 원문을 외부로 내보내지 않았다. 실제 OpenRouter 요청은 기존 키/모델로 수행했다.

## 증거·백업

- 결과·실행 스크립트·테스트/빌드 로그: `/Users/kkwakbab/Documents/ChatGPT/2차 프로젝트/output/openai-sdk-20260928/`.
- 변경 전 주요 파일 및 전체 파일 해시 manifest: `/var/folders/vp/7pp0r4tx0sz43lhc2tmlkmq00000gn/T/malhaebom-openai-sdk-before-bqwz_vy5`.
- 변경 전 API 이미지 보존 태그: `malhaebom-api:before-sdk-20260928-1501`.

## 6. 발견한 문제 / 남은 리스크

전체 `git diff --check`는 기존 `.github/PULL_REQUEST_TEMPLATE.md`의 3·13행 끝 공백을 보고했다. 이 파일은 이번 작업에서 수정하지 않고 보존했다. 이번 변경 파일의 diff·공백 및 백업 manifest 대비 변경 범위를 별도로 확인했다.

## 미확인 사항

최종 테스트·모델 확인은 실패 없이 통과했다. 로그인/실제 녹음/사용자 DB까지의 브라우저 E2E와 README·공고 요구사항·검색 의도 각각의 실시간 외부 호출은 이번에 재수행하지 않았다. 이 소비자들은 기존 전체 단위·통합 테스트로 확인했다. 제출용 검사 도구 자체를 재실행하지 않았으므로 스크린샷 경고의 소멸 여부는 별도 확인 대상이다.

## 7. 다음 작업

SDK 호출과 서버 출력 계약의 책임 경계를 유지한다. 후속 운영 검증은 실제 사용자 연습 흐름으로 진행한다. 기존 작업 파일은 보존했고 commit/push/PR 생성/merge를 수행하지 않았다.
