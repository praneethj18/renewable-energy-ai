import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.data_ingestion import load_dataset


dataset_path = PROJECT_ROOT / "data" / "synthetic_energy.csv"

print("DATA INGESTION TEST")
print("-" * 40)

df = load_dataset(dataset_path)

print(f"File loaded: {dataset_path.name}")
print(f"Total records: {len(df)}")
print(f"Total columns: {len(df.columns)}")

print("\nColumn names:")
print(df.columns.tolist())

print("\nFirst five records:")
print(df.head().to_string(index=False))

assert len(df) == 2160, "Unexpected number of records!"
assert len(df.columns) > 0, "No columns were loaded!"

print("\nSUCCESS: Dataset ingestion test passed.")

print("\nERROR HANDLING TEST")
print("-" * 40)

# Test 1: A file that does not exist.
missing_file = PROJECT_ROOT / "data" / "missing_dataset.csv"

try:
    load_dataset(missing_file)
    raise AssertionError("Missing file was not rejected!")
except FileNotFoundError:
    print("PASS: Missing file was rejected correctly.")

# Test 2: An unsupported file extension.
unsupported_file = PROJECT_ROOT / "data" / "sample.json"
unsupported_file.write_text('{"test": true}', encoding="utf-8")

try:
    load_dataset(unsupported_file)
    raise AssertionError("Unsupported format was not rejected!")
except ValueError:
    print("PASS: Unsupported file format was rejected correctly.")
finally:
    unsupported_file.unlink(missing_ok=True)

print("\nSUCCESS: Error handling tests passed.")

print("\nEXCEL INGESTION TEST")
print("-" * 40)

# Create a temporary Excel file using sample records.
excel_path = PROJECT_ROOT / "data" / "test_energy.xlsx"

try:
    sample_df = df.head(5).copy()

    sample_df.to_excel(
        excel_path,
        index=False,
    )

    # Load the Excel file using our ingestion service.
    excel_df = load_dataset(excel_path)

    print(f"Excel records loaded: {len(excel_df)}")
    print(f"Excel columns loaded: {len(excel_df.columns)}")

    assert len(excel_df) == 5
    assert list(excel_df.columns) == list(sample_df.columns)

    print("PASS: Excel ingestion works correctly.")

finally:
    excel_path.unlink(missing_ok=True)

print("\nSUCCESS: Excel ingestion test passed.")