"""APIx V1 — Real-Time Airfare Price Index engine.

V1 methodology
---------------
1. Use observed total fares.
2. Aggregate fares by route, fare class, and advance-purchase bucket.
3. Calculate price relatives against a configurable base period.
4. Apply configurable route weights.
5. Produce route-level and composite APIx values.

Important:
- This engine does NOT use ML predictions for the index.
- DGCA passenger weights can be supplied when the traffic dataset
  is integrated.
- Until then, equal route weights are used for development/testing.
"""

from pathlib import Path

import json
import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "airfare_clean.parquet"
)

DGCA_WEIGHTS_PATH = (
    BASE_DIR
    / "data"
    / "metadata"
    / "dgca_route_weights.csv"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "metadata"
)

ROUTE_OUTPUT_PATH = (
    OUTPUT_DIR
    / "apix_route_index.csv"
)

SUMMARY_OUTPUT_PATH = (
    OUTPUT_DIR
    / "apix_summary.json"
)


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_BASE_INDEX = 100.0

ROUTE_EXPECTED = [
    "BOM-BLR",
    "DEL-BLR",
    "DEL-BOM",
    "DEL-CCU",
    "DEL-HYD",
    "DEL-MAA",
]

SUPPORTED_LEAD_TIMES = [
    1,
    7,
    15,
    30,
    45,
]

REQUIRED_COLUMNS = [
    "collection_timestamp",
    "search_date",
    "travel_date",
    "advance_purchase_days",
    "origin",
    "destination",
    "route",
    "airline",
    "fare_class",
    "total_fare",
    "currency",
]


# ============================================================
# DATA LOADING
# ============================================================

def load_data(path: Path = INPUT_PATH) -> pd.DataFrame:
    """Load and validate normalized airfare observations."""

    print(f"Loading: {path}")

    df = pd.read_parquet(path)

    missing = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(missing)
        )

    return df


# ============================================================
# DATA PREPARATION
# ============================================================

