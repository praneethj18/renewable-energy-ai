from pathlib import Path

import numpy as np
import pandas as pd


# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

OUTPUT_FILE = DATA_DIR / "synthetic_energy.csv"

# Reproducible random generator
RANDOM_SEED = 42
rng = np.random.default_rng(RANDOM_SEED)

# Generate 90 days of hourly historical data
TIMESTAMPS = pd.date_range(
    end=pd.Timestamp.now(tz="UTC").floor("h"),
    periods=90 * 24,
    freq="h",
)

SOLAR_CAPACITY_MW = 10.0
WIND_CAPACITY_MW = 6.0


def generate_dataset() -> pd.DataFrame:
    records = []

    battery_soc = 50.0

    for timestamp in TIMESTAMPS:
        hour = timestamp.hour
        day_of_year = timestamp.dayofyear

        # -------------------------------------------------
        # 1. Generate simulated weather conditions
        # -------------------------------------------------

        temperature = (
            27
            + 5 * np.sin(2 * np.pi * (hour - 8) / 24)
            + 2 * np.sin(2 * np.pi * day_of_year / 365)
            + rng.normal(0, 1.5)
        )

        temperature = float(np.clip(temperature, 12, 45))

        cloud_cover = float(
            np.clip(rng.beta(2, 3) * 100, 0, 100)
        )

        wind_speed = float(
            np.clip(
                rng.weibull(2.0) * 7 + 1,
                0,
                25,
            )
        )

        wind_direction = float(rng.uniform(0, 360))

        # -------------------------------------------------
        # 2. Generate solar irradiance and solar generation
        # -------------------------------------------------

        daylight_factor = max(
            0,
            np.sin(np.pi * (hour - 6) / 12),
        )

        solar_irradiance = (
            950
            * daylight_factor
            * (1 - cloud_cover / 130)
        )

        solar_irradiance = float(
            np.clip(solar_irradiance, 0, 1000)
        )

        solar_mw = (
            SOLAR_CAPACITY_MW
            * solar_irradiance
            / 1000
            * max(0.7, 1 - 0.004 * (temperature - 25))
            + rng.normal(0, 0.15)
        )

        # Solar generation must be zero or positive.
        solar_mw = float(
            np.clip(solar_mw, 0, SOLAR_CAPACITY_MW)
        )

        # -------------------------------------------------
        # 3. Generate wind generation
        # -------------------------------------------------

        wind_mw = (
            WIND_CAPACITY_MW
            * min((wind_speed / 12) ** 2, 1)
            + rng.normal(0, 0.2)
        )

        wind_mw = float(
            np.clip(wind_mw, 0, WIND_CAPACITY_MW)
        )

        # -------------------------------------------------
        # 4. Generate electricity demand
        # -------------------------------------------------

        morning_peak = np.exp(
            -((hour - 9) ** 2) / 12
        )

        evening_peak = np.exp(
            -((hour - 19) ** 2) / 18
        )

        demand_mw = (
            4
            + 1.5 * morning_peak
            + 2.0 * evening_peak
            + 0.05 * max(temperature - 25, 0)
            + rng.normal(0, 0.25)
        )

        demand_mw = float(
            np.clip(demand_mw, 2, 10)
        )

        # -------------------------------------------------
        # 5. Simulate battery state of charge
        # -------------------------------------------------

        surplus_mw = solar_mw + wind_mw - demand_mw

        # Illustrative battery simulation.
        # A complete physical battery model will be added
        # during the optimization phase.

        battery_soc += np.clip(surplus_mw * 0.8, -3, 3)

        battery_soc = float(
            np.clip(battery_soc, 10, 95)
        )

        # -------------------------------------------------
        # 6. Store the hourly record
        # -------------------------------------------------

        records.append(
            {
                "timestamp_utc": timestamp.isoformat(),
                "asset_id": "synthetic_facility",
                "solar_mw": round(solar_mw, 4),
                "wind_mw": round(wind_mw, 4),
                "demand_mw": round(demand_mw, 4),
                "solar_irradiance_wm2": round(
                    solar_irradiance, 2
                ),
                "cloud_cover_pct": round(
                    cloud_cover, 2
                ),
                "temperature_c": round(
                    temperature, 2
                ),
                "wind_speed_ms": round(
                    wind_speed, 2
                ),
                "wind_direction_deg": round(
                    wind_direction, 2
                ),
                "battery_soc_pct": round(
                    battery_soc, 2
                ),
                "asset_status": "available",
                "data_source": "synthetic",
                "quality_flag": "good",
            }
        )

    return pd.DataFrame(records)


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    df = generate_dataset()

    df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print("Synthetic historical dataset generated.")
    print(f"Output file: {OUTPUT_FILE}")
    print(f"Total records: {len(df)}")
    print(f"Date range: {df['timestamp_utc'].iloc[0]}")
    print(f"             {df['timestamp_utc'].iloc[-1]}")
    print(f"Columns: {list(df.columns)}")
    print()
    print(df.head().to_string(index=False))


if __name__ == "__main__":
    main()