# Worklog — D10 관측 가설 및 D11 공식 baseline 오프라인 사전점검

- 일시: 2026-10-02
- 작업: 승인·CI 통과 후 병합된 PR #162 → #163 다음 단계
- 범위: 코드·문서·로컬 manifest 검증만. 유료 provider 호출, 실제 운영 설정 수정, Cloud Run 배포 없음.
- 관련 체크포인트: D10 실패 관측 기반 재조정 가설 / D11 공식 baseline과 인젝션 3건 준비

## 1. 목적

사용자가 제공한 운영 성공 코칭 trace와 버전 표기 불일치를 근거로 **검증 가능한 D10 한 줄 가설**을 명문화하고, D11 평가를 실행할 때 운영 설정이 불명확한 과거 실험 수치를 임의 재사용하지 않도록 **오프라인 사전점검 도구와 실행 전 조건**을 준비한다.

## 2. 작업 전 상태

- #162는 실제 코칭 서비스의 Prompt·Skill 버전 관측/DB 정합성을 수정한 소스 변경으로 main 병합됐다. #163은 기존 실험·D10 운영 증거와 누락 항목 인덱스를 보존하며, 두 문서 충돌 해결·최신 CI 4/4 및 승인 확인 후 main 병합됐다.
- 과거 사용자 브라우저 PlayMCP 인증 오류는 이후 복구됐다. 운영 사용자는 공고 검색→원문 분석→연습→1/2차 비교까지 성공했다고 직접 보고했다.
- 10/2 14:28 경 Langfuse Cloud 단일 코칭 trace의 provider HTTP 200·output validation 통과·`needs_more_info` 정상 상태, 그리고 **기록된** Skill v6 대 현재 로컬 기본 v6.1 불일치가 있었다. Environment는 `default`이고 Prompt Name은 화면에 보이지 않았다. 당시 실제 운영 번들·Prompt 릴리스는 검증되지 않았다.
- 역사적 동일 Skill v4/v5 2,048/45 평가와 v5 단독 4,096/60 후속 실행은 서로 다른 조건이다. 9/30 Dataset v2 정답표의 단일 사람 검토는 최신 v5 모델 출력 사람 검토와 다른 작업이다.

## 3. 수행한 작업

1. [D10 관측 기반 재조정 가설](../experiments/2026-10-02_d10-observability-hypotheses.md)을 작성했다. **기본 메타데이터 오표기**와 **실제 운영 리비전 불일치**를 구분하고, #162 적용 리비전의 같은 요청에 대해 Skill 실효값·trace·DB를 비교하도록 증명/반증 조건을 작성했다. 과거 PlayMCP 인증 실패는 복구 보고를 보존하고 원인 미확정으로 남겼다.
2. [D11 baseline 사전점검 계획](../experiments/2026-10-02_d11-baseline-preflight.md)에 기존 역사적 수치·현 운영 공식 측정의 경계를 명시했다. 모델/Prompt/Skill/원문 해시·생성 상한·timeout·repeat·비용 승인·Langfuse 환경이 실제 배포와 일치할 때만 유료 실행하도록 준비했다.
3. `evals/prepare_d11_baseline.py`와 회귀 테스트를 추가했다. 기존 Dataset v2 30건(normal 12/boundary 10/failure 8), 고유 ID, Skill 카탈로그, 결합 Prompt 해시, 기존 인젝션 회귀 3건(`coach-failure-23/28/29`)을 오프라인으로 점검한다. **세 건은 기존 30건에 포함되어 신규 3건 추가 실적으로 계산하지 않는다.**
4. 체크리스트 D10의 **가설 한 줄 문서 작성만 완료**로 변경했다. D10 운영 Langfuse 연결 검증은 여전히 부분완료, 관리형 Prompt/rollback은 미완료다. D11 공식 baseline 실행과 신규 3건의 독립 사람 판정/전후는 미완료를 유지한다.

## 주요 판단과 이유

- Langfuse Skill v6 표시값만으로 당시 실제 v6을 사용했다고 추론하지 않는다. `default` 환경/Prompt Name 미표시만으로 관리형 Prompt 비사용 또는 운영 장애라고 단정하지 않는다.
- 로컬 예비 생성 설정(Flash-Lite, 4,096 tokens/60초, 2회 반복)은 **제안**일 뿐 현재 운영 설정이나 공식 실험값이 아니다. `preflight.json`의 필수 운영 확인/비용 승인 필드는 null이며 `paid_run_authorized=false`이다.
- 과거 비교 runner는 2,048/45·1회 조건이 고정돼 있다. 비용 승인 전 이를 호출하거나 다른 실행의 결과와 혼합하지 않는다.
- 신규 인젝션 3건은 팀·독립 사람 검토가 입력·정답·근거·판정자를 확정해야 한다. LLM으로 입력과 정답을 동시에 생성하지 않는다.

## 4. 변경 파일

