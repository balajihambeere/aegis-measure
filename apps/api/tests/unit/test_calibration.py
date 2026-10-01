"""'Does the judge's verdict match a human's, on cases we already know the
real answer to' — calibration runs this check and gates on it."""

import uuid

import pytest

from app.models.calibration import HumanLabeledSample
from app.models.golden_case import GoldenCase
from app.models.rubric import Rubric
from app.models.suite import Suite
from app.services.calibration_service import is_calibrated, require_calibrated, run_calibration
from app.services.errors import ConflictError
from app.services.grading.llm_judge import LLMJudgeGrader


class _TableJudgeProvider:
    """Stands in for a real Claude call: looks up a scripted verdict by the
    exact candidate answer text."""

    def __init__(self, verdict_by_answer: dict[str, bool]):
        self._table = verdict_by_answer

    def grade_dimensions(self, *, candidate_answer: str, dimensions: list[dict], **_: object):
        passed = self._table[candidate_answer]
        return {d["key"]: {"passed": passed, "rationale": "stub"} for d in dimensions}


def _case_with_samples(db_session, samples: list[tuple[str, bool]]):
    rubric = Rubric(
        name=f"rubric-{uuid.uuid4()}", dimensions=[{"key": "core_fact_correct", "description": "x"}]
    )
    db_session.add(rubric)
    db_session.flush()

    suite = Suite(name=f"calib-suite-{uuid.uuid4()}")
    db_session.add(suite)
    db_session.flush()

    case = GoldenCase(
        suite_id=suite.id,
        rubric_id=rubric.id,
        question="q",
        context="c",
        reference_answer="r",
        source="manual",
    )
    db_session.add(case)
    db_session.flush()

    for candidate, human_verdict in samples:
        db_session.add(
            HumanLabeledSample(
                case_id=case.id,
                candidate_answer=candidate,
                human_verdict=human_verdict,
                labeled_by="Vyasa",
            )
        )
    db_session.flush()
    return rubric, case


def test_run_calibration_computes_agreement_rate_and_records_disagreements(db_session):
    rubric, _ = _case_with_samples(
        db_session,
        [("good answer", True), ("bad answer", False), ("tricky answer", False)],
    )
    # Judge agrees on the first two, wrongly says "passed" on the third.
    grader = LLMJudgeGrader(
        _TableJudgeProvider({"good answer": True, "bad answer": False, "tricky answer": True})
    )

    run = run_calibration(
        db_session,
        rubric_id=rubric.id,
        judge_model_version="test-model",
        grader=grader,
        threshold=0.9,
    )

    assert run.sample_size == 3
    assert run.agreement_count == 2
    assert run.agreement_rate == pytest.approx(2 / 3)
    assert run.passed_threshold is False  # 0.667 < 0.9 threshold
    assert len(run.disagreements) == 1


def test_calibration_gate_blocks_scheduled_use_until_threshold_met(db_session):
    rubric, _ = _case_with_samples(db_session, [("a", True), ("b", True)])
    grader = LLMJudgeGrader(_TableJudgeProvider({"a": True, "b": True}))

    assert is_calibrated(db_session, rubric.id, "test-model") is False
    with pytest.raises(ConflictError):
        require_calibrated(db_session, rubric.id, "test-model")

    run_calibration(
        db_session,
        rubric_id=rubric.id,
        judge_model_version="test-model",
        grader=grader,
        threshold=0.9,
    )

    assert is_calibrated(db_session, rubric.id, "test-model") is True
    require_calibrated(db_session, rubric.id, "test-model")  # must not raise


def test_a_new_judge_model_is_uncalibrated_even_if_an_old_one_passed(db_session):
    """Re-calibrate whenever the judge model changes."""
    rubric, _ = _case_with_samples(db_session, [("a", True)])
    grader = LLMJudgeGrader(_TableJudgeProvider({"a": True}))
    run_calibration(
        db_session,
        rubric_id=rubric.id,
        judge_model_version="old-model",
        grader=grader,
        threshold=0.5,
    )

    assert is_calibrated(db_session, rubric.id, "old-model") is True
    assert is_calibrated(db_session, rubric.id, "new-model") is False


def test_run_calibration_requires_at_least_one_sample(db_session):
    rubric = Rubric(name=f"empty-{uuid.uuid4()}", dimensions=[{"key": "x", "description": "x"}])
    db_session.add(rubric)
    db_session.flush()
    grader = LLMJudgeGrader(_TableJudgeProvider({}))

    with pytest.raises(ConflictError):
        run_calibration(
            db_session, rubric_id=rubric.id, judge_model_version="m", grader=grader, threshold=0.9
        )
