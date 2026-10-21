---
title: KDT AI Human 7기 — Project2용 AI Agent Engineering 지식 정리
updated: 2026-09-16
language: ko
purpose: proj2-3 개발 시 Codex/팀원이 참고할 수업 지식 요약
canonical_path: docs/knowledge/COURSE_KNOWLEDGE.md
sources:
  - https://github.com/nanocode00/factory-agent-hub/blob/main/knowledge/agent-engineering.md
  - https://drive.google.com/drive/folders/1dgs2PekmLTTZVVEzawHbetbiXHLvFJ9n
source_status: 제공 입력 문서의 출처 설명을 보존함. 이번 통합에서는 외부 원자료 및 최신 SDK 동작을 재검증하지 않음.
---

# Project2용 AI Agent Engineering 지식 정리

> **교육/기술 참고 지식** — 수업 자료를 정리한 문서이며 프로젝트 요구사항이나 구현 완료의 증거가 아니다.
>
> 공식 조건은 [REQUIREMENTS](../REQUIREMENTS.md), 팀 자율 제약은 [CONSTRAINTS](../CONSTRAINTS.md), 면접 도메인 규칙은 [Skill](../../skills/interview-coach/SKILL.md)을 따른다. 이 문서의 일반 기법이 프로젝트 범위를 넓히지 않는다.
>
> 모델명·가격·UI·서비스 정책·SDK 예시는 수업 당시 참고 정보다. 고정 요구사항으로 사용하지 않으며 실제 적용 시 버전과 최신 공식 자료를 확인한다. 아래 신규 보강 표기는 입력 자료가 설명한 2026-09-13~15 수업 보강을 가리킨다.

## 0. 이 문서의 역할

이 문서는 강의 순서를 그대로 옮긴 필기장이 아니라, Project2 구현 중 반복해서 확인할 원칙을 **설계 → 실행 → 검증 → 복구 → 관측 → 배포** 흐름으로 재구성한 참고 문서다.

가장 압축하면 운영 가능한 Agent는 다음 요소의 조합이다.

```text
LLM
+ Instructions / Skill
+ Context / State / Memory
+ Tools / MCP
+ Output Contract
+ Validation
+ Runtime / Harness
+ Retry / Recovery
+ Observability / Evaluation
= 운영 가능한 Agent
```

핵심 원칙은 단순하다.

- LLM이 잘 답할 것이라고 기대하지 말고 **계약과 검증**을 둔다.
- 비결정적 판단은 LLM에 맡기되, 권한·형식·ID·원문 일치처럼 결정적으로 검증할 수 있는 것은 **코드가 강제**한다.
- 도구가 많다고 Agent가 좋아지지 않는다. 사용자의 실제 업무 흐름에 맞춰 **워크플로 단위 도구**를 설계한다.
- 관측만으로는 품질을 알 수 없고, 평가만으로는 실패 원인을 알 수 없다. **Trace + Prompt Version + Dataset/Eval**을 연결한다.
- 기능을 늘리기 전에 실패 경로와 비범위를 먼저 고정한다.

---

# 1. Workflow와 Agent

## 1.1 무엇을 Agent에게 맡길 것인가

가장 유용한 구분 질문은 다음이다.

> **다음 행동이 입력을 보기 전에 이미 정해져 있는가?**

- 순서와 분기가 미리 고정되어 있으면 Workflow에 가깝다.
- 입력과 중간 결과를 보고 다음 행동이나 도구를 골라야 하면 Agent가 필요하다.

```text
Workflow
A → B → C → D

Agent
Goal
 ↓
Observe → Decide → Tool → Observe → Decide ...
```

Agent의 자율성은 장점만이 아니라 비용·지연·오류 공간을 늘리는 설계 선택이다. 규칙으로 충분히 처리 가능한 부분까지 LLM에게 넘기지 않는다.

## 1.2 실행 패턴

- **Sequential**: 앞 단계 결과가 다음 단계 입력이 되는 고정 파이프라인.
- **Parallel**: 독립 작업을 병렬 수행하고 결과를 병합.
- **Loop**: 검증 기준을 만족할 때까지 수정. 최대 시도 횟수와 종료 조건 필수.
- **Agentic**: 모델이 상황을 보고 다음 행동/Tool을 선택.

