from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from app.workflows.approval import human_approval_node
from app.workflows.asset_monitoring import asset_monitoring_node
from app.workflows.battery_management import battery_management_node
from app.workflows.demand_forecasting import demand_forecasting_node
from app.workflows.generation_forecasting import (
    generation_forecasting_node,
)
from app.workflows.nodes import (
    grid_coordination_node,
    weather_intelligence_node,
)
from app.workflows.performance_anomaly import (
    performance_anomaly_node,
)
from app.workflows.replanning import replanning_node
from app.workflows.reviewer import reviewer_node
from app.workflows.state import RenewableEnergyState


def route_after_approval(state: RenewableEnergyState) -> str:
    """Choose the next step based on the human's decision."""

    status = state.get("approval_status")

    if status == "approved":
        return "finish"

    if status == "rejected":
        return "replanning"

    return "finish"


def route_after_replanning(state: RenewableEnergyState) -> str:
    """Continue only when revised optimization inputs are ready."""

    if state.get("replan_status") == "ready":
        return "grid_coordination"

    return "finish"


def build_workflow():
    """Build the renewable energy workflow with bounded replanning."""

    workflow = StateGraph(RenewableEnergyState)

    workflow.add_node("asset_monitoring", asset_monitoring_node)
    workflow.add_node("weather_intelligence", weather_intelligence_node)
    workflow.add_node(
        "generation_forecasting",
        generation_forecasting_node,
    )
    workflow.add_node(
        "demand_forecasting",
        demand_forecasting_node,
    )
    workflow.add_node(
        "performance_anomaly",
        performance_anomaly_node,
    )
    workflow.add_node(
        "battery_management",
        battery_management_node,
    )
    workflow.add_node("grid_coordination", grid_coordination_node)
    workflow.add_node("reviewer", reviewer_node)
    workflow.add_node("human_approval", human_approval_node)
    workflow.add_node("replanning", replanning_node)

    workflow.add_edge(START, "asset_monitoring")
    workflow.add_edge("asset_monitoring", "weather_intelligence")

    # Forecasting agents execute in parallel.
    workflow.add_edge(
        "weather_intelligence",
        "generation_forecasting",
    )
    workflow.add_edge(
        "weather_intelligence",
        "demand_forecasting",
    )

    workflow.add_edge(
        ["generation_forecasting", "demand_forecasting"],
        "performance_anomaly",
    )

    workflow.add_edge(
        "performance_anomaly",
        "battery_management",
    )
    workflow.add_edge(
        "battery_management",
        "grid_coordination",
    )

    workflow.add_edge("grid_coordination", "reviewer")
    workflow.add_edge("reviewer", "human_approval")

    # Approval ends the workflow; rejection enters replanning.
    workflow.add_conditional_edges(
        "human_approval",
        route_after_approval,
        {
            "finish": END,
            "replanning": "replanning",
        },
    )

    # Replan only when feedback produced supported changes.
    workflow.add_conditional_edges(
        "replanning",
        route_after_replanning,
        {
            "grid_coordination": "grid_coordination",
            "finish": END,
        },
    )

    # Preserve state across human-approval pauses.
    checkpointer = MemorySaver()

    return workflow.compile(checkpointer=checkpointer)


renewable_energy_workflow = build_workflow()