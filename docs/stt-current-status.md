# STT 현재 상태

> 2026-09-17 정적 audit 정정: VAD·전달력은 현재 분석 service에 결합되어 있다. 아래 미결합 설명과 loss 수치는 이전 작업 시점 기록이다. 현재 근거와 인수 제한은 [음성 인수 기록](experiments/2026-09-17_voice-asset-intake.md)을 따른다.


## 서비스 기준 후보

- 런타임: `faster-whisper==1.2.1`
- 모델: `large-v3-turbo`
- 출력: 한국어 전사문, 구간·단어 타임스탬프, 처리시간, RTF, 독립 토큰 `음`·`어`의 횟수와 위치
- 현재 범위: Worker 내부 전사 모듈과 CLI, 표준 결과 계약, API 분석 Job, 단위 테스트

`faster-whisper` 내부 VAD는 끄고, 후속 Silero VAD가 같은 입력의 발화 구간을 계산한다. API 분석 Job은 이 결과로 CPM·긴 침묵·반복 표현을 계산하고 우선순위가 높은 피드백을 최대 2개 선택한다. 실제 GPU 모델의 최종 품질 비교는 아래 LoRA 관문과 별개로 남아 있다.

## Whisper-medium LoRA 1 epoch 관문

부산 방언 파일럿으로 `openai/whisper-medium`에 LoRA를 적용한 1 epoch 실행 결과를 확인했다.

| 항목 | 확인값 |
|---|---:|
| 학습 발화 | 300개 |
| 검증 발화 | 50개 |
| epoch | 1 |
| LoRA rank / alpha | 16 / 32 |
| 대상 모듈 | `q_proj`, `v_proj` |
| 최종 checkpoint | `checkpoint-19` |
| train loss | 5.1789 |
| eval loss | 3.9790 |
| 학습 시간 | 144.3869초 |

최종 adapter와 checkpoint 존재는 확인했지만 다음 검증은 아직 끝나지 않았다.

- 고정 test 100개에서 기본 medium과 LoRA의 CER·WER 비교
- `음`·`어` 사건 단위 Precision·Recall·F1 비교
- 표준어·면접 음성 성능 저하 여부 확인
- 동일 GPU·디코딩 조건의 RTF·GPU 메모리·실패율 비교
- LoRA 병합 후 CTranslate2 변환 및 faster-whisper 재로드 확인

따라서 이 결과만으로 파인튜닝 모델이 더 좋거나 서비스 모델로 선정됐다고 판단하지 않는다.

## 저장소에 포함하지 않는 산출물

- AI-Hub 원본·파생 WAV와 전사 CSV
- LoRA `adapter_model.safetensors`
- Whisper checkpoint와 모델 캐시
- 테스트 음성과 전사 결과 원문

위 산출물은 승인된 비공개 저장소나 팀 GPU 환경에서 별도 관리한다. 저장소에는 비민감 집계 결과와 재현 가능한 코드·설정만 남긴다.
