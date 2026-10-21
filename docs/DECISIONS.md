# Decision Log

## 2026-09-29 — 운영 Prompt와 도메인 Skill을 분리

모델 역할·응답 형식은 `prompts/`, 면접·원문 판단 규칙은 `skills/`에서 관리하고 호출 시 결합한다. 입력 근거의 신뢰 경계는 Skill에도 유지해 과거 v3 경로의 보호를 보존한다. 루브릭·공개 API·서버 validator는 변경하지 않는다. README·공고 분석에서 Skill 본문을 무시하던 중복 하드코딩은 제거한다.

기본 코칭 Prompt를 v4.2로 구분하며 v3/v4/v4.1 빌더는 같은 Skill 문자열을 넣을 때만 이전 조합을 재현한다. 과거 전체 입력은 당시 Skill snapshot과 Prompt 버전을 함께 복원해야 한다. Langfuse에는 템플릿만 관리하고 현재 Skill을 별도로 결합한다. 슬롯 없는 원격 Prompt는 로컬로 fallback하며 Cloud 동기화는 별도 실행이다.

## 2026-09-28 공통 provider에 OpenAI SDK 사용

추가 체인 없이 기존 provider 한 곳을 SDK로 전환한다. 모델·Skill·출력 계약 및 main의 비용/관측 정책을 보존하고 SDK 자동 retry는 0으로 설정한다.

> 제공 기획 기반 운영 문서. 기능·기술·정책은 목표 또는 재사용 계획이며 현재 구현 완료를 뜻하지 않는다. 기존 1차 코드는 이관되었으며 정적 조사 결과는 [CURRENT_STATE](CURRENT_STATE.md)를 따른다. 실행 검증은 별도다.

이 문서는 프로젝트의 중요한 선택을 누적 기록한다. 기존 결정을 뒤집을 때 기존 항목을 삭제하지 말고 새 결정으로 추가한다.

## 2026-09-23 — 원인 근거를 관찰 신호와 추론 연결로 분리

**결정**
`cause_reasoning`을 폐기하고 `cause_observation`, `cause_inference`로 분리한다. “로그를 봤다” 또는 “원인을 확인했다”만으로는 관찰 신호를 `met` 처리하지 않으며, 관찰 신호가 특정 원인 후보를 좁힌 연결도 별도로 확인한다.

**이유**
범용 면접 피드백의 일반적 조언과 구분되는, 답변 근거 중심의 원인 판단 코칭을 제공하기 위해서다. 확인되지 않은 로그 내용·기술 원인·성과를 모델이 대신 만들어서는 안 된다.

**버전 영향**
Skill은 `interview-coach-v4`, criteria는 `problem-solving-v4-draft.3`으로 올린다. 이전 평가·실행 결과는 당시 버전의 기록으로 보존하며 새 기준 결과와 직접 비교하지 않는다.

---

## 2026-09-16 — 대상 직무를 신입 백엔드로 제한

**결정**
초기 대상은 신입 백엔드 개발자 준비생으로 제한한다.

**이유**
도메인 판단 기준과 평가 범위를 좁혀 검수 가능한 수준으로 만들기 위해서다.

---

## 2026-09-16 — 초기 면접 유형을 문제 해결 경험 하나로 제한

**결정**
“프로젝트 개발 중 발생한 문제를 어떻게 해결했나요?”를 중심으로 문제 해결 경험 한 유형을 구현·평가한다.

**이유**
여러 질문 유형을 동시에 만들기보다 한 유형의 판단 기준·예외·평가셋을 깊게 검증하기 위해서다.

---

## 2026-09-16 — RAG를 사용하지 않음

**결정**
RAG, 벡터 DB, 임베딩/문서 조각 검색, LangGraph를 이번 프로젝트에 도입하지 않는다.

**이유**
검토된 구조화 공고/직무 레코드와 고정 Skill을 사용하고, 사례별 정답을 검색해 모델에 넣는 구조를 피한다.

---

## 2026-09-16 — 공개 공고/NCS 자체를 차별점으로 주장하지 않음

**결정**
고용24/NCS/공개 질문 데이터는 도메인 맥락과 참고 근거로 사용하되 자체 독점 자산으로 주장하지 않는다.

**이유**
이미 공개된 데이터이며 경쟁 서비스도 공고 기반 기능을 제공한다.

---

## 2026-09-16 — 핵심 자체 데이터 후보를 네 가지로 정의

