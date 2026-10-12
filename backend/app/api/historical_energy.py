from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(tags=["Historical Energy Data"])
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_PATH = PROJECT_ROOT / "data" / "real_world" / "germany_energy.csv"
REQUIRED = ("timestamp_utc", "solar_generation_mw", "wind_generation_mw", "demand_mw")


@router.get("/historical-energy")
def historical_energy(limit: int = Query(default=168, ge=1, le=2000)) -> dict[str, Any]:
    """Return public historical Germany energy data; this is not live site telemetry."""
    if not DATA_PATH.exists():
        raise HTTPException(status_code=404, detail="Historical dataset not found at data/real_world/germany_energy.csv.")
    rows: list[dict[str, Any]] = []
    try:
        with DATA_PATH.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            missing = [name for name in REQUIRED if name not in (reader.fieldnames or [])]
            if missing:
                raise HTTPException(status_code=422, detail=f"Dataset is missing expected normalized columns: {', '.join(missing)}")
            for raw in reader:
                try:
                    timestamp = datetime.fromisoformat(raw["timestamp_utc"].replace("Z", "+00:00"))
                    values = {}
                    for key in REQUIRED[1:]:
                        text = (raw.get(key) or "").strip()
                        values[key] = float(text) if text else None
                        if values[key] is not None and not __import__("math").isfinite(values[key]):
                            values[key] = None
                    if timestamp.tzinfo is None:
                        timestamp = timestamp.replace(tzinfo=__import__("datetime").timezone.utc)
                    rows.append({
                        "timestamp_utc": timestamp.isoformat(),
                        "solar_generation_mw": values["solar_generation_mw"],
                        "wind_generation_mw": values["wind_generation_mw"],
                        "demand_mw": values["demand_mw"],
                    })
                except (ValueError, TypeError, OverflowError):
                    continue
    except HTTPException:
        raise
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Could not read historical dataset: {exc}") from exc
    rows.sort(key=lambda row: row["timestamp_utc"])
    return {
        "source": "OPSD Germany",
        "geographic_scope": "Germany regional energy data",
        "data_type": "historical_public_data",
        "is_live_telemetry": False,
        "records_available": len(rows),
        "records": rows[-limit:],
    }
