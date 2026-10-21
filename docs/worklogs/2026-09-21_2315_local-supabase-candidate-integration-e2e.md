# Worklog — 로컬 Supabase Docker 인증 통합 및 최종 LLM 후보 E2E 코칭 파이프라인 검증

- 일시: 2026-09-21 23:15 KST
- 작업자/에이전트: Antigravity
- 관련 이슈/PR: PR #42 (팀 로컬 Supabase Docker 인증 지원 반영), test/final-candidate-service-integration
- 관련 요구사항/결정: P2-03, 로컬 Supabase 실행 및 전체 E2E 코칭 파이프라인 검증

## 1. 목적

PR #42 변경사항을 통합 브랜치에 안전하게 반영하고, 로컬 Supabase 스택(`127.0.0.1:54321`)과 전체 Docker 스택(Frontend: `18080`, Backend: `8000`)을 기반으로 실제 사용자 E2E 코칭 파이프라인(`Frontend -> Supabase Auth -> 공고 조회 -> 세션 생성 -> 음성 업로드/STT/VAD -> 전사 확정 -> /api/agent -> OpenRouter -> validator -> coaching_runs 저장 -> 결과 반환`)을 두 최종 후보 모델(`google/gemini-3.5-flash-lite`, `openai/gpt-5.6-luna`) 각각 3건(normal-01, boundary-13, failure-30)에 대해 라이브 실행하고 검증한다.

## 2. 작업 전 상태

- `test/final-candidate-service-integration` 브랜치에 이전 세션의 uncommitted 변경사항(candidate service integration runner, strict schema 정규화 등)이 존재함.
- `origin/main`에 PR #42(로컬 Supabase Docker 인증 지원)가 머지되어 있음.
- 백엔드 컨테이너와 프론트엔드 컨테이너가 실행 중이나, `.env`의 `SUPABASE_SERVICE_ROLE_KEY`가 문자열 키 형태로 되어 있어 로컬 Supabase DB 접근 시 401 권한 오류 발생.
- `backend/scripts/bootstrap_project_venv.py`에 `--with-dev-tools` 기능 필요(프로젝트 로컬 `.venv`에 Node 22 및 Supabase CLI 설치).

## 3. 수행 내용

1. **PR #42 및 개발 도구 스크립트 통합**:
   - `backend/app/core/auth.py`, `supabase_settings.py`, `backend/app/main.py`, `docker-compose.yml`, `supabase/config.toml` 등의 변경사항을 작업 트리에 반영.
   - `backend/scripts/bootstrap_project_venv.py`에 `--with-dev-tools`를 추가하여 프로젝트 로컬 `.venv` 내에 Node v22.14.0 및 Supabase CLI v2.117.0을 체크섬 검증 후 안전하게 추출 및 링크.
   - `docs/PYTHON_ENVIRONMENT.md` 갱신.
2. **로컬 Supabase 스택 구동 및 인증 환경 구성**:
   - `.venv/bin/supabase start`를 통해 API(54321), DB(54322), Studio(54323), Mailpit(54324) 구동 확인.
   - 로컬 Supabase의 실제 service_role JWT(`eyJ...`)를 추출하여 `.env`의 `SUPABASE_SERVICE_ROLE_KEY`에 반영하고, 32바이트 `MCP_INTERNAL_SECRET` 생성 및 주입.
   - Docker `api` 및 `frontend` 컨테이너 재빌드/재생성.
3. **전체 서비스 사용자 E2E 파이프라인 검증**:
   - 로컬 Supabase에서 실제 테스트 계정 회원가입/로그인으로 JWT 발급.
   - `Frontend(:18080) -> GET /api/job-postings`: 정상 목록 반환 확인.
   - `Frontend(:18080) -> POST /api/practice-sessions`: 연습 세션 생성 성공.
   - `Frontend(:18080) -> POST /analysis-jobs`: 7초 음성 업로드 및 Faster-Whisper/Silero VAD 비동기 분석 완료 확인.
   - `Frontend(:18080) -> POST /analysis-jobs/{job_id}/answer-revisions`: 전사문 확정 및 Answer Revision 생성 성공.
   - `Frontend(:18080) -> POST /api/agent`: stdio MCP를 통한 문맥 로딩(`get_question`, `get_practice_attempt`, `get_job_context`) -> OpenRouter 실제 호출 -> Pydantic validator 검증 -> Supabase `coaching_runs` 저장 -> 200 OK 응답 확인.
4. **최종 2개 모델 x 3건 라이브 통합 검증 실행**:
   - `evals/run_service_candidate_integration.py --live` 실행 (승인된 6개 유료 요청 범위 내).
   - `google/gemini-3.5-flash-lite`: 3/3 성공 (HTTP 200, Contract 100%, Validator 100%, p50 3.44s, 총 비용 $0.01132, 재시도 0회).
   - `openai/gpt-5.6-luna`: 1/3 성공, 2건 502 (boundary-13, failure-30에서 JSON parse 에러 발생으로 schema violation 처리).
   - 실측 결과에 기반하여 기본 프로덕션 후보 모델을 `google/gemini-3.5-flash-lite`로 설정.
5. **회귀 검증 및 Dockerfile 보강**:
   - Dockerfile에 `COPY scripts/ /app/scripts/` 추가 및 `PYTHONPATH=/app:/app/backend` 설정.
   - Docker `api` 컨테이너 내에서 전체 274개 단위 테스트 스위트 실행 (`Ran 274 tests ... OK`).

## 주요 판단과 이유

