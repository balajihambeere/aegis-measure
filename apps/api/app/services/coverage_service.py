import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.common import utcnow
from app.models.coverage import LaunchCoverageCheck
from app.schemas.coverage import LaunchCoverageCheckCreate
from app.services.errors import ConflictError, NotFoundError


def create_coverage_check(db: Session, data: LaunchCoverageCheckCreate) -> LaunchCoverageCheck:
    """'If this broke silently, who would notice, and when?' — a launch
    doesn't ship without someone answering this, in writing, with any gaps
    named explicitly rather than discovered by accident."""
    check = LaunchCoverageCheck(
        feature_name=data.feature_name,
        launch_date=data.launch_date,
        linked_suite_id=data.linked_suite_id,
        declared_gaps=data.declared_gaps,
        coverage_status=data.coverage_status,
        answered_by=data.answered_by,
        answered_at=utcnow(),
        re_review_due_at=data.re_review_due_at,
    )
    db.add(check)
    db.commit()
    db.refresh(check)
    return check


def get_coverage_check(db: Session, check_id: uuid.UUID) -> LaunchCoverageCheck:
    check = db.get(LaunchCoverageCheck, check_id)
    if check is None:
        raise NotFoundError(f"LaunchCoverageCheck {check_id} not found")
    return check


def list_coverage_checks(db: Session) -> list[LaunchCoverageCheck]:
    return list(
        db.execute(select(LaunchCoverageCheck).order_by(LaunchCoverageCheck.launch_date.desc()))
        .scalars()
    )


def complete_re_review(db: Session, check_id: uuid.UUID) -> LaunchCoverageCheck:
    """Closes a disclosed gap with an actual follow-up review, rather than
    quietly forgetting it once the deadline pressure that caused it passes."""
    check = get_coverage_check(db, check_id)
    if check.re_review_due_at is None:
        raise ConflictError(f"LaunchCoverageCheck {check_id} has no re-review scheduled")
    if check.re_review_completed_at is not None:
        raise ConflictError(f"LaunchCoverageCheck {check_id} re-review is already complete")
    check.re_review_completed_at = utcnow()
    db.commit()
    db.refresh(check)
    return check


def list_overdue_re_reviews(db: Session, today: date) -> list[LaunchCoverageCheck]:
    return list(
        db.execute(
            select(LaunchCoverageCheck).where(
                LaunchCoverageCheck.re_review_due_at.is_not(None),
                LaunchCoverageCheck.re_review_due_at <= today,
                LaunchCoverageCheck.re_review_completed_at.is_(None),
            )
        ).scalars()
    )
