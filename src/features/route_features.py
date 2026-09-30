"""Route feature engineering for APIx airfare data."""

import pandas as pd


def add_route_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add route-level features to airfare observations.

    Expected columns:
        origin
        destination
        route
    """

    df = df.copy()

    # Normalize route text.
    df["origin"] = (
        df["origin"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["destination"] = (
        df["destination"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["route"] = (
        df["origin"] + "-" + df["destination"]
    )

    # Route direction.
    df["route_direction"] = (
        df["origin"] + "_" + df["destination"]
    )

    # Domestic route indicator.
    df["is_domestic"] = 1

    # Airport-specific indicators.
    major_airports = [
        "DEL",
        "BOM",
        "BLR",
        "CCU",
        "HYD",
        "MAA",
    ]

    for airport in major_airports:
        df[f"is_origin_{airport.lower()}"] = (
            df["origin"] == airport
        ).astype(int)

        df[f"is_destination_{airport.lower()}"] = (
            df["destination"] == airport
        ).astype(int)

    # Route frequency within the current dataset.
    route_counts = df["route"].value_counts()

    df["route_observation_count"] = (
        df["route"].map(route_counts)
    )

    return df


if __name__ == "__main__":

    input_path = "data/processed/airfare_clean.parquet"

    df = pd.read_parquet(input_path)

    df = add_route_features(df)

    print("\n" + "=" * 60)
    print("APIx V1 — ROUTE FEATURES")
    print("=" * 60)

    feature_columns = [
        "origin",
        "destination",
        "route",
        "route_direction",
        "is_domestic",
        "route_observation_count",
    ]

    print("\nGenerated route features:")

    for column in feature_columns:
        print(f"  ✓ {column}")

    print("\nRoute distribution:")

    print(
        df["route"]
        .value_counts()
        .to_string()
    )

    print("\nSample:")

    print(
        df[feature_columns]
        .head(10)
        .to_string(index=False)
    )

    print("\nRoute feature engineering completed! 🚀")