#!/usr/bin/env python3
"""Validate reconstructed STT fine-tuning data before any training run.

The default paths target the locally reconstructed AI Hub 119 handoff dataset.
This script intentionally performs no model download or training.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = PROJECT_ROOT / "data" / "stt" / "handoff-reconstructed"
SOURCE_ID_RE = re.compile(r"^(DKSR\d{8})_", re.IGNORECASE)


@dataclass(frozen=True)
class Row:
    split: str
    line_number: int
    audio: str
    text: str
    filename: str
    segment_id: str
    source_id: str


@dataclass(frozen=True)
class SplitSummary:
    rows: int
    unique_audio: int
    unique_segments: int
    unique_sources: int
    duplicate_audio: int
    duplicate_segments: int
    missing_audio: int


def normalize_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split())


def normalize_audio(value: str) -> str:
    return value.replace("\\", "/").lstrip("./")


def resolve_audio(root: Path, audio: str) -> Path:
    path = Path(audio)
    return path if path.is_absolute() else root / normalize_audio(audio)


def parse_source_id(filename: str) -> str:
    match = SOURCE_ID_RE.match(filename)
    if not match:
        raise ValueError(
            f"unsupported segment filename {filename!r}; expected DKSR########_....wav"
        )
    return match.group(1).upper()


def load_manifest(path: Path, split: str) -> list[Row]:
    if not path.is_file():
        raise FileNotFoundError(f"{split} manifest not found: {path}")

    rows: list[Row] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            if not raw.strip():
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc

            audio = payload.get("audio")
            text = payload.get("text")
            if not isinstance(audio, str) or not audio.strip():
                raise ValueError(f"{path}:{line_number}: non-empty string audio is required")
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"{path}:{line_number}: non-empty string text is required")

            normalized_audio = normalize_audio(audio)
            filename = Path(normalized_audio).name
            if not filename.lower().endswith(".wav"):
                raise ValueError(f"{path}:{line_number}: expected WAV audio, got {audio!r}")

            segment_id = Path(filename).stem.upper()
            source_id = parse_source_id(filename)
            rows.append(
                Row(
                    split=split,
                    line_number=line_number,
                    audio=normalized_audio,
                    text=normalize_text(text),
                    filename=filename,
                    segment_id=segment_id,
                    source_id=source_id,
                )
            )

    if not rows:
        raise ValueError(f"{split} manifest is empty: {path}")
    return rows


def summarize(rows: list[Row], root: Path, *, check_audio: bool) -> SplitSummary:
    audio_counts = Counter(row.audio for row in rows)
    segment_counts = Counter(row.segment_id for row in rows)
    source_ids = {row.source_id for row in rows}

    missing_audio = 0
    if check_audio:
        for row in rows:
            if not resolve_audio(root, row.audio).is_file():
                missing_audio += 1

    return SplitSummary(
        rows=len(rows),
        unique_audio=len(audio_counts),
        unique_segments=len(segment_counts),
        unique_sources=len(source_ids),
        duplicate_audio=sum(count - 1 for count in audio_counts.values() if count > 1),
        duplicate_segments=sum(
            count - 1 for count in segment_counts.values() if count > 1
        ),
        missing_audio=missing_audio,
    )


def examples(values: set[str], *, limit: int = 10) -> list[str]:
    return sorted(values)[:limit]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--train-manifest", type=Path)
    parser.add_argument("--validation-manifest", type=Path)
    parser.add_argument(
        "--skip-audio-exists",
        action="store_true",
        help="Skip checking that every manifest audio path exists on disk.",
    )
    args = parser.parse_args()

    root = args.root.expanduser()
    if not root.is_absolute():
        root = PROJECT_ROOT / root

    train_manifest = args.train_manifest or root / "dataset" / "train.jsonl"
    validation_manifest = (
        args.validation_manifest or root / "dataset" / "validation.jsonl"
    )
    if not train_manifest.is_absolute():
        train_manifest = PROJECT_ROOT / train_manifest
    if not validation_manifest.is_absolute():
        validation_manifest = PROJECT_ROOT / validation_manifest

    train = load_manifest(train_manifest, "train")
    validation = load_manifest(validation_manifest, "validation")

    check_audio = not args.skip_audio_exists
    train_summary = summarize(train, root, check_audio=check_audio)
    validation_summary = summarize(validation, root, check_audio=check_audio)

    train_audio = {row.audio for row in train}
    validation_audio = {row.audio for row in validation}
    train_segments = {row.segment_id for row in train}
    validation_segments = {row.segment_id for row in validation}
    train_sources = {row.source_id for row in train}
    validation_sources = {row.source_id for row in validation}
    train_texts = {row.text for row in train}
    validation_texts = {row.text for row in validation}

    cross_audio = train_audio & validation_audio
    cross_segments = train_segments & validation_segments
    cross_sources = train_sources & validation_sources
    cross_texts = train_texts & validation_texts

    result = {
        "root": str(root),
        "train": train_summary.__dict__,
        "validation": validation_summary.__dict__,
        "cross_split": {
            "audio_paths": len(cross_audio),
            "segment_ids": len(cross_segments),
            "source_conversations": len(cross_sources),
            "normalized_texts_informational": len(cross_texts),
            "audio_examples": examples(cross_audio),
            "segment_examples": examples(cross_segments),
            "source_examples": examples(cross_sources),
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    blocking = any(
        (
            train_summary.duplicate_audio,
            train_summary.duplicate_segments,
            train_summary.missing_audio,
            validation_summary.duplicate_audio,
            validation_summary.duplicate_segments,
            validation_summary.missing_audio,
            len(cross_audio),
            len(cross_segments),
            len(cross_sources),
        )
    )
    if blocking:
        print("STT fine-tuning dataset preflight FAILED", file=sys.stderr)
        return 1

    print("STT fine-tuning dataset preflight PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