**결정**
- 사용자의 실제 역할
- 설명에서 빠진 정보
- 코칭 이후 변화
- 변화에 대한 사람의 판단

**주의**
수집 건수 자체를 품질이나 복제 방어력의 증거로 사용하지 않는다.

---

## 2026-09-16 — 공고 관련성과 C/R/A/D/V를 분리

**결정**
공고 요구사항과 답변의 관련성 판정은 문제 해결 답변의 C/R/A/D/V 상태와 별도 차원으로 관리한다.

**이유**
공고와 관련된 경험이라는 사실이 개인 기여, 원인 판단, 결과 검증까지 충족했다는 의미는 아니기 때문이다.

---

## 2026-09-16 — 확인 응답을 원래 답변과 분리

**결정**
확인 질문에 대한 응답은 별도 기록이며 1차 답변 판정을 소급 변경하지 않는다.

**이유**
첫 답변에서 실제로 말한 것과 이후 확인한 사용자 진술을 구분하기 위해서다.

---

## 2026-09-16 — 재답변 비교는 서버가 상태 변화 계산

**결정**
각 답변은 독립적으로 분석하고 비교 단계에서는 같은 criterion의 상태와 근거를 서버가 계산한다. 초기 비교 단계에 추가 LLM 호출은 필수가 아니다.

**이유**
비교의 재현성을 높이고 과거 답변의 사실이 현재 답변 판정에 섞이는 것을 막기 위해서다.

---

## 2026-09-16 — 기존 음성 자산을 우선 재사용

**결정**
새 STT/TTS 학습보다 기존 녹음/STT/VAD/TTS 자산을 재사용하고 내용 코칭 계층을 교체·추가한다.

**이유**
기존 프로젝트 기반의 2차 프로젝트이며 핵심 검증 대상이 내용 코칭과 도메인 판단이기 때문이다.

---

## 2026-09-16 — 통과 기획 원문과 운영 문서를 분리

**결정**
통과한 기획 원문은 `docs/proposal/`에 보존하고, 현재 상태·목표·요구사항·제약·평가는 별도 운영 문서로 관리한다.

**이유**
기획 원본을 보존하면서 구현 과정에서 갱신되는 사실과 결정을 분리하기 위해서다.

## 2026-09-16 — 문서 canonical 경로와 이관 대기 상태 확정

**결정** 기존 README·AGENTS·수업 협업 규칙을 보존하며 병합한다. 도메인 지식은 `skills/interview-coach/SKILL.md`, 평가 계획은 `evals/README.md`, 평가 결과는 `EVAL_REPORT.md`를 canonical로 유지한다. 신규 운영 문서는 기존 `SCAFFOLD.md`처럼 대문자 설명형 이름을 사용한다.

**이유** 같은 역할의 문서가 서로 다르게 갱신되는 것을 방지한다. `requirements/`는 기존에 없으므로 별도로 만들지 않는다. 기획 원본은 `proposal/`에 바이트 그대로 보존하며, 현재 코드에 대한 증거로 쓰지 않는다. 이번에는 코드 이관·구현·실행 검증을 수행하지 않는다.

**기록** [첫 Worklog]([REDACTED].md).

## 2026-09-16 — 운영 규칙의 단일 진입점과 실험 재현성

**결정** Git/PR·Issue·CI 운영 정책은 [AGENTS](../AGENTS.md)에, 실험/STT/TTS 상세 절차는 [실험 규칙](experiments/README.md)에 둔다. README와 CLAUDE는 참조 관계를 유지한다.

**이유** 규칙 중복을 줄이고 리뷰 책임, 데이터 누수 방지, baseline 비교 및 CI 다운로드 비용을 명확히 관리하기 위해서다. 신규 학습 제외는 유지하며 실험 규칙이 실행 승인을 대신하지 않는다. 이번에는 문서만 정리하고 branch protection·승인 강제·PR 줄 수 검사·timeout·concurrency·dependency split은 구현하지 않았다. 원격 설정은 미확인이다.

**기록** [운영 규칙 Worklog]([REDACTED].md).

## 2026-09-17 — 이관 코드와 목표 문서 분리 및 bootstrap 예외

**결정** PR #1의 코드를 기준으로 현재 구조를 정적 조사했다. CURRENT_STATE와 ARCHITECTURE는 실제 호출 경로를, TARGET_STATE·REQUIREMENTS는 미완료 목표를 기록한다. 이관된 PRD/Spec·실험 기록은 보존하며 docs/README에서 현재 기준 문서로 연결한다. 도메인 정책을 코드 현황에 맞춰 완화하지 않는다.

