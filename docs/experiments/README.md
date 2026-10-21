# 실험 재현성과 STT/TTS 운영 규칙

[AGENTS.md](../../AGENTS.md)는 필수 운영 규칙의 진입점이고, 이 문서는 모델 학습·fine-tuning·benchmark·모델 비교의 상세 기록 및 재현 절차를 관리한다. 교육 참고는 [수업 지식](../knowledge/COURSE_KNOWLEDGE.md), 제품 평가 계획은 [evals](../../evals/README.md)를 따른다.

> 기존 1차 코드는 이관되었으며 [인수 전 정적 확인](2026-09-17_voice-asset-intake.md)을 기록했다. 신규 STT/TTS 학습은 원칙적으로 [프로젝트 제약](../CONSTRAINTS.md)상 MVP에서 제외다. 2026-09-19 사용자 승인으로 historical adapter weight 유실에 대응하는 [Whisper Medium STT retrain]([REDACTED].md)만 별도 실험 예외로 허용됐다. 이 예외는 제품 기본 모델 교체나 TTS 학습을 자동 승인하지 않는다.

후속 STT 실험은 [clean continuation — LR 2e-5, 0.5 epoch]([REDACTED].md)에 기록한다.

2026-09-22 AI Hub 71592 ICT/New 면접 도메인 적응, historical 119 replay 비교, retention 평가, sealed final test까지 완료한 결과는 [AI Hub 71592 domain adaptation](stt/2026-09-22_aihub71592-domain-adaptation.md)에 기록한다.

2026-09-23 GPT-6 Luna/Sol과 현재 Flash-Lite 기준선을 같은 canonical prompt/repair 조건으로 비교하는 실행 준비와 단계별 계획은 [GPT-6 Luna / Sol 후보 비교 실행 계획](2026-09-23_gpt6-luna-sol-evaluation-plan.md)에 기록한다.

2026-09-27 1인 화자 실사용 녹음 30건으로 B0와 C2를 비교하고 숫자·영문 발화형 정규화 보조 지표를 추가한 결과는 [실사용 녹음 STT 평가](stt/2026-09-27_real-user-recording-eval.md)에 기록한다.

2026-09-28 실사용 녹음 30건을 dev/diagnostic set으로 고정하고 large-v3-turbo/B0/C2 × beam 1/3/5를 동일 조건에서 비교한 결과는 [실사용 STT 모델 × beam 비교](stt/2026-09-28_real-user-model-beam-matrix.md)에 기록한다.

2026-09-28 large-v3-turbo + beam 1을 기준선으로 none / initial_prompt / hotwords를 비교한 결과는 [large-v3-turbo prompt / hotwords A/B](stt/2026-09-28_large-v3-turbo-prompt-hotwords-ab.md)에 기록한다.

2026-09-28 서비스 기본 CPU/int8과 기존 실험 CUDA/float16을 동일 model revision·beam·devset·initial_prompt 조건에서 비교한 결과는 [STT service-runtime parity](stt/2026-09-28_stt-runtime-parity.md)에 기록한다.

2026-09-28 실제 /analysis-jobs 업로드부터 terminal status까지 로컬 Docker와 Cloud Run에서 동일하게 측정한 실행 방법과 CPU scaling 결과는 [Analysis E2E benchmark](stt/2026-09-28_analysis-e2e-benchmark.md)에 기록한다.

2026-09-30 D4 사람 검토로 `coach-boundary-17`의 V ground truth가 변경된 뒤, 9/22 Flash-Lite 30건 × 3회 저장 결과를 provider 재호출 없이 다시 채점한 결과는 [D4 boundary-17 offline 재채점](2026-09-30_d4-boundary17-offline-regrade.md)에 기록한다.

2026-10-01 영문 v4 합성 응답 30건의 팀원 2명 평가와 사용자 확인 전 AI 초안은 [팀 품질 검토 취합](2026-10-01_coaching-v4-team-quality-review.md)에 기록한다. 평가 범위가 달라 공통 기준과 최종 점수는 확정 대기 상태다.

## 실험 기록 위치와 원칙

[2026-10-02 D10 운영 관측 가설](2026-10-02_d10-observability-hypotheses.md)은 이전 인증 실패 및 기록 Skill 버전 불일치를 관측·가설·운영 검증 조건으로 구분한다. [D11 공식 baseline 오프라인 준비](2026-10-02_d11-baseline-preflight.md)는 현 Dataset·카탈로그·결합 Prompt 해시와 기존 인젝션 감시 항목을 재현 가능한 사전점검으로 고정하되 새 실제 평가나 운영 배포를 수행하지 않는다.

[2026-10-02 평가 증거·누락 점검](2026-10-02_evaluation-evidence-gap-audit.md)은 기존 측정 원본과 `EVAL_REPORT.md` 4·6·7장의 출처를 연결하고, 사람 검토·운영 요청 증거·출시 게이트의 미확인 범위를 구분한다. 새 모델 실행 결과가 아니다.

최신 영문 v5와 이전 영문 v4의 동일 Skill 30건 실측·회귀·출시 게이트는 [2026-10-02 최신 영문 Prompt 비교](2026-10-02_latest-english-v5-comparison.md)에 기록한다.

의미 있는 실험마다 다른 팀원이 같은 실험을 다시 실행할 수 있도록 기록한다. 승인된 실험을 시작할 때 `docs/experiments/` 아래 목적을 식별할 수 있는 기록 파일을 만들고 [Worklog](../worklogs/README.md)와 연결한다. STT/TTS별 하위 디렉터리와 실제 artifact 구조는 필요할 때 확정한다. 이번에는 빈 `stt/`, `tts/`나 artifact 디렉터리를 만들지 않는다.

