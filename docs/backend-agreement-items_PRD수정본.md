# 말해봄 Backend 협의 필요사항 - PRD 정렬 수정본

이 문서는 기존 `docs/backend-agreement-items.md`를 참고해 PRD와 현재 Backend 구현 상태의 차이를 정리한 수정본이다. 기존 문서는 수정하지 않는다.

## 1. 현재 Backend 상태

### 존재

- `FasterWhisperTranscriber` Python 서비스
- `transcribe_audio.py` CLI
- 로컬 개발용 FastAPI STT Job API
- 개발용 STT Job 생성·상태 조회 흐름

### 제품용 Frontend 계약으로 아직 연결되지 않음

- 로그인 사용자 검증
- `questionId`
- `questionType`
- `customQuestionText`
- `attemptNo`
- `sessionId`
- 비공개 Storage 업로드
- 전달력 분석 통합 응답
- 답변 구성 점검
- 음량·억양 참고 피드백 상태
- 사전 생성 코치 WAV 자산 연결
- 연습 기록 목록·상세 조회
- 개별 삭제·전체 삭제
- 최대 24시간 자동 삭제 연동

따라서 `개발용 API 존재`와 `제품용 Frontend 계약 미완성`을 구분한다. 개발용 FastAPI STT Job API를 제품용 통합 분석 API로 가정하지 않는다.

## 2. 제품용 분석 요청 계약

분석 요청 전 로그인 사용자 세션을 확인한다.

- 비로그인: 음성 저장 금지, 분석 Job 생성 금지
- 로그인: 비공개 저장, 분석 Job 생성, 분석 진행

요청 필드 후보:

- `sessionId`
- `sourceId`
- `questionType`: `preset` | `custom`
- `questionId` (`preset`일 때 필요)
- `customQuestionText` (`custom`일 때 필요)
- `attemptNo`
- `audio`

Backend와 최종 결정할 것:

- 인증 방식
- 인증 실패 HTTP status와 error code
- 실제 필드명과 생성 주체
- `preset`/`custom`별 필수 필드 검증
- `customQuestionText` 공백 제외 1~200자 검증

## 3. 개발용 Job과 제품용 Job 상태

현재 로컬 FastAPI STT Job API의 실제 endpoint와 status enum을 제품 계약에 그대로 복사하지 않는다. 저장소에서 확인 가능한 제품용 통합 status enum은 없으므로 실제 개발용 enum은 구현 문서와 Backend 담당자 확인이 필요하다.

Backend와 최종 결정할 것:

- 개발용 API의 실제 status enum
- 제품용 API에서 추가할 상태가 있는지
- `추가 합의 필요` 상태를 제품 계약에 어떻게 표현할지
- polling 여부·주기·timeout

## 4. 결과 타입별 응답 계약

제품용 response는 `questionType`에 따라 프론트가 표시 범위를 구분할 수 있어야 한다.

### 공통

- `transcript`
- `speakingRate`
- `longSilence`
- `repeatedExpressions`
- `feedback` 최대 2개

### preset 추가

- `answerStructureCheck`
- 세부 항목과 판정 기준은 기존 PRD/Spec 기준 적용 필요

### custom

- 전달 방식 분석만 제공
- `answerStructureCheck`는 표시하지 않음

### 음량·억양 참고 피드백

측정 근거가 있을 때만 제공한다.

```text
ProsodyReferenceState
- unavailable
- available
```

근거가 없으면 임의로 생성하지 않으며 핵심 분석 지표가 아닌 참고 피드백으로 전달한다.

## 5. 인증 계약

Backend와 최종 결정할 것:

- 인증 방식
- 인증 실패 HTTP status
- 인증 실패 error code
- Frontend 로그인 안내와 연결 방식

현재 제품용 인증 구현이 확인되지 않았으므로 `401`/`403` 중 하나를 확정하지 않는다.

## 6. 코치 음성 계약

고정 템플릿은 검수 완료된 사전 생성 코치 WAV 자산을 프론트에 제공한다. 분석 LLM이 만든 승인 피드백은 [분석 결과 코치 피드백 TTS Spec](specs/coach-feedback-tts.md)의 별도 런타임 endpoint로만 스트리밍 합성한다.

필드 후보:

- `coachAudioAvailable`
- `coachAudioUrl`
- `coachAssetId`
- `reviewStatus`
- `coachAudioMode`
- `coachTtsText` (최대 200자, 기록 화면 표시용)
- `coachAudioExpiresAt`