**결정** 사용자가 이번 초기 repository documentation bootstrap PR에 한해 400줄 제한의 1회성 예외를 승인했다. 기획 원본·강의 지식·research template·Worklog를 포함하는 초기 문서 체계이며 기능 변경을 회피하기 위한 예외가 아니다. 이후 일반 PR에는 400줄 원칙을 적용한다.

**검증 경계** 정적 코드 확인만 수행. 환경 재구축·모델/데이터 인수·benchmark·운영 E2E는 별도 작업이다. Issue는 중복 조회 후 후보만 기록하며 코드 수정·PR merge는 하지 않는다.

**기록** [통합 Worklog]([REDACTED].md).

## 2026-09-17 — PR #7 충돌 해결

최신 main의 실행용 Skill·코칭 출력 계약·평가 runner 안내를 보존하고 PR #7의 기준 문서와 운영 규칙을 병합한다. 평가 파일의 합성 30건(12/10/8)과 독립 판정 근거를 확보할 향후 계획(9/12/9)은 구분한다. 현재 파일 존재를 공식 평가 출처 요건 충족으로 해석하지 않는다. 이전 CURRENT_STATE·ARCHITECTURE 조사는 당시 snapshot 기록으로 표시한다.

기록: [충돌 해결 Worklog]([REDACTED].md).

## 2026-09-18 — 확정 답변 기반 코칭 예시 1개 허용

**결정** 대필 금지는 유지하되, 확정 답변의 사실과 현재 코칭만 재구성한 2~3문장 예시를 결과당 1개 제공한다. 없는 정보는 중립적인 대괄호 자리표시자로 남긴다.

**검증 경계** 서버는 필수 여부·500자 제한·신규 숫자를 검사한다. 역할·기술·성과의 의미상 추가 여부와 실제 모델 품질은 Skill 및 후속 사람 검토로 보완한다.

**기록** [기능 Spec](specs/coaching-example-answer.md), [Worklog]([REDACTED].md).

## 2026-09-18 — 평가 v2 판정과 의미 품질 정책

사용자 승인으로 intent를 질문 적합성에 한정하고 C/A/V 완성도와 독립 판정한다.
V는 확인 행위만 있으면 partial, 실제 관찰 결과가 있어야 met이다.
공고 requirement text가 없는 v2에서는 job alignment 및 영향을 받는 status를 고정 정확도에서 제외한다.
기존 v1은 재현용으로 보존한다. 의미 annotation은 승인 초안이며 독립 검토 상태를 별도 명시한다.
critical failure는 의미 품질 0/1/2 점수와 독립 집계하고 미검토는 null로 유지한다.
R/D 및 실제 모델 실행은 이번 변경에 포함하지 않는다.

## 2026-09-18 — 평가 전용 환경과 OpenRouter 키 선택

Python 3.12 로컬 venv와 재실행 가능한 evals/setup_env.sh를 사용한다.
운영/평가 버전 불일치를 막기 위해 네 경량 의존성은 requirements-eval.txt에서 공유한다.
루트 .env는 shell 값을 덮어쓰지 않고 로딩한다. 기본 OpenRouter endpoint에서는
OPENROUTER_API_KEY만 사용한다. MODEL_API_KEY 우선 선택은 사용자 지정 다른 endpoint에 유지한다.
실제 모델 호출은 setup에서 실행하지 않는다.

## 2026-09-18 — assessment 근거와 의미 품질 분리

- intent는 질문적합성만, C/A/V는 완성도를 독립판정한다. 비백엔드 경험의 내용구조도 intent와 분리하고 요청문은 경험으로 인정하지 않는다.
- 확인·테스트 행위만 있으면 Vpartial이며 관찰결과가 있어야 met이다.
- not_observed도 부재/미확인/팀only 실제원문 evidence를 허용한다. 없던 사실을 만들어 근거를 채우지 않는다.
- v2 evidence는 target별 support_segment_ids와 실제부분인용으로 채점하며 quote는 예시다. 선택근거 누락은 감점하지 않으며 실제반환근거는 모두 검사한다. 의미적 충분성은 사람semantic검토에 남긴다.
- requirement text없는 job alignment/status는 정확도에서 제외하고 semantic 및 critical을 분리한다.
- 기존252건을 별도 offline 결과로 재채점하되 새Skill 추론으로 간주하지 않는다. 실제API는 재실행하지 않는다.

