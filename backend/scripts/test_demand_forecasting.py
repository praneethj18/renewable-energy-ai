from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_PATH = PROJECT_ROOT / "data" / "synthetic_energy.csv"
MODEL_DIR = PROJECT_ROOT / "models"

TARGET = "demand_mw"


def main():
    print("Loading historical energy data...")

    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

    df = pd.read_csv(DATA_PATH)

    required_columns = [
        "timestamp_utc",
        "demand_mw",
        "temperature_c",
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(f"Missing columns: {missing}")

    df["timestamp_utc"] = pd.to_datetime(
        df["timestamp_utc"],
        utc=True,
        errors="coerce",
    )

    df = df.dropna(subset=required_columns)
    df = df.sort_values("timestamp_utc").reset_index(drop=True)

    df["hour"] = df["timestamp_utc"].dt.hour
    df["day_of_week"] = df["timestamp_utc"].dt.dayofweek

    # Use only previously observed demand as a feature.
    df["demand_lag_24"] = df[TARGET].shift(24)

    df = df.dropna().reset_index(drop=True)

    features = [
        "hour",
        "day_of_week",
        "temperature_c",
        "demand_lag_24",
    ]

    X = df[features]
    y = df[TARGET]

    # Chronological split: earlier records train the model;
    # later records are reserved for evaluation.
    split_index = int(len(df) * 0.8)

    X_train = X.iloc[:split_index]
    X_test = X.iloc[split_index:]

    y_train = y.iloc[:split_index]
    y_test = y.iloc[split_index:]

    print(f"Training records: {len(X_train)}")
    print(f"Testing records: {len(X_test)}")

    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=12,
        random_state=42,
        n_jobs=-1,
    )

    print("\nTraining demand forecasting model...")
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    # Baseline: demand at the same hour on the previous day.
    baseline_predictions = X_test["demand_lag_24"].to_numpy()

    model_mae = mean_absolute_error(y_test, predictions)
    model_rmse = np.sqrt(mean_squared_error(y_test, predictions))

    baseline_mae = mean_absolute_error(
        y_test,
        baseline_predictions,
    )
    baseline_rmse = np.sqrt(
        mean_squared_error(y_test, baseline_predictions)
    )

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    model_path = MODEL_DIR / "demand_forecast_model.joblib"

    joblib.dump(
        {
            "model": model,
            "features": features,
            "target": TARGET,
            "data_source": "synthetic_energy.csv",
        },
        model_path,
    )

    print("\nDEMAND FORECAST RESULTS")
    print("-----------------------")
    print(f"Model MAE: {model_mae:.4f} MW")
    print(f"Model RMSE: {model_rmse:.4f} MW")

    print("\nSAME-HOUR PREVIOUS-DAY BASELINE")
    print("--------------------------------")
    print(f"Baseline MAE: {baseline_mae:.4f} MW")
    print(f"Baseline RMSE: {baseline_rmse:.4f} MW")

    print(f"\nModel saved to: {model_path}")

    print(
        "\nNOTE: This evaluation uses synthetic data. "
        "It does not establish real-world forecasting accuracy."
    )


if __name__ == "__main__":
    main()