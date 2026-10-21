#!/usr/bin/env python3
"""Prepare product-persona AI Hub 119 manifests for new-data STT continuation.

The new-data pool is deliberately disjoint from the historical train/validation
and both holdout tests at the source-conversation level.
"""

from __future__ import annotations

import argparse
import io
import json
import random
import re
import shutil
import wave
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
PROJECT_ROOT = Path(__file__).resolve().parents[2]
AIHUB_ROOT = PROJECT_ROOT / "data/stt/aihub/119"
HISTORICAL_ROOT = PROJECT_ROOT / "data/stt/handoff-reconstructed"
OUTPUT_ROOT = PROJECT_ROOT / "data/stt/new-persona-119-20260921"

SOURCE_RE = re.compile(r"^([A-Z]+\d{8})[_\.]", re.IGNORECASE)
PLACEHOLDER_RE = re.compile(r"#.+?#|&[^&]+&")

TARGET_REGIONS = {"부산", "울산", "경남"}
TARGET_OCCUPATIONS = {"학생", "무직/취업준비생"}
TARGET_TOPICS = {"회사/학교", "꿈(목표)", "자격증", "아르바이트", "성격", "전자기기", "4차산업혁명"}
DEFAULT_COUNTS = {"train": 10000, "validation": 1000, "test": 1000}
@dataclass(frozen=True)
class Candidate:
    archive_group: str
    source_id: str
    utterance_id: str
    speaker_id: str
    start: float
    end: float
    text: str
    topic: str
    region: str
    occupation: str
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--aihub-root", type=Path, default=AIHUB_ROOT)
    p.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    p.add_argument("--seed", type=int, default=20260921)
    p.add_argument("--train-count", type=int, default=DEFAULT_COUNTS["train"])
    p.add_argument("--validation-count", type=int, default=DEFAULT_COUNTS["validation"])
    p.add_argument("--test-count", type=int, default=DEFAULT_COUNTS["test"])
    p.add_argument("--replay-count", type=int, default=2500)
    p.add_argument("--build", action="store_true")
    p.add_argument("--overwrite", action="store_true")
    return p.parse_args()
def source_ids_from_manifest(path: Path) -> set[str]:
    result: set[str] = set()
    if not path.is_file():
        return result
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            name = Path(str(row["audio"]).replace("\\", "/")).name
            match = SOURCE_RE.match(name)
            if match:
                result.add(match.group(1).upper())
    return result


def used_source_ids() -> set[str]:
    paths = [
        PROJECT_ROOT / "data/stt/handoff/train.jsonl",
        PROJECT_ROOT / "data/stt/handoff/validation.jsonl",
        PROJECT_ROOT / "data/stt/holdout-test/manifest.jsonl",
        PROJECT_ROOT / "data/stt/holdout-test-b-clean/manifest.jsonl",
    ]
    used: set[str] = set()
    for path in paths:
        used.update(source_ids_from_manifest(path))
    return used


def find_one(root: Path, pattern: str) -> Path:
    matches = list(root.rglob(pattern))
    if len(matches) != 1:
        raise RuntimeError(f"expected one {pattern!r} under {root}, found {len(matches)}")
    return matches[0]


def archive_pairs(root: Path) -> dict[str, tuple[Path, Path]]:
    return {
        "1": (
            find_one(root, "*(비식별화완료)경상도_학습데이터_1.zip"),
            find_one(root, "*(비식별화완료)경상도_1.zip"),
        ),
        "2": (
            find_one(root, "*(비식별화완료)경상도_학습데이터_2.zip"),
            find_one(root, "*(비식별화완료)경상도_2.zip"),
        ),
    }


def clean_text(value: object) -> str:
    return " ".join(str(value or "").split())


