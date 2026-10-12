from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Asset, Measurement

router = APIRouter(prefix="/measurements", tags=["Measurements"])


class MeasurementCreate(BaseModel):
    asset_id: int = Field(gt=0)
    timestamp: datetime
    generation_mw: float = Field(ge=0)
    demand_mw: float = Field(ge=0)
    solar_irradiance: float | None = Field(default=None, ge=0)
    temperature_c: float | None = Field(default=None, ge=-90, le=70)
    wind_speed_ms: float | None = Field(default=None, ge=0, le=150)
    cloud_cover_pct: float | None = Field(default=None, ge=0, le=100)

    @field_validator("timestamp")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Timestamp must include a timezone, such as +00:00")
        return value


class MeasurementResponse(BaseModel):
    id: int
    asset_id: int
    timestamp: datetime
    generation_mw: float
    demand_mw: float
    solar_irradiance: float | None
    temperature_c: float | None
    wind_speed_ms: float | None
    cloud_cover_pct: float | None

    model_config = {"from_attributes": True}


@router.post("/", response_model=MeasurementResponse, status_code=status.HTTP_201_CREATED)
def create_measurement(
    payload: MeasurementCreate,
    db: Session = Depends(get_db),
):
    asset = db.get(Asset, payload.asset_id)

    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    if payload.generation_mw > asset.capacity_mw:
        raise HTTPException(
            status_code=422,
            detail="Generation cannot exceed the asset's configured capacity",
        )

    measurement = Measurement(**payload.model_dump())
    db.add(measurement)
    db.commit()
    db.refresh(measurement)

    return measurement


@router.get("/", response_model=list[MeasurementResponse])
def list_measurements(
    asset_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    query = db.query(Measurement)

    if asset_id is not None:
        query = query.filter(Measurement.asset_id == asset_id)

    return query.order_by(Measurement.timestamp.desc()).limit(limit).all()