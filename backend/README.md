# Backend runtime notes

## 모델 없는 코칭 Thin Slice

`POST /api/agent`는 모델 선정 전 FastAPI·서버 문맥·Pydantic 출력 계약을 확인하기 위한 Mock 경로를 제공한다. `.env`에서 `COACHING_MOCK_ENABLED=true`로 명시한 개발 환경에서만 활성화한다. 기본값과 배포 환경에서는 `unavailable`을 반환한다.

Swagger `/docs`에서 Bearer JWT를 설정한 뒤 다음 개발 fixture ID를 사용한다.

```json
{
  "action": "analyze",
  "question_id": "preset-04",
  "answer_revision_id": "00000000-0000-0000-0000-000000000101",
  "job_snapshot_id": "00000000-0000-0000-0000-000000000201"
}
```

이 fixture의 답변·공고는 실제 사용자나 실제 채용공고 자료가 아니다. FastMCP는 `get_question`, `get_practice_attempt`, `get_job_context`, `compare_attempts` 네 도구를 제공하며 `MCP_INTERNAL_SECRET`으로 서명한 최대 5분 내부 토큰만 허용한다. 비교 토큰은 사용자와 1차·2차 코칭 결과 ID를 정확히 고정하고, 서버는 저장 결과만 비교해 추가 LLM 호출을 만들지 않는다. 실제 secret과 토큰을 모델 입력, 브라우저 응답, 로그와 Git에 넣지 않는다. 코칭 문맥 조회는 [코칭 FastAPI·MCP Thin Slice Spec](../docs/specs/coaching-thin-slice.md), 비교 계약은 [1차·2차 답변 근거 비교 Spec](../docs/specs/attempt-comparison.md)을 따른다.

질문 문맥은 [고정 Skill 묶음](../skills/interview-coach/SKILL.md)의 질문 유형, 기준 버전, 활성 기준 ID와 일치해야 한다. 서버는 `criteria.json`과 질문 유형 문서를 함께 로드하고 불일치하면 모델 호출 전에 `409 context_error`로 차단한다. 현재 기준은 팀 초안이며 상세 계약은 [코칭 Skill 런타임 Spec](../docs/specs/coaching-skill-runtime.md)을 따른다.

코칭 실패 응답은 `detail.state`, `detail.code`, `detail.message`, `detail.retryable`을 공통으로 사용한다. 출력·요청 스키마 위반은 `schema_violation`, 인증 실패는 `auth_error`, 제한 시간은 `timeout`, 요청 제한은 `rate_limited`다. 프런트는 이 상태만 보고 재로그인 또는 재시도 UI를 결정한다.

Langfuse가 설정된 경우 trace 이름은 `coaching.analyze`로 고정한다. prompt·Skill 버전, 모델, 지연, token, 비용, 실패 상태, 기준·부족 항목 수만 허용한다. 답변·인용·공고 URL·token은 기록하지 않으며 사용자와 연습 ID도 `COACHING_OBSERVATION_SALT`가 있을 때만 HMAC 가명 키로 기록한다. 상세 계약과 E2E 절차는 [코칭 평가·관측·E2E Spec](../docs/specs/coaching-evaluation-ops.md)을 따른다.

## 기본 질문 WAV

- 기본 질문 10개는 검수된 사전 생성 WAV만 사용한다. 브라우저는 Supabase Storage에 직접 접속하지 않고, 로그인 없이 `GET /api/preset-questions/{questionId}/audio`를 호출한다.
- API는 카탈로그에서 `accepted`·primary로 수용된 `preset-01`~`preset-10`만 `audio/wav`로 반환한다. 없는 질문·draft·자산 누락은 `404`, private Storage 읽기 실패는 `503`이며 다른 화자·런타임 TTS로 대체하지 않는다.
- `SUPABASE_SERVICE_ROLE_KEY`는 FastAPI 서버의 secret 환경 변수에만 둔다. 브라우저 환경 변수, API 응답, 로그, Git에 넣지 않는다. 배포 환경에서는 `CORS_ALLOWED_ORIGINS`에 실제 프런트 Origin을 쉼표로 구분해 설정한다.

### 운영 반입 순서

1. 다른 조원의 Supabase 운영 담당자가 PR의 `20260824034429_preset_question_audio.sql`을 검토한 뒤, 연결된 CLI에서 migration을 적용하고 `preset-question-audio`가 private인지 확인한다.
2. service-role 환경 변수가 설정된 backend 환경에서만 현재 프로세스의 `PRESET_QUESTION_SOURCE_DIR`를 지정하고 아래 명령을 실행한다. 이 도구는 10개 입력 WAV를 모두 24 kHz·mono·PCM16으로 먼저 검증하며, 한 업로드라도 실패하면 이번 실행에서 성공한 객체를 정리한다.

```powershell
Set-Location backend
python scripts/upload_preset_question_audio.py --source-dir $env:PRESET_QUESTION_SOURCE_DIR
```

3. 현재 카탈로그는 질문자 10개를 이미 `accepted`로 가리킨다. 따라서 10개 업로드가 모두 끝나기 전에는 이 기능을 배포하지 않는다. 로그인 없이 `preset-01`과 `preset-10`이 `200 audio/wav`, `preset-11`이 `404`인지 확인한다. 로컬 `local-results/`의 검수 요약과 원본 WAV는 Git에 넣지 않는다.

