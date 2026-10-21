# 기능 Spec — 분석 결과 코치 피드백 TTS

## Why

- **페르소나**: 자신의 녹음 결과를 확인하고 다음 연습에서 바꿀 점을 듣고 싶은 로그인 사용자
- **상황**: STT·VAD 분석과 분석 LLM이 전달 방식에 맞는 짧은 피드백을 만든 뒤, 결과 화면과 24시간 연습 기록에서 텍스트와 음성을 함께 확인한다.
- **문제**:
  1. 고정 템플릿만으로는 분석 LLM이 만든 구체적인 피드백 문장을 음성으로 들려줄 수 없다.
  2. 완성 WAV를 기다리면 결과 화면에서 첫 재생까지의 체감 대기 시간이 길어진다.
  3. 사용자 답변·원문 전사문·LLM 프롬프트를 클라이언트가 TTS로 다시 보내거나 오래 보관하면 개인정보 경계가 흐려진다.
- **측정 지표**: 첫 `audio` 이벤트 수신 지연시간, 생성·재생 성공률, 정상 완료 WAV의 24시간 삭제 성공률, 연습 기록의 텍스트·재생 버튼 표시 성공률

## Goal

- **해결 목표**: 인증된 사용자가 자신의 분석 결과에서 승인된 1~200자 코치 피드백을 스트리밍으로 듣고, 같은 피드백 텍스트와 정상 완료 WAV를 연습 기록에서 최대 24시간 다시 확인한다.
- **성공 기준**:
  - 준비 상태인 GPU Worker에서 일반 길이 코치 피드백 요청의 95% 이상이 5초 이내 첫 `audio` 이벤트를 수신한다.
  - 유효 요청의 생성 성공률과 재생 성공률은 각각 95% 이상이다.
  - 정상 완료된 WAV는 24 kHz·mono·PCM_16이며, 사람 청취에서 자연스러움·잡음·마지막 음절 완결을 수용한다.
  - 만료 시각이 지나면 생성 WAV와 TTS 메타데이터가 삭제되고 재생 요청은 `404 Not Found`를 반환한다.
- **Out of Scope**: 사용자 답변·원문 전사문을 직접 TTS 입력으로 사용, 사용자 음성 복제·추가 학습, LLM 프롬프트·원문 전사문·사용자 음성의 TTS 저장, 기본 질문 또는 고정 템플릿 코치 WAV의 런타임 재합성, 공개 Storage, 모델 가중치·생성 WAV의 Git 저장, 24시간 이후 연습 기록 보관

## What

### Happy Path

1. 인증된 사용자의 분석 Job이 완료되고, 분석 LLM이 결과 화면에 표시할 1~200자 `coachTtsText`를 만든다.
2. 분석 결과는 피드백별로 `coachAudioMode`를 하나만 선택한다. 수용된 고정 템플릿이면 `preset`, 분석 LLM 기반 피드백이면 `generated`, 음성을 만들 수 없으면 `text`다.
3. 결과 화면은 텍스트 피드백을 먼저 표시한다. `generated`인 경우 Bearer JWT와 `analysisResultId`만 사용해 `POST /api/analysis-results/{analysisResultId}/coach-tts/stream`을 호출한다.
4. 서버는 JWT의 사용자와 분석 결과 소유자가 같고, 분석 결과가 만료 전이며, 저장된 `coachTtsText`가 1~200자인지 확인한다. 클라이언트가 보낸 피드백 문장으로는 합성하지 않는다.
5. 서버는 승인된 `candidate_01_coach` 모델에 내부 전용 접미사 `//`를 한 번만 붙인 피드백을 전달하고, `start` 뒤 24 kHz·mono·PCM16 `audio` 조각을 순서대로 전송한다.
6. 프런트엔드는 Web Audio API로 첫 조각부터 재생한다. 서버는 조각을 메모리에만 누적하며, 실제 발화 후 -35 dB 이하 0.5초 연속 구간에서 생성기를 닫아 긴 뒤쪽 무음·잡음을 막는다.
7. 정상 종료 또는 종료 게이트로 끝난 경우에만 서버는 전체 WAV를 사용자 전용 비공개 Storage에 쓰고, `complete` 이벤트에 상대 `audioUrl`, `audioId`, 길이와 만료 시각을 넣는다.
8. 연습 기록은 만료 전 `coachTtsText`와 재생 버튼을 함께 표시한다. 재생 버튼은 소유자 전용 WAV 조회 API를 사용하며, 기록 조회만으로 모델을 다시 실행하지 않는다.
9. 분석 결과 생성 시각부터 24시간이 지나면 cleanup 작업이 WAV와 TTS 메타데이터를 삭제한다.

