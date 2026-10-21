import { useEffect, useState } from "react";

const eventName = "coach-request-progress";
type ProgressEvent = { path: string; requestId: number; stage: string };
let nextRequestId = 0;
const active = new Map<string, ProgressEvent>();
const latest = new Map<string, number>();

function publish(event: ProgressEvent) {
  if ((latest.get(event.path) || 0) > event.requestId) return;
  latest.set(event.path, event.requestId);
  active.set(event.path, event);
  window.dispatchEvent(new CustomEvent(eventName, { detail: event }));
}

export function useLoadingProgress(path: string, fallback: string) {
  const [stage, setStage] = useState(() => active.get(path)?.stage || fallback);
  useEffect(() => {
    const receive = (event: Event) => {
      const detail = (event as CustomEvent<ProgressEvent>).detail;
      if (detail.path === path) setStage(detail.stage);
    };
    window.addEventListener(eventName, receive);
    return () => window.removeEventListener(eventName, receive);
  }, [path]);
  return stage;
}

/** Decode real server events, then restore the original JSON/status contract. */
export const progressFetch: typeof fetch = async (input, init) => {
  const path = new URL(String(input), window.location.origin).pathname;
  const requestId = ++nextRequestId;
  publish({ path, requestId, stage: "요청을 준비하고 있어요…" });
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/x-ndjson");
  let reader: ReadableStreamDefaultReader<Uint8Array> | undefined;
  try {
    const response = await fetch(input, { ...init, headers });
    if (!response.headers.get("content-type")?.includes("application/x-ndjson") || !response.body) return response;
    reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let result: Response | null = null;
    const process = (line: string) => {
      if (!line.trim()) return;
      const event = JSON.parse(line);
      if (event.type === "progress" && typeof event.stage === "string") {
        publish({ path, requestId, stage: event.stage });
      } else if (event.type === "result") {
        result = new Response(JSON.stringify(event.body), {
          status: event.status, headers: { ...event.headers, "Content-Type": "application/json" },
        });
      }
    };
    for (;;) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      let newline: number;
      while ((newline = buffer.indexOf("\n")) >= 0) {
        process(buffer.slice(0, newline));
        buffer = buffer.slice(newline + 1);
      }
      if (done) break;
    }
    process(buffer);
    if (!result) throw new Error("진행 결과를 받지 못했습니다. 다시 시도해 주세요.");
    return result;
  } finally {
    await reader?.cancel().catch(() => undefined);
    if (active.get(path)?.requestId === requestId) active.delete(path);
  }
};