팀 Supabase 연결의 전체 절차와 주의사항은 [기본 질문 WAV · Supabase 연결 인수인계](../docs/handoffs/preset-question-audio-supabase-handoff.md)를 따른다.

## 사용자 입력 질문 TTS

- FastAPI와 같은 GPU에서 실행할 때는 Python 3.12.13, CUDA PyTorch, `backend/requirements-question-tts.txt`가 필요합니다.
- 같은 프로세스에서 로드하려면 `.env`에 `QUESTION_TTS_MODEL_PATH=`로 승인된 로컬 `candidate_04_questioner` checkpoint directory를 지정합니다. 비워 두면 FastAPI는 `TTS_WORKER_URL`의 별도 GPU Worker를 사용하고 비공개 Storage 저장·소유권·24시간 만료는 기존 질문 TTS 서비스에서 처리합니다.
- 실제 모델 경로, checkpoint, WAV는 Git에 넣지 않습니다.
- 모델이 없거나 CUDA·Qwen 초기화에 실패하면 API는 기본 화자로 대체하지 않고 `503 Service Unavailable`을 반환합니다.
- 생성된 질문 WAV는 private Storage에 24시간만 보관합니다. 이 질문 전용 endpoint는 코치 피드백을 처리하지 않으며, 분석 LLM 기반 코치 피드백은 별도 [코치 피드백 TTS Spec](../docs/specs/coach-feedback-tts.md)의 endpoint·소유자 검증·24시간 삭제 규칙을 따릅니다.
- 서버 시작 시 모델은 한 번만 로드하고, 사용자 질문과 무관한 짧은 내부 primer를 한 번 수행합니다. primer 출력은 전송·저장하지 않습니다.

### 팀 운영 순서

1. Supabase 운영 담당자가 PR에서 `supabase/migrations/20260819090000_question_tts_audio.sql`을 검토한 뒤, 연결된 CLI에서 `supabase db push`로 적용한다. Dashboard SQL Editor로 신규 구조를 임의 적용하지 않는다.
2. 서로 다른 두 사용자 JWT로 `POST /api/questions/tts`, 소유자 `GET /api/audio/questions/{audioId}`, 타인 `GET`의 404를 확인한다. `question-tts-audio`는 public bucket으로 바꾸지 않는다.
3. 서버 전용 scheduler에서 `python backend/scripts/cleanup_expired_question_tts_audio.py`를 실행한다. service-role key는 브라우저·API 응답·로그에 넣지 않는다.

### API 계약

`POST /api/questions/tts`는 스트리밍을 지원하지 않는 클라이언트용 완성-WAV 폴백이다. JSON `{"question": "..."}`을 받고, 공백 제외 1~200자의 질문에만 `audioUrl`, `text`, `durationMs`, `expiresAt`을 반환한다. 모델 입력에만 원문 뒤 `//`가 내부적으로 붙으며, 응답·저장 메타데이터에는 붙지 않는다.

`POST /api/questions/tts/stream`은 같은 JSON과 Bearer JWT를 받아 `application/x-ndjson; charset=utf-8`을 반환한다. 이벤트 순서는 `start` → `audio` 0개 이상 → `complete` 또는 `error`다. `audio`의 PCM은 24 kHz·mono·PCM16 Base64이고, 브라우저는 Web Audio API로 순서대로 재생한다. 실제 발화 뒤 -35 dB 이하 구간이 0.5초 이어지면 생성기를 닫아 뒤쪽 무음·잡음을 제한한다.

유효하지 않은 입력은 400, 인증 실패는 401, 모델을 시작하지 못한 경우는 스트림 시작 전 503이다. 스트림 도중 모델·저장소 오류는 `error` 이벤트로 끝나며 `complete`와 보관 WAV를 남기지 않는다. 사용자가 취소하거나 연결을 끊으면 부분 WAV·메타데이터를 저장하지 않는다.

`GET /api/audio/questions/{audioId}`는 소유자에게만 `audio/wav`를 반환한다. 만료됐거나 소유자가 다른 경우는 404다.

### 실제 GPU 검수

실제 모델 검수는 모델 경로를 `.env`에 설정한 GPU Worker에서만 수행한다.

```powershell
python backend/scripts/evaluate_question_tts.py
```

이 명령은 Git에서 제외된 `local-results/question-tts-stream-<timestamp>/`에 13개 고정 비민감 질문의 WAV, `metrics.jsonl`, `summary.json`을 만든다. `metrics.jsonl`에는 질문 원문·사용자 ID·모델 경로 없이 request ID, 첫 audio 시점, 전체 생성 시간, RTF, peak GPU memory, 종료 방식, WAV 형식, 수동 검수 상태만 기록한다. WAV를 직접 들어 보고 24 kHz/mono/PCM_16, 잡음, 마지막 음절, 자연스러움을 각각 `accepted` 또는 `rejected`로 검수한다. 일반 길이 질문의 95% 이상이 요청 후 5초 안에 첫 audio를 받고, 생성·재생 성공률도 각각 95% 이상일 때만 앱 연결 후보로 판단한다.
