# 2026-09-27 실사용 녹음 STT 평가

## 1. 목적

AI Hub 71592 면접 도메인 적응 후 선정한 C2 모델이 실제 말해봄 사용 조건에 가까운 개인 녹음에서도 기존 B0 clean continuation 대비 개선되는지 확인했다.

이번 평가는 1인 화자의 대본 낭독 30건으로 수행한 소규모 실사용 검증이다. 서비스 전체 사용자 성능이나 일반화 성능을 대표하지 않는다.

## 2. 데이터

- 녹음 수: 30개
- 파일 형식: M4A
- 대본: [실사용 평가 녹음 대본](assets/2026-09-27_real-user-recording-script.md)
- 데이터 보관: 로컬 Syncthing 공유 저장소
- Git 포함 여부: 음성 원본/ZIP 미포함
- ZIP 크기: 10,398,897 bytes
- ZIP SHA-256: c53c3161562a9b86ef5b5da27772eca0cc6dea7f1d80082e7e619c46fe5fbf39

실제 사용자 사례를 저장소에 자동 복제하지 않는 CONSTRAINTS.md의 데이터 규칙과 docs/experiments/README.md의 대형 음성 데이터 비커밋 원칙을 따른다.

| 구간 | 항목 | 목적 |
| --- | --- | --- |
| 일반 면접 | 01~10 | 자기소개, 지원 동기, 경험·협업 답변 |
| 기술 질문 | 11~18 | OS, 네트워크, DB, API, Docker, ML, STT, LLM |
| 숫자·영문 stress | 19~24 | 숫자, 날짜, 영문 기술용어, 약어 |
| 자연/긴 답변 | 25~30 | 추임새, 자기 수정, 반복, 장문 답변 |

## 3. 비교 모델과 추론 조건

| 항목 | B0 | C2 |
| --- | --- | --- |
| 역할 | clean continuation baseline | AI Hub 71592 + historical replay 20% |
| 로컬 CT2 artifact | artifacts/stt/whisper-medium-busan-qlora-clean-cont-lr2e-5-ct2 | artifacts/stt/71592-retention-models/c2-71592-replay20-ct2 |
| evaluator | backend/scripts/evaluate_stt_ct2.py | 동일 |
| language / task | ko / transcribe | 동일 |
| beam size | 5 | 5 |
| temperature | 0 | 0 |
| compute type | float16 | float16 |
| VAD filter | false | false |

기존 legacy-default CT2 경로는 현재 로컬에 남아 있지 않아 이번 30건 비교에서는 제외했다.

실행 환경은 직전 71592 실험과 같은 로컬 STT 환경을 사용했다.

- GPU: NVIDIA GeForce RTX 5070 Ti 16GB
- NVIDIA driver: 610.88
- STT runtime: repository .venvs/stt-runtime
- 추론 결과는 Git 제외 local-results/stt-real-eval-2026-09-27 아래에 보관했다.

## 4. Raw CER/WER

대본 텍스트를 그대로 reference로 두고 repository evaluator의 NFKC + 구두점 제거 정규화를 적용한 결과다.

| 모델 | CER | WER |
| --- | ---: | ---: |
| B0 clean | 16.03% | 19.59% |
| C2 71592 replay20 | 15.14% | 20.91% |

숫자·영문 stress 구간에서 1,233 → 천이백삼십삼, 2026 → 이천이십육, CER → 씨에알처럼 발화 내용은 맞지만 표기 형태가 다른 경우도 오류로 계산되어 전체 수치를 크게 올렸다.

19~24번을 제외한 24건 raw 결과:

| 모델 | CER | WER |
| --- | ---: | ---: |
| B0 clean | 9.41% | 13.05% |
| C2 71592 replay20 | 8.18% | 12.37% |

## 5. 발화형 정규화 보조 평가

backend/scripts/score_stt_spoken_form.py로 숫자 표기와 명백한 영문/한글 발음 표기만 같은 canonical token으로 변환했다.

