# 감정분류 데이터 전처리·Colab 검증 실행 순서

이 절차는 데이터 준비와 학습 전 검증까지만 수행한다. 모델 다운로드와 학습은 포함하지 않는다.

## 로컬 전처리

AI Hub 데이터의 다운로드 승인과 이용 범위를 먼저 확인한다. 원본 폴더에는 라벨 CSV와 음성 ZIP이 있어야 한다.

```powershell
pip install -r backend/requirements-emotion-data.txt
python backend/emotion_data/prepare_dataset.py `
  --source-dir C:\private\emotion-raw `
  --output-dir C:\private\emotion-prepared-new `
  --confirm-data-use
python backend/emotion_data/validate_dataset.py `
  --data-root C:\private\emotion-prepared-new
```

기존 출력 경로는 덮어쓰지 않는다. 재실행할 때는 새로운 출력 디렉터리를 지정한다.

## Colab 검증

1. 준비된 데이터 폴더를 ZIP으로 압축해 승인된 비공개 Google Drive 위치에 저장한다.
2. `notebooks/korean_emotion_data_validation_colab.ipynb`를 Colab에서 연다.
3. 런타임을 연결하고 위에서부터 셀을 실행한다.
4. notebook의 `ZIP_PATH`를 실제 Drive 경로로 바꾼다.
5. 마지막 출력이 `데이터 계약 검증 통과`인지 확인한다.

브라우저 직접 업로드는 대용량 ZIP에서 0%로 오래 정체될 수 있으므로 Drive 마운트 방식을 기본으로 한다. 데이터 ZIP은 GitHub에 올리지 않는다.

## 공개 저장 금지

- 원본·변환 WAV
- 라벨 CSV와 생성 manifest
- 데이터 ZIP
- 모델 캐시·가중치·checkpoint

학습 실행 전에는 데이터 라이선스, 다운로드 승인 범위, 외부 저장소 업로드 허용 여부를 데이터 관리자가 다시 확인해야 한다.
