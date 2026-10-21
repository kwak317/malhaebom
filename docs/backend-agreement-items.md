# 말해봄 Backend 협의 필요사항

> 이 문서는 HTTP API 구현 전 작성한 협의 기준의 역사 기록입니다. 현재 계약과 완료 상태는 [Frontend MVP 팀 인수인계](frontend-mvp-team-handoff.md), [PRD](prd.md), [저장소 구현 점검표](repository-audit.md)를 우선합니다. 아래의 “미구현·미정” 표시는 당시 상태입니다.

이 문서는 현재 말해봄 프론트엔드 와이어프레임과 기존 backend 구조를 기준으로, Frontend와 Backend를 실제 연결하기 전에 최종 합의해야 하는 기술 계약만 정리한 문서입니다.

현재 backend에는:

- `FasterWhisperTranscriber` Python 서비스
- `transcribe_audio.py` CLI

가 있으나,

- FastAPI/Flask HTTP endpoint
- 음성 업로드 API
- 분석 작업 생성 API
- 분석 상태 조회 API
- 삭제 API

등은 아직 구현되어 있지 않은 상태입니다.

따라서 아래 내용은 Backend 담당자와 최종 계약이 필요한 항목입니다.

## 1. 분석 API 구조

현재 상태:

backend에는 프론트가 호출할 수 있는 HTTP API가 아직 없고, 현재는 다음 CLI 방식입니다.

```bash
python backend/scripts/transcribe_audio.py ...
```

프론트에서 필요한 것:

녹음 완료 후 브라우저에서 음성 파일과 Attempt 정보를 서버에 전달할 수 있어야 합니다.

백엔드와 최종 결정할 것:

- 분석 요청 endpoint
- `POST /api/analysis` 형태를 사용할지 여부
- 요청 시 음성을 같이 업로드할지
- 업로드와 분석 작업 생성을 분리할지

우선순위: P0
상태: 미정

## 2. 분석 처리 방식 - 동기 / 비동기

현재 상태:

프론트 흐름은 `분석하기 → 분석 중 → 분석 완료 → 결과 화면`입니다. GPU/STT 처리 시간이 존재하므로 응답 방식을 정해야 합니다.

프론트에서 필요한 것:

분석 중 화면에서 작업 상태를 표시하고, 성공 시 결과 화면으로 이동하며, 실패 시 재시도할 수 있어야 합니다.

백엔드와 최종 결정할 것:

- 분석 완료까지 기다렸다가 결과를 반환하는 동기 방식인지
- `jobId`를 먼저 반환하고 상태를 조회하는 비동기 방식인지
- 비동기라면 polling 여부와 주기
- timeout 기준

예상 비동기 응답:

```json
{ "jobId": "..." }
```

우선순위: P0
상태: 미정

## 3. 음성 업로드 Request 계약

현재 상태:

프론트에서는 브라우저 녹음 결과를 `Blob`/`File` 형태로 전달할 예정입니다. backend 내부에서는 `wav`/`webm`/`mp3` 확장자를 확인하고 있습니다.

프론트에서 필요한 것:

지원 형식과 제한에 맞춰 음성 파일을 업로드하고, 최소·최대 녹음 시간과 파일 크기 오류를 처리해야 합니다.

백엔드와 최종 결정할 것:

- `multipart/form-data` 사용 여부
- `audio` field 이름
- 지원 MIME type과 기본 음성 format
- 최대 파일 크기
- 최소 5초·최대 60초 서버 검증 여부
- Frontend 검증과 동일한 제한을 Backend에서도 검증할지

현재 후보: 최소 5초, 최대 60초, 최대 15MB, `wav`/`webm`/`mp3`

우선순위: P0
상태: 미정

## 4. 분석 요청 시 함께 전달할 데이터

현재 상태:

프론트에서 다음 값을 관리할 후보가 있습니다.

