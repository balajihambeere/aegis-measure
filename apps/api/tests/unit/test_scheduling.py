"""Two overlapping triggers — fixed-interval scheduling here, with a
tightened window for high-risk launches."""

import uuid
from datetime import UTC, datetime, timedelta

from app.models.enums import CaseStatus, RunStatus, TriggerSource
from app.models.eval_run import EvalRun
from app.models.golden_case import GoldenCase
from app.models.suite import ScheduleOverride, Suite
from app.services.eval_engine import list_case_results
from app.services.grading.llm_judge import LLMJudgeGrader
from app.services.scheduling.tick import is_suite_due, run_due_suites

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


class _StubJudgeProvider:
    def grade_dimensions(self, *, dimensions: list[dict], **_: object):
        return {d["key"]: {"passed": True, "rationale": "stub"} for d in dimensions}


class _StubSUT:
    def answer(self, question: str) -> dict:
        return {"answer": "a", "retrieved_context": "c"}

    def answer_with_context(self, question: str, context: str) -> dict:
        return {"answer": "a"}


def _suite(db_session, interval_hours: int = 6) -> Suite:
    suite = Suite(
        name=f"suite-{uuid.uuid4()}", default_schedule_interval_hours=interval_hours
    )
    db_session.add(suite)
    db_session.flush()
    return suite


def test_a_suite_with_no_prior_run_is_due_immediately(db_session):
    suite = _suite(db_session)
    assert is_suite_due(db_session, suite, NOW) is True


def test_a_suite_is_not_due_until_its_interval_elapses(db_session):
    suite = _suite(db_session, interval_hours=6)
    db_session.add(
        EvalRun(
            suite_id=suite.id,
            trigger_source=TriggerSource.SCHEDULE,
            judge_model_version="m",
            status=RunStatus.COMPLETED,
            started_at=NOW - timedelta(hours=3),
        )
    )
    db_session.flush()

    assert is_suite_due(db_session, suite, NOW) is False
    assert is_suite_due(db_session, suite, NOW + timedelta(hours=4)) is True


def test_an_active_schedule_override_tightens_the_interval(db_session):
    """Hourly checks during the festive sale window instead of the suite's
    normal 6-hour default."""
    suite = _suite(db_session, interval_hours=6)
    db_session.add(
        EvalRun(
            suite_id=suite.id,
            trigger_source=TriggerSource.SCHEDULE,
            judge_model_version="m",
            status=RunStatus.COMPLETED,
            started_at=NOW - timedelta(hours=2),
        )
    )
    db_session.add(
        ScheduleOverride(
            suite_id=suite.id,
            interval_hours=1,
            starts_at=NOW - timedelta(hours=1),
            ends_at=NOW + timedelta(days=4),
            reason="festive sale weekend",
        )
    )
    db_session.flush()

    # Under the normal 6h interval this wouldn't be due yet; the 1h override
    # makes it due.
    assert is_suite_due(db_session, suite, NOW) is True


def test_an_override_outside_its_window_has_no_effect(db_session):
    suite = _suite(db_session, interval_hours=6)
    db_session.add(
        EvalRun(
            suite_id=suite.id,
            trigger_source=TriggerSource.SCHEDULE,
            judge_model_version="m",
            status=RunStatus.COMPLETED,
            started_at=NOW - timedelta(hours=2),
        )
    )
    db_session.add(
        ScheduleOverride(
            suite_id=suite.id,
            interval_hours=1,
            starts_at=NOW - timedelta(days=10),
            ends_at=NOW - timedelta(days=9),
            reason="a sale that already ended",
        )
    )
    db_session.flush()

    assert is_suite_due(db_session, suite, NOW) is False


def test_run_due_suites_fires_only_the_due_suites_and_skips_the_rest(db_session):
    due_suite = _suite(db_session)
    case = GoldenCase(
        suite_id=due_suite.id, question="q", source="manual", status=CaseStatus.APPROVED
    )
    db_session.add(case)

    not_due_suite = _suite(db_session, interval_hours=6)
    db_session.add(
        EvalRun(
            suite_id=not_due_suite.id,
            trigger_source=TriggerSource.SCHEDULE,
            judge_model_version="m",
            status=RunStatus.COMPLETED,
            started_at=NOW,
        )
    )
    db_session.commit()

    fired = run_due_suites(
        db_session,
        grader=LLMJudgeGrader(_StubJudgeProvider()),
        sut=_StubSUT(),
        judge_model_version="test-model",
        now=NOW,
    )

    fired_suite_ids = {r.suite_id for r in fired}
    assert due_suite.id in fired_suite_ids
    assert not_due_suite.id not in fired_suite_ids
    assert len(list_case_results(db_session, fired[0].id)) == 2


def test_run_due_suites_skips_a_suite_already_mid_run_instead_of_raising(db_session):
    suite = _suite(db_session)
    db_session.add(
        EvalRun(
            suite_id=suite.id,
            trigger_source=TriggerSource.ON_CHANGE,
            judge_model_version="m",
            status=RunStatus.RUNNING,
        )
    )
    db_session.commit()

    fired = run_due_suites(
        db_session,
        grader=LLMJudgeGrader(_StubJudgeProvider()),
        sut=_StubSUT(),
        judge_model_version="test-model",
        now=NOW,
    )

    assert fired == []
