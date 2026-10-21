# Frontend ↔ Analysis API 계약 초안

이 문서는 현재 구현 완료된 API 설명서가 아니라, PRD 기준으로 Frontend와 Backend가 맞춰야 할 제품용 분석 API 계약 초안이다. 로컬 개발용 FastAPI STT Job API와 제품용 통합 API를 동일한 것으로 가정하지 않는다.

## Why

- **페르소나**: 한국어 면접 답변을 연습하는 취업준비생
- **상황**: 기본 질문 또는 직접 질문에 5~60초 답변한 뒤 전달 방식과 전후 변화를 확인하려 함
- **문제**: 현재 Frontend 와이어프레임과 로컬 STT 처리 사이에 인증, 질문 타입, Attempt, 결과, 저장·삭제 계약이 연결되어 있지 않음
- **측정 지표**: 제품용 분석 요청의 계약 누락 0건, 비로그인 음성·Job 생성 0건, 성공 분석 결과에서 필수 결과 필드 누락 0건

## Goal

- **해결 목표**: 로그인 사용자의 유효한 녹음만 제품용 분석 Job으로 연결하고, Frontend가 상태·결과·오류·기록을 일관되게 표시할 수 있는 계약을 확정한다.
- **성공 기준**: request, job status, result, error, history, deletion 계약이 각각 필드 후보와 미정 사항을 구분해 문서화됨
- **성공 기준**: `preset`과 `custom` 결과 표시 범위가 구분됨
- **성공 기준**: 고정 템플릿 코치 WAV가 없거나 분석 LLM 기반 코치 TTS가 실패할 때 텍스트 피드백으로 폴백함
- **Out of Scope**: 답변 정답·품질·합격 가능성 판정, 사용자 음성 복제·학습, 사용자 답변·원문 전사문을 직접 입력으로 한 런타임 TTS, 실시간 면접 보조, 자유 대화, 장기 추세 분석, 실제 API 구현

## What

### Happy Path

1. 사용자가 `preset` 질문을 선택하거나 유효한 `custom` 질문을 등록한다.
2. 사용자가 5~60초 답변을 녹음한다.
3. 녹음 완료 후 Frontend가 로그인 상태를 확인한다.
4. 비공개 저장·분석 Job 생성·분석 요청을 진행한다.
5. Frontend가 개발용 또는 합의된 제품용 Job 상태를 확인한다.
6. 성공 response의 전달력 분석과 최대 2개 피드백을 표시한다.
7. `preset`이면 답변 구성 점검을 추가 표시하고, `custom`이면 표시하지 않는다.
8. 각 피드백은 `preset`, `generated`, `text` 중 하나의 코치 음성 모드를 가진다. `preset`은 검수 완료 고정 템플릿 WAV를 재생하고, `generated`는 분석 LLM 기반 코치 TTS 스트림을 재생하며, 사용할 수 없으면 `text`로 표시한다.
9. 같은 질문으로 Attempt 2를 진행하고 1차/2차 결과를 비교한다.
10. 로그인 사용자는 기록 목록·상세를 조회하고 개별·전체 삭제를 수행할 수 있다.

### Edge Cases

| # | 상황 | 처리 방식 |
|---|---|---|
| EC-01 | 비로그인 상태에서 분석 요청 | 음성 저장·Job 생성 없이 로그인 안내 |
| EC-02 | 공백만 입력한 custom 질문 | `질문을 입력해 주세요.` 표시, 요청 차단 |
| EC-03 | custom 질문이 200자 초과 | `질문은 200자 이내로 입력해 주세요.` 표시, 요청 차단 |
| EC-04 | preset request에 questionId 누락 | Backend 검증 오류 후보, 요청 실패 UX 표시 |
| EC-05 | custom request에 질문 텍스트 누락 | Backend 검증 오류 후보, 요청 실패 UX 표시 |
| EC-06 | 음성 파일이 5초 미만 또는 60초 초과 | Frontend·Backend 검증 계약에 따라 요청 차단 또는 오류 표시 |
| EC-07 | STT/분석 실패 | 오류 code와 재시도 가능 여부에 따라 재시도 또는 재녹음 |
| EC-08 | Job timeout | timeout 오류와 재시도 UX 표시 |
| EC-09 | 고정 템플릿 WAV 누락·미검수, 또는 코치 TTS 실패·만료 | 텍스트 피드백을 유지하고 재생 버튼을 표시하지 않음 |
| EC-10 | 기록 삭제 실패 | 실제 성공 전 목록에서 제거하지 않음 |

