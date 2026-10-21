# TTS 공개 모델 다운로드

말해봄 Mk.2의 Qwen3-TTS 계열 질문자/코치 모델을 Google OAuth 설정 없이 내려받는 경로다.

## 공개 번들

공개 Drive 폴더 `MALHAEBOM_TTS_PUBLIC`에는 추론·사전 생성에 필요한 모델 파일만 둔다.

- 질문자: `candidate_04_questioner` → `questioner_candidate04/model_or_adapter/`
- 코치: `candidate_01_coach` → `coach_candidate01/model_or_adapter/`

각 모델 디렉터리에는 모델 본체, tokenizer 설정, `speech_tokenizer/`가 포함된다.

현재 공개 번들에 포함되지 않음:

- 학습 dataset/manifest
- 참조·원화자 음성
- 생성 WAV/MP3
- 선택된 추론 모델 디렉터리 외 checkpoint/trainer state
- API key, OAuth token, credential

현재 handoff는 두 모델을 Qwen3-TTS 계열 산출물로 확인할 수 있지만, 실제 fine-tuning dataset/원본 녹음 출처까지는 재구성되지 않았다. 따라서 이 문서는 AI Hub 출처를 주장하지 않는다.

2026-09-18 기준으로 기존 보관 위치 두 곳을 재귀 확인했고, WAV/MP3/FLAC/M4A/OGG/AAC 형식의 원본·참조·평가 음성은 발견되지 않았다. `coach_candidate01.zip` 내부까지 확인했지만 음성 파일은 없었다. 따라서 현재 보존본만으로는 candidate별 학습 음성 데이터나 reference audio를 복구할 수 없으며, 해당 데이터의 별도 보관 여부와 출처는 팀장 확인이 필요하다.

## 팀원 사용법

Drive 폴더가 `링크가 있는 모든 사용자: 뷰어`로 설정된 뒤 두 모델을 모두 받으려면:

```bash
python3 backend/scripts/download_tts_models.py
```

질문자만:

```bash
python3 backend/scripts/download_tts_models.py --model questioner
```

코치만:

```bash
python3 backend/scripts/download_tts_models.py --model coach
```

스크립트는 프로젝트 환경에 `gdown`을 설치하지 않는다. `gdown==6.4.0`을 `.cache/tools/`에 격리 설치하고 `configs/tts/public_model_manifest.json`에 고정된 Drive file ID를 개별 다운로드한다.

설치 위치:

```text
models/tts/
├─ questioner_candidate04/
│  └─ model_or_adapter/
│     ├─ model.safetensors
│     ├─ config.json
│     ├─ generation_config.json
│     ├─ merges.txt
│     ├─ preprocessor_config.json
│     ├─ tokenizer_config.json
│     ├─ vocab.json
│     ├─ README.md
│     └─ speech_tokenizer/
└─ coach_candidate01/
   └─ model_or_adapter/
      ├─ model.safetensors
      ├─ config.json
      ├─ generation_config.json
      ├─ merges.txt
      ├─ preprocessor_config.json
      ├─ tokenizer_config.json
      ├─ vocab.json
      ├─ README.md
      └─ speech_tokenizer/
```

각 파일은 크기와 SHA-256을 manifest와 비교한다. 하나라도 다르면 설치 성공으로 처리하지 않는다.

기존 설치만 검증:

```bash
python3 backend/scripts/download_tts_models.py --verify-only
```

깨진 선택 모델을 다시 받기:

```bash
python3 backend/scripts/download_tts_models.py --model questioner --force
```

## 런타임 연결

질문자 실시간 TTS는 승인된 질문자 checkpoint directory를 사용한다. 예:

```dotenv
QUESTION_TTS_MODEL_PATH=/absolute/path/to/models/tts/questioner_candidate04/model_or_adapter
```

별도 GPU Worker를 사용할 때는 같은 질문자 모델 경로를 `TTS_WORKER_MODEL_PATH`에 전달한다.

코치 `candidate_01_coach`는 현재 고정 피드백 템플릿의 사전 생성·청취 검수용 모델이다. 앱 요청마다 이 모델을 실행하는 용도로 전달하지 않는다.

## 관리자 갱신

공개 모델 파일을 교체하면 Drive file ID, size, SHA-256을 `configs/tts/public_model_manifest.json`에서 함께 갱신한다.

기반 모델 README에는 Apache-2.0 표기가 포함되어 있다. 실제 fine-tuning 데이터/원화자 출처는 현재 handoff만으로 특정하지 않으므로, 별도 근거 없이 특정 dataset 출처를 문서에 추가하지 않는다. 추후 팀장 확인으로 원본/참조 음성 또는 dataset 보관 위치가 확인되면 공개 가능 범위와 재배포 권한을 먼저 확인한 뒤 별도 manifest로 추가한다.