## 2026-09-19 — C 최소 상황 기준 확정

C met은 문제 대상·문제로 인식한 상태와 증상/발생 조건/영향/비교 상태 중 하나가 연결되어 문제를 이해할 수 있을 때다. 문제 명칭만 있고 대상이나 발생 상황이 충분히 드러나지 않으면 partial, 문제 상황 자체가 없으면 not_observed다. 원인·개인 행동·검증 결과·직무 적합성을 C에 섞지 않는다. 이에 따라 v2 case14/18/21/22 C는 partial, case20은 intent off_topic과 독립적으로 C met을 유지한다.

## 2026-09-19 — Basic 후보와 Premium fallback 결론

최종 자동 평가와 63개 사람 semantic 검토를 함께 본다. Gemini Flash는 자동 품질 25/30과
p95 25.77초로 품질·응답성 기본 후보, DeepSeek Flash는 비용 $0.1012와 semantic 91.3%로
비용 효율 기본 후보로 유지한다. Qwen Flash는 자동 품질 14/29, semantic 68.0%, critical 3건,
p95 243.61초로 후보에서 제외한다.

DeepSeek/Gemini 실패 합집합 8건에서 GPT-5.6 Terra는 4건을 복구하고 semantic 83.3%,
critical 0, 복구당 $0.0159, recovery p95 6.09초를 보여 Premium fallback 1순위로 둔다.
Claude Sonnet 5와 DeepSeek V4 Pro는 각각 2/8 복구에 그쳤다.

사람 검토 63개 중 Batch1만 strict blind였으며 이후 batch는 mapping 노출 뒤 채점했다.
Premium semantic은 어려운 failure subset 점수이므로 Basic과 절대 비교하지 않는다. case20은
known ambiguous로 분리하고, R/D·requirement context·반복 consistency는 후속 평가로 남긴다.

## 2026-09-21 — 다양성 평가 후 LLM 후보를 Flash Lite와 Luna로 축소

2026-09-19의 Basic 후보·Premium fallback 결론은 당시 failure subset과 사람 semantic 검토에 근거한
historical decision으로 유지한다. 이후 목적이 다른 OpenRouter diversity에서 40개 모델을 preflight하고
22개 모델을 30건씩 평가해 structured-output 호환성을 넓게 확인했다. 이 계약 결과는 semantic 순위로
해석하지 않는다.

마지막으로 Gemini 3.5 Flash Lite, Gemini 3.8 Flash, GPT-5.6 Luna, GPT-5.6 Terra를 현재 동일 30건과
동일 prompt/schema/model-default 생성 조건으로 새로 실행했다. Flash Lite는 30/30과 p95 4.20초,
Luna는 29/30과 알려진 30건 비용 $0.03914948을 보였다. Gemini 3.8 Flash는 30/30이지만 Flash Lite보다
느리고 비쌌다. Terra는 과거 fallback 강점과 달리 이번 OpenRouter 경로에서 raw output/provider가 없는
schema/integration 단계 실패 20건이 있어 안정적인 기본 후보로 두지 않는다.

따라서 **기계 평가 기준 1차 최종 후보**를 Gemini 3.5 Flash Lite와 GPT-5.6 Luna로 좁힌다.
이는 production 모델 확정이 아니며 30건 blind semantic 검토 결과에 따라 변경할 수 있다.
[전체 평가 이력](../EVAL_REPORT.md), [Final Four 실험 기록](experiments/2026-09-21_openrouter-final-four.md),
[재현 명령](../evals/README.md)을 함께 유지한다.

## 2026-09-19 — 누락된 historical LoRA 대신 STT retrain 실험 허용

**결정** 기존 부산/경상도 Whisper LoRA 계보의 `adapter_model.safetensors`를 원 STT Drive와 최신 handoff에서 찾지 못했으므로 exact continuation은 중단한다. 기존 CTranslate2 모델은 baseline으로 보존하고, `openai/whisper-medium` + 동일 LoRA 구조를 사용한 새 QLoRA retrain을 별도 실험 범위에서 수행한다.

**경계** 이 결정은 STT 실험 실행만 승인하며 MVP 제품 범위 확장, 제품 기본 모델 자동 교체, TTS 신규 학습을 승인하지 않는다. 새 모델은 source-disjoint holdout에서 기존 CT2 baseline과 동일 조건 비교 후 별도 결정한다.

