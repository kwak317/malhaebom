# 준비·1차 코칭 자유 대화 연결

## Why
준비 단계와 1차 코칭 뒤 채팅이 공고 검색으로만 연결된다. 대화 후보의 경력 확인·저장 판단을 실제 인증·저장 흐름에 연결한다.

## Goal
NCS·README·이력서·1차 코칭 질문에 Gemini 3.5가 답한다. 경력은 최신 초안에 대한 명시적 동의 후 저장하고 같은 연습의 다음 코칭·꼬리질문에 참고 자료로 제공한다. 기존 평가·원문·비교는 불변이다.

## What
채팅 → 인증 → 대화 상태/현재 자료 조회 → 모델 제안 → 서버 정책 검증 → 버전 조건부 저장 → 답변과 질문을 분리해 표시한다. 재답변 버튼 또는 명시적 요청으로 녹음/WAV를 연다. 모델 실패·소유자 불일치·초안 충돌이면 현재 상태를 유지한다.

## How
`POST /api/agent/preparation`과 `POST /api/agent/preparation/bind`. 상태는 사용자 소유 `preparation_conversations`에 24시간 보관하며 서버만 쓴다. 초기 자료는 사용자 제공 참고자료라고 표시한다. 1차 코칭은 사용자 소유 세션의 확정 revision·coaching run을 서버가 읽는다. 요청 ID 재처리 방지·DB version CAS·세션 재결합 금지. 코칭/꼬리질문 조회는 같은 사용자·세션의 확인된 추가 문맥만 읽는다. 메인 코칭 Prompt/Skill/model은 바꾸지 않는다.

## AC
- Given 타인/만료 대화, When 요청, Then 404이며 LLM/저장 없음.
- Given 경력 초안, When 모호한 동의, Then 저장 없음.
- Given 최신 명시적 동의, When DB 저장 성공, Then 완료 안내와 참고문맥 생성.
- Given 동일 요청 또는 경쟁 요청, When 처리, Then 중복 저장 없음/409.
- Given 1차 코칭 질문, When 처리, Then 해당 revision만 제공하고 재채점 없음.
- Given 모델 계약 실패, When 두 번 생성, Then 현재 상태 유지 및 실패 안내.
