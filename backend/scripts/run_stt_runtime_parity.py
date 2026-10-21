#!/usr/bin/env python3
"""Compare service-default CPU/int8 with CUDA/float16 for the selected STT setup."""

from __future__ import annotations

import argparse
import gc
import json
import time
from pathlib import Path
from typing import Any

import run_stt_real_user_matrix as matrix
import run_stt_real_user_prompt_ab as prompt_ab
from stt_real_user_eval_utils import (
    devset_provenance,
    load_matching_completed_metrics,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVAL_DIR = ROOT / "local-results/stt-real-user-devset"
DEFAULT_OUTPUT_DIR = ROOT / "local-results/stt-runtime-parity"
DEFAULT_HINTS = ROOT / "configs/stt/real_user_prompt_hints.json"
EXPECTED_ROWS = 30

RUNTIMES: dict[str, dict[str, str]] = {
    "cpu-int8": {"device": "cpu", "compute_type": "int8"},
    "cuda-float16": {"device": "cuda", "compute_type": "float16"},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-dir", type=Path, default=DEFAULT_EVAL_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--hints", type=Path, default=DEFAULT_HINTS)
    parser.add_argument("--model", default=matrix.LARGE_MODEL_REPO)
    parser.add_argument("--model-revision", default=matrix.LARGE_MODEL_REVISION)
    parser.add_argument("--beam-size", type=int, default=1)
    parser.add_argument(
        "--runtimes",
        nargs="+",
        choices=tuple(RUNTIMES),
        default=list(RUNTIMES),
    )
    parser.add_argument("--max-samples", type=int)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def preflight(
    args: argparse.Namespace,
    rows: list[dict[str, Any]],
    hints: dict[str, Any],
    devset: dict[str, str | int],
) -> dict[str, Any]:
    import ctranslate2

    revision = str(args.model_revision).strip()
    if not revision:
        raise ValueError("--model-revision must not be empty")
    if args.beam_size < 1:
        raise ValueError("--beam-size must be >= 1")
    if args.max_samples is None and len(rows) != EXPECTED_ROWS:
        raise RuntimeError(f"expected {EXPECTED_ROWS} rows, got {len(rows)}")

    runtime_support: dict[str, list[str]] = {}
    for name in args.runtimes:
        config = RUNTIMES[name]
        device = config["device"]
        supported = sorted(ctranslate2.get_supported_compute_types(device))
        runtime_support[name] = supported
        if config["compute_type"] not in supported:
            raise RuntimeError(
                f"{name} compute type {config['compute_type']} is not supported: {supported}"
            )

    cuda_count = (
        ctranslate2.get_cuda_device_count()
        if hasattr(ctranslate2, "get_cuda_device_count")
        else None
    )
    if "cuda-float16" in args.runtimes and cuda_count == 0:
        raise RuntimeError("CTranslate2 reports no CUDA device")

    return {
        "ok": True,
        "rows": len(rows),
        "model": args.model,
        "model_revision": revision,
        "beam_size": args.beam_size,
        "runtimes": {name: RUNTIMES[name] for name in args.runtimes},
        "supported_compute_types": runtime_support,
        "hint_mode": "initial_prompt",
        "hint_terms": len(hints["payload"]["terms"]),
        "hints_sha256": hints["sha256"],
        "devset_provenance": devset,
        "cuda_device_count": cuda_count,
    }


def summary_row(payload: dict[str, Any]) -> dict[str, Any]:
    overall = payload["scores"]["overall"]
    core = payload["scores"]["core_excluding_stress"]["spoken_form_normalized"]
    stress_group = payload["scores"]["groups"].get("numbers-english-stress")
    stress = stress_group["spoken_form_normalized"] if stress_group else None
    terms = payload["term_metrics"]
    timing = payload["timing"]
    run = payload["run"]
    return {
        "runtime": run["runtime"],
        "device": run["device"],
        "compute_type": run["compute_type"],
        "overall_raw_cer": overall["raw"]["cer_percent"],
        "overall_raw_wer": overall["raw"]["wer_percent"],
        "overall_normalized_cer": overall["spoken_form_normalized"]["cer_percent"],
        "overall_normalized_wer": overall["spoken_form_normalized"]["wer_percent"],
        "core_normalized_cer": core["cer_percent"],
        "core_normalized_wer": core["wer_percent"],
        "stress_normalized_cer": stress["cer_percent"] if stress else None,
        "stress_normalized_wer": stress["wer_percent"] if stress else None,
        "term_recall": terms["recall_percent"],
        "false_insertions": terms["false_insertion_row_terms"],
        "aggregate_rtf": timing["aggregate_rtf"],
        "latency_p50_sec": timing["latency_p50_sec"],
        "latency_p95_sec": timing["latency_p95_sec"],
        "model_load_sec": run["model_load_sec"],
    }


def matching_completed(
    path: Path,
    *,
    runtime: str,
    args: argparse.Namespace,
    hints: dict[str, Any],
    devset: dict[str, str | int],
    row_count: int,
) -> dict[str, Any] | None:
    if not args.resume or not path.is_file():
        return None

    config = RUNTIMES[runtime]
    expected = {
        "runtime": runtime,
        "model": args.model,
        "model_revision": args.model_revision,
        "beam_size": args.beam_size,
        "device": config["device"],
        "compute_type": config["compute_type"],
        "hint_mode": "initial_prompt",
        "hints_sha256": hints["sha256"],
        "devset_provenance": devset,
        "row_count": row_count,
    }
    return load_matching_completed_metrics(
        path,
        expected_run=expected,
        row_count=row_count,
        summary_validator=summary_row,
    )


def run_runtime(
    model: Any,
    *,
    runtime: str,
    model_load_sec: float,
    rows: list[dict[str, Any]],
    args: argparse.Namespace,
    hints: dict[str, Any],
    devset: dict[str, str | int],
) -> dict[str, Any]:
    config = RUNTIMES[runtime]
    runtime_dir = args.output_dir / runtime
    runtime_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = runtime_dir / "metrics.json"

    completed = matching_completed(
        metrics_path,
        runtime=runtime,
        args=args,
        hints=hints,
        devset=devset,
        row_count=len(rows),
    )
    if completed is not None:
        print(f"[resume] {runtime}", flush=True)
        return completed

    records: list[dict[str, Any]] = []
    for position, row in enumerate(rows, start=1):
        started = time.perf_counter()
        segments, info = model.transcribe(
            str(args.eval_dir / row["audio"]),
            language="ko",
            task="transcribe",
            beam_size=args.beam_size,
            temperature=0.0,
            word_timestamps=True,
            vad_filter=False,
            condition_on_previous_text=False,
            initial_prompt=hints["initial_prompt"],
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
            f"[{runtime}] {position}/{len(rows)} {row['id']} "
            f"{elapsed:.3f}s rtf={record['rtf'] if record['rtf'] is not None else 'n/a'}",
            flush=True,
        )

    payload = {
        "schema_version": 2,
        "run": {
            "runtime": runtime,
            "model": args.model,
            "model_revision": args.model_revision,
            "beam_size": args.beam_size,
            "device": config["device"],
            "compute_type": config["compute_type"],
            "hint_mode": "initial_prompt",
            "hints_sha256": hints["sha256"],
            "devset_provenance": devset,
            "row_count": len(rows),
            "model_load_sec": model_load_sec,
        },
        "scores": matrix.score_groups(records),
        "term_metrics": prompt_ab.term_metrics(records, hints["payload"]),
        "timing": matrix.timing_metrics(records),
    }
    (runtime_dir / "predictions.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    metrics_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def render_markdown(rows: list[dict[str, Any]]) -> str:
    def fmt(value: float | int | None, digits: int = 2) -> str:
        return "-" if value is None else f"{float(value):.{digits}f}"

    lines = [
        "# STT service-runtime parity",
        "",
        "| Runtime | Core norm CER | Core norm WER | Stress norm CER | Stress norm WER | Hint recall | False insertions | RTF | p50 sec | p95 sec | Load sec |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['runtime']} | {fmt(row['core_normalized_cer'])}% | "
            f"{fmt(row['core_normalized_wer'])}% | {fmt(row['stress_normalized_cer'])}% | "
            f"{fmt(row['stress_normalized_wer'])}% | {fmt(row['term_recall'])}% | "
            f"{row['false_insertions']} | {fmt(row['aggregate_rtf'], 3)} | "
            f"{fmt(row['latency_p50_sec'], 3)} | {fmt(row['latency_p95_sec'], 3)} | "
            f"{fmt(row['model_load_sec'], 3)} |"
        )
    lines += [
        "",
        "> Only runtime device/compute type changes. Model revision, beam, devset and diagnostic initial_prompt are fixed.",
        "> This is a dev/diagnostic deployment-parity check, not final acceptance evidence.",
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
    args.hints = args.hints.expanduser().resolve()

    if "cuda-float16" in args.runtimes:
        matrix.ensure_cuda_library_path("cuda")

    rows = matrix.load_rows(args.eval_dir, args.max_samples)
    hints = prompt_ab.load_hints(args.hints)
    devset = devset_provenance(args.eval_dir, rows)
    print(json.dumps(preflight(args, rows, hints, devset), ensure_ascii=False, indent=2))
    if args.preflight_only:
        return 0

    from faster_whisper import WhisperModel

    args.output_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for runtime in args.runtimes:
        config = RUNTIMES[runtime]
        metrics_path = args.output_dir / runtime / "metrics.json"
        completed = matching_completed(
            metrics_path,
            runtime=runtime,
            args=args,
            hints=hints,
            devset=devset,
            row_count=len(rows),
        )
        if completed is not None:
            results.append(completed)
            continue

        load_started = time.perf_counter()
        model = WhisperModel(
            args.model,
            device=config["device"],
            compute_type=config["compute_type"],
            revision=args.model_revision,
        )
        model_load_sec = time.perf_counter() - load_started
        print(f"[loaded] {runtime} in {model_load_sec:.3f}s", flush=True)
        try:
            results.append(
                run_runtime(
                    model,
                    runtime=runtime,
                    model_load_sec=model_load_sec,
                    rows=rows,
                    args=args,
                    hints=hints,
                    devset=devset,
                )
            )
        finally:
            cleanup_model(model)

    summary_rows = [summary_row(payload) for payload in results]
    order = {name: index for index, name in enumerate(RUNTIMES)}
    summary_rows.sort(key=lambda row: order[row["runtime"]])
    summary = {
        "schema_version": 1,
        "rows": summary_rows,
        "model": args.model,
        "model_revision": args.model_revision,
        "beam_size": args.beam_size,
        "hints_sha256": hints["sha256"],
        "devset_provenance": devset,
        "note": "Dev/diagnostic deployment-parity check only.",
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown = render_markdown(summary_rows)
    (args.output_dir / "SUMMARY.md").write_text(markdown, encoding="utf-8")
    print(markdown, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
