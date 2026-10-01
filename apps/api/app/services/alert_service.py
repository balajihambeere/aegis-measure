import logging
import uuid
from datetime import date

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.alert import Alert
from app.models.common import utcnow
from app.models.enums import AlertType
from app.models.eval_run import CaseResult, EvalRun
from app.models.golden_case import GoldenCase
from app.services.calibration_service import is_calibrated
from app.services.coverage_service import list_overdue_re_reviews
from app.services.errors import NotFoundError

logger = logging.getLogger("aegis")

# A pass-rate drop this large is worth a human looking at, even if no single
# case's verdict flipped in isolation (e.g. several borderline cases
# degrading at once).
PASS_RATE_DROP_THRESHOLD = 0.1


def _deliver_webhook(message: str) -> None:
    url = get_settings().alert_webhook_url
    if not url:
        return
    try:
        httpx.post(url, json={"text": message}, timeout=5.0)
    except httpx.HTTPError:
        # Best-effort: a failed notification must never fail the eval run
        # that triggered it.
        logger.warning("alert webhook delivery failed", exc_info=True)


def create_alert(
    db: Session,
    *,
    alert_type: AlertType,
    message: str,
    suite_id: uuid.UUID | None = None,
    run_id: uuid.UUID | None = None,
) -> Alert:
    alert = Alert(suite_id=suite_id, run_id=run_id, alert_type=alert_type, message=message)
    db.add(alert)
    db.commit()
    db.refresh(alert)
    _deliver_webhook(message)
    return alert


def list_alerts(
    db: Session, suite_id: uuid.UUID | None = None, unacknowledged_only: bool = False
) -> list[Alert]:
    stmt = select(Alert).order_by(Alert.created_at.desc())
    if suite_id is not None:
        stmt = stmt.where(Alert.suite_id == suite_id)
    if unacknowledged_only:
        stmt = stmt.where(Alert.acknowledged_at.is_(None))
    return list(db.execute(stmt).scalars())


def acknowledge_alert(db: Session, alert_id: uuid.UUID) -> Alert:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise NotFoundError(f"Alert {alert_id} not found")
    alert.acknowledged_at = utcnow()
    db.commit()
    db.refresh(alert)
    return alert


def _has_unacknowledged_alert(db: Session, suite_id: uuid.UUID, alert_type: AlertType) -> bool:
    return (
        db.execute(
            select(Alert.id).where(
                Alert.suite_id == suite_id,
                Alert.alert_type == alert_type,
                Alert.acknowledged_at.is_(None),
            )
        ).first()
        is not None
    )


def check_for_new_failures(db: Session, run: EvalRun) -> None:
    """A case that passed last time and fails this time is exactly the kind
    of thing continuous scheduling exists to catch within hours instead of
    whenever someone happens to notice."""
    previous_run = db.execute(
        select(EvalRun)
        .where(
            EvalRun.suite_id == run.suite_id,
            EvalRun.id != run.id,
            EvalRun.started_at < run.started_at,
        )
        .order_by(EvalRun.started_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if previous_run is None:
        return

    previous_results = {
        (r.case_id, r.check_mode): r.passed
        for r in db.execute(
            select(CaseResult).where(CaseResult.run_id == previous_run.id)
        ).scalars()
    }
    current_results = db.execute(
        select(CaseResult).where(CaseResult.run_id == run.id)
    ).scalars()

    for result in current_results:
        previously_passed = previous_results.get((result.case_id, result.check_mode))
        if previously_passed is True and result.passed is False:
            case = db.get(GoldenCase, result.case_id)
            question = case.question if case else str(result.case_id)
            create_alert(
                db,
                alert_type=AlertType.NEW_FAILURE,
                suite_id=run.suite_id,
                run_id=run.id,
                message=(
                    f"New failure on {result.check_mode.value} check: '{question}' passed "
                    f"on the previous run and now fails."
                ),
            )


def check_for_pass_rate_drop(db: Session, run: EvalRun) -> None:
    previous_run = db.execute(
        select(EvalRun)
        .where(
            EvalRun.suite_id == run.suite_id,
            EvalRun.id != run.id,
            EvalRun.started_at < run.started_at,
        )
        .order_by(EvalRun.started_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if previous_run is None:
        return

    def _pass_rate(run_id: uuid.UUID) -> float | None:
        results = list(db.execute(select(CaseResult).where(CaseResult.run_id == run_id)).scalars())
        if not results:
            return None
        return sum(1 for r in results if r.passed) / len(results)

    current_rate = _pass_rate(run.id)
    previous_rate = _pass_rate(previous_run.id)
    if current_rate is None or previous_rate is None:
        return

    drop = previous_rate - current_rate
    if drop >= PASS_RATE_DROP_THRESHOLD:
        create_alert(
            db,
            alert_type=AlertType.PASS_RATE_DROP,
            suite_id=run.suite_id,
            run_id=run.id,
            message=(
                f"Pass rate dropped from {previous_rate:.0%} to {current_rate:.0%} "
                f"(suite {run.suite_id})."
            ),
        )


def check_calibration_staleness(db: Session, run: EvalRun) -> None:
    """The day a judge's verdicts stop matching human judgment is the day
    its number stops meaning what it claims to mean — surfaced as a standing
    alert rather than blocking the run outright, so a measurement still
    happens even while trust in it is flagged."""
    if _has_unacknowledged_alert(db, run.suite_id, AlertType.CALIBRATION_STALE):
        return

    rubric_ids = {
        rubric_id
        for rubric_id in db.execute(
            select(GoldenCase.rubric_id).where(
                GoldenCase.suite_id == run.suite_id, GoldenCase.rubric_id.is_not(None)
            )
        ).scalars()
        if rubric_id is not None
    }
    for rubric_id in rubric_ids:
        if not is_calibrated(db, rubric_id, run.judge_model_version):
            create_alert(
                db,
                alert_type=AlertType.CALIBRATION_STALE,
                suite_id=run.suite_id,
                run_id=run.id,
                message=(
                    f"Rubric {rubric_id} is not calibrated for judge model "
                    f"'{run.judge_model_version}' — results from this suite "
                    "should not be trusted until it is."
                ),
            )
            return  # one standing alert per suite is enough


def check_coverage_gaps_due(db: Session, today: date) -> None:
    """A disclosed gap with a promised re-review date that's arrived and
    wasn't closed — the exact thing that honest disclosure is supposed to
    prevent from being quietly forgotten."""
    for check in list_overdue_re_reviews(db, today):
        if check.linked_suite_id is not None and _has_unacknowledged_alert(
            db, check.linked_suite_id, AlertType.COVERAGE_GAP_DUE
        ):
            continue
        create_alert(
            db,
            alert_type=AlertType.COVERAGE_GAP_DUE,
            suite_id=check.linked_suite_id,
            message=(
                f"Re-review for '{check.feature_name}' was due {check.re_review_due_at} "
                "and hasn't been completed."
            ),
        )
