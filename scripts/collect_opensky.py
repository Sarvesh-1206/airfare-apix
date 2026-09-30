from pathlib import Path
from datetime import datetime, timezone

import httpx
import pandas as pd


OPENSKY_URL = "https://opensky-network.org/api/states/all"

OUTPUT_PATH = Path(
    "data/processed/opensky_live_history.parquet"
)


# India-focused bounding box
PARAMS = {
    "lamin": 6,
    "lomin": 68,
    "lamax": 37,
    "lomax": 98,
}


def fetch_opensky() -> dict:
    response = httpx.get(
        OPENSKY_URL,
        params=PARAMS,
        timeout=20,
    )

    response.raise_for_status()
    return response.json()


def normalize(data: dict) -> pd.DataFrame:
    rows = []

    snapshot_timestamp = data.get("time")

    for state in data.get("states") or []:
        if len(state) < 17:
            continue

        rows.append(
            {
                "snapshot_timestamp": snapshot_timestamp,
                "snapshot_datetime": (
                    datetime.fromtimestamp(
                        snapshot_timestamp,
                        tz=timezone.utc,
                    )
                    if snapshot_timestamp
                    else None
                ),
                "icao24": state[0],
                "callsign": (
                    state[1].strip()
                    if isinstance(state[1], str)
                    else None
                ),
                "origin_country": state[2],
                "time_position": state[3],
                "last_contact": state[4],
                "longitude": state[5],
                "latitude": state[6],
                "baro_altitude": state[7],
                "on_ground": state[8],
                "velocity": state[9],
                "true_track": state[10],
                "vertical_rate": state[11],
                "geo_altitude": state[13],
                "squawk": state[14],
                "position_source": state[16],
            }
        )

    return pd.DataFrame(rows)


def append_to_parquet(df: pd.DataFrame) -> None:
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if OUTPUT_PATH.exists():
        old_df = pd.read_parquet(OUTPUT_PATH)
        combined = pd.concat(
            [old_df, df],
            ignore_index=True,
        )
    else:
        combined = df

    combined = combined.drop_duplicates(
        subset=[
            "snapshot_timestamp",
            "icao24",
        ],
        keep="last",
    )

    combined.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    print(f"Saved: {OUTPUT_PATH}")
    print(f"Rows: {len(combined)}")


def main() -> None:
    print("Fetching OpenSky live data...")

    data = fetch_opensky()

    print(
        f"OpenSky timestamp: {data.get('time')}"
    )

    print(
        f"Raw aircraft count: "
        f"{len(data.get('states') or [])}"
    )

    df = normalize(data)

    print(f"Normalized rows: {len(df)}")

    append_to_parquet(df)


if __name__ == "__main__":
    main()