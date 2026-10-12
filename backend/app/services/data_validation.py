import pandas as pd


REQUIRED_COLUMNS = [
    "timestamp_utc",
    "asset_id",
    "solar_mw",
    "wind_mw",
    "demand_mw",
    "solar_irradiance_wm2",
    "cloud_cover_pct",
    "temperature_c",
    "wind_speed_ms",
    "wind_direction_deg",
    "battery_soc_pct",
    "asset_status",
    "data_source",
]


def validate_dataset(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Validate renewable energy records.

    Returns:
        valid_records: records that pass validation.
        invalid_records: rejected records with reasons.
    """

    data = df.copy()

    # Preserve original row numbers for traceability.
    data["_source_row"] = range(2, len(data) + 2)

    # Track why each record fails validation.
    data["_errors"] = [[] for _ in range(len(data))]

    # 1. Check required columns.
    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in data.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Dataset is missing required columns: {missing_columns}"
        )

    # 2. Check missing values.
    for column in REQUIRED_COLUMNS:
        missing = data[column].isna()

        for index in data.index[missing]:
            data.at[index, "_errors"].append(
                f"Missing required value: {column}"
            )

    # 3. Validate timestamps.
    parsed_timestamps = pd.to_datetime(
        data["timestamp_utc"],
        errors="coerce",
        utc=True,
    )

    invalid_timestamps = parsed_timestamps.isna()

    for index in data.index[invalid_timestamps]:
        data.at[index, "_errors"].append("Invalid timestamp")

    data["timestamp_utc"] = parsed_timestamps

    # 4. Validate numeric columns.
    numeric_columns = [
        "solar_mw",
        "wind_mw",
        "demand_mw",
        "solar_irradiance_wm2",
        "cloud_cover_pct",
        "temperature_c",
        "wind_speed_ms",
        "wind_direction_deg",
        "battery_soc_pct",
    ]

    for column in numeric_columns:
        original_values = data[column]

        data[column] = pd.to_numeric(
            original_values,
            errors="coerce",
        )

        invalid_numeric = (
            original_values.notna()
            & data[column].isna()
        )

        for index in data.index[invalid_numeric]:
            data.at[index, "_errors"].append(
                f"Non-numeric value: {column}"
            )

        non_finite = data[column].notna() & ~data[column].map(
            lambda value: __import__("math").isfinite(float(value))
        )

        for index in data.index[non_finite]:
            data.at[index, "_errors"].append(
                f"Non-finite value: {column}"
            )

    # 5. Validate physical ranges.
    ranges = {
        "solar_mw": (0, 10),
        "wind_mw": (0, 6),
        "demand_mw": (0, 1000),
        "solar_irradiance_wm2": (0, 1500),
        "cloud_cover_pct": (0, 100),
        "temperature_c": (-50, 60),
        "wind_speed_ms": (0, 100),
        "wind_direction_deg": (0, 360),
        "battery_soc_pct": (0, 100),
    }

    for column, (minimum, maximum) in ranges.items():
        outside_range = (
            data[column].notna()
            & (
                (data[column] < minimum)
                | (data[column] > maximum)
            )
        )

        for index in data.index[outside_range]:
            data.at[index, "_errors"].append(
                f"Out-of-range value: {column}"
            )

    # 6. Detect duplicate facility/timestamp readings.
    duplicate_rows = data.duplicated(
        subset=["asset_id", "timestamp_utc"],
        keep="first",
    )

    for index in data.index[duplicate_rows]:
        data.at[index, "_errors"].append(
            "Duplicate asset/timestamp record"
        )

    # 7. Separate valid and invalid records.
    valid_mask = data["_errors"].map(len) == 0

    valid_records = data.loc[valid_mask].copy()
    invalid_records = data.loc[~valid_mask].copy()

    # Store readable validation reasons.
    invalid_records["validation_errors"] = invalid_records[
        "_errors"
    ].map("; ".join)

    # Remove internal tracking fields from valid output.
    valid_records = valid_records.drop(
        columns=["_source_row", "_errors"]
    )

    return valid_records, invalid_records