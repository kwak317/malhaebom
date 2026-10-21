# Langfuse Prompt·Dataset·Trace 운영 Spec

## Why

- 로컬 계측 계약만으로는 실제 Langfuse 수신, Prompt version 연결, Dataset 등록을 증명할 수 없다.
- 기존 `langfuse 2.x` trace API는 신규 Langfuse Cloud 조직의 legacy 조회 API와 호환되지 않는다.
- 평가 전에 `production` label을 움직이면 release gate 없이 후보 Prompt가 운영에 적용될 수 있다.

## Goal

1. Python SDK `4.7.0+`의 OpenTelemetry ingestion과 Observations API v2를 사용한다.
2. 현재 고정 코칭 Prompt를 `candidate` label로 등록하고 generation observation에 원격 version을 연결한다.
3. 합성 평가셋 v2 30건을 안정적인 item ID로 Langfuse Dataset에 등록한다.
4. 원문 없는 smoke trace를 전송하고 세 observation과 Prompt 연결을 API로 검증한다.
5. 앱은 설정된 Prompt label을 읽되 조회 실패 시 현재 로컬 Prompt로 안전하게 fallback한다.

## What

- Prompt 이름: `malhaebom-coaching`
- 최초 label: `candidate`
- Dataset 이름: `malhaebom-coaching-eval-v2`
- Dataset 입력: `evals/dataset.v2.jsonl`의 합성 30건
- Dataset item ID: Dataset 이름과 case ID의 UUID5
- trace: `coaching.analyze`
- generation: `coaching.provider`
- validation span: `coaching.output_validation`
- 금지 데이터: 실제 답변·전사·공고·URL·evidence quote·token 원문

`production` label은 같은 Dataset의 baseline/candidate 평가와 release gate를 통과한 뒤에만 이동한다. 이번 작업은 candidate 등록과 smoke 연결까지만 수행한다.

## How

```bash
docker run --rm -v "$PWD:/app" -w /app \
  --env-file /absolute/path/to/.env \
  malhaebom-langfuse-v4-test \
  python -m evals.sync_langfuse_assets --apply --smoke-trace
```

- `--apply`가 없으면 외부 변경 없이 Prompt/Dataset hash와 case 수만 출력한다.
- 동일 Prompt 내용·config는 새 version을 만들지 않는다.
- Dataset item은 안정적인 UUID로 upsert한다.
- smoke trace 전송 뒤 Observations API v2에서 bounded time range로 다시 읽어 observation 3개와 Prompt 연결을 확인한다.
- 앱은 `LANGFUSE_PROMPT_NAME`, `LANGFUSE_PROMPT_LABEL`, `LANGFUSE_PROMPT_CACHE_TTL_SECONDS`를 사용한다. 설정하지 않거나 조회가 실패하면 `COACHING_PROMPT_VERSION`의 로컬 Prompt를 사용한다.
- 완료된 모델 비교의 `comparison.json`은 `evals.export_langfuse_experiments`로 가져올 수 있다. 이 경로는 provider를 다시 호출하지 않고 Langfuse Dataset item을 사용해 candidate × repeat별 Experiment run을 만들며 기존 평가 metric을 Score로 연결한다.
- import run의 latency/cost는 원래 평가 결과를 `recorded_*` Score/metadata로 보존한다. import task의 실행 시간·비용이나 새 provider trace로 해석하지 않는다.
- export 대상은 `metadata.synthetic=true`인 Langfuse Dataset item으로 제한한다. 실제 사용자 자료를 자동으로 Experiment Dataset으로 복제하지 않는다.

## AC

- **AC-01**: dry-run은 네트워크 쓰기 없이 Prompt/Dataset hash와 합성 case 30건을 출력한다.
- **AC-02**: 최초 apply는 candidate Prompt와 Dataset을 만들고 30개 item을 등록한다.
- **AC-03**: 같은 입력을 다시 apply하면 Prompt version은 늘지 않고 Dataset item ID도 유지된다.
- **AC-04**: smoke trace는 세 observation을 같은 trace ID로 남기며 generation에 Prompt 이름·version이 연결된다.
- **AC-05**: observation input/output에는 redacted 구조만 있고 사용자 원문이 없다.
- **AC-06**: 원격 Prompt 조회 성공 시 앱이 해당 문자열·version을 사용하고 실패 시 로컬 Prompt로 fallback한다.
- **AC-07**: 전체 backend test suite가 Langfuse SDK v4에서 통과한다.
- **AC-08**: 기존 comparison report의 재시도는 execution별 마지막 call만 Dataset item 결과로 연결하고, repeat는 서로 다른 Experiment run으로 보존한다.
- **AC-09**: 기존 report export는 provider API를 호출하지 않으며 contract/label/evidence/ID/semantic/latency/cost Score를 원본 attempt ID와 함께 추적할 수 있다.
