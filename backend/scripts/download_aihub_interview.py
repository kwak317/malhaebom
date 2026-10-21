#!/usr/bin/env python3
"""Selective downloader for AI Hub dataset 71592 (채용면접 인터뷰 데이터)."""

from pathlib import Path

from aihub_download_common import PROJECT_ROOT, run_dataset_cli

DATASET_KEY = "71592"
DATASET_NAME = "채용면접 인터뷰 데이터"
DEFAULT_DESTINATION = PROJECT_ROOT / "data" / "stt" / "aihub" / DATASET_KEY

if __name__ == "__main__":
    run_dataset_cli(
        dataset_name=DATASET_NAME,
        dataset_key=DATASET_KEY,
        default_destination=DEFAULT_DESTINATION,
    )
