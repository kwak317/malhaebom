# 로컬 검수 TTS 자산 인수인계

## Why

팀은 검수된 Qwen3-TTS 코치 WAV를 앱에 연결해야 하지만, 모델 가중치·참조 음성·WAV를 GitHub에 둘 수 없다. 로컬에서 수용된 자산과 아직 비공개 Storage에 배포되지 않은 상태를 구분하지 않으면 앱이 없는 파일 재생을 시도할 수 있다.

## Goal

- 팀 저장소에는 수용된 로컬 검수 사실, 실제 발화 문구, 안전한 폴백 규칙만 기록한다.
- 실제 WAV가 비공개 Storage에 배포되기 전에는 모든 코치 선택 결과가 텍스트 폴백을 유지한다.
- 다른 팀원이 어떤 자산을 언제 `accepted`로 바꿀 수 있는지 재현 가능하게 문서화한다.

### Out of Scope

- WAV·checkpoint·참조 음성·학습 데이터·실제 URL·절대 경로·SHA-256을 저장소에 추가
- Qwen 런타임 합성, 모델 학습 또는 모델 교체
- 비공개 Storage 업로드, 앱 코드·배포 변경

## What

1. `coach-low-volume-01`, `coach-low-volume-02`의 실제 발화 문구와 로컬 청취 수용 상태를 메타데이터에 기록한다.
2. 두 항목은 `audioAssetId: null`과 `draft`를 유지해, 현재 선택기는 텍스트만 반환한다.
3. `candidate_03_coach`는 현재 로컬 검수 음성 출처로 기록한다.
4. private Storage 배포와 후속 `accepted` 등록 절차를 문서화한다.

## How

- `configs/tts/tts_template_catalog.json`은 실제 발화 문구를 화면 폴백 문구로 사용한다.
- `configs/tts/tts_asset_manifest.json`은 `local_reviewed_pending_private_upload` 상태와 두 로컬 수용 템플릿을 기록한다.
- `TtsAssetSelector`는 `qcStatus == accepted`, `isPrimary == true`, 비어 있지 않은 `audioAssetId`가 모두 있을 때만 `mode: audio`를 반환한다.
- private Storage에 WAV가 업로드되고 수동 검수·자산 ID 연결이 완료된 별도 PR에서만 `accepted` 전환을 한다.

## AC

- Given `LOW_VOLUME`를 선택할 때, When private Storage 자산 ID가 없으면, Then 선택기는 실제 발화 문구와 `mode: text`·`audioAssetId: null`을 반환한다.
- Given 로컬 검수 메타데이터를 확인할 때, When 코치 항목을 읽으면, Then `candidate_03_coach`와 수용 템플릿 두 개·배포 대기 상태를 확인할 수 있다.
- Given 저장소를 검사할 때, When TTS 변경 PR을 검토하면, Then WAV·checkpoint·참조 음성·실제 URL·절대 경로·SHA-256이 없다.
- Given 비공개 Storage에 정적 자산 배포가 완료되지 않았을 때, When 팀원이 이 정적 자산 경로를 구현하면, Then 다른 WAV나 동적 TTS로 대체하지 않고 텍스트 폴백을 유지한다.