좋은 Loop는 다음을 가진다.

```text
Goal
→ Observe
→ Decide
→ Act
→ Verify
→ Success? / Repair / Retry / Escalate
```

사후에 “다시 생각해”라고 시키는 것보다 Tool Contract와 Output Contract를 먼저 명확하게 만들어 실패 공간을 줄이는 것이 우선이다.

---

# 2. Output Contract와 Validation

## 2.1 출력 계약

자연어 출력은 사람이 읽기에는 유연하지만 프로그램의 입력으로는 불안정하다. 따라서 생성 결과를 후처리 정규식으로 계속 보정하기보다 **생성 시점에 스키마를 고정**한다.

출력 계약의 기본 요소:

1. 고정된 키
2. 타입
3. enum / 범위 제약
4. 알 수 없을 때의 기본값 또는 명시적 상태
5. 정상 예시
6. JSON 등 기계가 검증할 수 있는 형식

스키마 통과와 의미상 정답은 별개다.

```text
Structural Validation
- JSON 파싱 가능?
- 필수 필드 존재?
- 타입/enum/range 일치?

Semantic / Business Validation
- 필드끼리 모순 없는가?
- 원문/도구 결과와 일치하는가?
- 업무 규칙을 위반하지 않는가?
```

## 2.2 검증기는 먼저 테스트한다

모델 성능을 재기 전에 Validator 자체가 올바른지 known-good / known-failure fixture로 검증한다.

```text
Known Good
Known NO_JSON
Known JSON_DECODE
Known SCHEMA_VIOLATION
        ↓
Validator Test
        ↓
Real Model Output
```

검증기가 틀리면 모델 평가도 틀린다.

## 2.3 실패를 상태로 분류한다

실패를 전부 `error` 하나로 뭉개면 복구 전략을 고를 수 없다.

예:

```text
NO_JSON
JSON_DECODE
SCHEMA_VIOLATION
SEMANTIC_CONFLICT
UPSTREAM_TIMEOUT
RATE_LIMIT
PERMISSION_DENIED
UNAVAILABLE
```

각 실패에 대해 다음을 미리 정한다.

- 재시도 대상인가?
- 같은 모델에 repair prompt를 보낼 것인가?
- 다른 모델/폴백으로 갈 것인가?
- 최종 사용자에게 무엇을 알려줄 것인가?
- Trace에 어떤 원인과 attempt를 남길 것인가?

재시도는 무한 루프가 아니라 **최대 횟수 + 조건 + 최종 폴백**을 가진 정책이다.

---

# 3. 모델 선택, 비용, 지연

모델 선택은 “가장 똑똑한 모델”이 아니라 같은 조건에서의 비교 문제다.

비교 축 예:

```text
품질        평가셋 판정 통과율 / 항목별 score
안정성      출력 계약 준수율 / 실패율
지연        p50 / p95
비용        요청당 token / 비용
```

평균만 보면 느린 꼬리가 숨으므로 p95를 함께 본다. 비용과 지연은 운영 품질의 일부다.

가능한 최적화 수단:

- 짧고 명확한 프롬프트
- Prompt Caching
- 작은 모델 / 큰 모델 비교 및 필요 시 routing
- 스트리밍으로 체감 지연 감소
- 불필요한 Tool/Context 제거

---

# 4. Tool 설계

## 4.1 좋은 Tool은 endpoint 복사본이 아니다

좋은 Tool Contract는 최소한 다음을 명확하게 만든다.

```text
What        무엇을 하는가
When        언제 써야 하는가
Arguments   어떤 입력을 받는가
Output      어떤 구조로 반환하는가
Constraints 무엇을 하지 못하는가
```

원칙:

- Single Responsibility
- 명확한 Tool 이름과 파라미터 이름
- 구조화된 입력/반환
- Tool description만 읽어도 호출 조건을 이해할 수 있어야 함
- 위험한 부작용과 읽기 전용 기능을 분리

## 4.2 Tool 수를 줄이는 이유

