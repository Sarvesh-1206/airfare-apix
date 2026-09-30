"""DGCA passenger-traffic weighting engine for APIx V1."""

from pathlib import Path
import json
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]

INPUT_PATH = BASE_DIR / "data" / "raw" / "aviation" / "dgca_city_pair_traffic_raw.csv"
PROCESSED_PATH = BASE_DIR / "data" / "processed" / "dgca_city_pair_traffic.parquet"
WEIGHTS_PATH = BASE_DIR / "data" / "metadata" / "dgca_route_weights.csv"
SUMMARY_PATH = BASE_DIR / "data" / "metadata" / "dgca_weight_summary.json"

# Routes currently represented by the live APIx basket.
ROUTE_CITY_MAP = {
    "DEL-BOM": {"DEL", "BOM"},
    "DEL-BLR": {"DEL", "BLR"},
    "BOM-BLR": {"BOM", "BLR"},
    "DEL-CCU": {"DEL", "CCU"},
    "DEL-HYD": {"DEL", "HYD"},
    "DEL-MAA": {"DEL", "MAA"},
}

CITY_ALIASES = {
    "DELHI": "DEL",
    "NEW DELHI": "DEL",
    "MUMBAI": "BOM",
    "BOMBAY": "BOM",
    "BENGALURU": "BLR",
    "BANGALORE": "BLR",
    "KOLKATA": "CCU",
    "CALCUTTA": "CCU",
    "HYDERABAD": "HYD",
    "CHENNAI": "MAA",
    "MADRAS": "MAA",
}

