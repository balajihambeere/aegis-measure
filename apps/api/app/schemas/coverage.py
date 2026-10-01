import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CoverageStatus


class LaunchCoverageCheckCreate(BaseModel):
    feature_name: str = Field(min_length=1, max_length=300)
    launch_date: date
    linked_suite_id: uuid.UUID | None = None
    declared_gaps: list[str] = Field(default_factory=list)
    coverage_status: CoverageStatus
    answered_by: str = Field(min_length=1, max_length=200)
    re_review_due_at: date | None = None


class LaunchCoverageCheckRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    feature_name: str
    launch_date: date
    linked_suite_id: uuid.UUID | None
    declared_gaps: list[str]
    coverage_status: CoverageStatus
    answered_by: str
    answered_at: datetime
    re_review_due_at: date | None
    re_review_completed_at: datetime | None
