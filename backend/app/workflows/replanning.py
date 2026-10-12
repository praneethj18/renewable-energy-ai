from typing import Any


def replanning_node(state: dict[str, Any]) -> dict[str, Any]:
    """Prepare revised optimization inputs using human rejection feedback."""

    feedback = state.get("rejection_feedback", "").strip()
    attempts = state.get("replan_attempts", 0)
    max_attempts = state.get("max_replan_attempts", 2)

    if attempts >= max_attempts:
        return {
            "replan_status": "blocked",
            "workflow_status": "replanning_limit_reached",
            "execution_trace": ["replanning:limit_reached"],
            "errors": [
                "Maximum replanning attempts reached. Human intervention is required."
            ],
        }

    if not feedback:
        return {
            "replan_status": "blocked",
            "workflow_status": "replanning_blocked",
            "execution_trace": ["replanning:missing_feedback"],
            "errors": [
                "Replanning requires specific human feedback."
            ],
        }

    feedback_lower = feedback.lower()

    # Start with the existing optimization inputs.
    initial_soc = float(state.get("initial_soc_pct", 45.0))
    terminal_soc = float(state.get("terminal_soc_pct", 45.0))

    # Apply only explicit, recognizable feedback.
    if "preserve more battery" in feedback_lower or "increase terminal soc" in feedback_lower:
        terminal_soc = min(90.0, terminal_soc + 10.0)

    elif "use more battery" in feedback_lower or "reduce terminal soc" in feedback_lower:
        terminal_soc = max(10.0, terminal_soc - 10.0)

    else:
        return {
            "replan_status": "blocked",
            "workflow_status": "replanning_blocked",
            "execution_trace": ["replanning:feedback_not_actionable"],
            "errors": [
                "Feedback could not be mapped to a supported optimization change. "
                "Please provide specific battery SoC guidance."
            ],
        }

    return {
        "initial_soc_pct": initial_soc,
        "terminal_soc_pct": terminal_soc,
        "replan_attempts": attempts + 1,
        "plan_version": int(state.get("plan_version", 1)) + 1,
        "replan_status": "ready",
        "workflow_status": "replanning_in_progress",
        "execution_trace": ["replanning:inputs_updated"],
    }
