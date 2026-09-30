"""Persist daily live airfare observations into a cumulative history store."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]

RAW_DIR = BASE_DIR / "data" / "raw" / "aviation"
HISTORY_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "airfare_live_history.parquet"
)
SUMMARY_PATH = (
    BASE_DIR
    / "data"
    / "metadata"
    / "live_history_summary.json"
)

REQUIRED_COLUMNS = [
    "collection_timestamp",
    "search_date",
    "travel_date",
    "advance_purchase_days",
    "origin",
    "destination",
    "route",
    "airline",
    "airline_iata_code",
    "flight_number",
    "departure_hour",
    "flight_duration_minutes",
    "stops",
    "fare_class",
    "base_fare",
    "taxes",
    "convenience_fee",
    "total_fare",
    "currency",
    "booking_source",
    "seats_available",
]


def discover_live_files() -> list[Path]:
    """Find live airfare Parquet files."""
    files = sorted(
        path
        for path in RAW_DIR.glob("airfare_live_*.parquet")
        if path.is_file()
    )

    if not files:
        raise FileNotFoundError(
            f"No live airfare Parquet files found in {RAW_DIR}"
        )

    return files


def load_live_file(path: Path) -> pd.DataFrame:
    """Load and validate one live airfare file."""
    df = pd.read_parquet(path)

    missing = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"{path.name} is missing required columns: "
            + ", ".join(missing)
        )

    return df[REQUIRED_COLUMNS].copy()


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize dates and numeric fields."""
    data = df.copy()

    for column in [
        "collection_timestamp",
        "search_date",
        "travel_date",
    ]:
        data[column] = pd.to_datetime(
            data[column],
            errors="coerce",
        )

    numeric_columns = [
        "advance_purchase_days",
        "departure_hour",
        "flight_duration_minutes",
        "stops",
        "base_fare",
        "taxes",
        "convenience_fee",
        "total_fare",
        "seats_available",
    ]

    for column in numeric_columns:
        data[column] = pd.to_numeric(
            data[column],
            errors="coerce",
        )

    # Remove rows that cannot identify an observation or fare.
    data = data.dropna(
        subset=[
            "collection_timestamp",
            "travel_date",
            "route",
            "airline",
            "fare_class",
            "total_fare",
        ]
    )

    data = data[data["total_fare"] > 0]

    # Preserve a deterministic observation key.
    # This prevents the same exact quote from being appended twice.
    data["_observation_key"] = (
        data["collection_timestamp"].astype(str)
        + "|"
        + data["search_date"].astype(str)
        + "|"
        + data["travel_date"].astype(str)
        + "|"
        + data["route"].astype(str)
        + "|"
        + data["airline"].astype(str)
        + "|"
        + data["flight_number"].astype(str)
        + "|"
        + data["fare_class"].astype(str)
        + "|"
        + data["booking_source"].astype(str)
        + "|"
        + data["total_fare"].round(2).astype(str)
    )

    return data


def load_existing_history() -> pd.DataFrame:
    """Load the existing history, or return an empty frame."""
    if not HISTORY_PATH.exists():
        return pd.DataFrame(
            columns=REQUIRED_COLUMNS + ["_observation_key"]
        )

    history = pd.read_parquet(HISTORY_PATH)

    if "_observation_key" not in history.columns:
        history = normalize(history)
    else:
        # Ensure datetime/numeric dtypes remain stable after reading Parquet.
        history = normalize(history)

    return history


def append_history(
    existing: pd.DataFrame,
    incoming: pd.DataFrame,
) -> tuple[pd.DataFrame, int]:
    """Append only genuinely new observations."""
    existing_keys = set(
        existing["_observation_key"].dropna().astype(str)
    )

    incoming = incoming[
        ~incoming["_observation_key"].astype(str).isin(existing_keys)
    ].copy()

    added = len(incoming)

    combined = pd.concat(
        [existing, incoming],
        ignore_index=True,
    )

    # Also remove duplicates that may exist inside the same new batch.
    combined = combined.drop_duplicates(
        subset=["_observation_key"],
        keep="first",
    )

    return combined, added