def load_raw_data():
    """Load the DGCA export, including quoted commas inside city names."""

    import csv

    print(f"Loading: {INPUT_PATH}")

    rows = []

    with open(
        INPUT_PATH,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.reader(
            file,
            delimiter=",",
            quotechar='"',
            doublequote=True,
        )

        for row in reader:
            if not row:
                continue

            # Some DGCA exports wrap the entire row in quotes.
            # If that happens, csv.reader returns the whole row
            # as one field. Parse that field one more time.
            if len(row) == 1 and "," in row[0]:

                inner_reader = csv.reader(
                    [row[0]],
                    delimiter=",",
                    quotechar='"',
                    doublequote=True,
                )

                row = next(inner_reader)

            rows.append(
                [value.strip() for value in row]
            )

    if not rows:
        raise ValueError(
            "DGCA file is empty."
        )

    header = rows[0]

    expected_columns = [
        "Year",
        "Month",
        "City1",
        "City2",
        "PaxToCity2",
        "PaxFromCity2",
        "FreightToCity2",
        "FreightFromCity2",
        "MailToCity2",
        "MailFromCity2",
    ]

    if header != expected_columns:
        print("\nDetected header:")
        print(header)

    valid_rows = []
    malformed_rows = 0

    for row_number, row in enumerate(
        rows[1:],
        start=2,
    ):

        if len(row) != len(header):
            malformed_rows += 1

            print(
                f"Skipping malformed row {row_number}: "
                f"{len(row)} fields"
            )

            continue

        valid_rows.append(row)

    df = pd.DataFrame(
        valid_rows,
        columns=header,
    )

    required = [
        "Year",
        "Month",
        "City1",
        "City2",
        "PaxToCity2",
        "PaxFromCity2",
    ]

    missing = [
        column
        for column in required
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            "Missing required DGCA columns: "
            + ", ".join(missing)
        )

    print(f"Loaded columns: {len(df.columns)}")
    print(f"Loaded rows: {len(df):,}")

    if malformed_rows:
        print(
            f"Malformed rows skipped: "
            f"{malformed_rows:,}"
        )

    return df


def normalize_city(value):
    """Normalize DGCA city names to APIx airport-style codes."""
    if pd.isna(value):
        return None

    city = str(value).strip().upper()
    return CITY_ALIASES.get(city, city)


def build_route(city1, city2):
    """Build a canonical alphabetical airport-code route."""
    if not city1 or not city2 or city1 == city2:
        return None

    pair = {city1, city2}

    for route, cities in ROUTE_CITY_MAP.items():
        if pair == cities:
            return route

    return None


def clean_data(df):
    """Clean and normalize DGCA city-pair passenger observations."""
    data = df.copy()

    data["year"] = pd.to_numeric(data["Year"], errors="coerce")
    data["month"] = pd.to_numeric(data["Month"], errors="coerce")

    data["city1"] = data["City1"].map(normalize_city)
    data["city2"] = data["City2"].map(normalize_city)

    data["pax_to_city2"] = pd.to_numeric(
        data["PaxToCity2"], errors="coerce"
    )
    data["pax_from_city2"] = pd.to_numeric(
        data["PaxFromCity2"], errors="coerce"
    )

    data["passengers"] = (
        data["pax_to_city2"].fillna(0)
        + data["pax_from_city2"].fillna(0)
    )

    data["route"] = [
        build_route(a, b)
        for a, b in zip(data["city1"], data["city2"])
    ]

    data = data[
        data["year"].notna()
        & data["month"].notna()
        & data["route"].notna()
    ].copy()

    data["year"] = data["year"].astype(int)
    data["month"] = data["month"].astype(int)

    data = data[
        data["month"].between(1, 12)
        & (data["passengers"] >= 0)
    ].copy()

    result = data[
        [
            "year",
            "month",
            "city1",
            "city2",
            "route",
            "pax_to_city2",
            "pax_from_city2",
            "passengers",
        ]
    ].copy()

    result["source"] = "DGCA"

    return result


def aggregate_route_traffic(cleaned):
    """Aggregate monthly city-pair traffic into route traffic."""
    return (
        cleaned.groupby("route", as_index=False)
        .agg(
            passengers=("passengers", "sum"),
            months_available=("month", "count"),
            first_year=("year", "min"),
            last_year=("year", "max"),
        )
    )


def calculate_weights(route_traffic):
    """Convert passenger traffic into normalized route weights."""
    result = route_traffic.copy()

    total = result["passengers"].sum()

    if total <= 0:
        raise ValueError("Total passenger traffic must be positive.")

    result["route_weight"] = (
        result["passengers"] / total
    )

    return result.sort_values(
        "route_weight", ascending=False
    ).reset_index(drop=True)


def main():
    print("=" * 60)
    print("DGCA WEIGHTS — APIx V1")
    print("=" * 60)

    raw = load_raw_data()

    print(f"Raw rows: {len(raw):,}")

    cleaned = clean_data(raw)

    print(f"Relevant cleaned rows: {len(cleaned):,}")

    route_traffic = aggregate_route_traffic(cleaned)
    weights = calculate_weights(route_traffic)

    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    WEIGHTS_PATH.parent.mkdir(parents=True, exist_ok=True)

    cleaned.to_parquet(PROCESSED_PATH, index=False)
    weights.to_csv(WEIGHTS_PATH, index=False)

    summary = {
        "project": "India Real-Time Airfare Price Index (APIx)",
        "component": "DGCA passenger-traffic route weights",
        "source": "DGCA",
        "raw_rows": int(len(raw)),
        "relevant_rows": int(len(cleaned)),
        "routes_in_basket": sorted(weights["route"].tolist()),
        "total_passengers": float(weights["passengers"].sum()),
        "weight_sum": float(weights["route_weight"].sum()),
        "method": (
            "Two-way passenger traffic by city pair, "
            "normalized across the APIx route basket."
        ),
    }

    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n=== DGCA ROUTE WEIGHTS ===")
    print(
        weights[
            ["route", "passengers", "route_weight"]
        ].to_string(index=False)
    )

    print("\nWeight sum:", round(weights["route_weight"].sum(), 6))

    print("\n=== FILES SAVED ===")
    print(f"✓ {PROCESSED_PATH}")
    print(f"✓ {WEIGHTS_PATH}")
    print(f"✓ {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
