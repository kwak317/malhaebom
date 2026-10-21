# 2026-09-28 Analysis E2E benchmark 실행

## 목적

standalone STT latency가 아니라 실제 /analysis-jobs 서비스 경로의 upload → completed 체감 지연을 로컬 Docker와 Cloud Run에서 같은 방식으로 측정할 수 있게 한다.

## 변경

- backend/scripts/benchmark_analysis_e2e.py
  - bearer token 기반 실제 API 호출
  - WAV/M4A multipart upload
  - 202 응답과 terminal status polling
  - warmup + measured runs
  - POST→202, 202→terminal, total, server STT, RTF 집계
  - p50/p95/mean/min/max 출력
  - summary.json / SUMMARY.md 생성
  - run 완료 후 analysis job 및 Storage audio cleanup
  - 기존 practice session 또는 검수 공고 기반 신규 session 지원
- PersistentAnalysisJobService.process()
  - mark_processing / VAD / hint / STT / delivery / persist / total timing log
  - 질문·공고·prompt 원문은 로그하지 않음
- backend/tests/test_benchmark_analysis_e2e.py
  - percentile
  - warmup 제외 summary
  - question form
  - posting requirement validation
  - repeated keep-jobs constraint

## 검증

- backend/tests/test_benchmark_analysis_e2e.py: 5 tests PASS
- backend/tests/test_persistent_analysis_api.py: project runtime wrapper PASS
- backend/tests/test_stt_runtime_parity.py: 3 tests PASS

## 실제 실행 결과

- Local Docker CPU/int8: measured 10/10 완료, E2E p50 3.670s / p95 3.825s, STT p50 3.370s / p95 3.573s.
- Local server timing에서 warm VAD는 약 50~65ms, STT가 전체 처리의 대부분이었다. 첫 smoke의 약 9s는 VAD cold initialization 약 4.7s 영향이 컸다.
- Cloud Run benchmark service를 서울 리전에 생성하고 `concurrency=1`, `min/max=1`, instance-based CPU로 2/4/8 vCPU를 비교했다.
- Cloud Run STT p50: 2 vCPU 20.697s, 4 vCPU 10.281s, 8 vCPU 7.596s. 4→8 vCPU부터 scaling 효율이 크게 감소했다.
- benchmark service는 Hosted Supabase 대신 mock/local analysis storage를 사용했다. 따라서 Cloud Run 수치는 production RLS/Storage persistence 검증으로 해석하지 않는다.

## Cloud Run 이미지 최적화

- 일반 Docker image의 CPU 실행에서도 CUDA PyTorch/NVIDIA dependency가 설치되는 것을 확인했다.
- `Dockerfile.cloudrun-cpu`, `cloudbuild.cloudrun-cpu.yaml`을 추가했다.
- CPU-only PyTorch 2.11.0 + torchaudio 2.11.0을 사용하고 system ffmpeg를 제거했다. 오디오 decode는 기존 PyAV 경로를 유지한다.
- faster-whisper large-v3-turbo를 `/opt/models/large-v3-turbo`에 pre-bake했다.
- local image: 3.444GB → 1.934GB.
- Cloud Build: 589.1s → 266.6s, registry push: 324.5s → 128.6s.
- offline/network-disabled model load는 초기 4.196s, fresh rebuild 재검증 12.682s로 변동했다. 둘 다 네트워크 다운로드 없이 local model path에서 성공했다.
- optimized image local smoke: E2E 4.599s, STT 3.432s, RTF 0.229.
- optimized Cloud Run 4 vCPU rollout-first request: E2E 17.249s / STT 10.625s. 다음 요청: E2E 10.737s / STT 10.246s.
- 벤치 종료 후 service `min instances`를 0으로 다시 낮췄다.

## 후속 작업

1. Hosted Supabase/RLS를 포함한 실제 persistent analysis path로 동일 benchmark 실행
2. scale-to-zero 상태의 순수 Cloud Run cold-start를 별도 측정
3. CPU 16 vCPU 확대보다 GPU/STT 전용 실행 환경을 우선 비교
4. 필요할 때만 concurrency 2를 별도 실험으로 추가

## 2026-09-29 PR #106 review 보완

- 작업 전 상태: Cloud Run CPU Dockerfile의 Hugging Face `snapshot_download`가 revision 없이 기본 브랜치를 받았다. 다른 STT 실험은 `0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf`로 고정돼 있어 이미지와 실험 결과의 모델 artifact를 연결할 수 없었다.
- 변경: `Dockerfile.cloudrun-cpu`에 같은 immutable revision을 고정하고 `ai.malhaebom.stt.model-revision` image label로 남겼다. `docs/experiments/stt/2026-09-28_analysis-e2e-benchmark.md`와 `docs/CURRENT_STATE.md`에서 기존 수치가 고정 전 이미지의 결과임을 분명히 했다.
- 검증: Dockerfile의 실제 `RUN python -c` 구문을 stub `snapshot_download`로 실행해 repo ID·고정 revision·local path 전달을 확인했다. `backend/tests/test_stt_runtime_parity.py` 3개, `backend/tests/test_benchmark_analysis_e2e.py` 5개, `git diff --check`가 통과했다.
- 미확인: 이 환경에는 Docker CLI가 없어 고정 revision 이미지의 build·label·모델 load 및 Cloud Run latency를 재측정하지 못했다. 기존 수치를 고정 revision 이미지 결과로 사용하지 않는다.
- 다음 작업: Docker 사용 환경에서 고정 revision 이미지를 build하고 label과 모델 load를 확인한 뒤 필요한 Cloud Run benchmark를 다시 실행한다.
