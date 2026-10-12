from dataclasses import dataclass

import pulp


@dataclass
class GridConfig:
    battery_capacity_mwh: float = 8.0
    max_charge_mw: float = 2.0
    max_discharge_mw: float = 2.0
    min_soc_pct: float = 10.0
    max_soc_pct: float = 90.0
    charge_efficiency: float = 0.95
    discharge_efficiency: float = 0.95
    initial_soc_pct: float = 45.0
    terminal_soc_pct: float = 45.0


def optimize_battery_schedule(
    generation_forecast_mw: list[float],
    demand_forecast_mw: list[float],
    config: GridConfig | None = None,
    timestep_hours: float = 1.0,
) -> dict:
    """
    Optimize battery charging, discharging, grid imports, and exports.

    This is a scheduling recommendation only. It does not control
    physical equipment.
    """
    if config is None:
        config = GridConfig()

    if not generation_forecast_mw:
        raise ValueError("Forecast must contain at least one timestep.")

    if len(generation_forecast_mw) != len(demand_forecast_mw):
        raise ValueError("Generation and demand forecast lengths must match.")

    if timestep_hours <= 0:
        raise ValueError("Timestep duration must be positive.")

    if config.battery_capacity_mwh <= 0:
        raise ValueError("Battery capacity must be positive.")

    if config.max_charge_mw < 0 or config.max_discharge_mw < 0:
        raise ValueError("Battery power limits cannot be negative.")

    if not 0 <= config.min_soc_pct < config.max_soc_pct <= 100:
        raise ValueError("Invalid battery SoC limits.")

    if not config.min_soc_pct <= config.initial_soc_pct <= config.max_soc_pct:
        raise ValueError("Initial SoC is outside configured limits.")

    if not config.min_soc_pct <= config.terminal_soc_pct <= config.max_soc_pct:
        raise ValueError("Terminal SoC is outside configured limits.")

    if not 0 < config.charge_efficiency <= 1:
        raise ValueError("Invalid charging efficiency.")

    if not 0 < config.discharge_efficiency <= 1:
        raise ValueError("Invalid discharging efficiency.")

    for value in generation_forecast_mw + demand_forecast_mw:
        if value < 0:
            raise ValueError("Forecast values cannot be negative.")

    count = len(generation_forecast_mw)

    model = pulp.LpProblem(
        "Renewable_Energy_Grid_Coordination",
        pulp.LpMinimize,
    )

    # Battery charging and discharging power in MW.
    charge = [
        pulp.LpVariable(
            f"charge_{t}",
            lowBound=0,
            upBound=config.max_charge_mw,
        )
        for t in range(count)
    ]

    discharge = [
        pulp.LpVariable(
            f"discharge_{t}",
            lowBound=0,
            upBound=config.max_discharge_mw,
        )
        for t in range(count)
    ]

    # Binary mode: 1 means charging is permitted; 0 means discharging
    # is permitted. This prevents simultaneous operation.
    battery_mode = [
        pulp.LpVariable(f"battery_mode_{t}", cat="Binary")
        for t in range(count)
    ]

    grid_import = [
        pulp.LpVariable(f"grid_import_{t}", lowBound=0)
        for t in range(count)
    ]

    grid_export = [
        pulp.LpVariable(f"grid_export_{t}", lowBound=0)
        for t in range(count)
    ]

    export_mode = [
        pulp.LpVariable(f"export_mode_{t}", cat="Binary")
        for t in range(count)
    ]

    curtailed = [
        pulp.LpVariable(f"curtailed_{t}", lowBound=0)
        for t in range(count)
    ]

    unmet_demand = [
        pulp.LpVariable(f"unmet_demand_{t}", lowBound=0)
        for t in range(count)
    ]

    min_energy = (
        config.battery_capacity_mwh * config.min_soc_pct / 100
    )

    max_energy = (
        config.battery_capacity_mwh * config.max_soc_pct / 100
    )

    initial_energy = (
        config.battery_capacity_mwh * config.initial_soc_pct / 100
    )

    terminal_energy = (
        config.battery_capacity_mwh * config.terminal_soc_pct / 100
    )

    energy = [
        pulp.LpVariable(
            f"battery_energy_{t}",
            lowBound=min_energy,
            upBound=max_energy,
        )
        for t in range(count + 1)
    ]

    model += energy[0] == initial_energy
    model += energy[count] == terminal_energy

    for t in range(count):
        # Battery operating limits.
        model += charge[t] <= (
            config.max_charge_mw * battery_mode[t]
        )

        model += discharge[t] <= (
            config.max_discharge_mw * (1 - battery_mode[t])
        )

        # Prevent simultaneous grid import and export.
        # The bound is based on the forecast scale, not an arbitrary
        # excessively large constant.
        maximum_flow = (
            generation_forecast_mw[t]
            + demand_forecast_mw[t]
            + config.max_charge_mw
            + config.max_discharge_mw
        )

        model += grid_import[t] <= maximum_flow * (1 - export_mode[t])
        model += grid_export[t] <= maximum_flow * export_mode[t]

        # Battery energy transition with charging/discharging efficiency.
        model += energy[t + 1] == (
            energy[t]
            + config.charge_efficiency * charge[t] * timestep_hours
            - discharge[t] * timestep_hours / config.discharge_efficiency
        )

        # Generation balance.
        model += (
            generation_forecast_mw[t]
            + discharge[t]
            + grid_import[t]
            + unmet_demand[t]
            == demand_forecast_mw[t]
            + charge[t]
            + grid_export[t]
            + curtailed[t]
        )

        # Renewable curtailment cannot exceed available generation.
        model += curtailed[t] <= generation_forecast_mw[t]

    # Objective:
    # 1. Avoid unmet demand.
    # 2. Reduce grid imports.
    # 3. Prefer using surplus generation for charging over curtailment.
    # 4. Avoid unnecessary battery cycling and grid exports.
    model += pulp.lpSum(
        100000 * unmet_demand[t] * timestep_hours
        + 1000 * grid_import[t] * timestep_hours
        + 100 * curtailed[t] * timestep_hours
        + 0.1 * grid_export[t] * timestep_hours
        + 0.01 * (charge[t] + discharge[t]) * timestep_hours
        for t in range(count)
    )

    solver = pulp.PULP_CBC_CMD(msg=False)
    model.solve(solver)

    status = pulp.LpStatus[model.status]

    if status != "Optimal":
        return {
            "status": status,
            "feasible": False,
            "message": "No optimal schedule was found.",
        }

    schedule = []
    independently_validated_energy = initial_energy

    for t in range(count):
        charge_mw = float(pulp.value(charge[t]) or 0)
        discharge_mw = float(pulp.value(discharge[t]) or 0)
        import_mw = float(pulp.value(grid_import[t]) or 0)
        export_mw = float(pulp.value(grid_export[t]) or 0)
        curtailed_mw = float(pulp.value(curtailed[t]) or 0)
        unmet_mw = float(pulp.value(unmet_demand[t]) or 0)

        # Independently recalculate battery energy.
        independently_validated_energy += (
            config.charge_efficiency * charge_mw * timestep_hours
            - discharge_mw * timestep_hours / config.discharge_efficiency
        )

        optimized_energy = float(pulp.value(energy[t + 1]))

        if abs(independently_validated_energy - optimized_energy) > 1e-5:
            raise RuntimeError("Battery energy validation failed.")

        if not (
            min_energy - 1e-6
            <= independently_validated_energy
            <= max_energy + 1e-6
        ):
            raise RuntimeError("Battery SoC limits were violated.")

        if charge_mw > 1e-6 and discharge_mw > 1e-6:
            raise RuntimeError("Simultaneous charging/discharging detected.")

        if import_mw > 1e-6 and export_mw > 1e-6:
            raise RuntimeError("Simultaneous grid import/export detected.")

        balance_error = (
            generation_forecast_mw[t]
            + discharge_mw
            + import_mw
            + unmet_mw
            - demand_forecast_mw[t]
            - charge_mw
            - export_mw
            - curtailed_mw
        )

        if abs(balance_error) > 1e-5:
            raise RuntimeError("Energy balance validation failed.")

        schedule.append({
            "timestep": t,
            "generation_mw": generation_forecast_mw[t],
            "demand_mw": demand_forecast_mw[t],
            "balance_before_battery_mw": (
                generation_forecast_mw[t] - demand_forecast_mw[t]
            ),
            "charge_mw": round(charge_mw, 4),
            "discharge_mw": round(discharge_mw, 4),
            "charge_efficiency_loss_mwh": round(
                charge_mw * timestep_hours * (1 - config.charge_efficiency), 4
            ),
            "discharge_efficiency_loss_mwh": round(
                discharge_mw * timestep_hours * (1 / config.discharge_efficiency - 1), 4
            ),
            "grid_import_mw": round(import_mw, 4),
            "grid_export_mw": round(export_mw, 4),
            "curtailed_generation_mw": round(curtailed_mw, 4),
            "unmet_demand_mw": round(unmet_mw, 4),
            "battery_energy_mwh": round(
                independently_validated_energy, 4
            ),
            "battery_soc_pct": round(
                independently_validated_energy
                / config.battery_capacity_mwh * 100,
                2,
            ),
            "balance_error_mw": round(balance_error, 8),
        })

    return {
        "status": status,
        "feasible": True,
        "objective_value": round(float(pulp.value(model.objective)), 4),
        "objective_description": (
            "Prioritize unmet-demand reduction, then grid-import reduction, "
            "renewable-curtailment reduction, and lower cycling."
        ),
        "timestep_hours": timestep_hours,
        "total_grid_import_mwh": round(
            sum(float(pulp.value(grid_import[t]) or 0) * timestep_hours for t in range(count)),
            4,
        ),
        "total_grid_export_mwh": round(
            sum(float(pulp.value(grid_export[t]) or 0) * timestep_hours for t in range(count)),
            4,
        ),
        "total_unmet_demand_mwh": round(
            sum(float(pulp.value(unmet_demand[t]) or 0) * timestep_hours for t in range(count)),
            4,
        ),
        "total_curtailed_generation_mwh": round(
            sum(float(pulp.value(curtailed[t]) or 0) * timestep_hours for t in range(count)),
            4,
        ),
        "total_efficiency_loss_mwh": round(
            sum(
                float(pulp.value(charge[t]) or 0) * timestep_hours * (1 - config.charge_efficiency)
                + float(pulp.value(discharge[t]) or 0) * timestep_hours * (1 / config.discharge_efficiency - 1)
                for t in range(count)
            ),
            4,
        ),
        "battery_capacity_mwh": config.battery_capacity_mwh,
        "initial_soc_pct": config.initial_soc_pct,
        "terminal_soc_pct": config.terminal_soc_pct,
        "schedule": schedule,
        "message": (
            "Schedule passed independent battery and energy-balance checks. "
            "This is a recommendation, not a physical control command."
        ),
    }
