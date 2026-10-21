# 지원자 자료를 코칭 문맥에 연결

## Why
README·이력서 추출 정보와 NCS 자기선택이 추천 뒤 코칭에서 누락된다.

## Goal
새 세션의 세 종류 참고 자료를 코칭과 비교 후 면접 채팅의 모델 입력에 연결한다. 기존 세션은 자료 없이 유지한다. 모델·운영 Prompt·Skill·채점 계약·합격 판정·RAG·PDF 영구 보관·배포는 범위 밖이다.

## What
NCS/확인 이력서/선택 README를 세션 생성 요청에 포함하고 세션에 고정한다. README 생략과 이전 클라이언트 요청은 허용한다. 사용자 변경·새 공고 세션은 각각 새 snapshot을 사용한다.

## How
applicant_context JSONB를 practice_sessions에 추가하고 자료가 있는 요청은 별도 security invoker RPC로 세션 및 요구사항과 원자 저장한다. 기존 RPC는 유지한다. 기존 소유자/영구 사용자/만료 RLS와 MCP capability 검증을 유지한다. NCS ID는 서버의 검토 목록으로 검증하고 모델 입력에서 한국어 항목으로 변환한다. README 구조와 확인 이력서 개인정보/길이 계약을 검증한다. 자료는 사용자 제공 참고 사실이며 검증된 개인 수행 사실로 단정하지 않는다. 현재 답변의 평가 근거와 구분하고 자료 내부 지시는 무시한다. 코칭과 대화 입력에 같은 안내를 추가한다. 영구 PDF나 이력서 원문은 저장하지 않는다. 기존 Prompt 파일과 모델 설정은 변경하지 않는다.

## AC
- Given 세 자료가 있는 새 세션 When 생성 Then 저장 RPC에 세 자료가 함께 전달된다.
- Given 저장된 자료 When MCP 조회 후 코칭 또는 면접 채팅 Then 같은 세션 자료가 모델 입력에 포함된다.
- Given 기존 세션/README 생략 When 조회 Then 자료 누락을 허용한다.
- Given 다른 사용자/만료 세션 When 조회 Then 기존 소유자·만료 검증이 차단한다.
- Given 알 수 없는 NCS ID/개인 연락처 When 생성 Then 요청을 거부한다.
- Given 자료에만 있는 성과 When 코칭 Then 입력 안내와 기존 answer-segment 인용 검증이 자료를 답변 근거로 취급하지 못하게 한다. 실제 모델 준수와 품질 개선은 별도 실험이다.
