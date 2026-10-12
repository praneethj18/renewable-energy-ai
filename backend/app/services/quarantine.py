from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

QUARANTINE_DIR = PROJECT_ROOT / "data" / "quarantine"


def save_quarantined_records(
    invalid_records: pd.DataFrame,
    source_name: str = "unknown",
) -> Path | None:
    """
    Save invalid records and their validation errors
    to a persistent quarantine CSV file.
    """

    if invalid_records.empty:
        return None

    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)

    output_file = (
        QUARANTINE_DIR
        / f"{Path(source_name).stem}_rejected.csv"
    )

    invalid_records.to_csv(output_file, index=False)

    return output_file