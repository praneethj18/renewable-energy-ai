from pathlib import Path
import hashlib

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_PATH = PROJECT_ROOT / "data" / "synthetic_energy.csv"
MODEL_DIR = PROJECT_ROOT / "models"

FEATURES = [
    "solar_irradiance_wm2",
    "cloud_cover_pct",
    "temperature_c",
    "wind_speed_ms",
    "wind_direction_deg",
]

TARGETS = {
    "solar": "solar_mw",
    "wind": "wind_mw",
}


def load_training_data() -> pd.DataFrame:
    """Load and validate synthetic historical energy data."""

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Training dataset not found: {DATA_PATH}"
        )

    df = pd.read_csv(DATA_PATH)

    required_columns = [
        "timestamp_utc",
        *FEATURES,
        *TARGETS.values(),
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Dataset is missing columns: {missing_columns}"
        )

    df = df[required_columns].copy()

    df["timestamp_utc"] = pd.to_datetime(
        df["timestamp_utc"],
        utc=True,
        errors="coerce",
    )

    numeric_columns = FEATURES + list(TARGETS.values())

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df = df.replace(
        [np.inf, -np.inf],
        np.nan,
    )

    df = df.dropna(
        subset=["timestamp_utc", *numeric_columns]
    )

    df = df.sort_values("timestamp_utc")

    if df["timestamp_utc"].duplicated().any():
        raise ValueError(
            "Duplicate timestamps exist in the training dataset."
        )

    if len(df) < 100:
        raise ValueError(
            "At least 100 valid records are required for training."
        )

    for target_column in TARGETS.values():
        if (df[target_column] < 0).any():
            raise ValueError(
                f"Negative values found in {target_column}."
            )

    return df.reset_index(drop=True)


def calculate_metrics(
    actual: np.ndarray,
    predicted: np.ndarray,
) -> dict:
    """Calculate MAE and RMSE."""

    return {
        "mae": float(
            mean_absolute_error(actual, predicted)
        ),
        "rmse": float(
            np.sqrt(
                mean_squared_error(actual, predicted)
            )
        ),
    }


def train_forecasting_model(target: str) -> dict:
    """
    Train a synthetic-data generation model.

    Uses a chronological split to avoid training on future records
    and testing on earlier records.
    """

    if target not in TARGETS:
        raise ValueError(
            "Target must be either 'solar' or 'wind'."
        )

    df = load_training_data()

    target_column = TARGETS[target]

    split_index = int(len(df) * 0.8)

    if split_index < 50 or len(df) - split_index < 20:
        raise ValueError(
            "Insufficient records for chronological evaluation."
        )

    train_df = df.iloc[:split_index]
    test_df = df.iloc[split_index:]

    X_train = train_df[FEATURES]
    y_train = train_df[target_column]

    X_test = test_df[FEATURES]
    y_test = test_df[target_column]

    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=12,
        random_state=42,
        n_jobs=-1,
    )

    model.fit(
        X_train,
        y_train,
    )

    predictions = model.predict(X_test)

    model_metrics = calculate_metrics(
        y_test.to_numpy(),
        predictions,
    )

    # Persistence baseline: use the most recent available
    # generation measurement as the next-period prediction.
    #
    # This is an explicit baseline, not a same-hour previous-day
    # baseline because the current model does not use lag features.
    baseline_predictions = np.full(
        shape=len(test_df),
        fill_value=float(train_df[target_column].iloc[-1]),
    )

    baseline_metrics = calculate_metrics(
        y_test.to_numpy(),
        baseline_predictions,
    )

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    model_path = (
        MODEL_DIR / f"{target}_forecast_model.joblib"
    )

    artifact = {
        "model": model,
        "features": FEATURES,
        "target": target_column,
        "data_source": "synthetic_energy.csv",
        "geographic_scope": "Synthetic facility",
        "training_records": len(train_df),
        "testing_records": len(test_df),
        "training_start_utc": (
            train_df["timestamp_utc"].iloc[0].isoformat()
        ),
        "training_end_utc": (
            train_df["timestamp_utc"].iloc[-1].isoformat()
        ),
        "testing_start_utc": (
            test_df["timestamp_utc"].iloc[0].isoformat()
        ),
        "testing_end_utc": (
            test_df["timestamp_utc"].iloc[-1].isoformat()
        ),
        "evaluation": {
            "model": {
                "mae_mw": model_metrics["mae"],
                "rmse_mw": model_metrics["rmse"],
            },
            "persistence_baseline": {
                "mae_mw": baseline_metrics["mae"],
                "rmse_mw": baseline_metrics["rmse"],
            },
        },
    }

    joblib.dump(
        artifact,
        model_path,
    )

    return {
        "target": target,
        "training_records": len(train_df),
        "testing_records": len(test_df),
        "mae_mw": round(model_metrics["mae"], 4),
        "rmse_mw": round(model_metrics["rmse"], 4),
        "baseline_mae_mw": round(
            baseline_metrics["mae"], 4
        ),
        "baseline_rmse_mw": round(
            baseline_metrics["rmse"], 4
        ),
        "data_source": "synthetic_energy.csv",
        "model_path": str(model_path),
    }


def predict_generation(
    target: str,
    weather: dict,
) -> float:
    """Predict solar or wind generation from weather features."""

    if target not in TARGETS:
        raise ValueError(
            "Target must be either 'solar' or 'wind'."
        )

    model_path = (
        MODEL_DIR / f"{target}_forecast_model.joblib"
    )

    if not model_path.exists():
        raise FileNotFoundError(
            f"Model not found: {model_path}. Train it first."
        )

    missing_features = [
        feature
        for feature in FEATURES
        if feature not in weather
    ]

    if missing_features:
        raise ValueError(
            f"Missing weather features: {missing_features}"
        )

    values = {}

    for feature in FEATURES:
        value = float(weather[feature])

        if not np.isfinite(value):
            raise ValueError(
                f"Weather feature {feature} must be finite."
            )

        values[feature] = value

    input_data = pd.DataFrame(
        [values],
        columns=FEATURES,
    )

    artifact = joblib.load(model_path)

    # Support both the existing model files and the new artifact
    # format produced by train_forecasting_model().
    model = (
        artifact["model"]
        if isinstance(artifact, dict)
        else artifact
    )

    prediction = float(
        model.predict(input_data)[0]
    )

    if not np.isfinite(prediction):
        raise ValueError(
            "Generation model returned a non-finite prediction."
        )

    return max(0.0, prediction)


def get_generation_model_metadata(target: str) -> dict:
    """Return provenance and held-out metrics from the loaded model artifact."""
    if target not in TARGETS:
        raise ValueError("Target must be either 'solar' or 'wind'.")
    model_path = MODEL_DIR / f"{target}_forecast_model.joblib"
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}. Train it first.")
    artifact = joblib.load(model_path)
    if not isinstance(artifact, dict):
        artifact = {}
    return {
        "model_version": hashlib.sha256(model_path.read_bytes()).hexdigest()[:12],
        "data_source": artifact.get("data_source", "Unknown"),
        "training_records": artifact.get("training_records"),
        "testing_records": artifact.get("testing_records"),
        "training_start_utc": artifact.get("training_start_utc"),
        "training_end_utc": artifact.get("training_end_utc"),
        "evaluation": artifact.get("evaluation"),
        "feature_order": artifact.get("features", FEATURES),
    }
