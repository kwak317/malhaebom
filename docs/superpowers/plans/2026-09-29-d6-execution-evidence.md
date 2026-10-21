# D6 Execution Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 인증된 실제 Agent 요청에서 MCP 호출·실패 경로·Langfuse trace를 재현하고 D6 체크포인트를 증거 기반으로 갱신한다.

**Architecture:** 기존 `POST /api/agent`와 `McpStdioContextGateway`를 유지한다. 별도 기능을 추가하기보다 테스트 사용자/고정 fixture 실행 하네스를 보강해 정상·경계·오염·권한 실패를 같은 요청 ID 체계로 재현하고, Langfuse에는 원문 없이 상태·model·token·cost·latency·retry만 남긴다.

**Tech Stack:** Python 3.12, FastAPI, unittest/pytest, Docker Compose, FastMCP, Supabase test data, Langfuse SDK.

**Spec:** `docs/project2-checkpoint-work-cards.md` D6, `docs/REQUIREMENTS.md`의 MCP·Langfuse·실패 경로 요구사항.

## Global Constraints

- RAG·LangGraph·벡터 검색을 추가하지 않는다.
- 실제 사용자 전사·공고 원문·evidence quote를 Langfuse나 저장소에 남기지 않는다.
- MCP는 허용된 도구와 검증된 사용자 문맥만 사용한다.
- 인증·소유자·유효기간·허용 ID 검증을 우회하지 않는다.
- 실패를 성공으로 기록하지 않으며, fixture 검증과 운영 사용자 E2E를 구분한다.
- 한 PR은 D6 실행 증거라는 하나의 목적만 다룬다.

## Review Focus

- 인증 사용자의 `/api/agent` 요청이 실제 MCP stdio gateway를 지나가는가 — `test_live_agent_uses_mcp_context`.
- 다른 사용자 ID·잘못된 revision/job ID가 차단되는가 — `test_mcp_rejects_wrong_owner_and_id`.
- MCP timeout/error가 사용자용 `503`과 실패 observation으로 남는가 — `test_mcp_failure_returns_retryable_503`.
- provider schema 실패가 retry 후 최종 `502` trace를 남기는가 — `test_contract_failure_records_failed_trace`.
- Langfuse payload에 transcript/source URL/quote가 유출되지 않는가 — 기존 `test_coaching_observability.py` 회귀.

---

### Task 1: 실행 전 상태와 테스트 fixture 고정

**Files:**
- Modify: `backend/tests/compose_coaching_e2e.py`
- Create: `backend/tests/d6_evidence_cases.json`
- Test: `backend/tests/test_d6_evidence_cases.py`

**Interfaces:**
- Produces case IDs `d6-normal-01`, `d6-boundary-01`, `d6-injection-01`, `d6-failure-01`.
- Each case contains only synthetic question/answer/context IDs and expected terminal state; no real user text.

- [ ] **Step 1: Write failing case-schema tests**

```python
def test_d6_cases_have_four_required_classes():
    cases = load_cases()
    assert {case["kind"] for case in cases} == {
        "normal", "boundary", "injection", "failure"
    }
    assert all(case["answer_revision_id"] for case in cases)
```

- [ ] **Step 2: Run** `python -m pytest backend/tests/test_d6_evidence_cases.py -q` and confirm the fixture/loader is absent.
- [ ] **Step 3: Add synthetic cases and loader**. Do not put expected labels into the LLM prompt; use them only in the external harness assertion.
- [ ] **Step 4: Run the test again** and require PASS.
- [ ] **Step 5: Commit** `test: add d6 synthetic execution cases`.

### Task 2: 인증 Agent→MCP 실행 증거 하네스

**Files:**
- Modify: `backend/tests/compose_coaching_e2e.py`
- Modify: `backend/tests/test_coaching_api.py`
- Modify: `backend/tests/test_mcp_tools.py`

**Interfaces:**
- Consumes `CoachingAnalyzeRequest`, `McpStdioContextGateway`, `McpAccessTokenCodec`.
- Produces JSONL evidence with `case_id`, `http_status`, `mcp_tools`, `trace_id`, `terminal_status`; never includes answer text.

- [ ] **Step 1: Add a failing integration assertion** that a normal authenticated request returns `200` and the MCP tool list contains `get_question`, `get_practice_attempt`, and `get_job_context`.

```python
assert result["http_status"] == 200
assert set(result["mcp_tools"]) >= {
    "get_question", "get_practice_attempt", "get_job_context"
}
```

- [ ] **Step 2: Run the isolated test/Compose harness**. Expected initial failure if the harness does not expose MCP evidence.
- [ ] **Step 3: Instrument only the test sink or gateway boundary**, not the production response, to collect tool names and redacted IDs:

```python
evidence.append({
    "case_id": case_id,
    "http_status": response.status_code,
    "mcp_tools": sorted(called_tools),
    "trace_id": response.headers.get("X-Trace-Id"),
    "terminal_status": body.get("status"),
})
```

- [ ] **Step 4: Run** `python backend/tests/compose_coaching_e2e.py` through the project’s documented Compose command and save only the redacted JSON result under `evals/results/` or the existing local-results location.
- [ ] **Step 5: Commit** `test: capture authenticated agent mcp evidence`.