def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare observations for index calculation."""

    data = df.copy()

    # --------------------------------------------------------
    # Dates
    # --------------------------------------------------------

    data["collection_timestamp"] = pd.to_datetime(
        data["collection_timestamp"],
        errors="coerce",
    )

    data["search_date"] = pd.to_datetime(
        data["search_date"],
        errors="coerce",
    )

    data["travel_date"] = pd.to_datetime(
        data["travel_date"],
        errors="coerce",
    )

    # --------------------------------------------------------
    # Numeric fields
    # --------------------------------------------------------

    data["total_fare"] = pd.to_numeric(
        data["total_fare"],
        errors="coerce",
    )

    data["advance_purchase_days"] = pd.to_numeric(
        data["advance_purchase_days"],
        errors="coerce",
    )

    # --------------------------------------------------------
    # Remove invalid observations
    # --------------------------------------------------------

    before = len(data)

    data = data.dropna(
        subset=[
            "collection_timestamp",
            "route",
            "fare_class",
            "total_fare",
            "advance_purchase_days",
        ]
    )

    data = data[
        data["total_fare"] > 0
    ]

    data = data[
        data["advance_purchase_days"].isin(
            SUPPORTED_LEAD_TIMES
        )
    ]

    removed = before - len(data)

    print("\n=== DATA PREPARATION ===")
    print(f"Input observations:  {before:,}")
    print(f"Removed observations:{removed:,}")
    print(f"Valid observations:  {len(data):,}")

    return data


# ============================================================
# ROUTE WEIGHTS
# ============================================================

def load_dgca_route_weights(
    path: Path = DGCA_WEIGHTS_PATH,
) -> pd.DataFrame:
    """Load and validate DGCA passenger-traffic route weights."""

    print(f"Loading DGCA weights: {path}")

    if not path.exists():
        raise FileNotFoundError(
            f"DGCA route weights not found: {path}"
        )

    weights = pd.read_csv(path)

    weights = validate_weights(weights)

    required_routes = set(
        ROUTE_EXPECTED
    )

    actual_routes = set(
        weights["route"]
    )

    missing_routes = required_routes - actual_routes

    if missing_routes:
        raise ValueError(
            "DGCA weights are missing APIx routes: "
            + ", ".join(sorted(missing_routes))
        )

    weights = weights[
        weights["route"].isin(required_routes)
    ].copy()

    weights = validate_weights(weights)

    return weights


def build_equal_route_weights(
    routes: list[str],
) -> pd.DataFrame:
    """Create temporary equal route weights.

    This is only a development fallback.
    DGCA passenger weights will replace this later.
    """

    unique_routes = sorted(
        pd.Series(routes).dropna().unique()
    )

    if not unique_routes:
        raise ValueError(
            "No routes available for weighting."
        )

    weight = 1.0 / len(unique_routes)

    weights = pd.DataFrame(
        {
            "route": unique_routes,
            "route_weight": weight,
        }
    )

    return weights


def validate_weights(
    weights: pd.DataFrame,
) -> pd.DataFrame:
    """Validate and normalize route weights."""

    required = [
        "route",
        "route_weight",
    ]

    missing = [
        column
        for column in required
        if column not in weights.columns
    ]

    if missing:
        raise ValueError(
            "Missing weight columns: "
            + ", ".join(missing)
        )

    weights = weights.copy()

    weights["route_weight"] = pd.to_numeric(
        weights["route_weight"],
        errors="coerce",
    )

    weights = weights.dropna(
        subset=[
            "route",
            "route_weight",
        ]
    )

    weights = weights[
        weights["route_weight"] >= 0
    ]

    if weights.empty:
        raise ValueError(
            "No valid route weights."
        )

    total_weight = weights[
        "route_weight"
    ].sum()

    if total_weight <= 0:
        raise ValueError(
            "Route weights must have a positive sum."
        )

    # Normalize to exactly 1.
    weights["route_weight"] = (
        weights["route_weight"]
        / total_weight
    )

    return weights


# ============================================================
# STRATUM AGGREGATION
# ============================================================

def aggregate_fares(
    data: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate observed fares by date, route, fare class,
    and advance-purchase bucket."""

    data = data.copy()

    data["index_date"] = (
        data["collection_timestamp"]
        .dt.normalize()
    )

    grouped = (
        data.groupby(
            [
                "index_date",
                "route",
                "fare_class",
                "advance_purchase_days",
            ],
            as_index=False,
        )
        .agg(
            mean_fare=(
                "total_fare",
                "mean",
            ),
            median_fare=(
                "total_fare",
                "median",
            ),
            observation_count=(
                "total_fare",
                "count",
            ),
            airline_count=(
                "airline",
                "nunique",
            ),
        )
    )

    return grouped


# ============================================================
# BASE PERIOD
# ============================================================

def determine_base_date(
    aggregated: pd.DataFrame,
    base_date: str | None = None,
) -> pd.Timestamp:
    """Determine the base period.

    If no base date is supplied, the earliest available
    observation date is used.
    """

    if aggregated.empty:
        raise ValueError(
            "Cannot determine base date from empty data."
        )

    available_dates = sorted(
        aggregated["index_date"].dropna().unique()
    )

    if base_date is None:
        return pd.Timestamp(
            available_dates[0]
        )

    requested = pd.Timestamp(
        base_date
    ).normalize()

    if requested not in available_dates:
        raise ValueError(
            f"Requested base date {requested.date()} "
            "does not exist in the dataset."
        )

    return requested


# ============================================================
# BASE FARES
# ============================================================

def calculate_base_fares(
    aggregated: pd.DataFrame,
    base_date: pd.Timestamp,
) -> pd.DataFrame:
    """Calculate base-period mean fare for each stratum."""

    base = aggregated[
        aggregated["index_date"] == base_date
    ].copy()

    if base.empty:
        raise ValueError(
            "No observations available for "
            "the selected base date."
        )

    base = base[
        [
            "route",
            "fare_class",
            "advance_purchase_days",
            "mean_fare",
        ]
    ].rename(
        columns={
            "mean_fare": "base_fare",
        }
    )

    return base


# ============================================================
# PRICE RELATIVES
# ============================================================

