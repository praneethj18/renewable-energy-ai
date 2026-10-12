from app.services.battery_management import (
    calculate_battery_limits,
    validate_battery_action,
)

def main():
    print("Testing battery management...")

    limits = calculate_battery_limits(soc_pct=45)

    print("\nBattery limits at 45% SoC:")
    for key, value in limits.items():
        print(f"{key}: {value}")

    action = validate_battery_action(
        soc_pct=45,
        charge_mw=1.9,
        discharge_mw=0,
        duration_hours=1,
    )

    print("\nValid charging action:")
    print(action)

    try:
        validate_battery_action(
            soc_pct=45,
            charge_mw=3,
            discharge_mw=0,
        )
    except ValueError as error:
        print("\nExpected rejection of invalid action:")
        print(error)
    else:
        raise AssertionError("Invalid charging action was accepted.")

    try:
        validate_battery_action(
            soc_pct=45,
            charge_mw=1,
            discharge_mw=1,
        )
    except ValueError as error:
        print("\nExpected rejection of simultaneous charging/discharging:")
        print(error)
    else:
        raise AssertionError(
            "Simultaneous charging/discharging was accepted."
        )

    print("\nAll battery management checks passed.")


if __name__ == "__main__":
    main()