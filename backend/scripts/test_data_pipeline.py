import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.data_pipeline import process_dataset

dataset_path = PROJECT_ROOT / "data" / "synthetic_energy.csv"

print("DATA PIPELINE TEST")
print("-" * 40)

result = process_dataset(dataset_path)

print(f"Total records: {result['total_records']}")
print(f"Valid records: {result['valid_records']}")
print(f"Invalid records: {result['invalid_records']}")
print(f"Acceptance rate: {result['acceptance_rate_pct']}%")

assert result["total_records"] == 2160

assert (
    result["valid_records"] + result["invalid_records"]
    == result["total_records"]
)

print("\nSUCCESS: Data pipeline test passed.")