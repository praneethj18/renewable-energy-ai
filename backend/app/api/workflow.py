import json
from threading import Event, Lock
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from langgraph.types import Command

from app.db.database import SessionLocal, get_db
from app.db.models import WorkflowRun
from app.services.alerts import record_workflow_alerts
from app.services.workflow_status import effective_workflow_status
from app.workflows.graph import renewable_energy_workflow


router = APIRouter(prefix="/workflow", tags=["Agent Workflow"])


class WorkflowStartRequest(BaseModel):
    latitude: float = Field(17.385, ge=-90, le=90)
    longitude: float = Field(78.4867, ge=-180, le=180)
    initial_soc_pct: float = Field(45.0, ge=10, le=90)
    terminal_soc_pct: float = Field(45.0, ge=10, le=90)
    timestep_hours: float = Field(1.0, gt=0, le=24)
    battery_capacity_mwh: float | None = Field(default=None, gt=0)
    max_charge_mw: float | None = Field(default=None, ge=0)
    max_discharge_mw: float | None = Field(default=None, ge=0)
    min_soc_pct: float | None = Field(default=None, ge=0, le=100)
    max_soc_pct: float | None = Field(default=None, gt=0, le=100)
    charge_efficiency: float | None = Field(default=None, gt=0, le=1)
    discharge_efficiency: float | None = Field(default=None, gt=0, le=1)
    battery_is_available: bool | None = False
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=100)


class ApprovalRequest(BaseModel):
    decision: str
    feedback: str = ""
    plan_version: int | None = Field(default=None, ge=1)


class RecalculateRequest(WorkflowStartRequest):
    plan_version: int = Field(ge=1)


# In-memory registry for workflow IDs.
# Workflow state itself is checkpointed by LangGraph's MemorySaver.
workflow_configs: dict[str, dict[str, Any]] = {}
workflow_request_lock = Lock()
workflow_request_registry: dict[str, dict[str, Any]] = {}


def _persisted_workflow_for_key(idempotency_key: str) -> dict[str, Any] | None:
    with SessionLocal() as db:
        rows = db.scalars(select(WorkflowRun).order_by(WorkflowRun.created_at.desc())).all()
        for row in rows:
            stored = row.state_json or {}
            inputs = stored.get("workflow_inputs", {})
            if isinstance(inputs, dict) and inputs.get("idempotency_key") == idempotency_key:
                return stored
    return None


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(
        value,
        default=lambda item: item.item() if hasattr(item, "item") else str(item),
    ))


def _persist_workflow(status: dict[str, Any], decision: dict[str, Any] | None = None) -> None:
    workflow_id = status["workflow_id"]
    with SessionLocal() as db:
        record = db.get(WorkflowRun, workflow_id)
        if record is None:
            record = WorkflowRun(id=workflow_id, status=status["status"], state_json={})
            db.add(record)
        record.status = status["status"]
        record.approval_status = status["approval_status"]
        record.plan_version = status["plan_version"]
        record.state_json = _json_safe(status)
        if decision:
            history = list(record.approval_history or [])
            history.append(_json_safe({**decision, "recorded_at": datetime.now(timezone.utc)}))
            record.approval_history = history
        db.commit()
        record_state = status.get("state", {})
        record_workflow_alerts(db, workflow_id, record_state)


def get_workflow_status(config: dict[str, Any]) -> dict[str, Any]:
    """Return a JSON-safe summary of the current workflow state."""

    snapshot = renewable_energy_workflow.get_state(config)
    state = snapshot.values or {}

    return {
        "workflow_id": config["configurable"]["thread_id"],
        "status": effective_workflow_status(
            state.get("workflow_status", "running"),
            state.get("approval_status", "pending"),
            state,
            waiting_for_human=bool(snapshot.next),
        ),
        "approval_status": state.get("approval_status", "pending"),
        "human_approved": state.get("human_approved", False),
        "replan_status": state.get("replan_status"),
        "replan_attempts": state.get("replan_attempts", 0),
        "plan_version": state.get("plan_version", 1),
        "workflow_inputs": state.get("workflow_inputs", {}),
        "grid_optimization": state.get("grid_optimization", {}),
        "review_result": state.get("review_result", {}),
        "agent_results": state.get("agent_results", {}),
        "asset_status": state.get("asset_status", {}),
        "generation_forecast_mw": state.get("generation_forecast_mw", []),
        "solar_forecast_mw": state.get("solar_forecast_mw", []),
        "wind_forecast_mw": state.get("wind_forecast_mw", []),
        "generation_forecast_timestamps": state.get("generation_forecast_timestamps", []),
        "demand_forecast_mw": state.get("demand_forecast_mw", []),
        "demand_forecast_timestamps": state.get("demand_forecast_timestamps", []),
        "anomalies": state.get("anomalies", []),
        "performance_analysis": state.get("performance_analysis", {}),
        "battery_status": state.get("battery_status", {}),
        "forecast_provenance": {
            name: state.get("agent_results", {}).get(name, {})
            for name in ("generation_forecasting", "demand_forecasting")
        },
        "execution_trace": state.get("execution_trace", []),
        "errors": state.get("errors", []),
        "waiting_for_human": bool(snapshot.next),
        "resumable": True,
        "state": state,
    }


