# Worklog — 말해봄 소개 사이트 소스 추가

- 일시: 2026-10-08
- 작업자/에이전트: ChatGPT / c2c
- 관련 PR: 작성 후 연결
- 관련 요구사항: `docs/specs/malhaebom-intro-site.md`

## 1. 목적
서비스 이용자를 위한 소개와 프로젝트 개발·평가 과정을 함께 설명하는 정적 사이트를 기존 말해봄 저장소에 안전하게 추가한다.

## 2. 작업 전 상태
- `origin/main` 기반 `proj2-3` 기존 프론트엔드는 별도 제품을 제공 중이다.
- 기본 작업 트리 `main`에서 기존 STT 문서 미커밋 변경 1건이 확인되어, 별도 worktree `proj2-3-site`/브랜치를 생성했다.
- 11페이지 랜딩 개선 PDF 기반 독립 사이트 아카이브가 로컬 제작되어 있었다.

## 3. 수행 내용
1. `site/` 아래 서비스 소개, 프로젝트 소개, 테마와 메뉴·FAQ, 자산/링크 설정, 콘텐츠 검토 체크리스트 및 정적 검사 스크립트를 추가했다.
2. PDF 추출 로고·마스코트 이미지를 WebP로 변환해 크기를 줄였다.
3. 저장소에 확인된 운영 URL `https://malhaebom.xyz`를 연습 CTA에 연결했다.
4. GitHub Pages는 별도 배포 브랜치/저장소가 필요하므로 현재 PR에서 게시 자동화나 기존 서비스 배포를 변경하지 않았다.
5. 기획 목업·예시 비교와 실제 배포 기능을 구분하고, 검증되지 않은 평가 수치·보관 기간은 게재하지 않았다.

## 주요 판단과 이유
- 기존 `docs/`는 프로젝트 문서 폴더이므로 GitHub Pages의 `docs` 게시를 사용하지 않는다.
- 서비스/프로젝트 소개는 한 사용자 경험을 설명하는 단일 논리 단위이므로 동일 PR에 포함한다.
- CI 사용량 제약을 고려해 의존성 없는 정적 HTML/CSS/JS로 구현하고 Pages 배포는 추후 별도로 검토한다.

## 4. 변경 파일
| 파일 | 변경 내용 |
| --- | --- |
| `site/index.html`, `site/project/index.html` | 서비스·프로젝트 소개 페이지 |
| `site/assets/*` | 브랜드 이미지, 스타일, 인터랙션, 링크 설정 |
| `site/README.md`, `site/docs/CONTENT_REVIEW.md` | 게시 안내 및 미확인 콘텐츠 검토 |
| `site/scripts/check_site.py` | 정적 파일·라우트·앵커 검증 |
| `docs/specs/malhaebom-intro-site.md` | Why/Goal/What/How/AC 정의 |
| `docs/worklogs/2026-10-08_malhaebom-intro-site.md` | 작업 근거와 결과 |

## 5. 검증
- `python site/scripts/check_site.py`: 두 페이지 17/7개 ID, 24/29개 내부 파일·링크 검사 통과; 미존재 자산·중복 앵커 없음.
- 로컬 HTTP smoke: `/`, `/project/`, CSS, JavaScript, WebP 이미지 2개 모두 HTTP 200 및 MIME 검사 통과.
- 추가 점검: git diff --check 및 PR 정책 검사는 커밋 전/후 각각 수행.
- 이 파일 추가는 실제 브라우저에서의 반응형 시각 검증이나 Pages 공개 검증을 대체하지 않는다.

## 6. 발견한 문제 / 남은 리스크
- 현재 GitHub Pages 공개 URL이 없고, 브라우저 시각 검증/실서비스 로그인 E2E는 범위 밖이다.
- 기존 로고 이미지는 첨부 PDF에서 잘라낸 소형 이미지다.
- 서비스 기능 일부의 운영 범위와 프로젝트 역할·평가 수치는 담당자 확인 전까지 공개 보류한다.

## 미확인 사항
- 모바일 실제 기기, 다크/시스템 테마 시각 QA, 브라우저별 동작.
- 팀 소개·기술 아키텍처 상세 수치, 데이터 보관 정책.
- Pages 브랜치 게시 권한과 사용 여부.

## 7. 다음 작업
- PR 리뷰·승인 후 병합, 원본 브랜드/화면 교체, 운영 기능·데이터 검증.
- GitHub Pages 전용 저장소 또는 배포 브랜치 확정 후 게시.

## 2026-10-08 추가 변경 — 기존 프론트엔드 리소스 적용
- 실제 브랜드 원본 `frontend/src/assets/malhaebom-detail-logo.png`, `frontend/public/malhaebom-favicon.png`에서 정적 사이트용 로고·히어로 캐릭터·파비콘 재생성.
- `frontend/src/assets/coach-recording.png`, `coach-transcribing.png` 및 기존 `demo-*.png` 화면 4장을 WebP로 최적화해 소개 페이지 내 별도 '기존 프론트엔드 데모' 섹션에 적용. 서비스 배경 SVG도 이용 방법 섹션에 재사용.
- 기존 프론트엔드의 코드와 원본 이미지는 수정하지 않았음. 이미지별 원본 경로는 `site/README.md` 대응표 참고.
- `python site/scripts/check_site.py`: 두 페이지 총 25개 ID/61개 링크·에셋, CSS 배경 경로·PNG/WebP 시그니처·앵커 중복 검사 통과.
- 로컬 HTTP smoke: 서비스 소개, 프로젝트 소개, CSS/JS, 브랜드 이미지 HTTP 200 재확인.
- Git diff --check: 추적 파일 검증 통과. PR 사이즈 정책은 후속 커밋 뒤 다시 검증.
- 남은 리스크: 데모 스크린샷의 현재 배포 화면과의 일치 여부·브라우저 시각 확인·팀 브랜드 사용 승인.

## 2026-10-08 콘텐츠 확인 및 정적 재검증
- `site/docs/CONTENT_REVIEW.md`에 사용자가 확인한 프로젝트 기간 `2026-09-18 ~ 2026-10-08`을 기록했다.
- 기록 보관 기간은 사용자가 `24시간`으로 전달했으나, 실제 운영의 저장·삭제·내보내기 정책과 대조하지 못했으므로 사이트 공개 문구에 확정값으로 추가하지 않았다.
- `python site/scripts/check_site.py`: `index.html` 18 IDs/31 links·assets, `project/index.html` 7 IDs/30 links·assets, 내부 경로·앵커·이미지 시그니처 검사 PASS.
- Git 추적 변경의 `git diff --check` PASS. 실제 공개 Pages 접속·모바일 시각 QA는 이번 정적 검증 범위 밖이다.
