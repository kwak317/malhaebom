# 고품질 한국어 감정 음성 선별 결과

## 범위

이 작업은 비공개 원본 데이터에 대한 오프라인 품질 선별이다. 원본 WAV, 파생 CSV, ZIP, 모델 가중치는 저장소에 포함하지 않는다.

## 검사 기준

| 항목 | 기준 |
|---|---|
| 형식 | 16 kHz, mono |
| 길이 | 1.5~12초 |
| 음량 | -35~ -8 dBFS |
| clipping 비율 | 0.5% 이하 |
| 활성 발화 비율 | 45% 이상 |
| 중복 | SHA-256 동일 WAV 제외 |

## 실행 결과 (2026-08-21)

| 항목 | 파일 수 |
|---|---:|
| 원본 manifest | 36,053 |
| 품질 통과 후보 | 18,649 |
| 제외 | 17,404 |
| 감정별 균형 최고품질 후보 | 783 |
| 균형 후보 전체 | 3,915 |

균형 후보는 기쁨·당황·분노·불안·슬픔을 각 783개로 구성했다. 가장 적은 당황 후보 수가 균형 세트의 상한을 결정했다.

## 재현

```powershell
pip install -r backend/requirements-emotion-quality.txt
python backend/emotion_data/select_high_quality.py `
  --data-root C:\private\korean-emotion-prepared `
  --output-dir C:\private\korean-emotion-high-quality `
  --confirm-data-use
```

실행 전 데이터 이용 승인 범위와 외부 저장소 공개 가능 여부를 확인한다.
