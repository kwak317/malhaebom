# 2026-09-28 STT 실사용 devset 준비

## 목적

2026-09-27 실사용 녹음 30건을 반복 가능한 dev/diagnostic 입력으로 고정하기 위해 ZIP fingerprint 검증, 대본 파싱, 음성 추출, manifest 생성을 하나의 준비 스크립트로 만든다.

## 작업 전 상태

- 실사용 녹음 30건과 대본은 로컬/Syncthing에 존재했다.
- 녹음 번호와 대본 번호는 1:1로 대응했지만 반복 실험용 manifest 생성 절차가 코드로 고정되어 있지 않았다.
- 이 30건은 이미 결과를 본 데이터이므로 final acceptance가 아니라 dev/diagnostic 용도로만 사용한다.

## 수행한 작업

- `backend/scripts/prepare_stt_real_user_devset.py` 추가
  - ZIP SHA-256 검증
  - canonical reference script SHA-256 검증
  - empty fingerprint bypass 차단
  - 명시적 fingerprint override 여부를 metadata에 기록
  - 01~30 대본 파싱
  - 녹음 번호와 script index 중복/누락 검사
  - 4개 구간 라벨 생성
  - `local-results/stt-real-user-devset` 아래 audio/manifest/metadata 생성
- `backend/tests/test_stt_real_user_devset.py` 추가
  - 대본 파싱
  - ZIP 음성 엔트리 탐색
  - 그룹 경계 검증

## 검증

- `backend/tests/test_stt_real_user_devset.py`: 6 tests PASS
- 실제 ZIP 30개와 frozen SHA-256 일치 확인
- 생성 manifest 30 rows 확인

## 변경 파일

- backend/scripts/prepare_stt_real_user_devset.py
- backend/tests/test_stt_real_user_devset.py
- docs/worklogs/README.md
- docs/worklogs/2026-09-28_0905_stt-real-user-devset-prep.md

## 다음 작업

이 devset 준비 결과를 입력으로 사용해 large-v3-turbo / B0 / C2 × beam 1/3/5 matrix를 별도 PR에서 실행·문서화한다.
