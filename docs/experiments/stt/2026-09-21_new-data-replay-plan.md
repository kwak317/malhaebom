# STT new-data continuation with replay — experiment plan

- Date: 2026-09-21
- Status: completed on 2026-09-22
- Scope: approved STT experiment only; does not change the product default model

> Result: the AI Hub 71592 interview-domain continuation was completed. C2 (71592 + 20% historical clean 119 replay) was selected because it matched C1 on 71592 validation while reducing historical 119 regression. See [AI Hub 71592 domain adaptation result](2026-09-22_aihub71592-domain-adaptation.md).

## Motivation

The next request is to continue fine-tuning the current trained STT weight with newly acquired data while excluding the original training data. That request is useful as a direct baseline, but new-data-only continuation can move the LoRA weights toward the new domain and reduce performance on the previously learned domain.

To measure that risk instead of assuming either strategy is better, compare new-data-only continuation against a limited replay mixture of the cleaned historical training set.

## Fixed starting point

All continuation candidates start from the current clean-continuation best adapter:

`artifacts/stt/whisper-medium-busan-qlora-clean-cont-lr2e-5/best_adapter`

The current model is never overwritten. Every candidate writes to a separate output directory.

## Planned comparison

| ID | Initial weight | Training data | Purpose |
| --- | --- | --- | --- |
| B0 | current clean-cont best | no additional training | current baseline |
| B1 | current clean-cont best | new data 100% | direct interpretation of the requested continuation |
| B2 | current clean-cont best | new data + limited clean-old replay, target 80:20 sampling | measure forgetting mitigation |
| B3 | current clean-cont best | optional new data + clean-old replay, target 70:30 sampling | only if B1/B2 leave an unresolved trade-off |

B3 is not run by default. It is a follow-up only if the predeclared B0/B1/B2 comparison is insufficient.

## Replay boundary

Historical replay is a narrow exception to the normal rule that additional fine-tuning should use new data.

- replay source: placeholder-free historical clean train only
- do not replay historical validation, Test A, or Test B
- do not concatenate all 48k old rows blindly
- sample a deterministic subset per experiment so the intended new:old ratio is explicit
- record source IDs and random seed
- check duplicate audio/transcript/source overlap with the new dataset before training
- replay exists only to test retention; it is not a way to inflate the effective training set

## Evaluation design

Keep adaptation and retention measurements separate.

### New-domain evaluation

Split the newly acquired dataset into source-disjoint train / validation / test.

- training and checkpoint selection use new validation
- final new-domain performance uses new test
- the new test is not opened during hyperparameter selection

### Historical retention evaluation

Use a separate old-domain validation set for replay-ratio/checkpoint decisions. Do not use Test B to choose replay ratio or checkpoint.

The already inspected clean Test B remains a final reporting benchmark only. Because its results are already known, it must not become a tuning target.

## Selection rule

Do not select a candidate from a single metric on one domain.

Report at minimum:

- new validation/test CER and WER
- old-domain retention validation CER and WER
- final Test B CER and WER after the candidate is fixed
- character/word edit counts
- representative regressions

The intended decision rule is:

1. require a meaningful improvement on the new domain,
2. reject candidates with material old-domain regression,
3. among candidates satisfying both, prefer the simpler/lower-replay recipe.

The numeric tolerance for a "material" retention regression must be fixed before opening the new final test results.

## Initial training direction

Start conservatively:

- fresh optimizer
- LR 1e-5 to 2e-5
- 0.5 to 1.0 epoch
- deterministic sampling
- save/eval checkpoints during training
- do not overwrite B0 or previous experiment artifacts

The executed 71592 follow-up fixed LR=1e-5, 0.5 epoch, seed=45, and exact 80:20 new:old sampling for C2. The optional 70:30 condition was not run in this experiment round.

Candidate discovery and acquisition priority are tracked in [new-data candidates](2026-09-21_new-data-candidates.md).

The completed 71592 preprocessing, training, retention comparison, candidate selection, and sealed final-test result are recorded in [2026-09-22 AI Hub 71592 domain adaptation](2026-09-22_aihub71592-domain-adaptation.md).
