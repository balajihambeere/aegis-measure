import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import AlertType


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    suite_id: uuid.UUID | None
    run_id: uuid.UUID | None
    alert_type: AlertType
    message: str
    created_at: datetime
    acknowledged_at: datetime | None
