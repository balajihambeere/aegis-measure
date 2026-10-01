"""A run finding something is only useful if someone notices — these are
the automatic notices."""

import uuid
from datetime import UTC, date, datetime, timedelta

from app.models.calibration import HumanLabeledSample
from app.models.coverage import LaunchCoverageCheck
from app.models.enums import (
    AlertType,
    CaseStatus,
    CheckMode,
    CoverageStatus,
    GraderType,
    RunStatus,
    TriggerSource,
)
from app.models.eval_run import CaseResult, EvalRun
from app.models.golden_case import GoldenCase
from app.models.rubric import Rubric
from app.models.suite import Suite
from app.services.alert_service import (
    check_calibration_staleness,
    check_coverage_gaps_due,
    check_for_new_failures,
    check_for_pass_rate_drop,
    list_alerts,
)
from app.services.calibration_service import run_calibration
from app.services.grading.llm_judge import LLMJudgeGrader

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def _suite(db_session) -> Suite:
    suite = Suite(name=f"suite-{uuid.uuid4()}")
    db_session.add(suite)
    db_session.flush()
    return suite


def _case(db_session, suite: Suite) -> GoldenCase:
    case = GoldenCase(
        suite_id=suite.id, question="q", source="manual", status=CaseStatus.APPROVED
    )
    db_session.add(case)
    db_session.flush()
    return case


def _run(db_session, suite: Suite, started_at: datetime) -> EvalRun:
    run = EvalRun(
        suite_id=suite.id,
        trigger_source=TriggerSource.SCHEDULE,
        judge_model_version="test-model",
        status=RunStatus.COMPLETED,
        started_at=started_at,
    )
    db_session.add(run)
    db_session.flush()
    return run


def _result(db_session, run: EvalRun, case: GoldenCase, passed: bool) -> CaseResult:
    result = CaseResult(
        run_id=run.id,
        case_id=case.id,
        check_mode=CheckMode.END_TO_END,
        grader_type=GraderType.LLM_JUDGE,
        candidate_answer="a",
        dimension_results={},
        passed=passed,
    )
    db_session.add(result)
    db_session.flush()
    return result


def test_new_failure_alert_fires_when_a_previously_passing_case_fails(db_session):
    suite = _suite(db_session)
    case = _case(db_session, suite)
    run1 = _run(db_session, suite, NOW - timedelta(hours=6))
    _result(db_session, run1, case, passed=True)
    run2 = _run(db_session, suite, NOW)
    _result(db_session, run2, case, passed=False)
    db_session.commit()

    check_for_new_failures(db_session, run2)

    alerts = list_alerts(db_session, suite_id=suite.id)
    assert any(a.alert_type == AlertType.NEW_FAILURE for a in alerts)


def test_no_new_failure_alert_without_a_prior_run(db_session):
    suite = _suite(db_session)
    case = _case(db_session, suite)
    run = _run(db_session, suite, NOW)
    _result(db_session, run, case, passed=False)
    db_session.commit()

    check_for_new_failures(db_session, run)

    assert list_alerts(db_session, suite_id=suite.id) == []


def test_pass_rate_drop_alert_fires_above_threshold(db_session):
    suite = _suite(db_session)
    cases = [_case(db_session, suite) for _ in range(4)]
    run1 = _run(db_session, suite, NOW - timedelta(hours=6))
    for c in cases:
        _result(db_session, run1, c, passed=True)
    run2 = _run(db_session, suite, NOW)
    for i, c in enumerate(cases):
        _result(db_session, run2, c, passed=(i < 2))  # 50% pass rate, was 100%
    db_session.commit()

    check_for_pass_rate_drop(db_session, run2)

    alerts = list_alerts(db_session, suite_id=suite.id)
    assert any(a.alert_type == AlertType.PASS_RATE_DROP for a in alerts)


