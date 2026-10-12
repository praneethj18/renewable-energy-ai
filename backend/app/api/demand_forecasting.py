from datetime import datetime, timezone
import hashlib
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
import pandas as pd

from app.workflows.demand_forecasting import (
    DATASET_PATH,
    MODEL_PATH,
    _load_history,
    demand_forecasting_node,
)

router = APIRouter(prefix="/forecast", tags=["Demand Forecasting"])


class DemandForecastRequest(BaseModel):
    forecast_timestamp: datetime
    temperature_c: float = Field(ge=-50, le=70)

    @field_validator("forecast_timestamp")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Forecast timestamp must include a timezone.")
        return value


@router.get("/demand/constraints")
def demand_forecast_constraints() -> dict[str, Any]:
    history = _load_history()
    observed = set(history["timestamp_utc"])
    latest = max(observed)
    valid_forecast_timestamps = sorted(
        timestamp + pd.Timedelta(hours=24)
        for timestamp in observed
        if latest < timestamp + pd.Timedelta(hours=24) <= latest + pd.Timedelta(hours=24)
    )
    if not valid_forecast_timestamps:
        raise HTTPException(
            status_code=422,
            detail="No forecast timestamp has an exact historical 24-hour lag in the available history.",
        )
    candidate = valid_forecast_timestamps[0]
    return {
        "latest_observation_utc": latest.isoformat(),
        "earliest_forecast_timestamp_utc": candidate.isoformat(),
        "latest_valid_forecast_timestamp_utc": valid_forecast_timestamps[-1].isoformat(),
        "valid_forecast_timestamps_utc": [value.isoformat() for value in valid_forecast_timestamps],
        "required_lag_hours": 24,
        "interval_minutes": 60,
        "model_version": hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest()[:12],
        "data_source": DATASET_PATH.name,
    }


@router.post("/demand")
def forecast_demand(request: DemandForecastRequest) -> dict[str, Any]:
    timestamp = request.forecast_timestamp
    timestamp = timestamp.astimezone(timezone.utc)
    history = _load_history()
    required_lag = pd.Timestamp(timestamp) - pd.Timedelta(hours=24)
    if not history["timestamp_utc"].eq(required_lag).any():
        raise HTTPException(
            status_code=422,
            detail=(
                "No historical demand observation exists exactly 24 hours "
                f"before {timestamp.isoformat()} ({required_lag.isoformat()}). "
                "Choose a timestamp with an observed previous-day value."
            ),
        )

    state = {
        "weather_data": {
            "hourly_forecast": [
                {
                    "timestamp_utc": timestamp.isoformat(),
                    "temperature_c": request.temperature_c,
                }
            ]
        }
    }
    result = demand_forecasting_node(state)
    demand_result = result.get("agent_results", {}).get("demand_forecasting", {})
    if demand_result.get("status") != "success":
        raise HTTPException(
            status_code=422,
            detail=demand_result.get("message", "Demand forecast failed."),
        )
    return result
