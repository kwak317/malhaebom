#!/usr/bin/env python3
"""Final fixed Test B regression check: existing B0 result vs B1 checkpoint-300."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEST_B = ROOT / "data/stt/holdout-test-b-clean"
RUNTIME_PYTHON = ROOT / ".venvs/stt-runtime/bin/python"
EVALUATOR = ROOT / "backend/scripts/evaluate_stt_ct2.py"
COMPARE = ROOT / "backend/scripts/compare_stt_test_b_b1_final.py"

B0_MODEL = ROOT / "artifacts/stt/whisper-medium-busan-qlora-clean-cont-lr2e-5-ct2"
B0_METRICS = ROOT / "artifacts/stt/test-b/clean-continuation/metrics.json"
B1_MODEL = ROOT / "artifacts/stt/persona-retention-models/b1-cp300-ct2"
B1_OUTPUT = ROOT / "artifacts/stt/test-b/b1-cp300-final"
EXPECTED_ROWS = 500
REQUIRED_CT2 = (
    "config.json",
    "model.bin",
    "tokenizer.json",
    "vocabulary.json",
    "preprocessor_config.json",
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--preflight-only", action="store_true")
    return p.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def runtime_env() -> dict[str, str]:
    env = os.environ.copy()
    lib_dirs: list[str] = []
    for py_dir in sorted((ROOT / ".venvs/stt-train/lib").glob("python3.*")):
        for rel in ("site-packages/nvidia/cublas/lib", "site-packages/nvidia/cudnn/lib"):
            candidate = py_dir / rel
            if candidate.is_dir():
                lib_dirs.append(str(candidate))
    existing = env.get("LD_LIBRARY_PATH")
    env["LD_LIBRARY_PATH"] = ":".join(
        [*lib_dirs, *([existing] if existing else [])]
    )
    return env


def run(argv: list[str], *, env: dict[str, str] | None = None) -> None:
    print("+ " + " ".join(argv), flush=True)
    subprocess.run(argv, cwd=ROOT, env=env, check=True)


def load_metrics(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def validate_model(name: str, model: Path) -> None:
    missing = [filename for filename in REQUIRED_CT2 if not (model / filename).is_file()]
    if missing:
        raise FileNotFoundError(f"{name} CT2 incomplete: {missing}")


def validate() -> None:
    manifest = TEST_B / "manifest.jsonl"
    rows = [
        json.loads(line)
        for line in manifest.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != EXPECTED_ROWS:
        raise RuntimeError(f"Test B rows {len(rows)} != {EXPECTED_ROWS}")
    missing_audio = [
        row["audio"] for row in rows if not (TEST_B / row["audio"]).is_file()
    ]
    if missing_audio:
        raise FileNotFoundError(f"missing Test B audio: {missing_audio[0]}")

    if not RUNTIME_PYTHON.is_file():
        raise FileNotFoundError(RUNTIME_PYTHON)
    validate_model("B0", B0_MODEL)
    validate_model("B1", B1_MODEL)

    for filename in ("config.json", "tokenizer.json", "vocabulary.json"):
        if sha256(B0_MODEL / filename) != sha256(B1_MODEL / filename):
            raise RuntimeError(f"B0/B1 CT2 metadata mismatch: {filename}")

    b0 = load_metrics(B0_METRICS)
    if not (
        b0.get("utterances") == EXPECTED_ROWS
        and b0.get("beam_size") == 5
        and b0.get("compute_type") == "float16"
        and Path(str(b0.get("model", ""))).resolve() == B0_MODEL.resolve()
        and Path(str(b0.get("eval_dir", ""))).resolve() == TEST_B.resolve()
    ):
        raise RuntimeError("existing B0 Test B metrics do not match the fixed final setup")

    print(
        json.dumps(
            {
                "test_b_rows": len(rows),
                "audio_missing": 0,
                "b0_existing_metrics": {
                    "cer_percent": b0["cer_percent"],
                    "wer_percent": b0["wer_percent"],
                },
                "b1_model": str(B1_MODEL),
                "decoding": {"beam_size": 5, "compute_type": "float16"},
                "rerun_b0": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print("Test B B0-vs-B1 final preflight PASSED")


def b1_metrics_complete() -> bool:
    path = B1_OUTPUT / "metrics.json"
    if not path.is_file():
        return False
    data = load_metrics(path)
    return (
        data.get("utterances") == EXPECTED_ROWS
        and data.get("start_index") == 0
        and data.get("beam_size") == 5
        and data.get("compute_type") == "float16"
        and Path(str(data.get("model", ""))).resolve() == B1_MODEL.resolve()
        and Path(str(data.get("eval_dir", ""))).resolve() == TEST_B.resolve()
    )


def main() -> int:
    args = parse_args()
    validate()
    if args.preflight_only:
        return 0

    if b1_metrics_complete():
        print("[skip] B1 cp300: complete final Test B metrics already exist", flush=True)
    else:
        run(
            [
                str(RUNTIME_PYTHON),
                str(EVALUATOR),
                "--model",
                str(B1_MODEL),
                "--eval-dir",
                str(TEST_B),
                "--output-dir",
                str(B1_OUTPUT),
            ],
            env=runtime_env(),
        )
    run([sys.executable, str(COMPARE)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
