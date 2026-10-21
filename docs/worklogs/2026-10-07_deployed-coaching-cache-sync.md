# 운영 코칭 캐시와 분석 모델 연결 동기화

- pinned 운영 이미지의 OpenRouter Gemini 3.5 system-only cache-control과 cached token/hash 관측 필드를 반영한다. 사용자 답변은 캐시 표시 대상이 아니다.
- README·이력서 분석 모델은 운영 google/gemini-3.1-flash-lite로 맞춘다.
- main의 실제 Prompt/Skill 저장 provenance, Skill catalog 기반 버전, 안전 경계·Prompt v5 지원은 유지한다. 운영 이미지의 과거 코드로 이를 되돌리지 않는다.
- 코칭·관측·README·이력서 64 tests 통과. 모델 호출·배포·운영 설정 변경 없음.
