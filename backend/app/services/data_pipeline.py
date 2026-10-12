from pathlib import Path

from backend.app.services.data_ingestion import load_dataset
from backend.app.services.data_validation import validate_dataset


def process_dataset(
    file_path: str | Path,
) -> dict:
    """
    Load a dataset, validate its records,
    and return valid and invalid records.
    """

    # Step 1: Load the CSV or Excel file.
    df = load_dataset(file_path)

    # Step 2: Validate the loaded records.
    valid_records, invalid_records = validate_dataset(df)

    # Step 3: Prepare processing statistics.
    total_records = len(df)
    valid_count = len(valid_records)
    invalid_count = len(invalid_records)

    acceptance_rate = (
        (valid_count / total_records) * 100
        if total_records > 0
        else 0.0
    )

    return {
        "total_records": total_records,
        "valid_records": valid_count,
        "invalid_records": invalid_count,
        "acceptance_rate_pct": round(acceptance_rate, 2),
        "valid_data": valid_records,
        "invalid_data": invalid_records,
    }