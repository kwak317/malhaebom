#!/usr/bin/env python3
"""Create a source-disjoint STT holdout test set from AI Hub validation archives."""

from __future__ import annotations

import argparse
import io
import json
import re
import wave
import zipfile
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET_ROOT = PROJECT_ROOT / "data" / "stt" / "handoff-reconstructed"
AIHUB_ROOT = (
    PROJECT_ROOT
    / "data"
    / "stt"
    / "aihub"
    / "119"
    / "014.한국어_방언_발화_데이터(경상도)"
    / "01.데이터"
)
DEFAULT_AUDIO_ZIP = (
    AIHUB_ROOT
    / "2.Validation"
    / "(new3)원천데이터"
    / "(비식별화완료)경상도_2.zip"
)
DEFAULT_LABEL_ZIP = (
    AIHUB_ROOT
    / "2.Validation"
    / "(new3)라벨링데이터"
    / "(비식별화완료)경상도_학습데이터_2.zip"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "stt" / "holdout-test"

SOURCE_RE = re.compile(r"(DKSR\d+)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--audio-zip", type=Path, default=DEFAULT_AUDIO_ZIP)
    parser.add_argument("--label-zip", type=Path, default=DEFAULT_LABEL_ZIP)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--source-count", type=int, default=20)
    parser.add_argument("--utterances-per-source", type=int, default=25)
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Print deterministic source selection without extracting WAV clips.",
    )
    return parser.parse_args()


def used_sources(manifest: Path) -> set[str]:
    sources: set[str] = set()
    with manifest.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            match = SOURCE_RE.search(str(row.get("audio", "")))
            if not match:
                raise ValueError(f"cannot infer source id from {row.get('audio')}")
            sources.add(match.group(1))
    return sources


def available_source_ids(
    label_zip: zipfile.ZipFile, audio_zip: zipfile.ZipFile
) -> list[str]:
    labels = {
        Path(name).stem
        for name in label_zip.namelist()
        if name.lower().endswith(".json")
    }
    audio = {
        Path(name).stem
        for name in audio_zip.namelist()
        if name.lower().endswith(".wav")
    }
    return sorted(labels & audio)


def extract_source(
    source_id: str,
    audio_zip: zipfile.ZipFile,
    label_zip: zipfile.ZipFile,
    output_audio: Path,
    utterance_limit: int,
) -> list[dict[str, Any]]:
    label = json.loads(label_zip.read(f"{source_id}.json"))
    source_audio = audio_zip.read(f"{source_id}.wav")

    with wave.open(io.BytesIO(source_audio), "rb") as source_wav:
        params = source_wav.getparams()
        sample_rate = source_wav.getframerate()
        if params.comptype != "NONE":
            raise ValueError(
                f"{source_id}: unsupported WAV compression {params.comptype}"
            )
        frames = source_wav.readframes(source_wav.getnframes())

    bytes_per_frame = params.sampwidth * params.nchannels
    rows: list[dict[str, Any]] = []
    for utterance in label.get("utterance", [])[:utterance_limit]:
        start_frame = round(float(utterance["start"]) * sample_rate)
        end_frame = round(float(utterance["end"]) * sample_rate)
        clip = frames[
            start_frame * bytes_per_frame : end_frame * bytes_per_frame
        ]
        utterance_id = str(utterance["id"])
        safe_id = utterance_id.replace(".", "_")
        filename = f"{safe_id}.wav"
        with wave.open(str(output_audio / filename), "wb") as clip_wav:
            clip_wav.setparams(params)
            clip_wav.writeframes(clip)

        reference = (
            utterance.get("dialect_form")
            or utterance.get("form")
            or utterance.get("standard_form")
        )
        rows.append(
            {
                "id": utterance_id,
                "source_id": source_id,
                "audio": f"audio/{filename}",
                "reference": reference,
                "standard_reference": utterance.get("standard_form"),
                "start": utterance["start"],
                "end": utterance["end"],
            }
        )
    return rows


def main() -> int:
    args = parse_args()
    dataset_root = args.dataset_root.resolve()
    train_manifest = dataset_root / "dataset" / "train.jsonl"
    validation_manifest = dataset_root / "dataset" / "validation.jsonl"

    used_train = used_sources(train_manifest)
    used_validation = used_sources(validation_manifest)
    used = used_train | used_validation

    with zipfile.ZipFile(args.audio_zip) as audio_zip, zipfile.ZipFile(
        args.label_zip
    ) as label_zip:
        candidates = [
            source_id
            for source_id in available_source_ids(label_zip, audio_zip)
            if source_id not in used
        ]
        if len(candidates) < args.source_count:
            raise RuntimeError(
                f"only {len(candidates)} source-disjoint candidates; "
                f"need {args.source_count}"
            )
        selected = candidates[: args.source_count]

        plan = {
            "train_sources": len(used_train),
            "validation_sources": len(used_validation),
            "used_source_union": len(used),
            "eligible_validation_sources": len(candidates),
            "selected_sources": selected,
            "source_count": len(selected),
            "utterances_per_source": args.utterances_per_source,
        }
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        if args.plan_only:
            print("STT holdout source plan PASSED")
            return 0

        output = args.output.resolve()
        if output.exists() and any(output.iterdir()):
            raise RuntimeError(
                f"holdout output is not empty: {output}; "
                "do not silently replace a fixed final test set"
            )
        output_audio = output / "audio"
        output_audio.mkdir(parents=True, exist_ok=True)

        rows: list[dict[str, Any]] = []
        for source_id in selected:
            rows.extend(
                extract_source(
                    source_id,
                    audio_zip,
                    label_zip,
                    output_audio,
                    args.utterances_per_source,
                )
            )

    selected_sources = {row["source_id"] for row in rows}
    overlap = selected_sources & used
    if overlap:
        raise RuntimeError(f"holdout source leakage detected: {sorted(overlap)}")

    manifest = output / "manifest.jsonl"
    with manifest.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    metadata = {
        **plan,
        "rows": len(rows),
        "source_overlap_with_train_validation": 0,
        "source_archive": str(args.audio_zip),
        "label_archive": str(args.label_zip),
        "reference_policy": "dialect_form -> form -> standard_form",
    }
    (output / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"created holdout: {len(rows)} utterances -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
