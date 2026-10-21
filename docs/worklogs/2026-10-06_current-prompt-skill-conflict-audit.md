# Worklog — 현재 v5 Prompt + Skill 중복·충돌 점검

- 일시: 2026-10-06
- 범위: 저장소 정적 조립 검증. provider/E2E 호출 없음.
- 대상: 현재 작업·평가 기준 `coaching-v5-skill-owned` + 현재 GitHub Skill.

## 정정

초기 점검에서 local fallback/default v4를 “현재 Prompt”로 잡아 현재 작업 기준과 배포 재현 기준을 섞었다.
현재 Prompt로 다루는 v5는 `coaching-v5-skill-owned`이며, #185 Skill A/B도 이 버전을 고정한다.

별도 `coaching-v5-reinforced-...` 후보는 Langfuse candidate로 등록됐지만 등록 시점에는 production 승격되지 않았다.
마지막 저장소 운영 증거 역시 v4 production을 기록하므로, 실제 live production 버전은 정적 저장소 점검과 분리한다.

## 수행

1. `coaching-v5-skill-owned`와 현재 Skill을 canonical builder로 실제 합성했다.
2. intent/C/A/V 및 result_verification 도메인 marker의 소유 위치를 대조했다.
3. v5 조립 결과에는 archived v4의 도메인 판정표·V gate가 없고 Skill 규칙만 한 번 포함됨을 테스트로 고정했다.
4. archived v4의 중복·충돌 가능성은 현재 v5 문제가 아니라 재현/배포 계열 기술부채로 별도 기록했다.

## 결론

현재 v5 Prompt + Skill의 도메인 규칙은 Skill 단일 소유로 정리되어 있어 중복·충돌 검증 항목은 완료 처리한다.
실제 production이 v5인지 여부는 D10 운영 증거에서 Langfuse managed Prompt/Cloud Run 설정을 확인한다.
