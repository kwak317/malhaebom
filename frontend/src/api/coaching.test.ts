import { describe, expect, it } from "vitest";
import { CoachingApiError, DEFAULT_COACHING_TIMEOUT_MS, requestCoaching } from "./coaching";
import type { CoachingFailureState } from "./coaching";

const request = {
  action: "analyze" as const,
  question_id: "preset-04",
  answer_revision_id: "00000000-0000-0000-0000-000000000101",
  job_snapshot_id: "00000000-0000-0000-0000-000000000201",
};

describe("requestCoaching", () => {
  it("MCP 장애 상태를 서버 계약과 같은 실패 상태로 표현한다", () => {
    const state: CoachingFailureState = "mcp_error";

    expect(state).toBe("mcp_error");
  });

  it("로컬 코칭 서버의 180초 제한보다 긴 기본 대기 시간을 사용한다", () => {
    expect(DEFAULT_COACHING_TIMEOUT_MS).toBe(200_000);
  });

  it("공통 rate limit 상태와 재시도 가능 여부를 보존한다", async () => {
    const fetchImpl = async () => new Response(JSON.stringify({
      detail: {
        state: "rate_limited",
        code: "COACHING_RATE_LIMITED",
        message: "잠시 뒤 다시 시도해 주세요.",
        retryable: true,
      },
    }), { status: 429, headers: { "Content-Type": "application/json" } });

    await expect(requestCoaching({ request, accessToken: "test-token", fetchImpl })).rejects.toMatchObject({
      name: "CoachingApiError",
      state: "rate_limited",
      retryable: true,
      status: 429,
    } satisfies Partial<CoachingApiError>);
  });

  it("성공 응답의 핵심 배열이 없으면 schema_violation으로 바꾼다", async () => {
    const fetchImpl = async () => new Response(JSON.stringify({ status: "ok" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });

    await expect(requestCoaching({ request, accessToken: "test-token", fetchImpl })).rejects.toMatchObject({
      state: "schema_violation",
      retryable: true,
    });
  });

  it("정상 코칭 응답에 예시 답변이 없으면 schema_violation으로 바꾼다", async () => {
    const fetchImpl = async () => new Response(JSON.stringify({
      status: "ok",
      job_alignment: [],
      intent_assessment: { label: "aligned", reason: "질문에 맞습니다." },
      criterion_assessments: [],
      evidence: [],
      gaps: [],
      clarifying_question: null,
      next_actions: [],
      example_answer: null,
    }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });

    await expect(requestCoaching({ request, accessToken: "test-token", fetchImpl })).rejects.toMatchObject({
      state: "schema_violation",
      retryable: true,
    });
  });
});
