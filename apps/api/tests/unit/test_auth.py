from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_needs_no_api_key():
    assert client.get("/health").status_code == 200


def test_protected_endpoint_without_key_is_rejected():
    resp = client.get("/suites")
    assert resp.status_code == 401


def test_protected_endpoint_with_wrong_key_is_rejected():
    resp = client.get("/suites", headers={"X-API-Key": "wrong-key"})
    assert resp.status_code == 401
