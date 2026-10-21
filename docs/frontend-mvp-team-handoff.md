# 말해봄 프론트엔드 MVP 작업계획서

> 이 문서는 Mock MVP 착수 당시 계획의 역사 기록입니다. 현재 프런트는 로그인, 분석 API, 질문 TTS, 연습 기록 API, 코칭 Mock 화면까지 연결되어 있으므로 최신 상태는 [저장소 구현 점검표](repository-audit.md)를 우선합니다.

## 1. 작업 목적

STT와 TTS 최종 모델이 아직 준비되지 않은 동안에도, 면접 연습 서비스의 전체 사용 흐름을 브라우저에서 시연할 수 있는 React + Vite 프론트엔드 MVP를 만든다.

완료 화면은 실제 모델을 호출하지 않는다. 대신 mock 분석 결과를 사용하며, 나중에 `AnalysisClient`와 `TtsAssetResolver`만 실제 구현체로 바꾸는 방식으로 연결한다.

## 2. 이번 작업 범위

```text
질문 선택
  → 마이크 권한 확인
  → 1차 녹음 (5~60초)
  → 녹음 재생
  → mock 분석 결과
  → TTS 자산 미준비 안내
  → 2차 녹음
  → 1차/2차 수치 비교
```

포함:

- 기본 면접 질문 10개
- 브라우저 `MediaRecorder` 녹음과 재생
- 60초 자동 종료, 5초 미만 분석 차단
- 마이크 거부·녹음 실패·분석 실패 안내
- mock STT·VAD·전달력 결과
- 최대 2개 피드백
- 같은 질문의 1차·2차 비교
- 현재 탭에서만 유지되는 `sessionStorage` 결과 요약

제외:

- 실제 STT/VAD API 호출
- 실제 TTS WAV 재생·동적 TTS 생성
- 로그인, Supabase, 영구 DB·Storage, 배포
- 직접 질문, 답변 내용 평가, 합격 예측, Voice Cloning
- 음량·억양 분석

## 3. 시작 전 준비

### 필수 프로그램

- Node.js LTS
- npm
- Chrome 또는 Edge (마이크 테스트용)

확인 명령:

```powershell
node --version
npm --version
```

현재 작성자 PC에서는 Node.js/npm이 설치되어 있지 않았다. 팀원 PC에서 위 명령이 동작하면 그대로 진행하고, 동작하지 않으면 Node.js LTS 설치 후 새 PowerShell을 열어 다시 확인한다.

### 작업 위치

```text
프로젝트 루트/
└─ frontend/
```

기존 `frontend/src/wireframe_초안.md`와 `docs/wireframe_완성본.md`는 삭제하지 않는다. 구현 기준은 `docs/wireframe_완성본.md`이며, 이 작업의 기능 계약은 `docs/specs/frontend-mock-mvp.md`를 따른다.

## 4. 구현 순서

### 1단계: React + Vite 프로젝트 구성

`frontend/`에 React + TypeScript 기반 Vite 앱을 구성한다.

필수 실행 명령:

```powershell
cd frontend
npm install
npm run dev
```

완료 기준:

- 브라우저에서 로컬 개발 주소가 열린다.
- 첫 화면에 `말해봄`과 `/practice` 연습 화면이 표시된다.
- `npm run build`가 성공한다.

### 2단계: 타입·질문·mock 서비스 분리

다음 경계를 만든다.

```text
src/types/analysis.ts
  - 백엔드 응답과 같은 AnalysisJobResponse 타입

src/data/questions.ts
  - 기본 질문 10개

src/services/analysis-client.ts
  - AnalysisClient 인터페이스

src/services/mock-analysis-client.ts
  - 현재 사용하는 mock 성공/실패 결과

src/services/tts-asset-resolver.ts
  - 현재는 unavailable만 반환
```

mock 분석 결과는 다음 구조를 유지한다.

```json
{
  "status": "completed",
  "result": { "text": "전사문" },
  "delivery": {
    "metrics": {
      "answer_duration_sec": 30,
      "speech_duration_sec": 22,
      "cpm": 290,
      "long_silences": [],
      "repetitions": []
    },
    "feedback": []
  },
  "error": null
}
```

주의: 녹음 Blob, 실제 전사문, TTS URL은 `sessionStorage`에 저장하지 않는다.

### 3단계: 질문 선택과 마이크 확인

와이어프레임의 첫 화면을 구현한다.

- 왼쪽 이용안내 카드는 고정한다.
- 오른쪽에서 질문 10개 중 하나를 radio 방식으로 선택한다.
- 질문 미선택 시 `이 질문으로 시작하기`는 비활성이다.
- 질문 선택 뒤 `마이크 확인`을 누르면 `navigator.mediaDevices.getUserMedia({ audio: true })`를 호출한다.
- 허용 시 `연습 시작하기`, 거부 시 `다시 확인`을 표시한다.

완료 기준:

- 질문을 바꾸면 마이크 준비 상태가 초기화된다.
- 마이크 거부 시 내부 오류 대신 브라우저 권한 설정 안내를 보여 준다.

