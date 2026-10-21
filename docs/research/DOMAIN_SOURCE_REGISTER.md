# 도메인 지식 출처 및 이용조건 등록부

> 기준일: 2026-09-30
> 목적: Project2 D3 체크포인트의 “공개 API·문서·사람 중 어디서 오는지, 라이선스 확인”을 저장소에서 추적한다.
> 이 문서는 법률 자문이 아니라 **서비스에서 사용하는 출처의 provenance와 보수적 이용정책을 기록하는 운영 문서**다.

## 판정 원칙

- “공개되어 있다”와 “자유롭게 재배포할 수 있다”를 구분한다.
- 이용허락 범위가 명시된 공공데이터는 해당 포털 조건을 따른다.
- 민간 웹페이지와 GitHub 공개 저장소는 공개 접근 가능하다는 이유만으로 원문 재배포 권한이 있다고 가정하지 않는다.
- 사람 검토는 검토자의 경험 범위·검토일·case를 기록하며, 실제 사용자 데이터는 동의 범위 밖으로 복제하지 않는다.
- 서비스에는 필요한 최소 원문/메타데이터만 사용하고, 연구·평가용 정답과 운영 사용자 원문을 분리한다.

## 현재 서비스 출처

| 출처 | 종류 | 현재 사용 위치 | 2026-09-30 이용조건 확인 | 서비스 정책 |
| --- | --- | --- | --- | --- |
| 한국산업인력공단 NCS 기준정보 조회 | 공공 OpenAPI | 백엔드 직무 자기점검/NCS 능력단위 | 공공데이터포털 dataset `15128213`: 무료, **이용허락범위 제한 없음** | 필요한 능력단위만 조회. NCS를 기업 채점표로 사용하지 않음 |
| 재정경제부 공공기관 채용정보 조회서비스 | 공공 OpenAPI | 공공기관 채용 검색 | 공공데이터포털 dataset `15125273`: 무료, **이용허락범위 제한 없음**. 운영계정은 심의 승인 조건 확인 | 채용 검색·원문 출처 연결에 사용. 원문을 임의의 정답으로 사용하지 않음 |
| 인사혁신처 공공취업정보 조회 서비스 | 공공 OpenAPI | 공공취업정보 검색 | 공공데이터포털 최신 catalog `15156780`: 무료, **이용허락범위 제한 없음** | 검색 결과를 source로 표시하고 사용자가 선택한 항목만 후속 검토 |
| ALIO 청년일자리/오픈데이터 | 공공기관 개방데이터/API | ALIO 채용 검색·검토 | `opendata.alio.go.kr` 이용약관상 공공기관 보유 개방데이터 활용 서비스. 회원/활용신청 약관 준수. 별도 원문 재배포 권한은 가정하지 않음 | API 결과를 검색·검토 문맥으로 사용하고 출처 URL/공고 ID 유지 |
| 사람인 채용공고 | 민간 공개 페이지 / PlayMCP·웹검색 결과 | 민간 공고 추천·선택 후 원문 검증 | 사람인 이용약관·게시물 정책을 확인했으나 **공개 페이지 원문의 포괄적 오픈 라이선스는 확인하지 않음** | 대량 수집/재배포하지 않음. 현재 공고 원문을 일시적으로 검증하고 필요한 요구사항·근거만 저장 |
| 잡코리아 채용공고 | 민간 공개 페이지 / 웹검색 결과 | 민간 공고 추천·선택 후 원문 검증 | 공개 채용 페이지 접근 가능. **오픈 라이선스는 확인하지 않음** | 사람인과 동일하게 일시 검증·최소 근거만 사용. 원문 대량 저장/재배포 금지 |
| GitHub 공개 README | 사용자 제출 공개 저장소/API | 프로젝트 기술·기능 흐름 근거 추출 | GitHub ToS상 public repository는 열람 가능하지만, **콘텐츠의 추가 이용권은 각 저장소 LICENSE에 따라 달라짐**. LICENSE가 없으면 공개라는 이유만으로 재배포 권한을 가정하지 않음 | 사용자가 제출한 공개 README 한 건을 읽고 근거 excerpt만 분석. 개인 기여 자동 판정·원문 재배포 금지 |
| 팀원/외부 사람 검토 | 사람 | 평가셋·도메인 기준 검토 | 외부 라이선스 대상이 아님. 대신 검토자·경험 범위·검토일·case·동의/보관 범위를 기록해야 함 | reviewer와 rationale을 case별로 보존. 실제 사용자 사례는 별도 동의 없이 공개 Dataset으로 이동하지 않음 |

## 공식 확인 URL

- NCS 기준정보: <https://www.data.go.kr/data/15128213/openapi.do>
- 재정경제부 공공기관 채용정보: <https://www.data.go.kr/data/15125273/openapi.do>
- 인사혁신처 공공취업정보: <https://www.data.go.kr/data/15156780/openapi.do>
- ALIO 오픈데이터: <https://opendata.alio.go.kr/>
- GitHub Terms: <https://docs.github.com/en/site-policy/github-terms/github-terms-of-service>
- GitHub repository licensing: <https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository>
- 사람인 회원약관: <https://www.saramin.co.kr/zf_user/help/terms-of-service>

## 코드 연결

| 출처 | 구현 근거 |
| --- | --- |
| NCS | `backend/app/services/ncs_competency.py` |
| 재정경제부 채용정보 | `backend/app/services/mofe_recruitment.py` |
| 인사혁신처 공공취업정보 | `backend/app/services/public_employment_recruitment.py` |
| ALIO | `backend/app/services/alio_recruitment.py` |
| 사람인/잡코리아 | `backend/app/services/saramin_recommendation.py`, PlayMCP 관련 service |
| GitHub README | `backend/app/services/github_readme_analysis.py` |
| 사람 검토 | `docs/research/DOMAIN_RESEARCH.md`, `evals/README.md` |

## 서비스에 저장할 수 있는 것과 저장하지 않을 것

### 저장 가능

- source type / provider
- source URL 또는 dataset/공고 ID
- 조회 시각·기준 시점
- 검증된 짧은 evidence
- reviewer / review status
- license/terms status

### 기본적으로 저장·재배포하지 않음

- 민간 채용 사이트 전체 HTML/전체 공고 원문
- GitHub README 전체 복제본
- 실제 사용자 답변/음성의 공개 Dataset 복제
- 평가 정답을 운영 모델 문맥으로 재사용

## D3 판정

현재 활성 source마다 **출처 유형, 서비스 사용 위치, 이용허락/약관 상태, 보수적 사용 정책**을 기록했다.
새 source를 추가할 때는 코드 연결과 함께 이 표를 먼저 갱신한다.
