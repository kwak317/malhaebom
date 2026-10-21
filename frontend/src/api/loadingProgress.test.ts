import { afterEach, describe, expect, it, vi } from "vitest";
import { progressFetch } from "./loadingProgress";

afterEach(() => vi.unstubAllGlobals());

function streamed(text: string, status = 200) {
  const encoded = new TextEncoder().encode(text);
  return new Response(new ReadableStream({ start(controller) {
    // Split inside Korean UTF-8 bytes as well as JSON event boundaries.
    for (let i = 0; i < encoded.length; i += 7) controller.enqueue(encoded.slice(i, i + 7));
    controller.close();
  } }), { status, headers: { "Content-Type": "application/x-ndjson" } });
}

describe("real request progress", () => {
  it("decodes split stages and preserves result body/status/trace", async () => {
    const observed: string[] = [];
    const listener = (event: Event) => observed.push((event as CustomEvent).detail.stage);
    window.addEventListener("coach-request-progress", listener);
    const fetcher = vi.fn().mockResolvedValue(streamed(
      JSON.stringify({ type: "progress", stage: "공고 검토 중…" }) + "\n" +
      JSON.stringify({ type: "heartbeat" }) + "\n" +
      JSON.stringify({ type: "result", status: 201, body: { value: "완료" }, headers: { "x-trace-id": "trace" } }),
    ));
    vi.stubGlobal("fetch", fetcher);
    try {
      const response = await progressFetch("https://api.example/api/job-search/recommendations", { method: "POST" });
      expect(observed).toContain("공고 검토 중…");
      expect(response.status).toBe(201);
      expect(response.headers.get("x-trace-id")).toBe("trace");
      expect(await response.json()).toEqual({ value: "완료" });
      expect(fetcher.mock.calls[0][1].headers.get("Accept")).toBe("application/x-ndjson");
    } finally { window.removeEventListener("coach-request-progress", listener); }
  });

  it("restores auth failure status for existing API handlers", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(streamed(JSON.stringify({
      type: "result", status: 401, body: { detail: "로그인 필요" },
    }) + "\n")));
    const response = await progressFetch("https://api.example/api/agent");
    expect(response.ok).toBe(false);
    expect(response.status).toBe(401);
  });

  it("passes through legacy JSON and rejects interrupted results", async () => {
    const legacy = new Response('{"ok":true}', { status: 200 });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(legacy).mockResolvedValueOnce(streamed(
      JSON.stringify({ type: "progress", stage: "읽는 중…" }) + "\n",
    )));
    expect(await progressFetch("https://api.example/api/github/readme/analyze")).toBe(legacy);
    await expect(progressFetch("https://api.example/api/github/readme/analyze")).rejects.toThrow("진행 결과");
  });

  it("delivers an event while the final response is still pending", async () => {
    let controller!: ReadableStreamDefaultController;
    const response = new Response(new ReadableStream({ start(value) { controller = value; } }), {
      headers: { "Content-Type": "application/x-ndjson" },
    });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));
    const seen: string[] = [];
    const listener = (e: Event) => seen.push((e as CustomEvent).detail.stage);
    window.addEventListener("coach-request-progress", listener);
    try {
      let finished = false;
      const pending = progressFetch("https://api.example/api/agent").then(value => { finished = true; return value; });
      controller.enqueue(new TextEncoder().encode('{"type":"progress","stage":"분석 중…"}\n'));
      await vi.waitFor(() => expect(seen).toContain("분석 중…"));
      expect(finished).toBe(false);
      controller.enqueue(new TextEncoder().encode('{"type":"result","status":200,"body":{"ok":true}}\n'));
      controller.close();
      expect(await (await pending).json()).toEqual({ ok: true });
    } finally { window.removeEventListener("coach-request-progress", listener); }
  });
});
