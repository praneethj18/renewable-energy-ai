from backend.app.services.forecasting import (
    train_forecasting_model,
    predict_generation,
)


def main():
    for target in ["solar", "wind"]:
        print(f"\nTesting {target.upper()} prediction...")

        train_forecasting_model(target)

        weather = {
            "solar_irradiance_wm2": 650.0,
            "cloud_cover_pct": 25.0,
            "temperature_c": 30.0,
            "wind_speed_ms": 5.0,
            "wind_direction_deg": 180.0,
        }

        prediction = predict_generation(target, weather)

        print(f"Predicted {target} generation: {prediction:.3f} MW")

    print("\nSUCCESS: Solar and wind predictions completed.")


if __name__ == "__main__":
    main()