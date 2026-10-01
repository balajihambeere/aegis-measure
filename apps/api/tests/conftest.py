import os
import re
from urllib.parse import urlsplit, urlunsplit

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base

# Tests run against a real Postgres (enum/JSON columns aren't meaningfully
# testable against SQLite) — either the one started by `docker compose up
# postgres`, or whatever DATABASE_URL the environment provides (CI sets this
# to the postgres service container).
BASE_DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://aegis:aegis@localhost:55433/aegis"
)


def _test_database_url(base_url: str) -> str:
    """Tests get their OWN database (name + '_test'), never the dev/
    migration-managed one. (An earlier version of this fixture ran
    Base.metadata.drop_all() straight against the dev database at session
    teardown, silently wiping every table Alembic had just created —
    discovered when a later `alembic upgrade head` found an empty schema
    but a stamped alembic_version. Isolating the database entirely removes
    the failure mode instead of just patching that one symptom.)"""
    parts = urlsplit(base_url)
    test_db_name = parts.path.lstrip("/") + "_test"
    if not re.fullmatch(r"[A-Za-z0-9_]+", test_db_name):
        raise ValueError(f"Unexpected database name in {base_url!r}: {test_db_name!r}")
    return urlunsplit((parts.scheme, parts.netloc, f"/{test_db_name}", parts.query, parts.fragment))


TEST_DATABASE_URL = _test_database_url(BASE_DATABASE_URL)


def _ensure_test_database_exists() -> None:
    test_db_name = urlsplit(TEST_DATABASE_URL).path.lstrip("/")
    admin_parts = urlsplit(BASE_DATABASE_URL)
    admin_url = urlunsplit((admin_parts.scheme, admin_parts.netloc, "/postgres", "", ""))

    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": test_db_name},
            ).first()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{test_db_name}"'))
    finally:
        admin_engine.dispose()


@pytest.fixture(scope="session")
def engine():
    _ensure_test_database_exists()
    eng = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    # join_transaction_mode="create_savepoint": the Session runs inside a
    # SAVEPOINT, so a test calling session.commit()/.rollback() (e.g. to
    # recover after an expected IntegrityError) doesn't end the outer
    # transaction this fixture uses to isolate/roll back each test.
    SessionLocal = sessionmaker(bind=connection, join_transaction_mode="create_savepoint")
    session: Session = SessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()
