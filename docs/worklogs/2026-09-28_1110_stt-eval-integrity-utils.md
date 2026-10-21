# 2026-09-28 STT 실사용 평가 무결성 유틸 분리

## 목적

model × beam 실험 PR의 리뷰 크기를 유지하면서 모델 fingerprint, resume 무결성 검증, 공통 scoring/timing 로직을 재사용 가능한 유틸로 분리한다.

## 수행한 작업

- CT2 필수 파일 존재 검사 및 content-based fingerprint
- devset manifest 로딩과 기본 검증
- percentile / timing / raw·spoken-form group scoring
- metrics JSON schema/config 일치 확인
- predictions.json 존재·행 수·필수 필드 검증
- 손상 JSON 또는 incomplete output은 resume 완료 결과로 인정하지 않음

## 검증

- backend/tests/test_stt_real_user_eval_utils.py: 5 tests PASS

## 다음 작업

후속 model × beam runner에서 이 유틸을 사용해 immutable model provenance와 안전한 --resume을 적용한다.
