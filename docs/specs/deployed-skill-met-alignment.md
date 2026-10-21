# 운영 Prompt와 Skill의 met 조건 정합화

## Why
2026-10-09 운영 revision `malhaebom-mk2-reference-finish-1009-verified`의 Langfuse `malhaebom-coaching-v5-reinforced-verification@4`는 반복·측정 유형만 결과 확인 met으로 인정하는 판정표를 포함한다. 같은 이미지의 Skill은 방법·조건과 연결된 정성적 결과도 인정한다. criteria.json에는 연결 조건이 축약됐으며 action_rationale 설명은 대안 비교를 요구하는 것으로 읽힐 수 있다.

## Goal
운영 본문에서 만든 새 후보의 도메인 판정 기준은 Skill에서만 제공한다. 문제 해결 6개 기준 × 4개 상태의 JSON 계약을 유형 문서와 일치시키고 재발 검사로 고정한다. 운영 배포·Langfuse 쓰기·기존 Prompt 수정·모델/평가셋 변경·머지는 제외한다.

## What
- 후보 Prompt는 역할·입력/실행 경계·출력 계약·안전 경계를 유지하고 판정표/가상 판정 예시를 제거한다.
- 운영의 사실·주체·부정·사건 연결 보존 규칙 중 Skill에 부족한 부분만 보완한다.
- met 조건은 현재 답변의 정확한 인용과 활성 Skill 정의를 함께 따른다. 테스트/목표 확인 자체를 관찰 결과로 바꾸지 않는다.
- 과거 v4/v5 실험 및 local fallback/default는 재현용으로 보존한다. 새 후보는 명시 선택만 가능하며 승격은 별도 평가/승인 대상이다.

## How
- 출처는 운영 immutable image `sha256:d3cd9b7d941eac39fb04f96e211bf6882b8291454050f7b0d3bfcad67a3663d1`와 읽기 전용으로 조회한 원격 Prompt @4다. 본문 SHA256은 Worklog에 기록한다.
- 먼저 운영 Skill을 고정한 상태에서 새 Prompt의 ownership/합성을 확인하고, 이후 Skill 카탈로그 정합화만 별도로 확인한다.
- 새 selector `coaching-v5.4-skill-met-aligned`를 canonical builder에 추가한다. 기본값·환경 설정은 변경하지 않는다.
- Skill 버전은 `interview-coach-v6.2-met-aligned`; 질문 호환 criteria_version은 기존 `problem-solving-v4-draft.3`를 유지한다. 원래 판정 의미를 바꾸는 신규 평가 기준을 도입하지 않는다.
- JSON Schema·ID/원문 검증은 서버 책임이다. 문장의 met 의미를 서버의 키워드 검사로 대신하지 않는다.

## AC
1. Given 새 후보와 임의 Skill When 합성 Then 후보 자체에 과거 met 분류/판정표/사례가 없고 제공된 Skill만 적용된다.
2. Given 문제 해결 유형 When 규칙을 로딩 Then 6개 기준의 4개 상태가 JSON과 유형 문서에서 동일하다. 한쪽만 변경한 fixture는 검사에 실패한다.
3. Given 결과 확인 met When 정의를 읽음 Then 방법·조건과 실제 관찰 결과의 연결 및 정성적 결과 허용이 동일하며 반복 횟수·측정 숫자를 필수로 요구하지 않는다.
4. Given 원인 연결/행동 선택 이유 When 카탈로그를 읽음 Then 관찰-판단 또는 선택-이유 연결을 요구하며 대안 비교/특정 접속사를 필수로 요구하지 않는다.
5. Given 기존 selector/default When 생성 Then 과거 템플릿이 유지된다. 메타데이터·관련 계약 테스트가 통과한다.
