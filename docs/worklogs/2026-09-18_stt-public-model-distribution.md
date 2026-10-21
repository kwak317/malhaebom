# STT 공개 모델 배포 경로

## 목적

팀원이 Google Cloud OAuth client, rclone 설정, 테스트 사용자 등록 없이 공개 가능한 STT 추론 모델만 한 번에 내려받을 수 있게 한다.

## 작업 전 상태

- 최신 handoff에는 CTranslate2 모델과 AI Hub 기반 dataset/quick-eval 자료가 함께 있었다.
- rclone read-only OAuth로 handoff 접근은 확인했지만 팀원 재현 절차가 복잡했다.
- 모델과 데이터의 공개 경계를 분리한 전용 배포 폴더가 없었다.

## 수행한 작업

- 개인 My Drive에 `MALHAEBOM_STT_PUBLIC` 폴더와 `model/` 하위 폴더를 생성했다.
- 공개 번들에는 추론 모델 5개 파일만 포함하도록 manifest를 만들었다.
- AI Hub archive, train/validation manifest, 재구성 WAV, quick-eval 자료, checkpoint, credential을 공개 번들에서 제외했다.
- `backend/scripts/download_stt_model.py`를 추가했다.
  - `gdown==6.4.0`을 `.cache/tools/`에 격리 설치
  - 공개 파일 ID 5개를 manifest에서 읽어 로그인 없이 개별 다운로드
  - 파일 크기와 SHA-256 검증
  - 검증 완료 후 `models/stt/`로 이동
  - 정상 설치가 이미 있으면 다운로드 생략
- 사용 절차를 `docs/STT_MODEL_DOWNLOAD.md`에 문서화했다.
- 최초 공개 경로의 파일 ID가 기존 객체와 공유되는 구조를 발견한 뒤, Google Drive `makeCopy()`로 5개 파일을 새 객체로 다시 생성했다. 새 공개 사본은 기존 파일과 모두 다른 file ID를 사용하며 `MALHAEBOM_STT_PUBLIC`의 공개 권한을 상속한다.

## 공개 모델 manifest

Drive folder id:

```text
1-R-Dje-Bx7A-Acw0H3aAwQI9NMzZa6TT
```

최종 대상:

```text
models/stt/whisper-medium-busan-lora-a100-fast-ct2-v3/
```

## 검증

- downloader Python syntax/import 검증
- fake model fixture를 이용해 manifest 기반 size/SHA-256 검증 로직 확인
- `gdown==6.4.0` 격리 설치와 `python -m gdown --version` 실행 확인
- 공개 폴더의 작은 모델 메타파일 4개 업로드 및 Drive 목록 재확인
- 작은 모델 메타파일 4개를 실제 downloader로 익명 다운로드하고 size/SHA-256 검증 및 설치까지 E2E 확인
- `model.bin`의 공개 file ID를 `gdown --json --no-cookies`로 익명 조회 확인
- 재발급된 `config.json` file ID를 `gdown --no-cookies`로 다시 익명 다운로드해 2,257 byte 크기까지 확인
- 새 공개 사본 5개 file ID를 모두 `gdown`의 `skip_download=True`/`use_cookies=False` 경로로 resolve해 `config.json`, `model.bin`, `preprocessor_config.json`, `tokenizer.json`, `vocabulary.json` 전부 익명 다운로드 대상으로 해석되는 것을 확인
- Drive UI에서 기존 `model/`을 제거하고 새 사본 폴더 `model_new/`를 `model/`로 이름 변경해 최종 공개 트리를 정리했다. 최종 `model/` 폴더는 기존과 다른 새 객체이며 내부 5개 파일 ID는 `configs/stt/public_model_manifest.json`과 일치한다.

## 실패/제약

ChatGPT Files의 Google Drive mount로 새 폴더 생성은 성공했다. 작은 모델 메타파일 4개는 materialize 후 새 공개 폴더로 재업로드했고, `model.bin`은 Drive UI의 서버사이드 복사로 추가했다. read-only 범위로 만든 rclone remote는 쓰기 시도에서 `ACCESS_TOKEN_SCOPE_INSUFFICIENT`를 반환했으며, 이 작업을 위해 OAuth 권한을 다시 넓히지는 않았다.

상위 공개 폴더 URL을 gdown `--json`으로 익명 탐색하면 401이 발생했지만, 개별 공개 파일 ID는 익명 접근이 정상 동작했다. 따라서 downloader는 폴더 탐색에 의존하지 않고 manifest의 공개 file ID를 직접 사용한다.

## 남은 작업

- 1.5 GB `model.bin`까지 포함한 전체 익명 `gdown` E2E 실행
- 공개 전 모델 가중치 재배포 가능 여부 최종 확인
