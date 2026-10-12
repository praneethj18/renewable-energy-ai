from pathlib import Path

import numpy as np
import pandas as pd
import openmeteo_requests
import requests_cache

from retry_requests import retry


PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIR = PROJECT_ROOT / "data" / "real_world"
OUTPUT_PATH = OUTPUT_DIR / "germany_weather.csv"

API_URL = "https://archive-api.open-meteo.com/v1/archive"

LATITUDE = 52.52
LONGITUDE = 13.41

START_DATE = "2015-01-01"
END_DATE = "2020-09-30"

HOURLY_VARIABLES = [
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


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Cache successful responses and retry temporary failures.
    cache_session = requests_cache.CachedSession(
        str(PROJECT_ROOT / ".cache" / "open_meteo"),
        expire_after=-1,
    )

    retry_session = retry(
        cache_session,
        retries=5,
        backoff_factor=0.5,
    )

    client = openmeteo_requests.Client(
        session=retry_session,
    )

    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "hourly": HOURLY_VARIABLES,
        "models": "era5",
        "timezone": "GMT",
        "wind_speed_unit": "ms",
        "precipitation_unit": "mm",
    }

    print("Downloading historical weather from Open-Meteo...")
    print(f"Location: {LATITUDE}, {LONGITUDE}")
    print(f"Period: {START_DATE} to {END_DATE}")
    print("Model: ERA5")

    responses = client.weather_api(
        API_URL,
        params=params,
    )

    if not responses:
        raise RuntimeError(
            "Open-Meteo returned no weather responses."
        )

    response = responses[0]
    hourly = response.Hourly()

    if hourly is None:
        raise RuntimeError(
            "The API response contains no hourly data."
        )

    timestamps = pd.date_range(
        start=pd.to_datetime(
            hourly.Time(),
            unit="s",
            utc=True,
        ),
        periods=(
            (hourly.TimeEnd() - hourly.Time())
            // hourly.Interval()
        ),
        freq=pd.Timedelta(
            seconds=hourly.Interval()
        ),
    )

    data = {
        "timestamp_utc": timestamps,
    }

    for index, variable in enumerate(HOURLY_VARIABLES):
        values = hourly.Variables(index).ValuesAsNumpy()

        if len(values) != len(timestamps):
            raise ValueError(
                f"Unexpected number of values for {variable}: "
                f"{len(values)} instead of {len(timestamps)}"
            )

        data[variable] = values

    df = pd.DataFrame(data)

    numeric_columns = [
        column
        for column in df.columns
        if column != "timestamp_utc"
    ]

    df[numeric_columns] = df[numeric_columns].replace(
        [np.inf, -np.inf],
        np.nan,
    )

    df = df.sort_values("timestamp_utc")

    if df["timestamp_utc"].duplicated().any():
        raise ValueError(
            "Duplicate UTC timestamps were returned."
        )

    # Verify the date coverage without inventing missing measurements.
    expected_start = pd.Timestamp(
        START_DATE,
        tz="UTC",
    )

    expected_end_exclusive = (
        pd.Timestamp(END_DATE, tz="UTC")
        + pd.Timedelta(days=1)
    )

    if df.empty:
        raise ValueError(
            "The downloaded weather dataset is empty."
        )

    if df["timestamp_utc"].min() != expected_start:
        raise ValueError(
            "Downloaded weather does not start at the expected timestamp."
        )

    if df["timestamp_utc"].max() >= expected_end_exclusive:
        raise ValueError(
            "Downloaded weather extends beyond the requested date range."
        )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Refuse to overwrite an existing file without inspection.
    if OUTPUT_PATH.exists():
        raise FileExistsError(
            f"{OUTPUT_PATH} already exists. Inspect or rename it "
            "before downloading again."
        )

    df.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print("\nWeather download completed.")
    print(f"Output file: {OUTPUT_PATH}")
    print(f"Records: {len(df)}")
    print(f"Columns: {len(df.columns)}")
    print(f"First timestamp: {df['timestamp_utc'].min()}")
    print(f"Last timestamp: {df['timestamp_utc'].max()}")
    print(
        "Missing values by column:\n"
        + df.isna().sum().to_string()
    )
    print("\nSample records:")
    print(df.head().to_string(index=False))

    print("\nData provenance:")
    print("Source: Open-Meteo Historical Weather API")
    print("Weather model: ERA5")
    print("Coordinates: Berlin reference location")
    print("Timezone: UTC")
    print("Scope: Single-location weather observations")


if __name__ == "__main__":
    main()