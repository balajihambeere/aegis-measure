import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import UUIDPKMixin, utcnow
from app.models.golden_case import GoldenCase  # noqa: F401 (used in forward-ref string below)


class HumanLabeledSample(UUIDPKMixin, Base):
    """A (candidate answer, human verdict) pair for a known case, used as
    calibration ground truth — 'does the judge's verdict match a person's,
    on cases we already know the real answer to.' Independent of whether the
    sample is a real system output or a deliberately-wrong one used to
    stress-test the grader."""

    __tablename__ = "human_labeled_samples"

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("golden_cases.id", ondelete="CASCADE"), index=True
    )
    candidate_answer: Mapped[str] = mapped_column(Text)
    human_verdict: Mapped[bool] = mapped_column(Boolean)
    labeled_by: Mapped[str] = mapped_column(String(200))
    labeled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    case: Mapped["GoldenCase"] = relationship()


class CalibrationRun(UUIDPKMixin, Base):
    """Before a rubric/judge-model combination can be trusted for scheduled
    runs, its verdicts must be checked against known human verdicts and must
    agree above a threshold. Re-run whenever the golden set gains a new case
    category or the judge model changes."""

    __tablename__ = "calibration_runs"

    rubric_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rubrics.id", ondelete="CASCADE"), index=True
    )
    judge_model_version: Mapped[str] = mapped_column(String(200))

    sample_size: Mapped[int] = mapped_column(Integer)
    agreement_count: Mapped[int] = mapped_column(Integer)
    agreement_rate: Mapped[float] = mapped_column(Float)
    threshold: Mapped[float] = mapped_column(Float)
    passed_threshold: Mapped[bool] = mapped_column(Boolean)

    # List of {case_id, judge_verdict, human_verdict, note} for every sample
    # where the judge and a human disagreed, so the gap is inspectable later.
    disagreements: Mapped[list[dict]] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
