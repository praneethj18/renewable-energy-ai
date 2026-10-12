import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.data_validation import validate_dataset


PROJECT_ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]

dataset_path = PROJECT_ROOT / "data" / "synthetic_energy.csv"

df = pd.read_csv(dataset_path)

valid, invalid = validate_dataset(df)

print("DATA VALIDATION RESULTS")
print("-" * 40)
print(f"Total records: {len(df)}")
print(f"Valid records: {len(valid)}")
print(f"Invalid records: {len(invalid)}")

if not invalid.empty:
    print("\nInvalid record examples:")
    print(
        invalid[
            ["_source_row", "validation_errors"]
        ].head(10).to_string(index=False)
    )

print("\nValidation test completed.")