**기록** [STT retrain Spec](specs/stt-finetuning-retrain.md), [실험 기록]([REDACTED].md), [Worklog]([REDACTED].md).

---

## 2026-09-21 — PR 크기 정책을 Review Core 중심 가이드라인으로 개선

**결정**
1. 기존의 `400 LOC` 무조건적 hard limit을 기본적인 **review-size guideline**으로 전환한다.
2. 코드, 테스트, 설정, 핵심 Spec, 실험 계획/평가기준/절차 등 실제 리뷰 대상이 되는 **Review Core**는 400줄 안팎을 유지하도록 권장한다.
3. Worklog, raw benchmark 결과 데이터, lockfile, machine artifact 등 부수/증빙 파일만 Review Core 산정에서 제외한다. `docs/experiments/**` 디렉터리 전체를 일괄 예외 처리하지 않고, 실험 계획·방법·기준 문서는 Review Core로 포함한다.
4. 하나의 논리적 작업이라면 부수/증빙 문서로 인해 전체 PR이 400줄을 다소 넘더라도 기계적으로 PR을 쪼개지 않는다. 단, 논리적인 commit 단위로 나누어 리뷰어가 단계적으로 볼 수 있게 한다.
5. Review Core 자체가 800줄을 초과하는 경우는 기능/책임 단위 분리를 강제(차단)하고, 400~800줄 구간은 PR description에 초과 사유와 분리하지 않은 이유를 필수로 기록하도록 CI 및 정책 스크립트(`scripts/check_pr_policy.py`)로 자동 검증한다.
6. PR description 변경은 같은 HEAD에 독립된 정책 check run을 새로 쌓지 않고 기존 `PR Policy Check` run의 새 attempt로 자동 재검사한다. 이를 위해 `edited` 이벤트는 전용 helper workflow가 처리하며, 정책 workflow는 실행 시점의 최신 PR description을 GitHub API에서 읽는다.
7. edit helper는 rerun 직전에 현재 PR HEAD를 다시 읽고 이벤트 HEAD와 달라졌으면 obsolete rerun을 수행하지 않는다. policy concurrency key는 PR 번호와 HEAD SHA를 함께 사용해 오래된 HEAD rerun이 최신 HEAD policy run을 취소하지 못하게 한다.

**이유**
단순한 기계적 줄 수 분할은 컨텍스트 단절과 리뷰 피로도를 높이고, 필수 증빙 문서(Worklog, Spec, 실험 결과) 작성을 기피하게 만드는 부작용이 있다. 따라서 리뷰어가 실제로 집중해서 검토해야 하는 핵심 변경(Review Core)을 중심으로 품질과 리뷰성을 확보하기 위해서다.
또한 같은 HEAD의 과거 실패와 최신 성공이 별도 check run으로 공존하면 GitHub UI와 자동 도구가 stale 실패를 현재 상태로 오해할 수 있으므로, 본문 수정은 기존 run의 rerun attempt로 갱신한다.
polling 중 새 commit이 들어오는 race에서도 최신 HEAD 검사를 보존해야 하므로 rerun 직전 HEAD 재검증과 HEAD별 concurrency 분리를 함께 적용한다.

## 2026-09-21 — 신규 STT 데이터 단독 학습과 제한적 old-data replay를 함께 비교

**결정** 현재 clean-continuation best adapter를 고정 시작점으로 두고, 추가 STT 학습은 최소 세 조건을 비교한다. B0는 추가 학습하지 않은 현재 모델, B1은 신규 데이터 100% continuation, B2는 신규 데이터와 placeholder-free historical clean train의 제한적 replay를 목표 80:20 sampling으로 혼합한다. 70:30 replay는 B0/B1/B2만으로 trade-off가 해소되지 않을 때만 후속 실험으로 검토한다.

**이유** 신규 데이터만 연속 학습하면 기존 도메인 성능 저하(catastrophic forgetting)가 발생할 수 있지만, historical train을 전부 재사용하면 신규 도메인 적응 효과와 일반화 해석이 흐려질 수 있다. 따라서 신규 데이터 단독 조건을 요청사항의 직접 baseline으로 보존하고, 제한적 replay가 retention에 실제 이득을 주는지 별도 측정한다.

