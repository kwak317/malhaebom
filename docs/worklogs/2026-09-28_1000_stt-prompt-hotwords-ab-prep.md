# 2026-09-28 STT prompt / hotwords A/B

## 목적

large-v3-turbo + beam 1을 고정하고 기술용어 context 전달 방식만 none / initial_prompt / hotwords로 비교할 수 있게 준비한다.

## 선행 결과

직전 30건 dev/diagnostic matrix에서 large-v3-turbo + beam 1은 다음 결과를 기록했다.

- core normalized CER 3.29%
- core normalized WER 6.63%
- stress normalized CER 6.00%
- stress normalized WER 17.86%
- RTF 0.020
- p50 0.258초

beam 3/5는 core CER/WER 개선이 없고 latency만 증가해 beam 1을 다음 기준선으로 고정했다.

## 수행한 작업

- 동일 content를 initial_prompt와 hotwords에 전달하는 15개 기술 스택 hint config를 추가했다.
- CER/WER 등 transcript-only 표현은 hint에서 제외했다.
- none / initial_prompt / hotwords를 동일 large-v3-turbo beam 1 조건으로 실행하는 A/B runner를 추가했다.
- raw/normalized CER·WER, core/stress 지표, RTF/latency를 자동 집계한다.
- hint-term recall과 false insertion을 별도 측정하도록 했다.
- 완료된 동일 mode를 재사용하는 --resume을 지원한다.
- prompt/hotwords helper 단위 테스트를 추가했다.

## 검증

- backend/tests/test_stt_real_user_prompt_ab.py: 5 runner-specific tests PASS
- backend/tests/test_stt_real_user_eval_utils.py: 7 shared integrity/provenance tests PASS
- faster-whisper 1.2.1 WhisperModel.transcribe에서 initial_prompt / hotwords 인자 확인
- preflight: 30 rows, pinned large-v3-turbo revision, beam 1, CUDA PASS
- hint terms: 15
- frozen devset provenance:
  - manifest SHA-256 `b217d02a4556ba61fe1c5b5ab2525432db11730c4b7ddecd2e24af79f4ce5dd8`
  - audio-set SHA-256 `a069c29d8524f67ba75dde551778f30fefc89c9f41194bbea649532fba068141`
  - data fingerprint `19ebb69f8fcfb065d6eae832b70535a570b84f1938f7735ed78e788e174a5ea3`
- resume은 manifest/audio/data fingerprint와 model revision까지 일치해야 하며 changed-manifest 회귀 테스트로 재사용 차단을 확인했다.
- 1 sample × 3 modes CUDA smoke: PASS
- smoke false insertion: 모두 0
- 부분 smoke에서 stress group이나 hint target이 없을 때 요약기가 실패하던 문제를 발견해 빈 group/None metric 처리를 추가했다.

## 변경 파일

- configs/stt/real_user_prompt_hints.json
- backend/scripts/run_stt_real_user_prompt_ab.py
- backend/tests/test_stt_real_user_prompt_ab.py
- docs/experiments/stt/2026-09-28_large-v3-turbo-prompt-hotwords-ab.md
- docs/experiments/README.md
- docs/worklogs/README.md
- docs/worklogs/2026-09-28_1000_stt-prompt-hotwords-ab-prep.md

## 미실행 / 다음 작업

- 30건 full none / initial_prompt / hotwords A/B를 완료했다.
- initial_prompt: core CER 2.44%, WER 5.27%, term recall 94.12%, false insertion 0.
- hotwords: core CER 3.64%, WER 6.12%, stress WER 11.90%, term recall 94.12%, false insertion 0.
- none 기준은 core CER 3.29%, WER 6.63%, term recall 82.35%였다.
- initial_prompt를 다음 단계의 기본 후보로 두되, 고정 hint list가 아닌 실제 공고/포트폴리오 기반 동적 추출 전략을 설계한다.
- 이후 실제 공고/포트폴리오 기반 hint extraction 전략을 설계한다.
- 최종 후보는 새로운 acceptance 녹음셋에서 검증한다.
