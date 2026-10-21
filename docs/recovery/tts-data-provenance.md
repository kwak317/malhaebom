# TTS source-data provenance recovery

## 목적

이 문서는 과거 `proj1-b`의 Qwen3-TTS 파일럿에서 사용했던 원천 음성을 복구·추정한 과정을 정리한다.

이번 작업은 새 TTS 데이터를 만드는 작업이 아니라 다음 두 모델의 **AI Hub 원천 화자와 fine-tuning corpus provenance를 가능한 범위까지 복구하는 작업**이었다.

- `candidate_04_questioner`
- `candidate_01_coach`

대상 데이터셋은 AI Hub 71592 `채용면접 인터뷰 데이터`이며, 질문 음성 `ckmk_q_*.wav`의 면접관 화자를 분석했다.

> `gender`, `ageRange`, `occupation`, `experience`는 레코드의 지원자 metadata이며 질문 음성을 말하는 면접관의 성별/연령 metadata가 아니다.

## 최종 결론

### 확정도가 높은 내용

- `candidate_04_questioner`는 AI Hub 71592의 익명 면접관 화자 cluster A와 일치한다.
- `candidate_01_coach`는 cluster A와 구분되는 익명 면접관 화자 cluster B와 일치한다.
- 두 화자는 여러 직군, 지원자 성별, 연령대, 경력 구분을 넘나들며 반복 등장한다.
- Validation/Training에서 추출한 상위 매칭 음성을 직접 청취해 각각 같은 화자임을 확인했다.
- surviving checkpoint 두 개는 모두 Qwen3-TTS 12Hz 0.6B Base 기반 custom-voice model이다.
- 과거 프로젝트 기록에는 두 모델 모두 1 epoch pilot fine-tune으로 남아 있다.
- 두 모델의 `spk_id`는 모두 `3000`이지만 화자 차이는 token row 하나가 아니라 fine-tuned weight 전반에 존재한다.
- surviving model artifact에는 `trainer_state.json`, training arguments, checkpoint step 등 exact training subset을 복구할 metadata가 남아 있지 않다.

### 가장 그럴듯한 원래 작업 방식

1. AI Hub 71592 질문 음성에서 면접관 화자 후보를 찾는다.
2. 각 후보 화자의 여러 발화를 묶어 single-speaker corpus를 만든다.
3. Qwen3-TTS 0.6B Base를 후보별로 1 epoch fine-tuning한다.
4. 생성 결과를 직접 청취해 후보를 비교한다.
5. `candidate_04_questioner`를 questioner용으로 선택하고, `candidate_01_coach`를 임시 coach voice로 사용한다.

정확히 어떤 WAV들이 원래 1 epoch 학습에 들어갔는지는 현존 자료로 확정할 수 없다.

## 화자 복구 결과

### Validation source cluster

Questioner 내부 pairwise cosine:

- min `0.991458`
- mean `0.993095`
- max `0.995035`

Coach 내부 pairwise cosine:

- min `0.990261`
- mean `0.992978`
- max `0.996204`

Questioner ↔ Coach cross cosine:

- min `0.969443`
- mean `0.975368`
- max `0.979662`

두 그룹은 각각 매우 응집된 동일 화자 cluster이며 서로는 구분되는 것으로 판단했다.

### Training pilot

작은 Training archive 8개에서 질문 음성 2,309개를 embedding했다.

- threshold `0.988`: Questioner 28개 / Coach 13개
- threshold `0.982`: Questioner 69개 / Coach 37개
- `0.980`까지 낮춰도 69/37이 유지됐다.

### Experienced 전체 14개 archive

총 질문 음성 9,167개를 분석했다.

Questioner target cluster:

- size `206`
- target centroid score `0.995994`
- other-role score `0.985499`
- 14/14 Experienced archive에 등장

Coach target cluster:

- size `66`
- target centroid score `0.994953`
- other-role score `0.983720`
- 11/14 Experienced archive에 등장

`0.982` global clustering은 전체 화자 지도에서는 일부 과병합이 보여 target A/B 복구 이후에는 seed matching으로 전환했다.

### Seed threshold calibration

Experienced 9,167개를 대상으로 recovered target centroid를 seed로 사용했다.

`cosine >= 0.991`에서:

- Questioner: target 171/206 검출, non-target 0/8,961 오탐
- Coach: target 61/66 검출, non-target 0/9,101 오탐

따라서 New archive 탐색은 `0.991`을 high-confidence threshold로 사용했다.

### New archive 3개 pilot

대상:

- Design Male New
- RND Female New
- ICT Female New

총 질문 음성 5,252개를 분석했다.

추가 high-confidence match:

