import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.weather import (
    get_weather,
    WeatherServiceError,
)


def main():
    print("WEATHER SERVICE TEST")
    print("-" * 40)

    # Hyderabad coordinates.
    latitude = 17.3850
    longitude = 78.4867

    try:
        result = get_weather(latitude, longitude)

        print("Weather API connection successful.")
        print("Source:", result["source"])
        print("Location:", result["location"])
        print("\nCurrent conditions:")
        print(result["current"])

        print("\nFirst five hourly forecasts:")

        for forecast in result["hourly_forecast"][:5]:
            print(forecast)

        assert len(result["hourly_forecast"]) > 0

        print("\nSUCCESS: Weather service test passed.")

    except (WeatherServiceError, ValueError) as exc:
        print("\nWEATHER SERVICE TEST FAILED")
        print(exc)


if __name__ == "__main__":
    main()