def scan_candidates(
    root: Path,
    used: set[str],
    available_source_ids: set[str],
) -> tuple[list[Candidate], dict[str, tuple[Path, Path]]]:
    pairs = archive_pairs(root)
    candidates: list[Candidate] = []

    for group, (label_zip, _) in pairs.items():
        with zipfile.ZipFile(label_zip) as zf:
            for member in zf.namelist():
                if not member.lower().endswith(".json"):
                    continue
                source_id = Path(member).stem.upper()
                if source_id in used:
                    continue
                if source_id not in available_source_ids:
                    # Labels span more source archives than are retained locally.
                    # Only select conversations whose source WAV is currently present.
                    continue
                payload = json.loads(zf.read(member))
                topic = clean_text((payload.get("metadata") or {}).get("topic"))
                if topic not in TARGET_TOPICS:
                    continue
                speakers = {
                    str(sp.get("id")): sp
                    for sp in payload.get("speaker", [])
                    if isinstance(sp, dict) and sp.get("id") is not None
                }
                for raw in payload.get("utterance", []):
                    if not isinstance(raw, dict):
                        continue
                    speaker_id = str(raw.get("speaker_id", ""))
                    speaker = speakers.get(speaker_id)
                    if not speaker:
                        continue
                    if clean_text(speaker.get("age")) != "20대":
                        continue
                    occupation = clean_text(speaker.get("occupation"))
                    if occupation not in TARGET_OCCUPATIONS:
                        continue
                    region = clean_text(
                        speaker.get("current_residence") or speaker.get("principal_residence")
                    )
                    if region not in TARGET_REGIONS:
                        continue
                    text = clean_text(raw.get("dialect_form", raw.get("form", "")))
                    if not text or PLACEHOLDER_RE.search(text):
                        continue
                    try:
                        start = float(raw["start"])
                        end = float(raw["end"])
                    except (KeyError, TypeError, ValueError):
                        continue
                    if start < 0 or end <= start:
                        continue
                    utterance_id = clean_text(raw.get("id"))
                    if not utterance_id:
                        continue
                    candidates.append(
                        Candidate(
                            archive_group=group,
                            source_id=source_id,
                            utterance_id=utterance_id,
                            speaker_id=speaker_id,
                            start=start,
                            end=end,
                            text=text,
                            topic=topic,
                            region=region,
                            occupation=occupation,
                        )
                    )
    return candidates, pairs


def split_candidates(
    candidates: list[Candidate],
    *,
    seed: int,
    counts: dict[str, int],
) -> dict[str, list[Candidate]]:
    by_source: dict[str, list[Candidate]] = defaultdict(list)
    for row in candidates:
        by_source[row.source_id].append(row)

    sources = sorted(by_source)
    random.Random(seed).shuffle(sources)
    n = len(sources)
    train_cut = int(n * 0.8)
    val_cut = int(n * 0.9)
    source_splits = {
        "train": set(sources[:train_cut]),
        "validation": set(sources[train_cut:val_cut]),
        "test": set(sources[val_cut:]),
    }

    selected: dict[str, list[Candidate]] = {}
    for offset, split in enumerate(("train", "validation", "test")):
        pool = [
            row
            for source_id in source_splits[split]
            for row in by_source[source_id]
        ]
        rng = random.Random(seed + offset + 1)
        rng.shuffle(pool)
        wanted = counts[split]
        if len(pool) < wanted:
            raise RuntimeError(
                f"{split} candidate pool too small: {len(pool)} < requested {wanted}"
            )
        selected[split] = sorted(
            pool[:wanted],
            key=lambda row: (row.source_id, row.start, row.utterance_id),
        )

    overlaps = {
        a + "_" + b: len({x.source_id for x in selected[a]} & {x.source_id for x in selected[b]})
        for a, b in (("train", "validation"), ("train", "test"), ("validation", "test"))
    }
    if any(overlaps.values()):
        raise AssertionError(f"source overlap after split: {overlaps}")
    return selected


def source_members(source_zip: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    with zipfile.ZipFile(source_zip) as zf:
        for member in zf.namelist():
            if member.lower().endswith(".wav"):
                result[Path(member).stem.upper()] = member
    return result


def write_segment(source_wav: bytes, start: float, end: float, destination: Path) -> None:
    with wave.open(io.BytesIO(source_wav), "rb") as src:
        params = src.getparams()
        if params.framerate <= 0:
            raise ValueError("invalid sample rate")
        start_frame = max(0, round(start * params.framerate))
        end_frame = min(params.nframes, round(end * params.framerate))
        if end_frame <= start_frame:
            raise ValueError(f"empty segment {start}..{end}")
        src.setpos(start_frame)
        frames = src.readframes(end_frame - start_frame)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(destination), "wb") as dst:
        dst.setparams(params)
        dst.writeframes(frames)


def project_relative(path: Path) -> str:
    return str(path.resolve().relative_to(PROJECT_ROOT.resolve())).replace("\\", "/")


