import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, UUIDPKMixin, utcnow

if TYPE_CHECKING:
    # Only for type-checkers/linters resolving the Mapped[...] forward refs
    # below; importing at runtime would be circular (GoldenCase imports Suite).
    from app.models.golden_case import GoldenCase


class Suite(UUIDPKMixin, TimestampMixin, Base):
    """A named grouping of golden-set cases, e.g. 'fabric-and-care' or
    'festive-sale-bundle-policy' — each with its own default schedule
    interval."""

    __tablename__ = "suites"

    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    description: Mapped[str] = mapped_column(String, default="")
    default_schedule_interval_hours: Mapped[int] = mapped_column(Integer, default=6)

    # Target classes passed as explicit strings (classic relationship()
    # resolution via the shared declarative registry) rather than inferred
    # from the Mapped[...] annotation, since GoldenCase imports Suite and a
    # module-level import back here would be circular.
    # passive_deletes=True: let Postgres's ON DELETE CASCADE handle removing
    # dependents; don't have the ORM try (and fail, since the FK is NOT NULL)
    # to null out child rows that happen to be loaded in the session.
    cases: Mapped[list["GoldenCase"]] = relationship(
        "GoldenCase", back_populates="suite", passive_deletes=True
    )
    schedule_overrides: Mapped[list["ScheduleOverride"]] = relationship(
        "ScheduleOverride", back_populates="suite", passive_deletes=True
    )


class ScheduleOverride(UUIDPKMixin, Base):
    """A time-bounded tightened interval for a high-risk launch window (e.g.
    hourly checks during the festive sale weekend instead of the suite's
    normal 6-hour default)."""

    __tablename__ = "schedule_overrides"

    suite_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suites.id", ondelete="CASCADE"), index=True
    )
    interval_hours: Mapped[int] = mapped_column(Integer)
    starts_at: Mapped[datetime] = mapped_column()
    ends_at: Mapped[datetime] = mapped_column()
    reason: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    suite: Mapped["Suite"] = relationship(back_populates="schedule_overrides")
