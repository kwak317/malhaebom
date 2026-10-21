#!/usr/bin/env python3
"""Run the held-out new-persona STT test comparison across B0/B1/B2 candidates."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PREPARE = PROJECT_ROOT / "backend/scripts/prepare_stt_eval_manifest.py"
EVALUATOR = PROJECT_ROOT / "backend/scripts/evaluate_stt_ct2.py"
COMPARE = PROJECT_ROOT / "backend/scripts/compare_stt_persona_test.py"
RUNTIME_PYTHON = PROJECT_ROOT / ".venvs/stt-runtime/bin/python"

SOURCE_MANIFEST = PROJECT_ROOT / "data/stt/new-persona-119-20260921/test.jsonl"
EVAL_DIR = PROJECT_ROOT / "data/stt/persona-test"
OUTPUT_ROOT = PROJECT_ROOT / "artifacts/stt/persona-test"
MODEL_ROOT = PROJECT_ROOT / "artifacts/stt/persona-retention-models"
EXPECTED_ROWS = 1000

MODELS = {
    "b0-clean": PROJECT_ROOT
    / "artifacts/stt/whisper-medium-busan-qlora-clean-cont-lr2e-5-ct2",
    "b1-cp300": MODEL_ROOT / "b1-cp300-ct2",
    "b2-cp200": MODEL_ROOT / "b2-cp200-ct2",
    "b2-cp391": MODEL_ROOT / "b2-cp391-ct2",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--preflight-only", action="store_true")
    return p.parse_args()


def run(argv: list[str], *, env: dict[str, str] | None = None) -> None:
    print("+ " + " ".join(argv), flush=True)
    subprocess.run(argv, cwd=PROJECT_ROOT, env=env, check=True)


def runtime_env() -> dict[str, str]:
    env = os.environ.copy()
    lib_dirs = []
    site_root = PROJECT_ROOT / ".venvs/stt-train/lib"
    for py_dir in sorted(site_root.glob("python3.*")):
        for rel in ("site-packages/nvidia/cublas/lib", "site-packages/nvidia/cudnn/lib"):
            candidate = py_dir / rel
            if candidate.is_dir():
                lib_dirs.append(str(candidate))
    existing = env.get("LD_LIBRARY_PATH")
    env["LD_LIBRARY_PATH"] = ":".join(
        [*lib_dirs, *([existing] if existing else [])]
    )
    return env


def model_complete(model: Path) -> bool:
    required = [
        model / "config.json",
        model / "model.bin",
        model / "tokenizer.json",
        model / "vocabulary.json",
        model / "preprocessor_config.json",
    ]
    return all(path.is_file() for path in required)


def prepare_manifest() -> None:
    run(
        [
            sys.executable,
            str(PREPARE),
            "--input",
            str(SOURCE_MANIFEST),
            "--output-dir",
            str(EVAL_DIR),
            "--name",
            "new-persona-test",
            "--overwrite",
        ]
    )


def validate() -> None:
    if not SOURCE_MANIFEST.is_file():
        raise FileNotFoundError(SOURCE_MANIFEST)
    if not RUNTIME_PYTHON.is_file():
        raise FileNotFoundError(RUNTIME_PYTHON)
    for name, model in MODELS.items():
        if not model_complete(model):
            raise FileNotFoundError(f"{name}: incomplete CT2 model: {model}")

    manifest = EVAL_DIR / "manifest.jsonl"
    rows = [
        json.loads(line)
        for line in manifest.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != EXPECTED_ROWS:
        raise RuntimeError(f"persona test rows {len(rows)} != expected {EXPECTED_ROWS}")
    missing = [
        row["audio"]
        for row in rows
        if not (EVAL_DIR / row["audio"]).resolve().is_file()
    ]
    if missing:
        raise FileNotFoundError(f"missing eval audio: {missing[0]}")

    print(
        json.dumps(
            {
                "persona_test_rows": len(rows),
                "audio_missing": 0,
                "models": {name: str(path) for name, path in MODELS.items()},
                "runtime_python": str(RUNTIME_PYTHON),
                "beam_size": 5,
                "compute_type": "float16",
                "test_b_touched": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print("persona test preflight PASSED")


def metrics_complete(path: Path, model: Path) -> bool:
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        data.get("utterances") == EXPECTED_ROWS
        and data.get("start_index") == 0
        and data.get("beam_size") == 5
        and data.get("compute_type") == "float16"
        and Path(str(data.get("model", ""))).resolve() == model.resolve()
        and Path(str(data.get("eval_dir", ""))).resolve() == EVAL_DIR.resolve()
    )


def evaluate() -> None:
    env = runtime_env()
    for name, model in MODELS.items():
        output = OUTPUT_ROOT / name
        metrics = output / "metrics.json"
        if metrics_complete(metrics, model):
            print(f"[skip] {name}: complete persona-test metrics already exist", flush=True)
            continue
        run(
            [
                str(RUNTIME_PYTHON),
                str(EVALUATOR),
                "--model",
                str(model),
                "--eval-dir",
                str(EVAL_DIR),
                "--output-dir",
                str(output),
            ],
            env=env,
        )


def main() -> int:
    args = parse_args()
    prepare_manifest()
    validate()
    if args.preflight_only:
        return 0
    evaluate()
    run([sys.executable, str(COMPARE)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
