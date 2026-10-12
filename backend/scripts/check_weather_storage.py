from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.db.database import SessionLocal
from backend.app.db.models import WeatherObservation


def check_weather_storage():
    db: Session = SessionLocal()

    try:
        total_records = db.query(func.count(WeatherObservation.id)).scalar()

        print(f"Total weather records stored: {total_records}")

        latest_records = (
            db.query(WeatherObservation)
            .order_by(WeatherObservation.timestamp.desc())
            .limit(5)
            .all()
        )

        print("\nLatest weather records:")

        for record in latest_records:
            print(
                f"Timestamp: {record.timestamp} | "
                f"Temperature: {record.temperature_c} °C | "
                f"Cloud cover: {record.cloud_cover_pct}% | "
                f"Wind speed: {record.wind_speed_kmh} km/h | "
                f"Solar radiation: {record.solar_radiation_wm2} W/m²"
            )

    finally:
        db.close()


if __name__ == "__main__":
    check_weather_storage()