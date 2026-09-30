from pathlib import Path
v

import pandas as pd


INPUT_PATH = Path(
    "data/training/airfare_historical_features.parquet"
)

OUTPUT_PATH = Path(
    "data/training/dnn_base.parquet"
)


def main() -> None:
    print("=" * 70)
    print("DeepAirfareNet - DNN Dataset Preparation")
    print("=" * 70)

    # ------------------------------------------------------------
    # 1. Load
    # ------------------------------------------------------------
    df = pd.read_parquet(INPUT_PATH)

    print(f"Original shape: {df.shape}")

    # ------------------------------------------------------------
    # 2. Remove leakage / redundant / raw-source columns
    # ------------------------------------------------------------
    drop_columns = [
        "price",                     # EXACT duplicate of total_fare
        "travel_date",               # identical to date
        "search_day_of_week",        # 100% missing
        "search_month",              # 100% missing
        "search_quarter",            # 100% missing
        "collection_hour",           # 100% missing
        "collection_day_of_week",    # 100% missing
        "source_file",               # metadata
        "ch_code",                   # raw source code
        "num_code",                  # raw source code
        "departure_time",            # raw string
        "arrival_time",              # raw string
        "flight_number",             # identifier
        "route_observation_count",   # possible leakage
    ]

    existing = [
        col for col in drop_columns
        if col in df.columns
    ]

    df = df.drop(columns=existing)

    print("\nDropped:")
    for col in existing:
        print(f"  - {col}")

   # ------------------------------------------------------------
    # 3. Reconstruct stops correctly
    # ------------------------------------------------------------
    if "stop" in df.columns:

        def parse_stops(value):
            if pd.isna(value):
                return pd.NA

            text = str(value).strip().lower()

            # Normalize actual and escaped whitespace
            text = (
                text
                .replace("\\n", " ")
                .replace("\\t", " ")
            )

            text = " ".join(text.split())

            # Non-stop variants
            if (
                "non-stop" in text
                or "non stop" in text
                or "nonstop" in text
            ):
                return 0

            # Two or more stops
            if "2+" in text:
                return 2

            # Extract numeric stop count
            match = re.search(r"(\d+)", text)

            if match:
                count = int(match.group(1))
                return min(count, 2)

            return pd.NA

        df["stops"] = df["stop"].apply(parse_stops)

        df = df.drop(columns=["stop"])
    # ------------------------------------------------------------
    # 4. Date processing
    # ------------------------------------------------------------
    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce",
    )

    df["travel_day_of_week"] = (
        df["date"].dt.dayofweek
    )

    df["travel_day_name"] = (
        df["date"].dt.day_name()
    )

    df["travel_month"] = (
        df["date"].dt.month
    )

    df["travel_month_name"] = (
        df["date"].dt.month_name()
    )

    df["travel_quarter"] = (
        df["date"].dt.quarter
    )

    df["travel_year"] = (
        df["date"].dt.year
    )

    df["is_weekend"] = (
        df["travel_day_of_week"] >= 5
    ).astype("int8")

    # Keep exact date for chronological splitting
    df["split_date"] = df["date"]

    # Remove raw date from model dataset
    df = df.drop(columns=["date"])

    # ------------------------------------------------------------
    # 5. Target
    # ------------------------------------------------------------
    df["total_fare"] = pd.to_numeric(
        df["total_fare"],
        errors="coerce",
    )

    before = len(df)

    df = df.dropna(
        subset=["total_fare"]
    ).copy()

    print(
        f"\nRemoved invalid target rows: "
        f"{before - len(df)}"
    )

    # ------------------------------------------------------------
    # 6. Validate stops
    # ------------------------------------------------------------
    print("\nStops:")
    print(
        df["stops"]
        .value_counts(dropna=False)
        .sort_index()
        .to_string()
    )

    missing_stops = df["stops"].isna().sum()

    print(
        f"\nMissing stops after mapping: "
        f"{missing_stops}"
    )

    if missing_stops > 0:
        raise ValueError(
            "Unexpected stop values remain unmapped."
        )

    # ------------------------------------------------------------
    # 7. Duplicate check
    # ------------------------------------------------------------
    duplicates = df.duplicated().sum()

    print(
        f"\nDuplicate rows: {duplicates}"
    )

    if duplicates > 0:
        df = (
            df.drop_duplicates()
            .reset_index(drop=True)
        )

    # ------------------------------------------------------------
    # 8. Missing-value audit
    # ------------------------------------------------------------
    print("\nRemaining missing values:")

    missing = df.isna().sum()

    if missing.sum() == 0:
        print("None")
    else:
        print(
            missing[missing > 0]
            .to_string()
        )

    # ------------------------------------------------------------
    # 9. Target statistics
    # ------------------------------------------------------------
    print("\nTarget statistics:")

    print(
        df["total_fare"]
        .describe()
        .to_string()
    )

    # ------------------------------------------------------------
    # 10. Final shape / columns
    # ------------------------------------------------------------
    print(
        f"\nFinal shape: {df.shape}"
    )

    print("\nFinal columns:")

    for i, col in enumerate(
        df.columns,
        start=1,
    ):
        print(f"{i:02d}. {col}")

    # ------------------------------------------------------------
    # 11. Save
    # ------------------------------------------------------------
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    print("\n" + "=" * 70)
    print(
        f"Saved: {OUTPUT_PATH}"
    )
    print(
        f"Final shape: {df.shape}"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()