#!/usr/bin/env python3
"""Run the fixed STT Test B three-way comparison without Makefile dependencies."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_PYTHON = PROJECT_ROOT / ".venvs/stt-runtime/bin/python"
EVALUATOR = PROJECT_ROOT / "[REDACTED].py"
PREFLIGHT = PROJECT_ROOT / "backend/scripts/validate_stt_test_b_ready.py"
COMPARE = PROJECT_ROOT / "backend/scripts/compare_stt_test_b_metrics.py"
TEST_B = PROJECT_ROOT / "data/stt/holdout-test-b-clean"
OUTPUT_ROOT = PROJECT_ROOT / "artifacts/stt/test-b"

MODELS = {
    "baseline": PROJECT_ROOT
    / "[REDACTED]",
    "retrain": PROJECT_ROOT
    / "[REDACTED]",
    "clean-continuation": PROJECT_ROOT
    / "[REDACTED]",
}


def runtime_env() -> dict[str, str]:
    env = os.environ.copy()
    libs = [
        PROJECT_ROOT
        / ".venvs/stt-train/lib/python3.[REDACTED]",
        PROJECT_ROOT
        / ".venvs/stt-train/lib/python3.[REDACTED]",
    ]
    existing = env.get("LD_LIBRARY_PATH")
    env["LD_LIBRARY_PATH"] = ":".join(
        [*(str(path) for path in libs), *([existing] if existing else [])]
    )
    return env


def run(argv: list[str], *, env: dict[str, str] | None = None) -> None:
    print("+ " + " ".join(argv), flush=True)
    subprocess.run(argv, cwd=PROJECT_ROOT, env=env, check=True)


def metrics_complete(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        data.get("utterances") == 500
        and data.get("start_index") == 0
        and data.get("beam_size") == 5
        and data.get("compute_type") == "float16"
        and Path(str(data.get("eval_dir", ""))).resolve() == TEST_B.resolve()
    )


def main() -> int:
    if not RUNTIME_PYTHON.is_file():
        raise FileNotFoundError(RUNTIME_PYTHON)

    run([sys.executable, str(PREFLIGHT)])

    env = runtime_env()
    for name, model in MODELS.items():
        output = OUTPUT_ROOT / name
        metrics = output / "metrics.json"
        if metrics_complete(metrics):
            print(f"[skip] {name}: complete Test B metrics already exist", flush=True)
            continue
        run(
            [
                str(RUNTIME_PYTHON),
                str(EVALUATOR),
                "--model",
                str(model),
                "--eval-dir",
                str(TEST_B),
                "--output-dir",
                str(output),
            ],
            env=env,
        )

    run([sys.executable, str(COMPARE)])
    print(f"comparison: {OUTPUT_ROOT / 'comparison.json'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
