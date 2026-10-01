import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import CaseStatus
from app.models.golden_case import GoldenCase
from app.schemas.golden_case import GoldenCaseCreate
from app.services.errors import ConflictError, NotFoundError
from app.services.suite_service import get_suite


def create_case(db: Session, data: GoldenCaseCreate) -> GoldenCase:
    # Raises NotFoundError if the suite doesn't exist — fail fast rather than
    # creating an orphaned case.
    get_suite(db, data.suite_id)

    case = GoldenCase(
        suite_id=data.suite_id,
        question=data.question,
        context=data.context,
        source=data.source,
        check_mode=data.check_mode,
        tags=data.tags,
        rubric_id=data.rubric_id,
        status=CaseStatus.DRAFT,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


def get_case(db: Session, case_id: uuid.UUID) -> GoldenCase:
    case = db.get(GoldenCase, case_id)
    if case is None:
        raise NotFoundError(f"Case {case_id} not found")
    return case


def list_cases(
    db: Session, suite_id: uuid.UUID | None = None, status: CaseStatus | None = None
) -> list[GoldenCase]:
    stmt = select(GoldenCase).order_by(GoldenCase.created_at)
    if suite_id is not None:
        stmt = stmt.where(GoldenCase.suite_id == suite_id)
    if status is not None:
        stmt = stmt.where(GoldenCase.status == status)
    return list(db.execute(stmt).scalars())


def retire_case(db: Session, case_id: uuid.UUID) -> GoldenCase:
    case = get_case(db, case_id)
    if case.status != CaseStatus.APPROVED:
        raise ConflictError(
            f"Only an approved case can be retired (case is {case.status.value})"
        )
    case.status = CaseStatus.RETIRED
    db.commit()
    db.refresh(case)
    return case
