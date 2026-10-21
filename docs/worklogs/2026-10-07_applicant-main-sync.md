# 승인·머지된 #178의 main 동기화

- #178은 resume-deployed-sync 브랜치에만 머지돼 main에 빠져 있었다.
- 원래 변경과 커밋 이력을 보존한 merge로 main에 동기화한다. 최신 main 상태 문서도 유지한다.
- 검증: applicant_context 및 NCS 관련 pytest 30 passed (Python 3.13, mock).
- 운영 환경은 변경하지 않는다. DB migration은 저장소에 포함되지만 이번 작업에서 운영 DB에 실행하지 않는다.

- CI에서 다른 PR #195의 source-manifest 해시 오탐 4개가 전파돼 secret scan이 실패했다. PR은 해당 base..head, main은 HEAD의 전체 도달 가능한 이력을 검사하도록 범위를 명시하며 탐지를 비활성화하지 않는다.
