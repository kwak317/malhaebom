#!/usr/bin/env python3
"""Helpers for AI Hub 71592 ICT/New answer segmentation and transcript alignment."""

from __future__ import annotations

import difflib
import hashlib
import json
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path

CONFIG_VERSION = 3
MIN_SEGMENT_SECONDS = 1.5
REQUIRED_CT2 = (
    "config.json",
    "model.bin",
    "tokenizer.json",
    "vocabulary.json",
    "preprocessor_config.json",
)


@dataclass(frozen=True)
class Record:
    source_id: str
    original_split: str
    target_split: str
    gender: str
    transcript: str
    duration_ms: int
    source_zip: Path
    audio_member: str
    label_zip: Path
    label_member: str


def find_one(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one {name!r}, found {len(matches)}")
    return matches[0].resolve()


def discover_archives(root: Path) -> dict[tuple[str, str, str], Path]:
    result: dict[tuple[str, str, str], Path] = {}
    for split, prefix in (("train", "T"), ("validation", "V")):
        for gender, token in (("female", "Female"), ("male", "Male")):
            result[(split, gender, "source")] = find_one(
                root, f"{prefix}S_05.ICT_{token}_New.zip"
            )
            result[(split, gender, "label")] = find_one(
                root, f"{prefix}L_05.ICT_{token}_New.zip"
            )
    return result


def clean_text(value: object) -> str:
    return " ".join(str(value or "").split())


def answer_member_map(source_zip: Path) -> dict[str, str]:
    with zipfile.ZipFile(source_zip) as zf:
        return {
            Path(member).name: member
            for member in zf.namelist()
            if Path(member).name.startswith("ckmk_a_")
            and member.lower().endswith(".wav")
        }


def stable_validation_split(source_ids: list[str], seed: int) -> dict[str, str]:
    ordered = sorted(
        source_ids,
        key=lambda sid: hashlib.sha256(f"{seed}:{sid}".encode()).hexdigest(),
    )
    cut = len(ordered) // 2
    return {
        sid: ("validation" if index < cut else "test")
        for index, sid in enumerate(ordered)
    }


def _parse_label(
    payload: dict[str, object],
) -> tuple[str, int, str]:
    dataset = payload.get("dataSet") or {}
    answer_block = (dataset.get("answer") or {}) if isinstance(dataset, dict) else {}
    raw_answer = (
        (answer_block.get("raw") or {}) if isinstance(answer_block, dict) else {}
    )
    transcript = clean_text(
        raw_answer.get("text") if isinstance(raw_answer, dict) else ""
    )
    raw_info = payload.get("rawDataInfo") or {}
    answer_info = (
        (raw_info.get("answer") or {}) if isinstance(raw_info, dict) else {}
    )
    if not isinstance(answer_info, dict):
        raise ValueError("missing rawDataInfo.answer")
    duration_ms = int(answer_info.get("duration"))
    audio_name = Path(str(answer_info.get("audioPath", ""))).name
    if not transcript or not audio_name:
        raise ValueError("missing answer transcript/audioPath")
    return transcript, duration_ms, audio_name


def scan_records(
    root: Path, seed: int
) -> tuple[list[Record], dict[str, object]]:
    archives = discover_archives(root)
    source_maps = {
        (split, gender): answer_member_map(archives[(split, gender, "source")])
        for split in ("train", "validation")
        for gender in ("female", "male")
    }
    raw_records: list[dict[str, object]] = []
    malformed: list[str] = []
    missing_audio: list[str] = []

    for split in ("train", "validation"):
        for gender in ("female", "male"):
            label_zip = archives[(split, gender, "label")]
            source_zip = archives[(split, gender, "source")]
            members = source_maps[(split, gender)]
            with zipfile.ZipFile(label_zip) as zf:
                for member in zf.namelist():
                    if not member.lower().endswith(".json"):
                        continue
                    try:
                        payload = json.loads(zf.read(member).decode("utf-8"))
                        transcript, duration_ms, audio_name = _parse_label(payload)
                    except Exception:
                        malformed.append(f"{label_zip.name}:{member}")
                        continue
                    audio_member = members.get(audio_name)
                    if audio_member is None:
                        missing_audio.append(f"{source_zip.name}:{audio_name}")
                        continue
                    raw_records.append(
                        {
                            "source_id": Path(member).stem,
                            "original_split": split,
                            "gender": gender,
                            "transcript": transcript,
                            "duration_ms": duration_ms,
                            "source_zip": source_zip,
                            "audio_member": audio_member,
                            "label_zip": label_zip,
                            "label_member": member,
                        }
                    )

    validation_ids = sorted(
        str(row["source_id"])
        for row in raw_records
        if row["original_split"] == "validation"
    )
    validation_plan = stable_validation_split(validation_ids, seed)
    records = [
        Record(
            source_id=str(row["source_id"]),
            original_split=str(row["original_split"]),
            target_split=(
                "train"
                if row["original_split"] == "train"
                else validation_plan[str(row["source_id"])]
            ),
            gender=str(row["gender"]),
            transcript=str(row["transcript"]),
            duration_ms=int(row["duration_ms"]),
            source_zip=Path(row["source_zip"]),
            audio_member=str(row["audio_member"]),
            label_zip=Path(row["label_zip"]),
            label_member=str(row["label_member"]),
        )
        for row in raw_records
    ]
    records.sort(key=lambda row: (row.target_split, row.source_id))
    summary = {
        "archives": {"/".join(k): str(v) for k, v in archives.items()},
        "valid_records": len(records),
        "original_train": sum(r.original_split == "train" for r in records),
        "original_validation": sum(
            r.original_split == "validation" for r in records
        ),
        "target_train": sum(r.target_split == "train" for r in records),
        "target_validation": sum(
            r.target_split == "validation" for r in records
        ),
        "target_test": sum(r.target_split == "test" for r in records),
        "malformed_labels": malformed,
        "missing_answer_audio": missing_audio,
    }
    return records, summary


def normalize_with_positions(text: str) -> tuple[str, list[int]]:
    chars: list[str] = []
    positions: list[int] = []
    for pos, raw in enumerate(text):
        for ch in unicodedata.normalize("NFKC", raw).lower():
            if ch.isalnum():
                chars.append(ch)
                positions.append(pos)
    return "".join(chars), positions


def hypothesis_chars(words: list[tuple[str, float, float]]) -> tuple[str, list[float]]:
    chars: list[str] = []
    times: list[float] = []
    for text, start, end in words:
        normalized, _ = normalize_with_positions(text)
        if not normalized:
            continue
        span = max(0.001, end - start)
        for index, ch in enumerate(normalized):
            chars.append(ch)
            times.append(start + span * ((index + 0.5) / len(normalized)))
    return "".join(chars), times


def aligned_reference_times(reference: str, words: list[tuple[str, float, float]], audio_duration: float) -> tuple[list[float], list[int], float]:
    ref_chars, positions = normalize_with_positions(reference)
    hyp_chars, hyp_times = hypothesis_chars(words)
    if not ref_chars or not hyp_chars:
        return [], positions, 0.0

    anchors: dict[int, float] = {}
    matcher = difflib.SequenceMatcher(None, ref_chars, hyp_chars, autojunk=False)
    matched = 0
    for block in matcher.get_matching_blocks():
        if block.size <= 0:
            continue
        matched += block.size
        for offset in range(block.size):
            anchors[block.a + offset] = hyp_times[block.b + offset]
    coverage = matched / len(ref_chars)
    if not anchors:
        return [], positions, coverage

    times: list[float | None] = [None] * len(ref_chars)
    for index, timestamp in anchors.items():
        times[index] = min(audio_duration, max(0.0, timestamp))
    anchor_ids = sorted(anchors)

    first = anchor_ids[0]
    first_t = float(times[first])
    for i in range(first):
        times[i] = first_t * ((i + 1) / (first + 1))

    for left, right in zip(anchor_ids, anchor_ids[1:]):
        left_t = float(times[left])
        right_t = max(left_t, float(times[right]))
        gap = right - left
        for step in range(1, gap):
            times[left + step] = left_t + (right_t - left_t) * (step / gap)

    last = anchor_ids[-1]
    last_t = float(times[last])
    remaining = len(ref_chars) - 1 - last
    for step in range(1, remaining + 1):
        times[last + step] = last_t + (audio_duration - last_t) * (
            step / (remaining + 1)
        )
    return [float(value) for value in times], positions, coverage


def punctuation_boundaries(text: str, positions: list[int]) -> set[int]:
    result: set[int] = set()
    punctuation = ".!?。！？"
    for index in range(len(positions) - 1):
        gap = text[positions[index] + 1 : positions[index + 1]]
        if any(mark in gap for mark in punctuation):
            result.add(index)
    if positions:
        tail = text[positions[-1] + 1 :]
        if any(mark in tail for mark in punctuation):
            result.add(len(positions) - 1)
    return result


def word_boundaries(text: str, positions: list[int]) -> set[int]:
    result: set[int] = set()
    for index in range(len(positions) - 1):
        gap = text[positions[index] + 1 : positions[index + 1]]
        if any(ch.isspace() or not ch.isalnum() for ch in gap):
            result.add(index)
    if positions:
        result.add(len(positions) - 1)
    return result


def make_segments(
    text: str,
    ref_times: list[float],
    positions: list[int],
    audio_duration: float,
    max_seconds: float,
) -> list[dict[str, object]]:
    sentence_boundaries = punctuation_boundaries(text, positions)
    safe_boundaries = word_boundaries(text, positions)
    result: list[dict[str, object]] = []
    start_index = 0

    while start_index < len(ref_times):
        clip_start = (
            0.0
            if start_index == 0
            else (ref_times[start_index - 1] + ref_times[start_index]) / 2
        )

        def boundary_end(index: int) -> float:
            return (
                audio_duration
                if index + 1 >= len(ref_times)
                else (ref_times[index] + ref_times[index + 1]) / 2
            )

        allowed = [
            idx
            for idx in safe_boundaries
            if idx >= start_index
            and boundary_end(idx) - clip_start <= max_seconds
            and boundary_end(idx) - clip_start >= MIN_SEGMENT_SECONDS
        ]
        if not allowed:
            allowed = [min(idx for idx in safe_boundaries if idx >= start_index)]

        sentence_candidates = [
            idx
            for idx in sentence_boundaries
            if idx in allowed
            and boundary_end(idx) - clip_start >= max_seconds * 0.55
        ]
        if sentence_candidates:
            end_index = max(sentence_candidates)
        else:
            end_index = max(allowed)
        start_orig = positions[start_index]
        end_orig = (
            positions[end_index + 1]
            if end_index + 1 < len(positions)
            else len(text)
        )
        segment_text = text[start_orig:end_orig].strip()
        clip_end = boundary_end(end_index)
        if (
            clip_end - clip_start >= MIN_SEGMENT_SECONDS
            and segment_text
        ):
            result.append(
                {
                    "text": segment_text,
                    "start": clip_start,
                    "end": clip_end,
                    "duration": clip_end - clip_start,
                }
            )
        start_index = end_index + 1
    return result


def run_fingerprint(
    *,
    model: Path,
    seed: int,
    max_segment_seconds: float,
    coverage_min: float,
) -> str:
    payload = {
        "version": CONFIG_VERSION,
        "model": str(model.resolve()),
        "seed": seed,
        "max_segment_seconds": max_segment_seconds,
        "coverage_min": coverage_min,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()


def select_pilot(records: list[Record], per_split: int) -> list[Record]:
    if per_split <= 0:
        return records
    selected: list[Record] = []
    for split in ("train", "validation", "test"):
        selected.extend(
            [r for r in records if r.target_split == split][:per_split]
        )
    return selected
