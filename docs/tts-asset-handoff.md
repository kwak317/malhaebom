# TTS 자산 인수인계

## 목적

기본 질문과 고정 템플릿 코치 피드백은 동적 TTS가 아니라 수동 청취 검수된 사전 생성 WAV를 재생한다. 이 문서는 실제 음성 파일을 GitHub에 올리지 않고, 어떤 조건에서 정적 앱 재생 자산으로 전환할 수 있는지 정한다. 사용자가 직접 입력한 질문의 승인된 실시간 TTS와 분석 LLM 기반 코치 피드백의 실시간 TTS는 이 문서 범위 밖이며 각각 [사용자 입력 면접 질문 TTS Spec](specs/custom-question-tts.md), [분석 결과 코치 피드백 TTS Spec](specs/coach-feedback-tts.md)을 따른다.

## 현재 전달 대상

기본 질문자 `candidate_04_questioner`의 기본 질문 10개 WAV는 화면의 질문 1~10번과 실제 재생을 대조한 뒤, 개인 Supabase의 private Storage에 업로드해 일반 API 재생까지 검증했다. 카탈로그에는 수용된 상태와 불투명 `audioAssetId`만 기록한다. 이 검증은 팀 Supabase 반입 완료를 뜻하지 않는다.

현재 로컬 청취 수용 상태인 코치 후보는 `candidate_03_coach`의 아래 두 문구다.

| 템플릿 ID | 문제 코드 | 발화 문구 | 저장소 상태 |
| --- | --- | --- | --- |
| `coach-low-volume-01` | `LOW_VOLUME` | 문장 끝까지 일정한 목소리로 전달해 보세요. 다음 답변에서도 이 리듬을 이어 가 보세요. | 로컬 검수 수용, 비공개 업로드 대기 |
| `coach-low-volume-02` | `LOW_VOLUME` | 핵심 문장은 평소보다 또렷하게 전달해 보세요. 다음 답변에서도 이 리듬을 이어 가 보세요. | 로컬 검수 수용, 비공개 업로드 대기 |

현재 두 항목에는 `audioAssetId`가 없다. 따라서 `TtsAssetSelector`는 반드시 `mode: text`를 반환한다. 이 상태는 배포 준비 완료가 아니다.

## 배포 연결 절차

1. **권한 확인:** 음성·참조 음성·모델의 사용 및 비공개 보관 권한을 팀이 확인한다.
2. **비공개 업로드:** 승인된 기본 질문 WAV만 팀의 비공개 Storage에 같은 불투명 `audioAssetId`로 올린다. 실제 접근 URL, 로컬 경로, 참조 음성, 모델 가중치는 저장소에 넣지 않는다.
3. **자산 연결 PR:** 정확한 템플릿 ID·발화 문구·저장 객체를 대조한 뒤, 질문자 10개가 모두 존재할 때만 현재의 `qcStatus: accepted`, `isPrimary: true` 상태를 배포한다. 하나라도 없으면 팀 환경에서는 이 변경을 배포하지 않는다.
4. **앱 해석:** 기본 질문은 로그인하지 않은 사용자도 `GET /api/preset-questions/{questionId}/audio`로 재생할 수 있다. 이 API만 서버 전용 권한으로 비공개 `preset-question-audio` 버킷을 읽는다. 프런트엔드는 Storage에 직접 접근하지 않는다. 재생 실패·자산 누락은 질문 텍스트만 표시하며 Qwen3-TTS로 대체하지 않는다.
5. **통합 검증:** 각 자산이 24 kHz / mono / PCM_16이며 수동 청취에서 자연스러움·잡음·마지막 음절 완결을 통과했는지 확인한다.

## 구현자가 지킬 계약

- `qcStatus == accepted`, `isPrimary == true`, 비어 있지 않은 `audioAssetId`가 모두 충족될 때만 `mode: audio`를 선택한다.
- 그 외 모든 경우는 `mode: text`와 `audioAssetId: null`을 반환한다.
- 코치 피드백은 STT·VAD 분석이 만든 허용 문제 코드 중 최대 두 개만 사용한다.
- 사용자 음성을 Voice Cloning·추가 학습에 사용하지 않는다.
- 기본 질문의 비로그인 재생은 비공개 Storage 자체를 공개하는 것이 아니다. 서버의 허용된 질문 ID 경로만 익명 요청을 받으며, 객체명·버킷명·서명 URL은 응답에 넣지 않는다.

## GitHub에 두지 않는 항목

- WAV·MP3 등 생성 음성 파일
- 모델 가중치·checkpoint·tokenizer·참조 음성
- 원본·파생 학습 데이터와 전사문
- 실제 Storage URL·서명 URL·로컬 절대 경로·비밀값
