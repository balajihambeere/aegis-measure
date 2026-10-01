import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.coverage import LaunchCoverageCheckCreate, LaunchCoverageCheckRead
from app.services import coverage_service

router = APIRouter(prefix="/coverage-checks", tags=["coverage"])


@router.post("", response_model=LaunchCoverageCheckRead, status_code=201)
def create_coverage_check(
    data: LaunchCoverageCheckCreate, db: Session = Depends(get_db)
) -> LaunchCoverageCheckRead:
    check = coverage_service.create_coverage_check(db, data)
    return LaunchCoverageCheckRead.model_validate(check)


@router.get("", response_model=list[LaunchCoverageCheckRead])
def list_coverage_checks(db: Session = Depends(get_db)) -> list[LaunchCoverageCheckRead]:
    return [
        LaunchCoverageCheckRead.model_validate(c)
        for c in coverage_service.list_coverage_checks(db)
    ]


@router.get("/{check_id}", response_model=LaunchCoverageCheckRead)
def get_coverage_check(
    check_id: uuid.UUID, db: Session = Depends(get_db)
) -> LaunchCoverageCheckRead:
    check = coverage_service.get_coverage_check(db, check_id)
    return LaunchCoverageCheckRead.model_validate(check)


@router.post("/{check_id}/complete-re-review", response_model=LaunchCoverageCheckRead)
def complete_re_review(
    check_id: uuid.UUID, db: Session = Depends(get_db)
) -> LaunchCoverageCheckRead:
    check = coverage_service.complete_re_review(db, check_id)
    return LaunchCoverageCheckRead.model_validate(check)
