# Worklog — AI Hub STT 119 다운로드·재구성 정리

- 일시: 2026-09-18
- 작업자/에이전트: 김재훈 / ChatGPT
- 관련 이슈/PR: 미생성
- 관련 요구사항/결정: 말해봄 Mk.2의 STT handoff 50,000/5,000 manifest를 AI Hub dataset 119에서 재현할 수 있도록 다운로드·재구성 절차를 정리한다.

## 1. 목적

환경설정 작업 때문에 임시 stash했던 AI Hub 데이터 준비 코드를 다시 검토하고, 현재 알고 있는 말해봄 STT provenance와 실제 로컬 데이터 상태에 맞게 정리한다.

완료 조건:

- Mallo에서 섞인 TTS dataset 71349 관련 downloader/문서 절차를 제거한다.
- 현재 말해봄에 필요한 STT dataset 119 downloader와 재구성 스크립트만 복구한다.
- 현재 로컬 archive, handoff manifest, 재구성 WAV 수량을 실측해 문서에 반영한다.
- manifest와 AI Hub label/source의 대응을 다시 검증한다.

## 2. 작업 전 상태

환경설정 PR 작업 전에 다음 변경을 `stash@{0}: wip-aihub-download-reconstruction`로 보관했다.

- `backend/scripts/aihub_download_common.py`
- `backend/scripts/download_aihub_stt.py`
- `backend/scripts/download_aihub_tts.py`
- `backend/scripts/reconstruct_aihub119_segments.py`
- `docs/AIHUB_DATA_DOWNLOAD.md`
- `docs/README.md`

검토 결과 `download_aihub_tts.py`와 기존 문서의 dataset 71349/친절체 절차는 현재 말해봄이 아니라 과거 Mallo TTS 작업 가정에서 섞인 내용이었다.

현재 프로젝트 로컬을 실측했을 때:

- `data/tts/` 자체가 존재하지 않았다.
- `data/tts/aihub/71349`도 존재하지 않았다.
- 프로젝트 내 실제 71349 이름 경로도 없었다.
- 따라서 별도로 삭제할 71349 원천데이터는 이미 없는 상태였다.

## 3. 수행 내용

1. stash에서 STT 관련 파일만 선택적으로 복구했다.
   - `aihub_download_common.py`
   - `download_aihub_stt.py`
   - `reconstruct_aihub119_segments.py`
   - `AIHUB_DATA_DOWNLOAD.md`
2. `download_aihub_tts.py`는 복구하지 않았다.
3. `AIHUB_DATA_DOWNLOAD.md`를 STT dataset 119 전용 문서로 다시 작성했다.
4. 현재 로컬에 존재하는 archive 4개의 실제 경로와 byte 크기를 확인했다.
5. handoff manifest의 행 수와 고유 source conversation 수를 다시 계산했다.
6. 재구성된 WAV 파일 수를 다시 계산했다.
7. 재구성 스크립트를 validation-only 모드로 실제 실행해 manifest ↔ label/source 매핑과 `dialect_form` 일치를 검증했다.
8. `docs/README.md`에 STT 119 데이터 준비 문서 링크를 추가했다.

## 주요 판단과 이유

- 현재 말해봄 데이터 준비 경로에는 STT dataset 119만 포함한다.
- dataset 71349는 현재 말해봄 TTS 모델 provenance로 확인되지 않았으므로 downloader와 절차를 유지하지 않는다.
- 최신 handoff manifest 50,000/5,000을 source of truth로 삼고, 현재 AI Hub 119 archive에서 동일 segment를 재구성한다.
- handoff text 비교 기준은 AI Hub label의 `form`이 아니라 `dialect_form`이다.
- dataset 119 전체를 다시 받지 않고 handoff 재구성에 필요한 Training/Validation label/source archive 4개만 유지한다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `backend/scripts/aihub_download_common.py` | AI Hub 공식 shell을 이용한 공통 선택 다운로드 도구 복구 |
| `backend/scripts/download_aihub_stt.py` | dataset 119 STT downloader 복구 |
| `backend/scripts/reconstruct_aihub119_segments.py` | handoff segment 재구성/검증 도구 복구 |
| `docs/AIHUB_DATA_DOWNLOAD.md` | TTS 71349 내용을 제거하고 STT 119 전용 문서로 재작성 |
| `docs/README.md` | STT 119 데이터 문서 링크 추가 |
| `docs/worklogs/2026-09-18_aihub-stt-reconstruction.md` | 이번 작업 기록 |
| `docs/worklogs/README.md` | 이번 Worklog 링크 추가 |

## 5. 검증

현재 로컬 AI Hub 119 archive:

```text
Training label
  filekey 572701
  (비식별화완료)경상도_학습데이터_1.zip
  323,123,858 bytes

Training source
  filekey 572702
  (비식별화완료)경상도_1.zip
  29,686,321,494 bytes

Validation label
  filekey 572713
  (비식별화완료)경상도_학습데이터_2.zip
  34,001,449 bytes

Validation source
  filekey 572714
  (비식별화완료)경상도_2.zip
  29,919,002,736 bytes
```

manifest / 재구성 파일 실측:

```text
train
  rows=50,000
  unique source conversations=413
  reconstructed WAV=50,000

validation
  rows=5,000
  unique source conversations=411
  reconstructed WAV=5,000
```

Python 문법 검증:

```text
py_compile OK backend/scripts/aihub_download_common.py
py_compile OK backend/scripts/download_aihub_stt.py
py_compile OK backend/scripts/reconstruct_aihub119_segments.py
```

재구성 validation:

```text
[train] manifest rows=50,000 source conversations=413
[train] missing label sources=0 missing source WAVs=0 missing utterances=0 invalid timings=0 text mismatches=0
[train] validation PASSED

[validation] manifest rows=5,000 source conversations=411
[validation] missing label sources=0 missing source WAVs=0 missing utterances=0 invalid timings=0 text mismatches=0
[validation] validation PASSED
```

## 6. 발견한 문제 / 남은 리스크

- AI Hub live tree의 filekey는 향후 변경될 수 있으므로 새 다운로드 전에 `tree` 또는 `plan`으로 다시 확인해야 한다.
- 현재 보관 중인 약 60 GB의 원본 archive와 약 7.34 GB의 재구성 데이터는 Git ignore 대상 로컬 자산이다.
- TTS 학습용 원천데이터 provenance는 이번 작업 범위에서 새로 정하지 않았다. 현재 확인된 TTS handoff는 모델/runtime 전달물이 기준이다.

## 미확인 사항

- AI Hub live tree를 이번 작업에서 다시 네트워크 조회하지 않았다. 문서의 filekey는 현재 로컬 archive와 2026-09-17에 확인한 live tree 기준이다.
- STT 실제 fine-tuning 실행은 이번 작업에 포함하지 않았다.

## 7. 다음 작업

- 환경설정 PR과 분리된 브랜치/PR로 STT 데이터 준비 스크립트와 문서를 반영한다.
- STT 재학습을 시작할 때 현재 재구성된 50,000/5,000 데이터 경로를 학습 스크립트 입력으로 연결한다.
