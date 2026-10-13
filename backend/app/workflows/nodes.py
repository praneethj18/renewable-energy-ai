from datetime import datetime, timezone
from typing import Any

from app.services.grid_optimizer import (
    GridConfig,
    optimize_battery_schedule,
)
from app.services.weather import get_weather


def weather_intelligence_node(
    state: dict[str, Any],
) -> dict[str, Any]:
    """Fetch real weather data for the requested location."""

    latitude = state.get("latitude")
    longitude = state.get("longitude")

    if latitude is None or longitude is None:
        return {
            "errors": [
                "Weather agent requires latitude and longitude."
            ],
            "agent_results": {
                "weather_intelligence": {
                    "status": "needs_input",
                    "message": "Provide latitude and longitude.",
                }
            },
            "execution_trace": [
                "weather_intelligence:needs_input"
            ],
        }

    try:
        weather_result = get_weather(
            latitude=float(latitude),
            longitude=float(longitude),
        )

        hourly_forecast = weather_result.get(
            "hourly_forecast", []
        )

        return {
            "weather_data": weather_result,
            "agent_results": {
                "weather_intelligence": {
                    "status": "success",
                    "records_received": len(hourly_forecast),
                    "source": weather_result.get(
                        "source", "Unknown"
                    ),
                    "current_conditions": weather_result.get(
                        "current", {}
                    ),
                }
            },
            "execution_trace": [
                "weather_intelligence:success"
            ],
        }

    except Exception as exc:
        return {
            "errors": [
                f"Weather agent failed: {exc}"
            ],
            "agent_results": {
                "weather_intelligence": {
                    "status": "error",
                    "message": str(exc),
                }
            },
            "execution_trace": [
                "weather_intelligence:error"
            ],
        }


