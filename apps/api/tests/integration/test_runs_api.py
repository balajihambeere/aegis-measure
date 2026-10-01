from app.api.deps import get_judge_grader, get_sut_adapter
from app.main import app
from app.services.grading.llm_judge import LLMJudgeGrader


class _TableJudgeProvider:
    def __init__(self, verdict_by_answer: dict[str, bool]):
        self._table = verdict_by_answer

    def grade_dimensions(self, *, candidate_answer: str, dimensions: list[dict], **_: object):
        passed = self._table[candidate_answer]
        return {d["key"]: {"passed": passed, "rationale": "stub"} for d in dimensions}


class _FixedAnswerSUT:
    def __init__(self, component_answer: str, e2e_answer: str, e2e_context: str = "ctx"):
        self._component_answer = component_answer
        self._e2e_answer = e2e_answer
        self._e2e_context = e2e_context

    def answer(self, question: str) -> dict:
        return {"answer": self._e2e_answer, "retrieved_context": self._e2e_context}

    def answer_with_context(self, question: str, context: str) -> dict:
        return {"answer": self._component_answer}


def _approve_case(client, suite_id, question, context, reference_answer) -> str:
    case = client.post(
        "/cases",
        json={
            "suite_id": suite_id,
            "question": question,
            "context": context,
            "source": "real_complaint",
        },
    ).json()
    client.post(
        f"/cases/{case['id']}/reviews",
        json={"reviewer_name": "Chitrangada", "proposed_answer": reference_answer},
    )
    client.post(
        f"/cases/{case['id']}/reviews",
        json={"reviewer_name": "merchandising-lead", "proposed_answer": reference_answer},
    )
    client.post(
        f"/cases/{case['id']}/resolve",
        json={"decision": "approve", "resolved_by": "Vyasa", "reference_answer": reference_answer},
    )
    return case["id"]


def test_triggering_a_run_through_the_api_grades_every_approved_case(client):
    suite = client.post("/suites", json={"name": "fabric-and-care-run-test"}).json()
    _approve_case(
        client,
        suite["id"],
        question="Does this need dry cleaning?",
        context="Pure silk listing.",
        reference_answer="Pure silk — dry clean only.",
    )

    app.dependency_overrides[get_judge_grader] = lambda: LLMJudgeGrader(
        _TableJudgeProvider({"Pure silk — dry clean only.": True})
    )
    app.dependency_overrides[get_sut_adapter] = lambda: _FixedAnswerSUT(
        component_answer="Pure silk — dry clean only.",
        e2e_answer="Pure silk — dry clean only.",
        e2e_context="Pure silk listing.",
    )

    run_resp = client.post("/runs", json={"suite_id": suite["id"], "trigger_source": "manual"})
    assert run_resp.status_code == 201
    run = run_resp.json()
    assert run["status"] == "completed"

    results = client.get(f"/runs/{run['id']}/results").json()
    assert len(results) == 2  # component + end_to_end, since default check_mode is BOTH
    assert all(r["passed"] for r in results)


def test_get_run_for_unknown_id_returns_404(client):
    import uuid

    resp = client.get(f"/runs/{uuid.uuid4()}")
    assert resp.status_code == 404
