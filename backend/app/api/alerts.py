from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Alert


router = APIRouter(prefix="/alerts", tags=["Alerts"])


class AlertResponse(BaseModel):
    id: int
    workflow_id: str | None
    asset_id: int | None
    severity: str
    title: str
    reason: str
    status: str
    created_at: datetime
    acknowledged_at: datetime | None

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[AlertResponse])
def list_alerts(
    status: str | None = Query(default=None, pattern="^(open|acknowledged)$"),
    db: Session = Depends(get_db),
):
    query = select(Alert).order_by(Alert.created_at.desc(), Alert.id.desc())
    if status:
        query = query.where(Alert.status == status)
    return db.scalars(query).all()


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
def acknowledge_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    if alert.status != "acknowledged":
        alert.status = "acknowledged"
        alert.acknowledged_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(alert)
    return alert
