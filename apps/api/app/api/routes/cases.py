import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.enums import CaseStatus
from app.schemas.golden_case import (
    CaseResolutionRequest,
    GoldenCaseCreate,
    GoldenCaseRead,
    ReviewStatusRead,
    ReviewSubmissionCreate,
    ReviewSubmissionRead,
)
from app.services import case_service, review_service

router = APIRouter(prefix="/cases", tags=["golden-cases"])


@router.post("", response_model=GoldenCaseRead, status_code=201)
def create_case(data: GoldenCaseCreate, db: Session = Depends(get_db)) -> GoldenCaseRead:
    case = case_service.create_case(db, data)
    return GoldenCaseRead.model_validate(case)


@router.get("", response_model=list[GoldenCaseRead])
def list_cases(
    suite_id: uuid.UUID | None = None,
    status: CaseStatus | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[GoldenCaseRead]:
    cases = case_service.list_cases(db, suite_id=suite_id, status=status)
    return [GoldenCaseRead.model_validate(c) for c in cases]


@router.get("/{case_id}", response_model=GoldenCaseRead)
def get_case(case_id: uuid.UUID, db: Session = Depends(get_db)) -> GoldenCaseRead:
    case = case_service.get_case(db, case_id)
    return GoldenCaseRead.model_validate(case)


@router.post("/{case_id}/retire", response_model=GoldenCaseRead)
def retire_case(case_id: uuid.UUID, db: Session = Depends(get_db)) -> GoldenCaseRead:
    case = case_service.retire_case(db, case_id)
    return GoldenCaseRead.model_validate(case)


@router.post("/{case_id}/reviews", response_model=ReviewSubmissionRead, status_code=201)
def submit_review(
    case_id: uuid.UUID, data: ReviewSubmissionCreate, db: Session = Depends(get_db)
) -> ReviewSubmissionRead:
    submission = review_service.submit_review(db, case_id, data)
    return ReviewSubmissionRead.model_validate(submission)


@router.get("/{case_id}/reviews", response_model=ReviewStatusRead)
def get_review_status(case_id: uuid.UUID, db: Session = Depends(get_db)) -> ReviewStatusRead:
    """Blind by design: the proposed answers are withheld until both
    independent reviewers have submitted — see app.services.review_service."""
    return review_service.get_review_status(db, case_id)


@router.post("/{case_id}/resolve", response_model=GoldenCaseRead)
def resolve_case(
    case_id: uuid.UUID, data: CaseResolutionRequest, db: Session = Depends(get_db)
) -> GoldenCaseRead:
    case = review_service.resolve_case(db, case_id, data)
    return GoldenCaseRead.model_validate(case)
