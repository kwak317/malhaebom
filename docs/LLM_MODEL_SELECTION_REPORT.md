# 말해봄 LLM 4종 선정 근거: 비용·속도·품질 비교

작성일: 2026-10-09. 현재 모델을 역할별로 **현재 사용하지 않는 대안**과 비교한다. 선정 이유는 확인된 유지 근거이며, 과거 의사결정 당시의 의도를 소급 확정하지 않는다. 새 유료 평가·모델 교체·배포는 수행하지 않았다.

## 1. 현재 운영과 비교 범위

운영 기준은 `malhaebom-mk2-request-trace-linkage-1009`(트래픽 100%)이며, 이미지 digest는 `sha256:fbfb2840cd3d3190d321cfb2a2c86af8931f5970cdca8e884ceaa31fc17b7465`다. 해당 이미지의 모델 상수와 운영 환경 설정을 대조했다. Git main 및 아래 과거 평가의 버전과 구분한다.

| 현재 LLM | 담당 | 운영 설정·소스 근거 |
| --- | --- | --- |
| Gemini 3.5 Flash Lite | 본 면접 코칭; 별도 override 없는 공고 요구사항 분석 | `COACHING_LLM_MODEL=google/gemini-3.5-flash-lite` |
| Claude Haiku 5.5 | 자유채팅의 요청 해석·응답·행동 제안 | 운영 `free_chat.py`의 `MODEL`; 자유채팅·준비 대화 활성화 |
| Gemini 3.1 Flash Lite | README·이력서 정보 분석 | 운영 `github_readme_analysis.py`의 `MODEL_NAME`; resume에서 같은 상수 import |
| Gemini 3.1 Pro Preview | STT 결과 텍스트의 전사 정규화 | 운영 `transcript_normalization.py`; reasoning low, max_tokens 5000 |

공고 검색은 `JOB_SEARCH_PROVIDER=playmcp_tavily`의 MCP·검색 경로다. **Gemini 3.8 Flash는 현재 사용 LLM에 포함하지 않는다.** Whisper Medium C2는 음성→텍스트 STT이며, 네 번째 LLM은 그 이후의 텍스트 보정이다. 각 요청이 네 모델을 모두 호출하는 구조가 아니다.

## 2. 비용 계산과 증거 해석

