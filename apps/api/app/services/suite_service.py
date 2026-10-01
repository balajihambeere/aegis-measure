import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.suite import Suite
from app.schemas.suite import SuiteCreate
from app.services.errors import ConflictError, NotFoundError


def create_suite(db: Session, data: SuiteCreate) -> Suite:
    if db.execute(select(Suite.id).where(Suite.name == data.name)).first():
        raise ConflictError(f"A suite named '{data.name}' already exists")
    suite = Suite(
        name=data.name,
        description=data.description,
        default_schedule_interval_hours=data.default_schedule_interval_hours,
    )
    db.add(suite)
    db.commit()
    db.refresh(suite)
    return suite


def list_suites(db: Session) -> list[Suite]:
    return list(db.execute(select(Suite).order_by(Suite.name)).scalars())


def get_suite(db: Session, suite_id: uuid.UUID) -> Suite:
    suite = db.get(Suite, suite_id)
    if suite is None:
        raise NotFoundError(f"Suite {suite_id} not found")
    return suite
