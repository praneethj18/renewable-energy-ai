from typing import Any


def effective_workflow_status(
    status: str | None,
    approval_status: str | None,
    state: dict[str, Any] | None,
    *,
    waiting_for_human: bool | None = None,
) -> str:
    """Resolve persisted/current workflow status without inventing decisions."""
    snapshot = state or {}
    trace = snapshot.get("execution_trace", [])
    paused_at_review = (
        waiting_for_human is True
        or snapshot.get("waiting_for_human") is True
        or (
            approval_status == "pending"
            and isinstance(trace, list)
            and any(str(event).endswith("ready_for_human_review") for event in trace)
        )
    )
    if paused_at_review and (status in {None, "", "running"}):
        return "awaiting_human_review"
    return status or "unknown"
