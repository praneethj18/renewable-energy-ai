from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ENERGY_PATH = (
    PROJECT_ROOT
    / "data"
    / "real_world"
    / "germany_energy.csv"
)

WEATHER_PATH = (
    PROJECT_ROOT
    / "data"
    / "real_world"
    / "germany_weather.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "real_world"
    / "germany_weather_energy_merged.csv"
)


ENERGY_COLUMNS = [
    "solar_generation_mw",
    "wind_generation_mw",
    "demand_mw",
]

WEATHER_COLUMNS = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "wind_speed_10m",
    "wind_speed_100m",
    "wind_direction_10m",
    "wind_direction_100m",
    "cloud_cover",
    "shortwave_radiation",
    "direct_radiation",
]


def load_and_validate(
    path: Path,
    required_columns: list[str],
    dataset_name: str,
) -> pd.DataFrame:
    """Load a dataset and validate its timestamp and numeric fields."""

    if not path.exists():
        raise FileNotFoundError(
            f"{dataset_name} dataset not found: {path}"
        )

    df = pd.read_csv(path)

    required = [
        "timestamp_utc",
        *required_columns,
    ]

    missing_columns = [
        column
        for column in required
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"{dataset_name} is missing columns: "
            f"{missing_columns}"
        )

    df = df[required].copy()

    df["timestamp_utc"] = pd.to_datetime(
        df["timestamp_utc"],
        utc=True,
        errors="coerce",
    )

    for column in required_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df[required_columns] = df[required_columns].replace(
        [np.inf, -np.inf],
        np.nan,
    )

    invalid_timestamps = int(
        df["timestamp_utc"].isna().sum()
    )

    if invalid_timestamps:
        raise ValueError(
            f"{dataset_name} contains "
            f"{invalid_timestamps} invalid timestamps."
        )

    duplicate_count = int(
        df["timestamp_utc"].duplicated().sum()
    )

    if duplicate_count:
        raise ValueError(
            f"{dataset_name} contains "
            f"{duplicate_count} duplicate timestamps."
        )

    if df[required_columns].isna().any().any():
        raise ValueError(
            f"{dataset_name} contains missing or non-finite "
            "numeric measurements. Resolve them explicitly "
            "before merging."
        )

    df = df.sort_values(
        "timestamp_utc"
    ).reset_index(drop=True)

    return df


def main():
    print("Loading and validating German energy data...")

    energy = load_and_validate(
        ENERGY_PATH,
        ENERGY_COLUMNS,
        "Energy",
    )

    print("Loading and validating historical weather data...")

    weather = load_and_validate(
        WEATHER_PATH,
        WEATHER_COLUMNS,
        "Weather",
    )

    print("\n--- Source Dataset Coverage ---")

    print(
        "Energy records:",
        len(energy),
    )

    print(
        "Energy start:",
        energy["timestamp_utc"].min(),
    )

    print(
        "Energy end:",
        energy["timestamp_utc"].max(),
    )

    print(
        "Weather records:",
        len(weather),
    )

    print(
        "Weather start:",
        weather["timestamp_utc"].min(),
    )

    print(
        "Weather end:",
        weather["timestamp_utc"].max(),
    )

    # Exact timestamp matching only. No nearest-time matching
    # or invented measurements.
    merged = energy.merge(
        weather,
        on="timestamp_utc",
        how="inner",
        validate="one_to_one",
    )

    print("\n--- Exact UTC Timestamp Join ---")

    print(
        "Matched records:",
        len(merged),
    )

    print(
        "Energy records without a matching weather timestamp:",
        len(energy) - len(merged),
    )

    print(
        "Weather records without a matching energy timestamp:",
        len(weather) - len(merged),
    )

    if merged.empty:
        raise ValueError(
            "The datasets have no matching UTC timestamps."
        )

    merged = merged.sort_values(
        "timestamp_utc"
    ).reset_index(drop=True)

    merged["data_source_energy"] = "OPSD_Germany"
    merged["data_source_weather"] = "Open-Meteo ERA5"
    merged["weather_reference_location"] = "Berlin, Germany"

    if OUTPUT_PATH.exists():
        raise FileExistsError(
            f"Output already exists: {OUTPUT_PATH}. "
            "Inspect or rename it before running this script again."
        )

    merged.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print("\n--- Merged Dataset ---")

    print(
        "Output:",
        OUTPUT_PATH,
    )

    print(
        "Rows:",
        len(merged),
    )

    print(
        "Columns:",
        len(merged.columns),
    )

    print(
        "Start:",
        merged["timestamp_utc"].min(),
    )

    print(
        "End:",
        merged["timestamp_utc"].max(),
    )

    print(
        "\nMissing values:\n",
        merged.isna().sum().to_string(),
    )

    print("\nSample records:")
    print(
        merged.head().to_string(index=False)
    )

    print(
        "\nGeographic limitation: energy measurements are "
        "German national/regional data, while weather observations "
        "represent a single reference location in Berlin."
    )


if __name__ == "__main__":
    main()