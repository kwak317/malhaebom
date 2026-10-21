#!/usr/bin/env python3
"""Compare no hints vs initial_prompt vs hotwords on the frozen real-user STT dev set."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import unicodedata
from pathlib import Path
from typing import Any

import run_stt_real_user_matrix as matrix
from stt_real_user_eval_utils import devset_provenance

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVAL_DIR = ROOT / "local-results/stt-real-user-devset"
DEFAULT_OUTPUT_DIR = ROOT / "local-results/stt-real-user-prompt-ab"
DEFAULT_HINTS = ROOT / "configs/stt/real_user_prompt_hints.json"
MODES = ("none", "initial_prompt", "hotwords")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-dir", type=Path, default=DEFAULT_EVAL_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--hints", type=Path, default=DEFAULT_HINTS)
    parser.add_argument("--model", default=matrix.LARGE_MODEL_REPO)
    parser.add_argument("--model-revision", default=matrix.LARGE_MODEL_REVISION)
    parser.add_argument("--beam-size", type=int, default=1)
    parser.add_argument("--modes", nargs="+", choices=MODES, default=list(MODES))
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--compute-type", default="float16")
    parser.add_argument("--max-samples", type=int)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_hints(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    terms = payload.get("terms")
    if not isinstance(terms, list) or not terms:
        raise ValueError("hints config must contain a non-empty terms list")

    canonical_terms: list[str] = []
    for item in terms:
        canonical = str(item.get("canonical", "")).strip()
        aliases = item.get("aliases")
        if not canonical or not isinstance(aliases, list) or not aliases:
            raise ValueError(f"invalid hint term: {item!r}")
        canonical_terms.append(canonical)

    prefix = str(payload.get("initial_prompt_prefix", "")).strip()
    if not prefix:
        raise ValueError("initial_prompt_prefix is required")

    return {
        "payload": payload,
        "sha256": sha256_file(path),
        "initial_prompt": f"{prefix} {', '.join(canonical_terms)}.",
        "hotwords": ", ".join(canonical_terms),
    }


def alias_regex(alias: str) -> re.Pattern[str]:
    normalized = unicodedata.normalize("NFKC", alias).lower().strip()
    parts = re.findall(r"[a-z0-9]+", normalized)
    if not parts:
        return re.compile(r"(?!x)x")
    body = r"[\s_\-]*".join(re.escape(part) for part in parts)
    return re.compile(rf"(?<![a-z0-9]){body}(?![a-z0-9])", re.IGNORECASE)


def text_has_alias(text: str, aliases: list[str]) -> bool:
    normalized = unicodedata.normalize("NFKC", text)
    return any(alias_regex(alias).search(normalized) for alias in aliases)


def term_metrics(records: list[dict[str, Any]], hints_payload: dict[str, Any]) -> dict[str, Any]:
    targets = hits = false_insertions = 0
    misses: list[dict[str, str]] = []
    false_examples: list[dict[str, str]] = []

    for row in records:
        for term in hints_payload["terms"]:
            canonical = str(term["canonical"])
            aliases = [str(alias) for alias in term["aliases"]]
            in_reference = text_has_alias(row["reference"], aliases)
            in_prediction = text_has_alias(row["prediction"], aliases)

            if in_reference:
                targets += 1
                if in_prediction:
                    hits += 1
                else:
                    misses.append({"id": row["id"], "term": canonical})
            elif in_prediction:
                false_insertions += 1
                false_examples.append({"id": row["id"], "term": canonical})

    return {
        "target_row_terms": targets,
        "hit_row_terms": hits,
        "recall_percent": 100 * hits / targets if targets else None,
        "false_insertion_row_terms": false_insertions,
        "misses": misses,
        "false_insertions": false_examples,
    }


def mode_kwargs(mode: str, hints: dict[str, Any]) -> dict[str, str]:
    if mode == "none":
        return {}
    if mode == "initial_prompt":
        return {"initial_prompt": hints["initial_prompt"]}
    if mode == "hotwords":
        return {"hotwords": hints["hotwords"]}
    raise ValueError(mode)


def matching_completed(
    path: Path,
    *,
    mode: str,
    args: argparse.Namespace,
    hints_sha256: str,
    devset: dict[str, str | int],
    row_count: int,
) -> dict[str, Any] | None:
    if not args.resume or not path.is_file():
        return None
    expected = {
        "mode": mode,
        "model": args.model,
        "model_revision": args.model_revision,
        "beam_size": args.beam_size,
        "device": args.device,
        "compute_type": args.compute_type,
        "hints_sha256": hints_sha256,
        "devset_provenance": devset,
        "row_count": row_count,
    }
    return matrix.load_matching_completed_metrics(
        path,
        expected_run=expected,
        row_count=row_count,
        summary_validator=summary_row,
    )


def preflight(
    args: argparse.Namespace,
    rows: list[dict[str, Any]],
    hints: dict[str, Any],
    devset: dict[str, str | int],
) -> dict[str, Any]:
    import ctranslate2
    import faster_whisper

    signature = __import__("inspect").signature(faster_whisper.WhisperModel.transcribe)
    for parameter in ("initial_prompt", "hotwords"):
        if parameter not in signature.parameters:
            raise RuntimeError(f"faster-whisper transcribe lacks {parameter}")

    cuda_count = (
        ctranslate2.get_cuda_device_count()
        if hasattr(ctranslate2, "get_cuda_device_count")
        else None
    )
    if args.device == "cuda" and cuda_count == 0:
        raise RuntimeError("CTranslate2 reports no CUDA device")

    return {
        "ok": True,
        "rows": len(rows),
        "model": args.model,
        "model_revision": args.model_revision,
        "beam_size": args.beam_size,
        "modes": args.modes,
        "device": args.device,
        "compute_type": args.compute_type,
        "hint_terms": len(hints["payload"]["terms"]),
        "hints_sha256": hints["sha256"],
        "devset_provenance": devset,
        "initial_prompt": hints["initial_prompt"],
        "hotwords": hints["hotwords"],
        "cuda_device_count": cuda_count,
    }


def run_mode(
    model: Any,
    *,
    mode: str,
    rows: list[dict[str, Any]],
    args: argparse.Namespace,
    hints: dict[str, Any],
    devset: dict[str, str | int],
) -> dict[str, Any]:
    mode_dir = args.output_dir / mode
    mode_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = mode_dir / "metrics.json"

    completed = matching_completed(
        metrics_path,
        mode=mode,
        args=args,
        hints_sha256=hints["sha256"],
        devset=devset,
        row_count=len(rows),
    )
    if completed is not None:
        print(f"[resume] {mode}", flush=True)
        return completed

    records: list[dict[str, Any]] = []
    extra = mode_kwargs(mode, hints)
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
            **extra,
        )
        prediction = " ".join(segment.text.strip() for segment in segments).strip()
        elapsed = time.perf_counter() - started
        duration = float(getattr(info, "duration", 0.0) or 0.0)
        records.append(
            {
                **row,
                "prediction": prediction,
                "audio_duration_sec": duration,
                "processing_time_sec": elapsed,
                "rtf": elapsed / duration if duration > 0 else None,
            }
        )
        print(f"[{mode}] {position}/{len(rows)} {row['id']} {elapsed:.3f}s", flush=True)

    payload = {
        "schema_version": 2,
        "run": {
            "mode": mode,
            "model": args.model,
            "model_revision": args.model_revision,
            "beam_size": args.beam_size,
            "device": args.device,
            "compute_type": args.compute_type,
            "hints_sha256": hints["sha256"],
            "devset_provenance": devset,
            "row_count": len(rows),
        },
        "scores": matrix.score_groups(records),
        "term_metrics": term_metrics(records, hints["payload"]),
        "timing": matrix.timing_metrics(records),
    }
    (mode_dir / "predictions.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    metrics_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def summary_row(payload: dict[str, Any]) -> dict[str, Any]:
    core = payload["scores"]["core_excluding_stress"]["spoken_form_normalized"]
    stress_group = payload["scores"]["groups"].get("numbers-english-stress")
    stress = stress_group["spoken_form_normalized"] if stress_group else None
    terms = payload["term_metrics"]
    timing = payload["timing"]
    return {
        "mode": payload["run"]["mode"],
        "core_cer": core["cer_percent"],
        "core_wer": core["wer_percent"],
        "stress_cer": stress["cer_percent"] if stress else None,
        "stress_wer": stress["wer_percent"] if stress else None,
        "term_recall": terms["recall_percent"],
        "false_insertions": terms["false_insertion_row_terms"],
        "rtf": timing["aggregate_rtf"],
        "p50_sec": timing["latency_p50_sec"],
        "p95_sec": timing["latency_p95_sec"],
    }


def render_markdown(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# STT real-user prompt/hotwords A/B",
        "",
        "| Mode | Core norm CER | Core norm WER | Stress norm CER | Stress norm WER | Hint-term recall | False insertions | RTF | p50 sec |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    def fmt(value: float | int | None, digits: int = 2) -> str:
        return "-" if value is None else f"{float(value):.{digits}f}"

    for row in rows:
        lines.append(
            f"| {row['mode']} | {fmt(row['core_cer'])}% | {fmt(row['core_wer'])}% | "
            f"{fmt(row['stress_cer'])}% | {fmt(row['stress_wer'])}% | "
            f"{fmt(row['term_recall'])}% | {row['false_insertions']} | "
            f"{fmt(row['rtf'], 3)} | {fmt(row['p50_sec'], 3)} |"
        )
    lines += [
        "",
        "> This is a dev/diagnostic A/B. The hint set is fixed before the run and is not final acceptance evidence.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    args.eval_dir = args.eval_dir.expanduser().resolve()
    args.output_dir = args.output_dir.expanduser().resolve()
    args.hints = args.hints.expanduser().resolve()

    matrix.ensure_cuda_library_path(args.device)
    rows = matrix.load_rows(args.eval_dir, args.max_samples)
    hints = load_hints(args.hints)
    devset = devset_provenance(args.eval_dir, rows)
    print(json.dumps(preflight(args, rows, hints, devset), ensure_ascii=False, indent=2))
    if args.preflight_only:
        return 0

    from faster_whisper import WhisperModel

    args.output_dir.mkdir(parents=True, exist_ok=True)
    model = WhisperModel(
        args.model,
        device=args.device,
        compute_type=args.compute_type,
        revision=args.model_revision,
    )
    results = [
        run_mode(
            model,
            mode=mode,
            rows=rows,
            args=args,
            hints=hints,
            devset=devset,
        )
        for mode in args.modes
    ]
    summary_rows = [summary_row(payload) for payload in results]
    summary = {
        "schema_version": 1,
        "rows": summary_rows,
        "hints_sha256": hints["sha256"],
        "note": "Dev/diagnostic A/B only; final decision requires a new acceptance set.",
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "SUMMARY.md").write_text(render_markdown(summary_rows), encoding="utf-8")
    print(render_markdown(summary_rows), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
