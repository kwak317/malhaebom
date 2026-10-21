# 2026-09-28 STT service-runtime parity

## 목적

large-v3-turbo + beam 1의 서비스 기본 CPU/int8과 기존 실험 CUDA/float16을 동일 입력·모델 revision·initial_prompt 조건으로 비교한다.

## 수행

- `backend/scripts/run_stt_runtime_parity.py` 추가
- CPU/int8, CUDA/float16 외 조건 고정
- immutable model revision 및 frozen devset provenance 재사용
- 기존 diagnostic initial_prompt SHA-256을 resume key에 포함
- raw/normalized CER·WER, core/stress, hint recall, false insertion, RTF, p50/p95, load time 집계
- corrupt/incompatible 결과 재사용 방지를 기존 integrity helper에 위임
- runtime parity 단위 테스트 추가

## 검증

- `backend/tests/test_stt_runtime_parity.py`: 3 tests PASS
- preflight:
  - frozen devset 30 rows
  - CPU int8 지원 확인
  - CUDA float16 지원 확인
  - CUDA device count 1
- 1 sample × 2 runtime smoke: PASS
- full 30 × 2 runtime: PASS

## 결과

- CPU/int8
  - core normalized CER 1.94%, WER 4.59%
  - overall normalized CER 2.93%, WER 5.80%
  - RTF 0.213, p50 3.022s, p95 3.155s
  - hint recall 94.12%, false insertion 0
- CUDA/float16
  - core normalized CER 2.44%, WER 5.27%
  - overall normalized CER 3.33%, WER 6.40%
  - RTF 0.020, p50 0.269s, p95 0.438s
  - hint recall 94.12%, false insertion 0

runtime별 prediction 차이 4건 중 real-30에서 CUDA/float16만 "다음 영상에서 만나요." tail hallucination을 추가했다.

## 판단

- 서비스 기본 CPU/int8을 이 실험만으로 변경하지 않는다.
- CPU가 devset 정확도는 소폭 우세하지만 로컬 p50이 약 3초다.
- CUDA는 약 10.9배 낮은 RTF를 보였지만 한 건의 tail hallucination이 관찰됐다.
- 실제 Cloud Run CPU 성능은 현재 Ryzen 로컬 측정과 다를 수 있으므로 배포 E2E latency를 별도 측정한다.
- 최종 품질 판단은 새 multi-speaker acceptance set으로 수행한다.

## 변경 파일

- backend/scripts/run_stt_runtime_parity.py
- backend/tests/test_stt_runtime_parity.py
- docs/experiments/stt/2026-09-28_stt-runtime-parity.md
- docs/experiments/README.md
- docs/CURRENT_STATE.md
- docs/worklogs/README.md
- docs/worklogs/2026-09-28_1412_stt-runtime-parity.md
