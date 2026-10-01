def test_metrics_endpoint_requires_auth(client):
    from fastapi.testclient import TestClient

    unauthenticated = TestClient(client.app)
    resp = unauthenticated.get("/metrics")
    assert resp.status_code == 401


def test_metrics_endpoint_reports_run_counts_and_pass_rate(client):
    suite = client.post("/suites", json={"name": "metrics-test-suite"}).json()
    case = client.post(
        "/cases",
        json={"suite_id": suite["id"], "question": "q", "source": "manual"},
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

    from app.api.deps import get_judge_grader, get_sut_adapter
    from app.main import app
    from app.services.grading.llm_judge import LLMJudgeGrader

    class _PassJudgeProvider:
        def grade_dimensions(self, *, dimensions, **_):
            return {d["key"]: {"passed": True, "rationale": "x"} for d in dimensions}

    class _StubSUT:
        def answer(self, question):
            return {"answer": "a", "retrieved_context": "c"}

        def answer_with_context(self, question, context):
            return {"answer": "a"}

    app.dependency_overrides[get_judge_grader] = lambda: LLMJudgeGrader(_PassJudgeProvider())
    app.dependency_overrides[get_sut_adapter] = lambda: _StubSUT()

    client.post("/runs", json={"suite_id": suite["id"]})

    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "aegis_eval_runs_total" in resp.text
    assert f'suite="{suite["name"]}"' in resp.text
    assert "aegis_suite_latest_pass_rate" in resp.text
