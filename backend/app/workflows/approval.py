from typing import Any

from langgraph.types import interrupt


def human_approval_node(
    state: dict[str, Any],
) -> dict[str, Any]:
    """Pause for human approval of a grid recommendation."""

    review_result = state.get("review_result", {})

    if review_result.get("status") != "ready_for_human_review":
        return {
            "approval_required": False,
            "human_approved": False,
            "approval_status": "blocked",
            "workflow_status": "blocked",
            "execution_trace": ["human_approval:blocked"],
        }

    decision = interrupt({
        "type": "human_approval_required",
        "message": (
            "Review the grid recommendation. "
            "Approve it or reject it with feedback for replanning."
        ),
        "grid_optimization": state.get("grid_optimization", {}),
        "review_result": review_result,
        "warnings": review_result.get("warnings", []),
        "allowed_decisions": ["approve", "reject"],
        "rejection_feedback_required": True,
    })

    if not isinstance(decision, dict):
        decision = {"decision": "reject"}

    choice = str(
        decision.get("decision", "reject")
    ).strip().lower()

    feedback = str(
        decision.get("feedback", "")
    ).strip()

    if choice == "approve":
        approved = True
        status = "approved"
        trace = "human_approval:approved"
        message = "Recommendation approved for the application's next stage."

        # Only mark the workflow completed when approving a revised plan
        # or an initial plan. The graph will end after this approval.
        workflow_status = "completed"

    elif choice == "reject":
        approved = False
        status = "rejected"
        trace = "human_approval:rejected"
        workflow_status = "replanning_requested"

        if not feedback:
            feedback = "No specific feedback provided."

        message = (
            "Recommendation rejected. "
            "The workflow must use the feedback to revise the plan."
        )

    else:
        approved = False
        status = "invalid_decision"
        trace = "human_approval:invalid_decision"
        workflow_status = "approval_required"
        message = (
            "Invalid decision. The recommendation remains unapproved."
        )

    return {
        "approval_required": status != "approved",
        "human_approved": approved,
        "approval_status": status,
        "workflow_status": workflow_status,
        "rejection_feedback": (
            feedback if choice == "reject" else ""
        ),
        "review_result": {
            **review_result,
            "human_decision": choice,
            "decision_message": message,
            "rejection_feedback": (
                feedback if choice == "reject" else None
            ),
        },
        "execution_trace": [trace],
    }