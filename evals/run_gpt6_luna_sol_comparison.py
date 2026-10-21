#!/usr/bin/env python3
"""Prepare or run the fixed GPT-6 Luna/Sol candidate comparison.

Network calls are disabled unless --live is supplied. The actual evaluation
logic stays in run_model_comparison.py so prompt, schema, repair, scoring, and
usage accounting remain canonical.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CANDIDATES = (
    "flash-lite=openai:google/gemini-3.5-flash-lite",
    "gpt6-luna=openai:openai/gpt-6-luna",
    "gpt6-sol=openai:openai/gpt-6-sol",
)
PREFLIGHT_CASES = (
    "coach-normal-01",
    "coach-boundary-13",
    "coach-failure-30",
)
PROMPT_VERSION = "coaching-output-v4.1"
SKILL_VERSION = "interview-coach-v2"
MAX_CALLS = 2
TIMEOUT_SECONDS = 90
MAX_COMPLETION_TOKENS = 2048
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def default_output_dir(phase: str) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return ROOT / "local-results" / f"gpt6-luna-sol-{phase}-{stamp}"


def build_command(phase: str, output_dir: Path) -> list[str]:
    command = [
        sys.executable,
        "-B",
        str(ROOT / "evals" / "run_model_comparison.py"),
        "--dataset",
        str(ROOT / "evals" / "dataset.v2.jsonl"),
    ]
    for candidate in CANDIDATES:
        command.extend(("--candidate", candidate))
    command.extend(
        (
            "--max-calls",
            str(MAX_CALLS),
            "--timeout-seconds",
            str(TIMEOUT_SECONDS),
            "--max-completion-tokens",
            str(MAX_COMPLETION_TOKENS),
            "--prompt-version",
            PROMPT_VERSION,
            "--skill-version",
            SKILL_VERSION,
            "--output-dir",
            str(output_dir),
        )
    )
    if phase == "preflight":
        for case_id in PREFLIGHT_CASES:
            command.extend(("--case-id", case_id))
    return command


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase",
        choices=("preflight", "full"),
        default="preflight",
        help="preflight=대표 3건, full=Dataset v2 전체 30건",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="실제 OpenRouter 호출 허용. 없으면 실행 계획만 출력",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="결과 디렉터리. 생략 시 local-results 아래 UTC timestamp 사용",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = (args.output_dir or default_output_dir(args.phase)).resolve()
    command = build_command(args.phase, output_dir)
    case_count = len(PREFLIGHT_CASES) if args.phase == "preflight" else 30
    plan = {
        "phase": args.phase,
        "network_calls": bool(args.live),
        "openrouter_key_present": bool(os.getenv("OPENROUTER_API_KEY", "").strip()),
        "candidates": list(CANDIDATES),
        "prompt_version": PROMPT_VERSION,
        "skill_version": SKILL_VERSION,
        "cases": list(PREFLIGHT_CASES) if args.phase == "preflight" else "dataset.v2.jsonl:30",
        "planned_unique_executions": case_count * len(CANDIDATES),
        "max_calls_per_execution": MAX_CALLS,
        "maximum_provider_calls": case_count * len(CANDIDATES) * MAX_CALLS,
        "timeout_seconds": TIMEOUT_SECONDS,
        "output_dir": str(output_dir),
        "command": shlex.join(command),
    }
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    if not args.live:
        return 0
    child_env = os.environ.copy()
    child_env["MODEL_API_BASE_URL"] = OPENROUTER_BASE_URL
    completed = subprocess.run(command, cwd=ROOT, check=False, env=child_env)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
