# 한국어 음성 감정분류 5,000개 파일럿 결과

## 범위

이 기록은 말해봄 서비스에 연결하지 않은 오프라인 가능성 실험이다. 감정 결과를 사용자 평가나 면접 답변의 품질·합격 가능성 판단에 사용하지 않는다.

## 실험 구성

| 항목 | 값 |
|---|---:|
| 시작 checkpoint | `jungjongho/wav2vec2-xlsr-korean-speech-emotion-recognition` |
| 전체 샘플 | 5,000 |
| train | 4,006 |
| validation | 474 |
| test | 520 |
| 라벨 | 기쁨·당황·분노·불안·슬픔 |
| epoch | 1 |
| global step | 501 |
| 학습률 | `1e-5` |
| 실행 환경 | Google Colab GPU, FP16 |

각 라벨은 1,000개로 구성했다. 원본 음성·파생 WAV·manifest·checkpoint는 데이터 이용 조건과 저장소 정책에 따라 비공개로 보관한다.

## 1 epoch 결과

| 지표 | 결과 |
|---|---:|
| train loss | 14.1952 |
| validation loss | 1.4395 |
| validation accuracy | 0.4051 |
| validation macro-F1 | 0.4031 |
| 학습 시간 | 956.9초 |

`final/` 모델과 `checkpoint-501/`, `train_metrics.json`, `validation_metrics.json` 생성 여부를 확인했다. 대용량 결과물은 GitHub에 올리지 않는다.

## 해석 제한

- 1 epoch 파일럿 결과만으로 모델이 정확하거나 서비스 적용 가능하다고 결론 내리지 않는다.
- test split 평가는 아직 이 기록에 포함하지 않았다.
- 라벨별 precision·recall·F1, confusion matrix, 동일 조건의 기본 모델 비교가 필요하다.
- 모델 카드와 AI Hub 데이터의 라이선스·이용 승인·외부 공개 조건은 배포 전에 별도로 확인해야 한다.

## 비공개 환경 재현

```powershell
pip install -r backend/requirements-emotion.txt
python backend/emotion/finetune_pilot.py `
  --data-root C:\private\korean-emotion-pilot-5000 `
  --output-dir C:\private\experiments\emotion-pilot-epoch1-new `
  --base-model jungjongho/wav2vec2-xlsr-korean-speech-emotion-recognition `
  --confirm-data-use
```

출력 경로는 매 실행마다 새 디렉터리를 사용해야 하며 기존 checkpoint를 자동 재개하거나 덮어쓰지 않는다.
