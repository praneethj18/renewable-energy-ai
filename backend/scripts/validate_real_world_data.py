from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "real_world"
    / "germany_energy.csv"
)


def main():
    print("Loading real-world energy dataset...")

    df = pd.read_csv(DATA_PATH)

    df["timestamp_utc"] = pd.to_datetime(
        df["timestamp_utc"],
        utc=True,
        errors="coerce",
    )

    energy_columns = [
        "solar_generation_mw",
        "wind_generation_mw",
        "demand_mw",
    ]

    print("\n--- Dataset Overview ---")
    print("Total records:", len(df))
    print("Total columns:", len(df.columns))
    print("Start:", df["timestamp_utc"].min())
    print("End:", df["timestamp_utc"].max())

    print("\n--- Missing Values ---")
    print(df.isnull().sum())

    print("\n--- Negative Values ---")
    for column in energy_columns:
        count = (df[column] < 0).sum()
        print(f"{column}: {count}")

    print("\n--- Duplicate Timestamps ---")
    print(df["timestamp_utc"].duplicated().sum())

    print("\n--- Hourly Continuity ---")
    expected_hours = pd.date_range(
        start=df["timestamp_utc"].min(),
        end=df["timestamp_utc"].max(),
        freq="h",
    )

    actual_hours = pd.DatetimeIndex(
        df["timestamp_utc"].dropna().unique()
    )

    missing_hours = expected_hours.difference(actual_hours)

    print("Expected hourly timestamps:", len(expected_hours))
    print("Actual unique timestamps:", len(actual_hours))
    print("Missing hourly timestamps:", len(missing_hours))

    print("\n--- Energy Statistics (MW) ---")
    print(df[energy_columns].describe().round(2))

    print("\nValidation inspection complete.")


if __name__ == "__main__":
    main()