GUI에서 수동으로만 수행하고 재현 방법이 남지 않은 실험은 최종 결과로 취급하지 않는다. 가능한 경우 script, config, command 중 하나 이상의 재현 가능한 실행 방법을 제공한다. 미확인 값은 추정하지 않고 미확인으로 적고, CUDA 등 비해당 항목은 이유와 함께 N/A로 남긴다.

## 의미 있는 실험마다 기록할 최소 항목

| 영역 | 기록할 내용 |
| --- | --- |
| 목적·코드 | 실험 목적, 코드 branch/commit. 미커밋 변경으로 실행했다면 해당 diff와 재현 시 필요한 변경 식별 정보 |
| 실행 환경 | OS, Python, 주요 package version, CUDA, cuDNN, GPU |
| 모델 | model name, checkpoint 및 식별 가능한 버전/위치 |
| 데이터 | 출처, version/snapshot date, 데이터 개수, train/validation/test split, preprocessing |
| 학습·추론 | hyperparameters, inference parameters, random seed |
| 재현 | 실행 command, script, config의 경로와 사용법 |
| 평가 | metric과 정의, 평가 script |
| 결과 | 주요 수치, artifact/checkpoint 위치, 실패·특이사항 |

대형 모델/음성/학습 데이터 자체를 문서와 함께 Git에 넣지 않는다. 접근 권한·동의 범위를 지키면서 위치·버전·재현에 필요한 정보를 기록한다. 기록이 있다는 사실과 실험 성공·재현 완료는 구분한다.

## STT/TTS 수행 순서

```text
기존 자산 조사
→ 기존 환경 재구축
→ 기존 checkpoint benchmark 재현
→ baseline 확정
→ 신규 데이터 확보
→ 신규 데이터로 fine-tuning
→ 동일 benchmark 재평가
→ baseline과 비교
```

모델과 코드를 전달받았다는 이유만으로 추가 학습하지 않는다. 자산 조사도 별도 승인된 코드 이관/실험 범위에서 수행한다. 2026-09-19 STT retrain은 누락 adapter 조사와 dataset preflight를 완료한 뒤 승인된 별도 실험이다.

### 1. 기존 자산·환경 조사

다음을 먼저 조사한다.

- model/checkpoint
- Python version, dependency versions, CUDA/cuDNN
- preprocessing, training parameters, inference parameters
- dataset 구성, benchmark 방식, metric

가능한 한 기존 환경과 동일하게 재구축한다. 차이가 불가피하면 항목별 차이와 이유를 기록한다.

### 2. 추가학습 전 baseline 재현

반드시 기존 checkpoint로 기존 benchmark를 먼저 실행한다. 전달받은 모델이 정상인지, 기존 성능 기록이 재현되는지 확인하고 추가학습 비교용 baseline을 확보한다.

기존 기록과 재현 결과가 의미 있게 다르면 추가학습보다 원인 분석을 우선한다. 차이의 판단 근거와 환경·데이터·전처리·추론 설정·평가 구현의 확인 결과를 기록한다. 비교 가능한 baseline이 확정되지 않은 상태를 성공적인 개선으로 보고하지 않는다.

### 3. 신규 데이터와 누수 방지

- 기존 fine-tuning에 이미 사용한 train 데이터를 그대로 다시 넣어 추가 학습하지 않는 것을 기본 원칙으로 한다. 반복 학습의 overfitting, 데이터 누수, 일반화 성능 해석의 어려움을 피하기 위한 규칙이다.
- 다만 catastrophic forgetting 측정을 위한 명시적 replay 실험은 별도 결정 문서가 있고, historical train의 정제 subset만 deterministic sampling하며, historical validation/test를 섞지 않는 경우에 한해 예외로 허용할 수 있다. 현재 예외는 [2026-09-21 신규 데이터 + replay 실험 계획](stt/2026-09-21_new-data-replay-plan.md)을 따른다.
- 추가 fine-tuning에는 새롭게 확보한 데이터를 사용하고 dataset provenance를 남긴다.
- 기존 held-out test set, benchmark dataset, 최종 비교용 test set은 학습에 사용하지 않는다.
- 신규 데이터도 train / validation / test로 명시적으로 나눈다. 분할별 개수·출처·중복/누수 확인 결과를 기록한다.
- training / model selection은 **validation set**, final evaluation은 **test set**으로 수행한다. 최종 test 성능을 반복해서 보며 hyperparameter나 모델을 선택하지 않는다.

### 4. 동일 조건의 candidate 비교

가능한 한 test dataset, preprocessing, inference/decoding parameters, metric implementation, 평가 script를 동일하게 유지한다. hardware가 다르면 차이를 기록하고 지연/성능 비교 해석에 반영한다.

fine-tuning 실험마다 다음을 남긴다.

- baseline checkpoint / candidate checkpoint
- dataset provenance
- training config
- reproduce command/script
- metric
- baseline 대비 변화
- 대표 성공 사례 / 대표 실패 사례
- regression 여부

## CI와 실제 모델 검증의 관계

일반 PR gate와 heavy validation의 실행·다운로드·cache·timeout 정책은 [AGENTS.md](../../AGENTS.md)의 「GitHub Actions 자원 보호」를 따른다. mock/fixture 통과는 실제 STT/TTS 추론·GPU·full benchmark·fine-tuning의 검증을 대신하지 않는다. 실제 모델 검증 결과는 이 문서 체계의 실험 기록과 Worklog에 연결한다.
