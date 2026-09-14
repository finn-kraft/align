"""Compatibility command for the validated gas analytics pipeline."""

from __future__ import annotations

import os
from pathlib import Path

try:
    from .pipeline import run_pipeline
except ImportError:  # Supports `python gas/process_data.py` during transition.
    from pipeline import run_pipeline


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "data" / "live_data.csv"
OUTPUT_FILE = BASE_DIR / "data" / "processed_data.csv"
REJECTED_FILE = BASE_DIR / "data" / "rejected_rows.csv"


def main() -> None:
    if not INPUT_FILE.exists():
        print("No input file found")
        return
    result = run_pipeline(
        INPUT_FILE,
        OUTPUT_FILE,
        REJECTED_FILE,
        source_name=os.environ.get("ALIGN_GAS_SOURCE_NAME", "google-sheet:jetta"),
    )
    print(f"Saved {len(result.analytics_rows)} dashboard rows to {OUTPUT_FILE}")
    print(f"Saved {len(result.rejected_rows)} rejected source rows to {REJECTED_FILE}")


if __name__ == "__main__":
    main()
