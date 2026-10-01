import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.rubric import Rubric
from app.schemas.rubric import RubricCreate
from app.services.errors import ConflictError, NotFoundError


def create_rubric(db: Session, data: RubricCreate) -> Rubric:
    if db.execute(select(Rubric.id).where(Rubric.name == data.name)).first():
        raise ConflictError(f"A rubric named '{data.name}' already exists")
    rubric = Rubric(
        name=data.name,
        dimensions=[d.model_dump() for d in data.dimensions],
    )
    db.add(rubric)
    db.commit()
    db.refresh(rubric)
    return rubric


def list_rubrics(db: Session) -> list[Rubric]:
    return list(db.execute(select(Rubric).order_by(Rubric.name)).scalars())


def get_rubric(db: Session, rubric_id: uuid.UUID) -> Rubric:
    rubric = db.get(Rubric, rubric_id)
    if rubric is None:
        raise NotFoundError(f"Rubric {rubric_id} not found")
    return rubric
