import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, UUIDPKMixin, utcnow
from app.models.enums import CaseStatus, CheckMode
from app.models.rubric import Rubric  # noqa: F401 (used in forward-ref string below)
from app.models.suite import Suite  # noqa: F401 (used in forward-ref string below)


class GoldenCase(UUIDPKMixin, TimestampMixin, Base):
    """A real question, the exact context the system would see, and a
    reference answer two independent reviewers agree is correct. A case only
    belongs in the golden set once that agreement actually happens — see
    ReviewSubmission and the two-reviewer-agreement rule enforced in
    app.services.review."""

    __tablename__ = "golden_cases"

    suite_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suites.id", ondelete="CASCADE"), index=True
    )
    rubric_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rubrics.id"), nullable=True
    )

    question: Mapped[str] = mapped_column(Text)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_answer: Mapped[str | None] = mapped_column(Text, nullable=True)

    check_mode: Mapped[CheckMode] = mapped_column(
        Enum(CheckMode, name="check_mode"), default=CheckMode.BOTH
    )
    status: Mapped[CaseStatus] = mapped_column(
        Enum(CaseStatus, name="case_status"), default=CaseStatus.DRAFT, index=True
    )

    # Provenance matters — cases must come from real usage, not imagined
    # questions. e.g. "real_complaint", "support_queue", "manual_spotcheck".
    source: Mapped[str] = mapped_column(String(100), default="")
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)

    # When two reviewers disagree, that's not a grading problem to paper
    # over — it means the underlying source material itself is ambiguous.
    # resolution_notes records why a case was approved or flagged.
    resolved_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    suite: Mapped["Suite"] = relationship(back_populates="cases")
    rubric: Mapped["Rubric | None"] = relationship()
    review_submissions: Mapped[list["ReviewSubmission"]] = relationship(
        back_populates="case",
        order_by="ReviewSubmission.submitted_at",
        passive_deletes=True,
    )


class ReviewSubmission(UUIDPKMixin, Base):
    """A single reviewer's independently-written answer for a case. A case
    can only be approved once two submissions from two different reviewers
    exist and agree — see app.services.review for the comparison and the
    blind-until-both-submitted rule enforced at the API layer."""

    __tablename__ = "review_submissions"

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("golden_cases.id", ondelete="CASCADE"), index=True
    )
    reviewer_name: Mapped[str] = mapped_column(String(200))
    proposed_answer: Mapped[str] = mapped_column(Text)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    case: Mapped["GoldenCase"] = relationship(back_populates="review_submissions")
