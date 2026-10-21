#!/usr/bin/env python3
"""Run the frozen real-user STT dev set across model x beam configurations."""

from __future__ import annotations

import argparse
import gc
import importlib.metadata
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from stt_real_user_eval_utils import (
    ct2_model_fingerprint,
    devset_provenance,
    load_matching_completed_metrics,
    load_rows,
    model_complete,
    score_groups,
    timing_metrics,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVAL_DIR = ROOT / "local-results/stt-real-user-devset"
DEFAULT_OUTPUT_DIR = ROOT / "local-results/stt-real-user-matrix"
DEFAULT_B0 = ROOT / "artifacts/stt/whisper-medium-busan-qlora-clean-cont-lr2e-5-ct2"
DEFAULT_C2 = ROOT / "artifacts/stt/71592-retention-models/c2-71592-replay20-ct2"
MODEL_ORDER = ("large-v3-turbo", "b0", "c2")
LARGE_MODEL_REPO = "mobiuslabsgmbh/faster-whisper-large-v3-turbo"
LARGE_MODEL_REVISION = "0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf"
EXPECTED_ROWS = 30
CUDA_REEXEC_MARKER = "STT_REAL_USER_MATRIX_CUDA_LIBS_READY"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-dir", type=Path, default=DEFAULT_EVAL_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--models",
        nargs="+",
        choices=MODEL_ORDER,
        default=list(MODEL_ORDER),
    )
    parser.add_argument("--large-model", default=LARGE_MODEL_REPO)
    parser.add_argument("--large-model-revision", default=LARGE_MODEL_REVISION)
    parser.add_argument("--b0-model", type=Path, default=DEFAULT_B0)
    parser.add_argument("--c2-model", type=Path, default=DEFAULT_C2)
    parser.add_argument("--beam-sizes", nargs="+", type=int, default=[1, 3, 5])
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--compute-type", default="float16")
    parser.add_argument("--max-samples", type=int)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse completed matching configuration outputs.",
    )
    return parser.parse_args()


def cuda_library_paths() -> list[str]:
    paths: list[str] = []
    site_root = ROOT / ".venvs/stt-train/lib"
    for py_dir in sorted(site_root.glob("python3.*")):
        for relative in (
            "site-packages/nvidia/cublas/lib",
            "site-packages/nvidia/cudnn/lib",
        ):
            candidate = py_dir / relative
            if candidate.is_dir():
                paths.append(str(candidate))
    return paths


def ensure_cuda_library_path(device: str) -> None:
    if device != "cuda" or os.environ.get(CUDA_REEXEC_MARKER) == "1":
        return

    required = cuda_library_paths()
    if not required:
        return

    existing = [item for item in os.environ.get("LD_LIBRARY_PATH", "").split(":") if item]
    missing = [item for item in required if item not in existing]
    if not missing:
        return

    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = ":".join([*required, *existing])
    env[CUDA_REEXEC_MARKER] = "1"
    os.execve(sys.executable, [sys.executable, *sys.argv], env)


def model_specs(args: argparse.Namespace) -> dict[str, str]:
    return {
        "large-v3-turbo": args.large_model,
        "b0": str(args.b0_model.expanduser().resolve()),
        "c2": str(args.c2_model.expanduser().resolve()),
    }


def model_provenance(args: argparse.Namespace) -> dict[str, dict[str, str]]:
    provenance: dict[str, dict[str, str]] = {}
    if "large-v3-turbo" in args.models:
        revision = str(args.large_model_revision).strip()
        if not revision:
            raise ValueError("--large-model-revision must not be empty")
        provenance["large-v3-turbo"] = {
            "kind": "huggingface",
            "repo_id": str(args.large_model),
            "revision": revision,
        }
    if "b0" in args.models:
        path = args.b0_model.expanduser().resolve()
        provenance["b0"] = {
            "kind": "local_ct2",
            "path": str(path),
            "fingerprint_sha256": ct2_model_fingerprint(path),
        }
    if "c2" in args.models:
        path = args.c2_model.expanduser().resolve()
        provenance["c2"] = {
            "kind": "local_ct2",
            "path": str(path),
            "fingerprint_sha256": ct2_model_fingerprint(path),
        }
    return provenance