## How

### 1. 인증 계약

로그인 사용자만 제품용 분석 요청을 생성할 수 있다.

- 인증 방식: `미정/합의 필요`
- 인증 실패 HTTP status: `미정/합의 필요` (401/403 중 임의 확정하지 않음)
- 인증 실패 code: `미정/합의 필요`
- Frontend UX: `분석 결과를 확인하려면 로그인이 필요해요.`와 `[로그인하기]`, 필요 시 `[회원가입]`
- 비로그인 상태에서는 audio upload, 음성 저장, 분석 Job 생성을 하지 않음

### 2. Question 계약

```text
questionType: preset | custom
```

`preset` 후보:

```text
questionId: string (required)
customQuestionText: null or omitted
```

`custom` 후보:

```text
customQuestionText: string (required, 공백 제외 1~200자)
questionId: null or omitted
```

정확한 최종 field name은 현재 Backend naming convention과 최종 API 계약 확인 후 확정한다.

### 3. 분석 Request

제품용 request 후보:

```http
POST <제품용 analysis endpoint - 미정>
Content-Type: multipart/form-data
Authorization: <인증 방식 - 미정>
```

```text
sessionId: string                 (후보)
sourceId: string                  (후보)
questionType: preset | custom     (필요)
questionId: string                (preset일 때 필요 후보)
customQuestionText: string        (custom일 때 필요 후보)
attemptNo: 1 | 2                  (필요 후보)
audio: Blob/File                  (필요 후보)
```

현재 확정되지 않은 항목:

- endpoint
- multipart field 이름
- `sessionId`·`sourceId` 생성 주체
- audio MIME type·파일 크기 제한
- `attemptNo` 저장 위치

### 4. Job 상태

P0 피드백 기준 로컬 개발용 FastAPI STT Job API와 개발용 Job 생성·상태 조회 흐름은 존재한다. 다만 이 저장소에서 제품용 endpoint와 실제 status enum을 확정할 수 있는 구현 문서는 확인되지 않았다.

따라서 현재 계약에는 상태 enum을 임의로 확정하지 않는다.

```text
개발용 실제 status enum: Backend 구현 문서/실행 API 확인 필요
제품용 추가 상태: 추가 합의 필요
```

제품용으로 polling이 필요하다면 다음도 합의한다.

- 상태 조회 endpoint
- polling 주기
- timeout 기준
- success/failed payload 포함 방식

### 5. 분석 Result

최소 결과 후보:

```text
transcript: string
speakingRate: number | null
longSilence: number | null
repeatedExpressions: number | null
feedback: array (최대 2개)
```

| 필드/영역 | 현재 구현 여부 | 제품용 필요 여부 | 최종명 |
|---|---|---|---|
| `transcript` | STT 내부 `text` 후보 | 필요 | normalize 여부 미정 |
| `speakingRate` | 제품 통합 응답 미확인 | 필요 | 미정 |
| `longSilence` | 제품 통합 응답 미확인 | 필요 | 미정 |
| `repeatedExpressions` | 제품 통합 응답 미확인 | 필요 | 미정 |
| `feedback` 최대 2개 | 제품 통합 응답 미확인 | 필요 | 미정 |
| `answerStructureCheck` | 제품 통합 응답 미확인 | preset만 필요 | 기존 PRD/Spec 기준 적용 필요 |
| volume/intonation reference | 측정 근거 상태 미확인 | 근거가 있을 때 선택 | `ProsodyReferenceState`와 필드명 미정 |

`custom` response에서는 `answerStructureCheck`를 Frontend가 표시하지 않는다.

