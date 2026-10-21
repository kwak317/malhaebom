# Project2 제출 증거 인덱스

> 기본 인덱스 점검: 2026-10-06 10:45 KST. **후속 검증 반영: 2026-10-08 KST** (아래 D12 정합성 섹션; 10/6 당시 상태와 구분)
> 원칙: 파일·링크·실행 증거가 실제로 확인된 항목만 완료로 표시한다. 문서의 존재와 품질·최종 제출 완료를 구분한다.

## 제출 준비 현황

| 제출 항목 | 상태 | 현재 증거 | 남은 작업 |
| --- | --- | --- | --- |
| GitHub 저장소·README·`.env.example` | [x] | [README](../README.md), [.env.example](../.env.example) | 최종 동결 직전 secret scan·링크 재검증 |
| 서비스 UI URL | [x] | [말해봄](https://malhaebom.xyz), README 배포 주소 | 마감 직전 외부 smoke 재실행 |
| Cloud Run API·health | [x] | [Cloud Run API](https://malhaebom-mk2-fmf5h3xp4q-du.a.run.app), [/health](https://malhaebom-mk2-fmf5h3xp4q-du.a.run.app/health) | 마감 직전 health와 CORS 재실행 |
| 10분 재현 절차·Docker | [x] | README 로컬 실행 절차, `Dockerfile`, `docker-compose.yml` | 제3자 최종 재현 결과가 새 변경 뒤에도 유효한지 확인 |
| Skill·MCP Tool·접근 제어 | [x] | `skills/interview-coach/`, `mcp_server/`, D9 체크포인트 근거 | 발표용 실제 호출 화면 선정 |
| `EVAL_REPORT.md` | [-] | [평가 보고서](../EVAL_REPORT.md), [운영 이미지 반복 평가](evidence/coaching-repeat3-2026-10-06.md) | 신규 출력 사람 평가·단일 변경 전후 결과 반영 |
| Langfuse 스크린샷 3장 이상 | [ ] | [홈 대시보드 1장](evidence/langfuse/2026-09-30/home-dashboard.png)만 추적됨 | 현재 운영 trace 상세을 포함한 비식별 캡처 최소 2장 추가; Prompt/Skill·token/cost/latency·실패/retry가 보이게 구성 |
| 정상 데모 영상 1개 | [ ] | 저장소에서 영상 파일 또는 제출 링크를 확인하지 못함 | 현재 운영 revision의 로그인→코칭→재연습 정상 흐름 녹화·링크 기록 |
| 실패 데모 영상 1개 | [ ] | 저장소에서 영상 파일 또는 제출 링크를 확인하지 못함 | 인증/도구/계약 실패 중 사용자 복구 안내가 보이는 흐름 녹화·링크 기록 |
| 별도 소개 페이지 URL | [ ] | 서비스 UI 외 별도 소개 페이지 URL을 확인하지 못함 | 요구되는 별도 소개 페이지의 실제 주소 확정·README 연결 |
| 발표 PDF | [ ] | 저장소에서 발표 PDF 또는 제출 링크를 확인하지 못함 | 10/11 자정 전 최종 PDF 링크와 버전 기록 |

## 2026-10-08 D12 평가·Langfuse 증거 정합성

이 표는 **확인한 실행 결과**와 **실제 제출용 파일 확보**를 구분한다. [D11 실험 PR #215](https://github.com/aihuman-7th/proj2-3/pull/215)와 [D10 운영 관측 PR #216](https://github.com/aihuman-7th/proj2-3/pull/216)은 **미병합** 상태로 확인했으며, 해당 내용을 이미 `main`에 반영했다고 표기하지 않는다.

| 대상 | 10/8까지 확인한 것 | 제출/완료 판정과 남은 일 |
| --- | --- | --- |
| [평가 보고서](../EVAL_REPORT.md) · D12 전후 비교 | 10/2 동일 조건 30건 v4/v5 자동 통과 22/30 vs 20/30, 10/6 운영 이미지 30건×3회 별도. 10/8 신규 인젝션 3건에서 **마지막 시도 계약 v4 3/3·v5 3/3, 기대 판정 v4 3/3·v5 2/3** ([PR #215](https://github.com/aihuman-7th/proj2-3/pull/215)). | v5 **최초 계약은 1/3**으로 후속 재시도와 구분. 신규 3건은 단일 사람 검토 기준이며 독립 정답·공식 Dataset 승격·방어 효과 검증 미완료. 운영 Skill v6과 D11 Skill v6.1을 혼동하지 않는다. |
| Langfuse 상세 운영 관측 | 사용자가 Langfuse Cloud 화면에서 Prompt `malhaebom-coaching-v5-reinforced-verification@4`에 `production` 라벨, 같은 trace의 provider HTTP 200, `CoachingLLMOutput.valid=true`, `error_count=0` 확인 ([PR #216](https://github.com/aihuman-7th/proj2-3/pull/216)). | **실측 관측 근거는 확보. 제출 가능한 비식별 스크린샷 3장 이상은 미확보.** 받은 원본 화면에 사용자·세션 식별자·SDK public key가 보여 원본을 저장소·발표물에 복사하지 않는다. Cloud Run revision·실제 Skill 번들·DB 연계·rollback도 별도 미확인. |
| 최신 v5 불일치 사람 검토 7건 | 10/2 v5의 자동 불일치 7건 및 검토 양식 준비는 기존 증거에 기록됨. | 실제 사람 semantic/critical 판정 입력과 최종 승인 **미완료**. 과거 v4 팀 품질 평가·D4 정답 검토를 대신 쓰지 않는다. |
| 정상/실패 데모·코드 동결·최종 발표 PDF | 기능 수정이 계속 예정돼 있어 10/8에 완료하지 않음. | 영상 2개 및 최종 동결은 수정·검증 뒤 수행. 발표 PDF와 최종 제출 링크는 별도 확인·등록 필요. |

**선택할 Langfuse 제출 캡처:** (1) 비식별 trace 전체 트리, (2) Prompt `@4`·모델·비용·지연 및 output_validation PASS, (3) 실패/retry와 복구 처리. 민감정보가 노출된 현재 채팅 원본 이미지 여러 장을 파일 없이 그대로 제출된 3장으로 계산하지 않는다.

## 바로 제출 가능한 핵심 링크

- 서비스: <https://malhaebom.xyz>
- API: <https://malhaebom-mk2-fmf5h3xp4q-du.a.run.app>
- Health: <https://malhaebom-mk2-fmf5h3xp4q-du.a.run.app/health>
- 평가 보고서: [EVAL_REPORT.md](../EVAL_REPORT.md)
- 운영 이미지 30건×3회 평가: [보고서](evidence/coaching-repeat3-2026-10-06.md), [raw 자료](../evals/results/2026-10-06-deployed-repeat3/README.md)
- 운영 관측과 과거 사람 평가 경계: [증거 문서](evidence/observability-human-evaluation-2026-10-06.md)
- 배포 환경 공고 API 기록: [증거 문서](evidence/job-source-analysis-e2e-2026-10-01.md)
- D2~D12 작업 상태: [체크포인트 작업표](project2-checkpoint-work-cards.md)

## Langfuse 캡처 체크리스트

공개 저장소나 제출 자료에 자격증명·사용자 ID·세션 ID·전사·공고 원문을 노출하지 않는다.

1. 현재 운영 성공 trace의 전체 트리: `coaching.provider` → `coaching.output_validation` → `coaching.analyze`.
2. provider 상세: model, token, cost, latency, retry/repair 및 Prompt·Skill 버전.
3. 실패 trace 상세: 고정 오류 코드, 실패 단계, retry 여부와 사용자 응답. 정상 trace와 동일한 실행 환경임을 확인한다.

기존 `home-dashboard.png`는 전체 건수 화면이며 trace 상세 캡처를 대체하지 않는다.

## 데모 영상 체크리스트

### 정상 영상

- 운영 URL과 촬영 일시·revision을 시작 화면 또는 설명에 표시한다.
- 로그인 후 공고 선택, 답변 입력/녹음, 코칭 결과, 재연습 비교까지 끊기지 않게 보여준다.
- 사용자 원문·JWT·이메일 등 민감정보는 비식별 테스트 계정과 합성 답변을 사용한다.

### 실패 영상

- 재현 가능한 실패 한 종류만 선택한다.
- 실패 상태가 저장되고 사용자에게 재시도 또는 다음 행동이 안내되는 장면을 포함한다.
- 개발자 콘솔의 secret·원문 로그를 노출하지 않는다.

## 완료 판정 금지 항목

- API HTTP 200만으로 로그인 사용자 전체 E2E를 완료 처리하지 않는다.
- Langfuse JSON/trace 링크만으로 필수 스크린샷 3장을 제출했다고 표시하지 않는다.
- 과거 v4 사람 평가를 최신 운영 90개 출력의 사람 평가로 재사용하지 않는다.
- 저장소에 없는 영상·PDF·외부 링크를 존재한다고 추정하지 않는다.