API endpoint 12개를 자동으로 Tool 12개로 노출한다고 운영 가능한 MCP가 되는 것은 아니다. LLM이 사용자의 의도를 endpoint 호출 순서로 다시 조립해야 하므로 선택 오류가 커질 수 있다.

```text
Endpoint 단위
list_links → get_stats → get_detail → ... → LLM이 조합

Workflow 단위
get_link_performance(period="7d", top_n=5)
```

수업의 핵심은 “무조건 적을수록 좋다”가 아니라 다음 가설을 **같은 평가 문항으로 before/after 측정**하는 것이다.

> 사용자 업무 흐름에 맞는 3~5개의 워크플로 도구가 원시 endpoint 목록보다 Tool 선택과 결과 해석을 안정화하는가?

## 4.3 반환 계약

최신 데이터/도메인 데이터 Tool은 값만 반환하지 말고 신뢰 경계를 같이 돌려준다.

권장 최소 메타데이터:

```json
{
  "status": "ok | partial | unavailable | ...",
  "data": {},
  "source": "...",
  "as_of": "...",
  "limitations": []
}
```

값의 **출처, 기준 시점, 상태, 한계**가 있어야 LLM이 부분 실패를 완전 성공처럼 포장하는 일을 줄일 수 있다.

---

# 5. MCP

## 5.1 MCP가 푸는 문제

MCP는 여러 Host/Agent와 여러 외부 서비스 사이의 개별 연결을 표준화한다.

```text
Host / Agent
    ↓
MCP Client
    ↓ protocol
MCP Server
    ↓
External System / Domain API
```

수업에서는 이를 N×M 직접 연결 문제를 N+M 구조로 줄이는 관점으로 설명한다.

세 역할:

- **Host**: 사용자 요청과 LLM 실행을 관리
- **Client**: MCP 연결, 라우팅, capability 발견
- **Server**: Tool / Resource / Prompt 제공

세 Primitive:

```text
Tool     = Action
Resource = Context / Data
Prompt   = Reusable Instruction
```

## 5.2 Skill과 MCP의 역할 분리

신규 MCP Server 강의에서 강조한 경계:

```text
Skill = 고정된 도메인 규칙·판단 기준·용어·예외
MCP   = 최신 값·개별 상태·도메인 데이터 조회 또는 허용된 동작
사람  = 되돌리기 어렵거나 고위험인 최종 승인
```

고정 규칙과 최신 데이터를 같은 곳에 섞지 않는다. Tool 응답은 `source`, `as_of`, `status`를 함께 제공하고, 지원하지 않는 질문에는 추측 대신 **지원 범위 밖**이라고 응답한다.

## 5.3 FastAPI 자동 변환의 한계 — 신규 보강

`FastMCP.from_fastapi(...)`처럼 한 번에 API를 MCP로 노출하는 기능은 출발점일 뿐 최종 설계가 아니다.

자동 변환 후 반드시 확인할 것:

- 사용자가 직접 부를 이유가 없는 health/admin endpoint가 Tool로 노출되지 않았는가
- 위험한 write endpoint가 일반 Tool처럼 보이지 않는가
- Tool 이름/파라미터가 LLM이 이해하기 쉬운가
- 실제 사용자 질문 고정 세트로 Tool 선택 정확도를 측정했는가

**Tool이 보인다 = 안전하게 써도 된다**가 아니다.

## 5.4 MCP Transport와 원격 배포 — 신규 보강

- `stdio`: 로컬 자식 프로세스와 표준 입출력 통신. stdout은 MCP 프로토콜 전용으로 취급하고 일반 로그는 stderr/logging으로 분리.
- `Streamable HTTP`: 원격 연결. 인증·인가·TLS·timeout·경로·상태 관리가 설계 요소가 됨.

원격 MCP의 최소 보안선:

- secret 하드코딩 금지
- 인증 적용
- 인증(authentication)과 인가(authorization)를 구분
- read/write scope 분리
- 필요 이상으로 공개 네트워크에 노출하지 않기
- 고위험 Tool은 approval gate
- 중요한 실행에 감사 가능한 로그 남기기

## 5.5 권한 계약과 NOT_BUILT — 신규 보강

