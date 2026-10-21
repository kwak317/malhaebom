# 저장소 구성 안내

초기 스캐폴드를 실제 말해봄 Mk.2 구현으로 확장한 현재 구조를 설명합니다. 실행 상태와 남은 작업은 [저장소 구현 점검표](repository-audit.md)를 함께 확인하세요.

## 한눈에

```text
backend/              FastAPI, 코칭 계약, STT·TTS 경계
frontend/             React + TypeScript + Vite, Nginx
skills/               Skill별 폴더, 코칭 질문 유형 문서와 criteria.json
mcp_server/           소유권·만료를 검사하는 읽기 도구
evals/                합성 평가셋 30건과 모델 비교 runner
configs/              질문 Rubric, STT·TTS 메타데이터
supabase/             DB·비공개 Storage migration
docs/specs/           기능별 Why · Goal · What · How · AC
EVAL_REPORT.md        실제 모델 선정 뒤 채울 평가 리포트
Dockerfile            FastAPI 이미지
docker-compose.yml    API와 프런트 실행 구성
```

## 주요 파일

### `backend/main.py`

FastAPI 진입점입니다. 모델 추론 없이 확인하는 `/health`, 코칭 `/api/agent`, 음성·분석·연습 기록 API를 조립합니다. 요청·응답 계약은 `backend/app/schemas/`에 있고 도메인 로직은 `backend/app/services/`에 둡니다.

### `backend/services/llm.py`

현재는 모델 출력의 Pydantic 형식, 서버가 허용한 ID, 답변 원문의 정확한 인용을 검증하고 응답의 `status`, `evidence`, `gaps`를 계산합니다. 실제 provider 호출·재시도는 모델 선정 뒤 이 경계에 연결합니다. 라우터나 UI가 provider SDK를 직접 호출하지 않게 유지합니다.

### `skills/interview-coach/`

- `SKILL.md`: 모델이 따라야 할 입력 경계와 판정 절차
- `problem-solving.md`: 문제 해결 질문의 세부 규칙과 경계 사례
- `preset-interview.md`: 다른 기본 질문의 판정 규칙
- `criteria.json`: 질문 유형, 기준 ID, Skill·criteria 버전, 검토 상태

비교 후 면접 대화 규칙은 `skills/interview-conversation/SKILL.md`에 있고, 공고 요구사항·README 분석 Skill도 각각의 폴더에 둡니다.

FastAPI와 평가 runner가 같은 묶음을 읽습니다. 현재 `review_status`는 `team_draft`이며 RAG나 외부 검색을 사용하지 않습니다.

### `mcp_server/server.py`

`get_question`, `get_practice_attempt`, `get_job_context`, `compare_attempts` 네 읽기 도구를 제공합니다. 서버가 발급한 짧은 내부 토큰, 사용자 소유권, 만료, 허용 ID를 검사하며 임의 SQL·URL·유사 문서 검색은 제공하지 않습니다. 비교 도구는 저장된 1차·2차 코칭 결과만 읽고 추가 LLM 호출 없이 criterion과 전달력 변화를 계산합니다.

### `evals/`

`dataset.jsonl`에는 합성 평가 30건이 정상 12, 경계 10, 실패 유도 8로 고정되어 있습니다. `run_model_comparison.py`는 동일 평가셋과 Skill 묶음으로 계약 준수율, 판정 정확도, 비용, p50·p95, 실패 상태를 비교합니다. 실제 사용자·공고 데이터는 포함하지 않습니다.

### `EVAL_REPORT.md`

Mock fixture는 runner와 회귀 검출을 확인하는 기준선이며 모델 후보가 아닙니다. 후보 모델이 정해지면 같은 평가셋을 두 번 이상 측정해 변경점, 회귀, 비용, 지연과 출시 게이트를 채웁니다. 측정하지 않은 수치를 완료로 기록하지 않습니다.

### Docker 구성

```bash
cp .env.example .env
docker compose up --build
```

- 웹: <http://localhost:18080>
- API 문서: <http://localhost:8000/docs>
- 상태: <http://localhost:8000/health>

Postgres 컨테이너는 포함하지 않으며 데이터·인증은 설정된 Supabase를 사용합니다. GPU 모델 가중치는 이미지에 넣지 않고 별도 Worker로 연결합니다.

### `.env.example`

필요한 키 이름과 안전한 기본값만 공유합니다. 실제 `.env`, service-role key, provider key, 모델 절대 경로는 Git에 넣지 않습니다. 로컬 FastAPI용 `TTS_WORKER_URL`과 Docker API용 `TTS_WORKER_DOCKER_URL`을 구분합니다.

## 협업 규칙

`main`에 직접 push하지 않습니다. 기능 브랜치에서 작업하고 PR 검토 뒤 병합합니다. 새 기능은 `docs/specs/_example.md` 형식을 따라 Spec을 먼저 작성하고, 관련 테스트와 실행 문서를 함께 갱신합니다.

## 다음 작업

1. `.env.example`을 복사하고 필요한 비밀 값은 로컬 `.env`에만 넣습니다.
2. `docker compose up --build`와 Compose E2E로 현재 계약을 재현합니다.
3. 후보 모델이 정해지면 30건을 같은 조건으로 반복 실행합니다.
4. 외부 기준 검토와 실제 Langfuse 결과를 `EVAL_REPORT.md`에 증거와 함께 기록합니다.
