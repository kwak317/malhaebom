# 2026-09-28 Analysis E2E benchmark

## 상태

EXECUTED — 로컬 Docker와 Cloud Run CPU benchmark 완료. Hosted Supabase/RLS를 포함한 실제 배포 E2E는 후속 검증으로 남긴다.

## 목적

실제 사용자의 체감 경로인 `POST /analysis-jobs` 업로드부터 분석 작업이 `completed` 또는 `failed`가 될 때까지의 시간을 측정한다.

standalone STT benchmark와 달리 다음을 함께 포함한다.

- 인증
- multipart audio upload
- Supabase analysis job 생성
- VAD
- practice session 기반 dynamic STT hint 조회
- faster-whisper STT
- delivery analysis
- Supabase 결과 저장
- polling latency

## 측정값

외부 benchmark CLI:

- POST start → 202
- 202 → terminal
- POST start → terminal
- result.processing_time_sec
- result.rtf
- p50 / p95 / mean / min / max
- 첫 요청과 warmup 제외 measured runs 구분

서버 구조화 로그:

- mark_processing_ms
- vad_ms
- hint_ms
- stt_ms
- delivery_ms
- persist_ms
- total_ms
- audio_duration_sec

로그에는 bearer token, 질문 원문, 공고/요구사항 원문, initial_prompt 전체를 남기지 않는다.

## 구현

CLI:

    backend/scripts/benchmark_analysis_e2e.py

단위 테스트:

    backend/tests/test_benchmark_analysis_e2e.py

출력 기본 경로:

    local-results/analysis-e2e-benchmark/<label>/summary.json
    local-results/analysis-e2e-benchmark/<label>/SUMMARY.md

benchmark job은 기본적으로 각 run 종료 후 DELETE /analysis-jobs/{job_id}로 삭제한다. 따라서 기존 practice session의 attempt_no=1 unique 제약을 반복 실행에서도 피한다.

## 1. 로컬 Docker CPU/int8

서비스 기본값을 명시한다.

    export STT_DEVICE=cpu
    export STT_COMPUTE_TYPE=int8
    docker compose up --build

health 확인:

    curl http://127.0.0.1:8000/health

로그에서 서버 내부 timing 확인:

    docker compose logs -f api | grep analysis_timing

Supabase 로그인 사용자의 access token을 shell 환경변수로 넣는다.

    export ANALYSIS_BENCH_TOKEN='...'

토큰은 CLI 출력과 result JSON에 저장하지 않는다.

### 단순 서비스 latency

공고 기반 dynamic hint를 제외하고 전체 service path latency만 확인한다.

    .venv/bin/python backend/scripts/benchmark_analysis_e2e.py \
      --base-url http://127.0.0.1:8000 \
      --audio \
        local-results/stt-real-user-devset/audio/01.m4a \
        local-results/stt-real-user-devset/audio/11.m4a \
        local-results/stt-real-user-devset/audio/25.m4a \
      --warmup 1 \
      --runs 10 \
      --label local-docker-cpu

### 기존 practice session으로 dynamic hint까지 포함

세션의 question type/id/text와 benchmark CLI의 question fields가 정확히 같아야 한다.

    .venv/bin/python backend/scripts/benchmark_analysis_e2e.py \
      --base-url http://127.0.0.1:8000 \
      --practice-session-id '<UUID>' \
      --question-type custom \
      --custom-question-text '해당 세션에 저장된 질문과 정확히 같은 텍스트' \
      --audio \
        local-results/stt-real-user-devset/audio/11.m4a \
        local-results/stt-real-user-devset/audio/21.m4a \
        local-results/stt-real-user-devset/audio/30.m4a \
      --warmup 1 \
      --runs 10 \
      --label local-docker-real-session

### 검수 공고로 benchmark session 자동 생성

선택 가능한 검수 공고 ID와 요구사항 ID 1~2개를 지정하면 POST /api/practice-sessions를 먼저 호출한다.

    .venv/bin/python backend/scripts/benchmark_analysis_e2e.py \
      --base-url http://127.0.0.1:8000 \
      --job-posting-id '<UUID>' \
      --requirement-id '<UUID>' \
      --requirement-id '<UUID>' \
      --question-type custom \
      --custom-question-text 'Python과 Docker를 사용한 문제 해결 경험을 설명해 주세요.' \
      --audio \
        local-results/stt-real-user-devset/audio/11.m4a \
        local-results/stt-real-user-devset/audio/21.m4a \
        local-results/stt-real-user-devset/audio/30.m4a \
      --warmup 1 \
      --runs 10 \
      --label local-docker-posting-context

이 모드는 analysis job과 Storage audio는 삭제하지만 생성한 practice session 자체는 남긴다.

## 2. Cloud Run

동일 명령에서 base URL만 배포 API URL로 바꾼다.

    .venv/bin/python backend/scripts/benchmark_analysis_e2e.py \
      --base-url 'https://<cloud-run-api>' \
      --practice-session-id '<UUID>' \
      --question-type custom \
      --custom-question-text '해당 세션의 질문' \
      --audio \
        local-results/stt-real-user-devset/audio/01.m4a \
        local-results/stt-real-user-devset/audio/11.m4a \
        local-results/stt-real-user-devset/audio/25.m4a \
      --warmup 1 \
      --runs 10 \
      --label cloud-run-cpu

