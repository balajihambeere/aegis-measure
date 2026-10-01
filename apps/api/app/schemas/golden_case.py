import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CaseStatus, CheckMode


class GoldenCaseCreate(BaseModel):
    suite_id: uuid.UUID
    question: str = Field(min_length=1)
    context: str | None = None
    source: str = Field(min_length=1, description="e.g. real_complaint, support_queue, manual")
    check_mode: CheckMode = CheckMode.BOTH
    tags: list[str] = Field(default_factory=list)
    rubric_id: uuid.UUID | None = None


class GoldenCaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    suite_id: uuid.UUID
    rubric_id: uuid.UUID | None
    question: str
    context: str | None
    reference_answer: str | None
    check_mode: CheckMode
    status: CaseStatus
    source: str
    tags: list[str]
    resolved_by: str | None
    resolved_at: datetime | None
    resolution_notes: str | None
    created_at: datetime
    updated_at: datetime


class ReviewSubmissionCreate(BaseModel):
    reviewer_name: str = Field(min_length=1, max_length=200)
    proposed_answer: str = Field(min_length=1)


class ReviewSubmissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reviewer_name: str
    proposed_answer: str
    submitted_at: datetime


class ReviewStatusRead(BaseModel):
    """The blind-review contract — while fewer than two independent
    submissions exist, reviewers can confirm their own was recorded but
    cannot see the other's answer."""

    case_id: uuid.UUID
    submission_count: int
    reviewer_names: list[str]
    submissions: list[ReviewSubmissionRead] | None = Field(
        default=None,
        description="Only populated once both independent submissions exist.",
    )


class CaseResolutionRequest(BaseModel):
    decision: Literal["approve", "needs_resolution"]
    resolved_by: str = Field(min_length=1, max_length=200)
    reference_answer: str | None = Field(
        default=None, description="Required when decision='approve'."
    )
    notes: str = ""
