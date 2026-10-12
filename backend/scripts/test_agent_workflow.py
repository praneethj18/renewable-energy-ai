import json
from langgraph.types import Command

from app.workflows.graph import renewable_energy_workflow


def start_workflow(thread_id: str):
    """Start the workflow and pause at the first human approval."""

    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "latitude": 17.385,
        "longitude": 78.4867,
        "initial_soc_pct": 45.0,
        "terminal_soc_pct": 45.0,
        "timestep_hours": 1.0,
        "replan_attempts": 0,
        "max_replan_attempts": 2,
        "agent_results": {},
        "execution_trace": [],
        "errors": [],
    }

    renewable_energy_workflow.invoke(initial_state, config=config)

    return config


def resume_workflow(config, decision: str, feedback: str = ""):
    """Resume the workflow with a human decision."""

    response = {"decision": decision}

    if feedback:
        response["feedback"] = feedback

    return renewable_energy_workflow.invoke(
        Command(resume=response),
        config=config,
    )


def test_approval_only():
    print("\n" + "=" * 55)
    print("TEST 1: APPROVE ORIGINAL RECOMMENDATION")
    print("=" * 55)

    config = start_workflow("approval-only-test-001")

    result = resume_workflow(config, "approve")

    print("Approval status:", result.get("approval_status"))
    print("Human approved:", result.get("human_approved"))

    print("\nFULL WORKFLOW RESULT:")
    print(json.dumps(result, indent=2, default=str))

    assert result.get("approval_status") == "approved"
    assert result.get("human_approved") is True

    print("PASS: Original recommendation approved.")


def test_rejection_replanning_and_second_approval():
    print("\n" + "=" * 55)
    print("TEST 2: REJECTION -> REPLANNING -> SECOND APPROVAL")
    print("=" * 55)

    config = start_workflow("replanning-cycle-test-001")

    # Step 1: Reject the original recommendation with feedback.
    first_result = resume_workflow(
        config,
        "reject",
        "Preserve more battery charge by increasing terminal SoC.",
    )

    print("\nAfter rejection and replanning:")
    print("Approval status:", first_result.get("approval_status"))
    print("Replan status:", first_result.get("replan_status"))
    print("Replan attempts:", first_result.get("replan_attempts"))
    print("Terminal SoC:", first_result.get("terminal_soc_pct"))
    print(
        "Optimization attempt:",
        first_result.get("grid_optimization", {}).get(
            "optimization_attempt"
        ),
    )

    assert first_result.get("approval_status") == "pending", (
        "Expected a second human-approval pause after replanning."
    )

    assert first_result.get("replan_status") == "ready"
    assert first_result.get("replan_attempts") == 1
    assert first_result.get("terminal_soc_pct") == 55.0

    optimization = first_result.get("grid_optimization", {})

    assert optimization.get("feasible") is True
    assert optimization.get("optimization_attempt") == 1
    assert optimization.get("terminal_soc_pct") == 55.0

    print("PASS: Revised schedule generated.")

    # Step 2: Verify the workflow paused again for human approval.
    snapshot = renewable_energy_workflow.get_state(config)

    assert snapshot.next, (
        "Expected the workflow to pause for a second human decision."
    )

    print("PASS: Workflow paused for second human approval.")

    # Step 3: Approve the revised recommendation.
    final_result = resume_workflow(config, "approve")

    print("\nAfter second approval:")
    print("Approval status:", final_result.get("approval_status"))
    print("Human approved:", final_result.get("human_approved"))
    print("Workflow status:", final_result.get("workflow_status"))
    print("Execution trace:", final_result.get("execution_trace"))

    assert final_result.get("approval_status") == "approved"
    assert final_result.get("human_approved") is True

    snapshot = renewable_energy_workflow.get_state(config)

    assert not snapshot.next, (
        "Expected the workflow to finish after the second approval."
    )

    print("PASS: Revised recommendation approved.")
    print("PASS: Workflow completed successfully.")


def main():
    test_approval_only()
    test_rejection_replanning_and_second_approval()

    print("\n" + "=" * 55)
    print("ALL TESTS PASSED")
    print("=" * 55)


if __name__ == "__main__":
    main()