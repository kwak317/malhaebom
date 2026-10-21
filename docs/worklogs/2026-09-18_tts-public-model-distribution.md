# TTS 공개 모델 배포 경로

## 목적

팀원이 Google OAuth/rclone 설정 없이 `candidate_04_questioner`와 `candidate_01_coach` 모델을 gdown으로 재현할 수 있게 한다.

## 확인된 출처 경계

- 두 전달 모델의 `model_or_adapter/README.md`는 Qwen3-TTS-12Hz-0.6B-Base 및 Apache-2.0을 기록한다.
- 현재 저장소·handoff에는 두 candidate의 실제 fine-tuning dataset/원본 녹음 출처를 입증하는 자료가 없다.
- 따라서 TTS 공개 manifest는 AI Hub 출처를 주장하지 않는다.
- 기존 보관 위치 두 곳을 재귀 확인했으며 실제 음성 파일은 0개였다.
- 두 번째 위치의 `coach_candidate01.zip` 중앙 디렉터리도 확인했지만 모델/설정/HuggingFace cache만 있었고 음성 파일은 없었다. `questioner_candidate04.zip`은 0 byte였다.
- 따라서 학습 dataset, 참조/원화자 음성, 생성 WAV는 현재 공개 번들에서 의도적으로 숨긴 것이 아니라 현재 보존본에서 확인되지 않은 상태다. 별도 보관 여부와 출처는 팀장 확인이 필요하다.

## 수행한 작업

- 개인 My Drive에 `MALHAEBOM_TTS_PUBLIC` 폴더를 생성했다.
- 질문자/코치 각각 선택된 `model_or_adapter/` 전체를 서버사이드 복사했다.
- 모델당 12개, 총 24개 파일을 공개 manifest 대상으로 고정했다.
- 원본 handoff 24개와 공개 번들 24개의 Drive file ID를 전수 비교했고 공통 ID가 0개임을 확인했다. 따라서 TTS 공개 번들은 이미 원본과 분리된 새 Drive 객체이며 STT처럼 재복사할 필요가 없다.
- Drive metadata에서 size와 SHA-256을 확인해 `configs/tts/public_model_manifest.json`에 기록했다.
- `backend/scripts/download_tts_models.py`를 추가했다.
  - `gdown==6.4.0` 격리 설치
  - `questioner`, `coach`, `all` 선택
  - 개별 공개 file ID 다운로드
  - size/SHA-256 검증
  - 검증 후 `models/tts/` 설치
- 사용 절차를 `docs/TTS_MODEL_DOWNLOAD.md`에 문서화했다.
- 공개 질문자 `config.json`을 `gdown --no-cookies`로 익명 다운로드해 4,726 byte 크기까지 확인했다.

## 남은 작업

- 익명 gdown 전체 E2E 실행
- 질문자 모델 실제 TTS smoke
- 코치 모델 사전 생성 smoke
- 팀장에게 candidate별 학습/참조 음성 데이터의 별도 보관 위치, 출처, 재배포 가능 여부 확인
