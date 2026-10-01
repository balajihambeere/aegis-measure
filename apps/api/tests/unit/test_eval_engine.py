"""One run of the harness, executing approved cases against a system under
test and — where a case runs both check modes — localizing whether a
failure is a reasoning fault or an upstream retrieval fault."""

import uuid

import pytest

from app.models.enums import CaseStatus, CheckMode, Diagnosis, RunStatus, TriggerSource
from app.models.eval_run import EvalRun
from app.models.golden_case import GoldenCase
from app.models.suite import Suite
from app.services.errors import ConflictError
from app.services.eval_engine import list_case_results, run_eval
from app.services.grading.llm_judge import LLMJudgeGrader
from app.services.sut_adapter.base import SUTUnavailableError


class _TableJudgeProvider:
    def __init__(self, verdict_by_answer: dict[str, bool]):
        self._table = verdict_by_answer

    def grade_dimensions(self, *, candidate_answer: str, dimensions: list[dict], **_: object):
        passed = self._table[candidate_answer]
        return {d["key"]: {"passed": passed, "rationale": "stub"} for d in dimensions}


class _ScriptedSUT:
    """The component endpoint (given the right context) answers correctly;
    the end-to-end endpoint retrieves the WRONG near-duplicate listing and
    answers that one correctly instead."""

    def __init__(
        self,
        component_answer: str = "Hand-wash separately, colour may run.",
        e2e_answer: str = "Machine-wash cold.",
        e2e_context: str = "SKU DUP-3391: plain white dupatta, machine-wash cold.",
        raise_unavailable: bool = False,
    ):
        self._component_answer = component_answer
        self._e2e_answer = e2e_answer
        self._e2e_context = e2e_context
        self._raise_unavailable = raise_unavailable

    def answer(self, question: str) -> dict:
        if self._raise_unavailable:
            raise SUTUnavailableError("SUT down")
        return {"answer": self._e2e_answer, "retrieved_context": self._e2e_context}

    def answer_with_context(self, question: str, context: str) -> dict:
        if self._raise_unavailable:
            raise SUTUnavailableError("SUT down")
        return {"answer": self._component_answer}


def _suite_and_approved_case(db_session, check_mode=CheckMode.BOTH) -> tuple[Suite, GoldenCase]:
    suite = Suite(name=f"dupatta-care-{uuid.uuid4()}")
    db_session.add(suite)
    db_session.flush()

    case = GoldenCase(
        suite_id=suite.id,
        question="Does the teal dupatta need hand washing?",
        context="SKU DUP-3390: teal cotton dupatta, hand-wash separately, colour may run.",
        reference_answer="Hand-wash separately, colour may run.",
        source="real_complaint",
        check_mode=check_mode,
        status=CaseStatus.APPROVED,
    )
    db_session.add(case)
    db_session.flush()
    return suite, case


def test_run_eval_localizes_an_upstream_retrieval_fault(db_session):
    suite, case = _suite_and_approved_case(db_session)
    provider = _TableJudgeProvider(
        {"Hand-wash separately, colour may run.": True, "Machine-wash cold.": False}
    )
    grader = LLMJudgeGrader(provider)
    sut = _ScriptedSUT()

    run = run_eval(
        db_session,
        suite_id=suite.id,
        trigger_source=TriggerSource.SCHEDULE,
        grader=grader,
        sut=sut,
        judge_model_version="test-model",
    )

    assert run.status == RunStatus.COMPLETED
    results = {r.check_mode: r for r in list_case_results(db_session, run.id)}
    assert len(results) == 2
    assert results[CheckMode.COMPONENT].passed is True
    assert results[CheckMode.END_TO_END].passed is False
    assert results[CheckMode.END_TO_END].diagnosis == Diagnosis.UPSTREAM_RETRIEVAL_FAULT


