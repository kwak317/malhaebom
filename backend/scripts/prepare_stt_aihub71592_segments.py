#!/usr/bin/env python3
"""Build aligned <=25 s ASR segments from AI Hub 71592 ICT/New interview answers."""

from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from dataclasses import asdict
from pathlib import Path

from stt_aihub71592_support import (
    REQUIRED_CT2,
    aligned_reference_times,
    make_segments,
    run_fingerprint,
    scan_records,
    select_pilot,
)
from stt_aihub71592_audio import read_pcm16, write_clip

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AIHUB_ROOT = PROJECT_ROOT / "data/stt/aihub/71592"
OUTPUT_ROOT = PROJECT_ROOT / "data/stt/aihub71592-ict-new-segmented"
ALIGN_MODEL = (
    PROJECT_ROOT
    / "artifacts/stt/whisper-medium-busan-qlora-clean-cont-lr2e-5-ct2"
)
SEED = 20260921
MAX_SEGMENT_SECONDS = 24.0
ALIGNMENT_COVERAGE_MIN = 0.70


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--aihub-root", type=Path, default=AIHUB_ROOT)
    p.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    p.add_argument("--align-model", type=Path, default=ALIGN_MODEL)
    p.add_argument("--seed", type=int, default=SEED)
    p.add_argument(
        "--max-segment-seconds",
        type=float,
        default=MAX_SEGMENT_SECONDS,
    )
    p.add_argument(
        "--coverage-min",
        type=float,
        default=ALIGNMENT_COVERAGE_MIN,
    )
    p.add_argument("--pilot-records-per-split", type=int, default=0)
    p.add_argument("--preflight-only", action="store_true")
    p.add_argument("--overwrite", action="store_true")
    return p.parse_args()


def serializable_record(record: object) -> dict[str, object]:
    raw = asdict(record)
    raw["source_zip"] = str(raw["source_zip"])
    raw["label_zip"] = str(raw["label_zip"])
    return raw


def validate_inputs(args: argparse.Namespace) -> tuple[list[object], dict]:
    records, summary = scan_records(args.aihub_root, args.seed)
    if summary["missing_answer_audio"]:
        raise RuntimeError(
            f"missing answer audio: {summary['missing_answer_audio'][:3]}"
        )
    if len(records) != 5840:
        raise RuntimeError(
            f"expected 5840 valid records, found {len(records)}"
        )
    for filename in REQUIRED_CT2:
        if not (args.align_model / filename).is_file():
            raise FileNotFoundError(args.align_model / filename)
    return records, summary


