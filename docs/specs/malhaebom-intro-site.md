# Spec — 말해봄 서비스·프로젝트 소개 사이트

## Why
- 현재 제품의 로그인/코칭 페이지와 분리된 홍보 및 프로젝트 설명용 URL이 필요하다.
- 이용자에게는 경험 연결→답변→코칭→재답변을, 발표/리뷰어에게는 설계 의도·검증 접근을 전달한다.
- 서비스/운영 기능을 건드리지 않고 정적 파일만 추가한다.

## Goal
- `site/index.html`과 `site/project/index.html` 두 경로를 모든 내부 파일/앵커가 유효한 정적 페이지로 제공한다.
- 최소 서버 의존성 0개(HTML/CSS/JS), `python site/scripts/check_site.py`로 내부 링크·중복 ID·자산 존재 검증에 통과한다.
- 사용자 안내용 CTA는 검증된 `https://malhaebom.xyz`로 연결하고 소스 링크는 현 저장소로 연결한다.
- Out of scope: GitHub Pages 공개, CI 워크플로 추가, 실제 제품 기능 변경, 공개용 성능 수치 미검증 상태의 게시.

## What
### Happy path
1. 서비스 소개 페이지에서 핵심 기능·사용 방법·기획용 화면을 확인한다.
2. 프로젝트 소개 페이지에서 개념적 아키텍처와 평가 접근법을 살펴본다.
3. CTA로 운영 중인 말해봄 서비스에 이동하거나 GitHub 저장소를 연다.
4. 라이트/다크/시스템 테마를 전환하면 각 페이지에 동일한 설정이 적용된다.

### Edge cases
- JavaScript가 비활성화되거나 스크립트 로드가 실패해도 본문·일반 링크가 노출된다(테마는 기본값).
- 모바일에서 메뉴와 CTA가 화면 밖으로 밀리지 않도록 반응형 레이아웃 제공.
- 서비스 URL이 제거되면 연습 버튼에서 안내 다이얼로그를 제공.
- 구상 중인 3단 코칭 UI와 전후 비교 문구는 '기획 예시'로 구분하고 실제 성과로 오인시키지 않는다.

## How
- 외부 패키지 없이 `site/` 아래 정적 페이지와 `assets/site.css`, `assets/site.js`, `assets/site-config.js`를 둔다.
- PDF에서 추출한 소형 브랜드 이미지를 WebP로 최적화해 사용한다. 원본 고해상도 자산은 추후 교체한다.
- Pages는 `site/` 하위 폴더를 곧바로 게시하도록 설정하지 않고, 향후 독립 저장소 또는 전용 `gh-pages` 브랜치에 복사하여 공개한다.
- 배포 중 서비스 주소는 `docs/CURRENT_STATE.md`의 확인된 프런트엔드 URL을 기준으로 하며 비밀키를 포함하지 않는다.
- `site/docs/CONTENT_REVIEW.md`에 미확인 기능·운영 정책을 분리한다.

## AC
- Given 정적 사이트 소스, When `python site/scripts/check_site.py` 실행, Then 두 페이지의 상대 자산·앵커·중복 ID 검사가 0 오류로 끝난다.
- Given `site/index.html`, When 서비스 소개 링크를 따라감, Then `site/project/index.html`에서 프로젝트 구조와 검증 섹션을 읽을 수 있다.
- Given 구성 파일, When CTA/저장소 링크를 확인, Then HTTPS 서비스 URL과 공식 GitHub 저장소 주소를 가리킨다.
- Given 정적 페이지 소스, When 기존 `frontend/`·`backend/` 경로와 diff를 비교, Then 제품 코드 변경이 없다.
- Given 배포 준비 체크리스트, When 공개 이전 점검, Then 미검증 기능·수치·기획 목업이 명시적으로 구분되어 있다.