### 6. Coach Audio 계약

코치 음성은 두 경로를 구분한다.

1. 고정 템플릿 피드백은 검수 완료된 사전 생성 WAV만 재생한다.
2. 분석 LLM이 만든 짧은 코치 피드백은 [분석 결과 코치 피드백 TTS Spec](coach-feedback-tts.md)의 인증·소유자 확인·24시간 보관 조건으로만 실시간 합성한다.

분석 결과 후보 데이터:

```text
feedback: array (최대 2개)
coachAudioMode: preset | generated | text
coachTtsAvailable: boolean          (후보)
coachTtsText: string | null         (최대 200자, 기록 화면 표시용)
coachAudioId: string | null         (불투명 식별자)
coachAudioUrl: string | null        (소유자 전용 상대 URL 후보)
coachAudioExpiresAt: ISO 8601 | null
reviewStatus: reviewed | ...        (고정 템플릿 자산의 실제 enum 미정)
```

각 피드백에는 하나의 `coachAudioMode`만 선택한다. Frontend는 LLM 피드백 원문을 요청 바디로 보내지 않고, 인증된 `analysisResultId`만 사용해 `generated` 코치 TTS를 요청한다. 고정 템플릿 자산이 없거나 코치 TTS가 시작·완료되지 않으면 `이번 피드백은 텍스트로 확인해 주세요.`를 표시한다.

### 7. Error 계약

각 오류의 code와 HTTP status는 실제 구현 확인 전까지 미정으로 둔다.

| 오류 범주 | Backend code | HTTP status | Frontend UX |
|---|---|---|---|
| 인증 실패 | 미정/합의 필요 | 미정/합의 필요 | 로그인 안내, Job 미생성 |
| custom 질문 검증 실패 | 미정/합의 필요 | 미정/합의 필요 | 입력 오류 표시 |
| 음성 파일 검증 실패 | 미정/합의 필요 | 미정/합의 필요 | 파일 길이·형식 안내 |
| STT 실패 | 미정/합의 필요 | 미정/합의 필요 | 재시도 또는 재녹음 |
| 분석 실패 | 미정/합의 필요 | 미정/합의 필요 | `[다시 분석하기]` 또는 재녹음 |
| Job timeout | 미정/합의 필요 | 미정/합의 필요 | timeout 안내·재시도 |
| 기록 조회 실패 | [연습 기록 Spec](supabase-practice-history.md) 참조 | `401` 또는 `503` | 목록 재시도 또는 로그인 안내 |
| 개별 삭제 실패 | [연습 기록 Spec](supabase-practice-history.md) 참조 | `404` 또는 `503` | 기존 목록 유지·재시도 |
| 전체 삭제 실패 | [연습 기록 Spec](supabase-practice-history.md) 참조 | `503` | 목록 임의 초기화 금지·재시도 |
| 코치 TTS 시작 실패 | 미정/합의 필요 | 미정/합의 필요 | 텍스트 피드백 유지, 재생 버튼 숨김 |
| 코치 TTS 중단·저장 실패 | 미정/합의 필요 | 미정/합의 필요 | 텍스트 피드백 유지, 완성 WAV 없음 |

### 8. 연습 기록 계약

상세 API·응답·삭제 순서의 기준 문서는 [Supabase 연습 기록 조회 Spec](supabase-practice-history.md)이다.

- `GET /practice-records`: 완료된 본인 세션 목록 조회
- `GET /practice-records/{practice_session_id}`: 본인 세션 상세 조회
- `DELETE /practice-records/{practice_session_id}`: 본인 세션 삭제
- `DELETE /practice-records`: 본인 완료 기록 전체 삭제

기존 SDD 정책:

- 생성 후 최대 24시간 보관
- 사용자 삭제 시 관련 데이터 삭제
- 비공개 Storage
- 브라우저 `sessionStorage`는 원본 저장소가 아님

### 9. 삭제 계약

사용자 세션 삭제 범위는 기존 SDD를 따른다.