@router.post("/start")
def start_workflow(request: WorkflowStartRequest):
    """Start a new workflow and run until completion or human approval."""

    idempotency_key = request.idempotency_key
    request_inputs = request.model_dump(exclude={"idempotency_key"})
    request_entry: dict[str, Any] | None = None
    owns_request = True
    if idempotency_key:
        with workflow_request_lock:
            request_entry = workflow_request_registry.get(idempotency_key)
            if request_entry is None:
                persisted = _persisted_workflow_for_key(idempotency_key)
                if persisted is not None:
                    stored_inputs = persisted.get("workflow_inputs", {})
                    comparable = {key: value for key, value in stored_inputs.items() if key != "idempotency_key"}
                    if comparable != request_inputs:
                        raise HTTPException(status_code=409, detail="This idempotency key was already used with different workflow inputs.")
                    return persisted
                if len(workflow_request_registry) >= 128:
                    for completed_key, completed_entry in list(workflow_request_registry.items()):
                        if completed_entry["done"].is_set():
                            workflow_request_registry.pop(completed_key, None)
                        if len(workflow_request_registry) < 128:
                            break
                request_entry = {"inputs": request_inputs, "done": Event()}
                workflow_request_registry[idempotency_key] = request_entry
            elif request_entry["inputs"] != request_inputs:
                raise HTTPException(status_code=409, detail="This idempotency key was already used with different workflow inputs.")
            else:
                owns_request = False

    if not owns_request and request_entry is not None:
        if not request_entry["done"].wait(timeout=35):
            raise HTTPException(status_code=409, detail="A workflow with this request key is still running. Retry the same request key to retrieve its result.")
        if request_entry.get("error"):
            raise HTTPException(status_code=500, detail=request_entry["error"])
        return request_entry["status"]

    workflow_id = str(uuid4())
    config = {
        "configurable": {
            "thread_id": workflow_id,
        }
    }

    initial_state = {
        "latitude": request.latitude,
        "longitude": request.longitude,
        "initial_soc_pct": request.initial_soc_pct,
        "terminal_soc_pct": request.terminal_soc_pct,
        "timestep_hours": request.timestep_hours,
        "battery_capacity_mwh": request.battery_capacity_mwh,
        "max_charge_mw": request.max_charge_mw,
        "max_discharge_mw": request.max_discharge_mw,
        "min_soc_pct": request.min_soc_pct,
        "max_soc_pct": request.max_soc_pct,
        "charge_efficiency": request.charge_efficiency,
        "discharge_efficiency": request.discharge_efficiency,
        "battery_is_available": request.battery_is_available,
        "workflow_inputs": request.model_dump(),
        "replan_attempts": 0,
        "max_replan_attempts": 2,
        "plan_version": getattr(request, "plan_version", 1),
        "agent_results": {},
        "execution_trace": [],
        "errors": [],
    }

    try:
        workflow_configs[workflow_id] = config
        renewable_energy_workflow.invoke(initial_state, config=config)
        status = get_workflow_status(config)
        _persist_workflow(status)
        if request_entry is not None:
            request_entry["status"] = status
            request_entry["done"].set()
        return status
    except Exception as exc:
        workflow_configs.pop(workflow_id, None)
        if request_entry is not None:
            request_entry["error"] = f"Workflow failed: {exc}"
            request_entry["done"].set()
        raise HTTPException(
            status_code=500,
            detail=f"Workflow failed: {exc}",
        ) from exc