- `questionId`
- `attemptNo`
- `sourceId`
- `sessionId`
- `audio`

프론트에서 필요한 것:

분석 요청과 1차·2차 결과를 동일한 세션으로 연결할 수 있어야 합니다.

백엔드와 최종 결정할 것:

- 실제 request에 포함할 값
- `sourceId` 생성 주체
- `sessionId` 생성 주체
- `attemptNo` 저장 위치
- `questionId` Backend 저장 여부

예상 후보:

```json
{ "sourceId": "...", "sessionId": "...", "questionId": "...", "attemptNo": 1, "audio": "..." }
```

우선순위: P0
상태: 미정

## 5. STT 결과 API Response 계약

현재 상태:

현재 backend 내부 결과 필드는 다음과 같습니다.

- `source_id`
- `model`
- `language`
- `language_probability`
- `audio_duration_sec`
- `processing_time_sec`
- `text`
- `fillers`
- `segments`
- `words`

프론트에서 필요한 것:

- `transcript`
- `answerDurationSec`
- `fillerCounts`
- `segments`
- `wordTimings`

백엔드와 최종 결정할 것:

- 현재 backend 필드명을 API에 그대로 노출할지
- API 계층에서 프론트용 이름으로 normalize할지
- 최종 response schema와 nullable/optional 필드

예: `text → transcript`, `audio_duration_sec → answerDurationSec`

우선순위: P1
상태: 미정

## 6. 최종 분석 결과 Response

현재 상태:

결과 화면에는 STT 전사문, 말하기 속도, 긴 침묵, 반복 표현, 최대 2개의 행동 피드백이 필요합니다. 현재 FasterWhisper backend 결과에는 전사문, 일부 filler, timestamps가 있지만 CPM, 긴 침묵 최종 결과, 반복 표현 분석, 행동 피드백은 없습니다.

프론트에서 필요한 것:

결과 화면에서 별도 임의 계산 없이 계약된 분석 결과와 피드백을 표시할 수 있어야 합니다.

백엔드와 최종 결정할 것:

- 하나의 analysis API response에서 모든 결과를 합쳐 반환할지
- 각 분석 결과를 별도 API/작업으로 처리할지
- 분석 지표의 필드명과 단위
- 피드백 최대 2개 제한을 어느 계층에서 적용할지

예상 후보:

```json
{
  "transcript": "...",
  "metrics": {
    "speakingRate": 345,
    "longSilence": 3,
    "repeatedExpressions": 5
  },
  "feedback": []
}
```

우선순위: P1
상태: 미정

## 7. 분석 상태 Response

현재 상태:

비동기 방식을 사용할 경우 프론트의 분석 중 화면에서 상태를 확인해야 합니다.

프론트에서 필요한 것:

상태에 따라 로딩, 성공, 실패 화면을 구분하고 성공 시 결과를 표시해야 합니다.

백엔드와 최종 결정할 것:

- 상태 enum
- 상태 response schema
- 성공 시 `result` 포함 여부
- 실패 시 `error` 포함 여부

예상 후보:

```json
{ "status": "queued" }
{ "status": "processing" }
{ "status": "success", "result": {} }
{ "status": "failed", "error": {} }
```

우선순위: P1
상태: 미정

## 8. 오류 코드 계약

현재 상태:

현재 backend는 Python 예외가 그대로 발생할 수 있습니다. 프론트에 traceback이나 내부 예외를 그대로 노출하면 안 됩니다.

프론트에서 필요한 것:

공통 오류 구조와 재시도 가능 여부를 기준으로 사용자 메시지와 버튼을 표시해야 합니다.

백엔드와 최종 결정할 것:

- 실제 error code 이름
- HTTP status code
- 재시도 가능한 오류 구분
- 사용자 메시지를 Backend에서 줄지 Frontend에서 mapping할지

오류 코드 후보:

