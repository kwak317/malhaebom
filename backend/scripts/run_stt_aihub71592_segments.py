#!/usr/bin/env python3
"""Launch AI Hub 71592 segmentation with the dedicated STT runtime and CUDA libs."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "backend/scripts/prepare_stt_aihub71592_segments.py"
RUNTIME_PYTHON = ROOT / ".venvs/stt-runtime/bin/python"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--preflight-only", action="store_true")
    p.add_argument("--pilot", action="store_true")
    return p.parse_args()


def runtime_env() -> dict[str, str]:
    env = os.environ.copy()
    libs: list[str] = []
    for py_dir in sorted((ROOT / ".venvs/stt-train/lib").glob("python3.*")):
        for rel in ("site-packages/nvidia/cublas/lib", "site-packages/nvidia/cudnn/lib"):
            candidate = py_dir / rel
            if candidate.is_dir():
                libs.append(str(candidate))
    existing = env.get("LD_LIBRARY_PATH")
    env["LD_LIBRARY_PATH"] = ":".join([*libs, *([existing] if existing else [])])
    return env


def main() -> int:
    args = parse_args()
    if not RUNTIME_PYTHON.is_file():
        raise FileNotFoundError(RUNTIME_PYTHON)
    argv = [str(RUNTIME_PYTHON), str(WORKER)]
    if args.preflight_only:
        argv.append("--preflight-only")
    if args.pilot:
        argv.extend(
            [
                "--pilot-records-per-split",
                "3",
                "--output-root",
                "data/stt/aihub71592-ict-new-segmented-pilot",
                "--overwrite",
            ]
        )
    print("+ " + " ".join(argv), flush=True)
    subprocess.run(argv, cwd=ROOT, env=runtime_env(), check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
