#!/usr/bin/env python3
"""Benchmark /analysis-jobs from upload through completed status."""

from __future__ import annotations

import argparse
import json
import math
import mimetypes
import os
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import httpx


DEFAULT_CUSTOM_QUESTION = (
    "Python, FastAPI, Docker를 사용한 프로젝트에서 문제를 해결한 경험을 설명해 주세요."
)


@dataclass(frozen=True)
class RunResult:
    index: int
    warmup: bool
    audio: str
    job_id: str
    practice_session_id: str | None
    submit_sec: float
    after_202_to_terminal_sec: float
    total_sec: float
    poll_count: int
    status: str
    server_stt_sec: float | None
    audio_duration_sec: float | None
    server_rtf: float | None
    model: str | None
    device: str | None
    compute_type: str | None


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def metric_summary(values: list[float]) -> dict[str, float | int | None]:
    return {
        "count": len(values),
        "min": min(values) if values else None,
        "mean": statistics.fmean(values) if values else None,
        "p50": statistics.median(values) if values else None,
        "p95": percentile(values, 0.95),
        "max": max(values) if values else None,
    }


def summarize(records: list[RunResult]) -> dict[str, Any]:
    measured = [row for row in records if not row.warmup]
    completed = [row for row in measured if row.status == "completed"]

    def numeric(name: str) -> list[float]:
        result: list[float] = []
        for row in completed:
            value = getattr(row, name)
            if isinstance(value, (int, float)):
                result.append(float(value))
        return result

    return {
        "measured_runs": len(measured),
        "completed_runs": len(completed),
        "failed_runs": len(measured) - len(completed),
        "submit_sec": metric_summary(numeric("submit_sec")),
        "after_202_to_terminal_sec": metric_summary(
            numeric("after_202_to_terminal_sec")
        ),
        "total_sec": metric_summary(numeric("total_sec")),
        "server_stt_sec": metric_summary(numeric("server_stt_sec")),
        "server_rtf": metric_summary(numeric("server_rtf")),
    }


def fmt(value: float | int | None, digits: int = 3) -> str:
    return "-" if value is None else f"{float(value):.{digits}f}"


