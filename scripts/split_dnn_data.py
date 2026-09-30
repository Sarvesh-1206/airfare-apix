from pathlib import Path

import pandas as pd


INPUT_PATH = Path("data/training/dnn_base.parquet")
OUTPUT_DIR = Path("data/training/splits")


def main() -> None:
    df = pd.read_parquet(INPUT_PATH)

    # Reconstruct date from travel features if date is no longer present.
    # The original dataset spans 2022-02-11 through 2022-03-31.
    #
    # For this first version, recover the chronological order using
    # the original feature columns.
    # travel_year + travel_month + travel_day_of_week is not enough
    # to reconstruct exact date, so load the original source alongside
    # dnn_base instead.

    # Use split_date already prepared in dnn_base
    if "split_date" not in df.columns:
        raise ValueError(
            "split_date column is missing from DNN dataset."
        )

    df["split_date"] = pd.to_datetime(
        df["split_date"],
        errors="coerce",
    )

    if df["split_date"].isna().any():
        raise ValueError(
            "Invalid or missing split_date values found."
    )

    df = df.sort_values("split_date").reset_index(drop=True)

    unique_dates = sorted(
        df["split_date"].dt.normalize().unique()
    )

    n_dates = len(unique_dates)

    train_end = unique_dates[int(n_dates * 0.70)]
    val_end = unique_dates[int(n_dates * 0.85)]

    train = df[df["split_date"] <= train_end].copy()

    val = df[
        (df["split_date"] > train_end)
        & (df["split_date"] <= val_end)
    ].copy()

    test = df[
        df["split_date"] > val_end
    ].copy()

    for name, part in [
        ("train", train),
        ("validation", val),
        ("test", test),
    ]:
        output = OUTPUT_DIR / f"{name}.parquet"
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        part.drop(columns=["split_date"]).to_parquet(
            output,
            index=False,
        )

        print(
            f"{name}: {len(part):,} rows | "
            f"{part['split_date'].min().date()} → "
            f"{part['split_date'].max().date()}"
        )

    print("\nSaved splits to:", OUTPUT_DIR)


if __name__ == "__main__":
    main()