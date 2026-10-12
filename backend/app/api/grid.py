from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import BatteryConfiguration
from app.services.grid_optimizer import (
    GridConfig,
    optimize_battery_schedule,
)

router = APIRouter(prefix="/grid", tags=["Grid Coordination"])


class GridOptimizationRequest(BaseModel):
    generation_forecast_mw: list[float] = Field(min_length=1)
    demand_forecast_mw: list[float] = Field(min_length=1)

    initial_soc_pct: float = Field(default=45.0, ge=10, le=90)
    terminal_soc_pct: float = Field(default=45.0, ge=10, le=90)
    timestep_hours: float = Field(default=1.0, gt=0)

    @model_validator(mode="after")
    def validate_forecast_lengths(self):
        if len(self.generation_forecast_mw) != len(self.demand_forecast_mw):
            raise ValueError(
                "Generation and demand forecast lengths must match."
            )
        return self


class EnergyBalanceRequest(BaseModel):
    solar_generation_mw: list[float] = Field(min_length=1)
    wind_generation_mw: list[float] = Field(min_length=1)
    demand_mw: list[float] = Field(min_length=1)
    timestamps_utc: list[str] | None = None
    tolerance_mw: float = Field(default=0.1, ge=0)

    @model_validator(mode="after")
    def validate_lengths(self):
        lengths = {
            len(self.solar_generation_mw),
            len(self.wind_generation_mw),
            len(self.demand_mw),
        }
        if len(lengths) != 1:
            raise ValueError("Solar, wind, and demand forecast lengths must match.")
        if self.timestamps_utc is not None and len(self.timestamps_utc) != len(self.demand_mw):
            raise ValueError("Timestamp count must match the forecast interval count.")
        return self


@router.post("/balance")
def calculate_energy_balance(request: EnergyBalanceRequest):
    intervals = []
    for index, (solar, wind, demand) in enumerate(zip(
        request.solar_generation_mw,
        request.wind_generation_mw,
        request.demand_mw,
    )):
        if min(solar, wind, demand) < 0:
            raise HTTPException(status_code=422, detail="Power values cannot be negative.")
        generation = solar + wind
        balance = generation - demand
        intervals.append({
            "timestamp_utc": request.timestamps_utc[index] if request.timestamps_utc else None,
            "solar_generation_mw": solar,
            "wind_generation_mw": wind,
            "total_generation_mw": round(generation, 4),
            "demand_mw": demand,
            "balance_mw": round(balance, 4),
            "surplus_mw": round(max(0.0, balance), 4),
            "deficit_mw": round(max(0.0, -balance), 4),
            "status": "balanced" if abs(balance) <= request.tolerance_mw else "surplus" if balance > 0 else "deficit",
        })
    return {
        "tolerance_mw": request.tolerance_mw,
        "intervals": intervals,
        "data_kind": "forecast_or_scenario",
    }


@router.post("/optimize")
def optimize_grid(request: GridOptimizationRequest, db: Session = Depends(get_db)):
    try:
        battery = db.get(BatteryConfiguration, 1)
        defaults = GridConfig()
        config = GridConfig(
            battery_capacity_mwh=battery.capacity_mwh if battery else defaults.battery_capacity_mwh,
            max_charge_mw=(
                battery.max_charge_mw
                if battery and battery.is_available
                else 0.0
            ),
            max_discharge_mw=(
                battery.max_discharge_mw
                if battery and battery.is_available
                else 0.0
            ),
            min_soc_pct=battery.min_soc_pct if battery else defaults.min_soc_pct,
            max_soc_pct=battery.max_soc_pct if battery else defaults.max_soc_pct,
            charge_efficiency=battery.charge_efficiency if battery else defaults.charge_efficiency,
            discharge_efficiency=battery.discharge_efficiency if battery else defaults.discharge_efficiency,
            initial_soc_pct=request.initial_soc_pct,
            terminal_soc_pct=request.terminal_soc_pct,
        )

        result = optimize_battery_schedule(
            generation_forecast_mw=request.generation_forecast_mw,
            demand_forecast_mw=request.demand_forecast_mw,
            config=config,
            timestep_hours=request.timestep_hours,
        )

        return result

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Grid optimization failed.",
        ) from exc
