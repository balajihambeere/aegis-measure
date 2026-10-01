from fastapi.testclient import TestClient

from app.deps import get_answer_generator
from app.main import app


class _FakeGenerator:
    def __init__(self, response: str = "fake answer", raise_missing_key: bool = False):
        self._response = response
        self._raise_missing_key = raise_missing_key

    def generate(self, *, question: str, context: str) -> str:
        if self._raise_missing_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured")
        return f"{self._response} (saw context: {context[:20]}...)"


def _client_with_generator(generator) -> TestClient:
    app.dependency_overrides[get_answer_generator] = lambda: generator
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_answer_with_context_skips_retrieval_and_uses_given_context():
    client = _client_with_generator(_FakeGenerator())
    resp = client.post(
        "/answer_with_context",
        json={"question": "Dry clean?", "context": "SKU X — pure silk, dry clean only."},
    )
    assert resp.status_code == 200
    assert "SKU X" in resp.json()["answer"]


def test_answer_retrieves_its_own_context():
    client = _client_with_generator(_FakeGenerator())
    resp = client.post("/answer", json={"question": "Does SKU BPS-2214 need dry cleaning?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["retrieved_sku"] == "BPS-2214"
    assert "BPS-2214" in body["retrieved_context"]


def test_answer_returns_503_when_generator_is_unavailable():
    client = _client_with_generator(_FakeGenerator(raise_missing_key=True))
    resp = client.post("/answer", json={"question": "Does SKU BPS-2214 need dry cleaning?"})
    assert resp.status_code == 503
