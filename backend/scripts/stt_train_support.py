#!/usr/bin/env python3
"""Shared dataset, collation, metric, and resume helpers for Whisper QLoRA."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import soundfile as sf
import torch
import torchaudio
from jiwer import cer, wer
from torch.utils.data import Dataset
from transformers import WhisperProcessor
from transformers.trainer_utils import get_last_checkpoint

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def project_path(value: str | Path, *, base: Path = PROJECT_ROOT) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (base / path).resolve()


def read_manifest(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            audio = row.get("audio")
            text = row.get("text")
            if not isinstance(audio, str) or not audio:
                raise ValueError(f"{path}:{line_number}: missing audio")
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"{path}:{line_number}: missing text")
            rows.append(row)
            if limit is not None and len(rows) >= limit:
                break
    if not rows:
        raise ValueError(f"manifest has no rows: {path}")
    return rows


class LazyWhisperDataset(Dataset):
    def __init__(
        self,
        rows: list[dict[str, Any]],
        dataset_root: Path,
        processor: WhisperProcessor,
    ) -> None:
        self.rows = rows
        self.dataset_root = dataset_root
        self.processor = processor

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> dict[str, Any]:
        row = self.rows[index]
        audio_path = project_path(row["audio"], base=self.dataset_root)
        audio, sample_rate = sf.read(audio_path, dtype="float32")
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        if sample_rate != 16000:
            audio_tensor = torch.from_numpy(audio)
            audio = torchaudio.functional.resample(
                audio_tensor, sample_rate, 16000
            ).numpy()
            sample_rate = 16000

        encoded = self.processor.feature_extractor(
            audio,
            sampling_rate=sample_rate,
            return_tensors="pt",
            return_attention_mask=True,
        )
        features = encoded.input_features[0]
        attention_mask = encoded.attention_mask[0]
        labels = self.processor.tokenizer(row["text"]).input_ids
        return {
            "input_features": features,
            "attention_mask": attention_mask,
            "labels": labels,
        }


@dataclass
class WhisperDataCollator:
    processor: WhisperProcessor
    decoder_start_token_id: int

    def __call__(self, features: list[dict[str, Any]]) -> dict[str, torch.Tensor]:
        input_features = [
            {
                "input_features": feature["input_features"],
                "attention_mask": feature["attention_mask"],
            }
            for feature in features
        ]
        batch = self.processor.feature_extractor.pad(
            input_features, return_tensors="pt"
        )

        label_features = [{"input_ids": feature["labels"]} for feature in features]
        labels_batch = self.processor.tokenizer.pad(
            label_features, return_tensors="pt"
        )
        labels = labels_batch["input_ids"].masked_fill(
            labels_batch.attention_mask.ne(1), -100
        )

        if (
            labels.shape[1]
            and (labels[:, 0] == self.decoder_start_token_id).all().item()
        ):
            labels = labels[:, 1:]
        batch["labels"] = labels
        return batch


def normalized_metrics(
    processor: WhisperProcessor, prediction_ids: Any, label_ids: Any
) -> dict[str, float]:
    if isinstance(prediction_ids, tuple):
        prediction_ids = prediction_ids[0]
    labels = label_ids.copy()
    labels[labels == -100] = processor.tokenizer.pad_token_id
    predictions = processor.tokenizer.batch_decode(
        prediction_ids, skip_special_tokens=True
    )
    references = processor.tokenizer.batch_decode(labels, skip_special_tokens=True)
    return {
        "cer": cer(references, predictions),
        "wer": wer(references, predictions),
    }


def check_audio_exists(rows: list[dict[str, Any]], dataset_root: Path) -> None:
    missing = [
        str(project_path(row["audio"], base=dataset_root))
        for row in rows
        if not project_path(row["audio"], base=dataset_root).is_file()
    ]
    if missing:
        raise FileNotFoundError(
            f"missing {len(missing)} audio files; first={missing[0]}"
        )


def resolve_resume(output_dir: Path, value: str) -> str | None:
    if value == "none":
        return None
    if value == "auto":
        return get_last_checkpoint(str(output_dir)) if output_dir.exists() else None
    path = project_path(value)
    if not path.is_dir():
        raise FileNotFoundError(f"resume checkpoint not found: {path}")
    return str(path)