정규화 예:

- 1,233 ↔ 천이백삼십삼
- 2026 ↔ 이천 이십육
- CER ↔ 씨에알
- Python ↔ 파이썬
- backend server ↔ 백엔드 서버

실제 오인식은 보정하지 않는다.

- Docker ↔ 덕허: 오류 유지
- WER ↔ 웨알: 오류 유지
- PR ↔ 피아리: 오류 유지

전체 결과:

| 모델 | Raw CER | 정규화 CER | Raw WER | 정규화 WER |
| --- | ---: | ---: | ---: | ---: |
| B0 clean | 16.03% | 13.91% | 19.59% | 15.03% |
| C2 71592 replay20 | 15.14% | 13.47% | 20.91% | 15.18% |

구간별 정규화 결과:

| 구간 | B0 CER | C2 CER | B0 WER | C2 WER |
| --- | ---: | ---: | ---: | ---: |
| 01~10 일반 면접 | 3.54% | 3.41% | 8.82% | 10.08% |
| 11~18 기술 질문 | 15.89% | 10.27% | 20.11% | 11.73% |
| 19~24 숫자·영문 stress | 33.66% | 37.72% | 36.90% | 46.43% |
| 25~30 자연/긴 답변 | 8.43% | 9.11% | 7.60% | 10.53% |
| 19~24 제외 24건 | 8.82% | 7.22% | 11.90% | 10.71% |

19~24를 제외한 면접형 24건에서 C2는 B0 대비 CER이 1.59%p, WER이 1.19%p 낮았다. 특히 기술 질문 11~18에서 C2의 개선 폭이 컸다.

## 6. 대표 관찰

17번 STT 지표 문장에서 B0는 CER, WER 발화를 과거 학습 데이터의 placeholder 형태인 &company-name...&으로 출력했다. C2는 씨에알, 더블유에알로 정상적인 발화형 전사를 생성했다.

19~24 stress 구간은 발화형 정규화 후에도 실제 기술용어 오인식이 남았다. 예시는 Docker → 덕허, JSON → 제이서, PR → 피아리 등이다. 따라서 이 구간은 일반 면접 성능과 합치기보다 영문·숫자 stress set으로 별도 추적한다.

## 7. 해석과 한계

- 30건 모두 동일 화자의 대본 낭독이므로 사용자 집단 전체로 일반화할 수 없다.
- 자유 발화가 아니라 대본 기반이라 실제 면접의 망설임·문장 재구성·발음 편차를 충분히 포함하지 않는다.
- 발화형 정규화는 보조 지표다. raw CER/WER를 대체하지 않고 함께 보고한다.
- 19~24 stress set은 일반 면접형 발화보다 의도적으로 어렵다.
- 이번 결과만으로 제품 기본 STT를 자동 교체하지 않는다. 기존 retention/final-test 근거와 함께 별도 runtime adoption 판단이 필요하다.

현재 근거에서 가장 제한적으로 말할 수 있는 수치:

> 1인 실사용 면접형 녹음 24건에서 C2는 발화형 정규화 기준 CER 7.22%, WER 10.71%를 기록했다.

## 8. 재현

각 모델의 evaluate_stt_ct2.py 출력 predictions.json들을 생성한 뒤 다음 명령 형태로 합산 재채점한다.

    python backend/scripts/score_stt_spoken_form.py \
      --predictions local-results/.../chunk-00/predictions.json \
      --predictions local-results/.../chunk-05/predictions.json \
      --predictions local-results/.../chunk-10/predictions.json \
      --predictions local-results/.../chunk-15/predictions.json \
      --predictions local-results/.../chunk-20/predictions.json \
      --predictions local-results/.../chunk-25/predictions.json

음성 원본은 저장소에 포함하지 않는다. 동일 데이터 확인이 필요한 경우 위 ZIP SHA-256과 로컬 보관본을 대조한다.
