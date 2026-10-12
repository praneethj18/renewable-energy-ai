from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error


PROJECT_ROOT = Path(__file__).resolve().parents[3]

MODEL_PATH = PROJECT_ROOT / "models" / "demand_forecast_model.joblib"
DATASET_PATH = PROJECT_ROOT / "data" / "synthetic_energy.csv"


def _error_result(message: str) -> dict[str, Any]:
    """Return a consistent demand forecasting error result."""
    return {
        "agent_results": {
            "demand_forecasting": {
                "status": "error",
                "message": message,
            }
        },
        "execution_trace": ["demand_forecasting:error"],
        "errors": [f"Demand forecasting failed: {message}"],
    }


def _load_history() -> pd.DataFrame:
    """Load and validate the historical synthetic demand dataset."""
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Demand history dataset not found: {DATASET_PATH}"
        )

    df = pd.read_csv(DATASET_PATH)

    required = {"timestamp_utc", "demand_mw", "asset_id", "temperature_c"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Demand dataset is missing columns: {sorted(missing)}"
        )

    df = df[df["asset_id"] == "synthetic_facility"].copy()

    df["timestamp_utc"] = pd.to_datetime(
        df["timestamp_utc"], utc=True, errors="coerce"
    )
    df["demand_mw"] = pd.to_numeric(
        df["demand_mw"], errors="coerce"
    )
    df["temperature_c"] = pd.to_numeric(
        df["temperature_c"], errors="coerce"
    )

    df = df.dropna(subset=["timestamp_utc", "demand_mw", "temperature_c"])
    df = df.sort_values("timestamp_utc")

    if df.empty:
        raise ValueError("No valid synthetic-facility demand history exists.")

    if df["timestamp_utc"].duplicated().any():
        raise ValueError("Historical demand contains duplicate timestamps.")

    if not np.isfinite(df["demand_mw"].to_numpy(dtype=float)).all():
        raise ValueError("Historical demand contains non-finite values.")

    if not np.isfinite(df["temperature_c"].to_numpy(dtype=float)).all():
        raise ValueError("Historical temperature contains non-finite values.")

    if (df["demand_mw"] < 0).any():
        raise ValueError("Historical demand contains negative values.")

    return df.reset_index(drop=True)


def _parse_timestamp(value: Any) -> datetime:
    """Parse a timestamp and require an explicit timezone."""
    if not value:
        raise ValueError("Weather forecast is missing timestamp_utc.")

    timestamp = datetime.fromisoformat(
        str(value).replace("Z", "+00:00")
    )

    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError(
            f"Timestamp must include a timezone: {value}"
        )

    return timestamp.astimezone(timezone.utc)


def _evaluate_model(artifact: dict[str, Any], history: pd.DataFrame) -> dict[str, Any]:
    """Evaluate the loaded model on the training pipeline's chronological holdout."""
    evaluation = history.copy().sort_values("timestamp_utc").reset_index(drop=True)
    evaluation["hour"] = evaluation["timestamp_utc"].dt.hour
    evaluation["day_of_week"] = evaluation["timestamp_utc"].dt.dayofweek
    evaluation["demand_lag_24"] = evaluation["demand_mw"].shift(24)
    evaluation = evaluation.dropna(subset=["demand_lag_24"]).reset_index(drop=True)
    split_index = int(len(evaluation) * 0.8)
    holdout = evaluation.iloc[split_index:]
    if holdout.empty:
        return {}

    features = artifact["features"]
    actual = holdout["demand_mw"].to_numpy(dtype=float)
    predicted = artifact["model"].predict(holdout[features])
    baseline = holdout["demand_lag_24"].to_numpy(dtype=float)
    return {
        "model_mae_mw": round(float(mean_absolute_error(actual, predicted)), 4),
        "model_rmse_mw": round(float(np.sqrt(mean_squared_error(actual, predicted))), 4),
        "same_hour_previous_day_mae_mw": round(float(mean_absolute_error(actual, baseline)), 4),
        "same_hour_previous_day_rmse_mw": round(float(np.sqrt(mean_squared_error(actual, baseline))), 4),
        "holdout_records": int(len(holdout)),
        "holdout_start_utc": holdout["timestamp_utc"].iloc[0].isoformat(),
        "holdout_end_utc": holdout["timestamp_utc"].iloc[-1].isoformat(),
        "evaluation_data_source": "synthetic_energy.csv",
        "evaluation_scope": "Chronological held-out synthetic-facility observations",
    }


