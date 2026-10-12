"""Focused, isolated checks for alert deduplication and workflow request retries."""

from concurrent.futures import ThreadPoolExecutor
import hashlib
from threading import Barrier
from time import sleep
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.api import alerts as alerts_api
from app.api import workflow as workflow_api
from app.db.database import Base
from app.db.models import Alert, WorkflowRun
from app.services.alerts import record_workflow_alerts


def check_alert_deduplication_and_acknowledgement() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    first_id, second_id = str(uuid4()), str(uuid4())
    timestamp = "2026-10-12T13:00:00+00:00"
    repeated = {
        "type": "generation_demand_imbalance",
        "severity": "medium",
        "timestep": 0,
        "generation_mw": 1.0,
        "demand_mw": 4.0,
        "description": "Forecast generation is below 25% of forecast demand.",
    }
    inactive = {"type": "inactive_assets", "severity": "high", "description": "One asset is inactive."}
    state = {
        "generation_forecast_timestamps": [timestamp],
        "anomalies": [repeated, dict(repeated), inactive, dict(inactive)],
    }
    with Session(engine) as db:
        db.add_all([
            WorkflowRun(id=first_id, status="awaiting_human_review", state_json={}),
            WorkflowRun(id=second_id, status="awaiting_human_review", state_json={}),
        ])
        db.commit()
        record_workflow_alerts(db, first_id, state)
        assert db.scalar(select(func.count()).select_from(Alert)) == 2, "same-batch findings were duplicated"
        record_workflow_alerts(db, second_id, state)
        assert db.scalar(select(func.count()).select_from(Alert)) == 2, "rerun findings were duplicated"
        alert = db.scalar(select(Alert).where(Alert.title == "Generation Demand Imbalance"))
        assert alert is not None
        first_ack = alerts_api.acknowledge_alert(alert.id, db)
        ack_time = first_ack.acknowledged_at
        second_ack = alerts_api.acknowledge_alert(alert.id, db)
        assert second_ack.status == "acknowledged" and second_ack.acknowledged_at == ack_time
    engine.dispose()


def check_legacy_alert_rerun_deduplication() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    prior_id, next_id = str(uuid4()), str(uuid4())
    finding = {
        "type": "generation_demand_imbalance",
        "severity": "medium",
        "timestep": 0,
        "description": "Repeated forecast finding.",
    }
    state = {"generation_forecast_timestamps": ["2026-10-12T13:00:00+00:00"], "anomalies": [finding]}
    legacy_identity = "|".join(str(finding.get(key, "")) for key in (
        "type", "asset_id", "timestep", "timestamp_utc", "description"
    ))
    legacy_fingerprint = hashlib.sha256(f"{prior_id}|{legacy_identity}".encode("utf-8")).hexdigest()
    with Session(engine) as db:
        db.add_all([
            WorkflowRun(id=prior_id, status="awaiting_human_review", state_json={"state": state}),
            WorkflowRun(id=next_id, status="awaiting_human_review", state_json={}),
            Alert(workflow_id=prior_id, fingerprint=legacy_fingerprint, severity="medium", title="Generation Demand Imbalance", reason=finding["description"], status="open"),
        ])
        db.commit()
        record_workflow_alerts(db, next_id, state)
        assert db.scalar(select(func.count()).select_from(Alert)) == 1, "legacy repeated finding was recreated"
    engine.dispose()


def check_workflow_request_idempotency() -> None:
    class FakeGraph:
        calls = 0

        def invoke(self, _state, **_kwargs):
            self.calls += 1
            sleep(0.15)

    graph = FakeGraph()
    key = f"test-{uuid4()}"
    barrier = Barrier(2)
    request = workflow_api.WorkflowStartRequest(idempotency_key=key)
    fake_result = {"workflow_id": "single-workflow", "status": "awaiting_human_review"}

    def call_start():
        barrier.wait()
        return workflow_api.start_workflow(request)

    try:
        with (
            patch.object(workflow_api, "renewable_energy_workflow", graph),
            patch.object(workflow_api, "_persisted_workflow_for_key", return_value=None),
            patch.object(workflow_api, "get_workflow_status", return_value=fake_result),
            patch.object(workflow_api, "_persist_workflow"),
            ThreadPoolExecutor(max_workers=2) as pool,
        ):
            responses = list(pool.map(lambda _index: call_start(), range(2)))
        assert graph.calls == 1, f"expected one workflow invocation, got {graph.calls}"
        assert responses[0] == responses[1] == fake_result
    finally:
        workflow_api.workflow_request_registry.pop(key, None)
        workflow_api.workflow_configs.pop("single-workflow", None)


if __name__ == "__main__":
    check_alert_deduplication_and_acknowledgement()
    check_legacy_alert_rerun_deduplication()
    check_workflow_request_idempotency()
    print("Alert deduplication, acknowledgement idempotence, and workflow request idempotency passed.")
