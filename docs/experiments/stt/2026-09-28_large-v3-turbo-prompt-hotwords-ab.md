# 2026-09-28 large-v3-turbo prompt / hotwords A/B

## 상태

COMPLETED — 30건 × 3 mode 실행 완료

직전 실사용 model × beam 비교에서 large-v3-turbo + beam 1이 가장 낮은 core CER/WER와 가장 낮은 RTF를 기록했다. 다음 단계에서는 모델과 beam을 고정하고, 기술용어 context hint를 전달하는 방식만 비교한다.

## 목적

동일한 기술 스택 hint content를 사용해 다음 3개 조건을 비교한다.

| Mode | 설정 |
| --- | --- |
| none | prompt/hotwords 없음 |
| initial_prompt | 자연어 안내문 + 고정 기술용어 목록 |
| hotwords | 동일 기술용어 목록을 hotwords로 전달 |

이번 실험의 질문은 다음 두 가지다.

1. 기술용어 힌트가 core/stress CER/WER를 실제로 낮추는가?
2. 힌트가 없는 문장에 기술용어를 잘못 삽입하는 false insertion이 증가하는가?

## 기준선

- model: large-v3-turbo
- model source: `mobiuslabsgmbh/faster-whisper-large-v3-turbo`
- pinned revision: `0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf`
- beam size: 1
- device: CUDA
- compute type: float16
- language: ko
- task: transcribe
- temperature: 0.0
- word_timestamps=True
- vad_filter=False
- condition_on_previous_text=False

직전 matrix의 기준선:

- core normalized CER: 3.29%
- core normalized WER: 6.63%
- stress normalized CER: 6.00%
- stress normalized WER: 17.86%
- aggregate RTF: 0.020
- p50 latency: 0.258초

## Hint content

설정 파일:

    configs/stt/real_user_prompt_hints.json

15개 기술 스택 용어를 고정한다.

- Python
- FastAPI
- React
- PostgreSQL
- Docker
- GitHub Actions
- Whisper Medium
- CTranslate2
- CUDA
- GPU
- REST API
- JSON
- CI
- CD
- PR

이 목록은 프로젝트/공고/포트폴리오에서 답변 전에 알 수 있는 종류의 기술 스택만 사용한다. CER/WER처럼 현재 devset 대본을 보고만 알 수 있는 표현은 넣지 않아 transcript oracle leak을 줄인다.

initial_prompt는 같은 용어 목록 앞에 다음 안내문만 붙인다.

    기술 면접 답변입니다. 다음 기술 용어가 등장할 수 있습니다: ...

hotwords는 안내문 없이 같은 15개 canonical term을 전달한다.

## faster-whisper 지원 확인

현재 stt-runtime:

- faster-whisper 1.2.1
- CTranslate2 4.8.1

설치된 WhisperModel.transcribe signature에 initial_prompt와 hotwords가 모두 존재함을 확인했다.

현재 구현에서 hotwords는 hint phrases로 prompt에 포함되며 prefix가 별도로 지정되면 효과가 없다. 이번 실험에서는 prefix를 사용하지 않는다.

## 데이터

직전과 동일한 frozen 30-recording dev/diagnostic set을 사용한다.

- 01~10 일반 면접
- 11~18 기술 질문
- 19~24 숫자·영문 stress
- 25~30 자연/긴 답변

이미 모델/beam 선택에 사용한 데이터이므로 이번 결과 역시 개발·진단용으로만 사용하고 final acceptance 근거로 쓰지 않는다.

Frozen devset provenance:

- manifest SHA-256: `b217d02a4556ba61fe1c5b5ab2525432db11730c4b7ddecd2e24af79f4ce5dd8`
- audio-set SHA-256: `a069c29d8524f67ba75dde551778f30fefc89c9f41194bbea649532fba068141`
- combined data fingerprint: `19ebb69f8fcfb065d6eae832b70535a570b84f1938f7735ed78e788e174a5ea3`

audio-set fingerprint는 manifest의 현재 row 순서대로 `id + audio relative path + audio content SHA-256`을 결합해 계산한다. `--resume`은 row count뿐 아니라 manifest/audio/data fingerprint와 pinned model revision까지 동일한 경우에만 기존 결과를 재사용한다.

## 측정값

각 mode별:

- 전체 raw CER / WER
- 전체 spoken-form normalized CER / WER
- 19~24 제외 core normalized CER / WER
- 19~24 stress normalized CER / WER
- hint-term row-level recall
- hint false insertion row-term count
- aggregate RTF
- latency p50 / p95
- 문장별 prediction

