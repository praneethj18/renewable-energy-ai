from typing import Any


def reviewer_node(
    state: dict[str, Any],
) -> dict[str, Any]:
    """Review forecasting, anomaly, battery, and grid results."""

    issues = []
    warnings = []

    # Check generation forecast
    generation = state.get("generation_forecast_mw")

    if not generation:
        issues.append("Generation forecast is missing.")

    # Check demand forecast
    demand = state.get("demand_forecast_mw")

    if not demand:
        issues.append("Demand forecast is missing.")

    # Check grid optimization
    optimization = state.get("grid_optimization", {})

    if not optimization.get("feasible", False):
        issues.append(
            "Grid optimization did not produce a feasible schedule."
        )

    # Review detected anomalies
    anomalies = state.get("anomalies", [])

    if anomalies:
        warnings.append(
            f"{len(anomalies)} anomaly or warning(s) require review."
        )

    performance = state.get("performance_analysis", {})
    measurement_comparison = performance.get("measurement_comparison", {})
    if measurement_comparison.get("status") != "available":
        warnings.append(
            "Actual-versus-forecast generation screening was not completed: "
            + str(measurement_comparison.get("message") or measurement_comparison.get("status", "unavailable"))
        )

    # Review battery validation
    battery_status = state.get("battery_status", {})

    if battery_status.get("status") not in {"ready", "unavailable"}:
        issues.append(
            "Battery management did not report a ready status."
        )
    elif battery_status.get("status") == "unavailable":
        warnings.append(
            "Battery is unavailable; the schedule must rely on grid exchange and show any remaining deficit."
        )

    # Check forecasting provenance warnings
    agent_results = state.get("agent_results", {})

    for agent_name in (
        "generation_forecasting",
        "demand_forecasting",
    ):
        agent_result = agent_results.get(agent_name, {})

        warning = agent_result.get("warning")

        if warning:
            warnings.append(
                f"{agent_name}: {warning}"
            )

    approved_for_review = len(issues) == 0

    review_result = {
        "status": (
            "ready_for_human_review"
            if approved_for_review
            else "rejected"
        ),
        "checks_passed": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "human_approval_required": approved_for_review,
        "reviewer_note": (
            "This is an automated review, not authorization to "
            "operate physical grid equipment."
        ),
    }

    return {
        "review_result": review_result,
        "approval_required": approved_for_review,
        "human_approved": False,
        "approval_status": (
            "pending" if approved_for_review else "blocked"
        ),
        "agent_results": {
            "reviewer": {
                "status": review_result["status"],
                "issue_count": len(issues),
                "warning_count": len(warnings),
            }
        },
        "execution_trace": [
            f"reviewer:{review_result['status']}"
        ],
    }
