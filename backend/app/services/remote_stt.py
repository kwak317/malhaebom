from __future__ import annotations

from pathlib import Path
from urllib.parse import urlencode

import httpx

from app.schemas.stt import (
    FillerAnalysis,
    FillerOccurrence,
    SegmentTranscript,
    SttResult,
    WordTiming,
)


class RemoteSttTranscriber:
    """Call the IAM-protected GPU service without altering its transcript."""

    def __init__(self, url: str) -> None:
        self.url = url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        identity_url = (
            "http://metadata.google.internal/computeMetadata/v1/"
            "instance/service-accounts/default/identity?"
            + urlencode({"audience": self.url, "format": "full"})
        )
        response = httpx.get(
            identity_url,
            headers={"Metadata-Flavor": "Google"},
            timeout=10.0,
            trust_env=False,
        )
        response.raise_for_status()
        return {"Authorization": "Bearer " + response.text.strip()}

    def warmup(self) -> None:
        response = httpx.get(
            self.url + "/health", headers=self._headers(), timeout=120.0
        )
        response.raise_for_status()
        if response.json().get("device") != "cuda":
            raise RuntimeError("GPU STT service is not ready.")

    def transcribe(
        self, path: Path, source_id: str, *, initial_prompt: str | None = None
    ) -> SttResult:
        data = {"source_id": source_id}
        if initial_prompt and initial_prompt.strip():
            data["initial_prompt"] = initial_prompt.strip()
        with path.open("rb") as audio:
            response = httpx.post(
                self.url + "/transcribe",
                headers=self._headers(),
                data=data,
                files={"audio": (path.name, audio, "application/octet-stream")},
                timeout=httpx.Timeout(300.0, connect=15.0),
            )
        response.raise_for_status()
        payload = response.json()
        if (payload.get("source_id") != source_id
                or payload.get("device") != "cuda"
                or payload.get("compute_type") != "float16"):
            raise RuntimeError("GPU STT response does not match the request.")
        payload["words"] = [WordTiming(**word) for word in payload["words"]]
        payload["segments"] = [
            SegmentTranscript(
                start=segment["start"], end=segment["end"], text=segment["text"],
                words=[WordTiming(**word) for word in segment["words"]],
            )
            for segment in payload["segments"]
        ]
        fillers = payload["fillers"]
        payload["fillers"] = FillerAnalysis(
            counts=fillers["counts"], total_count=fillers["total_count"],
            occurrences={token: [FillerOccurrence(**item) for item in items]
                         for token, items in fillers["occurrences"].items()},
        )
        return SttResult(**payload)