def grid_coordination_node(
    state: dict[str, Any],
) -> dict[str, Any]:
    """
    Optimize battery scheduling using aligned forecasts.

    Validates timestamps, executes the grid optimizer, and attaches
    the corresponding UTC timestamp to every schedule entry.

    The generated schedule is a recommendation, not a physical
    grid-control command.
    """

    generation = state.get("generation_forecast_mw")
    demand = state.get("demand_forecast_mw")

    generation_timestamps = state.get(
        "generation_forecast_timestamps"
    )
    demand_timestamps = state.get(
        "demand_forecast_timestamps"
    )

    attempt = int(state.get("replan_attempts", 0))

    # 1. Validate the forecast arrays.
    if (
        not isinstance(generation, list)
        or not isinstance(demand, list)
        or not generation
        or not demand
    ):
        message = (
            "Grid coordination requires non-empty generation "
            "and demand forecast lists."
        )

        return {
            "errors": [message],
            "agent_results": {
                "grid_coordination": {
                    "status": "needs_input",
                    "message": message,
                }
            },
            "execution_trace": [
                "grid_coordination:needs_input"
            ],
        }

    # 2. Validate that the forecast lengths match.
    if len(generation) != len(demand):
        message = (
            "Generation and demand forecast lengths do not match: "
            f"{len(generation)} versus {len(demand)}."
        )

        return {
            "errors": [message],
            "agent_results": {
                "grid_coordination": {
                    "status": "error",
                    "message": message,
                }
            },
            "execution_trace": [
                "grid_coordination:error"
            ],
        }

    # 3. Validate timestamp availability and array lengths.
    if (
        not isinstance(generation_timestamps, list)
        or not isinstance(demand_timestamps, list)
        or len(generation_timestamps) != len(generation)
        or len(demand_timestamps) != len(demand)
    ):
        message = (
            "Forecast timestamps are missing or their lengths "
            "do not match the forecast arrays."
        )

        return {
            "errors": [message],
            "agent_results": {
                "grid_coordination": {
                    "status": "error",
                    "message": message,
                }
            },
            "execution_trace": [
                "grid_coordination:error"
            ],
        }

    # 4. Both agents must forecast the same timestamps.
    if generation_timestamps != demand_timestamps:
        message = (
            "Generation and demand forecast timestamps "
            "are not aligned."
        )

        return {
            "errors": [message],
            "agent_results": {
                "grid_coordination": {
                    "status": "error",
                    "message": message,
                }
            },
            "execution_trace": [
                "grid_coordination:error"
            ],
        }

    # 5. Validate timestamp format, timezone, and continuity.
    try:
        parsed_timestamps = []

        for value in generation_timestamps:
            if not isinstance(value, str):
                raise ValueError(
                    "Forecast timestamps must be ISO-formatted strings."
                )

            timestamp = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )

            if (
                timestamp.tzinfo is None
                or timestamp.utcoffset() is None
            ):
                raise ValueError(
                    f"Timestamp must include a timezone: {value}"
                )

            parsed_timestamps.append(
                timestamp.astimezone(timezone.utc)
            )

        timestep_hours = float(
            state.get("timestep_hours", 1.0)
        )

        if (
            not timestep_hours > 0
            or not timestep_hours < float("inf")
        ):
            raise ValueError(
                "timestep_hours must be a finite positive number."
            )

        for index in range(1, len(parsed_timestamps)):
            elapsed_hours = (
                parsed_timestamps[index]
                - parsed_timestamps[index - 1]
            ).total_seconds() / 3600

            if abs(elapsed_hours - timestep_hours) > 1e-6:
                raise ValueError(
                    "Forecast timestamps are not continuous at "
                    f"the configured timestep. Problem at index {index}."
                )

    except (TypeError, ValueError, OverflowError) as exc:
        message = (
            f"Forecast timestamp validation failed: {exc}"
        )

        return {
            "errors": [message],
            "agent_results": {
                "grid_coordination": {
                    "status": "error",
                    "message": message,
                }
            },
            "execution_trace": [
                "grid_coordination:error"
            ],
        }

    # 6. Validate the requested battery constraints and optimize.
    try:
        def configured_float(key: str, default: float) -> float:
            value = state.get(key)
            return default if value is None else float(value)

        battery_available = state.get("battery_is_available") is not False
        config = GridConfig(
            battery_capacity_mwh=configured_float("battery_capacity_mwh", 8.0),
            max_charge_mw=(
                configured_float("max_charge_mw", 2.0) if battery_available else 0.0
            ),
            max_discharge_mw=(
                configured_float("max_discharge_mw", 2.0) if battery_available else 0.0
            ),
            min_soc_pct=configured_float("min_soc_pct", 10.0),
            max_soc_pct=configured_float("max_soc_pct", 90.0),
            charge_efficiency=configured_float("charge_efficiency", 0.95),
            discharge_efficiency=configured_float("discharge_efficiency", 0.95),
            initial_soc_pct=float(
                state.get("initial_soc_pct", 45.0)
            ),
            terminal_soc_pct=float(
                state.get("terminal_soc_pct", 45.0)
            ),
        )

        result = optimize_battery_schedule(
            generation_forecast_mw=generation,
            demand_forecast_mw=demand,
            config=config,
            timestep_hours=timestep_hours,
        )

        schedule = result.get("schedule")

        if not isinstance(schedule, list):
            raise ValueError(
                "Optimizer did not return a valid schedule list."
            )

        if len(schedule) != len(parsed_timestamps):
            raise ValueError(
                "Optimizer schedule length does not match "
                "the forecast horizon."
            )

        # 7. Attach the correct UTC timestamp to every schedule row.
        for entry, timestamp in zip(
            schedule,
            parsed_timestamps,
        ):
            entry["timestamp_utc"] = (
                timestamp.isoformat().replace("+00:00", "Z")
            )

        feasible = result.get("feasible", False)

        # 8. Record optimization settings and forecast metadata.
        result["optimization_attempt"] = attempt

        result["constraints_used"] = {
            "battery_capacity_mwh": config.battery_capacity_mwh,
            "max_charge_mw": config.max_charge_mw,
            "max_discharge_mw": config.max_discharge_mw,
            "min_soc_pct": config.min_soc_pct,
            "max_soc_pct": config.max_soc_pct,
            "charge_efficiency": config.charge_efficiency,
            "discharge_efficiency": config.discharge_efficiency,
            "initial_soc_pct": config.initial_soc_pct,
            "terminal_soc_pct": config.terminal_soc_pct,
            "timestep_hours": timestep_hours,
}

        result["forecast_metadata"] = {
            "forecast_count": len(parsed_timestamps),
            "forecast_start_utc": (
                parsed_timestamps[0]
                .isoformat()
                .replace("+00:00", "Z")
            ),
            "forecast_end_utc": (
                parsed_timestamps[-1]
                .isoformat()
                .replace("+00:00", "Z")
            ),
            "timestamps_aligned": True,
            "timestep_hours": timestep_hours,
        }

        status = "success" if feasible else "infeasible"

        message = (
            "Grid optimization completed successfully."
            if feasible
            else (
                "Grid optimization did not produce "
                "a feasible schedule."
            )
        )

        return {
            "grid_optimization": result,
            "agent_results": {
                "grid_coordination": {
                    "status": status,
                    "message": message,
                    "optimization_attempt": attempt,
                    "forecast_count": len(parsed_timestamps),
                    "timestamps_aligned": True,
                    "feasible": feasible,
                }
            },
            "execution_trace": [
                f"grid_coordination:{status}"
            ],
        }

    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception(
            "Grid coordination failed with an unexpected exception"
        )
        message = f"Grid coordination failed: {exc}"

        return {
            "errors": [message],
            "agent_results": {
                "grid_coordination": {
                    "status": "error",
                    "message": message,
                }
            },
            "execution_trace": [
                "grid_coordination:error"
            ],
        }
