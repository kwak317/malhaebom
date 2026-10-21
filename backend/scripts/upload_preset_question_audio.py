from __future__ import annotations

import argparse
import hashlib
import json
import sys
import wave
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence

import httpx


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.supabase_settings import SupabaseSettings, SupabaseSettingsError
from app.services.preset_question_audio import PRESET_QUESTION_BUCKET_ID


class UploadValidationError(RuntimeError):
    pass


class UploadError(RuntimeError):
    pass


@dataclass(frozen=True)
class UploadSource:
    question_number: int
    content: bytes
    sample_rate: int
    channels: int
    sample_width: int
    sha256: str


@dataclass(frozen=True)
class UploadResult:
    question_number: int
    content_bytes: int
    sample_rate: int
    channels: int
    sample_width: int
    sha256: str


def asset_id(question_number: int) -> str:
    return f"questioner-preset-{question_number:02d}-v1"


def object_key(question_number: int) -> str:
    return f"questioner/{asset_id(question_number)}.wav"


def validate_source_directory(source_dir: Path) -> list[UploadSource]:
    if not source_dir.is_dir():
        raise UploadValidationError("입력 WAV 폴더를 찾을 수 없습니다.")

    sources: list[UploadSource] = []
    for question_number in range(1, 11):
        path = source_dir / f"question_{question_number:02d}.wav"
        if not path.is_file():
            raise UploadValidationError("필수 질문 WAV가 없습니다.")
        try:
            content = path.read_bytes()
            with wave.open(str(path), "rb") as audio:
                channels = audio.getnchannels()
                sample_width = audio.getsampwidth()
                sample_rate = audio.getframerate()
                frame_count = audio.getnframes()
        except (OSError, wave.Error) as error:
            raise UploadValidationError("입력 WAV를 읽을 수 없습니다.") from error
        if (
            not content
            or channels != 1
            or sample_width != 2
            or sample_rate != 24_000
            or frame_count <= 0
        ):
            raise UploadValidationError("입력 WAV 형식이 올바르지 않습니다.")
        sources.append(
            UploadSource(
                question_number=question_number,
                content=content,
                sample_rate=sample_rate,
                channels=channels,
                sample_width=sample_width,
                sha256=hashlib.sha256(content).hexdigest(),
            )
        )
    return sources


class PresetQuestionUploader:
    def __init__(self, settings: SupabaseSettings, http_client: httpx.Client | Any | None = None) -> None:
        if not settings.service_role_key:
            raise UploadError("업로드용 서버 설정이 없습니다.")
        self.settings = settings
        self.http = http_client or httpx.Client(timeout=20.0)

    def upload_source_directory(self, source_dir: Path) -> list[UploadResult]:
        sources = validate_source_directory(source_dir)
        uploaded_question_numbers: list[int] = []
        try:
            for source in sources:
                self._upload(source)
                uploaded_question_numbers.append(source.question_number)
        except UploadError:
            self._cleanup_uploaded(uploaded_question_numbers)
            raise

        return [
            UploadResult(
                question_number=source.question_number,
                content_bytes=len(source.content),
                sample_rate=source.sample_rate,
                channels=source.channels,
                sample_width=source.sample_width,
                sha256=source.sha256,
            )
            for source in sources
        ]

    def _upload(self, source: UploadSource) -> None:
        self._request(
            "POST",
            f"/storage/v1/object/{PRESET_QUESTION_BUCKET_ID}/{object_key(source.question_number)}",
            headers={"Content-Type": "audio/wav", "x-upsert": "false"},
            content=source.content,
            expected=(200, 201),
        )

    def _cleanup_uploaded(self, uploaded_question_numbers: list[int]) -> None:
        for question_number in reversed(uploaded_question_numbers):
            try:
                self._request(
                    "DELETE",
                    f"/storage/v1/object/{PRESET_QUESTION_BUCKET_ID}",
                    json={"prefixes": [object_key(question_number)]},
                )
            except UploadError:
                pass

    def _request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        expected: tuple[int, ...] = (200, 201, 204),
        **kwargs: Any,
    ) -> None:
        request_headers = {
            "apikey": self.settings.service_role_key or "",
            "Authorization": f"Bearer {self.settings.service_role_key}",
        }
        if headers:
            request_headers.update(headers)
        try:
            response = self.http.request(
                method,
                f"{self.settings.url}{path}",
                headers=request_headers,
                **kwargs,
            )
        except httpx.HTTPError as error:
            raise UploadError("비공개 Storage 요청에 실패했습니다.") from error
        if response.status_code not in expected:
            raise UploadError("비공개 Storage 요청에 실패했습니다.")


def write_upload_summary(results: list[UploadResult], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"preset-question-audio-upload-{timestamp}.json"
    output_path.write_text(
        json.dumps(
            {
                "uploadedAt": timestamp,
                "success": True,
                "files": [
                    {
                        "questionNumber": result.question_number,
                        "sampleRate": result.sample_rate,
                        "channels": result.channels,
                        "sampleWidth": result.sample_width,
                        "bytes": result.content_bytes,
                        "sha256": result.sha256,
                    }
                    for result in results
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return output_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Upload reviewed preset-question WAV files to private Storage.")
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--result-dir", type=Path, default=Path("local-results"))
    args = parser.parse_args(argv)
    try:
        settings = SupabaseSettings.from_env(require_service_role=True)
        results = PresetQuestionUploader(settings).upload_source_directory(args.source_dir)
        write_upload_summary(results, args.result_dir)
    except (SupabaseSettingsError, UploadValidationError, UploadError):
        print("preset question audio upload failed")
        return 1
    print(f"preset question audio upload completed: count={len(results)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
