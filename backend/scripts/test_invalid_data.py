import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.data_validation import validate_dataset


# Load a few known-good records from the existing dataset.
dataset_path = PROJECT_ROOT / "data" / "synthetic_energy.csv"
df = pd.read_csv(dataset_path).head(5).copy()

# Test 1: Negative solar generation.
df.loc[df.index[0], "solar_mw"] = -2

# Test 2: Solar generation exceeds the configured capacity.
df.loc[df.index[1], "solar_mw"] = 15

# Test 3: Cloud cover exceeds 100%.
df.loc[df.index[2], "cloud_cover_pct"] = 120

# Test 4: Battery state of charge exceeds 100%.
df.loc[df.index[3], "battery_soc_pct"] = 150

# Test 5: Missing timestamp.
df.loc[df.index[4], "timestamp_utc"] = None

# Run validation.
valid, invalid = validate_dataset(df)

print("INVALID DATA VALIDATION TEST")
print("-" * 40)
print(f"Test records: {len(df)}")
print(f"Valid records: {len(valid)}")
print(f"Rejected records: {len(invalid)}")

if not invalid.empty:
    print("\nDetected validation errors:")

    print(
        invalid[
            ["_source_row", "validation_errors"]
        ].to_string(index=False)
    )

# Basic test assertions.
assert len(valid) == 0, "Some deliberately invalid records passed!"
assert len(invalid) == 5, "The validator did not reject all five records!"

print("\nSUCCESS: All five invalid records were rejected.")