from datetime import datetime, timezone
import math

import httpx


WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"
FORECAST_HORIZON_HOURS = 48


class WeatherServiceError(Exception):
    """Raised when weather data cannot be retrieved or validated."""


def _parse_utc_timestamp(value: str) -> datetime:
    """Parse an API timestamp and normalize it to UTC."""

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed.astimezone(timezone.utc)

    except (TypeError, ValueError) as exc:
        raise WeatherServiceError(
            f"Invalid weather forecast timestamp: {value!r}"
        ) from exc


def _finite_number(value, field: str, timestamp: str) -> float:
    """Validate a numeric weather measurement."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise WeatherServiceError(
            f"Missing or invalid {field} at {timestamp}."
        )

    if not math.isfinite(value):
        raise WeatherServiceError(
            f"Non-finite {field} at {timestamp}."
        )

    return float(value)


def get_weather(latitude: float, longitude: float) -> dict:
    """Retrieve current weather and the next 48 future hourly forecasts."""

    if (
        isinstance(latitude, bool)
        or not isinstance(latitude, (int, float))
        or not math.isfinite(latitude)
        or not -90 <= latitude <= 90
    ):
        raise ValueError("Latitude must be finite and between -90 and 90.")

    if (
        isinstance(longitude, bool)
        or not isinstance(longitude, (int, float))
        or not math.isfinite(longitude)
        or not -180 <= longitude <= 180
    ):
        raise ValueError("Longitude must be finite and between -180 and 180.")

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "precipitation,"
            "cloud_cover,"
            "wind_speed_10m,"
            "wind_direction_10m,"
            "wind_speed_100m,"
            "wind_direction_100m,"
            "shortwave_radiation,"
            "direct_radiation"
        ),
        "hourly": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "precipitation,"
            "cloud_cover,"
            "wind_speed_10m,"
            "wind_direction_10m,"
            "wind_speed_100m,"
            "wind_direction_100m,"
            "shortwave_radiation,"
            "direct_radiation"
        ),
        "forecast_days": 3,
        "timezone": "UTC",
        "wind_speed_unit": "ms",
    }

    try:
        response = httpx.get(
            WEATHER_API_URL,
            params=params,
            timeout=20.0,
        )
        response.raise_for_status()
        data = response.json()

    except httpx.HTTPError as exc:
        raise WeatherServiceError(
            f"Weather API request failed: {exc}"
        ) from exc

    except ValueError as exc:
        raise WeatherServiceError(
            "Weather API returned invalid JSON."
        ) from exc

    retrieved_at = datetime.now(timezone.utc)

    current = data.get("current")
    hourly = data.get("hourly")

    if not isinstance(current, dict) or not isinstance(hourly, dict):
        raise WeatherServiceError(
            "Weather API response is missing current or hourly data."
        )

    required_fields = [
        "time",
        "temperature_2m",
        "relative_humidity_2m",
        "precipitation",
        "cloud_cover",
        "wind_speed_10m",
        "wind_direction_10m",
        "wind_speed_100m",
        "wind_direction_100m",
        "shortwave_radiation",
        "direct_radiation",
    ]

    for field in required_fields:
        if field not in hourly:
            raise WeatherServiceError(
                f"Weather API response is missing hourly field: {field}"
            )

    forecast_length = len(hourly["time"])

    if forecast_length == 0:
        raise WeatherServiceError("Weather API returned an empty forecast.")

    for field in required_fields:
        if len(hourly[field]) != forecast_length:
            raise WeatherServiceError(
                f"Hourly forecast field has inconsistent length: {field}"
            )

    candidates = []

    for i in range(forecast_length):
        raw_timestamp = hourly["time"][i]
        timestamp = _parse_utc_timestamp(raw_timestamp)

        # Exclude hours that have already started.
        if timestamp <= retrieved_at:
            continue

        record = {
            "timestamp_utc": timestamp.isoformat(),
            "temperature_c": hourly["temperature_2m"][i],
            "relative_humidity_pct": hourly["relative_humidity_2m"][i],
            "precipitation_mm": hourly["precipitation"][i],
            "cloud_cover_pct": hourly["cloud_cover"][i],
            "wind_speed_kmh": (
                float(hourly["wind_speed_10m"][i]) * 3.6
                if hourly["wind_speed_10m"][i] is not None
                else None
            ),
            "wind_speed_ms": hourly["wind_speed_10m"][i],
            "wind_direction_deg": hourly["wind_direction_10m"][i],
            "wind_speed_100m_ms": hourly["wind_speed_100m"][i],
            "wind_direction_100m_deg": hourly["wind_direction_100m"][i],
            "solar_radiation_wm2": hourly["shortwave_radiation"][i],
            "direct_radiation_wm2": hourly["direct_radiation"][i],
        }

        numeric_fields = [
            "temperature_c",
            "relative_humidity_pct",
            "precipitation_mm",
            "cloud_cover_pct",
            "wind_speed_kmh",
            "wind_speed_ms",
            "wind_direction_deg",
            "wind_speed_100m_ms",
            "wind_direction_100m_deg",
            "solar_radiation_wm2",
            "direct_radiation_wm2",
        ]

        for field in numeric_fields:
            record[field] = _finite_number(
                record[field],
                field,
                record["timestamp_utc"],
            )

        if not 0 <= record["relative_humidity_pct"] <= 100:
            raise WeatherServiceError(
                f"Invalid humidity at {record['timestamp_utc']}."
            )

        if not 0 <= record["cloud_cover_pct"] <= 100:
            raise WeatherServiceError(
                f"Invalid cloud cover at {record['timestamp_utc']}."
            )

        if (
            record["precipitation_mm"] < 0
            or record["wind_speed_ms"] < 0
            or record["wind_speed_100m_ms"] < 0
            or record["solar_radiation_wm2"] < 0
            or record["direct_radiation_wm2"] < 0
        ):
            raise WeatherServiceError(
                f"Negative weather measurement at {record['timestamp_utc']}."
            )

        for direction_field in (
            "wind_direction_deg",
            "wind_direction_100m_deg",
        ):
            if not 0 <= record[direction_field] <= 360:
                raise WeatherServiceError(
                    f"Invalid {direction_field} at {record['timestamp_utc']}."
                )

        candidates.append((timestamp, record))

    candidates.sort(key=lambda item: item[0])

    # Keep one record per timestamp.
    unique_records = {}
    for timestamp, record in candidates:
        unique_records[timestamp] = record

    hourly_forecast = [
        record
        for _, record in sorted(unique_records.items())[
            :FORECAST_HORIZON_HOURS
        ]
    ]

    if len(hourly_forecast) != FORECAST_HORIZON_HOURS:
        raise WeatherServiceError(
            "Could not obtain 48 valid future hourly forecasts. "
            f"Received {len(hourly_forecast)}."
        )

    timestamps = [
        _parse_utc_timestamp(record["timestamp_utc"])
        for record in hourly_forecast
    ]

    for previous, current_timestamp in zip(timestamps, timestamps[1:]):
        if (current_timestamp - previous).total_seconds() != 3600:
            raise WeatherServiceError(
                "Weather forecast timestamps are not continuous hourly records."
            )

    return {
        "location": {
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "timezone": data.get("timezone"),
        },
        "retrieved_at_utc": retrieved_at.isoformat(),
        "current": current,
        "hourly_forecast": hourly_forecast,
        "forecast_horizon_hours": len(hourly_forecast),
        "forecast_start_utc": hourly_forecast[0]["timestamp_utc"],
        "forecast_end_utc": hourly_forecast[-1]["timestamp_utc"],
        "source": "Open-Meteo forecast API",
        "forecast_type": "Future hourly weather forecast",
        "fallback_status": "not_used",
    }
