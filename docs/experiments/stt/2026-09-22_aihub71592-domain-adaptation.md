# AI Hub 71592 ICT/New interview-domain STT adaptation

- Date: 2026-09-22
- Status: completed
- Scope: STT experiment only; this result does not automatically replace the product default STT model
- Selected candidate: C2 — AI Hub 71592 + 20% historical clean 119 replay
- Starting point: clean-continuation B0 adapter

## 1. Goal

This experiment tests whether the existing Whisper Medium Gyeongsang-domain adapter can be adapted to recruitment-interview speech without unnecessarily losing the historical AI Hub 119 domain.

AI Hub 71592 is treated as an **interview/content-domain** source. Its inspected metadata does not provide verified regional-origin evidence, so this experiment does not claim improved Gyeongsang coverage from 71592 itself.

The predeclared comparison was:

| ID | Training data | Purpose |
| --- | --- | --- |
| B0 | no additional training | historical baseline |
| C1 | 71592 ICT/New only | direct interview-domain continuation |
| C2 | same 71592 data + historical clean 119 replay at exact 80:20 new:old | forgetting mitigation |

The optional higher-replay follow-up was not run. C2 preserved 71592 validation performance while reducing historical regression relative to C1, so this experiment round was closed with C2; whether a higher replay ratio could recover more historical performance remains unanswered.

## 2. Code state and environment

The experiment was executed on branch `feat/stt-persona-replay-eval` from an uncommitted working tree based on:

`fcc503ca3fa9f3e8ebd25ca6547aff70ab56039b`

The base commit does **not** contain all experiment scripts/configs by itself; reproducibility requires the corresponding working-tree changes or their later committed form.

Training environment:

| Item | Value |
| --- | --- |
| GPU | NVIDIA GeForce RTX 5070 Ti, 16,303 MiB |
| NVIDIA driver | 610.88 |
| Python | 3.12.3 |
| PyTorch | 2.8.0+cu128 |
| Transformers | 5.15.1 |
| PEFT | 0.20.0 |
| bitsandbytes | 0.48.0 |

## 3. AI Hub 71592 acquisition and QA

Scope was limited to `05.ICT` + `New` applicant data.

Label QA found:

- 5,840 valid JSON records
- 1 malformed training JSON record: `ckmk_d_ict_m_n_337139.json`
- 0 missing answer transcripts among valid records
- 5,193 valid training interview answers, approximately 131.13 answer hours
- 647 valid validation interview answers, approximately 13.14 answer hours

Question and answer audio are separate. Answer recordings are long-form, so they cannot be used directly as ordinary short Whisper training clips.

## 4. Alignment and segmentation

The segmentation pipeline uses the fixed B0 CTranslate2 model only as a timestamp/alignment anchor. Training labels remain the official AI Hub transcripts.

Key settings:

- alignment model: `artifacts/stt/whisper-medium-busan-qlora-clean-cont-lr2e-5-ct2`
- beam size: 1
- word timestamps: enabled
- minimum alignment coverage: 0.70
- target maximum segment length: 24 s
- neighboring segment boundaries use a shared midpoint

Final segmentation result:

| Item | Value |
| --- | ---: |
| records requested | 5,840 |
| records rejected | 32 |
| accepted records | 5,808 |
| total segments | 27,056 |
| train segments | 24,557 |
| validation segments | 1,266 |
| test segments | 1,233 |
| train hours | 130.501 |
| validation hours | 6.642 |
| test hours | 6.417 |

Rejected records were primarily low-alignment-coverage cases; two records hit a word-timestamp alignment error and were rejected instead of aborting the run.

One generated train segment exceeded the hard 24 s manifest filter and was excluded from fine-tuning. The final training manifest therefore contains 24,556 new-domain rows.

### Split boundary

- original AI Hub Training remains training
- original AI Hub Validation is deterministically split 50/50 by source record ID into validation and final test
- train / validation / test source IDs are disjoint
- the labels do not expose a verified global speaker ID, so speaker-disjointness cannot be guaranteed