def preflight(
    args: argparse.Namespace,
    rows: list[dict[str, Any]],
    provenance: dict[str, dict[str, str]],
) -> dict[str, Any]:
    if any(beam < 1 for beam in args.beam_sizes):
        raise ValueError("all beam sizes must be >= 1")

    specs = model_specs(args)
    for name, path in (("b0", args.b0_model), ("c2", args.c2_model)):
        if name in args.models and not model_complete(path.expanduser().resolve()):
            raise FileNotFoundError(f"incomplete {name} CT2 model: {path}")

    import ctranslate2
    import faster_whisper  # noqa: F401

    payload = {
        "ok": True,
        "rows": len(rows),
        "expected_full_rows": EXPECTED_ROWS,
        "models": {name: specs[name] for name in args.models},
        "model_provenance": provenance,
        "beam_sizes": args.beam_sizes,
        "device": args.device,
        "compute_type": args.compute_type,
        "word_timestamps": True,
        "condition_on_previous_text": False,
        "vad_filter": False,
        "temperature": 0.0,
        "python": sys.version.split()[0],
        "faster_whisper": importlib.metadata.version("faster-whisper"),
        "ctranslate2": importlib.metadata.version("ctranslate2"),
        "cuda_device_count": (
            ctranslate2.get_cuda_device_count()
            if hasattr(ctranslate2, "get_cuda_device_count")
            else None
        ),
        "large_model_note": (
            "large-v3-turbo is loaded with the recorded immutable Hugging Face revision; "
            "the first run may download that snapshot if it is not cached."
        ),
    }
    if args.max_samples is None and len(rows) != EXPECTED_ROWS:
        raise RuntimeError(f"expected {EXPECTED_ROWS} rows, got {len(rows)}")
    if args.device == "cuda" and payload["cuda_device_count"] == 0:
        raise RuntimeError("CTranslate2 reports no CUDA device")
    return payload


def matching_completed_metrics(
    path: Path,
    *,
    model: str,
    model_source: str,
    model_provenance: dict[str, str],
    beam_size: int,
    args: argparse.Namespace,
    row_count: int,
    devset: dict[str, str | int],
) -> dict[str, Any] | None:
    if not args.resume or not path.is_file():
        return None
    expected = {
        "model": model,
        "model_source": model_source,
        "beam_size": beam_size,
        "device": args.device,
        "compute_type": args.compute_type,
        "row_count": row_count,
        "word_timestamps": True,
        "model_provenance": model_provenance,
        "devset_provenance": devset,
    }
    return load_matching_completed_metrics(
        path,
        expected_run=expected,
        row_count=row_count,
        summary_validator=summary_row,
    )