- `FILE_TOO_SHORT`
- `FILE_TOO_LARGE`
- `UNSUPPORTED_AUDIO`
- `NO_SPEECH`
- `STT_FAILED`
- `ANALYSIS_FAILED`
- `ANALYSIS_TIMEOUT`
- `FILE_NOT_FOUND`
- `SERVER_ERROR`

예상 공통 구조:

```json
{ "error": { "code": "STT_FAILED", "message": "..." } }
```

우선순위: P1
상태: 미정

## 9. 분석 재시도 방식

현재 상태:

분석 실패 화면에 `[다시 분석하기]` 기능이 필요합니다.

프론트에서 필요한 것:

원본 음성을 잃지 않은 상태에서 분석 요청을 다시 보내고, 재시도 중 상태를 표시해야 합니다.

백엔드와 최종 결정할 것:

- 기존 업로드 음성을 이용해 분석만 재실행할지
- 새 `jobId`를 생성할지
- 기존 `jobId`를 재사용할지
- 분석 실패 후 원본 음성을 재시도 가능한 동안 유지할지

우선순위: P1
상태: 미정

## 10. 1차 / 2차 Attempt 저장 구조

현재 상태:

서비스 흐름은 `Attempt 1 → 분석 → 피드백 → Attempt 2 → 분석 → 1차/2차 비교`입니다.

프론트에서 필요한 것:

1차와 2차 결과를 동일한 연습 세션에 연결하고, 2차에서 다시 녹음해도 Attempt 3이 아니라 Attempt 2를 갱신할 수 있어야 합니다.

백엔드와 최종 결정할 것:

- `sessionId`, `questionId`, `attemptNo`, `analysisResultId` 저장 구조
- Attempt 2 재녹음 시 기존 데이터 갱신 또는 새 버전 생성 방식
- 1차·2차 결과의 연결 관계

우선순위: P1
상태: 미정

## 11. 1차 / 2차 비교 결과 구조

현재 상태:

최종 결과 화면에는 1차·2차 말하기 속도, 긴 침묵, 반복 표현과 변화 상세가 필요합니다.

프론트에서 필요한 것:

1차·2차 결과를 동일한 구조로 표시하고, 비교값을 조회 화면에서도 재사용해야 합니다.

백엔드와 최종 결정할 것:

- Frontend가 Attempt 1/2 결과를 비교해 계산할지
- Backend가 `comparison` 객체로 만들어 반환할지
- 변화량과 비교 상세의 response schema

예상 후보:

```json
{
  "comparison": {
    "speakingRate": { "attempt1": 380, "attempt2": 350 },
    "longSilence": { "attempt1": 3, "attempt2": 1 },
    "repeatedExpressions": { "attempt1": 5, "attempt2": 2 }
  }
}
```

우선순위: P2
상태: 미정

## 12. 연습 기록 조회 API

현재 상태:

사용자는 첫 화면으로 돌아간 뒤에도 연습 기록 탭에서 완료한 세션을 확인해야 합니다. 최대 24시간 보관, 사용자 삭제, 24시간 이후 자동 삭제 정책은 기존 SDD에서 확정된 사항입니다.

프론트에서 필요한 것:

- 연습 기록 목록 조회
- 질문 클릭 후 세션 상세 결과 조회
- 목록·상세 로딩 및 오류 처리

백엔드와 최종 결정할 것:

- 목록 조회 endpoint
- 세션 상세 결과 조회 endpoint
- 목록 response 필드: `sessionId`, `questionId`, `questionText`, `completedAt`, Attempt 상태
- 상세 response 필드: 질문, 1차 결과, 1차 피드백, 2차 결과, comparison

후보 예시: `GET /api/sessions`, `GET /api/sessions/{sessionId}`

endpoint 이름은 임의로 확정하지 않습니다.

우선순위: P1
상태: 미정

## 13. 개별 연습 기록 삭제 API

현재 상태:

연습 기록 화면에서 각 질문 옆에 `[삭제]` 기능이 있습니다. 삭제 대상 정책은 기존 SDD에서 확정되어 있습니다.