def render_markdown(
    *,
    label: str,
    base_url: str,
    records: list[RunResult],
    summary: dict[str, Any],
) -> str:
    measured = [row for row in records if not row.warmup]
    first = records[0] if records else None
    lines = [
        f"# Analysis E2E benchmark — {label}",
        "",
        f"- Base URL: {base_url}",
        f"- Warmup runs: {sum(1 for row in records if row.warmup)}",
        f"- Measured runs: {len(measured)}",
        f"- Completed: {summary['completed_runs']}",
        f"- Failed: {summary['failed_runs']}",
        "",
    ]
    if first:
        lines += [
            "## First request",
            "",
            f"- submit: {first.submit_sec:.3f}s",
            f"- 202 → terminal: {first.after_202_to_terminal_sec:.3f}s",
            f"- total: {first.total_sec:.3f}s",
            f"- server STT: {fmt(first.server_stt_sec)}s",
            "",
        ]

    lines += [
        "## Warm/measured summary",
        "",
        "| Metric | p50 | p95 | mean | min | max |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key, title in (
        ("submit_sec", "POST → 202"),
        ("after_202_to_terminal_sec", "202 → completed/failed"),
        ("total_sec", "POST start → completed/failed"),
        ("server_stt_sec", "Server STT processing"),
        ("server_rtf", "Server STT RTF"),
    ):
        data = summary[key]
        lines.append(
            f"| {title} | {fmt(data['p50'])} | {fmt(data['p95'])} | "
            f"{fmt(data['mean'])} | {fmt(data['min'])} | {fmt(data['max'])} |"
        )

    lines += [
        "",
        "## Runs",
        "",
        "| # | Warmup | Audio | Status | Submit s | 202→terminal s | Total s | STT s | RTF | Device | Compute |",
        "| ---: | :---: | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in records:
        lines.append(
            f"| {row.index} | {'Y' if row.warmup else 'N'} | "
            f"{Path(row.audio).name} | {row.status} | {row.submit_sec:.3f} | "
            f"{row.after_202_to_terminal_sec:.3f} | {row.total_sec:.3f} | "
            f"{fmt(row.server_stt_sec)} | {fmt(row.server_rtf)} | "
            f"{row.device or '-'} | {row.compute_type or '-'} |"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url",
        default=os.getenv("ANALYSIS_BENCH_BASE_URL", "http://127.0.0.1:8000"),
    )
    parser.add_argument(
        "--token",
        default=os.getenv("ANALYSIS_BENCH_TOKEN"),
        help="Bearer token. Prefer ANALYSIS_BENCH_TOKEN to avoid shell history.",
    )
    parser.add_argument("--audio", type=Path, nargs="+", required=True)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--poll-interval", type=float, default=0.25)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--request-timeout", type=float, default=30.0)
    parser.add_argument("--label", default="benchmark")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("local-results/analysis-e2e-benchmark"),
    )
    parser.add_argument("--keep-jobs", action="store_true")
    parser.add_argument("--practice-session-id")
    parser.add_argument("--job-posting-id")
    parser.add_argument("--requirement-id", action="append", default=[])
    parser.add_argument(
        "--question-type",
        choices=("custom", "preset"),
        default="custom",
    )
    parser.add_argument("--question-id")
    parser.add_argument(
        "--custom-question-text",
        default=DEFAULT_CUSTOM_QUESTION,
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not args.token:
        raise ValueError(
            "Bearer token is required. Set ANALYSIS_BENCH_TOKEN or pass --token."
        )
    if args.runs < 1 or args.warmup < 0:
        raise ValueError("--runs must be >= 1 and --warmup must be >= 0")
    if args.poll_interval <= 0 or args.timeout <= 0 or args.request_timeout <= 0:
        raise ValueError("poll/request timeouts must be positive")
    for path in args.audio:
        if not path.is_file():
            raise FileNotFoundError(path)

    if args.practice_session_id and args.job_posting_id:
        raise ValueError(
            "use either --practice-session-id or --job-posting-id, not both"
        )
    if args.job_posting_id and not (1 <= len(args.requirement_id) <= 2):
        raise ValueError(
            "--job-posting-id requires one or two --requirement-id values"
        )
    if not args.job_posting_id and args.requirement_id:
        raise ValueError("--requirement-id requires --job-posting-id")

    if args.question_type == "preset":
        if not args.question_id:
            raise ValueError("--question-id is required for preset questions")
    elif not args.custom_question_text.strip():
        raise ValueError("--custom-question-text must not be blank")

    total = args.warmup + args.runs
    if args.keep_jobs and (args.practice_session_id or args.job_posting_id) and total > 1:
        raise ValueError(
            "--keep-jobs cannot repeat attempt 1 on one practice session"
        )


def question_fields(args: argparse.Namespace) -> dict[str, str]:
    fields = {
        "question_type": args.question_type,
        "attempt_no": "1",
    }
    if args.question_type == "preset":
        fields["question_id"] = args.question_id
    else:
        fields["custom_question_text"] = args.custom_question_text.strip()
    return fields


def create_practice_session(
    client: httpx.Client,
    args: argparse.Namespace,
) -> str | None:
    if args.practice_session_id:
        return args.practice_session_id
    if not args.job_posting_id:
        return None

    body: dict[str, Any] = {
        "job_posting_id": args.job_posting_id,
        "requirement_ids": args.requirement_id,
        "question_type": args.question_type,
        "question_id": args.question_id if args.question_type == "preset" else None,
        "custom_question_text": (
            args.custom_question_text.strip()
            if args.question_type == "custom"
            else None
        ),
    }
    response = client.post("/api/practice-sessions", json=body)
    if response.status_code != 201:
        raise RuntimeError(
            f"practice session creation failed: HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )
    payload = response.json()
    value = payload.get("practice_session_id")
    if not isinstance(value, str) or not value:
        raise RuntimeError("practice session response has no practice_session_id")
    return value


def poll_job(
    client: httpx.Client,
    job_id: str,
    *,
    poll_interval: float,
    timeout: float,
) -> tuple[dict[str, Any], int]:
    deadline = time.perf_counter() + timeout
    polls = 0
    while True:
        polls += 1
        response = client.get(f"/analysis-jobs/{job_id}")
        if response.status_code != 200:
            raise RuntimeError(
                f"job polling failed: HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )
        payload = response.json()
        status = payload.get("status")
        if status in {"completed", "failed"}:
            return payload, polls
        if time.perf_counter() >= deadline:
            raise TimeoutError(
                f"analysis job did not finish within {timeout}s: {job_id}"
            )
        time.sleep(poll_interval)


def _float_or_none(value: object) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def _str_or_none(value: object) -> str | None:
    return value if isinstance(value, str) else None


def run_once(
    client: httpx.Client,
    args: argparse.Namespace,
    *,
    audio: Path,
    index: int,
    warmup: bool,
    practice_session_id: str | None,
) -> RunResult:
    source_id = f"bench-{int(time.time() * 1000)}-{index}"
    fields = {"source_id": source_id, **question_fields(args)}
    if practice_session_id:
        fields["practice_session_id"] = practice_session_id

    content_type = mimetypes.guess_type(audio.name)[0] or "application/octet-stream"
    overall_started = time.perf_counter()
    with audio.open("rb") as handle:
        response = client.post(
            "/analysis-jobs",
            data=fields,
            files={"audio": (audio.name, handle, content_type)},
        )
    submit_sec = time.perf_counter() - overall_started
    if response.status_code != 202:
        raise RuntimeError(
            f"analysis upload failed: HTTP {response.status_code}: "
            f"{response.text[:1000]}"
        )

    created = response.json()
    job_id = created.get("job_id")
    if not isinstance(job_id, str) or not job_id:
        raise RuntimeError("analysis response has no job_id")
    actual_session_id = created.get("practice_session_id")
    if not isinstance(actual_session_id, str):
        actual_session_id = practice_session_id

    terminal_started = time.perf_counter()
    try:
        terminal, poll_count = poll_job(
            client,
            job_id,
            poll_interval=args.poll_interval,
            timeout=args.timeout,
        )
        terminal_sec = time.perf_counter() - terminal_started
        total_sec = time.perf_counter() - overall_started
        result = terminal.get("result")
        if not isinstance(result, dict):
            result = {}
        return RunResult(
            index=index,
            warmup=warmup,
            audio=str(audio),
            job_id=job_id,
            practice_session_id=actual_session_id,
            submit_sec=submit_sec,
            after_202_to_terminal_sec=terminal_sec,
            total_sec=total_sec,
            poll_count=poll_count,
            status=str(terminal.get("status", "unknown")),
            server_stt_sec=_float_or_none(result.get("processing_time_sec")),
            audio_duration_sec=_float_or_none(result.get("audio_duration_sec")),
            server_rtf=_float_or_none(result.get("rtf")),
            model=_str_or_none(result.get("model")),
            device=_str_or_none(result.get("device")),
            compute_type=_str_or_none(result.get("compute_type")),
        )
    finally:
        if not args.keep_jobs:
            cleanup = client.delete(f"/analysis-jobs/{job_id}")
            if cleanup.status_code not in {204, 404}:
                print(
                    f"[warn] failed to delete benchmark job {job_id}: "
                    f"HTTP {cleanup.status_code}",
                    file=sys.stderr,
                )


def main() -> int:
    args = parse_args()
    try:
        validate_args(args)
    except (ValueError, FileNotFoundError) as error:
        raise SystemExit(str(error)) from error

    base_url = args.base_url.rstrip("/")
    records: list[RunResult] = []
    with httpx.Client(
        base_url=base_url,
        headers={"Authorization": f"Bearer {args.token}"},
        timeout=args.request_timeout,
        follow_redirects=True,
    ) as client:
        health = client.get("/health")
        if health.status_code != 200:
            raise SystemExit(
                f"health check failed: HTTP {health.status_code}: "
                f"{health.text[:500]}"
            )

        practice_session_id = create_practice_session(client, args)
        if practice_session_id:
            print(f"[session] {practice_session_id}", flush=True)
        else:
            print(
                "[session] no practice session; posting-based dynamic hints "
                "are not exercised",
                flush=True,
            )

        total = args.warmup + args.runs
        for offset in range(total):
            warmup = offset < args.warmup
            audio = args.audio[offset % len(args.audio)]
            print(
                f"[{'warmup' if warmup else 'run'}] "
                f"{offset + 1}/{total} {audio.name}",
                flush=True,
            )
            row = run_once(
                client,
                args,
                audio=audio,
                index=offset + 1,
                warmup=warmup,
                practice_session_id=practice_session_id,
            )
            records.append(row)
            print(
                f"  status={row.status} submit={row.submit_sec:.3f}s "
                f"after202={row.after_202_to_terminal_sec:.3f}s "
                f"total={row.total_sec:.3f}s stt={fmt(row.server_stt_sec)}s",
                flush=True,
            )

    summary = summarize(records)
    result_dir = args.output_dir / args.label
    result_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "label": args.label,
        "base_url": base_url,
        "practice_session_id": (
            practice_session_id
            if (args.practice_session_id or args.job_posting_id)
            else None
        ),
        "question_type": args.question_type,
        "warmup": args.warmup,
        "runs": args.runs,
        "audio_files": [str(path) for path in args.audio],
        "summary": summary,
        "records": [asdict(row) for row in records],
    }
    (result_dir / "summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown = render_markdown(
        label=args.label,
        base_url=base_url,
        records=records,
        summary=summary,
    )
    (result_dir / "SUMMARY.md").write_text(markdown, encoding="utf-8")
    print()
    print(markdown)
    return 1 if summary["failed_runs"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
