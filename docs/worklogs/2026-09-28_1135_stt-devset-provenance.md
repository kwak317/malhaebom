# 2026-09-28 STT devset provenance 유틸

## 목적

실사용 STT 후속 실험의 --resume이 단순 row count가 아니라 frozen manifest와 실제 audio content까지 동일할 때만 결과를 재사용하도록 공통 devset provenance 계산을 추가한다.

## 수행한 작업

- manifest.jsonl SHA-256 기록
- 각 row의 id + audio relative path + audio content SHA-256을 deterministic하게 결합한 audio-set SHA-256 기록
- manifest/audio-set/row-count를 결합한 data fingerprint 기록
- manifest 내용이 바뀌는 회귀 테스트
- audio bytes가 바뀌는 회귀 테스트

## 검증

- backend/tests/test_stt_real_user_eval_utils.py: 7 tests PASS

## 다음 작업

후속 prompt/hotwords A/B runner의 run metadata와 --resume 조건에 이 provenance를 포함한다.

## 2026-09-28 PR #71 동기화

#71의 devset provenance 연동 commit을 merge하고, merge 과정에서 이전 runner가 선택되어 사라진 preflight/metrics/resume 연결을 복원했다. `python -m unittest backend.tests.test_stt_real_user_matrix backend.tests.test_stt_real_user_eval_utils -q`에서 10개 테스트가 통과했다.
