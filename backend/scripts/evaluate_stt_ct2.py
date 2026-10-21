#!/usr/bin/env python3
"""Evaluate one faster-whisper/CTranslate2 STT model with CER and WER."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

from faster_whisper import WhisperModel

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = (
    PROJECT_ROOT
    / "models"
    / "stt"
    / "[REDACTED]"
)
DEFAULT_EVAL_DIR = PROJECT_ROOT / "data" / "stt" / "holdout-test"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "artifacts" / "stt" / "baseline-holdout"


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def edit_distance(reference: list[str], hypothesis: list[str]) -> int:
    previous = list(range(len(hypothesis) + 1))
    for i, ref_token in enumerate(reference, start=1):
        current = [i]
        for j, hyp_token in enumerate(hypothesis, start=1):
            substitution = previous[j - 1] + (ref_token != hyp_token)
            insertion = current[j - 1] + 1
            deletion = previous[j] + 1
            current.append(min(substitution, insertion, deletion))
        previous = current
    return previous[-1]


def error_stats(
    references: list[list[str]], hypotheses: list[list[str]]
) -> tuple[int, int, float]:
    edits = 0
    units = 0
    for reference, hypothesis in zip(references, hypotheses):
        edits += edit_distance(reference, hypothesis)
        units += len(reference)
    rate = edits / units if units else 0.0
    return edits, units, rate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--eval-dir", type=Path, default=DEFAULT_EVAL_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument("--compute-type", default="float16")
    parser.add_argument(
        "--max-samples",
        type=int,
        help="Evaluate only the first N rows for a quick smoke check.",
    )
    parser.add_argument(
        "--start-index",
        type=int,
        default=0,
        help="Zero-based starting row index within the evaluation manifest.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = args.eval_dir / "manifest.jsonl"
    rows = [
        json.loads(line)
        for line in manifest.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rows = rows[args.start_index :]
    if args.max_samples is not None:
        rows = rows[: args.max_samples]
    if not rows:
        raise ValueError(f"empty evaluation manifest: {manifest}")

    model = WhisperModel(
        str(args.model), device="cuda", compute_type=args.compute_type
    )
    records = []
    for index, row in enumerate(rows, start=1):
        segments, _ = model.transcribe(
            str(args.eval_dir / row["audio"]),
            language="ko",
            task="transcribe",
            beam_size=args.beam_size,
            temperature=0.0,
            condition_on_previous_text=False,
            vad_filter=False,
        )
        prediction = " ".join(
            segment.text.strip() for segment in segments
        ).strip()
        records.append(
            {
                "id": row["id"],
                "source_id": row.get("source_id"),
                "reference": row["reference"],
                "prediction": prediction,
            }
        )
        print(f"{index}/{len(rows)}: {row['id']}", flush=True)

    references = [normalize(row["reference"]) for row in records]
    predictions = [normalize(row["prediction"]) for row in records]
    reference_chars = [list(text.replace(" ", "")) for text in references]
    prediction_chars = [list(text.replace(" ", "")) for text in predictions]
    reference_words = [text.split() for text in references]
    prediction_words = [text.split() for text in predictions]
    cer_edits, cer_units, cer_rate = error_stats(
        reference_chars, prediction_chars
    )
    wer_edits, wer_units, wer_rate = error_stats(
        reference_words, prediction_words
    )
    scores = {
        "cer_percent": cer_rate * 100,
        "wer_percent": wer_rate * 100,
        "cer_edits": cer_edits,
        "cer_units": cer_units,
        "wer_edits": wer_edits,
        "wer_units": wer_units,
        "utterances": len(rows),
        "start_index": args.start_index,
        "beam_size": args.beam_size,
        "compute_type": args.compute_type,
        "model": str(args.model.resolve()),
        "eval_dir": str(args.eval_dir.resolve()),
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "metrics.json").write_text(
        json.dumps(scores, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "predictions.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(scores, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
