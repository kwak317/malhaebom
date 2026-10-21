"""Generate the ten reviewed preset-question WAV assets through the local TTS worker."""

from __future__ import annotations

import argparse
import json
import sys
import wave
from pathlib import Path
from typing import Any, Sequence

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = PROJECT_ROOT / "configs" / "tts" / "tts_template_catalog.json"


def preset_questions(catalog_path: Path) -> list[tuple[int, str]]:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    questions: list[tuple[int, str]] = []
    for item in catalog["templates"]:
        question_id = str(item.get("questionId", ""))
        if (
            item.get("speakerRole") == "questioner"
            and item.get("qcStatus") == "accepted"
            and item.get("isPrimary") is True
            and question_id.startswith("preset-")
        ):
            questions.append((int(question_id.removeprefix("preset-")), str(item["displayText"])))
    questions.sort()
    if [number for number, _text in questions] != list(range(1, 11)):
        raise ValueError("기본 질문 10개 카탈로그가 올바르지 않습니다.")
    return questions


def validate_wav(path: Path) -> None:
    with wave.open(str(path), "rb") as audio:
        if (
            audio.getnchannels() != 1
            or audio.getsampwidth() != 2
            or audio.getframerate() != 24_000
            or audio.getnframes() <= 0
        ):
            raise ValueError(f"WAV 형식이 올바르지 않습니다: {path.name}")


def generate(output_dir: Path, worker_url: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    questions = preset_questions(CATALOG_PATH)
    with httpx.Client(timeout=120.0) as client:
        for number, text in questions:
            output_path = output_dir / f"question_{number:02d}.wav"
            if output_path.exists():
                raise FileExistsError(f"기존 WAV를 덮어쓸 수 없습니다: {output_path}")
            response = client.post(f"{worker_url.rstrip('/')}/internal/tts", json={"question": text})
            response.raise_for_status()
            if not response.headers.get("content-type", "").startswith("audio/wav") or not response.content:
                raise RuntimeError(f"질문 {number:02d}의 TTS 응답 형식이 올바르지 않습니다.")
            output_path.write_bytes(response.content)
            validate_wav(output_path)
            print(f"generated question_{number:02d}.wav", flush=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate ten preset-question WAV files.")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--worker-url", default="http://127.0.0.1:8100")
    args = parser.parse_args(argv)
    try:
        generate(args.output_dir, args.worker_url)
    except (httpx.HTTPError, OSError, ValueError, RuntimeError) as error:
        print(f"preset question audio generation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