### Task 3: MCP 권한·잘못된 ID·도구 실패 검증

**Files:**
- Modify: `backend/tests/test_mcp_tools.py`
- Modify: `backend/tests/test_coaching_api.py`
- Inspect/modify only if required: `backend/app/services/mcp_access.py`, `backend/app/services/mcp_context_gateway.py`, `backend/app/main.py`

**Interfaces:**
- `McpAccessTokenCodec.issue(...)` remains the only context-token issuer.
- Gateway errors remain internal; API maps them to the project’s existing retryable `503`/non-retryable context status.

- [ ] **Step 1: Add failing tests** for wrong owner, wrong allowed ID, expired token, and gateway timeout.

```python
def test_wrong_owner_is_rejected():
    response = call_tool_with_token(user_id="owner-a", requested_user_id="owner-b")
    assert response.isError is True

def test_gateway_timeout_becomes_retryable_503(client, monkeypatch):
    monkeypatch.setattr("app.services.mcp_context_gateway.McpStdioContextGateway.load_context", timeout)
    response = client.post("/api/agent", headers=AUTH, json=valid_request())
    assert response.status_code == 503
    assert response.json()["detail"]["retryable"] is True
```

- [ ] **Step 2: Run** the focused MCP/API tests and confirm each fails for the missing assertion.
- [ ] **Step 3: Implement only the smallest missing mapping or test double**. Do not weaken token validation or accept arbitrary IDs.
- [ ] **Step 4: Run** `python -m pytest backend/tests/test_mcp_tools.py backend/tests/test_coaching_api.py -q` and require PASS.
- [ ] **Step 5: Commit** `test: verify mcp authorization and failure paths`.

### Task 4: Langfuse 실패 trace와 민감정보 회귀

**Files:**
- Modify: `backend/tests/test_coaching_observability.py`
- Modify: `backend/tests/test_coaching_runtime.py`
- Inspect: `backend/app/services/coaching_observability.py`, `backend/app/services/coaching_runtime.py`

**Interfaces:**
- Failure observations use the existing trace ID and redacted metadata fields.
- Required failure metadata: `status`, `error_code`, `retryable`, `attempt_count`, `latency_ms`; forbidden: transcript, quote, source URL, access token.

- [ ] **Step 1: Add failing test** for final provider/schema failure.

```python
assert observation.status == "failed"
assert observation.metadata["attempt_count"] == 2
assert observation.metadata["retryable"] is False
assert "transcript" not in observation.payload
```

- [ ] **Step 2: Run focused observability/runtime tests and confirm failure.
- [ ] **Step 3: Record final failure in the existing sink’s `finally`/completion path**, preserving the same trace ID used by provider generation and contract validation.
- [ ] **Step 4: Run** `python -m pytest backend/tests/test_coaching_observability.py backend/tests/test_coaching_runtime.py -q`.
- [ ] **Step 5: Commit** `fix: record redacted coaching failure traces`.

### Task 5: 실제 외부 검증 및 Prompt 운영 증거

**Files:**
- Create: `docs/worklogs/YYYY-MM-DD_HHMM_d6-live-execution.md`
- Modify: `docs/project2-checkpoint-work-cards.md`
- Modify if needed: `EVAL_REPORT.md`

**Interfaces:**
- Input: four synthetic cases, authenticated test user, fixed model/prompt/skill versions.
- Output: redacted evidence table with HTTP status, terminal state, MCP tool names, trace URL/ID, latency, cost, retry count.

- [ ] **Step 1: Run normal/boundary/injection cases** against the configured local or approved deployment environment; record model, prompt version, skill version, dataset version, timestamp, denominator.
- [ ] **Step 2: Run wrong-owner/invalid-ID/timeout cases** and verify expected `401/403/404/503` mapping without exposing source text.
- [ ] **Step 3: Open Langfuse and capture one success, one contract/provider failure, and one MCP failure trace. Verify prompt version, model, token, cost, latency, retry, and redaction.
- [ ] **Step 4: If managed Prompt is used, create candidate → label production → make one request → verify version → rollback candidate. Record exact version IDs and rollback result; do not claim completion from local fallback.
- [ ] **Step 5: Update D6 checkboxes only from these artifacts. Keep fixture-only items `[-]` when authenticated MCP evidence is absent.
- [ ] **Step 6: Run** `git diff --check` and the focused/full backend gate available in the environment.
- [ ] **Step 7: Commit** `docs: record d6 live execution evidence`.

## Execution Order

1. Task 1 fixes reproducible synthetic inputs.
2. Task 2 proves the normal authenticated Agent→MCP path.
3. Task 3 proves ownership, ID, timeout, and tool failure behavior.
4. Task 4 proves failure trace safety and redaction.
5. Task 5 performs external verification and updates checkpoint/worklog evidence.

## Verification Gate

Do not mark D6 complete until all of the following exist:

- One redacted normal trace with actual MCP tool calls.
- One boundary/injection run with external expected judgment preserved outside the LLM prompt.
- One wrong-owner/invalid-ID denial and one MCP timeout/failure denial.
- One Langfuse provider/schema failure trace with retry count and no sensitive payload.
- Prompt production version and rollback evidence, or an explicit documented waiver.
- Worklog links to commands, trace IDs/URLs, changed files, failures, and remaining risks.