def build_audio_and_manifests(
    selected: dict[str, list[Candidate]],
    pairs: dict[str, tuple[Path, Path]],
    output_root: Path,
    *,
    overwrite: bool,
) -> None:
    if (resolved := output_root.resolve()).parent != (PROJECT_ROOT / "data/stt").resolve() or not resolved.name.startswith("new-persona-119-"):
        raise ValueError(f"refusing broad/out-of-scope generated dataset output: {resolved}")
    output_root = resolved
    if output_root.exists() and any(output_root.iterdir()):
        if not overwrite:
            raise RuntimeError(f"output is not empty: {output_root}")
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    selected_by_source: dict[str, list[tuple[str, Candidate]]] = defaultdict(list)
    for split, rows in selected.items():
        for row in rows:
            selected_by_source[row.source_id].append((split, row))

    source_locations: dict[str, tuple[Path, str]] = {}
    for _, (_, source_zip) in pairs.items():
        for source_id, member in source_members(source_zip).items():
            if source_id in source_locations:
                raise RuntimeError(f"duplicate source WAV across archives: {source_id}")
            source_locations[source_id] = (source_zip, member)

    for source_id, rows in selected_by_source.items():
        location = source_locations.get(source_id)
        if location is None:
            raise FileNotFoundError(f"source WAV missing for {source_id} in local source archives")
        source_zip, member = location
        with zipfile.ZipFile(source_zip) as zf:
            source_wav = zf.read(member)
        for split, row in rows:
            filename = row.utterance_id.replace(".", "_") + ".wav"
            destination = output_root / "audio" / split / filename
            write_segment(source_wav, row.start, row.end, destination)

    for split, rows in selected.items():
        manifest = output_root / f"{split}.jsonl"
        with manifest.open("w", encoding="utf-8") as handle:
            for row in rows:
                filename = row.utterance_id.replace(".", "_") + ".wav"
                payload = {
                    "audio": project_relative(output_root / "audio" / split / filename),
                    "text": row.text,
                    "source_id": row.source_id,
                    "utterance_id": row.utterance_id,
                    "topic": row.topic,
                    "region": row.region,
                    "occupation": row.occupation,
                    "dataset": "aihub119-new-persona",
                }
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def rewrite_historical_row(row: dict, old_root: Path) -> dict:
    old_audio = Path(str(row["audio"]))
    resolved = old_audio if old_audio.is_absolute() else old_root / old_audio
    if not resolved.is_file():
        raise FileNotFoundError(resolved)
    return {
        "audio": project_relative(resolved),
        "text": row["text"],
        "dataset": "aihub119-historical-clean-replay",
    }


def build_replay_manifest(output_root: Path, replay_count: int, seed: int) -> dict[str, int]:
    source = HISTORICAL_ROOT / "dataset-clean-no-placeholders/train.jsonl"
    rows = load_jsonl(source)
    rng = random.Random(seed + 100)
    rng.shuffle(rows)
    if len(rows) < replay_count:
        raise RuntimeError("historical clean train smaller than replay request")
    replay = [rewrite_historical_row(row, HISTORICAL_ROOT) for row in rows[:replay_count]]
    new_rows = load_jsonl(output_root / "train.jsonl")
    combined = new_rows + replay
    random.Random(seed + 101).shuffle(combined)
    path = output_root / "train-replay20.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for row in combined:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    retention = [
        rewrite_historical_row(row, HISTORICAL_ROOT)
        for row in load_jsonl(
            HISTORICAL_ROOT / "dataset-clean-no-placeholders/validation.jsonl"
        )
    ]
    with (output_root / "retention-validation.jsonl").open("w", encoding="utf-8") as handle:
        for row in retention:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {
        "new_train": len(new_rows),
        "replay": len(replay),
        "combined": len(combined),
        "retention_validation": len(retention),
    }


def summarize(selected: dict[str, list[Candidate]], used: set[str], candidates: list[Candidate]) -> dict:
    result: dict[str, object] = {
        "seed": 20260921,
        "filter": {
            "regions": sorted(TARGET_REGIONS),
            "age": "20대",
            "occupations": sorted(TARGET_OCCUPATIONS),
            "topics": sorted(TARGET_TOPICS),
            "placeholder_free": True,
        },
        "historical_used_sources_excluded": len(used),
        "candidate_utterances": len(candidates),
        "candidate_sources": len({x.source_id for x in candidates}),
        "splits": {},
    }
    for split, rows in selected.items():
        result["splits"][split] = {
            "rows": len(rows),
            "sources": len({x.source_id for x in rows}),
            "duration_hours": round(sum(x.end - x.start for x in rows) / 3600, 3),
            "regions": dict(Counter(x.region for x in rows)),
            "topics": dict(Counter(x.topic for x in rows)),
        }
    return result


def main() -> int:
    args = parse_args()
    root = args.aihub_root.resolve()
    output_root = args.output_root.resolve()
    used = used_source_ids()
    pairs = archive_pairs(root)
    available_source_ids: set[str] = set()
    for _, (_, source_zip) in pairs.items():
        available_source_ids.update(source_members(source_zip))
    candidates, pairs = scan_candidates(root, used, available_source_ids)
    counts = {
        "train": args.train_count,
        "validation": args.validation_count,
        "test": args.test_count,
    }
    selected = split_candidates(candidates, seed=args.seed, counts=counts)
    summary = summarize(selected, used, candidates)
    summary["output_root"] = str(output_root)
    summary["build_requested"] = bool(args.build)

    if args.build:
        build_audio_and_manifests(selected, pairs, output_root, overwrite=args.overwrite)
        summary["replay"] = build_replay_manifest(output_root, args.replay_count, args.seed)
        (output_root / "metadata.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
