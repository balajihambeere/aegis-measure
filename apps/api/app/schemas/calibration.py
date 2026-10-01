import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HumanLabeledSampleCreate(BaseModel):
    case_id: uuid.UUID
    candidate_answer: str = Field(min_length=1)
    human_verdict: bool
    labeled_by: str = Field(min_length=1, max_length=200)


class HumanLabeledSampleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_id: uuid.UUID
    candidate_answer: str
    human_verdict: bool
    labeled_by: str
    labeled_at: datetime


class CalibrationRunCreate(BaseModel):
    rubric_id: uuid.UUID
    judge_model_version: str = Field(min_length=1)
    threshold: float | None = Field(default=None, gt=0, le=1)


class CalibrationRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rubric_id: uuid.UUID
    judge_model_version: str
    sample_size: int
    agreement_count: int
    agreement_rate: float
    threshold: float
    passed_threshold: bool
    disagreements: list[dict]
    created_at: datetime
