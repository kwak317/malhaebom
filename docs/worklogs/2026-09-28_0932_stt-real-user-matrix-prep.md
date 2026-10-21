# 2026-09-28 STT 실사용 모델 × beam 비교

## 목적

2026-09-27 실사용 녹음 30건을 dev/diagnostic set으로 고정하고 large-v3-turbo / B0 / C2 × beam 1/3/5 비교를 한 번에 실행할 수 있는 하네스를 준비한다.

## 작업 전 상태

- PR #69의 실사용 평가 문서, 대본, spoken-form scorer가 main에 병합되어 있었다.
- 실사용 30건에서 C2의 면접형 core 개선은 확인했지만 B0/C2가 beam 5였고, 서비스 기본 large-v3-turbo와 동일 조건 비교는 없었다.
- 서비스 FasterWhisperTranscriber는 한국어, temperature 0, word timestamps 사용, VAD 비활성, previous text conditioning 비활성으로 동작한다.
- 로컬 B0/C2 CT2 artifact와 Syncthing 음성 ZIP 30건이 존재했다.

## 수행한 작업

- frozen ZIP fingerprint를 확인하면서 30건 devset manifest를 만드는 준비 스크립트를 추가했다.
- 모델 3개 × beam 3개를 동일 조건으로 실행하는 matrix runner를 추가했다.
- raw / spoken-form CER·WER, core/stress 구간, RTF, p50/p95, 모델 load time을 자동 집계하도록 했다.
- 완료 조합을 재사용할 수 있는 --resume을 추가했다.
- CUDA library path를 자동 보완해 기존 STT runtime에서 직접 실행되도록 했다.
- matrix runner 관련 순수 함수 단위 테스트를 추가했다. devset 준비 테스트 3개는 선행 PR로 분리했다.

## 검증

- make stt-runtime-env-verify: PASS
  - Python 3.12.3
  - faster-whisper 1.2.1
  - CTranslate2 4.8.1
  - CUDA device count 1
- Syncthing ZIP: 30 M4A, frozen SHA-256 일치
- B0 CT2: complete
- C2 CT2: complete
- matrix preflight: 30 rows, 3 models, beams 1/3/5 PASS
- B0 / beam 1 / 1 sample CUDA smoke: PASS
  - model load 2.234s
  - sample processing 1.262s
  - sample RTF 0.084
- backend/tests/test_stt_real_user_matrix.py: 2 matrix-specific tests PASS
- backend/tests/test_stt_real_user_eval_utils.py: 5 integrity helper tests PASS
- large-v3-turbo cache provenance 확인:
  - repo `mobiuslabsgmbh/faster-whisper-large-v3-turbo`
  - revision `0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf`
- B0 CT2 fingerprint: `dff88625c0265bc33398942d295085edca4d06c17661d6246bcbb1cfd4e723b5`
- C2 CT2 fingerprint: `29ec9fad29442a2af027843e7c773a275e97d97213c1c215710747a3a65ac333`
- pinned large-v3-turbo / beam 1 / 1 sample CUDA smoke: PASS
  - pinned snapshot model load 1.617s
  - sample processing 0.691s
- corrupt/incomplete metrics, missing predictions, provenance mismatch는 --resume 완료 결과로 인정하지 않도록 회귀 테스트 추가

## 변경 파일

- backend/scripts/run_stt_real_user_matrix.py
- backend/tests/test_stt_real_user_matrix.py
- docs/experiments/stt/2026-09-28_real-user-model-beam-matrix.md
- docs/experiments/README.md
- docs/worklogs/README.md
- docs/worklogs/2026-09-28_0932_stt-real-user-matrix-prep.md

## 주요 판단

- 기존 30건은 이미 결과를 본 데이터이므로 dev/diagnostic set으로만 사용한다.
- 이번 단계에서는 학습, hotwords, initial prompt를 섞지 않아 모델·beam 효과를 먼저 분리한다.
- 세 모델은 CUDA/float16으로 맞춘다. CPU/int8 배포 성능은 후보 선택 이후 별도 검증한다.
- large-v3-turbo 최초 실행은 cache가 없으면 다운로드가 발생할 수 있으므로 full run은 사용자 실행 단계로 남긴다.

## 미실행 / 다음 작업

- 9개 조합 full matrix를 실행했고 failures=0을 확인했다.
- large-v3-turbo + beam 1이 core normalized CER 3.29%, WER 6.63%, RTF 0.020, p50 0.258초로 다음 기준선에 적합했다.
- large-v3-turbo는 beam 1/3/5에서 core normalized CER/WER가 동일해 beam 증가 이득이 관찰되지 않았다.
- 숫자·영문 stress 구간에서도 large-v3-turbo beam 1이 CER 6.00%, WER 17.86%로 B0/C2보다 크게 낮았다.
- 다음 실험은 large-v3-turbo + beam 1에 대해 none / initial_prompt / hotwords를 비교한다.
- 최종 설정 선택 후에는 새 acceptance 녹음셋을 사용한다.