@router.post("/{workflow_id}/recalculate")
def recalculate_workflow(workflow_id: str, request: RecalculateRequest):
    """Re-run with revised assumptions and supersede the prior plan."""
    config = workflow_configs.get(workflow_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Workflow is not available in this application session.")
    snapshot = renewable_energy_workflow.get_state(config)
    current_version = (snapshot.values or {}).get("plan_version", 1)
    if request.plan_version != current_version:
        raise HTTPException(status_code=409, detail="The plan has changed. Refresh it before recalculating.")
    if not snapshot.next:
        raise HTTPException(status_code=409, detail="Only a workflow waiting for operator review can be recalculated.")
    revised_request = request.model_copy(update={"plan_version": request.plan_version + 1})
    updated = start_workflow(revised_request)
    with SessionLocal() as db:
        record = db.get(WorkflowRun, workflow_id)
        if record:
            persisted = dict(record.state_json or {})
            persisted["approval_status"] = "superseded"
            persisted["superseded_by_workflow_id"] = updated["workflow_id"]
            record.status = "superseded"
            record.approval_status = "superseded"
            record.state_json = persisted
            db.commit()
    updated["supersedes_workflow_id"] = workflow_id
    return updated


@router.get("/runs")
def list_workflows(limit: int = 50, db: Session = Depends(get_db)):
    records = db.scalars(
        select(WorkflowRun).order_by(WorkflowRun.created_at.desc()).limit(max(1, min(limit, 200)))
    ).all()
    return [
        {
            "workflow_id": row.id,
            "status": effective_workflow_status(
                row.status, row.approval_status, row.state_json
            ),
            "approval_status": row.approval_status,
            "plan_version": row.plan_version,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "workflow": row.state_json,
            "approval_history": row.approval_history,
        }
        for row in records
    ]


@router.get("/{workflow_id}/events")
def get_workflow_events(workflow_id: str, db: Session = Depends(get_db)):
    record = db.get(WorkflowRun, workflow_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    state = record.state_json or {}
    return {
        "workflow_id": workflow_id,
        "plan_version": record.plan_version,
        "execution_trace": state.get("execution_trace", []),
        "agent_results": state.get("agent_results", {}),
        "errors": state.get("errors", []),
    }


@router.get("/{workflow_id}")
def get_workflow(workflow_id: str):
    """Inspect the current state of a workflow."""

    config = workflow_configs.get(workflow_id)

    with SessionLocal() as db:
        record = db.get(WorkflowRun, workflow_id)
        if record is not None and record.approval_status == "superseded":
            persisted = dict(record.state_json or {})
            persisted["status"] = effective_workflow_status(
                record.status, record.approval_status, persisted
            )
            persisted["resumable"] = False
            persisted["approval_history"] = record.approval_history or []
            return persisted

    if config is None:
        with SessionLocal() as db:
            record = db.get(WorkflowRun, workflow_id)
            if record is None:
                raise HTTPException(status_code=404, detail="Workflow not found.")
            persisted = dict(record.state_json or {})
            persisted["status"] = effective_workflow_status(
                record.status, record.approval_status, persisted
            )
            persisted["resumable"] = False
            persisted["approval_history"] = record.approval_history or []
            return persisted

    return get_workflow_status(config)


@router.post("/{workflow_id}/approval")
def submit_approval(
    workflow_id: str,
    request: ApprovalRequest,
):
    """Submit an approval or rejection decision."""

    config = workflow_configs.get(workflow_id)

    if config is None:
        raise HTTPException(
            status_code=404,
            detail="Workflow not found in this application session.",
        )

    decision = request.decision.strip().lower()

    if decision not in {"approve", "reject"}:
        raise HTTPException(
            status_code=422,
            detail="Decision must be 'approve' or 'reject'.",
        )

    snapshot = renewable_energy_workflow.get_state(config)
    current_plan_version = (snapshot.values or {}).get("plan_version", 1)
    if request.plan_version is not None and request.plan_version != current_plan_version:
        raise HTTPException(
            status_code=409,
            detail="This decision refers to an outdated plan version. Review the current plan.",
        )

    with SessionLocal() as db:
        record = db.get(WorkflowRun, workflow_id)
        if record is not None and record.approval_status == "superseded":
            raise HTTPException(status_code=409, detail="This plan was superseded. Review the replacement plan.")

    if not snapshot.next:
        raise HTTPException(
            status_code=409,
            detail="Workflow is not waiting for human input.",
        )

    if decision == "reject" and not request.feedback.strip():
        raise HTTPException(
            status_code=422,
            detail="Provide feedback when rejecting a recommendation.",
        )

    try:
        renewable_energy_workflow.invoke(
            Command(
                resume={
                    "decision": decision,
                    "feedback": request.feedback,
                }
            ),
            config=config,
        )

        status = get_workflow_status(config)
        _persist_workflow(status, {
            "decision": decision,
            "feedback": request.feedback,
            "plan_version": current_plan_version,
        })
        return status

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not resume workflow: {exc}",
        ) from exc
