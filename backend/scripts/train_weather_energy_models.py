from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "real_world"
    / "germany_weather_energy_merged.csv"
)

MODEL_DIR = PROJECT_ROOT / "models" / "real_world_weather"
REPORT_PATH = MODEL_DIR / "evaluation_report.json"

TARGETS = [
    "solar_generation_mw",
    "wind_generation_mw",
    "demand_mw",
]

WEATHER_FEATURES = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "wind_speed_10m",
    "wind_speed_100m",
    "wind_direction_10m",
    "wind_direction_100m",
    "cloud_cover",
    "shortwave_radiation",
    "direct_radiation",
]


def load_data():
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Merged dataset not found: {DATA_PATH}"
        )

    df = pd.read_csv(DATA_PATH)

    required = [
        "timestamp_utc",
        *TARGETS,
        *WEATHER_FEATURES,
    ]

    missing = [c for c in required if c not in df.columns]

    if missing:
        raise ValueError(f"Missing columns: {missing}")

    df["timestamp_utc"] = pd.to_datetime(
        df["timestamp_utc"],
        utc=True,
        errors="coerce",
    )

    for column in TARGETS + WEATHER_FEATURES:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.replace([np.inf, -np.inf], np.nan)

    if df["timestamp_utc"].isna().any():
        raise ValueError("Invalid timestamps found.")

    if df["timestamp_utc"].duplicated().any():
        raise ValueError("Duplicate timestamps found.")

    df = df.sort_values("timestamp_utc").reset_index(drop=True)

    if (df[TARGETS] < 0).any().any():
        raise ValueError("Negative energy measurements found.")

    return df


def add_features(df):
    df = df.copy()

    timestamp = df["timestamp_utc"]

    df["hour"] = timestamp.dt.hour
    df["day_of_week"] = timestamp.dt.dayofweek
    df["month"] = timestamp.dt.month

    # Add calendar features that can be known at forecast time.
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["day_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
    df["day_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)

    # Build lag features only if the observation is exactly
    # 24 or 168 hours earlier. Never bridge missing-hour gaps.
    for target in TARGETS:
        for lag in (24, 168):
            lag_column = f"{target}_lag_{lag}"

            previous_timestamp = df["timestamp_utc"].shift(lag)
            elapsed = (
                df["timestamp_utc"] - previous_timestamp
            ).dt.total_seconds() / 3600

            previous_value = df[target].shift(lag)

            df[lag_column] = previous_value.where(
                elapsed == lag
            )

    return df


def calculate_metrics(actual, predicted):
    return {
        "mae_mw": float(
            mean_absolute_error(actual, predicted)
        ),
        "rmse_mw": float(
            np.sqrt(mean_squared_error(actual, predicted))
        ),
    }


def main():
    print("Loading merged real-world dataset...")
    df = add_features(load_data())

    calendar_features = [
        "hour",
        "day_of_week",
        "month",
        "hour_sin",
        "hour_cos",
        "day_sin",
        "day_cos",
    ]

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    all_results = {}

    for target in TARGETS:
        print(f"\nEvaluating {target}...")

        # Solar and wind use weather plus calendar features.
        # Demand also uses its own lag features.
        features = WEATHER_FEATURES + calendar_features

        if target == "demand_mw":
            features += [
                "demand_mw_lag_24",
                "demand_mw_lag_168",
            ]

        # Construct target-specific valid rows.
        required = [target, *features, f"{target}_lag_24"]

        model_df = df.dropna(
            subset=list(dict.fromkeys(required))
        ).copy()

        if len(model_df) < 1000:
            raise ValueError(
                f"Insufficient valid rows for {target}: "
                f"{len(model_df)}"
            )

        # Chronological split: no shuffling.
        split = int(len(model_df) * 0.8)

        train_df = model_df.iloc[:split].copy()
        test_df = model_df.iloc[split:].copy()

        if train_df["timestamp_utc"].max() >= (
            test_df["timestamp_utc"].min()
        ):
            raise ValueError(
                "Chronological split validation failed."
            )

        X_train = train_df[features]
        y_train = train_df[target]

        X_test = test_df[features]
        y_test = test_df[target]

        model = RandomForestRegressor(
            n_estimators=200,
            max_depth=16,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        )

        model.fit(X_train, y_train)

        predictions = model.predict(X_test)

        model_metrics = calculate_metrics(
            y_test.to_numpy(),
            predictions,
        )

        # Same-hour previous-day baseline.
        baseline_predictions = test_df[
            f"{target}_lag_24"
        ].to_numpy()

        baseline_metrics = calculate_metrics(
            y_test.to_numpy(),
            baseline_predictions,
        )

        result = {
            "target": target,
            "source": "OPSD Germany + Open-Meteo ERA5",
            "geographic_scope": (
                "German national/regional energy measurements "
                "with Berlin reference-location weather"
            ),
            "training_records": len(train_df),
            "test_records": len(test_df),
            "training_start_utc": (
                train_df["timestamp_utc"].min().isoformat()
            ),
            "training_end_utc": (
                train_df["timestamp_utc"].max().isoformat()
            ),
            "test_start_utc": (
                test_df["timestamp_utc"].min().isoformat()
            ),
            "test_end_utc": (
                test_df["timestamp_utc"].max().isoformat()
            ),
            "model": model_metrics,
            "same_hour_previous_day_baseline": baseline_metrics,
            "features": features,
            "limitations": [
                "Single-location Berlin weather is not representative "
                "of the entire German energy system.",
                "This is a retrospective one-step experiment, not a "
                "validated operational forecast.",
                "Weather features are historical observations; "
                "future forecast-time availability must be addressed "
                "before deployment.",
            ],
        }

        model_path = MODEL_DIR / f"{target}_weather_model.joblib"

        artifact = {
            "model": model,
            "features": features,
            "target": target,
            "source": result["source"],
            "geographic_scope": result["geographic_scope"],
            "training_records": len(train_df),
            "test_records": len(test_df),
            "metrics": {
                "model": model_metrics,
                "same_hour_previous_day_baseline": baseline_metrics,
            },
            "training_end_utc": result["training_end_utc"],
            "test_start_utc": result["test_start_utc"],
            "test_end_utc": result["test_end_utc"],
        }

        joblib.dump(artifact, model_path)

        result["model_path"] = str(model_path)
        all_results[target] = result

        print(f"Training records: {len(train_df)}")
        print(f"Test records: {len(test_df)}")
        print(f"Model MAE: {model_metrics['mae_mw']:.2f} MW")
        print(f"Model RMSE: {model_metrics['rmse_mw']:.2f} MW")
        print(
            "Baseline MAE: "
            f"{baseline_metrics['mae_mw']:.2f} MW"
        )
        print(
            "Baseline RMSE: "
            f"{baseline_metrics['rmse_mw']:.2f} MW"
        )
        print(f"Saved model: {model_path}")

    report = {
        "evaluation_type": (
            "Chronological retrospective one-step evaluation"
        ),
        "dataset": str(DATA_PATH),
        "weather_source": "Open-Meteo ERA5",
        "energy_source": "OPSD Germany",
        "results": all_results,
    }

    with open(REPORT_PATH, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    print("\nAll real-world weather-informed models evaluated.")
    print(f"Report saved to: {REPORT_PATH}")
    print(
        "Reminder: retrospective results do not establish "
        "operational forecast accuracy."
    )


if __name__ == "__main__":
    main()