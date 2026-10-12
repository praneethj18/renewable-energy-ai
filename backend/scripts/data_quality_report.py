import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.data_validation import validate_dataset


DATASET_PATH = PROJECT_ROOT / "data" / "synthetic_energy.csv"
REPORT_PATH = PROJECT_ROOT / "reports" / "data_quality_report.txt"
INVALID_PATH = PROJECT_ROOT / "reports" / "quarantined_records.csv"


def main():
    # Load the historical dataset.
    df = pd.read_csv(DATASET_PATH)

    # Validate all records.
    valid, invalid = validate_dataset(df)

    # Calculate quality statistics.
    total = len(df)
    valid_count = len(valid)
    invalid_count = len(invalid)

    acceptance_rate = (
        (valid_count / total) * 100 if total else 0
    )

    # Summarise the reasons for rejection.
    if invalid_count:
        error_summary = (
            invalid["validation_errors"]
            .str.split("; ")
            .explode()
            .value_counts()
        )
    else:
        error_summary = pd.Series(dtype=int)

    # Build the report.
    lines = [
        "RENEWABLE ENERGY AI - DATA QUALITY REPORT",
        "=" * 45,
        f"Total records processed: {total}",
        f"Valid records: {valid_count}",
        f"Invalid records: {invalid_count}",
        f"Acceptance rate: {acceptance_rate:.2f}%",
        "",
        "VALIDATION ERROR SUMMARY",
        "-" * 30,
    ]

    if error_summary.empty:
        lines.append("No validation errors found.")
    else:
        for reason, count in error_summary.items():
            lines.append(f"{reason}: {count}")

    report_text = "\n".join(lines)

    # Ensure the reports directory exists.
    REPORT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Save the quality report.
    REPORT_PATH.write_text(
        report_text,
        encoding="utf-8",
    )

    # Save rejected records separately.
    if not invalid.empty:
        invalid.to_csv(
            INVALID_PATH,
            index=False,
        )

    print(report_text)
    print()
    print(f"Report saved to: {REPORT_PATH}")

    if not invalid.empty:
        print(f"Rejected records saved to: {INVALID_PATH}")
    else:
        print("No rejected records to save.")


if __name__ == "__main__":
    main()