def demand_forecasting_node(
    state: dict[str, Any],
) -> dict[str, Any]:
    """Generate timestamp-aligned recursive demand predictions."""

    weather_data = state.get("weather_data")

    if not isinstance(weather_data, dict):
        return _error_result("Weather data is unavailable.")

    hourly_weather = weather_data.get("hourly_forecast")

    if not isinstance(hourly_weather, list) or not hourly_weather:
        return _error_result("No hourly weather forecasts are available.")

    try:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Demand model not found: {MODEL_PATH}"
            )

        artifact = joblib.load(MODEL_PATH)

        if not isinstance(artifact, dict) or "model" not in artifact:
            raise ValueError("Unexpected demand model artifact format.")

        expected_features = [
            "hour",
            "day_of_week",
            "temperature_c",
            "demand_lag_24",
        ]

        features = artifact.get("features")

        if features != expected_features:
            raise ValueError(
                f"Unexpected demand-model features: {features}"
            )

        history = _load_history()
        evaluation_metrics = _evaluate_model(artifact, history)
        history = history.set_index("timestamp_utc").sort_index()

        demand_by_timestamp = {
            pd.Timestamp(ts): float(value)
            for ts, value in history["demand_mw"].items()
        }

        last_observed_timestamp = history.index.max()
        last_observed_demand = float(
            history.loc[last_observed_timestamp, "demand_mw"]
        )

        forecasts = []
        previous_timestamp = None
        fallback_used = False

        for weather in hourly_weather:
            timestamp = _parse_timestamp(
                weather.get("timestamp_utc")
            )
            timestamp_key = pd.Timestamp(timestamp)

            if (
                previous_timestamp is not None
                and timestamp_key <= previous_timestamp
            ):
                raise ValueError(
                    "Weather timestamps must be strictly increasing."
                )

            if timestamp_key <= last_observed_timestamp:
                raise ValueError(
                    f"Forecast timestamp {timestamp.isoformat()} is not "
                    "later than the latest historical observation."
                )

            previous_timestamp = timestamp_key

            temperature = weather.get("temperature_c")

            if temperature is None:
                raise ValueError(
                    f"Temperature is missing at {timestamp.isoformat()}."
                )

            temperature = float(temperature)

            if not np.isfinite(temperature):
                raise ValueError(
                    f"Temperature is non-finite at {timestamp.isoformat()}."
                )

            # Prefer the exact demand value from 24 hours earlier.
            lag_timestamp = timestamp_key - pd.Timedelta(hours=24)
            lag_fallback = False

            if lag_timestamp in demand_by_timestamp:
                demand_lag_24 = demand_by_timestamp[lag_timestamp]
                lag_source = (
                    "historical_observation"
                    if lag_timestamp <= last_observed_timestamp
                    else "earlier_model_prediction"
                )

            elif lag_timestamp > last_observed_timestamp:
                # The exact 24-hour lag is not yet available.
                # Use the latest earlier forecast as a clearly labelled
                # approximation rather than inventing historical data.
                earlier_predictions = [
                    (ts, value)
                    for ts, value in demand_by_timestamp.items()
                    if last_observed_timestamp < ts < timestamp_key
                ]

                if earlier_predictions:
                    earlier_predictions.sort(key=lambda item: item[0])
                    demand_lag_24 = float(earlier_predictions[-1][1])
                    lag_source = "earlier_prediction_fallback"
                else:
                    demand_lag_24 = last_observed_demand
                    lag_source = "last_observed_value_fallback"

                lag_fallback = True
                fallback_used = True

            else:
                raise ValueError(
                    "Historical demand is missing at the required "
                    f"24-hour lag timestamp {lag_timestamp.isoformat()}."
                )

            input_data = pd.DataFrame(
                [{
                    "hour": timestamp.hour,
                    "day_of_week": timestamp.weekday(),
                    "temperature_c": temperature,
                    "demand_lag_24": demand_lag_24,
                }],
                columns=features,
            )

            prediction = float(
                artifact["model"].predict(input_data)[0]
            )

            if not np.isfinite(prediction):
                raise ValueError(
                    "Demand model returned a non-finite prediction "
                    f"at {timestamp.isoformat()}."
                )

            prediction = max(0.0, prediction)

            # Save the prediction for future recursive lags.
            demand_by_timestamp[timestamp_key] = prediction

            forecasts.append({
                "timestamp_utc": timestamp.isoformat(),
                "demand_forecast_mw": round(prediction, 4),
                "demand_lag_24_mw": round(demand_lag_24, 4),
                "lag_fallback_used": lag_fallback,
                "lag_source": lag_source,
            })

        forecast_timestamps = [
            item["timestamp_utc"] for item in forecasts
        ]

        return {
            "demand_forecast_mw": [
                item["demand_forecast_mw"] for item in forecasts
            ],
            "demand_forecast_timestamps": forecast_timestamps,
            "agent_results": {
                "demand_forecasting": {
                    "status": "success",
                    "forecast_count": len(forecasts),
                    "forecast_start_utc": forecast_timestamps[0],
                    "forecast_end_utc": forecast_timestamps[-1],
                    "forecasts": forecasts,
                    "initial_lag_fallback_used": fallback_used,
                    "model_data_source": artifact.get(
                        "data_source", "Unknown"
                    ),
                    "forecast_scope": "Synthetic facility prototype",
                    "forecast_method": "Recursive 24-hour-lag forecasting",
                    "model_version": hashlib.sha256(
                        MODEL_PATH.read_bytes()
                    ).hexdigest()[:12],
                    "evaluation_metrics": evaluation_metrics,
                    "warning": (
                        "This model was trained on synthetic demand data. "
                        "When the exact 24-hour lag is unavailable, an "
                        "earlier prediction or the latest observed demand "
                        "is used as a labelled fallback. These estimates "
                        "are not validated real-world facility forecasts."
                    ),
                }
            },
            "execution_trace": ["demand_forecasting:success"],
        }

    except Exception as exc:
        return _error_result(str(exc))