### 4단계: 실제 브라우저 녹음과 재생

`MediaRecorder` 기반으로 다음을 구현한다.

- 녹음 시작·중지
- 초 단위 경과 시간
- 60초 자동 중지
- 녹음 완료 파일 재생
- 5초 미만이면 분석 버튼 비활성 및 안내
- 컴포넌트 종료 또는 새 녹음 시작 시 object URL 해제와 MediaStream track 종료

완료 기준:

- 5초 이상 녹음한 뒤에는 `분석하기`가 활성화된다.
- 60초에 자동으로 녹음이 끝난다.
- 녹음 파일은 탭 세션 외부에 저장하지 않는다.

### 5단계: mock 분석 결과와 TTS 미준비 상태

`분석하기`를 누르면 분석 중 화면을 잠시 표시한 뒤 `MockAnalysisClient` 결과를 보여 준다.

결과 화면에는 아래를 표시한다.

- 전사문
- 답변 시간, 실제 발화 시간, CPM
- 긴 침묵 횟수·위치
- 반복 표현
- 최대 두 개 피드백
- `검수 완료된 피드백 음성이 준비되면 들을 수 있어요.` 안내
- `재녹음하기` 버튼

TTS 재생 버튼과 런타임 TTS 호출은 추가하지 않는다.

### 6단계: 2차 녹음과 전후 비교

- `재녹음하기`는 같은 질문을 유지한 2차 Attempt를 시작한다.
- 2차도 1차와 같은 녹음·mock 분석 절차를 사용한다.
- 둘 다 결과가 있을 때만 비교 화면을 연다.
- CPM, 긴 침묵 수, 반복 표현 수를 1차·2차 카드에 나란히 표시한다.
- 변화량은 표시하되 합격·불합격 또는 강한 좋음·나쁨 판단은 하지 않는다.

### 7단계: 현재 탭 기록과 오류 처리

- `sessionStorage`에는 질문 ID·질문 문구·attempt 번호·지표 요약만 저장한다.
- 탭을 닫으면 기록이 사라지는 현재 범위를 화면 또는 README에 명시한다.
- 마이크 거부, 녹음 생성 실패, mock 분석 실패, 결과 없음에 재시도 UI를 제공한다.
- 오류 메시지에는 기술 traceback, 로컬 경로, 음성 원문을 넣지 않는다.

## 5. 실제 모델 연결 시 교체할 파일

| 현재 구현 | 후속 구현 |
| --- | --- |
| `MockAnalysisClient` | FastAPI `POST /analysis-jobs` 업로드 + `GET /analysis-jobs/{jobId}` polling 구현체 |
| 고정 mock 결과 | 백엔드 `result`, `delivery` 응답 |
| `UnavailableTtsAssetResolver` | 검수 완료 TTS WAV URL을 반환하는 resolver |
| sessionStorage 요약 | 인증·비공개 Storage·DB 기반 기록 |

화면 컴포넌트가 백엔드 endpoint를 직접 호출하지 않게 유지해야 교체 범위가 작아진다.

## 6. 테스트와 검증

자동 테스트:

```powershell
cd frontend
npm run test
npm run build
```

최소 테스트 항목:

- 질문 미선택 CTA 비활성
- 질문 변경 시 마이크 상태 초기화
- mock 결과가 `result`와 `delivery`를 함께 반환
- TTS unavailable 안내와 재녹음 버튼 공존
- 5초 미만 분석 차단
- 60초 자동 종료
- 2차 결과 전 비교 차단
- `sessionStorage`에 전사문·Blob·URL이 없는지 확인

수동 브라우저 점검:

```powershell
cd frontend
npm run dev
```

- 질문 선택 → 마이크 허용 → 5초 이상 녹음 → 재생 → 분석 → 결과 → 재녹음 → 비교
- 마이크 권한 거부 후 `다시 확인`
- 5초 미만 녹음 시 분석 불가
- 분석 실패 mock에서 재시도 안내

## 7. 팀원 완료 보고 양식

```markdown
## 프론트엔드 MVP 완료 보고

- 브랜치:
- 변경 파일:
- 구현한 화면/상태:
- 실제 STT/TTS를 호출하지 않았음을 확인: 예 / 아니오
- `npm run test` 결과:
- `npm run build` 결과:
- 브라우저 수동 점검 결과:
- 남은 연결 작업: MockAnalysisClient 교체 / TTS WAV resolver 교체
- PR 링크:
```

## 8. 참고 문서

- `docs/specs/frontend-mock-mvp.md` — 기능 Spec과 AC
- `docs/superpowers/plans/2026-08-18-frontend-mock-mvp.md` — 테스트 우선의 세부 구현 순서
- `docs/wireframe_완성본.md` — 화면·상태·문구 기준
- `docs/prd.md` — 이관된 1차 MVP 흐름과 개인정보 원칙
- `docs/CONSTRAINTS.md` — 현재 프로젝트 범위·금지 사항·모델 사용 관련 제약의 canonical
