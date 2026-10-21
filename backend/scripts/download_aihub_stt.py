#!/usr/bin/env python3
"""Download approved STT source data from AI Hub dataset 119.

Dataset: 한국어 방언 발화(경상도)
The current handoff train/validation manifests use DKSR... IDs from this dataset.
"""

from pathlib import Path

from aihub_download_common import PROJECT_ROOT, run_dataset_cli

DATASET_KEY = "119"
DATASET_NAME = "한국어 방언 발화(경상도)"
DEFAULT_DESTINATION = PROJECT_ROOT / "data" / "stt" / "aihub" / DATASET_KEY


if __name__ == "__main__":
    run_dataset_cli(
        dataset_name=DATASET_NAME,
        dataset_key=DATASET_KEY,
        default_destination=DEFAULT_DESTINATION,
    )
