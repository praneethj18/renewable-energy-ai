import operator
from typing import Annotated, Any, TypedDict


class RenewableEnergyState(TypedDict, total=False):
    # Request information
    request_id: str
    plan_version: int
    workflow_inputs: dict[str, Any]
    location: str
    latitude: float
    longitude: float

    # Forecast inputs
    generation_forecast_mw: list[float]
    solar_forecast_mw: list[float]
    wind_forecast_mw: list[float]
    demand_forecast_mw: list[float]

    # Explicit forecast timestamps
    generation_forecast_timestamps: list[str]
    demand_forecast_timestamps: list[str]

    # Weather information
    weather_data: dict[str, Any]

    # Asset monitoring
    asset_status: dict[str, Any]

    # Performance and anomaly analysis
    anomalies: list[dict[str, Any]]
    performance_analysis: dict[str, Any]

    # Battery management
    battery_status: dict[str, Any]
    initial_soc_pct: float
    terminal_soc_pct: float
    timestep_hours: float
    battery_capacity_mwh: float
    max_charge_mw: float
    max_discharge_mw: float
    min_soc_pct: float
    max_soc_pct: float
    charge_efficiency: float
    discharge_efficiency: float
    battery_is_available: bool

    # Grid coordination
    grid_optimization: dict[str, Any]

    # Agent results: merge dictionaries from different agents
    agent_results: Annotated[dict[str, Any], operator.or_]

    # Execution tracking: accumulate entries from every node
    execution_trace: Annotated[list[str], operator.add]
    errors: Annotated[list[str], operator.add]

    # Review and approval
    review_result: dict[str, Any]
    approval_required: bool
    human_approved: bool
    approval_status: str

    # Human feedback and replanning
    rejection_feedback: str
    replan_attempts: int
    max_replan_attempts: int
    replan_status: str

    # Final output
    final_report: dict[str, Any]
    workflow_status: str
