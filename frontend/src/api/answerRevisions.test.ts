import { describe, expect, it, vi } from "vitest";

import { confirmAnswerRevision } from "./answerRevisions";

describe("confirmAnswerRevision", () => {
  it("확정 전사문만 revision API에 전송한다", async () => {
    const fetchImpl = vi.fn(async (_url: string | URL | Request, init?: RequestInit) => new Response(JSON.stringify({
      answer_revision_id: "revision-1",
      analysis_job_id: "job-1",
      practice_session_id: "session-1",
      question_id: "preset-04",
      answer_segments: [{ segment_id: "s1", text: "확정 답변" }],
      confirmed_at: "2026-09-17T07:00:00Z",
      expires_at: "2026-09-18T07:00:00Z",
      job_snapshot_id: "job-snapshot-1",
    }), { status: 201, headers: { "Content-Type": "application/json" } }));

    const result = await confirmAnswerRevision({
      analysisJobId: "job-1",
      confirmedText: "확정 답변",
      accessToken: "access-token",
      fetchImpl: fetchImpl as typeof fetch,
    });

    expect(result.answer_revision_id).toBe("revision-1");
    expect(fetchImpl).toHaveBeenCalledOnce();
    const [, init] = fetchImpl.mock.calls[0];
    expect(init?.headers).toEqual({ Authorization: "Bearer access-token", "Content-Type": "application/json" });
    expect(JSON.parse(String(init?.body))).toEqual({ confirmed_text: "확정 답변" });
  });
});
