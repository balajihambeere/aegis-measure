import uuid

from pydantic import BaseModel

from app.schemas.eval_run import EvalRunRead


class OnChangeTriggerRequest(BaseModel):
    suite_id: uuid.UUID | None = None
    reason: str = ""


class OnChangeTriggerResponse(BaseModel):
    triggered: list[EvalRunRead]
    skipped_suite_ids: list[uuid.UUID]