def run_configuration(
    model: Any,
    *,
    model_name: str,
    model_source: str,
    model_provenance: dict[str, str],
    beam_size: int,
    rows: list[dict[str, Any]],
    eval_dir: Path,
    output_dir: Path,
    args: argparse.Namespace,
    model_load_sec: float,
    devset: dict[str, str | int],
) -> dict[str, Any]:
    config_dir = output_dir / model_name / f"beam-{beam_size}"
    config_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = config_dir / "metrics.json"

    completed = matching_completed_metrics(
        metrics_path,
        model=model_name,
        model_source=model_source,
        model_provenance=model_provenance,
        beam_size=beam_size,
        args=args,
        row_count=len(rows),
        devset=devset,
    )
    if completed is not None:
        print(f"[resume] {model_name} beam={beam_size}", flush=True)
        return completed

    records: list[dict[str, Any]] = []
    for position, row in enumerate(rows, start=1):
        started = time.perf_counter()
        segments, info = model.transcribe(
            str(eval_dir / row["audio"]),
            language="ko",
            task="transcribe",
            beam_size=beam_size,
            temperature=0.0,
            word_timestamps=True,
            vad_filter=False,
            condition_on_previous_text=False,
        )
        prediction = " ".join(segment.text.strip() for segment in segments).strip()
        elapsed = time.perf_counter() - started
        duration = float(getattr(info, "duration", 0.0) or 0.0)

        record = {
            **row,
            "prediction": prediction,
            "audio_duration_sec": duration,
            "processing_time_sec": elapsed,
            "rtf": elapsed / duration if duration > 0 else None,
        }
        records.append(record)
        print(
            f"[{model_name} beam={beam_size}] "
            f"{position}/{len(rows)} {row['id']} "
            f"{elapsed:.3f}s rtf={record['rtf'] if record['rtf'] is not None else 'n/a'}",
            flush=True,
        )

    payload = {
        "schema_version": 2,
        "run": {
            "model": model_name,
            "model_source": model_source,
            "beam_size": beam_size,
            "device": args.device,
            "compute_type": args.compute_type,
            "row_count": len(rows),
            "word_timestamps": True,
            "model_provenance": model_provenance,
            "devset_provenance": devset,
            "temperature": 0.0,
            "condition_on_previous_text": False,
            "vad_filter": False,
            "model_load_sec": model_load_sec,
        },
        "scores": score_groups(records),
        "timing": timing_metrics(records),
    }
    (config_dir / "predictions.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    metrics_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def summary_row(payload: dict[str, Any]) -> dict[str, Any]:
    run = payload["run"]
    overall = payload["scores"]["overall"]
    core = payload["scores"]["core_excluding_stress"]
    stress = payload["scores"]["groups"].get("numbers-english-stress")
    timing = payload["timing"]
    return {
        "model": run["model"],
        "beam_size": run["beam_size"],
        "raw_cer": overall["raw"]["cer_percent"],
        "raw_wer": overall["raw"]["wer_percent"],
        "normalized_cer": overall["spoken_form_normalized"]["cer_percent"],
        "normalized_wer": overall["spoken_form_normalized"]["wer_percent"],
        "core_normalized_cer": (
            core["spoken_form_normalized"]["cer_percent"] if core else None
        ),
        "core_normalized_wer": (
            core["spoken_form_normalized"]["wer_percent"] if core else None
        ),
        "stress_normalized_cer": (
            stress["spoken_form_normalized"]["cer_percent"] if stress else None
        ),
        "stress_normalized_wer": (
            stress["spoken_form_normalized"]["wer_percent"] if stress else None
        ),
        "aggregate_rtf": timing["aggregate_rtf"],
        "latency_p50_sec": timing["latency_p50_sec"],
        "latency_p95_sec": timing["latency_p95_sec"],
        "model_load_sec": run["model_load_sec"],
    }


def render_markdown(rows: list[dict[str, Any]], failures: list[dict[str, str]]) -> str:
    lines = [
        "# STT real-user model × beam matrix",
        "",
        "| Model | Beam | Core norm CER | Core norm WER | All raw CER | All raw WER | RTF | p50 sec | p95 sec |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    def fmt(value: Any, digits: int = 2) -> str:
        return "-" if value is None else f"{float(value):.{digits}f}"

    for row in rows:
        lines.append(
            "| {model} | {beam} | {core_cer}% | {core_wer}% | {raw_cer}% | "
            "{raw_wer}% | {rtf} | {p50} | {p95} |".format(
                model=row["model"],
                beam=row["beam_size"],
                core_cer=fmt(row["core_normalized_cer"]),
                core_wer=fmt(row["core_normalized_wer"]),
                raw_cer=fmt(row["raw_cer"]),
                raw_wer=fmt(row["raw_wer"]),
                rtf=fmt(row["aggregate_rtf"], 3),
                p50=fmt(row["latency_p50_sec"], 3),
                p95=fmt(row["latency_p95_sec"], 3),
            )
        )

    if failures:
        lines += ["", "## Failures", ""]
        for failure in failures:
            lines.append(f"- {failure['model']}: {failure['error']}")

    lines += [
        "",
        "> The frozen 30 recordings are a dev/diagnostic set, not a final acceptance set.",
        "> Model load/download time is recorded separately and excluded from per-utterance latency.",
    ]
    return "\n".join(lines) + "\n"


def cleanup_model(model: Any) -> None:
    backend = getattr(model, "model", None)
    unload = getattr(backend, "unload_model", None)
    if callable(unload):
        unload()
    del model
    gc.collect()


def main() -> int:
    args = parse_args()
    args.eval_dir = args.eval_dir.expanduser().resolve()
    args.output_dir = args.output_dir.expanduser().resolve()
    args.b0_model = args.b0_model.expanduser().resolve()
    args.c2_model = args.c2_model.expanduser().resolve()

    ensure_cuda_library_path(args.device)
    rows = load_rows(args.eval_dir, args.max_samples)
    devset = devset_provenance(args.eval_dir, rows)
    provenance = model_provenance(args)
    preflight_payload = preflight(args, rows, provenance)
    preflight_payload["devset_provenance"] = devset
    print(json.dumps(preflight_payload, ensure_ascii=False, indent=2))
    if args.preflight_only:
        return 0

    from faster_whisper import WhisperModel

    specs = model_specs(args)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary_rows: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    for model_name in args.models:
        source = specs[model_name]
        pending_beams = []
        for beam_size in args.beam_sizes:
            metrics_path = args.output_dir / model_name / f"beam-{beam_size}" / "metrics.json"
            completed = matching_completed_metrics(
                metrics_path,
                model=model_name,
                model_source=source,
                model_provenance=provenance[model_name],
                beam_size=beam_size,
                args=args,
                row_count=len(rows),
                devset=devset,
            )
            if completed is not None:
                summary_rows.append(summary_row(completed))
            else:
                pending_beams.append(beam_size)

        if not pending_beams:
            continue

        try:
            load_started = time.perf_counter()
            model = WhisperModel(
                source,
                device=args.device,
                compute_type=args.compute_type,
                revision=(
                    args.large_model_revision
                    if model_name == "large-v3-turbo"
                    else None
                ),
            )
            model_load_sec = time.perf_counter() - load_started
            print(f"[loaded] {model_name} in {model_load_sec:.3f}s", flush=True)

            for beam_size in pending_beams:
                payload = run_configuration(
                    model,
                    model_name=model_name,
                    model_source=source,
                    model_provenance=provenance[model_name],
                    beam_size=beam_size,
                    rows=rows,
                    eval_dir=args.eval_dir,
                    output_dir=args.output_dir,
                    args=args,
                    model_load_sec=model_load_sec,
                    devset=devset,
                )
                summary_rows.append(summary_row(payload))
        except Exception as error:
            failures.append({"model": model_name, "error": repr(error)})
            print(f"[failed] {model_name}: {error!r}", file=sys.stderr, flush=True)
        finally:
            if "model" in locals():
                cleanup_model(model)
                del model

    order = {name: index for index, name in enumerate(MODEL_ORDER)}
    summary_rows.sort(key=lambda row: (order[row["model"]], row["beam_size"]))
    summary = {
        "schema_version": 1,
        "rows": summary_rows,
        "failures": failures,
        "devset": str(args.eval_dir),
        "note": "This is a dev/diagnostic matrix; do not use it as final acceptance evidence.",
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "SUMMARY.md").write_text(
        render_markdown(summary_rows, failures),
        encoding="utf-8",
    )
    print(render_markdown(summary_rows, failures), end="")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
