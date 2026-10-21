# 2026-09-27 STT 실사용 녹음 평가 문서화

## 목적

Syncthing 공유 폴더에 보관된 1인 화자 STT 실사용 녹음 30건으로 B0와 C2를 비교한 결과를 재현 가능하게 문서화한다. 개인 음성 원본은 Git에 넣지 않는다.

## 작업 전 상태

- B0 clean continuation과 C2 AI Hub 71592 + replay20 CT2 artifact가 로컬에 존재했다.
- evaluate_stt_ct2.py로 CER/WER 평가가 가능했다.
- 실사용 녹음 30개와 대본은 로컬 Syncthing 공유 폴더에만 있었다.
- raw CER/WER는 숫자·영문 표기 차이에 크게 영향을 받았다.

## 수행한 작업

- 대본 30문장을 저장소 문서 자산으로 추가했다.
- 실사용 평가 결과와 데이터 fingerprint, 모델/추론 조건, 한계를 실험 문서로 기록했다.
- 숫자/영문 발음 표기 차이만 보정하는 score_stt_spoken_form.py를 추가했다.
- 실제 오인식이 과도하게 보정되지 않는 단위 테스트를 추가했다.
- 음성 원본과 ZIP은 저장소에 추가하지 않았다.

## 주요 판단과 이유

- 실제 사용자 음성은 CONSTRAINTS.md의 데이터 규칙과 실험 문서의 대형 음성 비커밋 원칙에 따라 외부 보관한다.
- raw CER/WER와 발화형 정규화 CER/WER를 모두 남겨 정규화가 원본 지표를 덮어쓰지 않게 한다.
- 19~24번은 숫자·영문 stress set으로 별도 해석한다.
- 1인 낭독 30건이므로 제품 전체 성능이나 일반 사용자 정확도로 표현하지 않는다.

## 변경 파일

- backend/scripts/score_stt_spoken_form.py
- backend/tests/test_score_stt_spoken_form.py
- docs/experiments/stt/2026-09-27_real-user-recording-eval.md
- docs/experiments/stt/assets/2026-09-27_real-user-recording-script.md
- docs/experiments/README.md
- docs/worklogs/README.md
- docs/worklogs/2026-09-27_1706_stt-real-user-eval.md

## 검증

- scorer 단위 테스트 실행
- 변경 diff와 PR size policy 확인
- Git tracked 파일에 M4A/ZIP이 포함되지 않았는지 확인
- B0/C2 결과 수치가 로컬 local-results/stt-real-eval-2026-09-27 집계와 일치하는지 확인

## 발견한 문제

- 기존 legacy-default CT2는 현재 로컬 경로에 없어 이번 30건 비교에서 제외했다.
- 영문 기술용어 stress set은 발화형 정규화 이후에도 실제 오인식이 많았다.

## 미확인 사항

- 다화자·자유 발화 환경에서 같은 개선이 재현되는지 미확인이다.
- 이번 결과만으로 제품 기본 STT 교체 여부를 결정하지 않았다.

## 다음 작업

- 다른 화자와 자유 발화 샘플을 추가할 경우 현재 stress/core 구분을 유지해 회귀 평가한다.
- 제품 기본 STT 교체는 기존 retention/final-test와 실사용 평가를 함께 검토해 별도로 결정한다.