def write_final_manifests(
    output_root: Path,
    accepted: list[dict[str, object]],
    rejected: list[dict[str, object]],
    *,
    metadata: dict[str, object],
) -> None:
    accepted.sort(
        key=lambda row: (
            str(row["split"]),
            str(row["source_id"]),
            float(row["start"]),
        )
    )
    for split in ("train", "validation", "test"):
        path = output_root / f"{split}.jsonl"
        rows = [row for row in accepted if row["split"] == split]
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(
                    json.dumps(row, ensure_ascii=False) + "\n"
                )
    with (output_root / "rejected-records.jsonl").open(
        "w", encoding="utf-8"
    ) as handle:
        for row in rejected:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    (output_root / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    args.aihub_root = args.aihub_root.resolve()
    args.output_root = args.output_root.resolve()
    args.align_model = args.align_model.resolve()

    records, summary = validate_inputs(args)
    chosen = select_pilot(records, args.pilot_records_per_split)
    fingerprint = run_fingerprint(
        model=args.align_model,
        seed=args.seed,
        max_segment_seconds=args.max_segment_seconds,
        coverage_min=args.coverage_min,
    )
    preflight = {
        **summary,
        "selected_records": len(chosen),
        "align_model": str(args.align_model),
        "output_root": str(args.output_root),
        "seed": args.seed,
        "max_segment_seconds": args.max_segment_seconds,
        "coverage_min": args.coverage_min,
        "fingerprint": fingerprint,
    }
    print(json.dumps(preflight, ensure_ascii=False, indent=2))
    if args.preflight_only:
        print("AI Hub 71592 segmentation preflight PASSED")
        return 0

    if args.overwrite and args.output_root.exists():
        shutil.rmtree(args.output_root)
    args.output_root.mkdir(parents=True, exist_ok=True)
    record_dir = args.output_root / "records"
    record_dir.mkdir(exist_ok=True)

    from faster_whisper import WhisperModel
    import numpy as np

    model = WhisperModel(
        str(args.align_model),
        device="cuda",
        compute_type="float16",
    )
    source_handles: dict[Path, zipfile.ZipFile] = {}
    accepted: list[dict[str, object]] = []
    rejected: list[dict[str, object]] = []

    try:
        for number, record in enumerate(chosen, start=1):
            state_path = record_dir / f"{record.source_id}.json"
            if state_path.is_file():
                state = json.loads(
                    state_path.read_text(encoding="utf-8")
                )
                if state.get("fingerprint") != fingerprint:
                    raise RuntimeError(
                        f"resume fingerprint mismatch: {state_path}"
                    )
                if state.get("status") == "accepted":
                    accepted.extend(state.get("segments", []))
                else:
                    rejected.append(state)
                print(
                    f"[resume] {number}/{len(chosen)} "
                    f"{record.source_id}"
                )
                continue

            if record.source_zip not in source_handles:
                source_handles[record.source_zip] = zipfile.ZipFile(
                    record.source_zip
                )
            samples, sample_rate = read_pcm16(
                source_handles[record.source_zip],
                record.audio_member,
            )
            if sample_rate != 16000:
                raise RuntimeError(
                    f"{record.source_id}: expected 16 kHz, "
                    f"got {sample_rate}"
                )
            audio = samples.astype(np.float32) / 32768.0
            audio_duration = len(samples) / sample_rate

            try:
                transcribed, _ = model.transcribe(
                    audio,
                    language="ko",
                    task="transcribe",
                    beam_size=1,
                    temperature=0.0,
                    condition_on_previous_text=False,
                    vad_filter=False,
                    word_timestamps=True,
                )
                words: list[tuple[str, float, float]] = []
                for segment in transcribed:
                    for word in segment.words or []:
                        words.append(
                            (
                                word.word,
                                float(word.start),
                                float(word.end),
                            )
                        )
            except IndexError as exc:
                state = {
                    "fingerprint": fingerprint,
                    "status": "rejected",
                    "reason": "word_timestamp_alignment_error",
                    "error_type": type(exc).__name__,
                    "record": serializable_record(record),
                }
                state_path.write_text(
                    json.dumps(state, ensure_ascii=False, indent=2)
                    + "\n",
                    encoding="utf-8",
                )
                rejected.append(state)
                print(
                    f"[reject] {number}/{len(chosen)} "
                    f"{record.source_id} word_timestamp_alignment_error"
                )
                continue

            ref_times, positions, coverage = aligned_reference_times(
                record.transcript,
                words,
                audio_duration,
            )
            if coverage < args.coverage_min or not ref_times:
                state = {
                    "fingerprint": fingerprint,
                    "status": "rejected",
                    "reason": "low_alignment_coverage",
                    "coverage": coverage,
                    "record": serializable_record(record),
                }
                state_path.write_text(
                    json.dumps(
                        state, ensure_ascii=False, indent=2
                    )
                    + "\n",
                    encoding="utf-8",
                )
                rejected.append(state)
                print(
                    f"[reject] {number}/{len(chosen)} "
                    f"{record.source_id} coverage={coverage:.3f}"
                )
                continue

            planned = make_segments(
                record.transcript,
                ref_times,
                positions,
                audio_duration,
                args.max_segment_seconds,
            )
            rows: list[dict[str, object]] = []
            for index, item in enumerate(planned, start=1):
                name = f"{record.source_id}_s{index:02d}.wav"
                destination = (
                    args.output_root
                    / "audio"
                    / record.target_split
                    / name
                )
                write_clip(
                    samples,
                    sample_rate,
                    float(item["start"]),
                    float(item["end"]),
                    destination,
                )
                rows.append(
                    {
                        "audio": str(
                            destination.relative_to(args.output_root)
                        ),
                        "text": item["text"],
                        "source_id": record.source_id,
                        "segment_id": (
                            f"{record.source_id}_s{index:02d}"
                        ),
                        "split": record.target_split,
                        "gender": record.gender,
                        "alignment_coverage": coverage,
                        "start": item["start"],
                        "end": item["end"],
                        "duration": item["duration"],
                        "dataset": "aihub71592_ict_new",
                    }
                )

            if rows:
                state = {
                    "fingerprint": fingerprint,
                    "status": "accepted",
                    "coverage": coverage,
                    "source_id": record.source_id,
                    "target_split": record.target_split,
                    "segments": rows,
                }
                accepted.extend(rows)
            else:
                state = {
                    "fingerprint": fingerprint,
                    "status": "rejected",
                    "reason": "no_valid_segments",
                    "coverage": coverage,
                    "record": serializable_record(record),
                }
                rejected.append(state)
            state_path.write_text(
                json.dumps(state, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(
                f"{number}/{len(chosen)} {record.source_id}: "
                f"coverage={coverage:.3f} segments={len(rows)}"
            )
    finally:
        for handle in source_handles.values():
            handle.close()

    metadata = {
        "fingerprint": fingerprint,
        "records_requested": len(chosen),
        "records_rejected": len(rejected),
        "segments": len(accepted),
        "segments_by_split": {
            split: sum(row["split"] == split for row in accepted)
            for split in ("train", "validation", "test")
        },
        "hours_by_split": {
            split: round(
                sum(
                    float(row["duration"])
                    for row in accepted
                    if row["split"] == split
                )
                / 3600,
                3,
            )
            for split in ("train", "validation", "test")
        },
        "alignment": {
            "model": str(args.align_model),
            "beam_size": 1,
            "word_timestamps": True,
            "coverage_min": args.coverage_min,
            "max_segment_seconds": args.max_segment_seconds,
            "shared_midpoint_boundaries": True,
        },
        "split_note": (
            "AI Hub Training remains train. AI Hub Validation is "
            "deterministically split 50/50 by record id into "
            "validation/test; labels expose no verified speaker id, "
            "so speaker-disjointness cannot be guaranteed."
        ),
    }
    write_final_manifests(
        args.output_root,
        accepted,
        rejected,
        metadata=metadata,
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
