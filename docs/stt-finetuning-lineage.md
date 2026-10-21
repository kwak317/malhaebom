# 말해봄 STT 파인튜닝 전·후 비교 리포트

## 1. 문서 목적

이 문서는 말해봄 Mk.2에서 수행한 Whisper 기반 STT 파인튜닝의 계보와 각 단계의 평가 결과를 한 곳에서 확인할 수 있도록 정리한다.

개별 실험의 원본 기록과 재현 절차를 대체하지 않는다. 세부 설정, 실행 로그, artifact 경로와 평가 파일은 각 실험 문서를 source of truth로 사용한다.

또한 이 문서는 **모델 파인튜닝**과 **서비스 추론 최적화**를 명확히 구분한다.

- 파인튜닝 계보: Whisper Medium 기반 LoRA/QLoRA 학습과 면접 도메인 적응
- 서비스 추론 최적화: large-v3-turbo의 beam, initial_prompt, hotwords, runtime 비교

서비스 기본 STT 모델 변경은 파인튜닝 실험의 자동 결과가 아니다.

## 1-1. 비교 결론과 기존 모델의 차이

**50k 재학습과 데이터 정제에서 고정 평가셋의 전사 오류를 줄였고, B0 → C2 면접 도메인 추가 학습은 기술 질문에서 개선됐다. 그러나 C2는 전체 녹음 30건의 WER와 기존 방언 도메인 retention에서 B0보다 나빴다.** 최종 C2의 채용면접 test 결과는 CER **2.5876%**, WER **9.7740%**다. 모든 발화에서 개선됐다는 결론은 내리지 않는다.

| 항목 | 기존 1차 프로젝트 | 현재 재학습 계보 |
| --- | --- | --- |
| 기본 모델 | openai/whisper-medium | openai/whisper-medium |
| 학습 방식 | LoRA, 1k → 5k continuation | 새 50k QLoRA → clean continuation(B0) → 면접 적응(C2) |
| 데이터 규모 | 누적 6,000 segment | 119 train 50,000 → clean 48,000; 71592 신규 24,556 + replay 6,139 |
| LoRA 설정 | q_proj/v_proj, rank 16, alpha 32 | 동일 target/rank/alpha; 단계별 학습률·epoch 변경 |
| 평가 체계 | 독립 평가 및 원본 medium 대비 정량 비교 미완료 | 고정 holdout 500, Test B 500, 면접 final test 1,233, 1인 대본 녹음 30건 |
| 기존 도메인 보존 | 별도 retention 측정 없음 | C1/C2 retention 비교; C2에 clean 119 replay 20% |
| 후속 학습 계보 | 이후 인계에서 원 adapter 누락 확인 | 새 계보의 adapter·CT2·선택 설정을 B0/C2로 구분 |

학습 단계의 데이터는 중복 사용되므로 위 숫자를 합쳐 고유 데이터 총량으로 계산하지 않는다. 1차 프로젝트의 adapter 보관 기록과 이후 인계에서의 누락 확인은 서로 다른 시점이다.

## 1-2. 파인튜닝 전·후 비교표

여기서 **‘전’은 해당 추가 학습 단계의 기준 모델**이다. 이미 학습한 Legacy CT2·50k·B0를 미학습 Whisper Medium 원본으로 해석하지 않는다. 아래 각 행은 같은 평가셋·채점 방식·추론 조건으로 비교한 결과이며, 변화는 `후 − 전`의 **퍼센트포인트(%p)**다. CER/WER는 낮을수록 좋다.