정확한 필드명은 미정이다. 고정 템플릿 자산이 없거나 미검수이고 생성 코치 TTS도 완료되지 않으면 프론트가 텍스트 피드백만 표시할 수 있어야 한다. Frontend는 코치 피드백 원문을 TTS 요청 바디로 보내지 않고 `analysisResultId`만 보낸다.

## 7. 연습 기록 계약

확정 정책:

- 로그인 사용자 기준 저장·조회
- 최대 24시간 보관
- 사용자 직접 삭제 가능
- 생성 후 최대 24시간 뒤 자동 삭제
- 삭제 시 관련 세션 데이터 삭제
- 비공개 Storage

상세 제품 계약의 기준 문서는 [Supabase 연습 기록 조회 Spec](specs/supabase-practice-history.md)이다.

- `GET /practice-records`, `GET /practice-records/{practice_session_id}`, `DELETE /practice-records/{practice_session_id}`, `DELETE /practice-records`를 사용한다.
- 요청자의 Bearer JWT와 기존 RLS 범위로 소유권을 검증한다.
- 원본 음성 Storage 객체를 먼저 삭제하고, 성공한 뒤 관련 DB 행을 삭제한다. Storage 삭제 실패 시 DB 행은 유지해 재시도한다.
- 기존 만료 cleanup을 그대로 사용하며, 브라우저 `sessionStorage`를 원본 저장소로 사용하지 않는다.

## 8. 삭제 범위 계약

기존 SDD 정책의 삭제 범위를 그대로 사용한다.

사용자 세션 삭제 시 다음 연결 데이터를 삭제한다.

- 원본 녹음
- 관련 코치 WAV 세션 연결 데이터
- 전사문
- 분석 결과
- 피드백
- 비교 결과
- 세션 기록

연습 기록의 endpoint, 성공·실패 response, 부분 삭제 재시도, idempotent 처리, Storage/DB 삭제 순서는 [Supabase 연습 기록 조회 Spec](specs/supabase-practice-history.md)으로 확정한다.

## 9. 오류 계약

다음 범주마다 Backend error code, HTTP status, Frontend UX 연결을 결정한다. 구현이 확인되지 않은 값은 미정/합의 필요로 둔다.

| 오류 범주 | Backend code | HTTP status | Frontend UX |
|---|---|---|---|
| 인증 실패 | 미정/합의 필요 | 미정/합의 필요 | 로그인 안내, Job 생성 안 함 |
| 직접 질문 검증 실패 | 미정/합의 필요 | 미정/합의 필요 | 입력 오류 표시 |
| 음성 파일 검증 실패 | 미정/합의 필요 | 미정/합의 필요 | 파일 형식·길이·크기 안내 |
| STT 실패 | 미정/합의 필요 | 미정/합의 필요 | STT 오류 및 재녹음/재시도 |
| 분석 실패 | 미정/합의 필요 | 미정/합의 필요 | 분석 재시도 또는 재녹음 |
| Job timeout | 미정/합의 필요 | 미정/합의 필요 | timeout 안내 및 재시도 |
| 기록 조회 실패 | 연습 기록 Spec 참조 | `401` 또는 `503` | 목록 재시도 또는 로그인 안내 |
| 개별 삭제 실패 | 연습 기록 Spec 참조 | `404` 또는 `503` | 기록 유지, 삭제 재시도 |
| 전체 삭제 실패 | 연습 기록 Spec 참조 | `503` | 목록 임의 초기화 금지, 재시도 |

## 10. 우선 협의 항목

### P0

1. 개발용 FastAPI STT Job API의 실제 endpoint와 status enum
2. 제품용 분석 API endpoint와 인증 확인 시점
3. `preset`/`custom` request 필수 필드와 직접 질문 검증
4. 비로그인 사용자의 음성 저장·Job 생성을 차단하는 방식

### P1

5. 제품용 분석 결과 response schema
6. 비공개 Storage 업로드와 세션 연결
7. 24시간 자동 삭제 구현 위치
8. 정적 코치 WAV 자산 availability·review status 전달 방식

### P2

10. 1차/2차 comparison 계산 주체와 response 구조
11. 음량·억양 참고 피드백의 측정 근거 전달 방식

## 11. 범위 제외

- STT 최종 모델 선정·학습·fine-tuning
- TTS 모델·음색·화자 선정
- 사용자 음성 복제·학습
- 사용자 답변을 이용한 런타임 TTS 합성
- UI 디자인과 Figma 구성
