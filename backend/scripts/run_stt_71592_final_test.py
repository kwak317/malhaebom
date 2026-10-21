#!/usr/bin/env python3
"""Run the final selected C2 model on the sealed AI Hub 71592 test split."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREPARE = ROOT / "backend/scripts/prepare_stt_eval_manifest.py"
EVALUATOR = ROOT / "backend/scripts/evaluate_stt_ct2.py"
RUNTIME_PYTHON = ROOT / ".venvs/stt-runtime/bin/python"

SOURCE_MANIFEST = ROOT / "data/stt/aihub71592-domain-20260922/test.jsonl"
EVAL_DIR = ROOT / "data/stt/71592-final-test"
OUTPUT_DIR = ROOT / "artifacts/stt/71592-final-test/c2-replay20"
MODEL = ROOT / "artifacts/stt/71592-retention-models/c2-71592-replay20-ct2"
SELECTION_ARTIFACT = ROOT / "configs/stt/71592_c2_selection.json"
SELECTED_MODEL_ID = "c2-71592-replay20"
SELECTION_CANDIDATES = {"c1-71592-only", "c2-71592-replay20"}
EXPECTED_ROWS = 1233

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--preflight-only", action="store_true")
    return p.parse_args()


def run(argv: list[str], *, env: dict[str, str] | None = None) -> None:
    print("+ " + " ".join(argv), flush=True)
    subprocess.run(argv, cwd=ROOT, env=env, check=True)


def runtime_env() -> dict[str, str]:
    env = os.environ.copy()
    lib_dirs: list[str] = []
    site_root = ROOT / ".venvs/stt-train/lib"
    for py_dir in sorted(site_root.glob("python3.*")):
        for rel in (
            "site-packages/nvidia/cublas/lib",
            "site-packages/nvidia/cudnn/lib",
        ):
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


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def model_fingerprint(model: Path) -> str:
    if not model_complete(model):
        raise FileNotFoundError(f"incomplete selected C2 CT2 model: {model}")
    digest = hashlib.sha256()
    for path in sorted(
        (
            model / "config.json",
            model / "model.bin",
            model / "tokenizer.json",
            model / "vocabulary.json",
            model / "preprocessor_config.json",
        ),
        key=lambda item: item.name,
    ):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def repo_path(root: Path, value: object, label: str) -> Path:
    root = root.resolve()
    path = (root / str(value)).resolve()
    if path == root or root not in path.parents:
        raise ValueError(f"{label} must stay under repository root: {path}")
    return path


def validate_selection_artifact(
    artifact_path: Path = SELECTION_ARTIFACT,
    *,
    root: Path = ROOT,
    expected_model: Path = MODEL,
) -> dict:
    if not artifact_path.is_file():
        raise FileNotFoundError(
            f"frozen C2 selection artifact is required before final-test access: {artifact_path}"
        )
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1 or payload.get("selection_is_frozen") is not True:
        raise RuntimeError("selection artifact is not a frozen schema_version=1 record")

    selected = payload.get("selected_model")
    if not isinstance(selected, dict) or selected.get("id") != SELECTED_MODEL_ID:
        raise RuntimeError("selection artifact does not freeze the expected C2 model identity")
    ct2_path = repo_path(root, selected.get("ct2_path"), "selected_model.ct2_path")
    if ct2_path != expected_model.resolve():
        raise RuntimeError(f"selection artifact CT2 path mismatch: {ct2_path}")
    expected_fingerprint = str(selected.get("ct2_fingerprint", ""))
    if not expected_fingerprint or model_fingerprint(ct2_path) != expected_fingerprint:
        raise RuntimeError("selected C2 CT2 model fingerprint mismatch")

    adapter_path = repo_path(root, selected.get("adapter_path"), "selected_model.adapter_path")
    if not adapter_path.is_file():
        raise FileNotFoundError(adapter_path)
    if sha256_file(adapter_path) != selected.get("adapter_sha256"):
        raise RuntimeError("selected C2 adapter fingerprint mismatch")

    validation = payload.get("validation_evidence")
    if not isinstance(validation, list):
        raise RuntimeError("selection artifact is missing validation evidence")
    seen: set[str] = set()
    for item in validation:
        if not isinstance(item, dict):
            raise RuntimeError("invalid validation evidence entry")
        candidate = str(item.get("candidate", ""))
        seen.add(candidate)
        path = repo_path(root, item.get("path"), f"validation_evidence[{candidate}]")
        if not path.is_file() or sha256_file(path) != item.get("sha256"):
            raise RuntimeError(f"validation evidence fingerprint mismatch: {candidate}")
    if seen != SELECTION_CANDIDATES:
        raise RuntimeError(f"selection evidence candidates mismatch: {sorted(seen)}")

    retention = payload.get("retention_evidence")
    if not isinstance(retention, dict):
        raise RuntimeError("selection artifact is missing retention evidence")
    retention_path = repo_path(root, retention.get("path"), "retention_evidence.path")
    if not retention_path.is_file() or sha256_file(retention_path) != retention.get("sha256"):
        raise RuntimeError("retention evidence fingerprint mismatch")
    return payload


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
            "aihub71592-final-test",
            "--overwrite",
        ]
    )


def validate(selection: dict) -> None:
    if not SOURCE_MANIFEST.is_file():
        raise FileNotFoundError(SOURCE_MANIFEST)
    if not RUNTIME_PYTHON.is_file():
        raise FileNotFoundError(RUNTIME_PYTHON)
    if not model_complete(MODEL):
        raise FileNotFoundError(f"incomplete selected C2 CT2 model: {MODEL}")

    manifest = EVAL_DIR / "manifest.jsonl"
    rows = [
        json.loads(line)
        for line in manifest.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != EXPECTED_ROWS:
        raise RuntimeError(
            f"71592 final test rows {len(rows)} != expected {EXPECTED_ROWS}"
        )
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
                "final_test_rows": len(rows),
                "audio_missing": 0,
                "selected_model": selection["selected_model"]["id"],
                "model": str(MODEL),
                "selection_artifact": str(SELECTION_ARTIFACT),
                "runtime_python": str(RUNTIME_PYTHON),
                "beam_size": 5,
                "compute_type": "float16",
                "selection_is_frozen": selection["selection_is_frozen"],
                "post_test_policy": (
                    "Report this result as final 71592 test evidence. "
                    "Do not use it to retune replay ratio, checkpoint, or hyperparameters."
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print("71592 final test preflight PASSED")


def metrics_complete() -> bool:
    path = OUTPUT_DIR / "metrics.json"
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
        and Path(str(data.get("model", ""))).resolve() == MODEL.resolve()
        and Path(str(data.get("eval_dir", ""))).resolve()
        == EVAL_DIR.resolve()
    )


def evaluate() -> None:
    if metrics_complete():
        print("[skip] complete final test metrics already exist", flush=True)
        return
    run(
        [
            str(RUNTIME_PYTHON),
            str(EVALUATOR),
            "--model",
            str(MODEL),
            "--eval-dir",
            str(EVAL_DIR),
            "--output-dir",
            str(OUTPUT_DIR),
        ],
        env=runtime_env(),
    )


def main() -> int:
    args = parse_args()
    selection = validate_selection_artifact()
    prepare_manifest()
    validate(selection)
    if args.preflight_only:
        return 0
    evaluate()
    metrics = json.loads(
        (OUTPUT_DIR / "metrics.json").read_text(encoding="utf-8")
    )
    print(
        json.dumps(
            {
                "model": SELECTED_MODEL_ID,
                "utterances": metrics.get("utterances"),
                "cer_percent": metrics.get("cer_percent"),
                "wer_percent": metrics.get("wer_percent"),
                "metrics_path": str(OUTPUT_DIR / "metrics.json"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
