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
    / "germany_energy.csv"
)

MODEL_DIR = PROJECT_ROOT / "models" / "real_world"

TARGETS = [
    "solar_generation_mw",
    "wind_generation_mw",
    "demand_mw",
]


def prepare_features(df):
    df = df.copy()

    df["hour"] = df["timestamp_utc"].dt.hour
    df["day_of_week"] = df["timestamp_utc"].dt.dayofweek
    df["month"] = df["timestamp_utc"].dt.month

    # Build lag features only when timestamps are consecutive.
    for target in TARGETS:
        df[f"{target}_lag_24"] = np.nan
        df[f"{target}_lag_168"] = np.nan

    for target in TARGETS:
        for lag in (24, 168):
            lag_column = f"{target}_lag_{lag}"

            previous_values = df[target].shift(lag)
            previous_timestamps = df["timestamp_utc"].shift(lag)

            elapsed_hours = (
                df["timestamp_utc"] - previous_timestamps
            ).dt.total_seconds() / 3600

            df[lag_column] = previous_values.where(
                elapsed_hours == lag
            )

    # Remove rows where target values or lag features are missing.
    required_columns = (
        TARGETS
        + [
            f"{target}_lag_{lag}"
            for target in TARGETS
            for lag in (24, 168)
        ]
    )

    df = df.dropna(subset=required_columns).reset_index(drop=True)

    return df


def calculate_metrics(actual, predicted):
    mae = mean_absolute_error(actual, predicted)
    rmse = np.sqrt(mean_squared_error(actual, predicted))
    return mae, rmse


def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_PATH}"
        )

    print("Loading real-world German energy data...")

    df = pd.read_csv(DATA_PATH)

    df["timestamp_utc"] = pd.to_datetime(
        df["timestamp_utc"],
        utc=True,
        errors="raise",
    )

    df = df.sort_values("timestamp_utc").reset_index(drop=True)

    # Insert missing hours without inventing energy measurements.
    df = df.set_index("timestamp_utc")

    hourly_index = pd.date_range(
        start=df.index.min(),
        end=df.index.max(),
        freq="h",
    )

    df = df.reindex(hourly_index)
    df.index.name = "timestamp_utc"
    df = df.reset_index()

    df = prepare_features(df)

    if len(df) < 1000:
        raise ValueError("Not enough valid records for evaluation.")

    feature_columns = [
        "hour",
        "day_of_week",
        "month",
    ]

    for target in TARGETS:
        feature_columns.extend([
            f"{target}_lag_24",
            f"{target}_lag_168",
        ])

    # Chronological split: earlier records for training,
    # later records for testing.
    split_index = int(len(df) * 0.8)

    train_df = df.iloc[:split_index]
    test_df = df.iloc[split_index:]

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    all_metrics = {}

    for target in TARGETS:
        print(f"\nTraining model: {target}")

        model = RandomForestRegressor(
            n_estimators=100,
            max_depth=12,
            random_state=42,
            n_jobs=-1,
        )

        model.fit(
            train_df[feature_columns],
            train_df[target],
        )

        predictions = model.predict(
            test_df[feature_columns]
        )

        mae, rmse = calculate_metrics(
            test_df[target],
            predictions,
        )

        # Compare against the same-hour previous-day baseline.
        baseline_predictions = test_df[
            f"{target}_lag_24"
        ].to_numpy()

        baseline_mae, baseline_rmse = calculate_metrics(
            test_df[target].to_numpy(),
            baseline_predictions,
        )

        print(f"Model MAE: {mae:.2f} MW")
        print(f"Model RMSE: {rmse:.2f} MW")
        print(f"Baseline MAE: {baseline_mae:.2f} MW")
        print(f"Baseline RMSE: {baseline_rmse:.2f} MW")

        model_path = MODEL_DIR / f"{target}_model.joblib"

        joblib.dump(
            {
                "model": model,
                "features": feature_columns,
                "target": target,
                "source": "OPSD Germany",
                "geographic_scope": "Germany regional energy data",
                "training_records": len(train_df),
                "test_records": len(test_df),
                "metrics": {
                    "mae_mw": mae,
                    "rmse_mw": rmse,
                    "baseline_mae_mw": baseline_mae,
                    "baseline_rmse_mw": baseline_rmse,
                },
            },
            model_path,
        )

        all_metrics[target] = {
            "model_mae_mw": mae,
            "model_rmse_mw": rmse,
            "baseline_mae_mw": baseline_mae,
            "baseline_rmse_mw": baseline_rmse,
        }

        print(f"Saved model: {model_path}")

    metrics_path = MODEL_DIR / "evaluation_metrics.json"

    with open(metrics_path, "w", encoding="utf-8") as file:
        json.dump(all_metrics, file, indent=4)

    print("\nTraining and evaluation complete.")
    print(f"Training records: {len(train_df)}")
    print(f"Testing records: {len(test_df)}")
    print(f"Metrics saved to: {metrics_path}")
    print("Geographic scope: Germany regional energy data.")


if __name__ == "__main__":
    main()