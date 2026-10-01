import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.alert import AlertRead
from app.services import alert_service

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertRead])
def list_alerts(
    suite_id: uuid.UUID | None = None,
    unacknowledged_only: bool = False,
    db: Session = Depends(get_db),
) -> list[AlertRead]:
    alerts = alert_service.list_alerts(
        db, suite_id=suite_id, unacknowledged_only=unacknowledged_only
    )
    return [AlertRead.model_validate(a) for a in alerts]


@router.post("/{alert_id}/acknowledge", response_model=AlertRead)
def acknowledge_alert(alert_id: uuid.UUID, db: Session = Depends(get_db)) -> AlertRead:
    alert = alert_service.acknowledge_alert(db, alert_id)
    return AlertRead.model_validate(alert)
