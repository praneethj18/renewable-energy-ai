from backend.app.services.weather import get_weather
from backend.app.services.forecasting import predict_generation


def main():
    latitude = 17.385
    longitude = 78.4867

    print("Fetching real weather data from Open-Meteo...")

    weather_data = get_weather(
        latitude=latitude,
        longitude=longitude,
    )

    current = weather_data["current"]

    print("\nCurrent weather retrieved successfully.")
    print(f"Temperature: {current['temperature_2m']} °C")
    print(f"Wind speed: {current['wind_speed_10m']} km/h")
    print(f"Cloud cover: {current['cloud_cover']}%")
    print(f"Solar radiation: {current['shortwave_radiation']} W/m²")

    # Convert current API values to the feature names
    # expected by the existing forecasting models.
    weather_features = {
        "solar_irradiance_wm2": current["shortwave_radiation"],
        "cloud_cover_pct": current["cloud_cover"],
        "temperature_c": current["temperature_2m"],
        "wind_speed_ms": current["wind_speed_10m"] / 3.6,
        "wind_direction_deg": current["wind_direction_10m"],
    }

    print("\nGenerating preliminary predictions...")

    for target in ["solar", "wind"]:
        prediction = predict_generation(
            target=target,
            weather=weather_features,
        )

        print(
            f"Predicted {target} generation: "
            f"{prediction:.3f} MW"
        )

    print(
        "\nSUCCESS: Weather retrieval and forecasting "
        "integration test completed."
    )
    print(
        "Note: Predictions use models trained on synthetic data "
        "and are not validated real-world forecasts."
    )


if __name__ == "__main__":
    main()