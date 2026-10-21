"""사용자 HTTP 요청과 Langfuse trace를 서버가 생성한 ID로 연결한다."""
import logging
from fastapi.responses import PlainTextResponse

from app.services.coaching_observability import activate_coaching_trace, reset_coaching_trace

CHAT_PATHS = {"/api/agent/preparation", "/api/agent/chat"}
TRACE_HEADERS = ["X-Trace-Id", "X-Request-Id", "X-MCP-Tools"]


def record_request_link(app, request, trace_id, status_code, latency_ms):
    logging.getLogger(__name__).info("request_trace_link request_id=%s trace_id=%s method=%s path=%s status=%s",
        trace_id, trace_id, request.method, request.url.path, status_code, extra={
        "request_id": trace_id, "trace_id": trace_id, "path": request.url.path,
        "method": request.method, "http_status": status_code})
    callback = getattr(app.state.coaching_observation_sink, "record_http_request", None)
    if callback is not None:
        try:
            callback(trace_id=trace_id, method=request.method, path=request.url.path,
                     status_code=status_code, latency_ms=latency_ms)
        except Exception:
            logging.getLogger(__name__).warning("request_trace_export_failed trace_id=%s", trace_id)


def register_chat_request_tracing(app):
    import time

    @app.middleware("http")
    async def trace_chat_request(request, call_next):
        if request.method != "POST" or request.url.path not in CHAT_PATHS:
            return await call_next(request)
        trace, token = activate_coaching_trace()
        request.state.coaching_trace_id = trace.trace_id
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Trace-Id"] = trace.trace_id
            response.headers["X-Request-Id"] = trace.trace_id
            return response
        except Exception as error:
            logging.getLogger(__name__).error("request_trace_failed trace_id=%s error_type=%s",
                                              trace.trace_id, type(error).__name__)
            return PlainTextResponse("Internal Server Error", status_code=500,
                headers={"X-Trace-Id": trace.trace_id, "X-Request-Id": trace.trace_id})
        finally:
            record_request_link(app, request, trace.trace_id, status_code,
                                (time.perf_counter() - started) * 1000)
            reset_coaching_trace(token)
