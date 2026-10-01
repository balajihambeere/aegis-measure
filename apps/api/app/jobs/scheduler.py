import logging
from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler

from app.api.deps import get_judge_grader, get_sut_adapter
from app.config import get_settings
from app.db.session import SessionLocal
from app.services.alert_service import check_coverage_gaps_due
from app.services.scheduling.tick import run_due_suites

logger = logging.getLogger("aegis")

_scheduler: BackgroundScheduler | None = None


def _run_tick() -> None:
    """The scheduled trigger: fires on a fixed interval regardless of
    whether anything visibly changed — the whole point is not depending on
    anyone remembering to run it."""
    db = SessionLocal()
    try:
        settings = get_settings()
        fired = run_due_suites(
            db,
            grader=get_judge_grader(),
            sut=get_sut_adapter(),
            judge_model_version=settings.judge_model,
        )
        if fired:
            logger.info("scheduler tick fired %d run(s)", len(fired))
        check_coverage_gaps_due(db, date.today())
    except Exception:
        # A tick that raises must not take down the whole scheduler — the
        # next tick should still fire.
        logger.exception("scheduler tick failed")
    finally:
        db.close()


def start_scheduler(tick_interval_seconds: int) -> BackgroundScheduler:
    global _scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _run_tick, "interval", seconds=tick_interval_seconds, id="aegis-measure-tick"
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info("scheduler started (tick every %ss)", tick_interval_seconds)
    return scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
