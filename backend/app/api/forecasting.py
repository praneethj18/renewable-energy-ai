from datetime import datetime, timezone
from math import isfinite
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Asset
from app.services.forecasting import predict_generation, get_generation_model_metadata


router = APIRouter(
    prefix="/generation-forecast",
    tags=["Generation Forecasting"],
)


class GenerationForecastRequest(BaseModel):
    solar_irradiance_wm2: float = Field(ge=0, le=1500)
    cloud_cover_pct: float = Field(ge=0, le=100)
    temperature_c: float = Field(ge=-50, le=70)
    wind_speed_ms: float = Field(ge=0, le=100)
    wind_direction_deg: float = Field(ge=0, le=360)
    valid_timestamp_utc: datetime | None = None

    @field_validator("valid_timestamp_utc")
    @classmethod
    def require_utc_aware_timestamp(cls, value):
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Forecast valid timestamp must include a timezone.")
        return value


class GenerationForecastResponse(BaseModel):
    target: str
    predicted_generation_mw: float
    unit: str
    model_source: str
    data_source: str
    validation_note: str
    issued_at_utc: str
    valid_timestamp_utc: str
    model_version: str
    installed_capacity_mw: float
    clipped: bool
    clipping_reason: str | None = None
    status: str
    evaluation: dict | None = None
    feature_order: list[str]


@router.post(
    "/{target}",
    response_model=GenerationForecastResponse,
)
def forecast_generation(
    target: Literal["solar", "wind"],
    request: GenerationForecastRequest,
    db: Session = Depends(get_db),
):
    weather = request.model_dump()

    try:
        prediction = predict_generation(
            target=target,
            weather=weather,
        )

        metadata = get_generation_model_metadata(target)
        capacity = db.scalar(
            select(func.coalesce(func.sum(Asset.capacity_mw), 0.0)).where(
                Asset.asset_type == target,
                Asset.is_active.is_(True),
            )
        ) or 0.0
        raw_prediction = prediction
        if target == "solar" and request.solar_irradiance_wm2 <= 0:
            prediction = 0.0
        prediction = min(prediction, float(capacity))
        clipping_reasons = []
        if prediction != raw_prediction:
            clipping_reasons.append("model output constrained by installed capacity or zero solar irradiance")
        issued_at = datetime.now(timezone.utc)
        valid_at = request.valid_timestamp_utc or issued_at
        valid_at = valid_at.astimezone(timezone.utc)

        if not isfinite(prediction):
            raise ValueError(
                "The model returned a non-finite prediction."
            )

        return GenerationForecastResponse(
            target=target,
            predicted_generation_mw=round(prediction, 4),
            unit="MW",
            model_source=f"models/{target}_forecast_model.joblib",
            data_source=metadata["data_source"],
            validation_note=(
                "Experimental estimate from a model trained on synthetic "
                "data; not validated for real-world facility operation. "
                + ("No active installed capacity is registered for this target." if capacity <= 0 else "")
            ),
            issued_at_utc=issued_at.isoformat(),
            valid_timestamp_utc=valid_at.isoformat(),
            model_version=metadata["model_version"],
            installed_capacity_mw=float(capacity),
            clipped=bool(clipping_reasons),
            clipping_reason="; ".join(clipping_reasons) or None,
            status="no_active_capacity" if capacity <= 0 else "success",
            evaluation=metadata["evaluation"],
            feature_order=metadata["feature_order"],
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
