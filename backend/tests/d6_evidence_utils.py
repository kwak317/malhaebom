from __future__ import annotations

from collections.abc import Iterable


def build_redacted_evidence(
    *,
    case_id: str,
    http_status: int,
    called_tools: Iterable[str],
    trace_id: str | None,
    terminal_status: str | None,
    **_sensitive_fields: object,
) -> dict[str, object]:
    """Return D6 execution metadata without answer or source payloads."""
    return {
        "case_id": case_id,
        "http_status": http_status,
        "mcp_tools": sorted(set(called_tools)),
        "trace_id": trace_id,
        "terminal_status": terminal_status,
    }
