"""Datetime feature engineering for APIx datasets."""

from __future__ import annotations

import pandas as pd


def add_datetime_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add datetime-derived features for live and historical datasets."""

    df = df.copy()

    # ---------------------------------------------------------
    # Determine the travel date
    # ---------------------------------------------------------

    if "travel_date" in df.columns:
        travel_date = pd.to_datetime(
            df["travel_date"],
            errors="coerce",
        )

    elif "date" in df.columns:
        travel_date = pd.to_datetime(
            df["date"],
            errors="coerce",
        )

        # Keep a canonical travel_date column.
        df["travel_date"] = travel_date

    else:
        raise ValueError(
            "Dataset must contain either 'travel_date' or 'date'."
        )

    # ---------------------------------------------------------
    # Travel-date features
    # ---------------------------------------------------------

    df["travel_day_of_week"] = travel_date.dt.dayofweek

    df["travel_day_name"] = travel_date.dt.day_name()

    df["travel_month"] = travel_date.dt.month

    df["travel_month_name"] = travel_date.dt.month_name()

    df["travel_quarter"] = travel_date.dt.quarter

    df["travel_year"] = travel_date.dt.year

    df["is_weekend"] = (
        travel_date.dt.dayofweek >= 5
    ).astype("int8")

    # ---------------------------------------------------------
    # Departure and arrival time features
    # ---------------------------------------------------------

    if "departure_time" in df.columns:

        departure_time = pd.to_datetime(
            df["departure_time"],
            format="%H:%M",
            errors="coerce",
        )

        df["departure_hour"] = departure_time.dt.hour

    elif "dep_time" in df.columns:

        departure_time = pd.to_datetime(
            df["dep_time"],
            format="%H:%M",
            errors="coerce",
        )

        df["departure_hour"] = departure_time.dt.hour

    else:

        df["departure_hour"] = pd.NA

    if "arrival_time" in df.columns:

        arrival_time = pd.to_datetime(
            df["arrival_time"],
            format="%H:%M",
            errors="coerce",
        )

        df["arrival_hour"] = arrival_time.dt.hour

    elif "arr_time" in df.columns:

        arrival_time = pd.to_datetime(
            df["arr_time"],
            format="%H:%M",
            errors="coerce",
        )

        df["arrival_hour"] = arrival_time.dt.hour

    else:

        df["arrival_hour"] = pd.NA

    # ---------------------------------------------------------
    # Live-data search-date features
    # ---------------------------------------------------------

    if "search_date" in df.columns:

        search_date = pd.to_datetime(
            df["search_date"],
            errors="coerce",
        )

        df["search_day_of_week"] = search_date.dt.dayofweek

        df["search_month"] = search_date.dt.month

        df["search_quarter"] = search_date.dt.quarter

    else:

        # Historical data has no search date.
        # We intentionally do NOT fabricate one.
        df["search_day_of_week"] = pd.NA

        df["search_month"] = pd.NA

        df["search_quarter"] = pd.NA

    # ---------------------------------------------------------
    # Collection timestamp features
    # ---------------------------------------------------------

    if "collection_timestamp" in df.columns:

        collection_timestamp = pd.to_datetime(
            df["collection_timestamp"],
            errors="coerce",
        )

        df["collection_hour"] = (
            collection_timestamp.dt.hour
        )

        df["collection_day_of_week"] = (
            collection_timestamp.dt.dayofweek
        )

    else:

        # Historical dataset has no collection timestamp.
        df["collection_hour"] = pd.NA

        df["collection_day_of_week"] = pd.NA

    return df