### Edge Case

| # | 상황 | 처리 방식 |
|---|---|---|
| EC-01 | JWT 없음·만료 또는 다른 사용자의 `analysisResultId` | `401` 또는 `404`, 모델 호출·파일 조회·메타데이터 노출 없음 |
| EC-02 | 분석 결과가 없거나 24시간 만료 | `404`, 모델 호출·파일 생성 없음 |
| EC-03 | `coachTtsText` 없음·공백만·200자 초과 | 실시간 TTS를 호출하지 않고 텍스트 피드백만 표시 |
| EC-04 | 승인 모델 준비 실패 | `503`, 공식 기본 화자·다른 모델·정적 템플릿으로 대체하지 않고 텍스트 피드백 유지 |
| EC-05 | 스트림 시작 후 모델 오류 또는 최대 생성 한도 종료 | `error` 이벤트 후 종료, 완성 WAV·TTS 메타데이터 없음 |
| EC-06 | 사용자가 중지하거나 연결이 끊김 | 생성기를 닫고 부분 PCM·부분 WAV·TTS 메타데이터를 저장하지 않음. 기존 텍스트 피드백은 유지 |
| EC-07 | Storage 또는 DB 기록 실패 | `complete`를 보내지 않고 `error` 이벤트 전송, 업로드된 객체는 삭제 시도, 텍스트 피드백만 유지 |
| EC-08 | WAV 조회 시 만료·소유자 불일치·누락 | `404`, 객체 경로·서명 URL·다른 사용자 존재 여부를 노출하지 않음 |

## How

### API 계약

```http
POST /api/analysis-results/{analysisResultId}/coach-tts/stream
Authorization: Bearer {accessToken}
Accept: application/x-ndjson
```

- 요청 바디에는 `coachTtsText`, 사용자 답변, 전사문, LLM 프롬프트를 넣지 않는다.
- 정상 응답의 Content-Type은 `application/x-ndjson; charset=utf-8`이다.
- 이벤트 순서는 `start` → `audio` 1개 이상 → `complete` 또는 `error`다. `complete`와 `error` 뒤에는 이벤트를 보내지 않는다.

`start` 이벤트:

```json
{
  "type": "start",
  "format": "pcm_s16le",
  "sampleRate": 24000,
  "channels": 1
}
```

`audio` 이벤트:

```json
{
  "type": "audio",
  "sequence": 0,
  "pcmBase64": "..."
}
```

`complete` 이벤트:

```json
{
  "type": "complete",
  "audioId": "opaque-id",
  "audioUrl": "/api/audio/coach/{audioId}",
  "durationMs": 4200,
  "expiresAt": "2026-08-25T15:22:10+09:00"
}
```

`error` 이벤트:

```json
{
  "type": "error",
  "code": "COACH_TTS_GENERATION_FAILED",
  "message": "코치 음성을 만들지 못했습니다. 텍스트 피드백을 확인해 주세요."
}
```

```http
GET /api/audio/coach/{audioId}
Authorization: Bearer {accessToken}
```

- 성공 시 현재 소유자에게만 완성 WAV를 `audio/wav`로 반환한다.
- 만료·누락·소유자 불일치는 모두 `404 Not Found`로 처리한다.

### 모델·재생·보관 규칙

- 분석 LLM은 TTS 입력 후보로 `coachTtsText`만 만들며, 앞뒤 공백 제거 후 1~200자인지 서버에서 다시 검증한다.
- 승인된 `candidate_01_coach`만 사용한다. 서버는 시작 시 모델을 한 번 로드하고 사용자 데이터와 무관한 짧은 워밍업을 수행한다. 공식 기본 화자·자동 화자 대체는 허용하지 않는다.
- 모델 입력에만 `coachTtsText + "//"`를 사용한다. 접미사는 응답·DB·로그·파일명·연습 기록·학습 데이터에 넣지 않는다.
- 모델은 결정적 설정(`do_sample=False`)과 검증된 CUDA Graph 경로로 합성한다. 생성 조각은 즉시 PCM16으로 전송하고, 서버 메모리에만 누적한다.
- 정상 종료 또는 종료 게이트로 끝난 조각만 24 kHz·mono·PCM_16 WAV로 저장한다. 최대 생성 한도만으로 끝난 결과는 정상 완료가 아니다.
- `coachTtsText`, `audioId`, 소유자 ID, 생성·만료 시각만 최소 TTS 메타데이터로 보관한다. 원문 사용자 답변·전사문·LLM 프롬프트·모델 경로·WAV bytes는 로그나 Git에 넣지 않는다.
- WAV와 TTS 메타데이터의 `expiresAt`은 분석 결과 생성 시각부터 정확히 24시간이다. 사용자가 연습 기록을 삭제하면 만료 전이라도 관련 WAV·TTS 메타데이터를 함께 삭제한다.
- 기본 질문과 고정 템플릿 코치 WAV는 [TTS 사전 생성 피드백 템플릿 Spec](tts-사전생성-피드백템플릿.md)을 계속 따른다. `generated`가 실패해도 의미가 다른 정적 WAV로 대체하지 않는다.

