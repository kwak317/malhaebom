#!/usr/bin/env python3
"""Reconstruct handoff STT segment WAVs from approved AI Hub dataset 119 archives.

The handoff manifests contain rows such as::

    {"audio": "dataset/train/audio/DKSR20000718_1_1_1.wav",
     "text": "어떤 동물 키우세요?"}

AI Hub stores one long WAV per conversation (for example DKSR20000718.wav) and
its label JSON stores utterance ids such as DKSR20000718.1.1.1 with start/end
seconds.  This script validates that mapping and materializes only the segments
referenced by the supplied handoff manifests.

AI Hub source/label archives and generated WAVs stay under ignored data paths;
only this reconstruction code is intended for Git.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import shutil
import sys
import unicodedata
import wave
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AIHUB_ROOT = PROJECT_ROOT / "data" / "stt" / "aihub" / "119"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "data" / "stt" / "handoff-reconstructed"

SOURCE_ID_RE = re.compile(r"^(DKSR\d{8})_(.+)\.wav$", re.IGNORECASE)

ARCHIVE_PATTERNS = {
    "train": {
        "label": "*(비식별화완료)경상도_학습데이터_1.zip",
        "source": "*(비식별화완료)경상도_1.zip",
    },
    "validation": {
        "label": "*(비식별화완료)경상도_학습데이터_2.zip",
        "source": "*(비식별화완료)경상도_2.zip",
    },
}


@dataclass(frozen=True)
class ManifestRow:
    split: str
    line_number: int
    audio: str
    text: str
    filename: str
    source_id: str
    utterance_id: str


@dataclass(frozen=True)
class Utterance:
    utterance_id: str
    start: float
    end: float
    form: str
    dialect_form: str
    standard_form: str


@dataclass
class ValidationResult:
    rows: int = 0
    source_ids: int = 0
    missing_label_sources: int = 0
    missing_source_wavs: int = 0
    missing_utterances: int = 0
    invalid_timings: int = 0
    text_mismatches: int = 0

    @property
    def structural_ok(self) -> bool:
        return not any(
            (
                self.missing_label_sources,
                self.missing_source_wavs,
                self.missing_utterances,
                self.invalid_timings,
            )
        )


def resolve_path(path: Path) -> Path:
    path = path.expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


def find_archive(root: Path, pattern: str) -> Path:
    matches = list(root.rglob(pattern))
    if not matches:
        raise FileNotFoundError(f"AI Hub archive not found under {root}: {pattern}")
    if len(matches) > 1:
        rendered = "\n  ".join(str(path) for path in matches)
        raise RuntimeError(f"Expected one archive for {pattern}, found {len(matches)}:\n  {rendered}")
    return matches[0]


def parse_audio_name(audio: str) -> tuple[str, str, str]:
    filename = Path(audio.replace("\\", "/")).name
    match = SOURCE_ID_RE.match(filename)
    if not match:
        raise ValueError(
            f"Unsupported handoff audio filename {filename!r}; expected DKSR########_...wav"
        )
    source_id = match.group(1).upper()
    utterance_id = source_id + "." + match.group(2).replace("_", ".")
    return filename, source_id, utterance_id


def load_manifest(path: Path, split: str) -> list[ManifestRow]:
    rows: list[ManifestRow] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            if not raw_line.strip():
                continue
            try:
                payload = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            audio = payload.get("audio")
            text = payload.get("text")
            if not isinstance(audio, str) or not isinstance(text, str):
                raise ValueError(f"{path}:{line_number}: expected string audio/text fields")
            filename, source_id, utterance_id = parse_audio_name(audio)
            rows.append(
                ManifestRow(
                    split=split,
                    line_number=line_number,
                    audio=audio.replace("\\", "/"),
                    text=text,
                    filename=filename,
                    source_id=source_id,
                    utterance_id=utterance_id,
                )
            )
    if not rows:
        raise ValueError(f"Manifest is empty: {path}")
    return rows


def normalize_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split())


def zip_members_by_stem(archive: Path, suffix: str) -> dict[str, str]:
    members: dict[str, str] = {}
    with zipfile.ZipFile(archive) as zf:
        for name in zf.namelist():
            if not name.lower().endswith(suffix.lower()):
                continue
            stem = Path(name).stem.upper()
            if stem in members:
                raise RuntimeError(f"Duplicate {suffix} stem {stem} in {archive}")
            members[stem] = name
    return members


def load_target_labels(
    label_archive: Path,
    source_ids: set[str],
) -> tuple[dict[str, dict[str, Utterance]], set[str]]:
    label_members = zip_members_by_stem(label_archive, ".json")
    missing_sources = source_ids - set(label_members)
    labels: dict[str, dict[str, Utterance]] = {}

    with zipfile.ZipFile(label_archive) as zf:
        for source_id in sorted(source_ids - missing_sources):
            payload = json.loads(zf.read(label_members[source_id]))
            utterances: dict[str, Utterance] = {}
            for raw in payload.get("utterance", []):
                utterance_id = str(raw.get("id", ""))
                if not utterance_id:
                    continue
                try:
                    start = float(raw["start"])
                    end = float(raw["end"])
                except (KeyError, TypeError, ValueError):
                    continue
                utterances[utterance_id] = Utterance(
                    utterance_id=utterance_id,
                    start=start,
                    end=end,
                    form=str(raw.get("form", "")),
                    dialect_form=str(raw.get("dialect_form", raw.get("form", ""))),
                    standard_form=str(raw.get("standard_form", "")),
                )
            labels[source_id] = utterances
    return labels, missing_sources


def validate_split(
    split: str,
    rows: Sequence[ManifestRow],
    label_archive: Path,
    source_archive: Path,
    *,
    max_examples: int = 10,
) -> tuple[ValidationResult, dict[str, dict[str, Utterance]], dict[str, str]]:
    source_ids = {row.source_id for row in rows}
    labels, missing_label_sources = load_target_labels(label_archive, source_ids)
    source_members = zip_members_by_stem(source_archive, ".wav")
    missing_source_wavs = source_ids - set(source_members)

    result = ValidationResult(
        rows=len(rows),
        source_ids=len(source_ids),
        missing_label_sources=len(missing_label_sources),
        missing_source_wavs=len(missing_source_wavs),
    )
    examples: list[str] = []

    for row in rows:
        utterance = labels.get(row.source_id, {}).get(row.utterance_id)
        if utterance is None:
            result.missing_utterances += 1
            if len(examples) < max_examples:
                examples.append(f"missing utterance: {row.utterance_id} ({row.audio})")
            continue
        if utterance.start < 0 or utterance.end <= utterance.start:
            result.invalid_timings += 1
            if len(examples) < max_examples:
                examples.append(
                    f"invalid timing: {row.utterance_id} start={utterance.start} end={utterance.end}"
                )
        # The handed-off manifests were produced from AI Hub's dialect_form,
        # not from form.  form may retain dual annotations such as
        # "(쫌)/(조금)", whereas dialect_form contains the spoken/dialect
        # transcription used by the Whisper training manifest.
        if normalize_text(row.text) != normalize_text(utterance.dialect_form):
            result.text_mismatches += 1
            if len(examples) < max_examples:
                examples.append(
                    f"text mismatch: {row.utterance_id}\n"
                    f"  manifest={row.text!r}\n  dialect_form={utterance.dialect_form!r}\n"
                    f"  form={utterance.form!r}"
                )

    print(f"[{split}] manifest rows={result.rows:,} source conversations={result.source_ids:,}")
    print(
        f"[{split}] missing label sources={result.missing_label_sources} "
        f"missing source WAVs={result.missing_source_wavs} "
        f"missing utterances={result.missing_utterances} "
        f"invalid timings={result.invalid_timings} text mismatches={result.text_mismatches}"
    )
    for example in examples:
        print(f"[{split}] {example}")

    return result, labels, source_members


def write_segment(
    *,
    source_params: wave._wave_params,
    source_frames: bytes,
    sample_rate: int,
    utterance: Utterance,
    destination: Path,
) -> None:
    start_frame = max(0, round(utterance.start * sample_rate))
    end_frame = min(source_params.nframes, round(utterance.end * sample_rate))
    if end_frame <= start_frame:
        raise ValueError(
            f"Empty segment {utterance.utterance_id}: frames {start_frame}..{end_frame}"
        )
    bytes_per_frame = source_params.sampwidth * source_params.nchannels
    clip = source_frames[start_frame * bytes_per_frame : end_frame * bytes_per_frame]
    destination.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(destination), "wb") as target:
        target.setparams(source_params)
        target.setnframes(0)
        target.writeframes(clip)


def reconstruct_split(
    split: str,
    rows: Sequence[ManifestRow],
    labels: dict[str, dict[str, Utterance]],
    source_archive: Path,
    source_members: dict[str, str],
    output_root: Path,
    *,
    overwrite: bool,
) -> tuple[int, int]:
    grouped: dict[str, list[ManifestRow]] = defaultdict(list)
    for row in rows:
        grouped[row.source_id].append(row)

    written = 0
    skipped = 0
    with zipfile.ZipFile(source_archive) as zf:
        for source_index, source_id in enumerate(sorted(grouped), start=1):
            source_rows = grouped[source_id]
            member = source_members[source_id]
            print(
                f"[{split}] source {source_index}/{len(grouped)} {source_id}: "
                f"{len(source_rows)} segment(s)",
                flush=True,
            )
            source_bytes = zf.read(member)
            with wave.open(io.BytesIO(source_bytes), "rb") as source_wav:
                params = source_wav.getparams()
                if params.comptype != "NONE":
                    raise ValueError(
                        f"Unsupported compressed WAV {source_id}: comptype={params.comptype}"
                    )
                sample_rate = source_wav.getframerate()
                source_frames = source_wav.readframes(source_wav.getnframes())

            for row in source_rows:
                destination = output_root / row.audio
                if destination.exists() and not overwrite:
                    skipped += 1
                    continue
                utterance = labels[source_id][row.utterance_id]
                write_segment(
                    source_params=params,
                    source_frames=source_frames,
                    sample_rate=sample_rate,
                    utterance=utterance,
                    destination=destination,
                )
                written += 1

    return written, skipped


def copy_manifest(source: Path, split: str, output_root: Path) -> Path:
    destination = output_root / "dataset" / f"{split}.jsonl"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return destination


def selected_splits(args: argparse.Namespace) -> Iterable[tuple[str, Path]]:
    if args.split in {"train", "all"}:
        if args.train_manifest is None:
            raise SystemExit("--train-manifest is required for --split train/all")
        yield "train", resolve_path(args.train_manifest)
    if args.split in {"validation", "all"}:
        if args.validation_manifest is None:
            raise SystemExit("--validation-manifest is required for --split validation/all")
        yield "validation", resolve_path(args.validation_manifest)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-manifest", type=Path, help="handoff train.jsonl")
    parser.add_argument("--validation-manifest", type=Path, help="handoff validation.jsonl")
    parser.add_argument("--split", choices=("train", "validation", "all"), default="all")
    parser.add_argument("--aihub-root", type=Path, default=DEFAULT_AIHUB_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--build",
        action="store_true",
        help="Materialize WAV segments after validation. Without this flag, verify only.",
    )
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--allow-text-mismatch",
        action="store_true",
        help="Allow normalized manifest text to differ from AI Hub label form.",
    )
    args = parser.parse_args()

    aihub_root = resolve_path(args.aihub_root)
    output_root = resolve_path(args.output_root)
    failures = False

    for split, manifest_path in selected_splits(args):
        if not manifest_path.is_file():
            raise SystemExit(f"Manifest not found: {manifest_path}")
        label_archive = find_archive(aihub_root, ARCHIVE_PATTERNS[split]["label"])
        source_archive = find_archive(aihub_root, ARCHIVE_PATTERNS[split]["source"])
        rows = load_manifest(manifest_path, split)
        result, labels, source_members = validate_split(
            split,
            rows,
            label_archive,
            source_archive,
        )

        split_ok = result.structural_ok and (
            args.allow_text_mismatch or result.text_mismatches == 0
        )
        if not split_ok:
            failures = True
            print(f"[{split}] validation FAILED", file=sys.stderr)
            continue

        print(f"[{split}] validation PASSED")
        if args.build:
            written, skipped = reconstruct_split(
                split,
                rows,
                labels,
                source_archive,
                source_members,
                output_root,
                overwrite=args.overwrite,
            )
            copied_manifest = copy_manifest(manifest_path, split, output_root)
            print(
                f"[{split}] build complete: written={written:,} skipped={skipped:,} "
                f"manifest={copied_manifest}"
            )

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
