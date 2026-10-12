from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "real_world"
    / "opsd_time_series.csv"
)


def main():
    if not DATA_PATH.exists():
        print(f"ERROR: Dataset not found at {DATA_PATH}")
        return

    print("Reading dataset columns...")

    # Read only five rows to avoid loading the entire large CSV.
    df = pd.read_csv(DATA_PATH, nrows=5, low_memory=False)

    print("\nDataset file:", DATA_PATH)
    print("Columns available:", len(df.columns))

    print("\n--- First 5 rows ---")
    print(df.head().to_string())

    print("\n--- Relevant columns ---")

    relevant_columns = [
        column
        for column in df.columns
        if any(
            keyword in column.lower()
            for keyword in [
                "timestamp",
                "load",
                "demand",
                "solar",
                "wind",
            ]
        )
    ]

    for column in relevant_columns:
        print(column)

    print("\nInspection complete.")


if __name__ == "__main__":
    main()