term recall은 reference에 해당 고정 기술용어가 있는 row-term pair 중 prediction에서도 해당 표기를 보존한 비율이다. FastAPI/Fast API, CTranslate2/C Translate 2처럼 단순 spacing 차이만 alias로 허용한다.

false insertion은 reference에 없는 hint term이 prediction에 새로 등장한 row-term pair 수다.

## 준비 검증

preflight:

- devset 30건 확인
- pinned large-v3-turbo revision / beam 1 확인
- CUDA device count 1
- initial_prompt 지원 확인
- hotwords 지원 확인
- hint term 15개와 config SHA-256 고정

1개 녹음 × 3 mode CUDA smoke도 완료했다.

- none: 성공
- initial_prompt: 성공
- hotwords: 성공
- smoke false insertion: 세 mode 모두 0
- manifest 변경 후 row count가 동일해도 기존 metrics를 resume하지 않는 회귀 테스트 PASS

1개 샘플 smoke의 CER/WER 차이는 표본이 너무 작으므로 해석하지 않는다.

## 실행

preflight:

    .venvs/stt-runtime/bin/python backend/scripts/run_stt_real_user_prompt_ab.py \
      --preflight-only

full A/B:

    .venvs/stt-runtime/bin/python backend/scripts/run_stt_real_user_prompt_ab.py \
      --resume

출력:

- local-results/stt-real-user-prompt-ab/summary.json
- local-results/stt-real-user-prompt-ab/SUMMARY.md
- mode별 metrics.json
- mode별 predictions.json

## 결과

| Mode | Core norm CER | Core norm WER | Stress norm CER | Stress norm WER | Hint-term recall | False insertions | RTF | p50 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| none | 3.29% | 6.63% | **6.00%** | 17.86% | 82.35% | 0 | 0.019 | 0.257s |
| initial_prompt | **2.44%** | **5.27%** | 6.77% | 14.29% | **94.12%** | 0 | 0.019 | 0.251s |
| hotwords | 3.64% | 6.12% | 6.58% | **11.90%** | **94.12%** | 0 | **0.018** | **0.238s** |

전체 30건 normalized 지표:

- none: CER 3.84%, WER 8.04%
- initial_prompt: CER 3.33%, WER 6.40%
- hotwords: CER 4.24%, WER 6.85%

구간별로는 initial_prompt가 기술 질문 11~18에서 normalized CER 0.32%, WER 3.35%로 가장 낮았다. natural/long 25~30에서도 CER 5.90%, WER 6.43%로 none/hotwords보다 낮았다.

hotwords는 숫자·영문 stress 19~24에서 normalized WER 11.90%로 가장 낮았지만, core normalized CER는 none 3.29%보다 3.64%로 악화됐다.

hint-term recall은 none 14/17(82.35%)에서 initial_prompt와 hotwords 모두 16/17(94.12%)로 증가했다. 두 hint 방식 모두 놓친 항목은 real-24의 CD 한 건이었고, false insertion은 0건이었다.

## 해석

- 이 dev/diagnostic set에서는 initial_prompt가 가장 균형 잡힌 개선을 보였다.
- initial_prompt는 core CER/WER를 모두 낮추면서 기술용어 recall을 높였고 false insertion을 만들지 않았다.
- hotwords는 stress WER를 더 크게 낮췄지만 core CER가 악화돼 전체 면접 답변용 기본 전략으로 바로 선택하기에는 trade-off가 있다.
- 두 hint 방식의 RTF/p50 차이는 매우 작아 이번 표본에서는 성능 선택의 주요 요인으로 보지 않는다.
- 따라서 다음 단계의 기본 후보는 large-v3-turbo + beam 1 + initial_prompt로 두고, 실제 서비스에서는 고정 15개 목록이 아니라 공고/포트폴리오/프로젝트 맥락에서 동적으로 추출한 소수 기술용어를 넣는 방향을 검토한다.

## 판정 원칙

우선 core CER/WER가 악화되지 않는 것을 확인한다. 그 다음 stress CER/WER와 hint-term recall 개선을 본다. 정확도가 개선되더라도 false insertion이 증가하면 해당 hint 방식은 그대로 제품에 적용하지 않는다.

이 A/B 결과만으로 제품 기본 동작을 확정하지 않는다. 다음 단계에서는 공고/포트폴리오에서 실제로 hint terms를 추출하는 전략을 별도 설계하고, 최종 후보는 새로운 미공개 acceptance 녹음셋에서 검증한다.
