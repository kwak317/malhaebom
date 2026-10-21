# STT 6,000개 파인튜닝 기록

## 요약

- 기본 모델: `openai/whisper-medium`
- 방식: LoRA 파인튜닝
- 데이터: 부산·경상도 방언 면접 음성
- 학습 구성: 1차 1,000개 + 2차 5,000개
- 총 학습 세그먼트: 6,000개
- 실행 환경: Google Colab Tesla T4, FP16
- 결과물: LoRA adapter와 학습 로그는 비공개로 보관

## LoRA 설정

```text
target_modules = q_proj, v_proj
r = 16
lora_alpha = 32
lora_dropout = 0.05
learning_rate = 1e-4
epochs = 1 per batch
```

각 단계는 별도 출력 폴더에서 실행했으며, 2차 학습은 1차 LoRA 결과를 시작 어댑터로 사용했습니다.

## 저장·배포 정책

원본 음성, AI-Hub 라벨링 데이터, 체크포인트와 `adapter_model.safetensors`는 저장소에 포함하지 않습니다. 데이터 이용 승인 범위와 팀 내부 보관 정책에 따라 별도 전달합니다. 저장소에는 재현에 필요한 설정·실행 방법·평가 계획만 기록합니다.

## 검증 계획

서비스 모델을 확정하기 전에 고정된 동일 테스트셋으로 다음을 비교해야 합니다.

1. `faster-whisper large-v3-turbo`
2. `openai/whisper-medium` 기본 모델
3. `whisper-medium` 6,000개 LoRA 모델

측정 지표는 한국어 공백 제외 CER, WER, RTF, 실패율과 `음`·`어` 추임새 event Precision/Recall/F1입니다. 현재 학습 개수와 손실만으로 서비스 모델의 우수성을 확정하지 않습니다.

## 재현 안내

비공개 환경에서 데이터 ZIP과 adapter를 준비한 뒤 `openai/whisper-medium`을 로드하고, 동일한 전처리·greedy decoding 설정으로 평가합니다. 대용량 데이터와 가중치는 GitHub PR에 업로드하지 않습니다.

## 작업 경과 보고 (2026-08-18)

### 완료한 작업

1. 1차 `openai/whisper-medium + LoRA` 학습 결과를 확인했습니다.
2. 1차 결과물(`부산_LoRA_전달용_1epoch.zip`)에서 adapter와 학습 CSV를 복구했습니다.
3. 2차 학습용 `busan_continuation_5000.zip`을 Colab에 업로드했습니다.
4. Windows ZIP 경로가 Colab에서 파일명으로 합쳐지는 문제를 확인하고, 역슬래시를 슬래시로 정규화하는 압축 해제 로직을 적용했습니다.
5. 2차 학습 노트북의 중복 셀로 인해 발생하던 `NameError`, 빈 Dataset, Collator 초기화 오류를 정리한 수정 노트북을 생성했습니다.
6. 2차 파인튜닝 결과는 `whisper_medium_busan_lora_batch2_1epoch.zip`으로 저장했습니다.
7. 3차 데이터 준비를 위해 경상도 방언 라벨링 JSON을 압축 해제하고 전체 manifest를 생성했습니다.

### 2차 학습 결과

| 항목 | 결과 |
|---|---:|
| 2차 신규 학습 세그먼트 | 5,000개 |
| 누적 학습 세그먼트 | 6,000개 (1차 1,000 + 2차 5,000) |
| 학습 epoch | 1 |
| 학습 환경 | Google Colab Tesla T4, FP16 |
| 기본 모델 | `openai/whisper-medium` |
| 학습 방식 | LoRA (`q_proj`, `v_proj`) |

### 현재 상태와 남은 작업

- 3차 데이터 ZIP은 아직 완성되지 않았습니다.
- 1·2차 전체 `segment_id` 목록을 하나의 CSV로 복구하지 못해 3차 중복 검사는 보류 중입니다.
- 3차 학습 전에는 반드시 새 5,000개 WAV, `metadata_train.csv`, validation/test CSV를 함께 생성해야 합니다.
- 최종 모델 선정 전 `large-v3-turbo`, 기본 medium, 6,000개 LoRA 모델의 CER/WER·RTF·추임새 Recall/F1을 동일 테스트셋에서 비교해야 합니다.

### 산출물 보관 원칙

AI-Hub 원본 음성·라벨링 JSON·학습 WAV·LoRA 가중치는 비공개 로컬/승인된 저장소에서만 보관합니다. 이 PR에는 학습 설정과 진행 기록만 포함합니다.
