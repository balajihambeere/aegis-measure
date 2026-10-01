import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db.session import get_db
from app.main import app


@pytest.fixture
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app, headers={"X-API-Key": get_settings().aegis_api_key})
    app.dependency_overrides.clear()
