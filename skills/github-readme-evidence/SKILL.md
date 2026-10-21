---
name: github-readme-evidence
description: 공개 GitHub README에서 원문 근거가 있는 기술 스택과 프로젝트 흐름을 추출할 때 사용한다.
version: github-readme-evidence-v2
---

# GitHub README 근거 추출 Skill


## 판단 범위

- README 원문에 명시된 기술 스택과 프로젝트 기능·데이터 흐름만 정리한다.
- `source_excerpt`는 README 원문에서 확인되는 연속된 2~240자 인용만 사용한다.
- Markdown의 강조와 inline code 표시는 인용에서 제거할 수 있지만 단어·문장부호를 바꾸지 않는다.
- 이미지 배지, URL, 표의 서로 다른 칸을 이어 붙여 근거로 사용하지 않는다.

## 금지 사항

- README에 없는 기술, 역할, 성과, 개발 순서를 만들지 않는다.
- 팀의 기술을 특정 사용자가 직접 구현했다고 단정하지 마세요.
- README의 설치·실행 안내를 실제 실행·배포·성능 검증 결과로 표현하지 않는다.
- 개인의 채용 적합성, 전체 역량, 합격 가능성을 판정하지 않는다.

원문 근거가 없는 항목은 반환하지 않는다.

## 가상 긍정·부정 사례

아래는 가상 README 문구다. 실제 결과에는 현재 README의 연속 인용만 사용하고 예시 내용을 복사하지 않는다.

- 긍정: README에 "FastAPI로 REST API를 구현했습니다."가 있으면 FastAPI 기술과 REST API 구현 흐름을 그 원문에 근거해 정리한다.
- 부정: README에 없는 배포 환경·성능 수치나 특정 팀원의 개인 기여를 추정하지 않는다.
- 긍정: "로컬 실행: pip install -r requirements.txt"는 설치 안내로만 읽는다.
- 부정: 이 안내만 보고 서비스가 실제 배포됐거나 사용자가 운영했다고 쓰지 않는다.