프론트에서 필요한 것:

삭제 확인 후 특정 세션을 삭제하고, Backend의 실제 성공 응답을 받은 뒤에만 해당 기록을 목록에서 제거해야 합니다.

백엔드와 최종 결정할 것:

- 삭제 endpoint
- 삭제 성공 response
- 일부 리소스 삭제 실패 처리
- idempotent 삭제 여부

후보 예시: `DELETE /api/sessions/{sessionId}`

삭제 대상은 원본 녹음, TTS 음성, 전사문, 분석 결과, 피드백, 비교 결과, 세션 기록이며 기존 SDD 정책을 그대로 따릅니다.

우선순위: P1
상태: 미정

## 14. 전체 삭제 API

현재 상태:

연습 기록 화면에는 현재 사용자의 모든 연습 세션을 삭제하는 `[전체 삭제]` 기능이 있습니다.

프론트에서 필요한 것:

전체 삭제 확인 후 성공 여부를 확인하고, 성공한 경우에만 목록을 빈 상태로 변경해야 합니다. 일부 실패 시 목록을 임의로 비우지 않습니다.

백엔드와 최종 결정할 것:

- 전체 삭제 endpoint
- 인증/세션 기준
- 일부 삭제 실패 시 response
- transaction 또는 재시도 방식

삭제 대상은 기존 SDD 정책을 그대로 준수합니다.

우선순위: P1
상태: 미정

## 15. 24시간 자동 삭제 구현 위치

현재 상태:

사용자가 직접 삭제하지 않은 데이터도 생성 후 최대 24시간 뒤 자동 삭제해야 한다는 정책은 확정되어 있습니다.

프론트에서 필요한 것:

보관 만료 정책을 별도로 계산해 삭제하지 않고, Backend가 제공하는 기록 목록과 상세 결과를 기준으로 표시합니다.

백엔드와 최종 결정할 것:

- Supabase TTL/cron, scheduled cleanup worker, DB scheduled job 등 구현 계층
- 원본 녹음, TTS 음성, transcript, analysis, feedback, comparison, session이 누락 없이 함께 삭제되는지
- cleanup 실패 감지와 재처리 방식

우선순위: P1
상태: 구현 방식 확인 필요

## 16. Storage 업로드 구조

현재 상태:

기존 SDD에는 Storage bucket 비공개, browser에 service role key 노출 금지, 업로드·재생 시 제한된 권한만 발급한다는 정책이 확정되어 있습니다.

프론트에서 필요한 것:

정해진 방식으로 음성을 업로드하고, 재생이 필요한 경우 제한된 URL 또는 응답을 사용해야 합니다.

백엔드와 최종 결정할 것:

- 브라우저가 signed upload URL을 받는지
- API server가 직접 upload를 받는지
- Storage path 규칙
- `sessionId`/`sourceId`와 file path 연결 방식
- signed URL 만료 시간

우선순위: P1
상태: 미정

## 17. TTS 파일 전달/저장 API

현재 상태:

TTS 모델 자체의 선정·학습·음색은 이 문서의 대상이 아닙니다. 다만 프론트가 TTS 음성을 재생하려면 Backend/API 전달 계약이 필요합니다.

프론트에서 필요한 것:

피드백 반영 음성을 재생하고, 재생 실패 시 오류 상태를 표시할 수 있어야 합니다.

백엔드와 최종 결정할 것:

- TTS 결과를 URL로 반환할지
- Blob/File stream으로 반환할지
- Storage에 임시 저장할지
- 재생용 signed URL을 사용할지
- 기존 SDD 최대 24시간 삭제 정책을 어떻게 연결할지

TTS 입력 정책 자체는 별도 TTS/기획 협의사항으로 남깁니다.

우선순위: P2
상태: 미정

## 18. 인증/비로그인 사용자 식별 방식

