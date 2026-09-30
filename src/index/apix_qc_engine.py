"""Statistical quality-control engine for the India Real-Time Airfare Price Index.

The QC layer validates the live-fare history and APIx outputs without changing
the underlying observations or index. Checks are classified as PASS, REVIEW,
or FAIL.

Outputs:
    data/metadata/apix_qc_results.csv
    data/metadata/apix_qc_report.json
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]

HISTORY_PATH = (
    BASE_DIR / "data" / "processed" / "airfare_live_history.parquet"
)
DAILY_INDEX_PATH = (
    BASE_DIR / "data" / "metadata" / "apix_daily_index.csv"
)
ROUTE_INDEX_PATH = (
    BASE_DIR / "data" / "metadata" / "apix_daily_route_index.csv"
)
DGCA_WEIGHTS_PATH = (
    BASE_DIR / "data" / "metadata" / "dgca_route_weights.csv"
)

OUTPUT_DIR = BASE_DIR / "data" / "metadata"
RESULTS_PATH = OUTPUT_DIR / "apix_qc_results.csv"
REPORT_PATH = OUTPUT_DIR / "apix_qc_report.json"

EXPECTED_ROUTES = {
    "DEL-BOM",
    "DEL-BLR",
    "BOM-BLR",
    "DEL-CCU",
    "DEL-HYD",
    "DEL-MAA",
}
EXPECTED_LEAD_TIMES = {1, 7, 15, 30, 45}
EXPECTED_FARE_CLASSES = {"Economy", "Business"}

PASS = "PASS"
REVIEW = "REVIEW"
FAIL = "FAIL"


def result(check: str, status: str, value, threshold, message: str) -> dict:
    """Create one standardized QC result."""
    return {
        "check": check,
        "status": status,
        "value": value,
        "threshold": threshold,
        "message": message,
    }


def load_history() -> pd.DataFrame:
    """Load the cumulative live-fare history."""
    if not HISTORY_PATH.exists():
        raise FileNotFoundError(f"History file not found: {HISTORY_PATH}")

    df = pd.read_parquet(HISTORY_PATH).copy()

    required = [
        "collection_timestamp",
        "route",
        "fare_class",
        "advance_purchase_days",
        "total_fare",
    ]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(
            "History is missing required columns: "
            + ", ".join(missing)
        )

    df["collection_timestamp"] = pd.to_datetime(
        df["collection_timestamp"],
        errors="coerce",
    )
    df["advance_purchase_days"] = pd.to_numeric(
        df["advance_purchase_days"],
        errors="coerce",
    )
    df["total_fare"] = pd.to_numeric(
        df["total_fare"],
        errors="coerce",
    )
    df["collection_date"] = df["collection_timestamp"].dt.normalize()

    return df


def check_missing_values(df: pd.DataFrame) -> dict:
    """Check required APIx fields for missing values."""
    columns = [
        "collection_timestamp",
        "route",
        "fare_class",
        "advance_purchase_days",
        "total_fare",
    ]

    missing_cells = int(df[columns].isna().sum().sum())

    return result(
        "required_field_missing_values",
        PASS if missing_cells == 0 else FAIL,
        missing_cells,
        0,
        "No missing values in required APIx fields."
        if missing_cells == 0
        else f"{missing_cells:,} missing required-field cells found.",
    )


def check_duplicate_keys(df: pd.DataFrame) -> dict:
    """Check deterministic observation keys when available."""
    if "_observation_key" in df.columns:
        duplicate_count = int(
            df["_observation_key"].duplicated(keep=False).sum()
        )
        threshold = 0
        message = (
            "No duplicate observation keys found."
            if duplicate_count == 0
            else f"{duplicate_count:,} rows share duplicate observation keys."
        )
    else:
        columns = [
            "collection_timestamp",
            "route",
            "fare_class",
            "advance_purchase_days",
            "total_fare",
        ]
        duplicate_count = int(df.duplicated(subset=columns).sum())
        threshold = 0
        message = (
            "No duplicate observation combinations found."
            if duplicate_count == 0
            else f"{duplicate_count:,} duplicate observation combinations found."
        )

    return result(
        "duplicate_observations",
        PASS if duplicate_count == 0 else FAIL,
        duplicate_count,
        threshold,
        message,
    )


def check_positive_fares(df: pd.DataFrame) -> dict:
    """Check that all usable fares are positive."""
    invalid = int((df["total_fare"].dropna() <= 0).sum())

    return result(
        "positive_total_fares",
        PASS if invalid == 0 else FAIL,
        invalid,
        0,
        "All recorded total fares are positive."
        if invalid == 0
        else f"{invalid:,} non-positive fares found.",
    )


def check_routes(df: pd.DataFrame) -> dict:
    """Check expected APIx basket route coverage."""
    routes = set(df["route"].dropna().unique())
    missing = sorted(EXPECTED_ROUTES - routes)

    return result(
        "route_coverage",
        PASS if not missing else FAIL,
        len(routes & EXPECTED_ROUTES),
        len(EXPECTED_ROUTES),
        "All six APIx basket routes are represented."
        if not missing
        else "Missing routes: " + ", ".join(missing),
    )


def check_lead_times(df: pd.DataFrame) -> dict:
    """Check expected lead-time bucket coverage."""
    lead_times = set(
        df["advance_purchase_days"].dropna().round().astype(int).unique()
    )
    missing = sorted(EXPECTED_LEAD_TIMES - lead_times)

    return result(
        "lead_time_coverage",
        PASS if not missing else REVIEW,
        len(lead_times & EXPECTED_LEAD_TIMES),
        len(EXPECTED_LEAD_TIMES),
        "All five APIx lead-time buckets are represented."
        if not missing
        else "Missing lead-time buckets: "
        + ", ".join(map(str, missing)),
    )


def check_fare_classes(df: pd.DataFrame) -> dict:
    """Check Economy and Business strata."""
    classes = set(df["fare_class"].dropna().unique())
    missing = sorted(EXPECTED_FARE_CLASSES - classes)

    return result(
        "fare_class_coverage",
        PASS if not missing else REVIEW,
        len(classes & EXPECTED_FARE_CLASSES),
        len(EXPECTED_FARE_CLASSES),
        "Economy and Business strata are represented."
        if not missing
        else "Missing fare classes: " + ", ".join(missing),
    )


def check_collection_days(df: pd.DataFrame) -> dict:
    """Check whether enough collection days exist for time-series analysis."""
    days = int(df["collection_date"].dropna().nunique())

    if days >= 7:
        status = PASS
        message = "At least seven collection days are available."
    elif days >= 2:
        status = REVIEW
        message = "Multiple days exist, but a longer history is recommended."
    else:
        status = REVIEW
        message = "Only one collection day exists; daily movement cannot yet be validated."

    return result(
        "time_series_depth",
        status,
        days,
        7,
        message,
    )


def check_fare_outliers(df: pd.DataFrame) -> dict:
    """Flag extreme fare values using a robust IQR rule.

    This check does not delete or alter observations. It only flags them for
    review because genuine dynamic-fare spikes may be economically meaningful.
    """
    fares = df["total_fare"].dropna()

    if fares.empty:
        return result(
            "fare_outlier_screen",
            FAIL,
            None,
            None,
            "No fare observations available.",
        )

    q1 = fares.quantile(0.25)
    q3 = fares.quantile(0.75)
    iqr = q3 - q1
    upper = q3 + 3.0 * iqr
    lower = max(0.0, q1 - 3.0 * iqr)

    flagged = int(((fares < lower) | (fares > upper)).sum())

    return result(
        "fare_outlier_screen",
        REVIEW if flagged > 0 else PASS,
        flagged,
        0,
        (
            f"{flagged:,} fares flagged for review using a 3×IQR screen."
            if flagged > 0
            else "No extreme fares detected by the 3×IQR screen."
        ),
    )


def check_dgca_weights() -> dict:
    """Validate the six DGCA route weights."""
    if not DGCA_WEIGHTS_PATH.exists():
        return result(
            "dgca_weight_integrity",
            FAIL,
            None,
            1.0,
            "DGCA route-weight file is missing.",
        )

    weights = pd.read_csv(DGCA_WEIGHTS_PATH)

    if "route_weight" not in weights.columns:
        return result(
            "dgca_weight_integrity",
            FAIL,
            None,
            1.0,
            "DGCA file does not contain route_weight.",
        )

    routes = set(weights["route"].dropna())
    missing = EXPECTED_ROUTES - routes

    values = pd.to_numeric(
        weights["route_weight"],
        errors="coerce",
    ).dropna()

    total = float(values.sum()) if not values.empty else 0.0

    if missing:
        status = FAIL
        message = "Missing routes: " + ", ".join(sorted(missing))
    elif (values < 0).any():
        status = FAIL
        message = "Negative route weights found."
    elif not np.isclose(total, 1.0, atol=1e-6):
        status = REVIEW
        message = f"Route weights sum to {total:.8f}; normalization may be required."
    else:
        status = PASS
        message = "Six DGCA route weights are present and sum to 1."

    return result(
        "dgca_weight_integrity",
        status,
        total,
        1.0,
        message,
    )


def check_route_index_coverage() -> dict:
    """Check route-index coverage if the route output exists."""
    if not ROUTE_INDEX_PATH.exists():
        return result(
            "route_index_output",
            FAIL,
            None,
            None,
            "Daily route-index output is missing.",
        )

    route = pd.read_csv(ROUTE_INDEX_PATH)

    if "route" not in route.columns or "route_index" not in route.columns:
        return result(
            "route_index_output",
            FAIL,
            None,
            len(EXPECTED_ROUTES),
            "Route-index output has an unexpected schema.",
        )

    present = set(route["route"].dropna())
    missing = sorted(EXPECTED_ROUTES - present)

    return result(
        "route_index_output",
        PASS if not missing else REVIEW,
        len(present & EXPECTED_ROUTES),
        len(EXPECTED_ROUTES),
        "All APIx routes appear in the route-index output."
        if not missing
        else "Missing route-index routes: " + ", ".join(missing),
    )


def check_index_integrity() -> dict:
    """Check APIx daily index numerical integrity."""
    if not DAILY_INDEX_PATH.exists():
        return result(
            "index_integrity",
            FAIL,
            None,
            None,
            "Daily APIx index output is missing.",
        )

    index = pd.read_csv(DAILY_INDEX_PATH)

    if "apix_index" not in index.columns:
        return result(
            "index_integrity",
            FAIL,
            None,
            100.0,
            "Daily index output has no apix_index column.",
        )

    values = pd.to_numeric(index["apix_index"], errors="coerce")

    invalid = int(
        (values.isna() | ~np.isfinite(values)).sum()
    )

    base_ok = (
        not index.empty
        and np.isclose(float(values.iloc[0]), 100.0, atol=1e-6)
    )

    if invalid > 0:
        status = FAIL
        message = f"{invalid:,} invalid APIx index values found."
    elif not base_ok:
        status = FAIL
        message = "First APIx index value is not 100."
    else:
        status = PASS
        message = "APIx index values are finite and the base is 100."

    return result(
        "index_integrity",
        status,
        {
            "rows": int(len(index)),
            "invalid_values": invalid,
            "base_is_100": bool(base_ok),
        },
        "finite values; first value = 100",
        message,
    )


def run_checks() -> list[dict]:
    """Run all QC checks."""
    history = load_history()

    return [
        check_missing_values(history),
        check_duplicate_keys(history),
        check_positive_fares(history),
        check_routes(history),
        check_lead_times(history),
        check_fare_classes(history),
        check_collection_days(history),
        check_fare_outliers(history),
        check_dgca_weights(),
        check_route_index_coverage(),
        check_index_integrity(),
    ]


def main() -> None:
    print("=" * 64)
    print("APIx — STATISTICAL QUALITY-CONTROL ENGINE")
    print("=" * 64)

    checks = run_checks()
    results = pd.DataFrame(checks)

    counts = results["status"].value_counts().to_dict()

    if counts.get(FAIL, 0) > 0:
        overall_status = FAIL
    elif counts.get(REVIEW, 0) > 0:
        overall_status = REVIEW
    else:
        overall_status = PASS

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results.to_csv(RESULTS_PATH, index=False)

    report = {
        "project": "India Real-Time Airfare Price Index (APIx)",
        "component": "statistical quality-control engine",
        "overall_status": overall_status,
        "checks_total": int(len(results)),
        "pass_count": int(counts.get(PASS, 0)),
        "review_count": int(counts.get(REVIEW, 0)),
        "fail_count": int(counts.get(FAIL, 0)),
        "checks": checks,
        "principles": [
            "QC flags observations; it does not silently delete genuine fares.",
            "Extreme fares are reviewed because dynamic pricing can create legitimate spikes.",
            "One collection day is a REVIEW condition, not a data-processing failure.",
            "ML predictions are not used to validate or calculate the observed-fare APIx index.",
        ],
    }

    with open(REPORT_PATH, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    print("\n=== QC RESULTS ===")
    for item in checks:
        print(
            f"[{item['status']:<6}] "
            f"{item['check']}: {item['message']}"
        )

    print("\n=== OVERALL STATUS ===")
    print(overall_status)

    print("\n=== SUMMARY ===")
    print(f"PASS:   {report['pass_count']}")
    print(f"REVIEW: {report['review_count']}")
    print(f"FAIL:   {report['fail_count']}")

    print("\n=== FILES SAVED ===")
    print(f"✓ {RESULTS_PATH}")
    print(f"✓ {REPORT_PATH}")


if __name__ == "__main__":
    main()
