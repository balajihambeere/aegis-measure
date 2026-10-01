import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import TimestampMixin, UUIDPKMixin
from app.models.enums import CoverageStatus


class LaunchCoverageCheck(UUIDPKMixin, TimestampMixin, Base):
    """"If this broke silently, who would notice, and when?" — a tracked,
    explicit answer required before a feature with a fixed launch date
    ships, instead of "watch the queue and hope". Gaps are declared on
    purpose, not discovered by accident."""

    __tablename__ = "launch_coverage_checks"

    feature_name: Mapped[str] = mapped_column(String(300))
    launch_date: Mapped[date] = mapped_column(Date)
    linked_suite_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suites.id"), nullable=True
    )
    declared_gaps: Mapped[list[str]] = mapped_column(JSON, default=list)
    coverage_status: Mapped[CoverageStatus] = mapped_column(
        Enum(CoverageStatus, name="coverage_status"), default=CoverageStatus.NONE
    )
    answered_by: Mapped[str] = mapped_column(String(200))
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    re_review_due_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    re_review_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
