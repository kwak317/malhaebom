# Worklog — STT persona + AI Hub 71592 continuation experiment

- 일시: 2026-09-22
- 작업자/에이전트: 김재훈 / ChatGPT
- 관련 이슈/PR: #51 → #52 → #53 → #54 → #55 → #56 → final documentation PR
- 관련 요구사항/결정: STT retrain 실험 예외, 신규 데이터 + 제한적 historical replay 비교

## 1. 목적

기존 clean-continuation Whisper Medium adapter에서 신규 persona 데이터와 AI Hub 71592 면접 데이터를 사용한 continuation 실험을 재현 가능하게 정리하고, retention 및 held-out 평가 결과를 문서화한다.

## 2. 작업 전 상태

- B0 clean-continuation adapter와 CT2 모델이 존재했다.
- AI Hub 119 historical clean validation/Test B와 신규 persona split이 준비돼 있었다.
- AI Hub 71592 ICT/New 원본 답변은 장문이라 Whisper 학습용 segmentation이 필요했다.
- 작업 시작 기준 commit은 과거 main이었고, PR 정리 시 최신 `origin/main`으로 이동하면서 최신 PR 정책을 반영했다.

## 3. 수행 내용

1. 신규 119 persona subset 및 80:20 historical replay 학습 조건을 구성했다.
2. persona validation/retention/test와 기존 Test B를 분리해 평가했다.
3. AI Hub 71592 ICT/New answer audio를 B0 timestamp anchor로 정렬·segment했다.
4. 71592-only C1과 20% replay C2를 동일 설정으로 학습했다.
5. 71592 validation + historical 119 retention으로 C2를 선택한 뒤 sealed 71592 test를 C2 한 조건에서만 열었다.
6. 실험 결과와 protocol limitation을 실험 문서/Decision Log에 기록했다.

## 주요 판단과 이유

- C2는 C1과 71592 validation 성능이 사실상 같고 historical retention 회귀가 더 작아 상대적 후보로 선택했다.
- C2도 B0보다 historical 119 성능이 나쁘므로 전역적으로 우수한 모델이라고 해석하지 않는다.
- 71592에 검증된 지역 출신 메타데이터가 없어 경상도 성능 개선 근거로 사용하지 않는다.
- final 71592 test는 공개 후 tuning에 재사용하지 않는다.
- PR은 최신 Review Core 정책에 따라 책임 단위 stacked PR로 분리한다.

## 4. 변경 파일

변경은 persona 데이터/학습, 평가 runner, 71592 acquisition/segmentation, 71592 continuation/evaluation, 실험 문서로 구성된다. 상세 파일 목록은 각 stacked PR description과 실험 문서 `docs/experiments/stt/2026-09-22_aihub71592-domain-adaptation.md`를 따른다.

## 5. 검증

- persona B1/B2 학습 및 retention/persona test/Test B 평가 완료
- 71592 segmentation: 5,840 records 요청, 32 reject, 27,056 segments 생성
- C1/C2 training preflight 및 full run 완료
- historical retention 4,802 utterances 평가 완료
- selected C2 final 71592 test 1,233 utterances 평가 완료
- C2 final test: CER 2.5876%, WER 9.7740%
- Python experiment scripts는 작성 당시 py_compile/preflight로 검증했으며 heavy GPU run 결과까지 확인했다.

## 6. 발견한 문제 / 남은 리스크

- 71592 split은 source-record ID disjoint지만 verified speaker-disjoint를 보장할 수 없다.
- C2는 B0 대비 historical retention 회귀가 남아 있다.
- 계획했던 material-regression numeric tolerance를 final test 공개 전에 별도 수치로 고정하지 못했다.
- final 71592 test는 이미 노출됐으므로 후속 replay-ratio tuning의 selection target으로 사용하면 안 된다.

## 미확인 사항

- C2를 제품 runtime default로 실제 채택하는 통합 결정은 수행하지 않았다.
- 70:30 replay가 historical forgetting을 더 줄일지는 평가하지 않았다.

## 7. 다음 작업

- stacked PR #51~#56과 final documentation PR을 팀 리뷰에 올리고 CI/PR policy를 확인한다.
- 팀 승인 후 작성자가 순서대로 merge한다.
- runtime STT 모델 교체가 필요하면 별도 통합 결정과 검증을 진행한다.

## 8. 2026-09-23 PR #51 review 대응

- `prepare_stt_new_persona_dataset.py --overwrite`가 임의의 넓은 `--output-root`를 재귀 삭제할 수 있다는 리뷰를 반영했다.
- 출력 경로는 `data/stt`의 **직접 자식**이면서 이름이 `new-persona-119-`로 시작하는 생성 데이터셋 디렉터리만 허용한다.
- 프로젝트 루트, `data/stt` 자체, AI Hub 원본 디렉터리, artifacts 등 다른 broad target은 삭제 전에 fail-closed 한다.
- 재귀 삭제 전에 동일 검증을 다시 수행해 호출자가 helper를 직접 호출해도 보호되도록 했다.
- 프로젝트 루트가 재귀 삭제 전에 거부되고 `shutil.rmtree`가 호출되지 않는 permanent unittest를 복구했다.

## 9. 2026-09-23 PR #56 review 대응

- sealed 71592 final-test가 C2 선택 고정 여부를 literal boolean만으로 표시하던 문제를 수정했다.
- `configs/stt/71592_c2_selection.json`을 frozen selection artifact로 추가해 선택 모델 ID, adapter SHA-256, CT2 fingerprint, C1/C2 validation trainer-state fingerprint와 고정 metric, historical retention comparison fingerprint를 기록한다.
- final-test runner는 이 selection artifact를 **sealed test manifest를 준비/열기 전에 먼저 검증**한다.
- artifact 부재, 경로 이탈, 선택 모델 불일치, adapter/CT2/validation/retention fingerprint 불일치가 있으면 모두 fail-closed 한다.
- selection 검증 성공, artifact 부재, retention 변조, selection-before-manifest 호출 순서를 임시 회귀 harness 4건으로 검증했고 4/4 PASS를 확인했다.