### 실제 측정 결과

Cloud Run benchmark는 Hosted Supabase가 아닌 benchmark 전용 mock/local analysis storage를 사용했다. 따라서 아래 수치는 인증 형식, HTTP upload/polling, VAD, faster-whisper, delivery 분석을 포함하지만 Supabase RLS/Storage persistence latency를 포함하지 않는다. 인메모리 job이 다른 인스턴스로 이동하지 않도록 measured run 동안 `concurrency=1`, service `min=1`, `max=1`, instance-based CPU를 사용했다.

| 환경 | E2E p50 | E2E p95 | STT p50 | STT p95 | STT RTF p50 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Local Docker CPU/int8 | 3.670s | 3.825s | 3.370s | 3.573s | 약 0.234 |
| Cloud Run 2 vCPU / 8 GiB | 21.082s | 23.546s | 20.697s | 23.015s | 1.431 |
| Cloud Run 4 vCPU / 8 GiB | 10.717s | 11.108s | 10.281s | 10.697s | 0.706 |
| Cloud Run 8 vCPU / 8 GiB | 7.988s | 8.688s | 7.596s | 8.278s | 0.520 |

2→4 vCPU는 STT p50이 거의 절반으로 줄었지만, 4→8 vCPU는 10.281s→7.596s로 개선 폭이 작아졌다. 8 vCPU도 local Docker STT p50보다 약 2.25배 느렸다.

### CPU-only + Whisper pre-bake 이미지

Cloud Run용 `Dockerfile.cloudrun-cpu`를 별도로 추가했다.

- `torch==2.11.0+cpu`, `torchaudio==2.11.0+cpu`를 먼저 설치해 `silero-vad`가 CUDA/NVIDIA wheel을 끌어오지 않도록 했다.
- 서비스 코드는 PyAV로 오디오를 디코딩하므로 Cloud Run 전용 이미지에서는 system `ffmpeg`를 제거하고 `libgomp1`만 유지했다.
- `mobiuslabsgmbh/faster-whisper-large-v3-turbo`의 immutable revision `0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf`를 `/opt/models/large-v3-turbo`에 build-time pre-bake한다. Dockerfile의 `STT_MODEL_REVISION`과 image label `ai.malhaebom.stt.model-revision`에 revision을 남기고 `STT_MODEL_NAME`을 로컬 경로로 고정한다.
- revision 고정 전 이미지의 `--network none` 컨테이너에서 모델 경로 존재, `torch=2.11.0+cpu`, `cuda=False`, PyAV import, faster-whisper 모델 load를 확인했다. 오프라인 모델 load는 초기 검증 4.196s, fresh rebuild 재검증 12.682s로 변동해 단일 cold-start 값으로 해석하지 않는다.
- `cloudbuild.cloudrun-cpu.yaml`은 built-in `$PROJECT_ID`와 location/repository/image/tag substitution을 사용하므로 특정 GCP project ID를 파일에 고정하지 않는다.

    gcloud builds submit . \
      --config cloudbuild.cloudrun-cpu.yaml \
      --substitutions _LOCATION=asia-northeast3,_REPOSITORY=mcp-repo,_IMAGE_NAME=malhaebom-stt-benchmark,_TAG=cpu-prebaked

| 항목 | 기존 이미지 | CPU/pre-baked 이미지 |
| --- | ---: | ---: |
| Local Docker image size | 3.444 GB | 1.934 GB |
| Cloud Build start→finish | 589.1s | 266.6s |
| Artifact Registry push | 324.5s | 128.6s |

optimized revision의 Cloud Run image import는 59.63s, container health는 4.02s였다. 4 vCPU에서 revision rollout 후 첫 benchmark 요청은 E2E 17.249s / STT 10.625s였고, 바로 다음 요청은 E2E 10.737s / STT 10.246s였다. 기존 4 vCPU 이미지의 첫 benchmark 요청 35.792s와 비교하면 첫 요청 지연이 약 18.5s 감소했다.

이 첫 요청 비교는 scale-to-zero 뒤의 순수 cold-start 측정이 아니라 새 revision rollout 직후의 first-request 비교다. 실제 scale-to-zero cold-start는 별도 실험이 필요하다. 위 이미지 크기·빌드·지연 수치는 모델 revision을 고정하기 전 이미지에서 측정했다. 해당 이미지에 포함된 정확한 upstream commit은 추적할 수 없으므로, 고정 revision 이미지의 수치로 소급 해석하지 않는다. 고정 revision 이미지의 build 및 latency 재측정은 후속 검증이다.

## 비교 순서

1. local Docker CPU/int8, concurrency 1
2. Cloud Run CPU/int8, concurrency 1
3. cold first request와 warm p50/p95 분리
4. server STT p50/p95와 전체 total p50/p95 비교
5. 필요할 때만 concurrency 2를 별도 실험으로 추가

현재 CLI는 의도적으로 concurrency 1만 지원한다. 먼저 단일 요청 경로의 병목을 분리한 뒤 동시성 실험을 추가한다.