현재 상태:

헤더에는 `로그인 / 회원가입`이 있으나 실제 인증 범위가 별도 논의 중일 수 있습니다.

프론트에서 필요한 것:

연습 세션 생성, 기록 조회, 상세 조회, 개별·전체 삭제 시 사용자 소유권을 유지해야 합니다.

백엔드와 최종 결정할 것:

- 비로그인 사용자도 session을 생성할 수 있는지
- 비로그인 session 식별 방식
- 로그인 사용자와 session 연결 방식
- 기록 조회·삭제 시 사용자 소유권 검증 방식

기존 SDD/Spec에 이미 확정된 정책이 있다면 그 정책을 그대로 적용하고 미정 항목으로 만들지 않습니다.

우선순위: P1
상태: 기존 문서 확인 필요

## 19. 로그 정책

현재 상태:

운영 로그에는 음성 원문, 전사문, 민감정보, 실제 파일 경로를 남기지 않는 정책이 확정되어 있습니다.

프론트에서 필요한 것:

오류 응답의 `jobId`, `sourceId`, error code 등 비민감 식별자를 이용해 사용자 오류 상태를 안내할 수 있어야 합니다.

백엔드와 최종 결정할 것:

- 허용 로그 필드
- 처리 상태와 processing time 기록 방식
- error code와 model version 기록 방식
- 민감 데이터 없이 재현 가능한 디버깅 로그 구조

허용 후보: `jobId`, `sourceId`, 처리 상태, processing time, error code, model version

우선순위: P2
상태: 구현 방식 확인 필요

## Backend 문서에서 제외할 내용

Backend가 직접 결정하는 API 연결 계약이 아닌 다음 내용은 이 문서에서 세부 설계하지 않습니다.

- 최종 STT 모델 선정
- STT fine-tuning 데이터셋
- 부산 사투리 모델 학습 방식
- filler 모델 정확도
- TTS voice 선정
- TTS 모델 학습 방식
- 음색
- TTS 화자 선정
- UI 디자인
- Figma 구성

단, Frontend와 연결되는 request/response/API 계약은 포함할 수 있습니다.

# Backend 우선 확인 항목

회의나 메시지에서 먼저 확인할 항목만 정리합니다.

## P0

1. 프론트가 호출할 분석 HTTP API를 어떤 형태로 만들 예정인가?
2. 음성 업로드는 어떤 방식으로 받을 것인가?
3. 동기 응답인가, `jobId` + polling 방식인가?
4. `sessionId` / `sourceId` / `attemptNo`는 누가 생성하고 저장하는가?

## P1

5. 최종 analysis response schema는 무엇인가?
6. 공통 error response와 error code는 무엇인가?
7. 연습 기록 목록/상세 조회 API는 무엇인가?
8. 개별 삭제/전체 삭제 API는 무엇인가?
9. 최대 24시간 자동 삭제는 어떤 방식으로 구현하는가?
10. Storage signed URL/업로드 방식은 무엇인가?

## P2

11. 1차/2차 comparison을 Backend에서 계산해서 줄 것인가?
12. TTS 음성은 Frontend에 어떤 방식(URL/Blob)으로 전달할 것인가?

## 확정 정책과 기술 계약의 구분

다음은 기존 SDD에서 이미 확정된 정책이며, 새 합의 항목으로 만들지 않습니다.

- Storage 비공개
- service role key 브라우저 노출 금지
- 사용자 삭제 시 관련 세션 데이터 삭제
- 생성 후 최대 24시간 자동 삭제
- 사용자 음성·전사문 추가 학습 사용 금지
- Voice Cloning 금지
- 공개 저장소에 사용자 데이터 저장 금지
- 운영 로그에 원문·전사문·민감정보·파일 경로 기록 금지

이 문서에서 협의하는 내용은 위 정책을 실제 서비스에 구현하기 위한 API, 데이터 구조, 처리 방식입니다.