- 원본 녹음
- 관련 코치 WAV 세션 연결 데이터
- 분석 LLM 기반 코치 피드백 텍스트와 생성 WAV 메타데이터
- 전사문
- 분석 결과
- 피드백
- 비교 결과
- 세션 기록

연습 기록의 Storage·DB 삭제 순서와 부분 실패 재시도는 [Supabase 연습 기록 조회 Spec](supabase-practice-history.md)을 따른다. 원본 음성 Storage 객체를 먼저 삭제하고, 모두 성공한 뒤 해당 세션의 DB 행을 삭제한다.

## AC

### AC-01 · 인증 없는 분석 요청 차단

- **Given**: 사용자가 로그인하지 않았고 녹음이 완료됨
- **When**: 사용자가 `[분석하기]`를 누름
- **Then**: 음성 저장과 분석 Job 생성을 하지 않고 로그인 안내를 표시함

### AC-02 · 유효한 preset request

- **Given**: 로그인 사용자, `questionType=preset`, `questionId`, `attemptNo`, 유효한 audio가 있음
- **When**: Frontend가 제품용 분석 API를 요청함
- **Then**: Backend 계약에 맞는 request가 전송되고 Job 상태 확인 단계로 이동함

### AC-03 · 유효한 custom request

- **Given**: 로그인 사용자, `questionType=custom`, 공백 제외 1~200자의 `customQuestionText`가 있음
- **When**: Frontend가 분석을 요청함
- **Then**: custom 질문 텍스트가 request에 포함되고 preset용 답변 구성 점검은 표시 대상에서 제외됨

### AC-04 · 잘못된 custom 질문 차단

- **Given**: custom 질문이 공백만 있거나 공백 제외 200자를 초과함
- **When**: 사용자가 등록함
- **Then**: 질문을 등록하지 않고 해당 안내 문구를 표시함

### AC-05 · preset 결과 표시

- **Given**: `questionType=preset` 분석이 성공함
- **When**: 결과 화면을 표시함
- **Then**: transcript, 전달 방식 지표, 최대 2개 feedback, 답변 구성 점검을 표시함

### AC-06 · custom 결과 표시

- **Given**: `questionType=custom` 분석이 성공함
- **When**: 결과 화면을 표시함
- **Then**: transcript, 전달 방식 지표, 최대 2개 feedback만 표시하고 답변 구성 점검은 표시하지 않음

### AC-07 · 코치 음성 폴백

- **Given**: 분석 결과에 검수 완료 고정 템플릿 WAV가 없고, 분석 LLM 기반 코치 TTS가 시작·완료되지 않음
- **When**: 결과 화면을 표시함
- **Then**: 텍스트 피드백을 표시하고 재생 버튼을 표시하지 않음

### AC-08 · 코치 TTS 요청 원문 분리

- **Given**: 로그인 사용자의 분석 결과에 최대 200자 코치 피드백 텍스트가 있음
- **When**: Frontend가 코치 TTS를 요청함
- **Then**: Bearer JWT와 `analysisResultId`만 전송하고, 사용자 답변·원문 전사문·LLM 프롬프트를 요청 바디나 로그에 넣지 않음

### AC-09 · 기록 삭제 성공 확인

- **Given**: 로그인 사용자가 기록 삭제를 확인함
- **When**: Backend가 삭제 성공을 확인함
- **Then**: 해당 기록만 목록에서 제거하고, 성공 전에는 목록을 임의로 변경하지 않음

### AC-10 · 24시간 정책

- **Given**: 세션이 생성된 지 24시간이 지남
- **When**: Backend cleanup이 실행됨
- **Then**: 관련 음성·코치 WAV 연결 데이터·전사문·분석·피드백·비교·세션 기록이 정책에 따라 삭제됨

## 미정 항목 요약

- 제품용 endpoint
- 실제 개발용 FastAPI status enum 확인
- 인증 방식과 401/403 여부
- request field 최종명
- response field 최종명
- 오류 code/status
- Storage signed/private URL 방식
- 코치 WAV `reviewStatus` enum
- 분석 결과에서 `coachTtsText`를 생성·검수하는 LLM 계약
- 기록·삭제 API 계약