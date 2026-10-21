# 한국어 음성 감정분류 데이터 전처리·검증 파이프라인

## Why

- **페르소나**: 비공개 음성 데이터로 감정분류 실험을 준비하는 ML 개발자
- **상황**: 로컬 원본 데이터에서 학습용 16 kHz mono WAV와 재현 가능한 split을 준비하고 Colab에서 학습 전에 검증한다.
- **문제**: 경로가 고정된 일회성 스크립트와 수동 변환은 누락 파일, 잘못된 라벨, 데이터 중복을 놓치기 쉽다.
- **측정 지표**: 변환 성공률, 누락 파일 수, 라벨·split별 개수, 16 kHz mono 계약 위반 수

## Goal

- 명령행 인수로 원본·출력 경로를 받아 하드코딩 없이 전처리한다.
- 고정 seed와 라벨별 층화 split으로 동일 manifest를 재현한다.
- 학습 전에 전체 manifest와 WAV 계약을 검증한다.
- **Out of Scope**: 모델 다운로드·학습·평가, 서비스 연결, 원본·파생 음성 또는 manifest 공개

## What

### Happy Path

1. 데이터 관리자가 이용 범위를 확인하고 전처리 명령에 승인 플래그를 전달한다.
2. CSV 라벨과 ZIP 내부 WAV를 연결한다.
3. 허용된 5개 라벨만 16 kHz mono PCM WAV로 새 출력 디렉터리에 저장한다.
4. 라벨별로 train 80%, validation 10%, test 10%를 결정한다.
5. 별도 검증 명령과 Colab notebook으로 파일·형식·split을 확인한다.

### Edge Cases

- 승인 플래그가 없으면 원본을 읽기 전에 중단한다.
- 출력 디렉터리가 존재하면 덮어쓰지 않는다.
- CSV에 없는 WAV와 WAV가 없는 CSV 행은 학습 manifest에서 제외하고 요약에 기록한다.
- 지원하지 않는 원본 라벨은 제외한다.
- 중복 파일명, 빈 WAV, 읽을 수 없는 WAV, 잘못된 split은 검증 실패로 처리한다.

## How

- 원본 CSV 인코딩 기본값: `cp949` (인수로 변경 가능)
- 원본 CSV 열 위치: WAV ID 0번, 감정 라벨 2번
- 허용 매핑: happiness→기쁨, surprise→당황, anger/angry→분노, fear→불안, sad/sadness→슬픔
- 출력 음성: WAV, 16 kHz, mono, PCM_16
- manifest 열: `file`, `label`, `source_label`, `split`
- 기본 seed: 42
- raw dataset, prepared dataset, Colab 임시 디렉터리를 서로 분리한다.

## AC (Given-When-Then)

- **AC-01** GIVEN 데이터 이용 승인 플래그가 없을 때, WHEN 전처리를 실행하면, THEN 원본 파일을 처리하지 않고 실패한다.
- **AC-02** GIVEN 출력 디렉터리가 이미 있을 때, WHEN 전처리를 실행하면, THEN 기존 데이터를 삭제·덮어쓰지 않고 실패한다.
- **AC-03** GIVEN 동일 원본과 seed가 있을 때, WHEN 두 번 전처리하면, THEN 동일한 파일에 동일한 split이 배정된다.
- **AC-04** GIVEN 유효한 원본 WAV가 있을 때, WHEN 변환하면, THEN 결과는 16 kHz mono PCM_16이다.
- **AC-05** GIVEN 누락 파일·잘못된 라벨·형식·split이 있을 때, WHEN 검증하면, THEN 0이 아닌 종료 코드와 오류 요약을 반환한다.
- **AC-06** GIVEN PR 파일 목록을 확인할 때, WHEN 변경을 검토하면, THEN 음성·manifest·ZIP·checkpoint·모델 가중치가 포함되지 않는다.