| 파일 | 변경 |
| --- | --- |
| `docs/experiments/2026-10-02_d10-observability-hypotheses.md` | 운영 관측·가설·사후 검증 절차 |
| `docs/experiments/2026-10-02_d11-baseline-preflight.md` | 공식 baseline의 입력·설정 고정 전제, 역사적 수치와 신규 3건의 경계 |
| `evals/prepare_d11_baseline.py` | 오프라인 점검 manifest 생성, 기존 평가셋/카탈로그/해시 검증 |
| `backend/tests/test_prepare_d11_baseline.py` | Product CI의 `backend/tests` pytest 수집 대상인 2개 오프라인 무호출 회귀 테스트 |
| `docs/CURRENT_STATE.md`, `docs/project2-checkpoint-work-cards.md`, 실험/Worklog 색인 | 증거와 상태 동기화 |
| 본 Worklog | 명시적인 검증 범위·남은 위험 기록 |

## 5. 검증

- 리뷰 반영: 테스트를 Product CI 수집 대상인 `backend/tests/test_prepare_d11_baseline.py`로 이동했다. 부모 `local-results/`가 아예 없는 clean clone을 임시 루트로 재현해 디렉터리 자동 생성, manifest 저장 및 기존 출력 덮어쓰기 거부를 확인한다. 실제 Git-ignored 폴더의 사전 존재에 의존하지 않는다.
- `python -m unittest discover -s backend/tests -p test_prepare_d11_baseline.py -v`에서 새 테스트 **2건 수집·통과**, API/model 호출 없음. 함께 실행한 `backend/tests/test_prompt_skill_separation.py` **14건**, `backend/tests/test_coaching_prompt.py` **10건**도 통과했다.
- 리뷰 수정 후 로컬에 설치된 Python 프로필에는 pytest가 없어 CI와 같은 pytest 명령을 직접 실행할 수 없었다. Product CI는 `backend/requirements-ci.txt`에서 `pytest>=8,<9`를 설치하므로, `backend/tests` 수집 및 실제 pytest 실행 통과 여부는 수정 PR의 새 CI 결과로 별도 확인한다.
- 실제 로컬 manifest 생성 `local-results/d11-baseline-preflight-pr/preflight.json` 성공, Git 제외 경로. 검사 시점 main SHA `8911e8da61915343fa29cbae38d0c6e7feaade43`.
- Dataset SHA-256: `1727d4b41df520489ce590e26a5f91aa9457b2589aee9be07fecbb5284c6f6ea`, 30건 및 유형 12/10/8 고정. Skill 버전 `interview-coach-v6.1-domain-rules`, 번들 SHA-256 `6e12aeb78b1e1463022acedc22ae6498dfc035c867a8661277bfa5e2f90a67ae`, 로컬 결합 Prompt SHA-256 `c4194d1a477bc38a667d27de806c49a04c78e5246c69eb8c4cd4e84505ca86a3`. 실행 manifest의 운영 일치·유료 실행 승인은 **false**다.
- 신규 D10/D11/Worklog의 상대 링크 각각 **2/5/2개 확인**, 공백 점검 통과. `scripts/check_doc_references.py`: 유지관리 문서 7개 검사 통과. `git diff --check`: 통과. 최종 PR 변경량 검사는 커밋 후 `origin/main...HEAD` 기준으로 수행한다.

## 6. 발견한 문제 / 남은 리스크

- 운영 리비전·실제 Prompt/Skill·비용 상한과 명시적 Langfuse 환경 미확인. 코드/manifest만으로 D11 공식 baseline 확정 불가.
- 새 인젝션 3건의 입력·독립 정답·평가기준과 최신 v5 출력 사람 검토는 승인 전이다.
- #162가 `main`에 병합돼도 운영 컨테이너 재배포/신규 trace 검증은 자동으로 수행되지 않는다.
- 2,048/45 고정 페어 비교와 4,096/60 단독 결과를 혼합하지 않는다.

## 미확인 사항

실제 D10 Cloud Run revision, Langfuse 관리형 Prompt의 현재 label과 버전, 새로운 운영 trace, 동일 요청의 PlayMCP 검색→원문 분석 로그, 배포 적용 후 버전/rollback, D11 공식 유료 재측정은 진행하지 않았다.

## 7. 다음 작업

1. 운영 담당자가 실제 배포 리비전과 같은 실행의 Skill·Prompt/환경·trace/DB 일치를 확인한다. 식별 정보/토큰은 받지 않는다.
2. 팀이 비용 상한·실행 생성 조건·2회 이상 반복 횟수와 신규 인젝션 3건의 독립 정답을 합의한다.
3. 위 확인과 승인 후 공식 동일 조건 baseline을 기록하고 Prompt 또는 모델 설정 **한 변수만** 바꿔 재평가한다. 수치·회귀·사람 점수와 production trace는 별도 근거로 연결한다.
