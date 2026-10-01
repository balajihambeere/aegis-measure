import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.rubric import RubricCreate, RubricRead
from app.services import rubric_service

router = APIRouter(prefix="/rubrics", tags=["rubrics"])


@router.post("", response_model=RubricRead, status_code=201)
def create_rubric(data: RubricCreate, db: Session = Depends(get_db)) -> RubricRead:
    rubric = rubric_service.create_rubric(db, data)
    return RubricRead.model_validate(rubric)


@router.get("", response_model=list[RubricRead])
def list_rubrics(db: Session = Depends(get_db)) -> list[RubricRead]:
    return [RubricRead.model_validate(r) for r in rubric_service.list_rubrics(db)]


@router.get("/{rubric_id}", response_model=RubricRead)
def get_rubric(rubric_id: uuid.UUID, db: Session = Depends(get_db)) -> RubricRead:
    rubric = rubric_service.get_rubric(db, rubric_id)
    return RubricRead.model_validate(rubric)
