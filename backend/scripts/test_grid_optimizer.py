import json

from app.services.grid_optimizer import (
    GridConfig,
    optimize_battery_schedule,
)


def main():
    print("Testing grid optimizer...")

    config = GridConfig(
        initial_soc_pct=45,
        terminal_soc_pct=45,
    )

    result = optimize_battery_schedule(
        generation_forecast_mw=[10.3, 6.8, 6.8],
        demand_forecast_mw=[8.4, 9.2, 9.2],
        config=config,
    )

    print(json.dumps(result, indent=2))

    assert result["feasible"], "Optimizer did not find a feasible schedule."

    for step in result["schedule"]:
        assert step["charge_mw"] <= 2.0 + 1e-6
        assert step["discharge_mw"] <= 2.0 + 1e-6
        assert step["balance_error_mw"] < 1e-5

    print("\nAll grid optimizer checks passed.")


if __name__ == "__main__":
    main()