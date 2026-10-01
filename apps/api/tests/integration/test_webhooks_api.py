from app.api.deps import get_judge_grader, get_sut_adapter
from app.main import app
from app.services.grading.llm_judge import LLMJudgeGrader


class _StubJudgeProvider:
    def grade_dimensions(self, *, dimensions: list[dict], **_: object):
        return {d["key"]: {"passed": True, "rationale": "stub"} for d in dimensions}


class _StubSUT:
    def answer(self, question: str) -> dict:
        return {"answer": "a", "retrieved_context": "c"}

    def answer_with_context(self, question: str, context: str) -> dict:
        return {"answer": "a"}


def _approve_case(client, suite_id) -> None:
    case = client.post(
        "/cases", json={"suite_id": suite_id, "question": "q", "source": "manual"}
    ).json()
    client.post(
        f"/cases/{case['id']}/reviews", json={"reviewer_name": "A", "proposed_answer": "ans"}
    )
    client.post(
        f"/cases/{case['id']}/reviews", json={"reviewer_name": "B", "proposed_answer": "ans"}
    )
    client.post(
        f"/cases/{case['id']}/resolve",
        json={"decision": "approve", "resolved_by": "V", "reference_answer": "ans"},
    )


def test_on_change_webhook_triggers_every_suite_when_no_suite_id_given(client):
    suite_a = client.post("/suites", json={"name": "suite-a-on-change"}).json()
    suite_b = client.post("/suites", json={"name": "suite-b-on-change"}).json()
    _approve_case(client, suite_a["id"])
    _approve_case(client, suite_b["id"])

    app.dependency_overrides[get_judge_grader] = lambda: LLMJudgeGrader(_StubJudgeProvider())
    app.dependency_overrides[get_sut_adapter] = lambda: _StubSUT()

    resp = client.post("/webhooks/on-change", json={})
    assert resp.status_code == 201
    body = resp.json()
    triggered_suite_ids = {r["suite_id"] for r in body["triggered"]}
    assert suite_a["id"] in triggered_suite_ids
    assert suite_b["id"] in triggered_suite_ids
    assert body["skipped_suite_ids"] == []


def test_on_change_webhook_scoped_to_one_suite(client):
    suite = client.post("/suites", json={"name": "suite-scoped-on-change"}).json()
    _approve_case(client, suite["id"])

    app.dependency_overrides[get_judge_grader] = lambda: LLMJudgeGrader(_StubJudgeProvider())
    app.dependency_overrides[get_sut_adapter] = lambda: _StubSUT()

    resp = client.post("/webhooks/on-change", json={"suite_id": suite["id"]})
    assert resp.status_code == 201
    body = resp.json()
    assert len(body["triggered"]) == 1
    assert body["triggered"][0]["suite_id"] == suite["id"]