def test_run_eval_tags_reasoning_fault_when_both_checks_fail(db_session):
    suite, case = _suite_and_approved_case(db_session)
    provider = _TableJudgeProvider(
        {"Hand-wash separately, colour may run.": False, "Machine-wash cold.": False}
    )
    grader = LLMJudgeGrader(provider)
    sut = _ScriptedSUT(component_answer="Hand-wash separately, colour may run.")

    run = run_eval(
        db_session,
        suite_id=suite.id,
        trigger_source=TriggerSource.MANUAL,
        grader=grader,
        sut=sut,
        judge_model_version="test-model",
    )

    results = {r.check_mode: r for r in list_case_results(db_session, run.id)}
    assert results[CheckMode.COMPONENT].passed is False
    assert results[CheckMode.END_TO_END].passed is False
    assert results[CheckMode.END_TO_END].diagnosis == Diagnosis.REASONING_FAULT


def test_run_eval_only_runs_approved_cases(db_session):
    suite = Suite(name=f"draft-suite-{uuid.uuid4()}")
    db_session.add(suite)
    db_session.flush()
    draft_case = GoldenCase(
        suite_id=suite.id, question="q", source="manual", status=CaseStatus.DRAFT
    )
    db_session.add(draft_case)
    db_session.flush()

    grader = LLMJudgeGrader(_TableJudgeProvider({}))
    run = run_eval(
        db_session,
        suite_id=suite.id,
        trigger_source=TriggerSource.MANUAL,
        grader=grader,
        sut=_ScriptedSUT(),
        judge_model_version="test-model",
    )

    assert run.status == RunStatus.COMPLETED
    assert list_case_results(db_session, run.id) == []


def test_run_eval_only_runs_the_cases_configured_check_mode(db_session):
    suite, case = _suite_and_approved_case(db_session, check_mode=CheckMode.COMPONENT)
    provider = _TableJudgeProvider({"Hand-wash separately, colour may run.": True})
    grader = LLMJudgeGrader(provider)

    run = run_eval(
        db_session,
        suite_id=suite.id,
        trigger_source=TriggerSource.MANUAL,
        grader=grader,
        sut=_ScriptedSUT(),
        judge_model_version="test-model",
    )

    results = list_case_results(db_session, run.id)
    assert len(results) == 1
    assert results[0].check_mode == CheckMode.COMPONENT
    assert results[0].diagnosis == Diagnosis.NONE


def test_run_eval_records_sut_unavailability_as_a_failed_result_without_erroring_the_run(
    db_session,
):
    """Production reliability: one unreachable SUT call fails that case's
    result, not the whole run."""
    suite, case = _suite_and_approved_case(db_session)
    grader = LLMJudgeGrader(_TableJudgeProvider({}))
    sut = _ScriptedSUT(raise_unavailable=True)

    run = run_eval(
        db_session,
        suite_id=suite.id,
        trigger_source=TriggerSource.MANUAL,
        grader=grader,
        sut=sut,
        judge_model_version="test-model",
    )

    assert run.status == RunStatus.COMPLETED
    results = list_case_results(db_session, run.id)
    assert len(results) == 2
    assert all(r.passed is False for r in results)
    assert all("error" in r.dimension_results for r in results)
    # Neither side got a real graded answer — don't misdiagnose this as a
    # reasoning fault just because both results happen to be "failed".
    end_to_end = next(r for r in results if r.check_mode == CheckMode.END_TO_END)
    assert end_to_end.diagnosis == Diagnosis.NONE


def test_run_eval_refuses_to_start_while_a_run_is_already_in_flight(db_session):
    """The on-change and scheduled triggers can both reach for the same
    suite — don't race two runs against the same cases."""
    suite, _ = _suite_and_approved_case(db_session)
    db_session.add(
        EvalRun(
            suite_id=suite.id,
            trigger_source=TriggerSource.SCHEDULE,
            judge_model_version="test-model",
            status=RunStatus.RUNNING,
        )
    )
    db_session.commit()

    with pytest.raises(ConflictError):
        run_eval(
            db_session,
            suite_id=suite.id,
            trigger_source=TriggerSource.ON_CHANGE,
            grader=LLMJudgeGrader(_TableJudgeProvider({})),
            sut=_ScriptedSUT(),
            judge_model_version="test-model",
        )
