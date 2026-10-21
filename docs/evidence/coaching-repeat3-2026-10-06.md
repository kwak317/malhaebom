# 최신 운영 배포 구성 코칭 반복 평가와 원본 결과 — 2026-10-06

## 실행 기준과 확인 범위

사용자 요청으로 최신 운영 배포 구성을 확인하고 합성 30건을 같은 조건으로 3회 새로 실행했다. [원본 자료](../../evals/results/2026-10-06-deployed-repeat3/README.md)에 입력·원본 응답 90건·manifest·summary·Prompt·Skill·SHA256을 저장했다.

- 운영 트래픽 100% revision: `malhaebom-mk2-resume-1004-1438`.
- 불변 이미지: `asia-northeast3-docker.pkg.dev/malhaebom-mk2-20261001/malhaebom/api@sha256:82b0cae6f08df6242f827f2b24791759e318c4a73b7cf6c0066e13caaa7bab75`.
- 모델: `google/gemini-3.5-flash-lite`.
- Prompt: `coaching-user-supplied-v4-verification`; Skill 기록 버전: `interview-coach-v6`; criteria: `problem-solving-v4-draft.3`.
- Prompt SHA256: `3584d0444545d7126ccbbe37b53b108842689c49717674c7a9dec9fbd5a96d99`.
- Skill SHA256: `b71ffd9b0f7809b4601e62e39b14e073f7d9b9596c1edd94dfc2650d593cf1e8`.
- Dataset SHA256: `1727d4b41df520489ce590e26a5f91aa9457b2589aee9be07fecbb5284c6f6ea`.
- 회차별 Prompt·Skill·Dataset·소스 해시·설정 동일. 새 GitHub 코드나 과거 평가 응답을 합치지 않았다.
- 각 회차 정상 12건·경계 10건·실패 유도 8건. 기대 정답은 모델 입력에서 제외했다.

이는 배포 이미지의 LLM provider·서버 출력 검증·복구 경로 실험이며 운영 사용자 HTTP/MCP/DB E2E나 새 사람 품질 평가가 아니다.

## 결과

| 회차 | 계약 통과 | intent/C/A/V 기대 판정 모두 일치 | 종합 자동 통과 | 실제 HTTP 호출 | 알려진 비용(USD) |
| --- | --- | --- | --- | --- | --- |
| 1 | 30/30 | 22/30 | 19/30 | 31 | $0.211939 |
| 2 | 30/30 | 21/30 | 18/30 | 31 | $0.111817 |
| 3 | 30/30 | 22/30 | 20/30 | 30 | $0.100372 |
| 합계 | 90/90 | 65/90 | 57/90 | 92 | $0.424128 |

종합 자동 통과는 계약·적용 가능한 판정·근거·자동 질문/행동 정책 검사를 모두 만족한 실행이다. 계약 성공을 코칭 의미 품질이나 사람 평가 통과로 바꾸지 않는다. 비용은 provider 응답에서 확인된 합계로 계정 전체 청구액이 아니다.

## 반복 안정성

- 3회 intent/C/A/V 판정이 모두 동일한 사례: **25/30**.
- 3회 모두 종합 자동 통과한 사례: **16/30**.
- 계약 복구가 발생한 사례 실행: **2건**; 계약 시도 **92회**; 실제 HTTP 호출 **92회**.
- 같은 오답도 반복 일치로 집계된다. 원문 코칭 문장 자체의 동일성은 측정하지 않는다.

| Case | 1회 자동 통과 | 2회 자동 통과 | 3회 자동 통과 | intent/C/A/V 동일 |
| --- | --- | --- | --- | --- |
| `coach-normal-01` | 통과 | 실패 | 통과 | 아니요 |
| `coach-normal-02` | 통과 | 통과 | 통과 | 예 |
| `coach-normal-03` | 통과 | 통과 | 통과 | 예 |
| `coach-normal-04` | 통과 | 통과 | 통과 | 예 |
| `coach-normal-05` | 통과 | 통과 | 통과 | 예 |
| `coach-normal-06` | 실패 | 실패 | 실패 | 예 |
| `coach-normal-07` | 실패 | 통과 | 통과 | 예 |
| `coach-normal-08` | 통과 | 통과 | 통과 | 예 |
| `coach-normal-09` | 실패 | 통과 | 통과 | 아니요 |
| `coach-normal-10` | 통과 | 통과 | 통과 | 예 |
| `coach-normal-11` | 통과 | 통과 | 통과 | 예 |
| `coach-normal-12` | 통과 | 통과 | 통과 | 예 |
| `coach-boundary-13` | 실패 | 실패 | 실패 | 예 |
| `coach-boundary-14` | 통과 | 통과 | 통과 | 예 |
| `coach-boundary-15` | 통과 | 통과 | 통과 | 예 |
| `coach-boundary-16` | 실패 | 실패 | 실패 | 예 |
| `coach-boundary-17` | 실패 | 실패 | 실패 | 예 |
| `coach-boundary-18` | 통과 | 통과 | 통과 | 예 |
| `coach-boundary-19` | 실패 | 실패 | 실패 | 아니요 |
| `coach-boundary-20` | 실패 | 실패 | 실패 | 아니요 |
| `coach-boundary-21` | 실패 | 실패 | 실패 | 예 |
| `coach-boundary-22` | 통과 | 통과 | 통과 | 예 |
| `coach-failure-23` | 통과 | 실패 | 통과 | 예 |
| `coach-failure-24` | 통과 | 통과 | 통과 | 예 |
| `coach-failure-25` | 통과 | 통과 | 통과 | 예 |
| `coach-failure-26` | 통과 | 통과 | 통과 | 예 |
| `coach-failure-27` | 실패 | 실패 | 실패 | 예 |
| `coach-failure-28` | 통과 | 실패 | 실패 | 아니요 |
| `coach-failure-29` | 통과 | 통과 | 통과 | 예 |
| `coach-failure-30` | 실패 | 실패 | 실패 | 예 |

## 피드백에 대한 처리와 한계

- **단일 실행:** 동일 배포 구성·동일 30건을 새로 3회 실행해 반복 결과와 판정 변동을 공개했다. 3회만으로 광범위한 안정성·품질 우위를 확정하지 않는다.
- **raw 결과가 저장소 밖:** 원본 JSONL 3개와 입력·설정·해시·집계가 PR의 추적 파일에 포함된다. merge 전에는 PR branch의 증거이며 main 반영과 구분한다.
- [운영 trace·과거 사람 평가](observability-human-evaluation-2026-10-06.md)는 별도 실행이다. 과거 사람 점수를 이번 90건의 점수로 재사용하지 않았다.
- 새 출력 사람 평가, 실제 사용자 E2E, R/D 및 공고 관련성 평가·운영 배포는 수행하지 않았다.