**경계** replay는 일반적인 "추가 fine-tuning은 신규 데이터 사용" 규칙의 명시적 실험 예외다. placeholder-free historical clean train만 사용하고 historical validation/Test A/Test B는 replay에 넣지 않는다. Test B는 이미 결과를 확인했으므로 replay 비율·checkpoint 선택에 사용하지 않고 최종 보고용으로만 유지한다. 신규 데이터도 source-disjoint train/validation/test로 분리하며, 최종 new-domain test를 본 뒤 hyperparameter를 다시 조정하지 않는다.

**기록** [신규 데이터 + replay 실험 계획](experiments/stt/2026-09-21_new-data-replay-plan.md).

## 2026-09-22 — AI Hub 71592 면접 도메인 적응 후보로 20% historical replay 조건을 선택

**결정** AI Hub 71592 ICT/New 면접 답변으로 추가 적응한 두 조건 중 C2(71592 신규 데이터 80% + placeholder-free historical clean 119 replay 20%)를 실험 후보로 선택한다. C1(71592 only)과 C2는 71592 validation에서 사실상 동률이었고, C2가 historical 119 retention에서 C1보다 CER/WER 회귀를 줄였다. 선택 이후 봉인된 71592 test는 C2 한 조건에 대해서만 열었으며 CER 2.5876%, WER 9.7740%를 기록했다.

**근거** 71592 validation은 C1 CER 2.9298% / WER 9.5594%, C2 CER 2.9290% / WER 9.5510%였다. historical 119 retention은 B0 CER 5.9693% / WER 15.3344%, C1 6.5171% / 17.1378%, C2 6.4600% / 16.8062%였다. 따라서 replay는 신규 면접 도메인 성능을 눈에 띄게 희생하지 않으면서 C1 대비 forgetting을 완화했다.

**경계** C2는 B0보다 historical 119 retention이 여전히 나쁘므로 전역적으로 더 좋은 STT라고 결론내리지 않는다. 71592에는 검증된 지역 출신 메타데이터가 없으므로 이 결과를 경상도 음성 성능 개선 근거로 사용하지 않는다. 기존 계획의 material regression numeric tolerance는 final test 공개 전에 별도 수치로 고정되지 않았으므로 C2 선택은 테스트한 C1/C2 사이의 상대적 선택으로 해석한다. 71592 final test는 이제 노출되었으며 replay 비율, checkpoint, segmentation, learning rate 등 후속 tuning에 사용하지 않는다. 이 선택은 제품 기본 STT 모델 자동 교체를 의미하지 않는다.

**기록** [AI Hub 71592 domain adaptation 실험](experiments/stt/2026-09-22_aihub71592-domain-adaptation.md).

## 2026-09-21 — ALIO 요구사항은 원문 수동 검토·개인 소유로 저장

**결정**
ALIO 검색 결과는 바로 연습에 쓰지 않는다. 사용자가 원문을 확인한 뒤 요구사항 1~5개와 각 원문 근거를 입력해 검토 완료해야 한다. 저장한 `alio` 공고는 검토자 본인에게만 보이며, 그 요구사항 1~2개를 선택한 뒤 1차 답변을 시작한다.

**이유**
제목이나 검색 요약으로 요구사항을 추정하면 실제 공고 내용과 다른 맥락으로 코칭할 수 있다. 현재 인증 체계에는 팀 역할·승인 워크플로가 없으므로, 전역 검토 완료 상태를 가장한 공유 데이터보다 검토자 소유 레코드가 정직한 MVP 경계다.

**주의**
ALIO가 기관의 외부 채용 사이트를 원문 링크로 반환할 수 있으므로, `alio.go.kr` 도메인만 요구하지 않고 검색 결과에서 받은 HTTP(S) 원문 링크를 저장한다. URL 형식 검증은 출처 링크의 존재를 보장할 뿐, 서버가 공고 내용을 자동 검증한다는 뜻은 아니다.

**기록** [기능 Spec](specs/alio-reviewed-practice-context.md).

## 2026-09-28 — 비교 후 면접 대화 허용

사용자 요청으로 비교 후 첫 질문, 사용자 답변/질문에 대한 짧은 피드백과 질문 최대 1개, 사용자가 종료하는 시점의 요약을 제공한다. 단일 프로세스의 임시 문맥으로 시작하며 기존 기록·판정은 유지한다. 기존 무제한 대화 제외 경계에서 해당 연습 세션만 확장한다.
