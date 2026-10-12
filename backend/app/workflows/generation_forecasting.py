from datetime import datetime, timezone
from typing import Any

import numpy as np

from app.services.forecasting import (
    get_generation_model_metadata,
    predict_generation,
)


def _parse_timestamp(value: Any) -> datetime:
    if not value:
        raise ValueError("Weather record is missing timestamp_utc.")

    timestamp = datetime.fromisoformat(
        str(value).replace("Z", "+00:00")
    )

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    return timestamp.astimezone(timezone.utc)


def _error_result(message: str) -> dict[str, Any]:
    return {
        "agent_results": {
            "generation_forecasting": {
                "status": "error",
                "message": message,
            }
        },
        "execution_trace": [
            "generation_forecasting:error"
        ],
        "errors": [
            f"Generation forecasting failed: {message}"
        ],
    }


def generation_forecasting_node(
    state: dict[str, Any],
) -> dict[str, Any]:
    """Generate timestamped solar and wind forecasts."""

    weather_data = state.get("weather_data")

    if not isinstance(weather_data, dict):
        return _error_result("Weather data is unavailable.")

    hourly_forecast = weather_data.get("hourly_forecast")

    if not isinstance(hourly_forecast, list) or not hourly_forecast:
        return _error_result(
            "No hourly weather forecasts are available."
        )

    try:
        asset_records = state.get("asset_status", {}).get("assets", [])
        capacity_by_type = {
            kind: sum(
                float(asset.get("capacity_mw", 0))
                for asset in asset_records
                if asset.get("asset_type", "").lower() == kind
                and asset.get("is_active")
            )
            for kind in ("solar", "wind")
        }
        model_metadata = {
            kind: get_generation_model_metadata(kind)
            for kind in ("solar", "wind")
        }
        forecasts = []
        previous_timestamp = None

        for weather in hourly_forecast:
            if not isinstance(weather, dict):
                raise ValueError(
                    "Weather forecast record must be an object."
                )

            timestamp = _parse_timestamp(
                weather.get("timestamp_utc")
            )

            if (
                previous_timestamp is not None
                and timestamp <= previous_timestamp
            ):
                raise ValueError(
                    "Weather forecast timestamps must be strictly increasing."
                )

            previous_timestamp = timestamp

            features = {
                "solar_irradiance_wm2": weather.get(
                    "solar_radiation_wm2"
                ),
                "cloud_cover_pct": weather.get(
                    "cloud_cover_pct"
                ),
                "temperature_c": weather.get(
                    "temperature_c"
                ),
                "wind_speed_ms": weather.get(
                    "wind_speed_ms"
                ),
                "wind_direction_deg": weather.get(
                    "wind_direction_deg"
                ),
            }

            missing_features = [
                name
                for name, value in features.items()
                if value is None
            ]

            if missing_features:
                raise ValueError(
                    f"Weather at {timestamp.isoformat()} is missing "
                    f"features: {missing_features}"
                )

            for name, value in features.items():
                try:
                    numeric_value = float(value)
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        f"Weather feature {name} must be numeric."
                    ) from exc

                if not np.isfinite(numeric_value):
                    raise ValueError(
                        f"Weather feature {name} must be finite."
                    )

                features[name] = numeric_value

            if not 0 <= features["cloud_cover_pct"] <= 100:
                raise ValueError(
                    "Cloud cover must be between 0 and 100 percent."
                )

            if features["solar_irradiance_wm2"] < 0:
                raise ValueError(
                    "Solar irradiance cannot be negative."
                )

            if features["wind_speed_ms"] < 0:
                raise ValueError(
                    "Wind speed cannot be negative."
                )

            if not 0 <= features["wind_direction_deg"] <= 360:
                raise ValueError(
                    "Wind direction must be between 0 and 360 degrees."
                )

            solar_mw = predict_generation(
                "solar",
                features,
            )

            wind_mw = predict_generation(
                "wind",
                features,
            )

            solar_unclipped = solar_mw
            wind_unclipped = wind_mw
            if features["solar_irradiance_wm2"] <= 0:
                solar_mw = 0.0
            solar_mw = min(solar_mw, capacity_by_type["solar"])
            wind_mw = min(wind_mw, capacity_by_type["wind"])

            if (
                not np.isfinite(solar_mw)
                or not np.isfinite(wind_mw)
                or solar_mw < 0
                or wind_mw < 0
            ):
                raise ValueError(
                    f"Invalid generation prediction at "
                    f"{timestamp.isoformat()}."
                )

            generation_mw = solar_mw + wind_mw

            forecasts.append({
                "timestamp_utc": timestamp.isoformat(),
                "solar_generation_mw": round(solar_mw, 4),
                "wind_generation_mw": round(wind_mw, 4),
                "total_generation_mw": round(generation_mw, 4),
                "solar_capacity_mw": round(capacity_by_type["solar"], 4),
                "wind_capacity_mw": round(capacity_by_type["wind"], 4),
                "solar_clipped": solar_mw != solar_unclipped,
                "wind_clipped": wind_mw != wind_unclipped,
            })

        solar_values = [
            item["solar_generation_mw"]
            for item in forecasts
        ]

        wind_values = [
            item["wind_generation_mw"]
            for item in forecasts
        ]

        total_values = [
            item["total_generation_mw"]
            for item in forecasts
        ]

        # Explicit timestamps in shared workflow state.
        forecast_timestamps = [
            item["timestamp_utc"]
            for item in forecasts
        ]

        return {
            "solar_forecast_mw": solar_values,
            "wind_forecast_mw": wind_values,
            "generation_forecast_mw": total_values,
            "generation_forecast_timestamps": forecast_timestamps,
            "agent_results": {
                "generation_forecasting": {
                    "status": "success",
                    "forecast_count": len(forecasts),
                    "forecast_start_utc": forecast_timestamps[0],
                    "forecast_end_utc": forecast_timestamps[-1],
                    "forecasts": forecasts,
                    "model_data_source": "Synthetic training dataset",
                    "weather_data_source": weather_data.get(
                        "source",
                        "Unknown",
                    ),
                    "forecast_scope": "Synthetic facility prototype",
                    "model_version": {
                        "solar": model_metadata["solar"]["model_version"],
                        "wind": model_metadata["wind"]["model_version"],
                    },
                    "evaluation_metrics": {
                        "solar": model_metadata["solar"]["evaluation"],
                        "wind": model_metadata["wind"]["evaluation"],
                    },
                    "warning": (
                        "These models were trained on synthetic data. "
                        "Although the inputs come from a real weather "
                        "forecast API, the predictions are experimental "
                        "and are not validated real-world facility forecasts."
                    ),
                }
            },
            "execution_trace": [
                "generation_forecasting:success"
            ],
        }

    except Exception as exc:
        return _error_result(str(exc))