This limitation must remain attached to any generalization claim.

## 5. Training manifests

Generated under `data/stt/aihub71592-domain-20260922/`.

| Split / mixture | Rows | Hours / ratio |
| --- | ---: | --- |
| C1 new train | 24,556 | 130.493 h |
| validation | 1,266 | 6.642 h |
| sealed test | 1,233 | 6.417 h |
| historical retention validation | 4,802 | separate old-domain validation |
| C2 new rows | 24,556 | 80% |
| C2 historical clean 119 replay | 6,139 | 20% |
| C2 combined train | 30,695 | exact 80:20 |

Replay rows come only from the placeholder-free historical clean training set. Historical validation and held-out test sets are not replayed.

## 6. Fine-tuning setup

Both candidates start from:

`artifacts/stt/whisper-medium-busan-qlora-clean-cont-lr2e-5/best_adapter`

Common settings:

- base model: `openai/whisper-medium`
- epochs: 0.5
- train batch size: 16
- eval batch size: 8
- gradient accumulation: 2
- effective train batch: 32
- learning rate: 1e-5
- warmup ratio: 0.03
- eval/save every 100 optimizer steps
- seed: 45
- fresh candidate output directories
- best checkpoint selected by validation CER

Configs:

- `configs/stt/finetune_71592_only_5070ti.json`
- `configs/stt/finetune_71592_replay20_5070ti.json`

## 7. 71592 validation result

Both runs improved through their final checkpoint, and the final checkpoint was the best checkpoint for each run.

| Candidate | Best step | CER | WER | Eval loss |
| --- | ---: | ---: | ---: | ---: |
| C1 — 71592 only | 384 / 384 | 2.9298% | 9.5594% | 0.123965 |
| C2 — 71592 + replay20 | 480 / 480 | **2.9290%** | **9.5510%** | **0.123964** |

The difference is too small to treat as a meaningful new-domain win. The useful finding is that adding 20% replay did **not** measurably sacrifice 71592 validation performance.

The 71592 test remained sealed at this stage.

## 8. Historical 119 retention result

C1 and C2 were converted to CTranslate2 and evaluated with the same decoder settings as B0:

- 4,802 historical clean validation utterances
- beam size: 5
- compute type: float16

| Model | CER | WER | ΔCER vs B0 | ΔWER vs B0 |
| --- | ---: | ---: | ---: | ---: |
| B0 clean | **5.9693%** | **15.3344%** | — | — |
| C1 — 71592 only | 6.5171% | 17.1378% | +0.5478 pp | +1.8034 pp |
| C2 — 71592 + replay20 | 6.4600% | 16.8062% | +0.4907 pp | +1.4718 pp |

Both 71592 continuations regress on the historical domain relative to B0.

However, C2 reduces the regression relative to C1 by approximately:

- 0.0571 percentage points CER
- 0.3317 percentage points WER

Because C1 and C2 are effectively tied on 71592 validation while C2 retains more historical performance, **C2 was selected before opening the 71592 final test**.

No 70:30 replay follow-up was run. Residual historical forgetting therefore remains an open limitation rather than a solved problem.

## 9. Final sealed 71592 test

After C2 selection was frozen, only C2 was evaluated on the sealed 1,233-utterance 71592 test split.

Decoder:

- beam size: 5
- compute type: float16

Final result:

| Metric | Value |
| --- | ---: |
| CER | **2.5876%** |
| WER | **9.7740%** |
| CER edits / units | 2,436 / 94,143 |
| WER edits / units | 3,361 / 34,387 |
| utterances | 1,233 |

The final test is now exposed. These results are reporting evidence only and must not be used to retune replay ratio, checkpoint, segmentation rules, learning rate, or other hyperparameters.

## 10. Decision

Select **C2 — 71592 + 20% historical clean replay** as the experimental interview-domain continuation candidate.

