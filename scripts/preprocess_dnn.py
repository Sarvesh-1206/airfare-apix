
from pathlib import Path
import re

import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


INPUT_DIR = Path("data/training/splits")
OUTPUT_DIR = Path("data/training/processed")
ARTIFACT_DIR = Path("artifacts")


TARGET = "total_fare"


CATEGORICAL_COLUMNS = [
    "airline",
    "dep_time",
    "from",
    "arr_time",
    "to",
    "fare_class",
    "airline_iata_code",
    "origin",
    "destination",
    "route",
    "currency",
    "booking_source",
    "travel_day_name",
    "travel_month_name",
    "route_direction",
]


NUMERICAL_COLUMNS = [
    "time_taken",
    "flight_duration_minutes",
    "stops",
    "travel_day_of_week",
    "travel_month",
    "travel_quarter",
    "travel_year",
    "is_weekend",
    "departure_hour",
    "arrival_hour",
    "is_domestic",
    "is_origin_del",
    "is_destination_del",
    "is_origin_bom",
    "is_destination_bom",
    "is_origin_blr",
    "is_destination_blr",
    "is_origin_ccu",
    "is_destination_ccu",
    "is_origin_hyd",
    "is_destination_hyd",
    "is_origin_maa",
    "is_destination_maa",
]


def main() -> None:
    print("=" * 70)
    print("DeepAirfareNet - Preprocessing")
    print("=" * 70)

    train = pd.read_parquet(INPUT_DIR / "train.parquet")
    validation = pd.read_parquet(INPUT_DIR / "validation.parquet")
    test = pd.read_parquet(INPUT_DIR / "test.parquet")

    train = train.copy()
    validation = validation.copy()
    test = test.copy()

    # ------------------------------------------------------------
    # Convert flight duration text to minutes
    # ------------------------------------------------------------
    def duration_to_minutes(value):
        if pd.isna(value):
            return np.nan

        text = str(value).lower().strip()

        hours = 0
        minutes = 0

        hour_match = re.search(r"(\d+)\s*h", text)
        minute_match = re.search(r"(\d+)\s*m", text)

        if hour_match:
            hours = int(hour_match.group(1))

        if minute_match:
            minutes = int(minute_match.group(1))

        return hours * 60 + minutes

    for dataset in [train, validation, test]:

        dataset["time_taken"] = dataset[
            "time_taken"
        ].apply(duration_to_minutes)

        dataset[TARGET] = pd.to_numeric(
            dataset[TARGET],
            errors="coerce",
    )
        
    train = train.dropna(subset=[TARGET])
    validation = validation.dropna(subset=[TARGET])
    test = test.dropna(subset=[TARGET])

    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "encoder",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=False,
                ),
            ),
        ]
    )

    numerical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "categorical",
                categorical_pipeline,
                CATEGORICAL_COLUMNS,
            ),
            (
                "numerical",
                numerical_pipeline,
                NUMERICAL_COLUMNS,
            ),
        ],
        remainder="drop",
    )

    X_train = train[CATEGORICAL_COLUMNS + NUMERICAL_COLUMNS]
    X_validation = validation[
        CATEGORICAL_COLUMNS + NUMERICAL_COLUMNS
    ]
    X_test = test[CATEGORICAL_COLUMNS + NUMERICAL_COLUMNS]

    y_train = np.log1p(train[TARGET].to_numpy())
    y_validation = np.log1p(validation[TARGET].to_numpy())
    y_test = np.log1p(test[TARGET].to_numpy())

    print("\nFitting preprocessor on training data only...")
    X_train_processed = preprocessor.fit_transform(X_train)

    X_validation_processed = preprocessor.transform(
        X_validation
    )

    X_test_processed = preprocessor.transform(X_test)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    np.save(OUTPUT_DIR / "X_train.npy", X_train_processed)
    np.save(
        OUTPUT_DIR / "X_validation.npy",
        X_validation_processed,
    )
    np.save(OUTPUT_DIR / "X_test.npy", X_test_processed)

    np.save(OUTPUT_DIR / "y_train.npy", y_train)
    np.save(
        OUTPUT_DIR / "y_validation.npy",
        y_validation,
    )
    np.save(OUTPUT_DIR / "y_test.npy", y_test)

    joblib.dump(
        preprocessor,
        ARTIFACT_DIR / "dnn_preprocessor.joblib",
    )

    print("\nProcessed shapes:")
    print("X_train:", X_train_processed.shape)
    print("X_validation:", X_validation_processed.shape)
    print("X_test:", X_test_processed.shape)

    print("\nSaved preprocessing artifacts successfully.")
    print("=" * 70)


if __name__ == "__main__":
    main()