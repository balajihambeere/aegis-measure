import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.suite import SuiteCreate, SuiteRead
from app.services import suite_service

router = APIRouter(prefix="/suites", tags=["suites"])


@router.post("", response_model=SuiteRead, status_code=201)
def create_suite(data: SuiteCreate, db: Session = Depends(get_db)) -> SuiteRead:
    suite = suite_service.create_suite(db, data)
    return SuiteRead.model_validate(suite)


@router.get("", response_model=list[SuiteRead])
def list_suites(db: Session = Depends(get_db)) -> list[SuiteRead]:
    return [SuiteRead.model_validate(s) for s in suite_service.list_suites(db)]


@router.get("/{suite_id}", response_model=SuiteRead)
def get_suite(suite_id: uuid.UUID, db: Session = Depends(get_db)) -> SuiteRead:
    suite = suite_service.get_suite(db, suite_id)
    return SuiteRead.model_validate(suite)
