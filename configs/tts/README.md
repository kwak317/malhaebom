# TTS 자산 매니페스트

> 2026-09-17 정적 audit 정정: 현재 catalog는 질문자 10개 accepted, 코치 90개 draft다. 아래 전체 draft·질문자 미등록 설명은 이전 시점 기록이다. 현재 근거와 인수 제한은 [음성 인수 기록](../../docs/experiments/2026-09-17_voice-asset-intake.md)을 따른다.


이 폴더는 앱이 질문자·코치 음성 자산을 연결할 때 사용할 **메타데이터만** 관리합니다. WAV, Qwen checkpoint, 학습 데이터, 생성 스크립트는 넣지 않습니다.

## 현재 상태

- 질문자 화자 후보: `candidate_04_questioner`
- 질문자 앱 템플릿: 10개 모두 `accepted`이며 비공개 Storage의 `audioAssetId`가 등록됨
- 코치 고정 문구 초안: `candidate_01_coach` 기준 90개, 아직 `draft`이고 `audioAssetId` 없음
- 별도 로컬 검수 코치 기록: `candidate_03_coach`의 `LOW_VOLUME` 문구 2개
- 코치 `LOW_VOLUME` 문구 2개는 로컬 청취 수용 상태이나, 비공개 Storage 업로드 전이다 (`local_reviewed_pending_private_upload`).
- 질문자 10개는 개인 Supabase에서 확인된 자산이며 팀 Supabase 연결 여부는 별도로 확인해야 한다. 코치 문구는 아직 텍스트 안내만 반환한다.

`tts_template_catalog.json`에는 질문자 10개와 코치 90개가 있습니다. 질문자 항목은 `accepted`와 `audioAssetId`를 가지며, 코치 항목은 `draft`라서 선택기가 재생 대신 텍스트 안내를 반환합니다. `tts_asset_manifest.json`의 `candidate_03_coach` 두 항목은 별도 로컬 검수 이력이며 `candidate_01_coach` 초안으로 바꾸어 기록하지 않습니다.

로컬 검수 자산을 앱에 연결하는 역할 분담과 체크리스트는 [TTS 자산 인수인계](../../docs/tts-asset-handoff.md)를 따른다. Git에 넣지 않는 질문자·코치 모델의 팀원 다운로드 절차는 [TTS 공개 모델 다운로드](../../docs/TTS_MODEL_DOWNLOAD.md)와 `public_model_manifest.json`을 따른다.

## 비공개 자산을 등록하는 순서

1. 로컬 TTS 환경에서 고정 문장을 WAV로 생성한다.
2. 24 kHz / mono / PCM_16 / 0 bytes 초과를 확인한다.
3. 자연스러움·잡음·마지막 음절 완결을 수동 청취 검수한다.
4. 배포 권한을 확인한 수용 WAV만 팀이 승인한 비공개 Storage에 업로드한다.
5. 별도 PR에서 실제 객체와 연결되는 불투명한 `audioAssetId`, `qcStatus: accepted`, `isPrimary: true`를 함께 등록한다.
6. 앱의 자산 해석기는 허용된 비공개 접근 경로만 반환하고, 실패하면 텍스트 안내로 폴백한다.

`qcStatus`가 `accepted`가 아니거나 `audioAssetId`가 비어 있으면, 이 정적 자산 선택기는 음성을 재생하지 않고 텍스트 안내만 표시해야 합니다. 정적 자산 선택 중에는 Qwen TTS를 실행하지 않습니다. 분석 LLM 기반 실시간 코치 TTS는 [별도 Spec](../../docs/specs/coach-feedback-tts.md)을 따릅니다.

## GitHub에 넣지 않는 항목

- `*.wav`, `*.mp3` 등 음성 파일
- `model.safetensors`, checkpoint, `speech_tokenizer/`
- 원본·파생 학습 데이터와 전사문
- 로컬 절대 경로와 사용자 음성
