from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import BatteryConfiguration
from app.services.battery_management import (
    BatteryConfig,
    calculate_battery_limits,
    validate_battery_action,
)


router = APIRouter(prefix="/battery", tags=["Battery Storage"])


class BatteryConfigurationInput(BaseModel):
    capacity_mwh: float = Field(gt=0)
    max_charge_mw: float = Field(ge=0)
    max_discharge_mw: float = Field(ge=0)
    min_soc_pct: float = Field(ge=0, le=100)
    max_soc_pct: float = Field(gt=0, le=100)
    charge_efficiency: float = Field(gt=0, le=1)
    discharge_efficiency: float = Field(gt=0, le=1)
    configured_soc_pct: float = Field(ge=0, le=100)
    is_available: bool = False

    @model_validator(mode="after")
    def validate_soc_bounds(self):
        if self.min_soc_pct >= self.max_soc_pct:
            raise ValueError("Minimum SoC must be below maximum SoC.")
        if not self.min_soc_pct <= self.configured_soc_pct <= self.max_soc_pct:
            raise ValueError("Configured SoC must be within battery SoC limits.")
        return self


class BatteryActionInput(BaseModel):
    soc_pct: float = Field(ge=0, le=100)
    charge_mw: float = Field(default=0, ge=0)
    discharge_mw: float = Field(default=0, ge=0)
    duration_hours: float = Field(default=1, gt=0, le=24)


def _configuration(db: Session) -> BatteryConfiguration:
    row = db.get(BatteryConfiguration, 1)
    if row is None:
        row = BatteryConfiguration(id=1)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _config(row: BatteryConfiguration) -> BatteryConfig:
    return BatteryConfig(
        capacity_mwh=row.capacity_mwh,
        max_charge_mw=row.max_charge_mw,
        max_discharge_mw=row.max_discharge_mw,
        min_soc_pct=row.min_soc_pct,
        max_soc_pct=row.max_soc_pct,
        charge_efficiency=row.charge_efficiency,
        discharge_efficiency=row.discharge_efficiency,
    )


def _response(row: BatteryConfiguration) -> dict:
    return {
        "capacity_mwh": row.capacity_mwh,
        "max_charge_mw": row.max_charge_mw,
        "max_discharge_mw": row.max_discharge_mw,
        "min_soc_pct": row.min_soc_pct,
        "max_soc_pct": row.max_soc_pct,
        "charge_efficiency": row.charge_efficiency,
        "discharge_efficiency": row.discharge_efficiency,
        "configured_soc_pct": row.configured_soc_pct,
        "is_available": row.is_available,
        "state_source": "configured value; no battery telemetry is connected",
        "updated_at": row.updated_at,
    }


@router.get("/configuration")
def get_battery_configuration(db: Session = Depends(get_db)):
    return _response(_configuration(db))


@router.put("/configuration")
def update_battery_configuration(
    payload: BatteryConfigurationInput,
    db: Session = Depends(get_db),
):
    row = _configuration(db)
    for field, value in payload.model_dump().items():
        setattr(row, field, value)
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _response(row)


@router.get("/status")
def get_battery_status(db: Session = Depends(get_db)):
    row = _configuration(db)
    limits = calculate_battery_limits(row.configured_soc_pct, _config(row))
    return {
        **_response(row),
        **limits,
    }


@router.post("/validate")
def validate_battery_operation(
    payload: BatteryActionInput,
    db: Session = Depends(get_db),
):
    row = _configuration(db)
    if not row.is_available and (payload.charge_mw or payload.discharge_mw):
        raise HTTPException(status_code=422, detail="Battery is configured as unavailable.")
    try:
        result = validate_battery_action(
            soc_pct=payload.soc_pct,
            charge_mw=payload.charge_mw,
            discharge_mw=payload.discharge_mw,
            duration_hours=payload.duration_hours,
            config=_config(row),
        )
        return {**result, "constraints": _response(row)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
