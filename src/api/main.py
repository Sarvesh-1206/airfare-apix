"""FastAPI service for the India Real-Time Airfare Price Index (APIx)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Query

BASE_DIR = Path(__file__).resolve().parents[2]
METADATA_DIR = BASE_DIR / "data" / "metadata"

DAILY_INDEX_PATH = METADATA_DIR / "apix_daily_index.csv"
ROUTE_INDEX_PATH = METADATA_DIR / "apix_daily_route_index.csv"
STRATA_INDEX_PATH = METADATA_DIR / "apix_daily_strata.csv"
QC_REPORT_PATH = METADATA_DIR / "apix_qc_report.json"
TIMESERIES_SUMMARY_PATH = METADATA_DIR / "apix_timeseries_summary.json"

app = FastAPI(
    title="India Real-Time Airfare Price Index (APIx)",
    description=(
        "Read-only API service for the observed-fare APIx index, "
        "route-level indices, lead-time strata, and QC status."
    ),
    version="1.0.0",
)


def _read_csv(path: Path) -> pd.DataFrame:
    """Read an APIx CSV output or raise a service error."""
    if not path.exists():
        raise HTTPException(
            status_code=503,
            detail=f"Required APIx output is not available: {path.name}",
        )

    try:
        return pd.read_csv(path)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to read {path.name}: {exc}",
        ) from exc


def _read_json(path: Path) -> dict[str, Any]:
    """Read an APIx JSON output or raise a service error."""
    if not path.exists():
        raise HTTPException(
            status_code=503,
            detail=f"Required APIx report is not available: {path.name}",
        )

    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to read {path.name}: {exc}",
        ) from exc


def _clean_value(value: Any) -> Any:
    """Convert pandas/numpy values into JSON-safe values."""
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a DataFrame into JSON-safe records."""
    records = df.to_dict(orient="records")
    return [
        {key: _clean_value(value) for key, value in record.items()}
        for record in records
    ]


@app.get("/", tags=["system"])
def root() -> dict[str, Any]:
    """Basic API service information."""
    return {
        "service": "APIx FastAPI Service",
        "project": "India Real-Time Airfare Price Index (APIx)",
        "version": app.version,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["system"])
def health() -> dict[str, Any]:
    """Report whether the APIx output layer is available."""
    files = {
        "daily_index": DAILY_INDEX_PATH,
        "route_index": ROUTE_INDEX_PATH,
        "strata_index": STRATA_INDEX_PATH,
        "qc_report": QC_REPORT_PATH,
        "timeseries_summary": TIMESERIES_SUMMARY_PATH,
    }

    availability = {
        name: path.exists()
        for name, path in files.items()
    }

    return {
        "status": "healthy" if all(availability.values()) else "degraded",
        "outputs": availability,
    }


@app.get("/api/v1/index/latest", tags=["index"])
def latest_index() -> dict[str, Any]:
    """Return the latest available APIx observation."""
    df = _read_csv(DAILY_INDEX_PATH)

    if df.empty:
        raise HTTPException(
            status_code=404,
            detail="No APIx index observations are available.",
        )

    row = df.iloc[-1]

    return {
        "index": "APIx",
        "date": _clean_value(row.get("collection_date")),
        "value": _clean_value(row.get("apix_index")),
        "daily_change_pct": _clean_value(row.get("daily_change_pct")),
        "cumulative_change_pct": _clean_value(
            row.get("cumulative_change_pct")
        ),
        "routes_available": _clean_value(row.get("routes_available")),
        "route_weight_coverage": _clean_value(
            row.get("route_weight_coverage")
        ),
    }


@app.get("/api/v1/index/history", tags=["index"])
def index_history(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> dict[str, Any]:
    """Return the APIx daily time series, optionally filtered by date."""
    df = _read_csv(DAILY_INDEX_PATH)

    if "collection_date" not in df.columns:
        raise HTTPException(
            status_code=500,
            detail="Daily index output has no collection_date column.",
        )

    df["collection_date"] = pd.to_datetime(
        df["collection_date"],
        errors="coerce",
    )

    if start_date:
        start = pd.to_datetime(start_date, errors="coerce")
        if pd.isna(start):
            raise HTTPException(
                status_code=400,
                detail="Invalid start_date. Use YYYY-MM-DD.",
            )
        df = df[df["collection_date"] >= start]

    if end_date:
        end = pd.to_datetime(end_date, errors="coerce")
        if pd.isna(end):
            raise HTTPException(
                status_code=400,
                detail="Invalid end_date. Use YYYY-MM-DD.",
            )
        df = df[df["collection_date"] <= end]

    df["collection_date"] = df["collection_date"].dt.strftime("%Y-%m-%d")

    return {
        "index": "APIx",
        "count": int(len(df)),
        "data": _records(df),
    }


@app.get("/api/v1/index/routes", tags=["index"])
def route_indices(
    date: str | None = Query(default=None),
) -> dict[str, Any]:
    """Return route-level APIx indices."""
    df = _read_csv(ROUTE_INDEX_PATH)

    if "collection_date" not in df.columns:
        raise HTTPException(
            status_code=500,
            detail="Route index output has no collection_date column.",
        )

    if date:
        requested = pd.to_datetime(date, errors="coerce")
        if pd.isna(requested):
            raise HTTPException(
                status_code=400,
                detail="Invalid date. Use YYYY-MM-DD.",
            )

        dates = pd.to_datetime(df["collection_date"], errors="coerce")
        df = df[dates.dt.normalize() == requested.normalize()]

    return {
        "index": "APIx",
        "date": date,
        "count": int(len(df)),
        "data": _records(df),
    }


@app.get("/api/v1/index/lead-times", tags=["index"])
def lead_time_indices(
    date: str | None = Query(default=None),
    fare_class: str | None = Query(default=None),
) -> dict[str, Any]:
    """Return APIx strata by lead time and fare class."""
    df = _read_csv(STRATA_INDEX_PATH)

    if "collection_date" not in df.columns:
        raise HTTPException(
            status_code=500,
            detail="Strata output has no collection_date column.",
        )

    if date:
        requested = pd.to_datetime(date, errors="coerce")
        if pd.isna(requested):
            raise HTTPException(
                status_code=400,
                detail="Invalid date. Use YYYY-MM-DD.",
            )
        dates = pd.to_datetime(df["collection_date"], errors="coerce")
        df = df[dates.dt.normalize() == requested.normalize()]

    if fare_class:
        df = df[
            df["fare_class"].astype(str).str.casefold()
            == fare_class.casefold()
        ]

    return {
        "index": "APIx",
        "date": date,
        "fare_class": fare_class,
        "count": int(len(df)),
        "data": _records(df),
    }


@app.get("/api/v1/quality", tags=["quality"])
def quality_report() -> dict[str, Any]:
    """Return the latest APIx QC report."""
    report = _read_json(QC_REPORT_PATH)

    return {
        "index": "APIx",
        "overall_status": report.get("overall_status"),
        "pass_count": report.get("pass_count"),
        "review_count": report.get("review_count"),
        "fail_count": report.get("fail_count"),
        "checks": report.get("checks", []),
    }


@app.get("/api/v1/summary", tags=["system"])
def summary() -> dict[str, Any]:
    """Return the latest APIx time-series summary."""
    return _read_json(TIMESERIES_SUMMARY_PATH)
