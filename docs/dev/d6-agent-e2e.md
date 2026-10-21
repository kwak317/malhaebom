# D6 Agent live E2E 실행 가이드

`backend/tests/run_d6_agent_e2e.py`로 로그인 사용자 문맥의 normal / boundary / injection Agent E2E를 반복 검증하는 로컬 개발자용 절차다.

## 1. 로컬 로그인 확인

- `docker compose` 스택을 실행한다.
- 브라우저에서 `http://localhost:18080`에 접속한다.
- local Supabase 계정으로 로그인된 상태인지 확인한다.

runner는 Docker Compose의 API host port를 자동 감지하므로 일반적인 로컬 실행에서는 `D6_API_BASE_URL`을 직접 설정할 필요가 없다.

## 2. 현재 Supabase JWT 복사

로그인된 `localhost:18080` 탭에서 DevTools Console을 열고 다음 snippet을 직접 실행한다.

```javascript
const k = Object.keys(localStorage).find(k => k.includes('auth-token'));

if (!k) {
  throw new Error('Supabase auth session not found. Log in first.');
}

const s = JSON.parse(localStorage.getItem(k));

if (!s?.access_token) {
  throw new Error('access_token not found.');
}

copy(s.access_token);

console.log(
  'D6 JWT copied:',
  k,
  'expires:',
  s.expires_at ? new Date(s.expires_at * 1000) : 'unknown'
);
```

이 snippet은 현재 브라우저 session의 `access_token`을 clipboard에 복사한다. 토큰 문자열 자체는 Console에 출력하지 않는다.

> JWT는 Git, 이슈, PR, Worklog, 채팅에 붙여 넣지 않는다. 위 snippet은 로그인한 local 개발 환경에서 사용자가 명시적으로 Console에서 실행하는 용도다.

## 3. runner 실행

오래된 테스트 환경변수가 남아 있으면 먼저 제거한다.

```bash
unset D6_ACCESS_TOKEN D6_API_BASE_URL
python backend/tests/run_d6_agent_e2e.py
```

`/health` 확인 후 다음 숨김 입력에 2단계에서 복사한 JWT를 붙여 넣는다.

```text
Paste current local Supabase access token (hidden input):
```

token은 터미널에 표시되지 않는다.

## 4. 테스트용 job 선택

인증에 성공하면 completed analysis job 후보가 transcript/feedback 없이 번호로 표시된다.

```text
[1] question=preset-04 attempt=1 practiced_at=... job=xxxxxxxx…
[2] question=preset-04 attempt=2 practiced_at=... job=yyyyyyyy…
Select a dedicated test job number (synthetic revisions will be appended):
```

synthetic immutable revision이 추가되므로 개인 기록 대신 테스트용으로 사용해도 되는 job을 선택한다. runner는 가장 최근 job을 자동 선택하지 않는다.

## 5. 결과 확인

runner는 normal / boundary / injection을 순서대로 실행한다.

- normal: HTTP 200 + `ok | needs_more_info`
- boundary: HTTP 200 + `needs_more_info`
- injection: HTTP 200 + `needs_more_info`

세 case가 모두 정책을 통과하면 다음 summary가 출력된다.

```json
{"summary": {"passed": 3, "total": 3}}
```

답변 원문, JWT, answer revision ID, job snapshot ID, user ID는 출력하지 않는다.

## 점검만 하기

revision을 추가하지 않고 API health, 인증, candidate job 수만 확인하려면:

```bash
python backend/tests/run_d6_agent_e2e.py --doctor
```

HTTP 401은 job 0건이 아니라 token 만료 또는 local Supabase issuer 불일치 등 인증 실패를 뜻한다.
