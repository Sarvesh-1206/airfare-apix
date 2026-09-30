"""Clean and normalize the historical airfare dataset."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "aviation"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
METADATA_DIR = PROJECT_ROOT / "data" / "metadata"

ECONOMY_FILE = RAW_DIR / "economy.csv.csv"
BUSINESS_FILE = RAW_DIR / "business.csv.csv"

OUTPUT_FILE = PROCESSED_DIR / "airfare_historical_clean.parquet"
QUALITY_REPORT = METADATA_DIR / "historical_data_quality_report.json"


EXPECTED_COLUMNS = [
    "date",
    "airline",
    "ch_code",
    "num_code",
    "dep_time",
    "from",
    "time_taken",
    "stop",
    "arr_time",
    "to",
    "price",
]


def parse_duration(value: object) -> float:
    """Convert values such as '02h 10m' into minutes."""
    if pd.isna(value):
        return float("nan")

    text = str(value).strip().lower()

    hours_match = re.search(r"(\d+)\s*h", text)
    minutes_match = re.search(r"(\d+)\s*m", text)

    hours = int(hours_match.group(1)) if hours_match else 0
    minutes = int(minutes_match.group(1)) if minutes_match else 0

    return float(hours * 60 + minutes)


def normalize_stops(value: object) -> object:
    """Normalize stop descriptions."""
    if pd.isna(value):
        return pd.NA

    text = str(value)
    text = re.sub(r"\s+", " ", text).strip().lower()

    if "non-stop" in text or "non stop" in text:
        return 0

    match = re.search(r"(\d+)\s*-?\s*stop", text)

    if match:
        return int(match.group(1))

    return pd.NA


def normalize_airline(value: object) -> object:
    """Normalize airline names while preserving historical meaning."""
    if pd.isna(value):
        return pd.NA

    text = str(value).strip()

    mapping = {
        "Air India": "Air India",
        "AirAsia": "AirAsia",
        "GO_FIRST": "Go First",
        "Go First": "Go First",
        "Indigo": "IndiGo",
        "IndiGo": "IndiGo",
        "SpiceJet": "SpiceJet",
        "Vistara": "Vistara",
    }

    return mapping.get(text, text)


def clean_historical_file(path: Path, fare_class: str) -> pd.DataFrame:
    """Load and normalize one historical CSV."""
    df = pd.read_csv(path)

    missing_columns = [
        column for column in EXPECTED_COLUMNS if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"{path.name} is missing required columns: {missing_columns}"
        )

    df = df[EXPECTED_COLUMNS].copy()

    # Preserve source information.
    df["source_file"] = path.name
    df["fare_class"] = fare_class

    # Date.
    df["date"] = pd.to_datetime(
        df["date"],
        format="%d-%m-%Y",
        errors="coerce",
    )

    # Airline and codes.
    df["airline"] = df["airline"].map(normalize_airline)
    df["airline_iata_code"] = df["ch_code"].astype("string").str.strip().str.upper()

    df["flight_number"] = pd.to_numeric(
        df["num_code"],
        errors="coerce",
    ).astype("Int64")

    # Cities.
    df["origin"] = (
        df["from"]
        .astype("string")
        .str.strip()
        .str.title()
    )

    df["destination"] = (
        df["to"]
        .astype("string")
        .str.strip()
        .str.title()
    )

    df["route"] = (
        df["origin"].str.upper()
        + "-"
        + df["destination"].str.upper()
    )

    # Times.
    df["departure_time"] = (
        df["dep_time"]
        .astype("string")
        .str.strip()
    )

    df["arrival_time"] = (
        df["arr_time"]
        .astype("string")
        .str.strip()
    )

    # Duration.
    df["flight_duration_minutes"] = df["time_taken"].map(parse_duration)

    # Stops.
    df["stops"] = df["stop"].map(normalize_stops)

    # Price.
    df["total_fare"] = pd.to_numeric(
        df["price"]
        .astype("string")
        .str.replace(",", "", regex=False)
        .str.strip(),
        errors="coerce",
    )

    # Historical source is INR.
    df["currency"] = "INR"

    # Historical data came from the EaseMyTrip dataset.
    df["booking_source"] = "EaseMyTrip"

    return df


def validate_data(df: pd.DataFrame) -> dict:
    """Run quality checks and return a report."""
    report = {
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "missing_values": {
            column: int(value)
            for column, value in df.isna().sum().items()
            if value > 0
        },
        "duplicate_rows": int(df.duplicated().sum()),
        "negative_fares": int((df["total_fare"] < 0).sum()),
        "zero_fares": int((df["total_fare"] == 0).sum()),
        "invalid_duration": int(
            (df["flight_duration_minutes"] <= 0).sum()
        ),
        "invalid_stops": int(
            (
                df["stops"].notna()
                & (df["stops"] < 0)
            ).sum()
        ),
        "date_min": (
            df["date"].min().strftime("%Y-%m-%d")
            if df["date"].notna().any()
            else None
        ),
        "date_max": (
            df["date"].max().strftime("%Y-%m-%d")
            if df["date"].notna().any()
            else None
        ),
        "fare_min": (
            float(df["total_fare"].min())
            if df["total_fare"].notna().any()
            else None
        ),
        "fare_max": (
            float(df["total_fare"].max())
            if df["total_fare"].notna().any()
            else None
        ),
        "fare_mean": (
            float(df["total_fare"].mean())
            if df["total_fare"].notna().any()
            else None
        ),
    }

    return report


def main() -> None:
    """Run the complete historical cleaning pipeline."""
    print("=== APIx Historical Data Cleaning ===")

    if not ECONOMY_FILE.exists():
        raise FileNotFoundError(f"Missing file: {ECONOMY_FILE}")

    if not BUSINESS_FILE.exists():
        raise FileNotFoundError(f"Missing file: {BUSINESS_FILE}")

    print("\nLoading economy dataset...")
    economy = clean_historical_file(
        ECONOMY_FILE,
        fare_class="Economy",
    )

    print(f"Economy rows: {len(economy):,}")

    print("\nLoading business dataset...")
    business = clean_historical_file(
        BUSINESS_FILE,
        fare_class="Business",
    )

    print(f"Business rows: {len(business):,}")

    print("\nCombining datasets...")
    df = pd.concat(
        [economy, business],
        ignore_index=True,
    )

    original_rows = len(df)

    print(f"Combined rows: {original_rows:,}")

    # Remove exact duplicates only.
    duplicate_count = int(df.duplicated().sum())

    if duplicate_count:
        print(f"Removing exact duplicates: {duplicate_count}")
        df = df.drop_duplicates().reset_index(drop=True)

    # Final validation.
    report = validate_data(df)

    report["original_rows"] = original_rows
    report["rows_removed"] = original_rows - len(df)
    report["economy_rows"] = int(len(economy))
    report["business_rows"] = int(len(business))

    report["airlines"] = (
        df["airline"]
        .value_counts()
        .sort_index()
        .to_dict()
    )

    report["routes"] = (
        df["route"]
        .value_counts()
        .sort_index()
        .to_dict()
    )

    report["fare_classes"] = (
        df["fare_class"]
        .value_counts()
        .sort_index()
        .to_dict()
    )

    # Save processed data.
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)

    df.to_parquet(
        OUTPUT_FILE,
        index=False,
        engine="pyarrow",
    )

    with QUALITY_REPORT.open("w", encoding="utf-8") as file:
        json.dump(
            report,
            file,
            indent=2,
        )

    print("\n=== CLEANING COMPLETE ===")
    print(f"Final rows: {len(df):,}")
    print(f"Final columns: {len(df.columns)}")
    print(f"Duplicates removed: {duplicate_count}")
    print(f"Output: {OUTPUT_FILE}")
    print(f"Quality report: {QUALITY_REPORT}")

    print("\n=== FARE CLASS ===")
    print(df["fare_class"].value_counts())

    print("\n=== AIRLINES ===")
    print(df["airline"].value_counts())

    print("\n=== TOP ROUTES ===")
    print(df["route"].value_counts().head(15))

    print("\n=== PRICE SUMMARY ===")
    print(df["total_fare"].describe())


if __name__ == "__main__":
    main()