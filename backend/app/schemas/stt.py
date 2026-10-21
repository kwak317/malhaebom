from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class WordTiming:
    word: str
    start: float
    end: float
    probability: float | None


@dataclass(frozen=True)
class SegmentTranscript:
    start: float
    end: float
    text: str
    words: list[WordTiming] = field(default_factory=list)


@dataclass(frozen=True)
class FillerOccurrence:
    start: float
    end: float
    duration: float
    probability: float | None


@dataclass(frozen=True)
class FillerAnalysis:
    counts: dict[str, int]
    total_count: int
    occurrences: dict[str, list[FillerOccurrence]]


@dataclass(frozen=True)
class SttResult:
    source_id: str
    model: str
    device: str
    compute_type: str
    language: str
    language_probability: float | None
    audio_duration_sec: float
    processing_time_sec: float
    rtf: float | None
    text: str
    fillers: FillerAnalysis
    segments: list[SegmentTranscript]
    words: list[WordTiming]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
