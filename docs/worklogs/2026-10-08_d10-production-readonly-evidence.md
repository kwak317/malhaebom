# 2026-10-08 D10 운영 Prompt·출력 계약 실증 및 접근 한계

## 목적과 범위

기존 D10 체크리스트의 Langfuse 관측·관리형 Prompt 연결을 **사용자 제공 화면 및 읽기 전용 조회**로 검증한 결과를 비식별 기록한다. Cloud Run 배포, Prompt label/버전 수정, 사용자 DB 접근, 신규 LLM 요청, rollback은 실행하지 않았다.

## 근거와 직접 관측

- **출처 A — 사용자 제공 Langfuse Cloud Tracing/Prompts 캡처(10/8):** 화면의 Langfuse 프로젝트는 10/6 후보 등록 manifest(`docs/evidence/coaching-v5-reinforced-registration-2026-10-06.json`)의 프로젝트 ID와 일치했다. 원본에는 user/session ID·SDK public key 등 식별 정보가 있어 화면 원본과 ID 원문은 Git에 추가하지 않는다.
- **출처 B — 저장소의 후보 등록 이력:** 10/6 `malhaebom-coaching-v5-reinforced-verification`이 #1 `candidate`로 등록됐고 당시 운영 배포 변경은 없었다. **10/8 관측 상태를 10/6 기록으로 소급 적용하지 않는다.**
- **출처 C — 읽기 전용 CLI/SDK 탐색:** 로컬 Langfuse 키 `auth_check=True`, **다른 Prompt인** `malhaebom-coaching`의 `candidate` v3와 `latest`는 있으나 이 이름의 `production`은 404. 이는 *이번 운영에서 확인한 reinforced Prompt의 production 부재*를 의미하지 않는다.

| 항목 | 2026-10-08 관측값 | 판단 범위 |
| --- | --- | --- |
| 관리형 Prompt 이름 | `malhaebom-coaching-v5-reinforced-verification` | 과거 등록 manifest의 별도 reinforced 후보 |
| Langfuse Prompt 버전/라벨 | **#4, `production` 및 `latest`** | `coaching-output-v4` 코드 버전과 무관한 **관리형 숫자 버전** |
| Prompt 연결 이력 | #4 `Linked Generations`에서 지난 1일간 약 80건의 `coaching.provider` | 카운트는 화면의 시간 범위에 종속됨 |
| 특정 코칭 호출 | 10/8 12:38:46(KST) `coaching.provider`, `google/gemini-3.5-flash-lite` | 약 8.19초, 24,266 tokens, $0.006809, `outcome=success`, HTTP 200, 재시도 없음 |
| 실제 버전 연결 | **동일 trace ID**를 Tracing과 #4 Linked Generations에서 대조, generation Attributes `version=malhaebom-coaching-v5-reinforced-verification@4` | **이 코칭 호출은 관리형 Prompt #4에 연결됨** |
| 서버 출력 검증 | 같은 trace의 `coaching.output_validation`, input contract `CoachingLLMOutput`, **`valid=true`, `error_count=0`** | 구조/서버 계약 통과. 내용 정확도나 보안 품질 판정은 별개 |
| Skill 메타데이터 | `coaching.provider`와 `coaching.output_validation`에 **`interview-coach-v6`**로 동일 표시 | 실제 로드된 Skill 번들 SHA/내용은 확인하지 못함 |
| trace 트리 | `coaching.provider`, `coaching.output_validation`, `coaching.analyze` 같은 트리에 존재 | Cloud Run revision, HTTP request ID 또는 DB 행과의 1:1 연결은 미확정 |

## 공개 URL 및 권한 점검

- 공개 Frontend `https://www.malhaebom.xyz/`에 대해 10/8 익명 GET **HTTP 200** 확인. 문서화된 Cloud Run health 주소 두 개는 해당 로컬 런타임에서 5초 timeout이었고 **서비스 장애라고 단정하지 않는다**.
- 현재 로컬 `gcloud` 계정이 목록 조회할 수 있는 프로젝트는 4개였으며, 운영 URL의 프로젝트 번호에 해당하는 프로젝트는 그 목록에서 확인되지 않았다. 기본 프로젝트의 `asia-northeast3` 서비스에서 `malhaebom-stt-benchmark`만 말해봄 관련 이름으로 확인했다. 타 프로젝트 두 곳은 리소스 목록 조회 실패였다. **실제 운영 `malhaebom-mk2` revision/이미지/배포 commit에 대한 접근 증거가 없다.**
- 사용자는 실제 Cloud Run 운영 계정이 본인 계정이 아니어서 콘솔 접근이 어려울 것으로 알렸다. 추가로 권한 없는 리소스를 변경하거나 권한 우회는 시도하지 않았다.

## 확정·미확정 경계

**확인:** Langfuse Cloud 한 코칭 실행에서 관리형 Prompt reinforced **@4**가 사용되고 모델 호출이 성공했으며 같은 trace의 **서버 출력 계약 검증은 PASS**였다. 10/8 화면에서 이 버전의 `production` 라벨도 확인했다.

**미확정:** 이 호출을 처리한 **Cloud Run revision/배포 commit**, 실제 로딩된 Skill 코드/번들(메타데이터 값은 v6), Supabase `coaching_runs` 행과 동일 요청 상관관계, PlayMCP 도구 호출 연결. `valid=true`가 코칭의 의미 품질 또는 인젝션 방어 성공을 의미하지는 않는다.

**D10 Prompt release/rollback은 미완료:** 10/6 candidate #1에서 10/8 production #4로 상태가 달라졌다는 화면은 있지만, 승인 gate·릴리스 manifest·전환/롤백 전후의 동일 운영 요청 증거를 확보하지 못했다. 사용자에 따르면 기능 수정이 예정되어 있어 실제 운영 변경을 수행하지 않았다.

## 후속 조건

1. 운영 담당자에게 현재 Cloud Run 활성 revision/배포 commit, `COACHING_SKILL_VERSION` 명시 설정 여부, 컨테이너의 Skill catalog 버전/번들 SHA **비식별 값만** 요청.
2. 운영 Langfuse trace와 같은 Cloud Run request ID 및 DB 기록이 연결되는지, 운영 담당자가 접근 가능한 환경에서 확인.
3. 기능 변경 및 운영 승인이 끝난 뒤에만 Prompt 전환·실제 rollback을 runbook(`docs/runbooks/d10-production-evidence-capture.md`)대로 실행. 현재는 release/rollback 미완료를 유지.

이번 PR은 **기록과 상태 정리 전용**이며 운영 설정을 변경하지 않았다.
