# 고품질 데이터 기반 감정분류 정확도 개선 실험

## 평가 조건

- 시작 모델: `jungjongho/wav2vec2-xlsr-korean-speech-emotion-recognition`
- 감정 라벨: 기쁨·당황·분노·불안·슬픔
- 고정 validation: 고품질 선별 데이터 409개
- 평가지표: accuracy, macro-F1
- 원본 WAV·manifest·checkpoint는 비공개 보관

## 결과 (2026-08-21)

| 실험 | 학습 구성 | Validation Accuracy | Macro-F1 | 결정 |
|---|---|---:|---:|---|
| 원본 모델 | 파인튜닝 없음 | 29.83% | 29.17% | 기준선 |
| 고품질 파인튜닝 | 균형 고품질 train 3,121개와 추가 고품질 train | **64.30%** | **64.36%** | 채택 |
| weighted loss | 분노 0.7, 불안 1.3, 슬픔 1.5 | 62.10% | 기록 없음 | 미채택 |
| 추가 데이터 확장 | 7,536개 train, 균형 sampler | 61.12% | 기록 없음 | 미채택 |

## 결론

- 원본 모델 대비 최고 accuracy는 34.47%p 상승했다.
- 추가 데이터 확장과 weighted loss는 고정 validation accuracy를 낮춰 채택하지 않았다.
- 최종 채택 checkpoint는 64.30% validation accuracy를 기록한 비공개 모델이다.
- 원본 모델 카드의 76.7%는 데이터·평가 조건이 공개되지 않아 이 실험 수치와 직접 비교하지 않는다.

## KESDy18 검토

KESDy18은 기쁨·분노·슬픔·중립 4개 라벨로 구성되어 당황·불안이 없는 현재 5개 감정 학습에 바로 합치지 않았다. 이후 3개 공통 감정의 외부 평가 또는 별도 보조 실험 대상으로 검토한다.