- Questioner 42개
- Coach 17개

`0.989 <= cosine < 0.991`은 relaxed 후보로만 기록했다.

## 현재 복구된 source pool

Training label metadata와 조인 가능한 recovered pool:

### Questioner A

- 248 rows
- 약 54.74분
- Experienced 206
- scanned New high-confidence 42

### Coach B

- 83 rows
- 약 16.82분
- Experienced 66
- scanned New high-confidence 17

이 숫자는 원래 학습 샘플 수가 아니다. 전체 New archive를 전부 scan하지 않았기 때문에 실제 동일 화자 발화는 더 있을 수 있고, 원래 fine-tuning은 이 recovered pool의 일부만 사용했을 수도 있다.

현재 local-only recovered manifests:

```text
.cache/aihub71592/recovered_tts_sources/
├── README.md
├── questioner_recovered_manifest.csv
└── coach_recovered_manifest.csv
```

AI Hub 원천/전사 데이터를 저장소에 올리지 않기 위해 위 CSV는 `.cache`에만 유지한다.

## Label metadata에서 확인한 패턴

현재 조인된 Questioner 248개와 Coach 83개는 모두 `date = 20230116`이다.

- Questioner는 7개 직군에 걸쳐 있다.
- Coach는 6개 직군에 걸쳐 있다.
- 지원자 남녀 모두 존재한다.
- 여러 age range가 존재한다.
- Experienced/New 모두 존재한다.
- Questioner 질문 248/248이 exact text 기준 모두 고유하다.
- Coach 질문 83/83도 exact text 기준 모두 고유하다.
- ID가 가까운 작은 묶음은 있으나 전체 범위에는 넓게 분산돼 있다.

따라서 특정 직군, applicant gender, archive, 연속 ID range, 반복 질문 template만으로 원래 subset을 설명하는 증거는 없다.

## Exact training membership 추정 시도

surviving Base checkpoint와 fine-tuned checkpoint를 이용해 teacher-forced loss membership pilot을 수행했다.

- Questioner: Training 후보 20 + 동일 화자 Validation control 4
- Coach: Training 후보 20 + 동일 화자 Validation control 4
- 총 48 samples

비교 지표:

```text
delta = base_loss - finetuned_loss
```

| Role | Metric | Training candidates | Validation controls |
| --- | --- | ---: | ---: |
| Questioner | recipe delta mean | 1.799 | 1.860 |
| Questioner | explicit delta mean | 0.593 | 0.617 |
| Coach | recipe delta mean | 2.090 | 2.305 |
| Coach | explicit delta mean | 0.683 | 0.671 |

Training 후보와 same-speaker Validation control이 의미 있게 분리되지 않았다. 따라서 loss signal만으로 exact training WAV membership을 추정하는 것은 신뢰하기 어렵다고 판단했고 여기서 중단했다.

## 보존한 핵심 스크립트

위치:

```text
scripts/recovery/tts_provenance/
```

- `recheck_aihub71592_top_archives_multi_sample.py`: Validation source 후보 재검증 및 Qwen speaker encoder helper
- `scan_aihub71592_training_centroid.py`: Validation source centroid로 Training 질문 음성 scan
- `cluster_aihub71592_interviewers.py`: 질문 음성 embedding을 interviewer cluster로 grouping
- `extend_aihub71592_interviewer_scan.py`: Experienced 14개 archive까지 embedding/cache 확장
- `scan_aihub71592_new_seeded.py`: recovered A/B seed로 New archive 직접 scan
- `analyze_71592_target_metadata.py`: recovered WAV와 Training label metadata 조인/분석
- `run_tts_membership_loss_pilot.py`: Base vs fine-tuned teacher-forced loss membership pilot
- `finalize_tts_recovered_sources.py`: recovered source pool 최종 통계와 local-only manifest 생성

## 재현 시 필요한 추가 요소

- AI Hub API key
- `backend/scripts/aihub_download_common.py`
- Qwen3-TTS Python environment
- local Qwen3-TTS 0.6B Base checkpoint
- `models/tts/questioner_candidate04/model_or_adapter`
- `models/tts/coach_candidate01/model_or_adapter`

중간 산출물과 AI Hub 원천/라벨 데이터는 `.cache/aihub71592/` 아래 local-only로 유지한다.

## 작업 종료 기준

> 원래 fine-tuning에 사용한 exact WAV subset은 복구하지 못했지만, 두 모델의 원천 면접관 화자는 높은 신뢰도로 복구했고, 재현 가능한 same-speaker source pool과 분석 절차를 확보했다.

따라서 TTS 데이터 provenance 추정 및 인계용 데이터 준비 작업은 이 상태에서 종료한다.