def test_no_pass_rate_drop_alert_for_a_small_drop(db_session):
    suite = _suite(db_session)
    cases = [_case(db_session, suite) for _ in range(10)]
    run1 = _run(db_session, suite, NOW - timedelta(hours=6))
    for c in cases:
        _result(db_session, run1, c, passed=True)
    run2 = _run(db_session, suite, NOW)
    for i, c in enumerate(cases):
        _result(db_session, run2, c, passed=(i != 0))  # 90% pass rate, was 100%
    db_session.commit()

    check_for_pass_rate_drop(db_session, run2)

    assert list_alerts(db_session, suite_id=suite.id) == []


def test_calibration_staleness_alert_fires_for_an_uncalibrated_rubric(db_session):
    suite = _suite(db_session)
    rubric = Rubric(name=f"r-{uuid.uuid4()}", dimensions=[{"key": "x", "description": "x"}])
    db_session.add(rubric)
    db_session.flush()
    case = GoldenCase(
        suite_id=suite.id,
        rubric_id=rubric.id,
        question="q",
        source="manual",
        status=CaseStatus.APPROVED,
    )
    db_session.add(case)
    db_session.flush()
    run = _run(db_session, suite, NOW)
    db_session.commit()

    check_calibration_staleness(db_session, run)

    alerts = list_alerts(db_session, suite_id=suite.id)
    assert any(a.alert_type == AlertType.CALIBRATION_STALE for a in alerts)


def test_no_calibration_staleness_alert_once_calibrated(db_session):
    suite = _suite(db_session)
    rubric = Rubric(name=f"r-{uuid.uuid4()}", dimensions=[{"key": "x", "description": "x"}])
    db_session.add(rubric)
    db_session.flush()
    labeled_case = GoldenCase(
        suite_id=suite.id, rubric_id=rubric.id, question="q", source="manual"
    )
    db_session.add(labeled_case)
    db_session.flush()
    db_session.add(
        HumanLabeledSample(
            case_id=labeled_case.id, candidate_answer="a", human_verdict=True, labeled_by="V"
        )
    )
    db_session.flush()

    class _AlwaysPassProvider:
        def grade_dimensions(self, *, dimensions, **_):
            return {d["key"]: {"passed": True, "rationale": "x"} for d in dimensions}

    run_calibration(
        db_session,
        rubric_id=rubric.id,
        judge_model_version="test-model",
        grader=LLMJudgeGrader(_AlwaysPassProvider()),
        threshold=0.5,
    )

    approved_case = GoldenCase(
        suite_id=suite.id,
        rubric_id=rubric.id,
        question="q2",
        source="manual",
        status=CaseStatus.APPROVED,
    )
    db_session.add(approved_case)
    run = _run(db_session, suite, NOW)
    db_session.commit()

    check_calibration_staleness(db_session, run)

    assert list_alerts(db_session, suite_id=suite.id) == []


def test_coverage_gap_due_alert_fires_once_past_the_re_review_date(db_session):
    suite = _suite(db_session)
    db_session.add(
        LaunchCoverageCheck(
            feature_name="festive-sale-bundle",
            launch_date=date(2026, 9, 20),
            linked_suite_id=suite.id,
            declared_gaps=["children's sizing"],
            coverage_status=CoverageStatus.PARTIAL,
            answered_by="Vyasa",
            answered_at=NOW - timedelta(days=10),
            re_review_due_at=date(2026, 9, 28),
        )
    )
    db_session.commit()

    check_coverage_gaps_due(db_session, date(2026, 10, 1))

    alerts = list_alerts(db_session, suite_id=suite.id)
    assert any(a.alert_type == AlertType.COVERAGE_GAP_DUE for a in alerts)


def test_no_coverage_gap_alert_before_the_due_date(db_session):
    suite = _suite(db_session)
    db_session.add(
        LaunchCoverageCheck(
            feature_name="festive-sale-bundle",
            launch_date=date(2026, 9, 20),
            linked_suite_id=suite.id,
            declared_gaps=[],
            coverage_status=CoverageStatus.PARTIAL,
            answered_by="Vyasa",
            answered_at=NOW,
            re_review_due_at=date(2026, 10, 10),
        )
    )
    db_session.commit()

    check_coverage_gaps_due(db_session, date(2026, 10, 1))

    assert list_alerts(db_session, suite_id=suite.id) == []
