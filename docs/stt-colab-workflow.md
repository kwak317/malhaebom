# STT Colab 학습 워크플로 안정화

## 목적

Colab에서 Whisper-medium LoRA 학습을 재실행할 때 셀을 임의 순서로 실행해 발생하는 상태 누락과 데이터 경로 오류를 줄인다.

## 오늘 반영한 작업

- Windows ZIP 내부의 역슬래시 경로를 Colab 경로로 정규화하는 압축 해제 절차 정리
- `adapter_config.json`과 `adapter_model.safetensors`를 자동 탐색하도록 로드 단계 정리
- `processor` → `model` → CSV → Dataset → Collator → Trainer 순서 명시
- `metadata_train.csv`, validation/test CSV와 WAV 존재 여부를 학습 전에 검사
- train/validation/test 간 `segment_id` 중복 검사 추가
- WAV 경로가 CSV와 다를 때 파일명 기준으로 보조 검색하는 전처리 방식 정리
- 전처리 실패를 숨기지 않고 오류 파일을 확인할 수 있도록 진행률과 예외 출력 추가
- 런타임 재시작 후 처음부터 실행할 수 있는 수정 노트북 제공
- 경상도 방언 라벨링 JSON 압축 해제 및 전체 manifest 생성 절차 문서화

## 실행 순서

```text
GPU 확인
→ 패키지 설치
→ ZIP 업로드
→ 정규화 압축 해제
→ LoRA·processor 로드
→ CSV·데이터 계약 검사
→ Dataset 전처리
→ Collator
→ Trainer
→ 결과 저장
```

## 저장소 제외 항목

AI-Hub 원본 음성·라벨링 JSON·학습 WAV·모델 가중치는 저장소에 포함하지 않는다. 승인된 비공개 환경에서만 보관하며, 이 문서는 재현 절차와 검증 기준만 제공한다.

## 검증 상태

문서와 실행 절차 변경만 포함한다. 실제 학습 성능 평가는 고정 테스트셋에서 CER/WER, RTF, 실패율, 추임새 Recall/F1을 별도로 측정해야 한다.