| 추가 학습 / 평가셋 | 전 → 후 | CER 전 → 후 | CER 변화 | WER 전 → 후 | WER 변화 |
| --- | --- | --- | ---: | --- | ---: |
| 50k QLoRA / holdout 500 | Legacy CT2 → 50k | 9.1435% → 8.2708% | -0.8727%p | 16.1931% → 16.2937% | +0.1006%p |
| 데이터 정제 continuation / Test B 500 | 50k → B0 | 5.6038% → 5.3738% | -0.2300%p | 13.5489% → 13.1213% | -0.4276%p |
| 면접 적응 / 녹음 30건 raw | B0 → C2 | 16.03% → 15.14% | -0.89%p | 19.59% → 20.91% | +1.32%p |
| 면접 적응 / 녹음 24건 raw (stress 제외) | B0 → C2 | 9.41% → 8.18% | -1.23%p | 13.05% → 12.37% | -0.68%p |
| 면접 적응 / 녹음 24건 발화형 정규화 | B0 → C2 | 8.82% → 7.22% | -1.60%p | 11.90% → 10.71% | -1.19%p |
| 면접 적응 / 기술 질문 8건 발화형 정규화 | B0 → C2 | 15.89% → 10.27% | -5.62%p | 20.11% → 11.73% | -8.38%p |
| 면접 적응 / 기존 119 validation 4,802 | B0 → C2 | 5.9693% → 6.4600% | +0.4907%p | 15.3344% → 16.8062% | +1.4718%p |

변화는 문서에 표시된 반올림 수치로 계산했다. 원 실험의 미반올림 값에서 계산한 근사 변화와 마지막 자릿수가 다를 수 있다. 기술 질문 8건은 24건의 부분집합이며 별도 독립 평가가 아니다.

**원본 medium → 기존 6k 및 기존 6k → 최종 C2의 동일 test 직접 비교 결과는 확보되지 않았다.** 따라서 그 비교의 개선율은 계산하지 않는다. C2 final test 1,233건에는 같은 test의 B0 결과가 보고되지 않아, C2 2.5876%를 B0 Test B 5.3738%와 비교해 개선율을 계산할 수 없다.

### CER/WER와 정규화의 의미

- CER: `(문자 치환 + 삭제 + 삽입) / 정답 문자 수 × 100`; 공백을 제외한다.
- WER: `(단어 치환 + 삭제 + 삽입) / 정답 단어 수 × 100`; 공백 기반 단어 경계를 사용한다.
- 데이터 전체의 edit와 unit을 합산한 비율이며 발화별 오류율의 단순 평균이 아니다.
- raw도 NFKC·구두점 제거·공백 정리 등 기본 전처리를 적용한다. 발화형 정규화는 숫자·영문과 명백한 한글 발음 표기를 추가로 통일한 **보조 지표**다. 실제 기술용어 오인식을 정답으로 바꾸지는 않는다.

## 1-3. 출처 대조와 확인 범위 (2026-10-09)

