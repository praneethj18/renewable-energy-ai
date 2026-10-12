from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "real_world"
    / "opsd_time_series.csv"
)

OUTPUT_DIR = PROJECT_ROOT / "data" / "real_world"
OUTPUT_PATH = OUTPUT_DIR / "germany_energy.csv"

REQUIRED_COLUMNS = [
    "utc_timestamp",
    "DE_solar_generation_actual",
    "DE_wind_generation_actual",
    "DE_load_actual_entsoe_transparency",
]


def main():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {INPUT_PATH}"
        )

    print("Reading required German energy columns...")

    df = pd.read_csv(
        INPUT_PATH,
        usecols=lambda column: column in REQUIRED_COLUMNS,
        low_memory=False,
    )

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    df = df.rename(
        columns={
            "utc_timestamp": "timestamp_utc",
            "DE_solar_generation_actual": "solar_generation_mw",
            "DE_wind_generation_actual": "wind_generation_mw",
            "DE_load_actual_entsoe_transparency": "demand_mw",
        }
    )

    df["timestamp_utc"] = pd.to_datetime(
        df["timestamp_utc"],
        utc=True,
        errors="coerce",
    )

    numeric_columns = [
        "solar_generation_mw",
        "wind_generation_mw",
        "demand_mw",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    # Remove missing timestamps and rows without all three
    # actual energy measurements.
    df = df.dropna(
        subset=["timestamp_utc"] + numeric_columns
    )

    # Remove physically impossible negative measurements.
    df = df[
        (df["solar_generation_mw"] >= 0)
        & (df["wind_generation_mw"] >= 0)
        & (df["demand_mw"] >= 0)
    ]

    df = df.sort_values("timestamp_utc")
    df = df.drop_duplicates(
        subset=["timestamp_utc"],
        keep="last",
    )

    df["data_source"] = "OPSD_Germany"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df.to_csv(OUTPUT_PATH, index=False)

    print("\nReal-world dataset prepared successfully.")
    print("Output:", OUTPUT_PATH)
    print("Valid records:", len(df))
    print("First timestamp:", df["timestamp_utc"].min())
    print("Last timestamp:", df["timestamp_utc"].max())

    print("\nSample records:")
    print(df.head().to_string(index=False))

    print("\nData source: Open Power System Data (OPSD)")
    print("Geographic scope: Germany")
    print("Measurements: National/regional energy data")
    print("Note: These are not individual-facility measurements.")


if __name__ == "__main__":
    main()