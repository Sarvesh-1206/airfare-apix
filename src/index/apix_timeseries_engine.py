"""Build multi-day APIx time-series from cumulative live fares."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[2]
HISTORY_PATH = BASE_DIR / "data" / "processed" / "airfare_live_history.parquet"
DGCA_WEIGHTS_PATH = BASE_DIR / "data" / "metadata" / "dgca_route_weights.csv"
OUTPUT_DIR = BASE_DIR / "data" / "metadata"

DAILY_INDEX_PATH = OUTPUT_DIR / "apix_daily_index.csv"
STRATA_INDEX_PATH = OUTPUT_DIR / "apix_daily_strata.csv"
ROUTE_INDEX_PATH = OUTPUT_DIR / "apix_daily_route_index.csv"
SUMMARY_PATH = OUTPUT_DIR / "apix_timeseries_summary.json"

ROUTES = ["DEL-BOM", "DEL-BLR", "BOM-BLR", "DEL-CCU", "DEL-HYD", "DEL-MAA"]
LEAD_TIMES = [1, 7, 15, 30, 45]
FARE_CLASSES = ["Economy", "Business"]


def load_history():
    if not HISTORY_PATH.exists():
        raise FileNotFoundError(f"History not found: {HISTORY_PATH}")
    df = pd.read_parquet(HISTORY_PATH).copy()
    required = [
        "collection_timestamp", "advance_purchase_days", "route",
        "fare_class", "total_fare"
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("History missing columns: " + ", ".join(missing))

    df["collection_timestamp"] = pd.to_datetime(df["collection_timestamp"], errors="coerce")
    df["collection_date"] = df["collection_timestamp"].dt.normalize()
    df["advance_purchase_days"] = pd.to_numeric(df["advance_purchase_days"], errors="coerce")
    df["total_fare"] = pd.to_numeric(df["total_fare"], errors="coerce")
    df = df.dropna(subset=["collection_date", "route", "fare_class",
                           "advance_purchase_days", "total_fare"])
    df = df[(df["total_fare"] > 0) &
            df["route"].isin(ROUTES) &
            df["fare_class"].isin(FARE_CLASSES)]
    df["advance_purchase_days"] = df["advance_purchase_days"].round().astype(int)
    return df[df["advance_purchase_days"].isin(LEAD_TIMES)].copy()


def load_weights():
    if not DGCA_WEIGHTS_PATH.exists():
        raise FileNotFoundError(f"DGCA weights not found: {DGCA_WEIGHTS_PATH}")
    w = pd.read_csv(DGCA_WEIGHTS_PATH)
    if not {"route", "route_weight"}.issubset(w.columns):
        raise ValueError(
            "DGCA weights must contain route and route_weight columns."
    )
    w = w[["route", "route_weight"]].copy()
    w["route_weight"] = pd.to_numeric(
        w["route_weight"],
        errors="coerce",
    )

    w = w.rename(
        columns={"route_weight": "weight"}
    )
    w = w.dropna(subset=["route", "weight"])
    w = w[w["route"].isin(ROUTES)]
    if set(w["route"]) != set(ROUTES):
        raise ValueError("DGCA weights do not contain all six APIx routes.")
    total = w["weight"].sum()
    if total <= 0:
        raise ValueError("DGCA weights sum to zero.")
    w["weight"] /= total
    return w


def aggregate(df):
    return (
        df.groupby(["collection_date", "route", "fare_class",
                    "advance_purchase_days"], as_index=False)
        .agg(average_fare=("total_fare", "mean"),
             observations=("total_fare", "size"))
    )


def calculate_relatives(daily):
    base_date = daily["collection_date"].min()
    base = daily[daily["collection_date"] == base_date][
        ["route", "fare_class", "advance_purchase_days", "average_fare"]
    ].rename(columns={"average_fare": "base_fare"})

    out = daily.merge(
        base,
        on=["route", "fare_class", "advance_purchase_days"],
        how="left",
    )
    out["price_relative"] = out["average_fare"].div(out["base_fare"]).mul(100)
    out = out[(out["base_fare"] > 0) & np.isfinite(out["price_relative"])].copy()
    return out, base_date


def build_route_index(relatives, weights):
    route = (
        relatives.groupby(["collection_date", "route"], as_index=False)
        .agg(route_index=("price_relative", "mean"),
             available_strata=("price_relative", "size"),
             route_observations=("observations", "sum"))
        .merge(weights, on="route", how="left")
    )
    return route.sort_values(["collection_date", "route"]).reset_index(drop=True)


def build_composite(route):
    records = []
    for date, g in route.groupby("collection_date"):
        g = g.dropna(subset=["route_index", "weight"])
        if g.empty:
            continue
        coverage = g["weight"].sum()
        ew = g["weight"] / coverage
        records.append({
            "collection_date": date,
            "apix_index": float((g["route_index"] * ew).sum()),
            "routes_available": int(g["route"].nunique()),
            "routes_expected": len(ROUTES),
            "route_weight_coverage": float(coverage),
            "route_observations": int(g["route_observations"].sum()),
        })
    return pd.DataFrame(records).sort_values("collection_date").reset_index(drop=True)


def main():
    print("=" * 64)
    print("APIx — MULTI-DAY TIME-SERIES ENGINE")
    print("=" * 64)

    history = load_history()
    weights = load_weights()

    print(f"\nHistory observations: {len(history):,}")
    print(f"Collection days:     {history['collection_date'].nunique():,}")

    if history["collection_date"].nunique() < 2:
        print("\n⚠ Only one collection day is available.")
        print("Base index will be calculated, but day-to-day movement needs more days.")

    print("\nDGCA route weights:")
    for r in weights.itertuples(index=False):
        print(f"  {r.route}: {r.weight:.6f}")

    daily = aggregate(history)
    relatives, base_date = calculate_relatives(daily)
    route = build_route_index(relatives, weights)
    composite = build_composite(route)

    if composite.empty:
        raise ValueError("No APIx composite observations could be calculated.")

    first = composite.iloc[0]["apix_index"]
    composite["apix_index"] = composite["apix_index"].div(first).mul(100)
    composite["daily_change_pct"] = composite["apix_index"].pct_change().mul(100)
    composite["cumulative_change_pct"] = composite["apix_index"].div(100).sub(1).mul(100)

    strata = (
        relatives.groupby(["collection_date", "fare_class",
                           "advance_purchase_days"], as_index=False)
        .agg(index=("price_relative", "mean"),
             observations=("observations", "sum"))
        .sort_values(["collection_date", "fare_class", "advance_purchase_days"])
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    composite.to_csv(DAILY_INDEX_PATH, index=False)
    strata.to_csv(STRATA_INDEX_PATH, index=False)
    route.to_csv(ROUTE_INDEX_PATH, index=False)

    summary = {
        "project": "India Real-Time Airfare Price Index (APIx)",
        "component": "multi-day time-series index engine",
        "methodology": "Observed total-fare price relatives with DGCA two-way passenger-traffic route weights.",
        "ml_used_in_index": False,
        "base_collection_date": str(base_date.date()),
        "collection_start": str(composite["collection_date"].min().date()),
        "collection_end": str(composite["collection_date"].max().date()),
        "collection_days": int(composite["collection_date"].nunique()),
        "history_observations": int(len(history)),
        "valid_relative_records": int(len(relatives)),
        "base_index": 100.0,
        "latest_index": float(composite.iloc[-1]["apix_index"]),
        "latest_cumulative_change_pct": float(composite.iloc[-1]["cumulative_change_pct"]),
        "route_weights": {r.route: float(r.weight) for r in weights.itertuples(index=False)},
        "notes": [
            "ML predictions are not used to calculate APIx.",
            "The first collection day is the base period.",
            "Available DGCA route weights are renormalized on days with missing routes.",
            "A meaningful time series requires multiple collection days."
        ],
    }
    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    display_cols = ["collection_date", "apix_index", "daily_change_pct",
                    "cumulative_change_pct", "routes_available",
                    "route_weight_coverage", "route_observations"]
    display = composite[display_cols].copy()
    nums = display.select_dtypes(include=np.number).columns
    display[nums] = display[nums].round(2)

    print("\n=== APIx DAILY INDEX ===")
    print(display.to_string(index=False))
    print("\n=== FILES SAVED ===")
    print(f"✓ {DAILY_INDEX_PATH}")
    print(f"✓ {STRATA_INDEX_PATH}")
    print(f"✓ {ROUTE_INDEX_PATH}")
    print(f"✓ {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