사용자가 제공한 「STT 파인튜닝 전·후 비교 분석」과 [Drive 인계 폴더](https://drive.google.com/drive/folders/1soqPlnBbmYWWgycaXIv6jU72IkXhcURF)를 기존 저장소의 실험 기록과 대조했다. 이번 작업은 리포트 작성이며 새 학습·추론·서비스 배포를 수행하지 않았다.

| 출처 | 확인 내용 | 이 리포트에서의 역할 |
| --- | --- | --- |
| 사용자 첨부 비교 문서 | 기존 6k부터 C2까지 학습 단계와 주요 평가 수치 | 비교 구성의 출발점; 정규화 구분은 원 실험으로 보완 |
| [Drive 인계 가이드](https://docs.google.com/document/d/1oO-jzj8gu7rLKJ6gDYPKm8D0aqUKUU6ok4LWS2-alnA/edit) | B0/C2 구분, 지표, 공통 추론 조건, 인계 범위 | 실험 모델과 서비스 기본 모델의 경계 확인 |
| [Drive README](https://docs.google.com/document/d/1kV-jpOn3oo_xyLjuxTbR-L6VX0vMtRPn/edit) | B0 best step 500, C2 best step 480, ZIP 크기·공개 체크섬·설정 | 전달된 모델의 식별·재현 정보 |
| Drive ARCHIVE-SHA256SUMS.txt | B0/C2 ZIP의 게시된 SHA256이 README와 일치 | 게시 정보 대조; 다운로드본 무결성 검증과 구분 |
| 저장소 실험·선택 기록 | 아래 단계별 문서, [C2 선택 JSON](../configs/stt/71592_c2_selection.json) | 수치·평가셋·정규화·선택 근거 확인 |

폴더에서 B0-Clean-Continuation.zip·C2-Interview-Domain.zip을 확인했다. README의 크기는 각각 1,555,782,541 bytes·1,555,790,246 bytes다. **이번에는 ZIP 전체 다운로드·내부 파일 해시 검증·모델 로드를 수행하지 않았다.** 인계 가이드의 완료 안내를 수신자의 실행 검증 완료로 바꾸지 않는다.

첨부 문서의 면접형 24건 CER 7.22%/WER 10.71%와 기술 질문 CER 10.27%/WER 11.73%는 원 실험에서 **발화형 정규화 결과**다. raw 지표로 표기하지 않으며, 기준이 다른 평가셋끼리 직접 순위를 만들지 않는다.

## 2. 전체 계보

```text
openai/whisper-medium
  └─ Legacy 6k LoRA
       ├─ 1차 1,000 segment
       └─ 2차 5,000 segment
            ↓
       adapter weight 인계 누락
            ↓
  └─ 50k QLoRA retrain
       └─ AI Hub 119 경상도 train 50,000 / validation 5,000
            ↓
  └─ Clean continuation (B0)
       └─ placeholder 제거 train 48,000 / validation 4,802
            ↓
  └─ AI Hub 71592 interview-domain adaptation
       ├─ C1: 71592 only
       └─ C2: 71592 80% + historical clean 119 replay 20%
            ↓
       experimental candidate: C2
```

별도의 서비스 추론 최적화 계보는 다음과 같다.

```text
large-v3-turbo
  → model × beam 비교
  → initial_prompt / hotwords A/B
  → dynamic initial_prompt
  → CPU/int8 ↔ CUDA/float16 runtime parity
```

이 경로는 모델 가중치를 변경하는 파인튜닝이 아니라 추론 조건과 서비스 통합을 최적화한 작업이다.

## 3. Legacy: Whisper Medium 6,000개 LoRA

기존 말해봄 STT 기록에는 `openai/whisper-medium`을 부산·경상도 방언 면접 음성에 LoRA로 적응한 이력이 남아 있다.

### 학습 구성

| 항목 | 값 |
| --- | --- |
| base model | `openai/whisper-medium` |
| 데이터 | 부산·경상도 방언 면접 음성 |
| 1차 학습 | 1,000 segment |
| 2차 학습 | 5,000 segment |
| 누적 | 6,000 segment |
| LoRA target | `q_proj`, `v_proj` |
| rank / alpha | 16 / 32 |
| dropout | 0.05 |
| learning rate | 1e-4 |
| epoch | 각 단계 1 |
| 환경 | Google Colab Tesla T4 / FP16 |

2차 학습은 1차 LoRA 결과를 시작 adapter로 사용했다.

### 계보 한계

이 단계의 CTranslate2 추론 모델은 남아 있었지만, 이후 추가 학습에 필요한 `adapter_model.safetensors`가 원 STT Drive와 최신 handoff에서 확인되지 않았다.

따라서 후속 작업에서는 legacy 모델을 baseline artifact로 보존하고, 기존 adapter를 복구하거나 역변환했다고 주장하지 않은 상태에서 새로운 retrain 계보를 시작했다.

관련 기록:

- [STT 6,000개 파인튜닝 기록](stt-finetuning-6000.md)
- [STT 재학습 실험 Spec](specs/stt-finetuning-retrain.md)

## 4. AI Hub 119 기반 50k QLoRA retrain

### 목적

legacy LoRA adapter가 누락되어 정확한 continuation이 불가능했기 때문에, AI Hub 119 경상도 데이터의 handoff manifest를 재구성하고 같은 `openai/whisper-medium`에서 새 QLoRA candidate를 학습했다.

### 데이터와 누수 통제

| Split | 규모 |
| --- | ---: |
| Train | 50,000 |
| Validation | 5,000 |
| Final holdout | 500 utterances |

train/validation 간 audio, segment, source overlap은 모두 0으로 검증했다.

Final holdout은 AI Hub 공식 Validation archive에서 현재 train/validation source와 겹치지 않는 source 20개를 선택하고 source당 25 utterance로 학습 전에 고정했다.

### 학습 설정

| 항목 | 값 |
| --- | --- |
| base model | `openai/whisper-medium` |
| quantization | 4-bit NF4 + double quantization |
| LoRA target | `q_proj`, `v_proj` |
| rank / alpha / dropout | 16 / 32 / 0.05 |
| train batch | 16 |
| eval batch | 8 |
| gradient accumulation | 2 |
| effective batch | 32 |
| epochs | 2 |
| learning rate | 1e-4 |
| warmup ratio | 0.05 |
| seed | 42 |
| model selection | validation CER |
| GPU | RTX 5070 Ti 16GB |

Full training은 3,126 optimizer step / 2 epoch를 완료했다.

Validation best는 checkpoint-3000이었다.

- CER: **8.5512%**
- WER: **20.2180%**

### 고정 holdout 500개 결과

동일 500 utterance, beam size 5, temperature 0, previous-text conditioning off, VAD off, CTranslate2 float16 조건으로 비교했다.

| 지표 | Legacy CT2 baseline | 50k retrain CT2 | 변화 |
| --- | ---: | ---: | ---: |
| CER | 9.1435% | **8.2708%** | -0.8727%p |
| WER | **16.1931%** | 16.2937% | +0.1006%p |

CER edit는 901 → 815로 86건 감소했다. 반면 WER edit는 644 → 648로 4건 증가했다.

WER 악화 사례에는 `따로국밥 ↔ 따로 국밥`, `즐겨 보고 ↔ 즐겨보고`처럼 문자 내용은 같지만 한국어 띄어쓰기 경계가 다른 경우가 포함됐다.

따라서 이 단계에서는 **문자 단위 내용 보존은 개선됐지만 whitespace-sensitive WER는 사실상 비슷했다**고 해석했다.

관련 기록:

- [Whisper Medium 50k QLoRA retrain](experiments/stt/2026-09-19_whisper-medium-50k-retrain.md)
- [AI Hub STT 119 데이터 준비 및 재구성](AIHUB_DATA_DOWNLOAD.md)

## 5. Placeholder 제거와 Clean Continuation

### 문제 발견

50k 데이터의 일부 transcript에는 다음과 같은 익명화 placeholder가 포함돼 있었다.

```text
#이름#
&company-name...&
```

실제 음성에서는 이름이나 회사명을 발음하지만 정답 text가 placeholder로 남아 있을 수 있어, 실제 발화와 학습 label의 불일치가 발생할 가능성이 있었다.

실제 평가에서도 legacy 학습 흔적으로 보이는 placeholder 출력 사례가 확인됐다.

### 데이터 정제

원본 manifest는 유지하고 placeholder가 들어간 row만 제외한 별도 clean manifest를 만들었다.

| Split | 원본 | Clean |
| --- | ---: | ---: |
| Train | 50,000 | 48,000 |
| Validation | 5,000 | 4,802 |

기존 Test A는 이미 확인했기 때문에, 원 train/validation과 Test A source까지 모두 제외한 새 Test B 500 utterance를 학습 전에 별도로 고정했다.

### Continuation 설정

50k retrain best adapter를 시작점으로 짧은 저학습률 continuation을 수행했다.

| 항목 | 값 |
| --- | --- |
| init adapter | 50k retrain best adapter |
| learning rate | 2e-5 |
| epochs | 0.5 |
| train batch | 16 |
| eval batch | 8 |
| gradient accumulation | 2 |
| effective batch | 32 |
| warmup ratio | 0.03 |
| seed | 43 |

750/750 step을 완료했고 best checkpoint는 checkpoint-500이었다.

Clean validation:

- CER: **7.4092%**
- WER: **19.6174%**

### Clean Test B 500개 결과

세 모델을 동일한 decoding 조건으로 비교했다.

| 모델 | CER | WER |
| --- | ---: | ---: |
| Historical baseline | 5.8024% | 13.7894% |
| 50k retrain | 5.6038% | 13.5489% |
| **Clean continuation (B0)** | **5.3738%** | **13.1213%** |

Clean continuation은 50k retrain 대비:

- CER: **-0.2300%p**
- WER: **-0.4276%p**

Historical baseline 대비:

- CER: **-0.4286%p**
- WER: **-0.6681%p**

학습 중 model selection에 사용하지 않은 Test B에서도 CER/WER가 모두 개선돼, 이후 면접 도메인 적응의 baseline을 이 clean continuation 모델(B0)로 사용했다.

관련 기록:

- [STT clean continuation — LR 2e-5, 0.5 epoch](experiments/stt/2026-09-21_clean-continuation-lr2e-5.md)

## 6. AI Hub 71592 채용면접 도메인 적응

### 목적과 데이터 의미

다음 단계에서는 말해봄의 실제 사용 목적과 더 가까운 **채용면접 답변 도메인**에 STT를 적응시키는 실험을 진행했다.

AI Hub 71592 ICT/New 지원자 답변을 사용했다.

이 데이터는 면접/content domain 적응용이다. 확인한 metadata만으로 지역 출신을 검증할 수 없기 때문에 **71592 결과를 경상도 음성 성능 개선 근거로 사용하지 않는다.**

### Segmentation

원본 answer audio는 장문이므로 B0 CTranslate2의 timestamp를 alignment anchor로 사용해 Whisper 학습용 segment로 분할했다. 학습 label은 AI Hub 공식 transcript를 그대로 사용했다.

최종 결과:

| 항목 | 값 |
| --- | ---: |
| accepted records | 5,808 |
| total segments | 27,056 |
| train segments | 24,557 |
| validation segments | 1,266 |
| test segments | 1,233 |
| train hours | 약 130.50 h |
| validation hours | 약 6.64 h |
| test hours | 약 6.42 h |

24초 hard filter를 초과한 train segment 1개를 제외해 실제 신규-domain fine-tuning manifest는 **24,556 row**다.

### C1 / C2 비교

B0 clean continuation adapter에서 두 후보를 동일 설정으로 추가 학습했다.

| 후보 | 학습 데이터 | 목적 |
| --- | --- | --- |
| C1 | AI Hub 71592 only | 직접 면접 도메인 적응 |
| C2 | 71592 80% + historical clean 119 replay 20% | catastrophic forgetting 완화 |

C2 train 구성:

- 71592 new rows: 24,556
- historical clean replay rows: 6,139
- combined: 30,695
- 정확한 new:old 비율: 80:20

공통 설정:

| 항목 | 값 |
| --- | --- |
| base model | `openai/whisper-medium` |
| init adapter | B0 clean continuation |
| epochs | 0.5 |
| learning rate | 1e-5 |
| train / eval batch | 16 / 8 |
| gradient accumulation | 2 |
| effective batch | 32 |
| warmup ratio | 0.03 |
| seed | 45 |
| model selection | validation CER |

## 7. 71592 Validation과 Historical Retention

### 71592 validation

| Candidate | CER | WER | Eval loss |
| --- | ---: | ---: | ---: |
| C1 — 71592 only | 2.9298% | 9.5594% | 0.123965 |
| **C2 — 71592 + replay20** | **2.9290%** | **9.5510%** | **0.123964** |

두 후보는 신규 면접 도메인 validation에서 사실상 동률이었다.

### AI Hub 119 historical retention

동일한 historical clean validation 4,802 utterance에서 평가했다.

| 모델 | CER | WER |
| --- | ---: | ---: |
| **B0 clean** | **5.9693%** | **15.3344%** |
| C1 — 71592 only | 6.5171% | 17.1378% |
| C2 — 71592 + replay20 | 6.4600% | 16.8062% |

C1과 C2 모두 B0보다 historical domain에서 회귀했다. 따라서 replay가 catastrophic forgetting을 제거한 것은 아니다.

다만 C2는 C1 대비 historical regression을 줄였다.

- CER regression 완화: 약 0.0571%p
- WER regression 완화: 약 0.3317%p

71592 validation이 사실상 동률인 상태에서 historical retention이 더 나았기 때문에, sealed final test를 열기 전에 **C2를 실험 후보로 선택**했다.

이는 C2가 B0보다 전역적으로 더 좋은 STT라는 의미가 아니다. 71592 train/validation/test의 source ID는 분리했지만 검증된 전역 speaker ID가 없어 화자 독립성은 보장하지 못한다.

## 8. Sealed 71592 Final Test

C2 선택을 고정한 뒤에만 1,233 utterance final test를 열었다.

| Metric | Result |
| --- | ---: |
| CER | **2.5876%** |
| WER | **9.7740%** |
| CER edits / units | 2,436 / 94,143 |
| WER edits / units | 3,361 / 34,387 |
| utterances | 1,233 |

이 final test는 이미 공개됐기 때문에 이후 replay ratio, checkpoint, segmentation, learning rate 등의 tuning target으로 재사용하지 않는다.

관련 기록:

- [AI Hub 71592 interview-domain STT adaptation](experiments/stt/2026-09-22_aihub71592-domain-adaptation.md)

## 9. 실제 말해봄 사용 조건에 가까운 30건 녹음 평가

C2가 AI Hub 평가뿐 아니라 실제 말해봄 사용 조건에 가까운 음성에서도 개선되는지 확인하기 위해 1인 화자의 대본 낭독 30건을 별도로 평가했다.

구성:

- 일반 면접 01~10
- 기술 질문 11~18
- 숫자·영문 stress 19~24
- 자연/긴 답변 25~30

### 전체 raw 결과

| 모델 | CER | WER |
| --- | ---: | ---: |
| B0 clean | 16.03% | **19.59%** |
| C2 replay20 | **15.14%** | 20.91% |

숫자와 영문 표현은 `1,233 ↔ 천이백삼십삼`, `CER ↔ 씨에알`처럼 의미는 맞지만 표기 형태가 달라 raw CER/WER에 크게 반영됐다.

### 발화형 정규화 보조 평가

| 모델 | normalized CER | normalized WER |
| --- | ---: | ---: |
| B0 clean | 13.91% | **15.03%** |
| C2 replay20 | **13.47%** | 15.18% |

숫자·영문 stress 6건을 제외한 면접형 24건 **발화형 정규화 결과**:

| 모델 | CER | WER |
| --- | ---: | ---: |
| B0 clean | 8.82% | 11.90% |
| **C2 replay20** | **7.22%** | **10.71%** |

특히 기술 질문 11~18 **발화형 정규화 결과**:

| 모델 | CER | WER |
| --- | ---: | ---: |
| B0 clean | 15.89% | 20.11% |
| **C2 replay20** | **10.27%** | **11.73%** |

그 밖의 발화형 정규화 결과도 함께 보고한다.

| 구간 | B0 CER → C2 CER | B0 WER → C2 WER |
| --- | --- | --- |
| 일반 면접 10건 | 3.54% → 3.41% | 8.82% → 10.08% |
| 숫자·영문 stress 6건 | 33.66% → 37.72% | 36.90% → 46.43% |
| 자연/긴 답변 6건 | 8.43% → 9.11% | 7.60% → 10.53% |

개선이 기술 질문에 집중됐고, stress·자연/긴 답변 및 일반 면접 WER는 악화됐다. 숫자·영문 표기 차이만으로 모든 악화를 설명하지 않는다.

이 결과는 1인 화자의 대본 낭독 30건에 한정된 소규모 검증이므로 서비스 전체 사용자 성능이나 일반화 성능을 대표하지 않는다. 기존 30건은 후속 설정 탐색에도 사용된 dev/diagnostic set으로, 신규 독립 acceptance set을 대체하지 않는다.

관련 기록:

- [2026-09-27 실사용 녹음 STT 평가](experiments/stt/2026-09-27_real-user-recording-eval.md)

## 10. 최종 해석

파인튜닝 실험에서 확인한 흐름은 다음과 같다.

1. Legacy 6k LoRA는 부산·경상도 면접 음성 적응 이력을 제공하지만 adapter 누락으로 exact continuation이 불가능했다.
2. AI Hub 119 50k/5k를 재구성해 새로운 QLoRA 계보를 만들었고 고정 holdout에서 CER를 개선했다.
3. placeholder row를 제거한 clean continuation은 별도 Test B에서 CER/WER를 모두 개선했다.
4. AI Hub 71592 면접 데이터로 적응했을 때 C1/C2의 신규 도메인 성능은 거의 같았다.
5. historical clean replay 20%를 포함한 C2가 C1보다 기존 domain forgetting을 완화했다.
6. sealed 71592 test에서 C2는 CER 2.5876%, WER 9.7740%를 기록했다.
7. 실제 말해봄 사용 조건에 가까운 1인 30건 검증에서는 특히 기술 질문 구간에서 C2가 B0보다 낮은 CER/WER를 기록했다.

하지만 C2는 historical retention에서 B0보다 여전히 나쁘므로, **C2를 전역적으로 더 우수한 STT 모델로 일반화하지 않는다.**

## 11. 서비스 STT 추론 최적화와의 구분

파인튜닝 이후 실제 서비스 후보를 비교하는 과정에서는 `faster-whisper large-v3-turbo`가 별도의 기준선으로 평가됐다.

이후 수행한 다음 작업은 파인튜닝이 아니다.

- large-v3-turbo / B0 / C2 model × beam 비교
- `initial_prompt` / `hotwords` A/B
- 공고·질문 문맥 기반 dynamic initial prompt
- CPU/int8 ↔ CUDA/float16 runtime parity
- Cloud Run CPU benchmark

따라서 다음 두 결론을 섞지 않는다.

- **파인튜닝 실험 결론**: Whisper Medium 계보에서는 B0 → C2로 면접 도메인 적응 가능성과 replay를 통한 forgetting 완화를 확인했다.
- **서비스 추론 결론**: 실제 runtime 모델 선택은 large-v3-turbo를 포함한 별도 model/beam/prompt/runtime 평가 근거로 판단한다.

현재 제품 기본 STT 모델과 runtime은 이 문서의 파인튜닝 결과만으로 자동 변경하지 않는다.

## 12. 관련 문서

- [STT 6,000개 파인튜닝 기록](stt-finetuning-6000.md)
- [STT 재학습 실험 Spec](specs/stt-finetuning-retrain.md)
- [Whisper Medium 50k QLoRA retrain](experiments/stt/2026-09-19_whisper-medium-50k-retrain.md)
- [STT clean continuation](experiments/stt/2026-09-21_clean-continuation-lr2e-5.md)
- [AI Hub 71592 interview-domain adaptation](experiments/stt/2026-09-22_aihub71592-domain-adaptation.md)
- [실사용 녹음 STT 평가](experiments/stt/2026-09-27_real-user-recording-eval.md)
- [STT 현재 상태](stt-current-status.md)
- [STT 실험 목록](experiments/README.md)
