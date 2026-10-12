import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.data_pipeline import process_dataset


test_file = PROJECT_ROOT / "data" / "test_pipeline_invalid.csv"

# Create a deliberately invalid dataset.
df = pd.DataFrame([
    {
        "timestamp_utc": "2026-10-11T00:00:00Z",
        "asset_id": "TEST_SOLAR",
        "solar_mw": 5,
        "wind_mw": 2,
        "demand_mw": 100,
        "solar_irradiance_wm2": 700,
        "cloud_cover_pct": 20,
        "temperature_c": 30,
        "wind_speed_ms": 5,
        "wind_direction_deg": 180,
        "battery_soc_pct": 60,
        "asset_status": "available",
        "data_source": "test",
    },
    {
        "timestamp_utc": "INVALID_TIMESTAMP",
        "asset_id": "TEST_WIND",
        "solar_mw": 2,
        "wind_mw": 2,
        "demand_mw": 100,
        "solar_irradiance_wm2": 700,
        "cloud_cover_pct": 20,
        "temperature_c": 30,
        "wind_speed_ms": 5,
        "wind_direction_deg": 180,
        "battery_soc_pct": 60,
        "asset_status": "available",
        "data_source": "test",
    },
])

try:
    df.to_csv(test_file, index=False)

    print("INVALID DATA PIPELINE TEST")
    print("-" * 40)

    result = process_dataset(test_file)

    print(f"Total records: {result['total_records']}")
    print(f"Valid records: {result['valid_records']}")
    print(f"Invalid records: {result['invalid_records']}")

    if not result["invalid_data"].empty:
        print("\nValidation errors:")
        print(
            result["invalid_data"][
                ["asset_id", "validation_errors"]
            ].to_string(index=False)
        )

    assert result["total_records"] == 2
    assert result["valid_records"] == 1
    assert result["invalid_records"] == 1

    print("\nSUCCESS: Invalid records were identified.")

finally:
    test_file.unlink(missing_ok=True)