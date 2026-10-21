from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class SpeechSegment:
    start: float
    end: float


@dataclass(frozen=True)
class LongSilence:
    start: float
    end: float
    duration: float


@dataclass(frozen=True)
class RepeatedExpression:
    word: str
    first_start: float
    second_start: float


@dataclass(frozen=True)
class SoftEnding:
    expression: str
    start: float
    end: float
    suggestion: str


@dataclass(frozen=True)
class DeliveryMetrics:
    answer_duration_sec: float
    speech_duration_sec: float
    cpm: float | None
    long_silences: list[LongSilence] = field(default_factory=list)
    repetitions: list[RepeatedExpression] = field(default_factory=list)
    soft_endings: list[SoftEnding] = field(default_factory=list)


@dataclass(frozen=True)
class FeedbackItem:
    code: str
    evidence: str
    action: str


@dataclass(frozen=True)
class DeliveryAnalysisResult:
    source_id: str
    metrics: DeliveryMetrics
    feedback: list[FeedbackItem]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
