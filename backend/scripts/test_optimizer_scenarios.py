from backend.app.services.grid_optimizer import (
    GridConfig,
    optimize_battery_schedule,
)


def run_test(name, generation, demand, config=None):
    print(f"\n--- {name} ---")

    result = optimize_battery_schedule(
        generation_forecast_mw=generation,
        demand_forecast_mw=demand,
        config=config,
    )

    print("Status:", result["status"])
    print("Feasible:", result["feasible"])

    if result["feasible"]:
        for step in result["schedule"]:
            print(
                f"Hour {step['timestep']}: "
                f"Generation={step['generation_mw']} MW, "
                f"Demand={step['demand_mw']} MW, "
                f"Charge={step['charge_mw']} MW, "
                f"Discharge={step['discharge_mw']} MW, "
                f"Import={step['grid_import_mw']} MW, "
                f"Export={step['grid_export_mw']} MW, "
                f"SoC={step['battery_soc_pct']}%"
            )

    return result


def main():
    config = GridConfig(
        initial_soc_pct=45,
        terminal_soc_pct=45,
    )

    # Scenario 1: Generation meets demand.
    normal = run_test(
        "Normal generation",
        [8.0, 8.5],
        [7.0, 7.5],
        config,
    )
    assert normal["feasible"]

    # Scenario 2: Surplus generation.
    surplus = run_test(
        "Surplus generation",
        [10.3],
        [8.4],
        config,
    )
    assert surplus["feasible"]

    # Scenario 3: Deficit.
    deficit = run_test(
        "Generation deficit",
        [6.8],
        [9.2],
        config,
    )
    assert deficit["feasible"]

    # Scenario 4: Surplus followed by a deficit.
    # The optimizer can store energy in the first period and use it later.
    shifting = run_test(
        "Surplus followed by deficit",
        [10.0, 6.0],
        [8.0, 9.0],
        config,
    )
    assert shifting["feasible"]

    schedule = shifting["schedule"]

    assert schedule[0]["charge_mw"] > 0, (
        "Expected the battery to charge during the surplus period."
    )

    assert schedule[1]["discharge_mw"] > 0, (
        "Expected the battery to discharge during the deficit period."
    )

    # Scenario 5: Charging power must remain within the limit.
    charging = run_test(
        "Charging power limit",
        [12.0, 12.0],
        [5.0, 5.0],
        config,
    )
    assert charging["feasible"]

    for step in charging["schedule"]:
        assert step["charge_mw"] <= config.max_charge_mw + 1e-6
        assert step["discharge_mw"] <= config.max_discharge_mw + 1e-6

    print("\nAll optimizer scenario checks passed.")


if __name__ == "__main__":
    main()