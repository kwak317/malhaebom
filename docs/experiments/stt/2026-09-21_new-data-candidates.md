# STT new-data candidates

- Date: 2026-09-21
- Purpose: choose product-aligned new speech data for B1/B2 continuation experiments
- Product focus: regional job seekers, with the initial user pool concentrated in Busan/Gyeongsang, practicing interview answers alone
- Existing historical domain: AI Hub dataSetSn=119 Korean Gyeongsang dialect speech

## Selection principle

The next STT experiment should not optimize generic Korean ASR in isolation. The target is:

> recognize natural interview answers from Gyeongsang-region job seekers while retaining the current dialect robustness.

Therefore the data roles are separated.

1. **Regional/acoustic domain**: unused AI Hub 119 speech from product-like speakers
2. **Interview/content domain**: mock job-interview answers
3. Standard/general Korean corpora are supplementary only if later robustness work needs them

Historical clean train used for B2 replay is not counted as new data.

## P1 — AI Hub 119 unused product-persona pool

The currently available 119 label archives contain 8,542 source conversations. Existing train, validation, Test A and Test B use 864 unique conversations, leaving **7,678 unused source conversations**.

After excluding placeholder-style references, the unused pool contains:

- 1,998,758 clean utterances
- approximately 2,420.70 hours
- no source-conversation overlap with the historical train/validation/Test A/Test B source sets

### Product-persona filter

For each utterance, use the utterance speaker metadata and require:

- age: `20대`
- occupation: `학생` or `무직/취업준비생`
- placeholder-free transcription
- current residence in the selected region

For Busan/Ulsan/Gyeongnam:

- 2,950 source conversations
- 532,521 usable utterances
- approximately **629.03 hours**

For Busan/Ulsan/Gyeongnam/Daegu/Gyeongbuk:

- 4,411 source conversations
- 831,143 usable utterances
- approximately **983.27 hours**

The Southeast subset also contains many interview-adjacent everyday topics, including:

- 회사/학교: 23,810 utterances
- 꿈(목표): 16,941
- 자격증: 15,530
- 아르바이트: 15,037
- 성격: 14,201

Examples of previously unused conversations include 20대 students/job seekers in Busan/Ulsan/Gyeongnam discussing goals, part-time work and other experience-oriented topics.

### Interpretation

This pool is the preferred source of **new regional speech**. It does not require recycling the original 48k clean historical training rows.

The source-level split must remain disjoint. AI Hub speaker IDs in this corpus are local conversation IDs such as `1` and `2`, not a verified global speaker identity, so conversation/source disjointness can be guaranteed but cross-conversation real-speaker identity cannot be assumed from the ID alone.

Do not use all 629+ hours in the first experiment. Build a deterministic subset after deciding the initial hour/utterance budget and train/validation/test allocation.

## P2 — AI Hub 71592 채용면접 인터뷰 데이터

This dataset is a direct match for the product content domain: mock recruitment interviews with separate question and answer audio and literal answer transcripts.

The live AI Hub file tree separates data by:

- train / validation
- source / labeling data
- job category
- gender
- new / experienced applicant

The first acquisition is restricted to `05.ICT` + `New`.

### ICT New label inspection

Downloaded label files:

- `TL_05.ICT_Female_New.zip`
- `TL_05.ICT_Male_New.zip`
- `VL_05.ICT_Female_New.zip`
- `VL_05.ICT_Male_New.zip`

Local label QA:

- 5,840 valid JSON records
- 1 malformed training JSON record: `ckmk_d_ict_m_n_337139.json`
- 0 missing answer transcripts among valid records

Training labels:

- 5,193 valid interview answers
- approximately **131.13 answer hours**
- answer duration p10 56.2 s / median 87.0 s / p90 118.5 s
- 3,479 records are age range `-34`

Validation labels:

- 647 interview answers
- approximately **13.14 answer hours**
- answer duration p10 37.2 s / median 82.4 s / p90 89.9 s
- 470 records are age range `-34`

Question examples cover job motivation, role fit, conflict resolution, ICT skill-building effort, strengths/weaknesses, study habits, coding interests and similar interview topics.

### Validation source acquisition

To verify the source/label contract before downloading the full training audio, the ICT New validation source archives were downloaded:

- `VS_05.ICT_Female_New.zip`: 488,667,545 bytes
- `VS_05.ICT_Male_New.zip`: 854,977,623 bytes

Validation integrity check:

- 218 female + 429 male = 647 labels
- 436 female + 858 male = 1,294 WAV files, exactly question + answer audio for every label
- 0 missing audio references
- sampled WAVs are 16 kHz, mono, 16-bit
- answer audio totals approximately **13.15 hours**

The full ICT New training source archives were subsequently downloaded and the experiment was completed on 2026-09-22. The final preprocessing, split, training, retention, and sealed-test record is [AI Hub 71592 domain adaptation](2026-09-22_aihub71592-domain-adaptation.md).

### Role in the experiment

71592 has no verified regional-origin metadata in the inspected label structure. Treat it as the **interview-form/content adaptation source**, not as evidence of Gyeongsang dialect coverage.

## Recommended data composition direction

Keep the two new-data sources conceptually separate until a fixed experiment budget is chosen:

- **119 persona subset**: regional accent/dialect and target-user acoustic characteristics
- **71592 ICT New**: long-form interview answer structure and job-interview vocabulary

B1 should use only genuinely new data from these pools. B2 uses the exact same new-data set plus deterministic replay sampled from the historical placeholder-free clean train.

Do not let B1 and B2 use different new-data examples; otherwise replay effect cannot be isolated.

## Evaluation boundary

- new-domain validation/test must be fixed before training
- historical retention validation is used for replay/checkpoint decisions
- Test B is already inspected and remains final reporting only
- no model selection or replay-ratio selection from Test B

## Supplementary candidates

If later experiments show a need for broader standard-Korean robustness:

- Seoul Corpus / OpenSLR SLR113: spontaneous interview-style Seoul Korean, useful as a standard-speech supplement
- AI Hub dataSetSn=123: large spontaneous Korean corpus with self-introduction, school/company-life and related topics
- AI Hub general free-conversation corpora: useful for speaker diversity, not the first product-specific continuation

These are lower priority than the verified 119 + 71592 combination for the current product context.

## Historical next preprocessing step (completed)

This was the pre-training plan. The 71592 path below was completed on 2026-09-22; see the linked result document above.

Before training:

1. generate a deterministic 119 persona candidate manifest from only unused conversations
2. convert 71592 ICT New answer records into answer-only ASR manifests
3. define new train/validation/test boundaries and duplicate/leakage checks
4. fix the initial data-hour budget
5. then prepare identical B1/B2 new-data manifests, with replay added only to B2
