import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.data_pipeline import process_dataset
from backend.app.services.quarantine import save_quarantined_records


TEST_FILE = PROJECT_ROOT / "data" / "test_quarantine_input.csv"

record = {
    "timestamp_utc": "INVALID_TIMESTAMP",
    "asset_id": "TEST_QUARANTINE",
    "solar_mw": 2,
    "wind_mw": 1,
    "demand_mw": 100,
    "solar_irradiance_wm2": 500,
    "cloud_cover_pct": 20,
    "temperature_c": 30,
    "wind_speed_ms": 5,
    "wind_direction_deg": 180,
    "battery_soc_pct": 60,
    "asset_status": "available",
    "data_source": "quarantine_test",
}

try:
    # Create a temporary input dataset.
    pd.DataFrame([record]).to_csv(TEST_FILE, index=False)

    # Process and validate the dataset.
    result = process_dataset(TEST_FILE)

    print("QUARANTINE TEST")
    print("-" * 40)
    print(f"Total records: {result['total_records']}")
    print(f"Valid records: {result['valid_records']}")
    print(f"Invalid records: {result['invalid_records']}")

    assert result["invalid_records"] == 1

    # Persist rejected records.
    quarantine_file = save_quarantined_records(
        result["invalid_data"],
        source_name="test_quarantine",
    )

    assert quarantine_file is not None
    assert quarantine_file.exists()

    # Read the file back to verify persistence.
    saved_records = pd.read_csv(quarantine_file)

    assert len(saved_records) == 1
    assert "validation_errors" in saved_records.columns

    print(f"\nQuarantine file: {quarantine_file}")
    print(f"Saved rejected records: {len(saved_records)}")
    print("Validation error:", saved_records["validation_errors"].iloc[0])
    print("\nSUCCESS: Quarantine storage test passed.")

finally:
    TEST_FILE.unlink(missing_ok=True)