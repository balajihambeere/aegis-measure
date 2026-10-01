import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CheckMode, Diagnosis, GraderType, RunStatus, TriggerSource


class EvalRunCreate(BaseModel):
    suite_id: uuid.UUID
    trigger_source: Literal["manual", "on_change"] = "manual"
    judge_model_version: str = Field(
        default="", description="Defaults to the configured JUDGE_MODEL."
    )


class EvalRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    suite_id: uuid.UUID
    trigger_source: TriggerSource
    judge_model_version: str
    status: RunStatus
    started_at: datetime
    finished_at: datetime | None
    error_message: str


class CaseResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_id: uuid.UUID
    case_id: uuid.UUID
    check_mode: CheckMode
    grader_type: GraderType
    candidate_answer: str
    retrieved_context: str | None
    dimension_results: dict
    passed: bool
    diagnosis: Diagnosis
    created_at: datetime
