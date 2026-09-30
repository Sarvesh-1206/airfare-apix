"""Run the daily APIx live-fare pipeline.

Pipeline:
1. Optionally run the configured live-fare collector.
2. Persist newly collected observations into cumulative history.
3. Recalculate the multi-day APIx time series.

The collector is intentionally configurable because the project may use an
authorized airline/OTA/API source with its own command or module.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
HISTORY_MODULE = "src.index.live_fare_history"
TIMESERIES_MODULE = "src.index.apix_timeseries_engine"


def run_module(module: str) -> None:
    """Run a project Python module and stop on failure."""
    print(f"\n{'=' * 64}")
    print(f"RUNNING: {module}")
    print("=" * 64)

    result = subprocess.run(
        [sys.executable, "-m", module],
        cwd=BASE_DIR,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Module failed with exit code {result.returncode}: {module}"
        )


def run_configured_collector() -> None:
    """Run an optional collector command from APIX_COLLECTOR_COMMAND."""
    command = os.getenv("APIX_COLLECTOR_COMMAND", "").strip()

    if not command:
        print("\n=== LIVE COLLECTOR ===")
        print("No APIX_COLLECTOR_COMMAND configured.")
        print("Using existing airfare_live_*.parquet files.")
        return

    print("\n=== LIVE COLLECTOR ===")
    print(f"Configured command: {command}")

    result = subprocess.run(
        command,
        cwd=BASE_DIR,
        shell=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Configured live collector failed with "
            f"exit code {result.returncode}."
        )


def main() -> None:
    print("=" * 64)
    print("APIx — DAILY PIPELINE ORCHESTRATOR")
    print("=" * 64)

    print(f"\nProject directory: {BASE_DIR}")

    run_configured_collector()
    run_module(HISTORY_MODULE)
    run_module(TIMESERIES_MODULE)

    print("\n" + "=" * 64)
    print("APIx DAILY PIPELINE COMPLETE")
    print("=" * 64)
    print("Live collection → history → time-series index")


if __name__ == "__main__":
    main()