- **Google Gemini 3.5 Flash-Lite 기본 후보 채택**:
  실제 서비스 통합 E2E 경로에서 Flash-Lite는 3건 모두(정상, 경계, 실패 유도) 단 1회의 재시도나 스키마 위반 없이 100% 통과(p50 3.44초, 비용 $0.011)한 반면, GPT-5.6 Luna는 경계 및 실패 유도 케이스에서 JSON parse 단계 실패(502 bad gateway)가 발생함. 따라서 안정성과 속도 면에서 Flash-Lite를 기본 모델(`COACHING_LLM_MODEL=google/gemini-3.5-flash-lite`)로 선정함.
- **로컬 격리 및 보안 준수**:
  원격 Supabase 및 외부 저장소에는 일체 쓰기 작업을 수행하지 않았으며, 오직 로컬 Docker Supabase(`127.0.0.1:54321`)만을 사용함. 민감한 API 키와 JWT 비밀값은 로그나 커밋에 노출하지 않음.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `backend/scripts/bootstrap_project_venv.py` | `--with-dev-tools` 옵션 추가 (Node v22, Supabase CLI 로컬 설치) |
| `docs/PYTHON_ENVIRONMENT.md` | `--with-dev-tools` 사용법 문서화 |
| `Dockerfile` | `COPY scripts/` 추가 및 `PYTHONPATH=/app:/app/backend` 설정 |
| `backend/app/services/coaching_runtime.py` | OpenRouter temperature 생략 및 GPT-5 strict schema 정규화 |
| `docs/CURRENT_STATE.md` | 로컬 Supabase Docker 통합 및 라이브 E2E 검증 현황 갱신 |
| `EVAL_REPORT.md` | 2개 모델 x 3건 서비스 통합 실측 결과 갱신 |
| `docs/worklogs/2026-09-21_2315_local-supabase-candidate-integration-e2e.md` | 전체 작업 로그 작성 |

## 5. 검증

1. **전체 단위 테스트**:
   ```text
   docker compose exec -T -e PYTHONPATH=/app:/app/backend -e OPENROUTER_API_KEY="" -e MCP_INTERNAL_SECRET="" api python -m unittest discover -s backend/tests
   Ran 274 tests in 4.466s - OK
   ```
2. **라이브 6건 통합 검증**:
   ```text
   docker compose exec -T api python evals/run_service_candidate_integration.py --live
   - google/gemini-3.5-flash-lite: 3/3 성공 (HTTP 200, Contract 통과, Validator 통과)
   - openai/gpt-5.6-luna: 1/3 성공 (정상 케이스 통과, 경계/실패 케이스 502)
   ```
3. **사용자 E2E 파이프라인 실측**:
   - `Frontend(18080)` 프록시를 통한 공고 목록 조회 -> 세션 생성 -> 음성 분석 -> 전사 확정 -> `/api/agent` 코칭 응답(200 OK) -> Supabase `coaching_runs` 테이블 저장 확인.
4. **JSON Envelope 정규화 보완 및 Luna 실패 2건 선별 재검증**:
   - 원인: Luna의 `coach-boundary-13` 실패는 모델 추론 문제가 아니라 마크다운 code fence(```json)로 감싸진 JSON 응답에 대한 strict JSON 파싱 실패였음.
   - 조치: `OpenAICompatibleJsonProvider`에 conservative한 markdown code fence(` ```json ` / ` ``` `) 정규화 함수 `_normalize_json_envelope` 추가 (앞뒤 설명 텍스트 임의 발췌는 방지하여 계약 보존).
   - 단위 테스트: `backend/tests/test_coaching_runtime.py`에 code fence 정규화 및 Provider unwrap 단위 테스트 추가 (통과).
   - 선별 재검증 (`coach-boundary-13`, `coach-failure-30`):
     - `coach-boundary-13`: **HTTP 200 OK 통과** (지연 10,510ms, 계약/Validator 100% 통과, retry 0회, contract repair 0회, 비용 $0.0027466).
     - `coach-failure-30`: **HTTP 502 실패 유지** (OpenRouter에서 빈 객체/스키마 위반 응답 반환으로 계약 실패 2회 후 502).
   - 결론: code fence 정규화로 `coach-boundary-13`은 정상 복구되었으나, `coach-failure-30`(날조 유도)에서는 Luna가 여전히 스키마 계약을 충족하지 못함.

## 6. 발견한 문제 / 남은 리스크

- `openai/gpt-5.6-luna`는 OpenRouter 엔드포인트에서 구조화 출력(structured output) 시 비정상 JSON 형식(schema violation)을 반환하는 경우가 확인되어, 단독 기본 모델로는 부적합하며 fallback 모델로 사용할 때 추가적인 repair 파서 검토가 필요함.
- `openai/gpt-5.6-luna`: markdown code fence 정규화로 경계 케이스(`coach-boundary-13`)는 정상 복구되었으나, 허위 성과 날조 유도 케이스(`coach-failure-30`)에서는 OpenRouter 호출 시 schema violation(502)이 지속되어, 여전히 단독 기본 모델로는 부적합함.
- `google/gemini-3.5-flash-lite`: 이번 3건 E2E 표본에서 3/3 통과(p50: 3,440ms, p95: 3,584ms [표본 3건 기준])하였으며, 허위 성과 날조 시도도 안전하게 방어함.
- Whisper large-v3-turbo CPU 추론 시 첫 모델 로딩 및 긴 음성 전사에 수십 초의 지연이 발생할 수 있음 (GPU 환경 권장).

## 7. 다음 작업

- 사용자와 최종 결과 리뷰 후 브랜치 정리 및 PR 준비.
- 프론트엔드 UI 화면에서 실제 사용자 브라우저를 통한 수동 플로우 점검.