가격은 10/9 [OpenRouter 모델 API](https://openrouter.ai/api/v1/models)의 비캐시 텍스트 입력/출력 단가다. [가격 snapshot](../evals/results/llm-selection-20261009/catalog.json)에 원본 단가·지원 파라미터·조회일·계산값을 보존했다. USD 기준이며 결제·검색·이미지·음성·캐시·재시도 비용은 별도다.

| 모델 | 입력 $/100만 token | 출력 $/100만 token | 입력 2,000 + 출력 500 token 예시 |
| --- | ---: | ---: | ---: |
| Gemini 3.5 Flash Lite | 0.30 | 2.50 | $0.001850 |
| Claude Haiku 5.5 | 0.10 | 0.50 | $0.000450 |
| Gemini 3.1 Flash Lite | 0.25 | 1.50 | $0.001250 |
| Gemini 3.1 Pro Preview | 2.00 | 12.00 | $0.010000 |
| GPT-5.6 Luna | 0.20 | 1.20 | $0.001000 |
| GPT-5.6 Terra | 2.00 | 12.00 | $0.010000 |
| Claude Haiku 4.5 | 1.00 | 5.00 | $0.004500 |
| GPT-4.1 Mini | 0.40 | 1.60 | $0.001600 |
| Gemini 2.5 Flash Lite | 0.10 | 0.40 | $0.000400 |

계산식은 `입력 token×입력 단가/1,000,000 + 과금 출력 token×출력 단가/1,000,000`이다. Haiku 5.5는 입력 100,000 token부터 API snapshot의 상위 단가가 적용되며, Pro의 장문 요율도 실제 provider 견적을 확인해야 한다. 추론 token까지 출력으로 과금될 수 있어 표의 짧은 예시를 실제 호출 평균이나 월 청구액으로 해석하지 않는다.
속도는 **프로젝트 완료 시간 실측**과 **공개 provider p50 latency/생성 throughput**을 나눈다. 공개 수치는 서로 다른 요청·provider·추론 설정의 관측값으로, 서비스 완료 시간이나 동일 조건 순위가 아니다. 품질은 계약 통과, 의미 정확성, 사람 평가, 실제 저장 성공을 구분한다. 지원 기능·제조사 설명만으로 한국어 면접 품질 우위를 확정하지 않는다.

## 3. 본 코칭: Gemini 3.5 Flash Lite

[9/21 Final Four](experiments/2026-09-21_openrouter-final-four.md)의 합성 30건 비교는 dataset·Prompt·Skill·schema를 고정했다. 생성 설정은 각 모델 default라 추론량까지 동일하지 않으며, 최신 운영 품질 평가도 아니다.

| 후보 | 완료 p50 / p95 | 당시 알려진 30건 비용 | 계약 결과·품질 해석 |
| --- | ---: | ---: | --- |
| **현재: Gemini 3.5 Flash Lite** | 3.41 / 4.20초 | $0.10706534 | 30/30; 사람 의미 품질 우위는 미확정 |
| 대안: GPT-5.6 Luna | 9.36 / 13.77초 | $0.03914948 | 29/30; validator 위반 1건 |
| 대안: GPT-5.6 Terra | 1.18 / 8.29초 | ≥$0.10570740 | 10/30; 20건 schema/integration 실패, 의미 품질 실패로 단정 금지 |

**유지 근거:** Luna보다 당시 총비용은 약 2.73배였으나 완료 p50은 약 2.75배 짧고 계약은 30/30이었다. 면접 직후 기다리는 코칭에는 응답 지연과 계약 안정성을 우선하는 선택이 타당하다. Terra의 빠른 p50에는 실패 경로가 섞여 있어 정상 응답 속도 우위로 사용할 수 없다.
**한계:** 가장 싼 모델을 고른 것은 아니다. [10/6 반복 평가](evidence/coaching-repeat3-2026-10-06.md)는 계약 90/90이지만 종합 자동 통과 57/90이었다. 모델 자체가 코칭 품질을 보장하지 않으며 Prompt·근거 검증·사람 검토가 필요하다. Luna는 비용 절감 재평가 후보이고, Terra는 통합 실패를 해결한 뒤 다시 비교해야 한다.

## 4. 자유채팅: Claude Haiku 5.5

| 후보 | 공개 p50 latency / throughput 사례 | 같은 token 예시 비용 | 품질 근거 |
| --- | --- | ---: | --- |
| **현재: Haiku 5.5** | Anthropic 1.78초 / 150 token/s | $0.000450 | 로컬 150회 평가 기록 있음; 대안과 품질 A/B 없음 |
| 대안: Haiku 4.5 | Azure 0.66초 / 77 token/s | $0.004500 | 대화 후보; 우리 동의·단계·저장 계약 미검증 |
| 대안: GPT-4.1 Mini | OpenAI 0.86초 / 75 token/s | $0.001600 | 공식 instruction following·tool calling·구조화 출력 지원; 프로젝트 미검증 |

출처: [Haiku 5.5](https://openrouter.ai/anthropic/claude-haiku-5.5), [Haiku 4.5](https://openrouter.ai/anthropic/claude-haiku-4.5), [GPT-4.1 Mini 관측](https://openrouter.ai/openai/gpt-4.1-mini), [OpenAI 공식 설명](https://developers.openai.com/api/docs/models/gpt-4.1-mini). 10/9 Standard provider 행의 사례이며 최저지연 endpoint를 골라 만든 순위가 아니다.
**선정 근거:** 짧은 요청을 반복하는 채팅의 표준 예시 비용은 Haiku 4.5보다 90%, GPT-4.1 Mini보다 약 72% 낮다. 요청 해석·짧은 응답 생성에 쓰고 실제 동의·저장·전환은 서버가 검증하므로, 고가 범용 모델을 모든 턴에 쓰는 대신 저렴한 모델을 제한된 역할에 두는 구성이 합리적이다.
**품질·속도 한계:** [에이전트 리포트](AGENT_REPORT.md)의 Haiku 후속 로컬 실행은 150회 중 오류 미검출 147회, 186 calls, $0.2187281이다. 다른 후보보다 대화 품질이 좋다는 증거도, 147회 기능 실행 성공이라는 뜻도 아니다. 공개 첫 응답 지연은 두 대안보다 길고 throughput은 높아 ‘항상 가장 빠름’은 주장하지 않는다. 비용 근거는 강하지만 품질 우위는 **잠정**이다.

## 5. 자료 분석: Gemini 3.1 Flash Lite

| 후보 | 공개 p50 latency / throughput 사례 | 같은 token 예시 비용 | 품질 근거 |
| --- | --- | ---: | --- |
| **현재: Gemini 3.1 Flash Lite** | Google AI Studio 0.80초 / 153 token/s | $0.001250 | 단순 정보 추출 용도·구조화 출력 지원; 운영 분석 경로 사용 |
| 대안: Gemini 2.5 Flash Lite | Google AI Studio 0.57초 / 170 token/s | $0.000400 | 저비용 추출 후보; 동일 자료 추출 품질 미검증 |
| 대안: GPT-4.1 Mini | OpenAI 0.86초 / 75 token/s | $0.001600 | instruction following·구조화 출력 지원; 동일 자료 품질 미검증 |

출처: [3.1 Flash Lite](https://openrouter.ai/google/gemini-3.1-flash-lite), [2.5 Flash Lite](https://openrouter.ai/google/gemini-2.5-flash-lite), 위 GPT-4.1 Mini 관측·공식 문서. 공개 수치는 자료 전체 분석 완료 시간과 다르다.
**선정 근거:** README·이력서에서 사실을 정해진 필드로 추출하는 역할에 맞는 모델이고, 예시 비용은 GPT-4.1 Mini보다 약 22% 낮다. 현재 분석 계약과 연결된 구현을 유지할 운영상 근거는 있다. 그러나 2.5 Flash Lite는 예시 비용이 68% 낮고 공개 속도도 경쟁력이 있어, 가격·속도만으로 현재 선택이 최적이라고 주장할 수 없다.
**판단:** 추출 정확도·누락·없는 경력 생성·근거 위치 연결의 동일 조건 비교가 없어 품질상 유지 근거는 **잠정**이다. 긴 입력일수록 현재 모델의 입력비 절감 효과와 문맥 사용량을 따로 계산하고, 2.5 후보의 품질이 동등하면 교체 검토가 가능하다.

## 6. 전사 정규화: Gemini 3.1 Pro Preview — 운영 기능 확인

**유지 근거는 배포사이트에서 사투리 STT 전사문을 표준어·어투로 보정하는 기능을 확인한 결과다.** 10/8 로그인한 `https://malhaebom.xyz`에서 사투리 WAV 두 개를 독립된 연습으로 업로드하고 STT 후 표준어 변환을 실행했다. 당시 revision은 `malhaebom-mk2-transcript-fast-1008`, 트래픽 100%, 모델은 Pro / low / max_tokens 5000이었다. 현재 revision과 구분한다.

| 운영 시험 | 음성 길이 | STT 엔진 처리 | 표준어 변환 API | 결과 |
| --- | ---: | ---: | ---: | --- |
| 사투리 1차 답변 | 47.2초 | 2.6초 | 31.7초 | HTTP 200, attempt=1; 수정문·확인 항목 6개 표시 |
| 사투리 2차 답변 | 39.3초 | 3.1초 | 25.2초 | HTTP 200, attempt=1; 수정문·확인 항목 4개 표시 |

1차는 `지가→제가`, `까보이→확인해 보니` 등 방언·구어체를 바꾸고 면접 답변 어투로 정리했다. 2차는 `퀄이 로그→쿼리 로그`를 보정하면서 800→200ms 수치, 조회 API 캐시 직접 적용, 상품 수정 시 캐시 삭제, 데이터 일치 확인을 유지한 수정문이 화면에 표시됐다.
**증거:** [배포사이트 테스트 기록·화면](../evals/results/llm-selection-20261009/production-normalization-20261008/WAV_TEST_RESULTS.md), [실측 결과](../evals/results/llm-selection-20261009/production-normalization-20261008/wav-production-results.json), [호출 로그](../evals/results/llm-selection-20261009/production-normalization-20261008/wav1-normalization-logs.json), [운영 시간 로그](../evals/results/llm-selection-20261009/production-normalization-20261008/production-timing-logs.json), [당시 트래픽](../evals/results/llm-selection-20261009/production-normalization-20261008/production-traffic.json). 원문·보정문과 원본 SHA256도 같은 증거 폴더에 보존했다.
**확인 범위:** WAV 업로드→STT→표준어·어투 변환→화면 표시까지 확인했다. 음성은 준비된 사투리 시험 파일이며 실제 마이크 녹음, 발화 정답에 대한 독립 인적 평가, 전사문 확정·코칭 제출은 포함하지 않았다. 변환 시간은 인증·Prompt 조회·검증을 포함한 서버 API latency이며 브라우저 전체 대기 시간은 아니다. Pro는 다른 모델과 비교하지 않고 **운영에서 보정 기능 확인**을 채택 근거로 기록한다.

## 7. 모델 회사 공식 문서의 품질 비교

전사 정규화는 비교 대상에서 제외한다. 아래는 Google·Anthropic·OpenAI가 발표한 **동일 출처 표 안의 비교**다. 제조사 평가이며 독립 검증은 아니다. 서로 다른 버전의 GDPval, 도구 유무, grader, 추론량을 섞어 종합 순위를 만들지 않았다. 외부 후보는 현재 네 모델에 포함되지 않는 모델만 사용한다.

| 현재 모델 / 역할 | 공식 평가·조건 | 현재 점수 | 외부 후보 점수 | 선정 근거로 해석 |
| --- | --- | ---: | --- | --- |
| 3.5 Flash Lite / 코칭 | GDPval-AA v2, Elo | 1140 | GPT-5.4 Mini 1171; Haiku 4.5 907 | Haiku 대비 업무 수행 역량 근거; GPT 후보 대비 최고 품질은 아님 |
| 3.5 Flash Lite / 코칭 | GDM-MRCR v2 8-needle, 128k 평균 | 72.2% | GPT-5.4 Mini 42.7%; Haiku 4.5 35.3% | 긴 문맥에서 근거를 찾는 역량의 간접 근거 |
| Haiku 5.5 / 자유채팅 | GDPval-AA v2.1, 평가 rating | 1620 | Haiku 4.5 735; GPT-6 Luna 1437 | 업무 요청 수행 후보로서 역량·낮은 단가를 함께 지지 |
| Haiku 5.5 / 자유채팅 | AA-Briefcase v1.1, 평가 rating | 1578 | Haiku 4.5 614; GPT-6 Luna 1336 | 여러 단계의 업무 문맥 처리에 대한 간접 근거 |
| 3.1 Flash Lite / 자료 분석 | FACTS Benchmark Suite | 40.6% | 2.5 Flash Lite 17.9%; Haiku 4.5 18.6% | 사실성 기준은 더 비싼 3.1을 선택할 품질상 근거 |
| 3.1 Flash Lite / 자료 분석 | MRCR v2 8-needle, 128k 평균 | 60.1% | 2.5 Flash Lite 30.6%; Haiku 4.5 35.3% | 긴 자료의 사실 회수 능력에 대한 근거 |

출처·방법: [Google 3.5 모델 카드](https://deepmind.google/models/model-cards/gemini-3-5-flash-lite/)와 [평가 방법](https://deepmind.google/models/evals-methodology/gemini-3-5-flash-lite/), [Anthropic Haiku 5.5 발표](https://www.anthropic.com/claude-haiku-5-5), [Google 3.1 Lite 모델 카드](https://deepmind.google/models/model-cards/gemini-3-1-flash-lite/)와 [평가 방법](https://deepmind.google/models/evals-methodology/gemini-3-1-flash-lite/). 10/9 확인; 발표 시점은 각각 7월·10월·3월이다.

**코칭:** 3.5의 공식 평가는 기본 high thinking이며 외부 후보는 최대/최선 공개 추론 설정을 사용했다. 지식 업무 점수는 GPT-5.4 Mini에 약간 뒤지지만 긴 문맥 점수는 앞선다. 과거 프로젝트의 계약·지연 실측과 합치면 ‘최고 지능’보다 근거 활용·응답성의 균형을 택한 유지 이유가 된다. Elo/rating 차이를 정확도 향상률로 계산하지 않는다.
**자유채팅:** Haiku의 공식 업무 평가 두 항목이 외부 후보보다 높아 비용만으로 정한 선택은 아니다. 다만 effort에 따라 성능·과금이 달라지고, 공개 점수가 운영 free-chat 설정과 같은 조건이라는 증거는 없다. [OpenAI 자체 평가](https://openai.com/index/gpt-4-1/)의 GPT-4.1 Mini는 IFEval 84.1%, MultiChallenge 35.8%, ComplexFuncBench 49.3%로 지시·다중 턴·도구 호출 후보 근거도 있다. Haiku와 공통 표가 없어 직접 품질 승패는 미정이다.
**자료 분석:** 3.1 Lite 공식 결과는 `gemini-3.1-flash-lite-preview`의 high thinking 평가로, 운영 GA 모델 호출의 실측이 아니다. FACTS는 grounding·parametric·search·멀티모달을 합친 지표이고 MRCR은 정보 회수다. 둘 모두 2.5보다 높아 추가 비용을 감수할 역량 근거가 있지만, 제출한 이력서 필드 추출 정확도 향상을 증명하지는 않는다.

## 8. 선정 근거의 강도와 추가 검증

| 역할 | 현재 선택을 지지하는 근거 | 남은 비교 |
| --- | --- | --- |
| 본 코칭 | 외부 후보 대비 과거 계약 안정성·완료 속도 실측 | 최신 고정 조건의 사람 코칭 품질·비용 |
| 자유채팅 | 낮은 단가·실제 로컬 다중 턴 실행 기록 | 동의→실제 저장·전환, 반복 질문, 범위 밖 안내의 대안 A/B |
| 자료 분석 | 추출 역할 적합성·현재 구현·GPT 후보 대비 단가 | 2.5/GPT 후보 대비 사실 정확도·누락·날조 |
| 전사 정규화 | 배포사이트의 WAV 2건 STT·표준어/어투 보정·화면·HTTP·로그 | 운영 기능 확인 기록; 독립 발화 정확도 평가는 별도 |

전사 정규화를 제외한 다음 비교는 역할별 같은 입력·Prompt·schema·재시도·provider·생성 설정을 기록하고, 각 모델 최소 30건×3회로 완료 p50/p95·전체 과금·계약·의미 오류를 따로 측정한다. 자유채팅은 기존 50개 다중 턴×3회의 실행 결과와 서버 상태까지 대조한다. 이 계획은 이번 문서에서 실행하지 않았다.

현재 선택은 코칭의 비교 실측, 자유채팅·자료 분석의 공개 품질 근거, 전사 정규화의 운영 기능 확인으로 구분한다. 범용 벤치마크 점수를 한국어 면접·자료 추출·전사 보정 점수로 대체하지 않으며, 추가 비교 전에는 네 모델이 모두 최적이라고 결론 내리지 않는다.
