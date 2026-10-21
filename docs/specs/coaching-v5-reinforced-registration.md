# 배포 v4 기반 보강 후보를 v5로 등록

## Why
2026-10-05 보강한 배포 v4 기반 후보가 로컬에만 있어 코드와 관리형 Prompt에서 명시적으로 선택할 수 없다.

## Goal
후보 본문을 변경하지 않고 `coaching-v5-reinforced-verification`으로 등록하고 Langfuse 후보 버전·해시를 고정한다. GitHub PR만 생성하고 병합·배포·production 라벨 이동은 제외한다.

## What
- 개인/팀 행동, 명시적 미수행, 판정 독립성, 확인 질문과 예시 사실 보존을 보강한 어제 후보를 보존한다.
- 기존 `coaching-v5-skill-owned`와 v4 기본값은 유지한다.
- 명시적 `COACHING_PROMPT_VERSION=coaching-v5-reinforced-verification` 선택을 지원한다.

## How
- 후보 본문 SHA256은 `ed39574026c68be510dad31fb9b8b5077fc92f11848a72c9105f3f16b8bfd9f9`이다.
- Langfuse 이름은 `malhaebom-coaching-v5-reinforced-verification`, 라벨은 `candidate`다. 코드 v5와 Langfuse 숫자 버전은 다른 개념이다.
- 모델·Skill·서버 검증·출력 상한을 변경하지 않는다. 어제 후보 runtime 수정은 가져오지 않는다.
- 이 후보는 배포 v4 기반 실험 snapshot이라 도메인 판정표와 경계 예시를 Prompt 본문에도 포함한다. 따라서 **새 canonical rule source가 아니며 그대로 production 승격하지 않는다.** 이후 승격 후보는 Skill bundle을 단일 기준원으로 사용하는 `coaching-v5-skill-owned` 구조로 옮긴 뒤 재평가한다.

## AC
- Given 새 v5 명시 선택, When runtime·평가 builder 호출, Then 동일 후보 템플릿과 현재 Skill을 결합한다.
- Given 버전 미설정, Then 기존 v4 기본값을 선택한다.
- Langfuse 숫자 버전·본문·candidate 라벨을 재조회해 GitHub 후보 파일과 해시 일치를 확인한다.
- 운영 v4 production 라벨·Cloud Run revision 및 트래픽을 보존하고 PR은 미병합 상태로 둔다.
