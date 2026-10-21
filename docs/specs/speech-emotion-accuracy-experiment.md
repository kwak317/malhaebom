# 한국어 음성 감정분류 정확도 개선 실험 기록

## Why

- **페르소나**: 파인튜닝 설정을 비교하는 ML 개발자
- **상황**: 동일 validation split에서 고품질 데이터와 추가 학습 방식이 accuracy에 미치는 영향을 확인한다.
- **문제**: 학습 데이터 수를 늘리거나 loss 가중치를 적용해도 accuracy가 실제로 상승하는지 기록 없이 판단할 수 없다.
- **측정 지표**: 고정 validation accuracy와 macro-F1

## Goal

- 최고 validation accuracy를 낸 checkpoint와 실험별 결과를 기록한다.
- 성능이 하락한 실험도 남겨 같은 조건의 재실행을 줄인다.
- **Out of Scope**: 서비스 연결, 원본 음성·checkpoint 공개, test 결과로 설정 튜닝

## What

1. 원본 모델과 고품질 데이터 파인튜닝 모델을 동일 validation으로 평가한다.
2. 추가 데이터와 weighted loss를 각각 1 epoch 단위로 비교한다.
3. validation accuracy가 최고인 checkpoint만 채택한다.

## How

- 시작 모델: `jungjongho/wav2vec2-xlsr-korean-speech-emotion-recognition`
- 라벨: 기쁨·당황·분노·불안·슬픔
- 고정 validation: 고품질 세트 409개
- 저장 정책: checkpoint와 데이터는 비공개 보관, 저장소에는 지표·설정만 기록

## AC (Given-When-Then)

- GIVEN 동일 validation이 있을 때, WHEN 실험을 비교하면, THEN 모든 accuracy는 그 validation 기준으로 기록된다.
- GIVEN 추가 실험의 accuracy가 최고값보다 낮을 때, WHEN 결과를 적용하면, THEN 기존 최고 checkpoint를 유지한다.
- GIVEN Git 변경을 검토할 때, WHEN 파일을 확인하면, THEN WAV·CSV·ZIP·checkpoint가 포함되지 않는다.
