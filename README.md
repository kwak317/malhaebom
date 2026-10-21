# 말해봄 Mk.2

말해봄 Mk.2는 신입 개발자 취업준비생이 한국어 면접 답변을 녹음하고,
답변에서 확인되는 근거를 바탕으로 다시 연습하도록 돕는 면접 코칭 에이전트입니다.
React 웹 앱, STT·VAD 분석 API, Skill·MCP·LLM 코칭과 평가 자료를 함께 관리합니다. 2차 프로젝트에서는 RAG를 사용하지 않습니다.

## 배포 주소

- 소개페이지: [malhaebom.xyz](https://malhaebom.xyz/) · [www.malhaebom.xyz](https://www.malhaebom.xyz/)
- 연습 시작: [/app/practice](https://malhaebom.xyz/app/practice) — 필요한 로그인 후 채팅
- 기존 서비스 홈: [/app/](https://malhaebom.xyz/app/)
- Backend API: [Cloud Run](https://malhaebom-mk2-fmf5h3xp4q-du.a.run.app) · [/health](https://malhaebom-mk2-fmf5h3xp4q-du.a.run.app/health)

2026-10-10 운영 제품 코드 기준: main `e6ecc4b`, Vercel `dpl_A6EgFiF3ABvaGNm8Q41QA2ed6A2P`,
Cloud Run `malhaebom-mk2-main-sync-final-1010` 트래픽 100%.
[실행 소스 동기화 증거](docs/evidence/serving-source-main-sync-20261010.json)와
[최신 미리보기 PR #251](https://github.com/aihuman-7th/proj2-3/pull/251)을 확인합니다.
주소·파일 일치 검증과 신규 Google OAuth/실녹음 전체 E2E·코칭 품질 평가는 구분합니다.

## 주요 기능

1. NCS 역량 자기점검, 선택적 GitHub README·이력서 PDF 분석과 사용자 확인
2. 확인한 경험 기반 공고 추천·검색, 공고 원문 분석·요구사항 선택
3. 기본/직접 입력 질문, 녹음·WAV 제출, STT 원문 확인·수정·표준어 변환
4. 답변 근거 코칭, 자유채팅·동의 후 경험 반영, 재답변 비교·꼬리질문
5. 이력서 초안·문장 다듬기·PDF 다운로드, 연습 결과·채팅 조회·기록 삭제

## 먼저 찾을 자료

| 목적 | 안내 |
| --- | --- |
| 현재 구현·배포 확인 | [현재 상태](docs/CURRENT_STATE.md) |
| 제출물과 남은 검증 확인 | [제출 증거](docs/SUBMISSION_EVIDENCE.md) · [평가 리포트](EVAL_REPORT.md) |
| 전체 문서 찾기 | [문서 안내](docs/README.md) |
| 운영 기준·후보·평가 원본 구분 | [평가 안내](evals/README.md) |
| 변경 이유·과거 실행 확인 | [Worklog 전체 인덱스](docs/worklogs/INDEX.md) |
| 개발 환경 실행 | 아래 Docker Compose/로컬 실행 절차 |

공개 주소·health·Frontend Origin CORS는 비밀값 없이 다음 명령으로 다시 확인할 수 있습니다.

```bash
python scripts/check_deployment_smoke.py
```

세 검사가 모두 `PASS`여야 성공하며, 다른 배포를 확인할 때는 `--frontend-url`,
`--api-url`, `--origin`을 명시합니다. 이 smoke 검사는 인증 후 사용자 흐름이나
Langfuse trace를 검증하지 않습니다.

## 팀원

| 이름 | GitHub |
| --- | --- |
| 곽호준 | [@kwak317](https://github.com/kwak317) |
| 김재훈 | [@nanocode00](https://github.com/nanocode00) |
| 서정현 | [@SJeongHyeon](https://github.com/SJeongHyeon) |

> 초기 코드 이관은 PR #1로 반영되었습니다. 이후 검증된 로컬 clean-clone 실행 절차는 아래에 기록하며, 외부 운영 배포 검증 여부는 [현재 상태](docs/CURRENT_STATE.md)와 별도로 구분합니다.

## 프로젝트 문서 안내

| 역할 | Canonical 문서 |
| --- | --- |
| 개발·Git/PR·Issue·CI 운영 규칙 | [AGENTS.md](AGENTS.md) |
| 실험·STT/TTS 재현 규칙 | [docs/experiments/README.md](docs/experiments/README.md) |
| 프로젝트 개요 | [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) |
| 현재 상태 | [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md) |
| 목표 상태 | [docs/TARGET_STATE.md](docs/TARGET_STATE.md) |
| 공식 요구사항·프로젝트 적용 해석 | [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) |
| 제약조건 | [docs/CONSTRAINTS.md](docs/CONSTRAINTS.md) |
| 최종 제출 증거 인덱스 | [docs/SUBMISSION_EVIDENCE.md](docs/SUBMISSION_EVIDENCE.md) |
| 교육·기술 참고 지식 | [docs/knowledge/COURSE_KNOWLEDGE.md](docs/knowledge/COURSE_KNOWLEDGE.md) |
| 코칭 도메인 Skill·규칙 | [skills/interview-coach/SKILL.md](skills/interview-coach/SKILL.md) |
| 신뢰 경계 | [docs/TRUST_BOUNDARY.md](docs/TRUST_BOUNDARY.md) |
| 도메인 출처·이용조건 | [docs/research/DOMAIN_SOURCE_REGISTER.md](docs/research/DOMAIN_SOURCE_REGISTER.md) |
| 아키텍처 | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| 구현 계획 | [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) |
| 평가 계획 | [evals/README.md](evals/README.md) |
| 평가 결과·제출 양식 | [EVAL_REPORT.md](EVAL_REPORT.md) |
| 주요 의사결정 | [docs/DECISIONS.md](docs/DECISIONS.md) |
| 경쟁 서비스 조사 | [docs/research/COMPETITOR_RESEARCH.md](docs/research/COMPETITOR_RESEARCH.md) |
| 채용공고 조사 | [docs/research/JOB_POSTING_RESEARCH.md](docs/research/JOB_POSTING_RESEARCH.md) |
| 도메인 조사 | [docs/research/DOMAIN_RESEARCH.md](docs/research/DOMAIN_RESEARCH.md) |
| 통과 기획서 원본·버전 주의사항 | [docs/proposal/README.md](docs/proposal/README.md) |
| Worklog 규칙 | [docs/worklogs/README.md](docs/worklogs/README.md) |
| Worklog 템플릿 | [docs/worklogs/TEMPLATE.md](docs/worklogs/TEMPLATE.md) |
| 첫 문서 병합 기록 | [docs/worklogs/2026-09-16_docs-bootstrap.md](docs/worklogs/2026-09-16_docs-bootstrap.md) |

## Worklog 규칙

**의미 있는 작업을 수행한 뒤 Worklog를 작성한다.** 위치는 [docs/worklogs/](docs/worklogs/README.md)이며, 문서 변경도 포함합니다. 목적·작업 전 상태·수행 내용·판단 이유·변경 파일·검증·발견한 문제·미확인 사항·다음 작업을 기록합니다. 현재 상태와 중요한 결정이 바뀌면 해당 기준 문서도 함께 갱신합니다.

## 현재 구성

```text
backend/          FastAPI, STT·VAD 분석, LLM 호출 진입점
frontend/         React + TypeScript + Vite 웹 앱
skills/           면접 답변 판단 기준과 코칭 규칙
mcp_server/       FastMCP 조회 도구 4개와 HTTP·stdio transport
evals/            고정 평가셋·과거 결과·명시 선택 실험 후보
prompts/          Prompt 템플릿과 버전별 재현 자료
configs/          STT·TTS·질문 Rubric 설정
supabase/         DB와 비공개 Storage migration
docs/             최신 안내·제출 증거·Spec·과거 작업/실험·보관 자산
```

`skills/interview-coach/`에는 코칭 도메인 규칙과 질문별 기준이, `prompts/`에는
역할·입출력 지시가 분리되어 있습니다. 활성 기준과 판정은 서버에서도 검증하며,
추가 질문의 팀 초안 규칙은 외부 면접관 검수를 완료한 것으로 표현하지 않습니다.

현재 코칭 provider 호출·출력 계약·재시도는 `backend/app/services/coaching_runtime.py`,
Prompt와 Skill 조립은 `backend/app/services/coaching_prompt.py`를 참조합니다.
버전별 검증 범위와 Langfuse production 승격 여부는
[현재 상태](docs/CURRENT_STATE.md)를 기준으로 확인합니다.

## 채점자 빠른 재현

Docker Desktop(Compose 포함)이 실행 중인 환경에서 다음 순서로 진행합니다.

```bash
git clone https://github.com/aihuman-7th/proj2-3.git
cd proj2-3
cp .env.example .env
# .env에 아래 표의 Supabase 주소·키, OpenRouter/NCS 키, MCP 비밀값 입력
docker compose up
```

Windows PowerShell에서는 `cp .env.example .env` 대신 `Copy-Item .env.example .env`를 사용할 수 있습니다. 처음 실행하면 Compose가 이미지를 자동 빌드합니다. 로그 창을 유지하고 웹 <http://localhost:18080>와 API <http://localhost:8000/health>를 확인합니다. API의 정상 응답은 `{"status":"ok"}`입니다. 다른 터미널의 `docker compose ps`에서 두 서비스가 healthy인지 확인할 수 있습니다.

- 포트가 사용 중이면 `.env`의 `WEB_PORT`·`API_PORT`를 바꾸고 해당 주소로 접속합니다.
- 예제의 `STT_WARMUP_ENABLED=false`는 시작할 때 음성 모델 다운로드를 하지 않습니다. 첫 음성 분석 시 모델 준비/다운로드 시간이 별도로 필요합니다.
- 화면·API 기동과 실제 로그인→음성 분석→코칭 재현은 구분합니다. 전체 흐름에는 아래 표의 유효한 키, 필요한 Supabase migration, Google 로그인 시 로컬 origin 허용이 필요합니다.
- 준비 대화까지 재현하려면 해당 DB migration과 Prompt 구성이 준비된 환경에서 `PREPARATION_CONVERSATION_ENABLED=true`를 설정합니다. TTS는 별도 Worker가 필요한 선택 기능입니다.
- 종료는 `docker compose down`입니다. 데이터/볼륨을 삭제하는 옵션은 사용하지 않습니다.

새 clone 기동 시간의 측정 결과와 빌드 캐시·외부 서비스 검증 범위는 [재현 점검](docs/evidence/clean-compose-reproduction-20261010.md)에 기록합니다. CPU 이미지 개선 후 새 clone 후보는 검증 환경에서 **6분 35초에 웹/API healthy**를 확인했습니다. 시간·환경·모델 캐시를 사용한 WAV 검사 범위는 [CPU 재현 점검](docs/evidence/local-cpu-reproduction-20261010.md)을 확인합니다. 모든 PC의 최초 의존성/음성 모델 다운로드가 10분 이내임을 보장하는 기록은 아닙니다.

### 로컬 CPU STT/VAD 확인

기동 후 개인정보 없는 한국어 WAV를 준비해 아래 명령으로 실제 전사와 음성 구간을 확인할 수 있습니다. 첫 실행에는 모델 준비 시간이 추가됩니다. 외부 코칭 API·로그인·DB 검사는 포함하지 않습니다.

```bash
docker compose cp ./sample.wav api:/tmp/local-cpu-test.wav
docker compose exec -T api python scripts/check_local_cpu_stt.py /tmp/local-cpu-test.wav
```

## Docker Compose로 실행

로컬 Compose는 `Dockerfile.local-cpu`로 CPU 전용 PyTorch/TorchAudio 2.8.0과 호환 PyAV 16.1.0을 설치하고 STT를 `cpu/int8`로 고정합니다. 로컬 프런트는 `frontend/Dockerfile.local-reproduction`으로 소개 HTML까지 포함합니다. 운영 배포용 Dockerfile들과 설정은 유지합니다. STT 모델도 기존 `large-v3-turbo`를 유지합니다. 최초 음성 분석에는 약 1.62GB의 모델 파일 다운로드가 필요하며 기동 시간과 별도입니다. 로컬 이미지는 `HF_HUB_DISABLE_XET=1`로 HTTP 다운로드를 사용합니다. 로컬 Compose에서 `STT_DEVICE=cuda`를 지정해도 CPU 설정이 적용됩니다. 로컬에서 직접 전사하려면 `STT_REMOTE_URL`을 비워 둡니다.

Python 컨테이너는 3.12, frontend 빌드는 Node 22입니다. 아래 절차는 2026-09-30에 새 clone 기반으로 검증했습니다. Supabase 설정·migration 적용과 외부 모델 접근 권한은 각 실행 환경에서 별도로 준비해야 합니다.

```bash
cp .env.example .env
# .env에 Supabase 공개/서버 키와 필요한 모델 설정 입력
# API 컨테이너에서 호스트 TTS Worker를 쓰면
# TTS_WORKER_URL=http://host.docker.internal:8100 으로 설정
docker compose up --build
```

- 웹: <http://localhost:18080>
- API 문서: <http://localhost:8000/docs>
- 상태 확인: <http://localhost:8000/health>

### 빈 환경에서의 최초 실행

기존 checkout의 `.env`, `node_modules`, Docker 컨테이너를 재사용하지 않고 아래처럼 새 폴더에서 검증합니다. Docker Desktop이 실행 중이어야 합니다.

```powershell
cd $env:TEMP
git clone https://github.com/aihuman-7th/proj2-3.git malhaebom-clean-run
cd malhaebom-clean-run
Copy-Item .env.example .env
notepad .env
docker compose up --build
```

`docker compose up --build`는 로그를 계속 표시하므로 그 창은 켜 둡니다. 새 PowerShell 창에서 상태를 확인합니다.

```powershell
cd $env:TEMP\malhaebom-clean-run
Invoke-WebRequest -UseBasicParsing http://localhost:8000/health |
  Select-Object -ExpandProperty Content
```

성공 응답은 `{"status":"ok"}`입니다. 별도 명시가 없으면 `API_PORT=8000`, `WEB_PORT=18080`을 사용합니다.

### 실제 최소 흐름에 필요한 환경 변수

값은 팀의 안전한 공유 경로에서 받아 `.env`에만 입력합니다. 실제 값, JWT, `Authorization` 헤더, service-role key는 화면 캡처·채팅·Git에 올리지 않습니다.

| 범위 | 필요한 변수 | 용도 |
| --- | --- | --- |
| 로그인·저장 | `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SERVICE_ROLE_KEY` | 브라우저 로그인과 서버의 사용자별 데이터 접근 |
| Docker에서 Hosted Supabase 연결 | `SUPABASE_DOCKER_URL` | Docker API 컨테이너가 별도 주소를 써야 할 때 설정; 일반적으로 Hosted URL과 동일 |
| NCS 역량 선택 | `NCS_API_KEY` | data.go.kr의 NCS API에 활용 신청·등록된 키 |
| README 분석·공고 추천·코칭 | `OPENROUTER_API_KEY`, `COACHING_PROVIDER=openrouter`, `COACHING_LLM_MODEL`, `COACHING_LLM_BASE_URL` | 외부 LLM 호출. `COACHING_LLM_API_KEY`는 별도로 지정하지 않으면 `OPENROUTER_API_KEY`를 사용 |
| 내부 MCP 문맥 조회 | `MCP_INTERNAL_SECRET` | 32자 이상 서버 전용 비밀값 |

`VITE_API_BASE_URL`, `VITE_COACHING_DEMO_TOKEN`, Langfuse 변수는 같은 Compose의 실제 사용자 최소 흐름에 필수가 아닙니다. `ALIO_API_KEY`, `MOFE_PUBLIC_INSTITUTION_JOB_API_KEY`, `INCHEON_RECRUITMENT_API_KEY`는 해당 공공 채용공고 제공자를 테스트할 때만 추가합니다.

실제 브라우저 검증은 로그인 → NCS 역량 선택 → GitHub README 분석 → 공고/요구사항/질문 선택 → WAV 업로드 또는 녹음 → 분석 완료 → 전사문 확정 → 코칭 결과 확인 순서로 진행합니다.

코칭 모델은 OpenRouter의 Gemini 3.5 Flash-Lite를 기본으로 사용합니다. API 키는 `.env`에만
저장하고 Git에는 올리지 않습니다.

```text
OPENROUTER_API_KEY=발급받은_키
COACHING_PROVIDER=openrouter
COACHING_LLM_MODEL=google/gemini-3.5-flash-lite
COACHING_LLM_BASE_URL=https://openrouter.ai/api/v1
```

호스트 Ollama를 코칭 모델로 쓸 때는 `.env`에 다음 값을 둡니다. Compose의 API는
`COACHING_OLLAMA_DOCKER_URL`을 통해 호스트 Ollama에 접속합니다.

```text
COACHING_PROVIDER=ollama
COACHING_MODEL=qwen2.5-coder:latest
COACHING_OLLAMA_URL=http://127.0.0.1:11434
COACHING_OLLAMA_DOCKER_URL=http://host.docker.internal:11434
```

`*-base` 모델은 코드 완성용이라 코칭 대화에 사용하지 않습니다. 로컬 Ollama 코칭은
최초 모델 로딩과 구조화 출력 시간을 고려해 기본 timeout 180초를 적용합니다.

웹 컨테이너는 `/api`, `/analysis-jobs`, `/practice-records` 요청을 API 컨테이너로
전달합니다. 같은 Compose로 배포할 때 `VITE_API_BASE_URL`은 비워 둡니다. 프런트와
API를 서로 다른 도메인에 배포할 때만 프런트 빌드 환경에 공개 API URL을 설정합니다.
`VITE_SUPABASE_*`를 비우면 Compose는 같은 `.env`의 공개 `SUPABASE_URL`과
`SUPABASE_PUBLISHABLE_KEY`를 프런트 빌드 값으로 사용합니다.

### 코칭 Mock Compose E2E

운영용 `.env`와 분리된 override로 코칭 결과 화면 → Nginx API proxy → FastAPI Mock 출력 검증과 네 MCP 조회 도구를 함께 확인합니다.

```bash
docker compose -f docker-compose.yml -f docker-compose.e2e.yml \
  up --build --abort-on-container-exit --exit-code-from coaching-e2e coaching-e2e
```

성공하면 `screen`, `api_proxy`, `mock_contract`, `mcp_tools`가 포함된 한 줄 JSON을 출력합니다. 고정 E2E 토큰은 이 override에서만 허용되며 `COACHING_MOCK_ENABLED=true`가 아니면 API가 시작을 거부합니다. 실행 뒤에는 `docker compose -f docker-compose.yml -f docker-compose.e2e.yml down`으로 컨테이너를 정리합니다.

브라우저에서 Mock 결과 카드만 확인할 때는 같은 E2E 구성을 띄우고 <http://localhost:18080/demo/coaching>을 엽니다.

#### D8 최소 흐름 재현 확인

아래 명령은 실제 사용자 음성·Supabase·외부 LLM을 사용하지 않는 **Mock 계약 E2E**입니다. 프런트 화면, Nginx의 `/api` proxy, FastAPI의 출력 계약, MCP 조회 도구가 한 번에 연결되는지만 확인합니다.

```powershell
docker compose -f docker-compose.yml -f docker-compose.e2e.yml `
  up --build --abort-on-container-exit --exit-code-from coaching-e2e coaching-e2e
```

성공 시 `coaching-e2e` 컨테이너가 다음 필드를 포함한 JSON 한 줄을 출력합니다.

```json
{
  "screen": "ok",
  "api_proxy": "ok",
  "mock_contract": "needs_more_info",
  "mcp_tools": ["compare_attempts", "get_job_context", "get_practice_attempt", "get_question"],
  "http_status": 200
}
```

실행 뒤에는 이 Compose 실행이 만든 컨테이너만 정리합니다. 다른 프로젝트 컨테이너를 제거하는 `--remove-orphans`는 사용하지 않습니다.

```powershell
docker compose -f docker-compose.yml -f docker-compose.e2e.yml down
```

실제 사용자 최소 흐름은 로그인 → 검토 공고 1개 선택 → 요구사항 1~2개 선택 → 질문 선택 → 5~60초 녹음 → STT 전사문 확인·수정 → 전사 revision 저장 → 코칭 결과 확인 순서입니다. 전사문 확인 후에는 브라우저가 원문을 코칭 API에 직접 보내지 않고, 서버가 발급한 `answer_revision_id`와 `job_snapshot_id`로만 코칭을 요청합니다. 실제 로그인·음성·외부 provider 검증은 운영 환경변수와 Supabase migration이 준비된 환경에서 별도로 수행해야 합니다.

## 로컬에서 따로 실행

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
```

새 터미널에서:

```bash
cd frontend
npm ci
npm run dev
```

위 로컬 uvicorn 명령은 `.env`를 자동으로 읽는 옵션이 없습니다. 필요한 환경변수를 shell에 제공하거나 `uvicorn backend.main:app --env-file .env --reload --port 8000`을 사용합니다. Frontend 공개 설정은 `frontend/.env.example`을 참고합니다. 실제 실행은 미검증입니다.

Vite 개발 서버는 API 기본값으로 `http://127.0.0.1:8000`을 사용합니다.

## GPU 기능

STT는 `STT_DEVICE=cuda`, `STT_COMPUTE_TYPE=float16`로 GPU를 사용할 수 있습니다.
질문·코치 TTS는 승인된 모델 가중치가 있는 별도 GPU Worker를 실행하고
로컬 FastAPI에는 `TTS_WORKER_URL`, Docker의 API 컨테이너에는
`TTS_WORKER_DOCKER_URL`로 연결합니다. 기본 Docker 주소는
`http://host.docker.internal:8100`입니다. Worker 자체에는 저장소 밖의 승인 모델
경로를 `TTS_WORKER_MODEL_PATH`로 전달합니다. 모델 가중치, 사용자 음성, 생성 WAV, 실제
`.env` 값은 저장소에 올리지 않습니다.

## 현재 완료와 보류

현재 구현과 검증 경계는 [현재 상태](docs/CURRENT_STATE.md), 제출 항목별 확보/미확인은
[제출 증거 인덱스](docs/SUBMISSION_EVIDENCE.md)를 기준으로 확인합니다.
[저장소 구현 점검표](docs/repository-audit.md)와 날짜가 붙은 실험은 당시 기록입니다.
자동 계약 점수·사람 품질 판단·실제 사용자 E2E는 서로 다른 증거로 구분합니다.

## 프런트엔드 단독 배포

`frontend/`를 Vercel 프로젝트 루트로 배포할 수 있습니다. 이 경우 다음 변수를
Vercel 빌드 환경에 설정합니다.

```text
VITE_SUPABASE_URL
VITE_SUPABASE_PUBLISHABLE_KEY
VITE_API_BASE_URL
```

API에는 해당 프런트 주소를 `CORS_ALLOWED_ORIGINS`로 등록해야 합니다.

## 협업 규칙

[AGENTS.md](AGENTS.md)가 브랜치·커밋·PR review-size·동료 승인·작성자 merge·Issue 운영 규칙의 기준입니다. Review Core는 400 LOC 안팎을 권장하고 800 LOC를 hard limit으로 사용합니다. `docs/*`를 포함한 허용 작업 브랜치에서 작업하며 main에 직접 push하지 않습니다. 기능 구현 전 [Spec 양식](docs/specs/_example.md)을 사용합니다.

기존 수업 안내의 조원 소개 PR 과제와 타 조 코드 복사 제출 금지 원칙은 유지합니다. 제출 시각·태그 운영의 확인 상태는 [요구사항](docs/REQUIREMENTS.md)을 따릅니다.

> **상태 정정 (2026-09-23):** 아래 문단의 `/api/agent`·HTTP `/mcp` 미연결 설명은 과거 상태다. 현재 두 endpoint와 고정 Skill, Langfuse 호출 계측은 연결되어 있으며, 남은 운영 검증 범위는 [CURRENT_STATE](docs/CURRENT_STATE.md)의 최신 섹션을 우선한다.

현재 구현·목표 차이와 Issue 후보는 [CURRENT_STATE](docs/CURRENT_STATE.md), 음성 모델·데이터·benchmark 인수 상태는 [음성 인수 기록](docs/experiments/2026-09-17_voice-asset-intake.md)을 참고합니다. 현재 `/api/agent`와 HTTP `/mcp`는 연결되지 않았으며 새 Skill·Langfuse 통합도 검증 전입니다.