def calculate_price_relatives(
    aggregated: pd.DataFrame,
    base_fares: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate stratum-level price relatives."""

    result = aggregated.merge(
        base_fares,
        on=[
            "route",
            "fare_class",
            "advance_purchase_days",
        ],
        how="left",
    )

    # Only strata with a valid base fare can produce
    # a price relative.
    result = result[
        result["base_fare"].notna()
    ].copy()

    result = result[
        result["base_fare"] > 0
    ]

    result["price_relative"] = (
        result["mean_fare"]
        / result["base_fare"]
        * DEFAULT_BASE_INDEX
    )

    return result


# ============================================================
# STRATUM WEIGHTS
# ============================================================

def calculate_stratum_weights(
    base_fares: pd.DataFrame,
) -> pd.DataFrame:
    """Create equal weights across fare-class/lead-time strata.

    Route weights are applied separately later.

    This keeps V1 methodology transparent while we wait
    for a richer DGCA weighting structure.
    """

    strata = (
        base_fares[
            [
                "route",
                "fare_class",
                "advance_purchase_days",
            ]
        ]
        .drop_duplicates()
        .copy()
    )

    counts = (
        strata.groupby("route")
        .size()
        .rename("stratum_count")
        .reset_index()
    )

    strata = strata.merge(
        counts,
        on="route",
        how="left",
    )

    strata["stratum_weight"] = (
        1.0
        / strata["stratum_count"]
    )

    return strata[
        [
            "route",
            "fare_class",
            "advance_purchase_days",
            "stratum_weight",
        ]
    ]


# ============================================================
# COMPOSITE INDEX
# ============================================================

def calculate_composite_index(
    relatives: pd.DataFrame,
    route_weights: pd.DataFrame,
    stratum_weights: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate weighted route and composite indices."""

    result = relatives.merge(
        route_weights,
        on="route",
        how="left",
    )

    result = result.merge(
        stratum_weights,
        on=[
            "route",
            "fare_class",
            "advance_purchase_days",
        ],
        how="left",
    )

    result = result.dropna(
        subset=[
            "route_weight",
            "stratum_weight",
        ]
    ).copy()

    result["combined_weight"] = (
        result["route_weight"]
        * result["stratum_weight"]
    )

    result["weighted_relative"] = (
        result["price_relative"]
        * result["combined_weight"]
    )

    # --------------------------------------------------------
    # Route-level index
    # --------------------------------------------------------

    route_index = (
        result.groupby(
            [
                "index_date",
                "route",
            ],
            as_index=False,
        )
        .agg(
            route_index=(
                "weighted_relative",
                "sum",
            ),
            observations=(
                "observation_count",
                "sum",
            ),
        )
    )

    # --------------------------------------------------------
    # Composite APIx
    # --------------------------------------------------------

    composite = (
        result.groupby(
            "index_date",
            as_index=False,
        )
        .agg(
            apix=(
                "weighted_relative",
                "sum",
            ),
            observations=(
                "observation_count",
                "sum",
            ),
            routes_covered=(
                "route",
                "nunique",
            ),
        )
    )

    # --------------------------------------------------------
    # Merge route information
    # --------------------------------------------------------

    route_index = route_index.merge(
        route_weights,
        on="route",
        how="left",
    )

    route_index["route_index"] = (
        route_index["route_index"]
        / route_index["route_weight"]
    )

    return route_index, composite, result


# ============================================================
# SUMMARY
# ============================================================

def build_summary(
    data: pd.DataFrame,
    aggregated: pd.DataFrame,
    route_index: pd.DataFrame,
    composite: pd.DataFrame,
    base_date: pd.Timestamp,
) -> dict:
    """Build metadata summary."""

    return {
        "project": (
            "India Real-Time Airfare Price Index (APIx)"
        ),
        "version": "V1",
        "base_index": DEFAULT_BASE_INDEX,
        "base_date": str(
            base_date.date()
        ),
        "input_rows": int(len(data)),
        "aggregated_rows": int(
            len(aggregated)
        ),
        "routes": int(
            data["route"].nunique()
        ),
        "airlines": int(
            data["airline"].nunique()
        ),
        "fare_classes": sorted(
            data["fare_class"]
            .dropna()
            .unique()
            .tolist()
        ),
        "lead_times": sorted(
            data["advance_purchase_days"]
            .dropna()
            .astype(int)
            .unique()
            .tolist()
        ),
        "date_range": {
            "start": str(
                data["collection_timestamp"]
                .min()
                .date()
            ),
            "end": str(
                data["collection_timestamp"]
                .max()
                .date()
            ),
        },
        "route_index_rows": int(
            len(route_index)
        ),
        "composite_index_rows": int(
            len(composite)
        ),
        "latest_apix": (
            float(
                composite.sort_values(
                    "index_date"
                )
                .iloc[-1]["apix"]
            )
            if not composite.empty
            else None
        ),
        "weighting_method": (
            "DGCA two-way passenger-traffic route weights."
        ),
        "weight_source": str(DGCA_WEIGHTS_PATH),
        "fare_measure": "mean total_fare",
        "ml_used_for_index": False,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("APIx V1 — INDEX ENGINE")
    print("=" * 60)

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    df = load_data()

    # --------------------------------------------------------
    # Prepare
    # --------------------------------------------------------

    data = prepare_data(df)

    # --------------------------------------------------------
    # Aggregate
    # --------------------------------------------------------

    aggregated = aggregate_fares(
        data
    )

    print("\n=== AGGREGATION ===")
    print(
        f"Aggregated rows: {len(aggregated):,}"
    )

    # --------------------------------------------------------
    # Base date
    # --------------------------------------------------------

    base_date = determine_base_date(
        aggregated
    )

    print(
        f"Base date: {base_date.date()}"
    )

    # --------------------------------------------------------
    # Base fares
    # --------------------------------------------------------

    base_fares = calculate_base_fares(
        aggregated,
        base_date,
    )

    print(
        f"Base strata: {len(base_fares):,}"
    )

    # --------------------------------------------------------
    # Price relatives
    # --------------------------------------------------------

    relatives = calculate_price_relatives(
        aggregated,
        base_fares,
    )

    print(
        f"Valid relative observations: "
        f"{len(relatives):,}"
    )

    # --------------------------------------------------------
    # Route weights
    # --------------------------------------------------------

    route_weights = load_dgca_route_weights()


    print("\n=== ROUTE WEIGHTS ===")
    print(
        route_weights.to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # Stratum weights
    # --------------------------------------------------------

    stratum_weights = (
        calculate_stratum_weights(
            base_fares
        )
    )

    # --------------------------------------------------------
    # Composite
    # --------------------------------------------------------

    route_index, composite, detailed = (
        calculate_composite_index(
            relatives,
            route_weights,
            stratum_weights,
        )
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    summary = build_summary(
        data,
        aggregated,
        route_index,
        composite,
        base_date,
    )

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    route_index.to_csv(
        ROUTE_OUTPUT_PATH,
        index=False,
    )

    with open(
        SUMMARY_OUTPUT_PATH,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            summary,
            file,
            indent=2,
        )

    # Detailed development output
    detailed.to_csv(
        OUTPUT_DIR
        / "apix_detailed_index.csv",
        index=False,
    )

    composite.to_csv(
        OUTPUT_DIR
        / "apix_composite_index.csv",
        index=False,
    )

    # --------------------------------------------------------
    # Display
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("APIx RESULT")
    print("=" * 60)

    if not composite.empty:

        display_composite = composite.copy()

        numeric_columns = display_composite.select_dtypes(
            include=np.number
        ).columns

        display_composite[numeric_columns] = (
            display_composite[numeric_columns].round(2)
        )

        print(
            display_composite.to_string(index=False)
)

        print(
            f"\nLatest APIx: "
            f"{summary['latest_apix']:.2f}"
        )

    else:
        print(
            "No composite index could be calculated."
        )

    print("\n=== FILES SAVED ===")

    print(
        f"✓ Route index: "
        f"{ROUTE_OUTPUT_PATH}"
    )

    print(
        f"✓ Composite index: "
        f"{OUTPUT_DIR / 'apix_composite_index.csv'}"
    )

    print(
        f"✓ Detailed index: "
        f"{OUTPUT_DIR / 'apix_detailed_index.csv'}"
    )

    print(
        f"✓ Summary: "
        f"{SUMMARY_OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()