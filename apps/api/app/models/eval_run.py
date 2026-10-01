import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import UUIDPKMixin, utcnow
from app.models.enums import CheckMode, Diagnosis, GraderType, RunStatus, TriggerSource
from app.models.suite import Suite  # noqa: F401 (used in forward-ref string below)


class EvalRun(UUIDPKMixin, Base):
    """One firing of the harness — either an on-change (deploy) trigger or a
    scheduled trigger — against a suite's approved golden cases."""

    __tablename__ = "eval_runs"

    suite_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suites.id", ondelete="CASCADE"), index=True
    )
    trigger_source: Mapped[TriggerSource] = mapped_column(
        Enum(TriggerSource, name="trigger_source")
    )
    judge_model_version: Mapped[str] = mapped_column(String(200), default="")
    rubric_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rubrics.id"), nullable=True
    )
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="run_status"), default=RunStatus.RUNNING, index=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, default="")

    suite: Mapped["Suite"] = relationship()
    results: Mapped[list["CaseResult"]] = relationship(
        back_populates="run", passive_deletes=True
    )


class CaseResult(UUIDPKMixin, Base):
    """One case graded in one check mode within one run. Running both
    component and end_to_end rows for the same case is what lets the
    platform localize a fault instead of just detecting one (see
    `diagnosis`)."""

    __tablename__ = "case_results"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("eval_runs.id", ondelete="CASCADE"), index=True
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("golden_cases.id", ondelete="CASCADE"), index=True
    )
    check_mode: Mapped[CheckMode] = mapped_column(Enum(CheckMode, name="result_check_mode"))
    grader_type: Mapped[GraderType] = mapped_column(Enum(GraderType, name="grader_type"))

    candidate_answer: Mapped[str] = mapped_column(Text)
    retrieved_context: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Per-rubric-dimension pass/fail + rationale, e.g.
    # {"core_fact_correct": {"passed": true, "rationale": "..."}, ...}
    dimension_results: Mapped[dict] = mapped_column(JSON, default=dict)
    passed: Mapped[bool] = mapped_column(Boolean)

    diagnosis: Mapped[Diagnosis] = mapped_column(
        Enum(Diagnosis, name="diagnosis"), default=Diagnosis.NONE
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    run: Mapped["EvalRun"] = relationship(back_populates="results")
