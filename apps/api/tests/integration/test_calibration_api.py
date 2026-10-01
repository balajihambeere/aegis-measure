from app.api.deps import get_judge_grader
from app.main import app
from app.services.grading.llm_judge import LLMJudgeGrader


class _TableJudgeProvider:
    def __init__(self, verdict_by_answer: dict[str, bool]):
        self._table = verdict_by_answer

    def grade_dimensions(self, *, candidate_answer: str, dimensions: list[dict], **_: object):
        passed = self._table[candidate_answer]
        return {d["key"]: {"passed": passed, "rationale": "stub"} for d in dimensions}


def _override_grader(client, verdict_by_answer):
    app.dependency_overrides[get_judge_grader] = lambda: LLMJudgeGrader(
        _TableJudgeProvider(verdict_by_answer)
    )


def test_calibration_run_end_to_end_through_the_api(client):
    rubric = client.post(
        "/rubrics",
        json={
            "name": "product-answer-rubric",
            "dimensions": [{"key": "core_fact_correct", "description": "states the fact"}],
        },
    ).json()

    suite = client.post("/suites", json={"name": "fabric-and-care"}).json()
    case = client.post(
        "/cases",
        json={
            "suite_id": suite["id"],
            "question": "Does this need dry cleaning?",
            "context": "Pure silk listing.",
            "source": "manual",
            "rubric_id": rubric["id"],
        },
    ).json()

    # Reviewers approve it so it has a reference_answer, as calibration grades
    # candidate answers against the case's reference answer.
    client.post(
        f"/cases/{case['id']}/reviews",
        json={"reviewer_name": "Chitrangada", "proposed_answer": "Pure silk — dry clean only."},
    )
    client.post(
        f"/cases/{case['id']}/reviews",
        json={"reviewer_name": "merchandising-lead", "proposed_answer": "Dry clean only, silk."},
    )
    client.post(
        f"/cases/{case['id']}/resolve",
        json={
            "decision": "approve",
            "resolved_by": "Vyasa",
            "reference_answer": "Pure silk — dry clean only.",
        },
    )

    sample_correct = client.post(
        "/human-labeled-samples",
        json={
            "case_id": case["id"],
            "candidate_answer": "Pure silk, dry clean only.",
            "human_verdict": True,
            "labeled_by": "Vyasa",
        },
    )
    assert sample_correct.status_code == 201

    sample_wrong = client.post(
        "/human-labeled-samples",
        json={
            "case_id": case["id"],
            "candidate_answer": "Machine wash cold is fine.",
            "human_verdict": False,
            "labeled_by": "Vyasa",
        },
    )
    assert sample_wrong.status_code == 201

    _override_grader(
        client,
        {"Pure silk, dry clean only.": True, "Machine wash cold is fine.": False},
    )

    run = client.post(
        "/calibration-runs",
        json={"rubric_id": rubric["id"], "judge_model_version": "test-model-v1", "threshold": 0.9},
    )
    assert run.status_code == 201
    body = run.json()
    assert body["sample_size"] == 2
    assert body["agreement_count"] == 2
    assert body["passed_threshold"] is True

    listed = client.get("/calibration-runs", params={"rubric_id": rubric["id"]}).json()
    assert len(listed) == 1


def test_creating_a_rubric_with_a_duplicate_name_returns_409_not_500(client):
    body = {"name": "duplicate-rubric-name", "dimensions": [{"key": "x", "description": "x"}]}
    client.post("/rubrics", json=body)
    resp = client.post("/rubrics", json=body)
    assert resp.status_code == 409


def test_calibration_run_for_rubric_with_no_samples_returns_409(client):
    rubric = client.post(
        "/rubrics",
        json={"name": "unused-rubric", "dimensions": [{"key": "x", "description": "x"}]},
    ).json()
    _override_grader(client, {})

    run = client.post(
        "/calibration-runs",
        json={"rubric_id": rubric["id"], "judge_model_version": "test-model-v1"},
    )
    assert run.status_code == 409
