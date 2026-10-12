import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Alert, WorkflowRun


def workflow_finding_fingerprint(finding: dict, timestamps: list) -> str:
    """Fingerprint a finding by its event so reruns do not create new copies."""
    timestamp = finding.get("timestamp_utc")
    timestep = finding.get("timestep")
    if timestamp is None and isinstance(timestep, int) and not isinstance(timestep, bool) and 0 <= timestep < len(timestamps):
        timestamp = timestamps[timestep]
    identity = "|".join(str(value or "") for value in (
        finding.get("type"), finding.get("asset_id"), finding.get("severity"),
        timestamp, finding.get("description"),
    ))
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def record_workflow_alerts(
    db: Session,
    workflow_id: str,
    state: dict,
) -> None:
    """Persist newly observed workflow findings without duplicating them."""
    seen_fingerprints: set[str] = set()
    timestamps = state.get("generation_forecast_timestamps", [])
    if not isinstance(timestamps, list):
        timestamps = []
    existing_fingerprints: set[str] = set()
    prior_workflow_ids = {
        alert.workflow_id
        for alert in db.scalars(select(Alert)).all()
        if alert.workflow_id is not None
    }
    if prior_workflow_ids:
        prior_runs = db.execute(
            select(WorkflowRun.id, WorkflowRun.state_json).where(WorkflowRun.id.in_(prior_workflow_ids))
        ).all()
        for _prior_id, persisted in prior_runs:
            persisted = persisted or {}
            prior_state = persisted.get("state", {}) if isinstance(persisted, dict) else {}
            if not isinstance(prior_state, dict):
                prior_state = {}
            prior_findings = prior_state.get("anomalies", []) or persisted.get("anomalies", [])
            prior_timestamps = prior_state.get("generation_forecast_timestamps", []) or persisted.get("generation_forecast_timestamps", [])
            if not isinstance(prior_timestamps, list):
                prior_timestamps = []
            for prior_finding in prior_findings:
                if isinstance(prior_finding, dict):
                    existing_fingerprints.add(workflow_finding_fingerprint(prior_finding, prior_timestamps))
    for finding in state.get("anomalies", []):
        if not isinstance(finding, dict):
            continue
        fingerprint = workflow_finding_fingerprint(finding, timestamps)
        if fingerprint in seen_fingerprints:
            continue
        seen_fingerprints.add(fingerprint)
        exists = db.scalar(select(Alert.id).where(Alert.fingerprint == fingerprint))
        if exists or fingerprint in existing_fingerprints:
            continue
        db.add(Alert(
            workflow_id=workflow_id,
            asset_id=finding.get("asset_id"),
            fingerprint=fingerprint,
            severity=str(finding.get("severity", "medium")),
            title=str(finding.get("type", "Workflow finding")).replace("_", " ").title(),
            reason=str(finding.get("description", "Finding returned by the analysis workflow")),
            status="open",
        ))
    db.commit()
