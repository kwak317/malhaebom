# D10 운영 관측 기반 개선 가설 및 사후 검증 계획

- 작성: 2026-10-02, `#162`·`#163` 병합 후
- 종류: **기존 사용자 화면 및 소스 기반 가설·사전 계획**. 새로운 운영 요청, GCP 로그 조회, 배포·Langfuse 설정 변경 없음.
- 기준: [10/2 운영 증거 교차검증](2026-10-02_evaluation-evidence-gap-audit.md), [PR #162](https://github.com/aihuman-7th/proj2-3/pull/162), [공식 D10 체크리스트](../project2-checkpoint-work-cards.md)

## 1. 관측과 해결·미해결 경계

| 항목 | 관측 사실 | 해석 범위 |
| --- | --- | --- |
| 외부 사용자 흐름 | 사용자가 운영 브라우저에서 로그인 → 공고 검색 → 선택 공고 원문 분석 → 연습 → 1·2차 비교 성공을 보고했다. Frontend/Cloud Run health와 CORS의 공개 read-only 점검도 각각 HTTP 200이었다. | 사용자가 실제 완료한 서비스 기능의 수동 증거다. PlayMCP 도구 내부 호출 로그나 운영 리비전 연결은 별개다. |
| 당시 인증 실패 | 초기 공고 검색 시 PlayMCP 인증 안내가 표시됐으나 이후 정상 사용이 보고됐다. | 복구 사실을 보존한다. 당시 원인·갱신 방식은 로그 없이 확정하지 않는다. |
| Langfuse 코칭 성공 | 10/2 약 14:28의 Cloud trace에서 `coaching.provider` 성공/HTTP 200·재시도 없음, `coaching.output_validation` `valid=true`·오류 0, `coaching.analyze` 정상 상태 `needs_more_info`. 총 16.00초·17,428 tokens·$0.008467. | 코칭 모델 호출과 계약 검증 및 결과 관측 성공. 한 번의 관측값을 서비스 지연·비용 통계로 일반화하지 않는다. |
| 버전 메타데이터 불일치 | 해당 provider Attributes의 **표시값**은 `skill_version=interview-coach-v6`. 현재 코드 기본 카탈로그는 `interview-coach-v6.1-domain-rules`. | **실제로 v6이 실행됐는지 미확인**. #162에서 소스 측 기본 기록값을 현재 카탈로그로 바꿨지만 운영 적용 여부는 아직 증명되지 않았다. |
| Environment/Prompt 연결 | Tracing 목록에 Environment `default`, Prompt Name 미표시. | 이 화면만으로 `production` 구분이나 관리형 Prompt 연결을 증명할 수 없다. 관리형 Prompt 미사용도 단정하지 않는다. |

## 2. D10 한 줄 재조정 가설

> 동일 코칭 trace의 Skill 표시값(v6)이 현재 기본 카탈로그(v6.1)와 다른 원인은 실제 Skill 변경 실패가 아니라 이전 기본값을 기록한 관측 메타데이터 경로일 수 있으므로, **#162 적용 리비전에서 로드한 Skill 버전과 새 trace·DB 기록을 같은 실행 단위로 대조**한다.

- **가설 H1(관측 버전 오표기):** 실제 번들 v6.1을 사용하면서 기록 경로가 기본값 v6을 보낸 경우. #162 반영 후 새로 발생한 trace와 DB가 v6.1로 같아지면 이 설명과 일치한다. 단, 당시 v6 실제 로드 가능성을 소급 제거하지는 못한다.
- **대안 H2(운영 리비전의 다른 코드·설정):** 관측 당시 운영 이미지 자체가 다른 번들 또는 명시적인 `COACHING_SKILL_VERSION`을 로드한 경우. 당시 리비전·환경 값의 **존재/버전만** 확인하고 Secret 원문은 보지 않는다. #162 병합만으로 이미 배포됐다고 추정하지 않는다.
- **관측 설정 H3:** Langfuse `default`/Prompt Name 미표시는 명시적 environment·관리형 Prompt 연결의 누락 또는 UI 표기 차이일 수 있다. 설정값과 trace의 Prompt 버전·label을 같이 확인하되, `default` 자체를 실패로 판정하지 않는다.
- **과거 인증 실패 H4(낮은 우선순위):** `PLAYMCP_AUTH_FILE` 제공·0600 권한·token refresh 중 하나가 원인이었을 가능성은 남는다. 현재 복구 보고로 해결된 증상인 만큼 재발 시에만 `PlayMCP authentication failure: <오류 유형>`과 리비전·시각을 요청한다.

## 3. 운영 담당자가 확인할 최소 증거(민감값 제외)

1. 실제 적용된 Cloud Run **revision / 배포 commit**과 `#162` 포함 여부.
2. 같은 새 코칭 요청의 런타임 Prompt 버전·Skill 카탈로그 버전/번들 해시, Langfuse provider `version`·`skill_version`, Supabase `coaching_runs`의 해당 버전. 기록이 일치하는지만 결과에 남긴다.
3. 해당 요청의 Langfuse `environment`, 관리형 Prompt를 사용했다면 Prompt Name/Version/`production` label. 사용하지 않았다면 **unmanaged**로 정확히 표기한다.
4. 같은 운영 사용자 흐름의 **PlayMCP 실제 도구 호출 → 추천 응답 → 원문 분석 응답** 연결 시각·요청 상관관계(redacted). 코칭 stdio MCP 로그와 구분한다.
5. 실패/성공 관측의 trace 트리와 모델·latency·token·cost만 캡처한다. 사용자/세션 ID, API 키, 토큰, 원문 답변·공고 URL을 제거하고 제출한다.

위 항목을 새 요청으로 확인하기 전까지 **D10 배포 URL은 완료**, **관측 trace 증거는 부분 완료**, **가설 문서 작성만 완료**, **관리형 Prompt release/rollback은 미완료**로 관리한다. 기존 추적 기록이나 DB 행을 소급 변경하지 않는다.