기능 가능 여부와 실행 권한은 다른 문제다.

수업에서는 도구/자동화를 위험도에 따라 L1~L4 수준으로 분류하고, 특히 다음 질문을 사용한다.

> **이 실행은 되돌릴 수 있는가?**

권장 규칙:

- read와 write를 분리
- 위험도가 높을수록 scope와 승인 요구를 강화
- 멱등성만으로 안전하다고 판단하지 않음
- 만들지 않을 고위험 기능을 `NOT_BUILT` 또는 비범위 문서에 구체적인 실패 시나리오와 함께 기록
- 모델이 요청하더라도 서버가 권한 계약을 강제

## 5.6 계약 테스트 — 신규 보강

MCP manifest는 단순 설명서가 아니라 실행 경계다.

최소 테스트:

```text
read/write 분류
risk level
required_scope
approval_required
```

실패 상태도 구분한다.

```text
401 인증 없음
403 권한 부족
409 승인 없음/상태 충돌 등 계약상 차단
422 잘못된 인자
```

특히 **실패한 write 호출이 외부 상태를 바꾸지 않았음**을 assert로 검증한다.

## 5.7 Tool Spec도 공격 표면이다 — 신규 보강

Practice_MCP에는 prompt injection/poisoning용 서버와 scanner가 포함되어 있다. 교훈은 Tool description이나 외부 문자열을 신뢰된 지시로 취급하지 않는 것이다.

- Tool description은 선택 품질에 영향을 주지만 보안 경계는 아님
- 외부 데이터 속 지시문과 시스템/Skill 규칙을 구분
- 위험한 실행은 프롬프트가 아니라 서버 권한 검증으로 차단
- 공격/오염 입력도 평가셋에 포함 가능

---

# 6. State, Session, Memory, Context — 2026-09-14~15 신규 보강

기존 지식베이스의 Memory 개요를 아래처럼 구체화한다.

## 6.1 LLM은 stateless

LLM API 호출은 독립적이다. 이전 대화를 기억하는 것처럼 보이는 이유는 이전 message 목록을 다음 요청에 다시 전달하기 때문이다.

```text
Session ≈ 이번 대화의 message/context 묶음
```

실서비스 세션에는 단순 message 배열 외에도 최소 다음이 필요하다.

- session ID
- user/tenant와의 소유 관계
- 생성/만료 시각
- 어떤 상태가 세션에 속하는지

## 6.2 State scope와 격리

state는 대화 텍스트 밖에서 참조하는 부가 정보다. 개인/임시/공용 정보를 한 저장소에서 무구분으로 프롬프트에 넣으면 다른 사용자 정보가 섞일 수 있다.

예시 개념:

```text
user:*  개인 범위
app:*   공용 범위
temp:*  현재 세션/작업 범위
```

안전 원칙:

> “모델에게 누설하지 말라고 부탁”하는 것이 아니라 **애초에 허용되지 않은 정보를 Context에 넣지 않는다.**

특히 tenant 경계는 같은 tenant 안의 user 경계보다 먼저 확인해야 한다.

## 6.3 Session vs Long-term Memory

- **Session**: 화이트보드. 현재 대화에서만 필요한 정보.
- **Long-term Memory**: 파일 캐비닛. 다음 세션에도 필요한 핵심 사실을 별도로 저장.

세션 전체를 장기 저장하는 것이 아니라 재사용 가치가 있는 핵심만 저장한다. 민감정보나 사용자가 저장을 거부한 정보는 재사용 가치와 별개로 저장 후보에서 제외한다.

## 6.4 Memory 조회: load vs preload

- **Reactive load**: 모델이 필요하다고 판단할 때 조회. 비용 효율적이지만 조회 필요성 판단도 모델에 맡김.
- **Preload**: 대화 전에 관련 Memory를 미리 주입. 누락 가능성은 줄지만 매 요청 비용이 듦.

조회 결과는 단순 `found/not_found`가 아니다.

```text
found
stale
forbidden
not_found
```

상태마다 후속 행동이 달라야 한다.

## 6.5 Memory 4분류

