from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import WeatherObservation


def save_weather_data(
    db: Session,
    weather_data: dict,
) -> int:
    """Save hourly weather forecasts to PostgreSQL."""

    location = weather_data["location"]
    hourly_forecast = weather_data["hourly_forecast"]

    saved_count = 0

    for item in hourly_forecast:
        observation = WeatherObservation(
            latitude=location["latitude"],
            longitude=location["longitude"],
            timestamp=datetime.fromisoformat(
                item["timestamp_utc"].replace("Z", "+00:00")
            ),
            temperature_c=item.get("temperature_c"),
            precipitation_mm=item.get("precipitation_mm"),
            cloud_cover_pct=item.get("cloud_cover_pct"),
            wind_speed_kmh=item.get("wind_speed_kmh"),
            wind_direction_deg=item.get("wind_direction_deg"),
            solar_radiation_wm2=item.get("solar_radiation_wm2"),
            source=weather_data.get("source", "Open-Meteo"),
        )

        db.add(observation)
        saved_count += 1

    db.commit()

    return saved_count