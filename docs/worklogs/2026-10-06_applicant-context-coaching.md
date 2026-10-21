# 2026-10-06 지원자 자료를 3.5 코칭 문맥에 연결 (로컬)

## 목적과 구현
README 3.1 추출 결과, 사용자 확인 이력서 facts, NCS 자기선택을 새 연습 세션의 applicant_context snapshot으로 저장하고 코칭 MCP job context와 비교 후 면접 채팅 provider 입력에 전달한다. 기존 세션 NULL과 이전 클라이언트는 유지한다. NCS ID는 검토 목록으로 검증해 한국어 항목으로 변환한다. README 출처/버전/원문 근거를 보존하고 이력서는 현재 UI에서 확인한 facts만 저장한다. PDF·전체 이력서 원문은 저장하지 않는다. 클라이언트 전달 자료의 원본 3.1 산출물 진위를 보증하지 않으며 사용자 제공 참고 자료로 취급한다.

## 범위와 파일
- schemas: applicant_context.py 신규, practice_setup.py 입력, coaching.py JobContext
- services: supabase_practice_setup.py 원자 저장 RPC, supabase_coaching_context.py 조회, coaching_runtime.py 입력, interview_chat.py 조회/입력
- frontend: api/practiceSetup.ts, pages/PracticePage.tsx, PracticeSetupFlow.test.tsx
- migration: 20261006090000_practice_applicant_context.sql 신규; 기존 RPC/RLS/grant 유지
- tests: test_applicant_context.py 신규
- Spec: ../specs/applicant-context-coaching.md

Prompt·Skill 파일과 모델 선택은 수정하지 않았다. 기존 로컬 v5를 운영 후보로 승격하지 않았다. 기능 작업 폴더 proj2-3-complete-flow에서 기존 변경을 보존했으며 output/applicant-context-20261006/before에 작업 직전 백업, change.patch에 이번 증분을 보관한다. 현재 운영은 malhaebom-mk2-langfuse-v4-1006 트래픽 100%, 이미지 sha256:82b0cae6f08df6242f827f2b24791759e318c4a73b7cf6c0066e13caaa7bab75로 재확인했다.

## 검증
- applicant context suite 20 tests PASS: 스키마, 개인정보, NCS, 기존 요청, 원자 RPC 전달, 실제 서비스의 mock provider 입력, 답변 validation context 분리, MCP 저장소 조회, 채팅 입력/소유자 경계. 공통 chat test를 재사용하여 실행 개수에 반복 항목이 포함된다.
- context suites (수정 전 마지막 신규 provider 테스트 추가 이전) 25 PASS; practice setup 9 PASS; interview chat 28 PASS; coaching runtime 24 PASS. 각각 독립 실행이며 합산 고유 테스트 수로 보고하지 않는다.
- frontend 관련 33 PASS: README 제출/생략에 대한 같은 세션 전달, 기존 설정/대화 흐름. 기존 스크롤 assertion의 5ms sleep은 완료 조건 waitFor로 변경했다.
- 임시 독립 PostgreSQL 17: migration 실행 및 원자 저장·구형 RPC·잘못된 요구사항 rollback·다른 사용자 조회/비공개 공고 생성 차단·익명 차단·만료 조회 차단 PASS. auth 함수는 테스트용 JWT stub, 실제 Supabase 인증 E2E가 아니다. SQL harness: output/applicant-context-20261006/db-bootstrap.sql.
- 원본 node_modules 중복 타입 폴더 때문에 원본 npm build 실패. 해당 폴더 수정/삭제 없이 frontend-build 복사본에서 lockfile 기반 npm ci --ignore-scripts 후 tsc/Vite production build PASS.
- git diff --check PASS, 별도 읽기 전용 보안 검토 수행. 64KB 제한 불일치를 API/DB 공통 128KB로 조정하고 출처 문자열 상한을 추가했다.

## 미확인과 다음 단계
실제 Gemini 3.5 호출/코칭 품질 개선, 실제 로그인 사용자 E2E, 운영 DB 적용·배포는 미수행이다. SQL/API mock 합성 데이터 증거를 운영 증거로 취급하지 않는다. 운영 반영 승인 시 운영 기준 소스에 이번 증분만 적용하고 DB migration → backend → frontend 순서로 반영·검증해야 한다. 기존 로컬 Prompt·Skill 후보나 다른 변경은 배포에 혼입하지 않는다. 세션 만료 접근 차단은 확인했으나 물리 데이터 삭제는 기존 정리 정책을 따른다.

## GitHub 및 배포 검증 (2026-10-06)

이력서 동기화 PR #177을 base로 별도 PR을 구성했다. PR 후보 backend 85 tests, frontend 39 tests와 production build 통과. 초기 격리 테스트는 configs/mcp_server mount 누락과 신규 테스트 NavigationProvider 누락으로 실패했으며 mount/테스트 wrapper를 바로잡아 재검증했다. 운영은 기존 immutable image에 9개 app 파일만 overlay한 `malhaebom-mk2-context-ncs-1006-1230`에 트래픽 100%; 기존 Prompt/Skill/model 유지. DB migration 적용 및 JSONB 컬럼 확인. Frontend dpl_57mR9wJxWVsD4jBLuEnrXyizkSR7 promote 후 malhaebom.xyz에서 index-aYpGl2Oe.js 확인. health 200/auth 401 확인은 실제 사용자 코칭 성공 증명이 아니다.