Reason:

1. C1 and C2 have effectively identical 71592 validation performance.
2. C2 has lower historical 119 regression than C1 on both CER and WER.
3. C2 therefore gives the better observed adaptation/retention trade-off among the tested recipes.
4. The final sealed 71592 test is consistent with the validation range and does not reveal an obvious domain-test collapse.

This is **not** a claim that C2 is globally better than B0. B0 remains better on the historical 119 retention set. The result instead establishes that, when interview-domain adaptation is desired, limited replay mitigates part of the forgetting caused by 71592-only continuation.

This decision also does not automatically change the product runtime/default model. Runtime adoption should be a separate product/integration decision.

### Protocol note

The replay plan stated that a numeric tolerance for a "material" retention regression should be fixed before the final new-domain test was opened. A separate numeric tolerance was not formalized before this run.

Therefore the C2 choice must be interpreted as a **relative choice among the tested C1/C2 conditions**, not as proof that its remaining regression is below a pre-approved production threshold. The final 71592 test has now been opened, so any future replay-ratio optimization such as 70:30 should not reuse this test as a model-selection target; a new untouched evaluation boundary would be needed for a clean follow-up.

## 11. Reproduction

Dataset segmentation:

```bash
make overnight-stt-71592-segment
```

Domain manifests:

```bash
make stt-71592-domain-manifests
```

Training preflight and run:

```bash
make stt-71592-c1-c2-preflight
make overnight-stt-71592-c1-c2
```

Historical retention:

```bash
make stt-71592-retention-preflight
make overnight-stt-71592-retention
```

Final test:

```bash
make stt-71592-final-test-preflight
make overnight-stt-71592-final-test
```

The final-test command is reproducible for auditing, but the test is already exposed and repeated runs must not become a tuning loop.

## 12. Primary artifacts

Dataset/manifests:

- `data/stt/aihub71592-ict-new-segmented/metadata.json`
- `data/stt/aihub71592-domain-20260922/metadata.json`
- `data/stt/aihub71592-domain-20260922/train.jsonl`
- `data/stt/aihub71592-domain-20260922/train-replay20.jsonl`
- `data/stt/aihub71592-domain-20260922/validation.jsonl`
- `data/stt/aihub71592-domain-20260922/test.jsonl`

Models:

- C1: `artifacts/stt/whisper-medium-71592-only-lr1e-5/best_adapter`
- C2: `artifacts/stt/whisper-medium-71592-replay20-lr1e-5/best_adapter`
- C2 CT2: `artifacts/stt/71592-retention-models/c2-71592-replay20-ct2`

Evaluation:

- `artifacts/stt/71592-retention/comparison.json`
- `artifacts/stt/71592-final-test/c2-replay20/metrics.json`
- `artifacts/stt/71592-final-test/c2-replay20/predictions.json`

Scripts:

- `backend/scripts/prepare_stt_aihub71592_segments.py`
- `backend/scripts/prepare_stt_71592_domain_manifests.py`
- `backend/scripts/run_stt_71592_c1_c2.py`
- `backend/scripts/run_stt_71592_retention.py`
- `backend/scripts/compare_stt_71592_retention.py`
- `backend/scripts/run_stt_71592_final_test.py`

## 13. Limitations

- 71592 provides interview-domain evidence, not verified regional-origin evidence.
- train/validation/test are source-record-ID disjoint, but verified speaker-disjointness is unavailable.
- automatic segmentation depends on B0-derived timestamp alignment, although official transcripts remain the labels.
- 32 source records were rejected during alignment and one >24 s generated train clip was filtered from training.
- C2 still regresses versus B0 on historical 119 validation; replay mitigates forgetting but does not eliminate it.
- the planned numeric material-regression tolerance was not separately fixed before the final test, so C2 selection is relative among tested candidates rather than threshold-qualified.
- the final 71592 test is now exposed and frozen for reporting only.
