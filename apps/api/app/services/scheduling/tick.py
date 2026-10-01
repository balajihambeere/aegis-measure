from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.common import utcnow
from app.models.enums import TriggerSource
from app.models.eval_run import EvalRun
from app.models.suite import ScheduleOverride, Suite
from app.services.errors import ConflictError
from app.services.eval_engine import run_eval
from app.services.grading.llm_judge import LLMJudgeGrader
from app.services.suite_service import list_suites
from app.services.sut_adapter.base import SUTAdapter


def _effective_interval_hours(db: Session, suite: Suite, now: datetime) -> int:
    """A suite's schedule tightens for a time-bounded high-risk window (e.g.
    hourly during a major sale) instead of its normal default (e.g. every 6
    hours). The tightest active override wins if more than one happens to
    overlap."""
    override = db.execute(
        select(ScheduleOverride)
        .where(
            ScheduleOverride.suite_id == suite.id,
            ScheduleOverride.starts_at <= now,
            ScheduleOverride.ends_at > now,
        )
        .order_by(ScheduleOverride.interval_hours.asc())
        .limit(1)
    ).scalar_one_or_none()
    return override.interval_hours if override else suite.default_schedule_interval_hours


def _last_run_started_at(db: Session, suite_id) -> datetime | None:
    return db.execute(
        select(EvalRun.started_at)
        .where(EvalRun.suite_id == suite_id)
        .order_by(EvalRun.started_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def is_suite_due(db: Session, suite: Suite, now: datetime) -> bool:
    last_run = _last_run_started_at(db, suite.id)
    if last_run is None:
        return True
    interval = _effective_interval_hours(db, suite, now)
    return now - last_run >= timedelta(hours=interval)


def run_due_suites(
    db: Session,
    *,
    grader: LLMJudgeGrader,
    sut: SUTAdapter,
    judge_model_version: str,
    now: datetime | None = None,
) -> list[EvalRun]:
    """The scheduled trigger: fires every suite whose interval has elapsed
    since its last run, whether or not anything visibly changed on either
    side. Call this on a fixed tick (see app.jobs.scheduler) — it doesn't
    need to know why it's running, only whether enough time has passed."""
    now = now or utcnow()
    fired: list[EvalRun] = []
    for suite in list_suites(db):
        if not is_suite_due(db, suite, now):
            continue
        try:
            fired.append(
                run_eval(
                    db,
                    suite_id=suite.id,
                    trigger_source=TriggerSource.SCHEDULE,
                    grader=grader,
                    sut=sut,
                    judge_model_version=judge_model_version,
                )
            )
        except ConflictError:
            # Another trigger (e.g. an on-change webhook) is already running
            # this suite right now — skip it this tick rather than erroring
            # the whole sweep over every other suite.
            continue
    return fired
