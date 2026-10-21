# TTS 현재 상태

> 2026-09-17 정적 audit 정정: 실시간 질문·코치 TTS API와 frontend 재생 경로가 현재 코드에 존재한다. 아래 미구현 설명은 이전 시점이며, 개인 Storage/청취 검증 진술은 이번에 재검증하지 않았다. 현재 근거와 인수 제한은 [음성 인수 기록](experiments/2026-09-17_voice-asset-intake.md)을 따른다.


## 앱 연결 원칙

- 기본 질문은 검수된 사전 생성 WAV를 재생하고 없으면 오류 상태를 표시한다. 고정 템플릿 코치 피드백은 검수되지 않은 자산을 텍스트로 폴백한다. 직접 질문과 결과 화면의 말하기 예시는 별도 GPU Worker 스트리밍 경로가 화면에 연결됐다. 분석 LLM 모델 선정과 코치 음성의 24시간 Storage 기록은 [별도 Spec](specs/coach-feedback-tts.md)의 후속 범위다.
- 사용자 원문 음성·전사문·개인별 수치를 TTS 입력, Voice Cloning 또는 추가 학습 데이터로 사용하지 않는다.
- WAV·모델 가중치·참조 음성·학습 데이터·실제 접근 URL은 저장소에 넣지 않는다.

## 현재 자산 상태

| 역할 | 화자 | 상태 |
| --- | --- | --- |
| 질문자 | `candidate_04_questioner` | 기본 질문 10개가 개인 Supabase의 private Storage에서 업로드·API 재생 검증 완료. 팀 Supabase 반입은 별도 대기 |
| 코치 | `candidate_03_coach` | `LOW_VOLUME` 문구 2개가 로컬 청취 수용, 비공개 Storage 업로드 대기 |
| 코치 템플릿 초안 | `candidate_01_coach` | 문제 코드 5종의 고정 문구 90개가 `draft`, 검수·업로드 전 |

로컬 검수 코치 발화 문구는 다음 두 개다.

1. `coach-low-volume-01`: 문장 끝까지 일정한 목소리로 전달해 보세요. 다음 답변에서도 이 리듬을 이어 가 보세요.
2. `coach-low-volume-02`: 핵심 문장은 평소보다 또렷하게 전달해 보세요. 다음 답변에서도 이 리듬을 이어 가 보세요.

두 항목은 `tts_asset_manifest.json`에서 `pending_private_upload`와 `audioAssetId: null`을 유지한다. 별도의 `tts_template_catalog.json`에는 `candidate_01_coach` 고정 문구 90개가 모두 `draft`로 있다. 따라서 현재 코치 선택 결과는 텍스트이며, 아직 앱에서 재생 가능한 코치 자산은 없다.

## 모델 범위와 제한

- 위 코치 후보는 로컬에서 Qwen3-TTS 1.7B Base와 승인된 `candidate_03` 참조 음성을 사용해 사전 생성·청취 검수한 결과다. 새 모델 가중치나 새 checkpoint를 이 저장소에 배포한 것은 아니다.
- 다른 문제 코드 `SPEED_FAST`, `LONG_SILENCE`, `FILLER_REPEAT`, `TERMINAL_INTONATION`에는 수용된 WAV가 없으므로 텍스트 폴백을 유지한다.
- 질문자용 기본 템플릿 10개는 개인 Supabase에서 비공개 Storage 연결과 일반 API 재생을 검증했다. 팀 Supabase에는 아직 반입하지 않았다.

## 다음 연결 전 조건

1. 팀이 음성 사용 권한과 보관 정책을 확인한 뒤, 동일한 10개 수용 WAV를 팀 Supabase의 private Storage에 업로드한다.
2. 실제 저장 객체와 정확한 발화 문구를 대조하고 수동 청취 검수를 다시 확인한다.
3. 현재 카탈로그의 불투명 `audioAssetId`, `qcStatus: accepted`, `isPrimary: true`는 개인 테스트에서 검증한 10개 자산을 가리킨다. 팀 배포 전에는 같은 식별자로 업로드가 모두 성공했는지 확인한다.
4. 팀 환경에서 앱의 자산 해석기가 권한 있는 비공개 접근만 제공하는지, 실패 시 질문 텍스트만 표시하는지 통합 테스트한다.

자세한 전달 계약은 [TTS 자산 인수인계](tts-asset-handoff.md)를 참고한다.
