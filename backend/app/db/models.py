from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(30), nullable=False)
    capacity_mw: Mapped[float] = mapped_column(Float, nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    measurements: Mapped[list["Measurement"]] = relationship(
        back_populates="asset",
        cascade="all, delete-orphan",
    )


class Measurement(Base):
    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id"),
        nullable=False,
        index=True,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    generation_mw: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    demand_mw: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    solar_irradiance: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    temperature_c: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    wind_speed_ms: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    cloud_cover_pct: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    asset: Mapped["Asset"] = relationship(back_populates="measurements")


class WeatherObservation(Base):
    __tablename__ = "weather_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    precipitation_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    cloud_cover_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_speed_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_direction_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    solar_radiation_wm2: Mapped[float | None] = mapped_column(Float, nullable=True)

    source: Mapped[str] = mapped_column(
        String(50),
        default="Open-Meteo",
        nullable=False,
    )

    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class BatteryConfiguration(Base):
    __tablename__ = "battery_configuration"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    capacity_mwh: Mapped[float] = mapped_column(Float, default=8.0, nullable=False)
    max_charge_mw: Mapped[float] = mapped_column(Float, default=2.0, nullable=False)
    max_discharge_mw: Mapped[float] = mapped_column(Float, default=2.0, nullable=False)
    min_soc_pct: Mapped[float] = mapped_column(Float, default=10.0, nullable=False)
    max_soc_pct: Mapped[float] = mapped_column(Float, default=90.0, nullable=False)
    charge_efficiency: Mapped[float] = mapped_column(Float, default=0.95, nullable=False)
    discharge_efficiency: Mapped[float] = mapped_column(Float, default=0.95, nullable=False)
    configured_soc_pct: Mapped[float] = mapped_column(Float, default=45.0, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    approval_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    plan_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    state_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    approval_history: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    workflow_id: Mapped[str | None] = mapped_column(
        ForeignKey("workflow_runs.id"), nullable=True, index=True
    )
    asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("assets.id"), nullable=True, index=True
    )
    fingerprint: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
