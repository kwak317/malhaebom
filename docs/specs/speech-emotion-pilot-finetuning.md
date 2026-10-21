# 한국어 음성 감정분류 5,000개 파일럿 파인튜닝

## Why

- **페르소나**: 말해봄의 음성 분석 가능성을 검토하는 ML 개발자
- **상황**: 한국어 면접 음성에서 발화 감정을 분류할 수 있는지 제품 적용 전에 오프라인으로 확인한다.
- **문제**: 사전학습 모델의 분류 헤드와 데이터 계약이 불명확하면 학습은 실행돼도 결과를 신뢰하거나 재현하기 어렵다.
- **측정 지표**: 고정 validation split의 accuracy와 macro-F1, 학습 완료 여부, checkpoint 생성 여부

## Goal

- 승인된 5개 감정 라벨의 음성 5,000개로 1 epoch 파일럿 학습을 재현한다.
- 별도 validation split에서 accuracy와 macro-F1을 기록한다.
- 시작 checkpoint, 라벨, split, 학습 설정과 결과를 추적할 수 있게 한다.
- **Out of Scope**: 말해봄 서비스 연결, 사용자 감정 판정, 실시간 추론 API, 모델 성능 우수성 확정, 원본 음성·가중치 공개

## What

### Happy Path

1. 작업자가 비공개 저장소에서 `audio/`와 `manifest.csv`를 준비한다.
2. 스크립트가 파일 존재 여부, 16 kHz mono, 라벨과 split을 검증한다.
3. 공식 checkpoint를 명시적으로 로드하고 학습 전 샘플 추론을 통과한다.
4. 새로운 실험 디렉터리에서 1 epoch만 학습한다.
5. final checkpoint와 validation 지표를 비공개 위치에 저장한다.

### Edge Cases

- 데이터 사용 승인을 확인하지 않으면 학습을 시작하지 않는다.
- 출력 디렉터리가 이미 존재하면 덮어쓰거나 자동 재개하지 않는다.
- 지원하지 않는 라벨·split, 누락 파일, 16 kHz mono가 아닌 음성은 오류로 중단한다.
- CUDA가 없거나 FP16을 지원하지 않으면 FP32로 실행한다.
- 원본 음성·checkpoint는 Git 저장소에 추가하지 않는다.

## How

- 시작 모델: `jungjongho/wav2vec2-xlsr-korean-speech-emotion-recognition`
- 라벨: `기쁨`, `당황`, `분노`, `불안`, `슬픔`
- manifest 필수 열: `file`, `label`, `split`
- 허용 split: `train`, `validation`, `test`
- 입력 음성: WAV, 16 kHz, mono
- 학습: 1 epoch, batch size 2, gradient accumulation 2, learning rate `1e-5`
- 결과물: 격리된 출력 디렉터리의 `final/`, `train_metrics.json`, `validation_metrics.json`
- 데이터 사용 조건과 참여자 동의는 데이터 관리자가 실행 전에 확인하며, `--confirm-data-use` 없이는 실행하지 않는다.

## AC (Given-When-Then)

- **AC-01** GIVEN 승인 확인 인수가 없을 때, WHEN 학습 명령을 실행하면, THEN 데이터나 모델을 로드하기 전에 실패한다.
- **AC-02** GIVEN 출력 디렉터리가 이미 있을 때, WHEN 학습 명령을 실행하면, THEN 기존 실험을 덮어쓰지 않고 실패한다.
- **AC-03** GIVEN manifest 또는 샘플 형식이 계약과 다를 때, WHEN 검증하면, THEN 위반 내용을 표시하고 학습을 시작하지 않는다.
- **AC-04** GIVEN 유효한 파일럿 데이터와 명시적 시작 checkpoint가 있을 때, WHEN 1 epoch가 끝나면, THEN final checkpoint와 epoch 학습 지표가 생성된다.
- **AC-05** GIVEN validation split이 있을 때, WHEN 학습 후 평가하면, THEN accuracy와 macro-F1이 JSON으로 저장된다.
- **AC-06** GIVEN PR 변경 파일을 검사할 때, WHEN Git 추적 파일을 확인하면, THEN 음성·데이터 manifest·모델 가중치·checkpoint가 포함되지 않는다.