### 출시 전 검수

- GPU Worker에서 개인정보가 없는 고정 코치 피드백 10개를 스트리밍으로 생성한다. WAV·상세 측정값은 Git에서 제외된 로컬 결과 폴더에만 둔다.
- 각 결과의 첫 `audio` 이벤트 수신 시간, 전체 생성 시간, 생성 성공 여부, 음성 길이, RTF, peak GPU memory, 종료 방식, WAV 형식, 사람 청취 검수 상태를 기록한다. 피드백 원문·사용자 ID·모델 경로는 결과 기록에 넣지 않는다.
- 사람이 잡음, 마지막 음절 완결, 자연스러움을 확인해 `accepted` 또는 `rejected`로 남긴다. 성공 기준 미달 시 앱 연결 후보로 주장하지 않는다.

## AC (Given-When-Then)

### AC-01 · 인증된 분석 결과만 스트리밍

- **Given**: 로그인 사용자가 만료 전 자신의 `analysisResultId`와 1~200자 `coachTtsText`를 가짐
- **When**: `POST /api/analysis-results/{analysisResultId}/coach-tts/stream`을 호출함
- **Then**: 서버는 `start` 뒤 연속된 PCM16 `audio` 이벤트를 하나 이상 전송함

### AC-02 · 클라이언트 원문 분리

- **Given**: 분석 결과 화면에 코치 피드백 텍스트가 표시됨
- **When**: Frontend가 코치 TTS를 요청함
- **Then**: 요청에는 Bearer JWT와 `analysisResultId`만 포함하고, 사용자 답변·원문 전사문·LLM 프롬프트·피드백 원문을 보내지 않음

### AC-03 · 내부 접미사와 모델 고정

- **Given**: 서버가 유효한 저장 피드백을 합성함
- **When**: 모델 입력을 준비함
- **Then**: `candidate_01_coach`에만 공백 없는 `//` 접미사를 정확히 한 번 붙여 전달하고, 외부 응답·DB·로그에는 접미사를 넣지 않음

### AC-04 · 첫 음성 지연시간과 형식

- **Given**: GPU Worker가 준비 상태이고 개인정보가 없는 코치 피드백 10개 검수 세트가 있음
- **When**: 각 항목을 스트리밍 요청함
- **Then**: 95% 이상에서 첫 `audio` 이벤트를 5초 이내 수신하고, 정상 WAV는 24 kHz·mono·PCM_16임

### AC-05 · 정상 완료만 보관

- **Given**: 음성 조각이 하나 이상 전송됨
- **When**: 정상 종료 또는 종료 게이트로 생성이 끝남
- **Then**: 비공개 Storage에 완성 WAV와 최소 TTS 메타데이터를 쓰고 `complete`에 만료 시각을 전송함

### AC-06 · 취소·실패 시 부분 자산 없음

- **Given**: 스트림 중 사용자가 중지하거나 모델·Storage·DB 오류가 발생함
- **When**: 서버가 생성 중단을 처리함
- **Then**: `complete`를 보내지 않고 부분 WAV·TTS 메타데이터를 남기지 않으며, 화면은 텍스트 피드백을 유지함

### AC-07 · 연습 기록 재생

- **Given**: 만료 전 정상 완료된 코치 WAV가 있는 사용자의 연습 기록
- **When**: 사용자가 기록 상세를 열고 재생 버튼을 누름
- **Then**: 피드백 텍스트와 재생 버튼을 함께 표시하고, 소유자 전용 `audio/wav`를 재생하며 모델을 다시 실행하지 않음

### AC-08 · 만료·삭제

- **Given**: 분석 결과 생성 뒤 24시간이 지났거나 사용자가 연습 기록을 삭제함
- **When**: cleanup 또는 삭제 처리가 완료됨
- **Then**: 관련 WAV와 TTS 메타데이터를 삭제하고 이후 음성 조회는 `404 Not Found`를 반환함
