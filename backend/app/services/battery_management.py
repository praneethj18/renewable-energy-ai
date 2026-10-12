from dataclasses import dataclass


@dataclass
class BatteryConfig:
    capacity_mwh: float = 8.0
    max_charge_mw: float = 2.0
    max_discharge_mw: float = 2.0
    min_soc_pct: float = 10.0
    max_soc_pct: float = 90.0
    charge_efficiency: float = 0.95
    discharge_efficiency: float = 0.95


def validate_battery_config(config: BatteryConfig) -> None:
    if config.capacity_mwh <= 0:
        raise ValueError("Battery capacity must be positive.")

    if config.max_charge_mw < 0 or config.max_discharge_mw < 0:
        raise ValueError("Battery power limits cannot be negative.")

    if not 0 <= config.min_soc_pct < config.max_soc_pct <= 100:
        raise ValueError("Invalid battery SoC limits.")

    if not 0 < config.charge_efficiency <= 1:
        raise ValueError("Invalid charging efficiency.")

    if not 0 < config.discharge_efficiency <= 1:
        raise ValueError("Invalid discharging efficiency.")


def calculate_battery_limits(
    soc_pct: float,
    config: BatteryConfig | None = None,
) -> dict:
    if config is None:
        config = BatteryConfig()

    validate_battery_config(config)

    if not 0 <= soc_pct <= 100:
        raise ValueError("SoC must be between 0 and 100.")

    current_energy_mwh = config.capacity_mwh * soc_pct / 100

    min_energy_mwh = (
        config.capacity_mwh * config.min_soc_pct / 100
    )

    max_energy_mwh = (
        config.capacity_mwh * config.max_soc_pct / 100
    )

    return {
        "capacity_mwh": config.capacity_mwh,
        "soc_pct": soc_pct,
        "current_energy_mwh": round(current_energy_mwh, 4),
        "minimum_energy_mwh": round(min_energy_mwh, 4),
        "maximum_energy_mwh": round(max_energy_mwh, 4),
        "available_charge_energy_mwh": round(
            max(0, max_energy_mwh - current_energy_mwh), 4
        ),
        "available_discharge_energy_mwh": round(
            max(0, current_energy_mwh - min_energy_mwh), 4
        ),
        "max_charge_mw": config.max_charge_mw,
        "max_discharge_mw": config.max_discharge_mw,
        "charge_efficiency": config.charge_efficiency,
        "discharge_efficiency": config.discharge_efficiency,
    }


def validate_battery_action(
    soc_pct: float,
    charge_mw: float,
    discharge_mw: float,
    duration_hours: float = 1.0,
    config: BatteryConfig | None = None,
) -> dict:
    if config is None:
        config = BatteryConfig()

    validate_battery_config(config)

    if not 0 <= soc_pct <= 100:
        raise ValueError("SoC must be between 0 and 100.")

    if duration_hours <= 0:
        raise ValueError("Duration must be positive.")

    if charge_mw < 0 or discharge_mw < 0:
        raise ValueError("Charging and discharging power cannot be negative.")

    if charge_mw > 0 and discharge_mw > 0:
        raise ValueError(
            "Simultaneous charging and discharging are prohibited."
        )

    if charge_mw > config.max_charge_mw:
        raise ValueError("Charging power exceeds the configured limit.")

    if discharge_mw > config.max_discharge_mw:
        raise ValueError("Discharging power exceeds the configured limit.")

    current_energy = config.capacity_mwh * soc_pct / 100

    next_energy = (
        current_energy
        + charge_mw * duration_hours * config.charge_efficiency
        - discharge_mw * duration_hours / config.discharge_efficiency
    )

    min_energy = config.capacity_mwh * config.min_soc_pct / 100
    max_energy = config.capacity_mwh * config.max_soc_pct / 100

    if next_energy < min_energy - 1e-9:
        raise ValueError("Action would violate minimum battery SoC.")

    if next_energy > max_energy + 1e-9:
        raise ValueError("Action would violate maximum battery SoC.")

    next_soc = next_energy / config.capacity_mwh * 100

    return {
        "valid": True,
        "charge_mw": charge_mw,
        "discharge_mw": discharge_mw,
        "duration_hours": duration_hours,
        "current_energy_mwh": round(current_energy, 4),
        "next_energy_mwh": round(next_energy, 4),
        "next_soc_pct": round(next_soc, 2),
    }