#!/usr/bin/env python3
"""Prepare cleaned AI Hub 71592 manifests for domain-continuation experiments."""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = ROOT / "data/stt/aihub71592-ict-new-segmented"
HISTORICAL_ROOT = ROOT / "data/stt/handoff-reconstructed"
OUTPUT_ROOT = ROOT / "data/stt/aihub71592-domain-20260922"
SEED = 20260922
MIN_SECONDS = 1.5
MAX_SECONDS = 24.0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--source-root", type=Path, default=SOURCE_ROOT)
    p.add_argument("--historical-root", type=Path, default=HISTORICAL_ROOT)
    p.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    p.add_argument("--seed", type=int, default=SEED)
    p.add_argument("--overwrite", action="store_true")
    return p.parse_args()


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def project_relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def rewrite_71592(row: dict, source_root: Path) -> dict:
    audio = source_root / str(row["audio"])
    if not audio.is_file():
        raise FileNotFoundError(audio)
    duration = float(row["duration"])
    return {
        "audio": project_relative(audio),
        "text": str(row["text"]),
        "source_id": str(row["source_id"]),
        "segment_id": str(row["segment_id"]),
        "split": str(row["split"]),
        "gender": row.get("gender"),
        "duration": duration,
        "alignment_coverage": float(row["alignment_coverage"]),
        "dataset": "aihub71592-ict-new",
    }


def rewrite_historical(row: dict, historical_root: Path) -> dict:
    audio = Path(str(row["audio"]))
    resolved = audio if audio.is_absolute() else historical_root / audio
    if not resolved.is_file():
        raise FileNotFoundError(resolved)
    return {
        "audio": project_relative(resolved),
        "text": str(row["text"]),
        "dataset": "aihub119-historical-clean-replay",
    }


def cleaned_split(source_root: Path, split: str) -> tuple[list[dict], Counter]:
    stats: Counter = Counter()
    cleaned: list[dict] = []
    for raw in load_jsonl(source_root / f"{split}.jsonl"):
        stats["input"] += 1
        text = " ".join(str(raw.get("text", "")).split())
        duration = float(raw.get("duration", 0.0))
        if not text:
            stats["empty_text"] += 1
            continue
        if duration < MIN_SECONDS:
            stats["too_short"] += 1
            continue
        if duration > MAX_SECONDS:
            stats["too_long"] += 1
            continue
        row = dict(raw)
        row["text"] = text
        cleaned.append(rewrite_71592(row, source_root))
        stats["kept"] += 1
    return cleaned, stats


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def validate_split_disjoint(splits: dict[str, list[dict]]) -> None:
    source_sets = {
        split: {str(row["source_id"]) for row in rows}
        for split, rows in splits.items()
    }
    for left, right in (("train", "validation"), ("train", "test"), ("validation", "test")):
        overlap = source_sets[left] & source_sets[right]
        if overlap:
            raise RuntimeError(f"{left}/{right} source_id overlap: {len(overlap)}")


def main() -> int:
    args = parse_args()
    source_root = args.source_root.resolve()
    historical_root = args.historical_root.resolve()
    output_root = args.output_root.resolve()

    if output_root.exists() and any(output_root.iterdir()) and not args.overwrite:
        raise RuntimeError(f"output exists; pass --overwrite: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)

    splits: dict[str, list[dict]] = {}
    split_stats: dict[str, dict[str, int]] = {}
    for split in ("train", "validation", "test"):
        rows, stats = cleaned_split(source_root, split)
        splits[split] = rows
        split_stats[split] = dict(stats)
    validate_split_disjoint(splits)

    for split, rows in splits.items():
        write_jsonl(output_root / f"{split}.jsonl", rows)

    new_train = splits["train"]
    replay_count = len(new_train) // 4
    historical_train_path = (
        historical_root / "dataset-clean-no-placeholders/train.jsonl"
    )
    historical_rows = load_jsonl(historical_train_path)
    rng = random.Random(args.seed + 100)
    rng.shuffle(historical_rows)
    if len(historical_rows) < replay_count:
        raise RuntimeError(
            f"historical train {len(historical_rows)} < replay {replay_count}"
        )
    replay = [
        rewrite_historical(row, historical_root)
        for row in historical_rows[:replay_count]
    ]
    mixed = [*new_train, *replay]
    random.Random(args.seed + 101).shuffle(mixed)
    write_jsonl(output_root / "train-replay20.jsonl", mixed)

    historical_validation = [
        rewrite_historical(row, historical_root)
        for row in load_jsonl(
            historical_root / "dataset-clean-no-placeholders/validation.jsonl"
        )
    ]
    write_jsonl(
        output_root / "retention-validation.jsonl",
        historical_validation,
    )

    metadata = {
        "seed": args.seed,
        "filters": {
            "min_duration_seconds": MIN_SECONDS,
            "max_duration_seconds": MAX_SECONDS,
            "nonempty_text": True,
        },
        "source": str(source_root),
        "splits": {
            split: {
                **split_stats[split],
                "hours": round(
                    sum(float(row["duration"]) for row in rows) / 3600, 3
                ),
                "source_ids": len({row["source_id"] for row in rows}),
            }
            for split, rows in splits.items()
        },
        "replay20": {
            "new_71592": len(new_train),
            "old_119_clean": len(replay),
            "combined": len(mixed),
            "new_fraction": len(new_train) / len(mixed),
            "old_fraction": len(replay) / len(mixed),
        },
        "retention_validation_rows": len(historical_validation),
        "test_policy": (
            "test.jsonl is held out from training and checkpoint selection; "
            "open only after C1/C2 selection using validation + retention."
        ),
        "split_caveat": (
            "71592 source_id is disjoint across train/validation/test, but "
            "the dataset labels expose no verified speaker id, so "
            "speaker-disjointness cannot be guaranteed."
        ),
    }
    (output_root / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
