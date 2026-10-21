"""Opt-in progress transport; existing JSON clients keep their response contract."""
import asyncio
import json
import re
from contextvars import ContextVar

_sink: ContextVar = ContextVar("loading_progress_sink", default=None)
PROGRESS_PATHS = {
    "/api/resume/analyze", "/api/github/readme/analyze", "/api/job-search/recommendations", "/api/agent",
}


def report_progress(stage: str) -> None:
    sink = _sink.get()
    if sink is not None:
        loop, queue = sink
        loop.call_soon_threadsafe(queue.put_nowait, {"type": "progress", "stage": stage})


class LoadingProgressMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        headers = dict(scope.get("headers", []))
        if (scope["type"] != "http" or scope.get("method") != "POST"
                or (scope.get("path") not in PROGRESS_PATHS and not re.fullmatch(r"/analysis-jobs/[0-9a-fA-F-]{36}/normalize-transcript", scope.get("path", "")))
                or b"application/x-ndjson" not in headers.get(b"accept", b"")):
            return await self.app(scope, receive, send)
        queue = asyncio.Queue()
        status, response_headers, chunks = 500, {}, []

        async def capture(message):
            nonlocal status, response_headers
            if message["type"] == "http.response.start":
                status = message["status"]
                response_headers = {k.decode(): v.decode() for k, v in message.get("headers", [])
                                    if k.lower() in {b"x-trace-id", b"x-mcp-tools"}}
            elif message["type"] == "http.response.body":
                chunks.append(message.get("body", b""))

        async def run():
            token = _sink.set((asyncio.get_running_loop(), queue))
            try:
                # Only the original app reads receive; no competing body reader.
                await self.app(scope, receive, capture)
                queue.put_nowait({"type": "result", "status": status,
                                  "body": json.loads(b"".join(chunks)), "headers": response_headers})
            except Exception:
                queue.put_nowait({"type": "result", "status": 500,
                                  "body": {"detail": "작업을 완료하지 못했습니다. 다시 시도해 주세요."}})
            finally:
                _sink.reset(token)

        task = asyncio.create_task(run())
        try:
            await send({"type": "http.response.start", "status": 200, "headers": [
                (b"content-type", b"application/x-ndjson; charset=utf-8"),
                (b"cache-control", b"no-store"), (b"x-accel-buffering", b"no"),
            ]})
            event = {"type": "progress", "stage": "요청을 확인하고 있어요…"}
            while True:
                await send({"type": "http.response.body", "body": encode(event), "more_body": True})
                if event["type"] == "result":
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=10)
                except asyncio.TimeoutError:
                    event = {"type": "heartbeat"}
            await send({"type": "http.response.body", "body": b"", "more_body": False})
        finally:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)


def install_loading_progress(app) -> None:
    app.add_middleware(LoadingProgressMiddleware)


def encode(event: dict) -> bytes:
    return (json.dumps(event, ensure_ascii=False) + "\n").encode()
