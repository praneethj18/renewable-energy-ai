from typing import Any

from app.services.battery_management import (
    BatteryConfig,
    calculate_battery_limits,
    validate_battery_action,
)


def battery_management_node(
    state: dict[str, Any],
) -> dict[str, Any]:
    """Analyze battery capacity, SoC, and operational constraints."""

    try:
        config_values = {
            "capacity_mwh": state.get("battery_capacity_mwh"),
            "max_charge_mw": state.get("max_charge_mw"),
            "max_discharge_mw": state.get("max_discharge_mw"),
            "min_soc_pct": state.get("min_soc_pct"),
            "max_soc_pct": state.get("max_soc_pct"),
            "charge_efficiency": state.get("charge_efficiency"),
            "discharge_efficiency": state.get("discharge_efficiency"),
        }
        defaults = BatteryConfig()
        config = BatteryConfig(**{
            field: getattr(defaults, field) if value is None else float(value)
            for field, value in config_values.items()
        })
        if state.get("battery_is_available") is False:
            config.max_charge_mw = 0.0
            config.max_discharge_mw = 0.0

        soc_pct = float(state.get("initial_soc_pct", 45.0))

        limits = calculate_battery_limits(
            soc_pct=soc_pct,
            config=config,
        )

        generation = state.get("generation_forecast_mw", [])
        demand = state.get("demand_forecast_mw", [])

        # Estimate the battery action required for the first forecast period.
        # This is a validation estimate, not an instruction to operate hardware.
        recommended_charge_mw = 0.0
        recommended_discharge_mw = 0.0

        if generation and demand:
            surplus_mw = float(generation[0]) - float(demand[0])

            if surplus_mw > 0:
                recommended_charge_mw = min(
                    surplus_mw,
                    config.max_charge_mw,
                )
            elif surplus_mw < 0:
                recommended_discharge_mw = min(
                    abs(surplus_mw),
                    config.max_discharge_mw,
                )

        try:
            action_check = validate_battery_action(
                soc_pct=soc_pct,
                charge_mw=recommended_charge_mw,
                discharge_mw=recommended_discharge_mw,
                duration_hours=float(
                    state.get("timestep_hours", 1.0)
                ),
                config=config,
            )

            action_status = "valid"
            action_message = (
                "Estimated battery action satisfies configured constraints."
            )

        except ValueError as exc:
            action_check = {
                "valid": False,
                "message": str(exc),
            }

            action_status = "invalid"
            action_message = str(exc)

        battery_status = {
            "status": (
                "ready"
                if action_status == "valid" and state.get("battery_is_available") is not False
                else "unavailable"
                if state.get("battery_is_available") is False
                else "attention_required"
            ),
            "limits": limits,
            "action_check": action_check,
            "action_status": action_status,
            "action_message": action_message,
            "recommendation_only": True,
            "is_available": state.get("battery_is_available") is not False,
            "state_source": "configured SoC; no battery telemetry is connected",
        }

        return {
            "battery_status": battery_status,
            "agent_results": {
                "battery_management": {
                    "status": battery_status["status"],
                    "soc_pct": soc_pct,
                    "capacity_mwh": config.capacity_mwh,
                    "max_charge_mw": config.max_charge_mw,
                    "max_discharge_mw": config.max_discharge_mw,
                    "action_status": action_status,
                }
            },
            "execution_trace": [
                f"battery_management:{battery_status['status']}"
            ],
        }

    except Exception as exc:
        return {
            "battery_status": {
                "status": "error",
                "message": str(exc),
            },
            "agent_results": {
                "battery_management": {
                    "status": "error",
                    "message": str(exc),
                }
            },
            "execution_trace": [
                "battery_management:error"
            ],
            "errors": [
                f"Battery management failed: {exc}"
            ],
        }