def build_summary(
    history: pd.DataFrame,
    source_files: list[Path],
    added_rows: int,
) -> dict:
    """Build metadata describing the historical live store."""
    if history.empty:
        return {
            "project": "India Real-Time Airfare Price Index (APIx)",
            "component": "historical live-fare store",
            "rows": 0,
            "new_rows_added": int(added_rows),
            "source_files": [p.name for p in source_files],
        }

    collection_timestamp = pd.to_datetime(
        history["collection_timestamp"],
        errors="coerce",
    )

    collection_dates = (
        collection_timestamp
        .dt.normalize()
        .dropna()
    )

    if collection_dates.empty:
        return {
            "project": "India Real-Time Airfare Price Index (APIx)",
            "component": "historical live-fare store",
            "rows": int(len(history)),
            "new_rows_added": int(added_rows),
            "collection_days": 0,
            "collection_start": None,
            "collection_end": None,
            "routes": sorted(
                history["route"].dropna().unique().tolist()
            ),
            "airlines": sorted(
                history["airline"].dropna().unique().tolist()
            ),
            "fare_classes": sorted(
                history["fare_class"].dropna().unique().tolist()
            ),
            "lead_times": sorted(
                history["advance_purchase_days"]
                .dropna()
                .astype(int)
                .unique()
                .tolist()
            ),
            "source_files": [p.name for p in source_files],
        }

    return {
        "project": "India Real-Time Airfare Price Index (APIx)",
        "component": "historical live-fare store",
        "rows": int(len(history)),
        "new_rows_added": int(added_rows),
        "collection_days": int(collection_dates.nunique()),
        "collection_start": str(collection_dates.min().date()),
        "collection_end": str(collection_dates.max().date()),
        "routes": sorted(
            history["route"].dropna().unique().tolist()
        ),
        "airlines": sorted(
            history["airline"].dropna().unique().tolist()
        ),
        "fare_classes": sorted(
            history["fare_class"].dropna().unique().tolist()
        ),
        "lead_times": sorted(
            history["advance_purchase_days"]
            .dropna()
            .astype(int)
            .unique()
            .tolist()
        ),
        "source_files": [p.name for p in source_files],
    }


def main() -> None:
    print("=" * 60)
    print("APIx — LIVE FARE HISTORY")
    print("=" * 60)

    source_files = discover_live_files()

    print("\n=== SOURCE FILES ===")
    for path in source_files:
        print(f"✓ {path.name}")

    incoming_parts = []

    for path in source_files:
        df = load_live_file(path)
        df = normalize(df)
        incoming_parts.append(df)

    incoming = pd.concat(
        incoming_parts,
        ignore_index=True,
    )

    print(f"\nIncoming observations: {len(incoming):,}")

    existing = load_existing_history()

    print(f"Existing history:      {len(existing):,}")

    history, added_rows = append_history(
        existing,
        incoming,
    )

    # Enforce stable datetime dtypes before sorting, saving, and summarizing.
    history["collection_timestamp"] = pd.to_datetime(
        history["collection_timestamp"],
        errors="coerce",
    )

    history["search_date"] = pd.to_datetime(
        history["search_date"],
        errors="coerce",
    )

    history["travel_date"] = pd.to_datetime(
        history["travel_date"],
        errors="coerce",
    )

    history = history.sort_values(
        ["collection_timestamp", "route", "flight_number"],
        kind="stable",
    ).reset_index(drop=True)

    HISTORY_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    SUMMARY_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    history.to_parquet(
        HISTORY_PATH,
        index=False,
    )

    summary = build_summary(
        history,
        source_files,
        added_rows,
    )

    with open(
        SUMMARY_PATH,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            summary,
            file,
            indent=2,
        )

    print("\n=== HISTORY UPDATE ===")
    print(f"New observations added: {added_rows:,}")
    print(f"Total history rows:     {len(history):,}")
    print(
        f"Collection days:        "
        f"{summary.get('collection_days', 0):,}"
    )

    print("\n=== FILES SAVED ===")
    print(f"✓ {HISTORY_PATH}")
    print(f"✓ {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
