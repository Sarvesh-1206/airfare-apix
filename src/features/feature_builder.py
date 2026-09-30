"""Unified feature engineering pipeline for APIx."""

from pathlib import Path

import pandas as pd
from src.features.datetime_features import add_datetime_features
from src.features.route_features import add_route_features



LIVE_INPUT_PATH = Path(
    "data/processed/airfare_clean.parquet"
)

LIVE_OUTPUT_PATH = Path(
    "data/training/airfare_features.parquet"
)

HISTORICAL_INPUT_PATH = Path(
    "data/processed/airfare_historical_clean.parquet"
)

HISTORICAL_OUTPUT_PATH = Path(
    "data/training/airfare_historical_features.parquet"
)


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build the complete APIx feature dataset."""

    df = df.copy()

    # Add datetime features only when the dataset has
    # the relevant date/timestamp columns.
    if "travel_date" in df.columns:
        df = add_datetime_features(df)

    # Historical data uses `date` as the travel date.
    elif "date" in df.columns:
        df["travel_date"] = pd.to_datetime(
            df["date"],
            errors="coerce",
        )

        # Reuse the common datetime feature pipeline.
        df = add_datetime_features(df)

    df = add_route_features(df)

    return df


def process_dataset(
    input_path: Path,
    output_path: Path,
    dataset_name: str,
) -> None:
    """Load, feature-engineer, and save one dataset."""

    print("\n" + "=" * 60)
    print(f"APIx V1 — {dataset_name.upper()} FEATURE BUILDER")
    print("=" * 60)

    print(f"\nLoading: {input_path}")

    if not input_path.exists():
        raise FileNotFoundError(
            f"Input dataset not found: {input_path}"
        )

    df = pd.read_parquet(input_path)

    print(f"Input rows: {len(df):,}")
    print(f"Input columns: {len(df.columns):,}")

    original_columns = set(df.columns)

    df = build_features(df)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_parquet(
        output_path,
        index=False,
    )

    new_columns = [
        column
        for column in df.columns
        if column not in original_columns
    ]

    print("\nFeature engineering complete! 🚀")
    print(f"Output rows: {len(df):,}")
    print(f"Output columns: {len(df.columns):,}")

    print("\nSaved to:")
    print(f"  ✓ {output_path}")

    print("\nNew feature columns:")

    for column in new_columns:
        print(f"  ✓ {column}")


if __name__ == "__main__":

    # ---------------------------------------------------------
    # LIVE DATA
    # ---------------------------------------------------------

    process_dataset(
        input_path=LIVE_INPUT_PATH,
        output_path=LIVE_OUTPUT_PATH,
        dataset_name="Live Fare",
    )

    # ---------------------------------------------------------
    # HISTORICAL DATA
    # ---------------------------------------------------------

    process_dataset(
        input_path=HISTORICAL_INPUT_PATH,
        output_path=HISTORICAL_OUTPUT_PATH,
        dataset_name="Historical Fare",
    )