```text
Short-term  현재 세션 작업 기억
Long-term   세션 밖에 보존한 재사용 정보
Episodic    특정 사용자/업무에 실제 있었던 사건의 시간순 기록
Semantic    비교적 안정적인 규칙·정책·지식
```

Episodic과 Semantic은 서로 대체할 수 없다. “무슨 일이 있었는지”만 알아도 규칙을 모르면 판단을 만들 수 있고, 규칙만 알아도 개인 사건을 모르면 엉뚱한 결론이 날 수 있다.

Semantic 규칙이 여러 버전으로 충돌하면 모델에게 임의 선택을 시키지 말고 코드/버전 정책으로 먼저 정리하며, 애매하면 `확인 필요` 상태를 유지한다.

## 6.6 Context Window는 예산이다

모델의 최대 context와 실제 서비스가 사용할 context budget은 다르다. 비용·latency 때문에 최대치보다 작은 예산을 운영 정책으로 잡을 수 있다.

단순 `oldest-first` 삭제는 처음에 말한 핵심 사실을 먼저 버릴 수 있다.

전략 예:

- rolling window
- truncate middle
- 중요도 기반 보호
- 외부 state/memory로 이동

핵심은 **위치가 아니라 중요도와 사용 목적**으로 무엇을 남길지 정하는 것이다.

## 6.7 Compaction

오래된 대화를 단순 삭제하지 않고 핵심 사실을 요약해서 Context를 줄이는 방법이다.

검증할 때는 압축률만 보면 안 된다.

```text
Compression ratio + 핵심 사실 recall
```

질문 하나에 답했다고 안전한 것이 아니라, 보존해야 할 여러 사실을 고정하고 회수율을 측정한다.

## 6.8 Selection

모든 Memory를 넣는 대신 현재 요청과 관련된 정보만 선택한다.

- “관련된 것만” 같은 느슨한 기준은 실패할 수 있음
- 명시적인 key/identity/relevance 기준을 둠
- **관련성**과 **이 목적에 사용해도 되는 권한**을 분리

같은 사람 정보라도 현재 목적에 사용할 수 없는 데이터면 Context에 넣지 않는다.

## 6.9 긴 대화의 품질 저하를 실측

긴 대화는 “몇 턴이면 항상 무너진다”가 아니라 고정된 사실/정정 시나리오에 노이즈 턴을 추가하고 동일 기준으로 측정한다.

예:

```text
명확한 정정 사실 고정
+ 무관한 대화 0 / 3 / 6턴
→ 마지막에 정정 사실 회수 정확도 측정
```

핵심 사실을 매 턴 재주입해야 한다면 그것을 priority state/memory로 승격하는 정책을 실험할 수 있다.

---

# 7. Prompt Management와 Release Gate — 2026-09-15 신규 보강

프롬프트는 단순 문자열이 아니라 운영 중인 버전 자산이다.

## 7.1 Release Manifest

Prompt와 모델, 평가셋, grader 버전을 함께 고정한다.

```text
PromptReleaseManifest
- prompt/version
- model
- dataset/version
- grader/version
- release candidate id
```

어느 점수가 어느 조합에서 나왔는지 재현 가능해야 한다.

## 7.2 baseline vs candidate

- 같은 평가셋
- 같은 모델 조건 또는 비교 조건 명시
- 같은 grader
- 같은 반복 횟수

으로 baseline과 candidate를 비교한다.

## 7.3 critical case는 반복

위험 사례는 한 번 통과했다고 성공으로 보지 않는다. 신규 강의 예시는 critical 사례를 반복해 `pass^3`처럼 반복 안정성을 본다.

## 7.4 PROMOTE / HOLD / ROLLBACK

```text
candidate
  ↓ fixed eval
release gate pass? ── No → HOLD
  │
 Yes
  ↓
PROMOTE
  ↓ production observation
abnormal? ── Yes → ROLLBACK
```

Langfuse의 **불변 version**과 이동 가능한 **label**을 구분하고, production label은 gate를 통과한 version에만 이동한다.

출시 기록은 파일/Worklog에도 남겨 나중에 “왜 이 prompt를 올렸는가”를 복구할 수 있게 한다.

---

# 8. Langfuse — Observability, Prompt Management, Evaluation

