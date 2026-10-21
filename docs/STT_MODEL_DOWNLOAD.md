# STT 공개 모델 다운로드

말해봄 Mk.2의 STT CTranslate2 모델을 팀원이 Google OAuth 설정 없이 내려받기 위한 경로다.

## 공개 번들 경계

Google Drive의 `MALHAEBOM_STT_PUBLIC` 폴더에는 추론에 필요한 모델 파일만 둔다.

포함:

- `config.json`
- `model.bin`
- `preprocessor_config.json`
- `tokenizer.json`
- `vocabulary.json`

포함하지 않음:

- AI Hub 원천/라벨 ZIP
- `train.jsonl`, `validation.jsonl`
- 재구성된 학습/검증 WAV
- quick-eval WAV/manifest
- checkpoint/trainer state
- API key, OAuth token, rclone credential

공개 링크를 활성화하기 전에는 모델 가중치 자체의 재배포 가능 여부도 적용되는 데이터/모델 라이선스 기준으로 별도 확인한다.

## 팀원 사용법

공개 Drive 폴더가 `링크가 있는 모든 사용자: 뷰어`로 설정된 뒤 다음 한 줄을 실행한다.

```bash
python3 backend/scripts/download_stt_model.py
```

스크립트는 프로젝트 환경에 `gdown`을 설치하지 않는다. 고정 버전 `gdown==6.4.0`을 `.cache/tools/` 아래에 별도로 설치한 뒤 익명 다운로드를 수행한다. 폴더 목록을 스크래핑하지 않고 `configs/stt/public_model_manifest.json`에 고정한 공개 파일 ID 5개를 각각 내려받는다.

다운로드 후 다음 위치에 모델이 설치된다.

```text
models/stt/whisper-medium-busan-lora-a100-fast-ct2-v3/
├─ config.json
├─ model.bin
├─ preprocessor_config.json
├─ tokenizer.json
└─ vocabulary.json
```

각 파일의 크기와 SHA-256은 `configs/stt/public_model_manifest.json`과 비교한다. 하나라도 다르면 설치 성공으로 처리하지 않는다.

이미 정상 모델이 있으면 네트워크 다운로드 없이 검증 후 종료한다.

```bash
python3 backend/scripts/download_stt_model.py --verify-only
```

깨진 로컬 다운로드를 지우고 다시 받으려면:

```bash
python3 backend/scripts/download_stt_model.py --force
```

## 관리자 준비

배포 폴더 ID, 각 파일의 Drive file ID와 checksum은 `configs/stt/public_model_manifest.json`에서 관리한다. 공개 폴더의 모델 파일을 교체하면 새 file ID와 size, SHA-256을 함께 갱신한다.

이 다운로드 경로는 공개 가능한 추론 모델 전달만 담당한다. AI Hub 데이터 재구성은 [AI Hub STT 119 데이터 준비 및 재구성](AIHUB_DATA_DOWNLOAD.md)의 비공개 로컬 절차를 따른다.
