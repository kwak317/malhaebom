from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.stt_transcriber import FasterWhisperTranscriber


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="말해봄 faster-whisper 전사")
    parser.add_argument("audio_path", type=Path, help="로컬 음성 파일")
    parser.add_argument("--source-id", required=True, help="비민감 분석 작업 ID")
    parser.add_argument("--output", required=True, type=Path, help="결과 JSON 경로")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = FasterWhisperTranscriber().transcribe(args.audio_path, args.source_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "source_id": result.source_id,
                "model": result.model,
                "duration_sec": result.audio_duration_sec,
                "processing_time_sec": result.processing_time_sec,
                "rtf": result.rtf,
                "filler_total": result.fillers.total_count,
                "output_file": args.output.name,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