세 축을 함께 운영한다.

```text
Observability
무슨 일이 있었나? 어디서 느렸나? 어떤 Tool을 썼나?

Prompt Management
어느 prompt/version이 운영 중인가? 무엇을 왜 바꿨나?

Evaluation
바꾼 뒤 실제 품질이 좋아졌나? 회귀는 없나?
```

## 8.1 Trace 설계

개념:

```text
trace       사용자 요청 한 건 전체
span        일반 작업 구간
generation  LLM 호출
agent       Agent 판단/실행 구간
tool        Tool 호출
```

Trace에서 추적할 후보:

- input/output
- model
- token/cost
- latency
- retry 여부
- prompt version
- user_id / session_id
- Tool calls
- validation result / error type

`session_id`는 여러 trace를 관측상 묶는 식별자이지, 자동 Memory 기능이 아니다.

## 8.2 Own DB와 Langfuse 역할 분리

```text
Own DB / Event Store
= 서비스 상태와 정본(Source of Truth)

Langfuse
= trace, prompt/model/tool 맥락, latency, token/cost, score와 분석
```

관측 플랫폼 기록을 업무 정본으로 착각하지 않는다.

## 8.3 Eval

- 고정 Dataset을 먼저 만든다.
- 정상뿐 아니라 경계/실패 유도 사례를 포함한다.
- 종합 점수 하나로 뭉개기보다 도메인 핵심 축을 분리한다.
- 변경 후 같은 Dataset으로 다시 측정한다.
- LLM-as-judge를 쓴다면 생성 모델과 다른 judge를 고려하고 사람 판정과의 불일치를 기록한다.

---

# 9. FastAPI, Docker, 데이터 저장

## 9.1 FastAPI

FastAPI는 Pydantic을 통해 request parsing, validation, schema, docs를 연결하기 좋다.

권장 분리:

```text
router/controller
  ↓
service
  ↓
LLM / MCP / domain adapters
```

LLM 호출을 UI/router 여러 곳에 흩뿌리지 않고 service layer에 모으면 이후 교체가 쉽다.

HTTP 상태는 의미에 맞게 구분한다.

```text
400 business rule
401 unauthenticated
403 unauthorized
404 not found
409 conflict / approval missing if contract defines so
422 schema/input validation
5xx internal/upstream failure
```

## 9.2 Docker

목표는 “내 PC에서 됨”이 아니라 같은 명령으로 재현하는 것이다.

- `.env.example` 제공
- secret 미커밋
- Dockerfile / compose
- health check
- README 실행 절차

## 9.3 DB / 실행 원장

실험이나 단일 인스턴스에서는 SQLite, 서비스 운영에서는 Postgres/Supabase 등을 고려할 수 있다.

기술 실패와 사람 검토 상태를 분리한다.

```text
validation_success = true
human_review_required = true
```

둘은 동시에 참일 수 있다.

---

# 10. Grounding, Prompt Injection, 신뢰성

- 모델이 생성한 숫자나 근거를 사실처럼 확정하지 않는다.
- 가능하면 원문 ID, 문장 ID, source, as_of와 연결한다.
- 외부 Tool/문서의 문자열에 포함된 지시를 시스템 규칙보다 높은 권한으로 취급하지 않는다.
- Skill은 고정 판단 기준, MCP는 구조화된 최신 사실이라는 경계를 유지한다.
- unsupported / unavailable / stale / conflicting 상태를 명시적으로 반환한다.
- 사람 판정과 모델 판정을 구분하고, 평가 정답을 생성 모델 입력에 섞지 않는다.

---

# 11. Project2에서 RAG / LangGraph 경계

공식 필수·허용·금지와 RAG 판정 기준의 canonical은 [요구사항](../REQUIREMENTS.md)의 「공식 기술 경계」다. 일반 수업에서 소개한 Memory selection·compaction·임베딩 예시를 프로젝트 적용 승인으로 해석하지 않는다. 말해봄은 [팀 자율 제약](../CONSTRAINTS.md)에 따라 벡터 DB·임베딩 검색·장기 누적 코칭을 추가하지 않는다.

교육적 설계 관점에서는 고정된 판단 기준을 Skill로, 허용된 개별 상태·구조화 사실을 MCP로 제공하는 경계를 참고한다.

---

# 12. 말해봄에 적용할 때의 체크포인트

> 아래는 강의 내용을 말해봄 기획에 적용한 **프로젝트 적용 메모**이며, 강의 원문 자체의 요구사항은 아니다.

## 12.1 State / Session

- `user_id`, `session_id`, `attempt_id`, `revision_id`의 소유 관계를 서버에서 검증한다.
- 다른 사용자의 연습 기록이 LLM Context에 들어오지 않게 조회 단계에서 차단한다.
- 1차/2차 답변 비교는 같은 공고·질문·기준 버전으로 고정한다.
- 현재 MVP가 장기 누적 코칭을 제외하므로, 일반적인 장기 Memory 시스템을 새로 만드는 것은 현재 범위에 포함하지 않는다. 관련 설명은 교육용 참고다.

## 12.2 Tool / MCP

원시 CRUD를 많이 노출하기보다 실제 코칭 흐름에서 필요한 소수의 조회 도구로 묶는 편이 적합하다.

예시 후보:

```text
get_job_context(...)
get_question(...)
get_practice_attempt(...)
compare_attempts(...)
```

Tool 결과에는 가능한 범위에서 다음을 포함한다.

```text
record/version id
source
as_of
status
```

## 12.3 Prompt release

- 같은 평가셋으로 prompt baseline/candidate를 비교한다.
- prompt version, Skill version, dataset version, model을 함께 기록한다.
- 실패 유도/critical 사례는 반복 실행해 안정성을 본다.
- gate 미통과 버전을 production으로 올리지 않고 이전 검증 버전으로 rollback 가능하게 한다.

## 12.4 권한과 비범위

말해봄은 사용자의 경험을 수정하거나 채용 합격 여부를 판정하는 서비스가 아니다. 따라서 다음은 권한 계약과 비범위로 명확히 둔다.

- 사용자가 말하지 않은 경험·성과 생성 금지
- 확인되지 않은 개인 행동 추측 금지
- 합격 가능성 판정 금지
- 공고에 없는 기업 요구사항 생성 금지
- 실제 사용자/검토자 데이터의 보관 범위와 동의를 별도 관리

---

# 13. 구현 중 빠르게 보는 점검표

```text
[ ] LLM에게 맡긴 판단과 코드가 강제할 조건이 분리되어 있는가
[ ] 모든 LLM 출력에 구조화 계약과 Validator가 있는가
[ ] 실패 종류별 retry / fallback / user message가 있는가
[ ] Tool은 endpoint 목록이 아니라 사용자 workflow를 반영하는가
[ ] Tool 응답에 source / as_of / status / limitation이 필요한가 검토했는가
[ ] read / write / risk / scope / approval 경계가 있는가
[ ] session/user/tenant 데이터가 프롬프트 전에 격리되는가
[ ] context budget과 보존해야 할 핵심 사실을 정의했는가
[ ] Prompt/Skill/model/dataset version이 추적 가능한가
[ ] Langfuse trace에서 retry·tool·prompt version·latency·cost를 추적 가능한가
[ ] 같은 평가셋으로 변경 전후를 재측정하는가
[ ] RAG / LangGraph를 Project2 코드에 넣지 않았는가
[ ] 구현하지 않기로 한 기능과 이유가 문서화되어 있는가
```

---

# 14. 주요 원자료 위치

- 기존 통합 지식베이스: `nanocode00/factory-agent-hub/knowledge/agent-engineering.md`
- Drive 루트: `https://drive.google.com/drive/folders/1dgs2PekmLTTZVVEzawHbetbiXHLvFJ9n`
- 신규 보강 폴더: `3. 메모리/컨텍스트와 신뢰성`
- 신규 보강 폴더: `4. MCP_Server`
- 신규 보강 폴더: `Practice_MCP`
- 기존 보강 자료: `Practice_Langfuse`

이 문서는 실습 코드를 복사하기 위한 문서가 아니라, **왜 그렇게 설계하고 무엇을 검증해야 하는지 복구하기 위한 지식 문서**다.
