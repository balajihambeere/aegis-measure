import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.common import utcnow
from app.models.enums import CaseStatus, CheckMode, Diagnosis, GraderType, RunStatus, TriggerSource
from app.models.eval_run import CaseResult, EvalRun
from app.models.golden_case import GoldenCase
from app.models.rubric import DEFAULT_RUBRIC_DIMENSIONS
from app.services import alert_service
from app.services.errors import ConflictError, NotFoundError
from app.services.grading.llm_judge import LLMJudgeGrader
from app.services.suite_service import get_suite
from app.services.sut_adapter.base import SUTAdapter, SUTUnavailableError


def _rubric_dimensions(case: GoldenCase) -> list[dict]:
    return case.rubric.dimensions if case.rubric is not None else DEFAULT_RUBRIC_DIMENSIONS


def _run_component_check(
    db: Session, run: EvalRun, case: GoldenCase, sut: SUTAdapter, grader: LLMJudgeGrader
) -> CaseResult:
    try:
        sut_response = sut.answer_with_context(question=case.question, context=case.context or "")
        candidate_answer = sut_response["answer"]
        grading = grader.grade(
            question=case.question,
            context=case.context,
            reference_answer=case.reference_answer or "",
            candidate_answer=candidate_answer,
            rubric_dimensions=_rubric_dimensions(case),
        )
        passed = grading.passed
        dimension_results = grading.as_json()
    except SUTUnavailableError as exc:
        candidate_answer = ""
        passed = False
        dimension_results = {"error": {"passed": False, "rationale": str(exc)}}

    result = CaseResult(
        run_id=run.id,
        case_id=case.id,
        check_mode=CheckMode.COMPONENT,
        grader_type=GraderType.LLM_JUDGE,
        candidate_answer=candidate_answer,
        retrieved_context=case.context,
        dimension_results=dimension_results,
        passed=passed,
    )
    db.add(result)
    return result


def _run_end_to_end_check(
    db: Session, run: EvalRun, case: GoldenCase, sut: SUTAdapter, grader: LLMJudgeGrader
) -> CaseResult:
    try:
        sut_response = sut.answer(question=case.question)
        candidate_answer = sut_response["answer"]
        retrieved_context = sut_response["retrieved_context"]
        grading = grader.grade(
            question=case.question,
            context=retrieved_context,
            reference_answer=case.reference_answer or "",
            candidate_answer=candidate_answer,
            rubric_dimensions=_rubric_dimensions(case),
        )
        passed = grading.passed
        dimension_results = grading.as_json()
    except SUTUnavailableError as exc:
        candidate_answer = ""
        retrieved_context = None
        passed = False
        dimension_results = {"error": {"passed": False, "rationale": str(exc)}}

    result = CaseResult(
        run_id=run.id,
        case_id=case.id,
        check_mode=CheckMode.END_TO_END,
        grader_type=GraderType.LLM_JUDGE,
        candidate_answer=candidate_answer,
        retrieved_context=retrieved_context,
        dimension_results=dimension_results,
        passed=passed,
    )
    db.add(result)
    return result


def _localize_faults(component: CaseResult | None, end_to_end: CaseResult | None) -> None:
    """Running both checks on the same case localizes the fault: the pair of
    results tells you which half of the system to go fix, not just that
    something broke. Skipped when either side is itself an infrastructure
    error (the SUT was unreachable) rather than a real graded answer —
    blaming 'reasoning' when the system never got a chance to reason would
    misdiagnose the fault."""
    if component is None or end_to_end is None:
        return
    if "error" in component.dimension_results or "error" in end_to_end.dimension_results:
        return
    if component.passed and not end_to_end.passed:
        end_to_end.diagnosis = Diagnosis.UPSTREAM_RETRIEVAL_FAULT
    elif not component.passed and not end_to_end.passed:
        end_to_end.diagnosis = Diagnosis.REASONING_FAULT


def run_eval(
    db: Session,
    *,
    suite_id: uuid.UUID,
    trigger_source: TriggerSource,
    grader: LLMJudgeGrader,
    sut: SUTAdapter,
    judge_model_version: str,
) -> EvalRun:
    """One firing of the harness. Runs every approved case in the suite, in
    whichever check mode(s) it's configured for, and — for cases running
    both modes — localizes the fault when they disagree.

    The on-change and scheduled triggers can both reach for the same suite
    close together; refuse to start a second run while one is still in
    flight rather than racing two runs against the same cases."""
    get_suite(db, suite_id)  # raises NotFoundError if missing

    if db.execute(
        select(EvalRun.id).where(
            EvalRun.suite_id == suite_id, EvalRun.status == RunStatus.RUNNING
        )
    ).first():
        raise ConflictError(f"A run is already in progress for suite {suite_id}")

    run = EvalRun(
        suite_id=suite_id,
        trigger_source=trigger_source,
        judge_model_version=judge_model_version,
        status=RunStatus.RUNNING,
    )
    db.add(run)
    # Committed immediately (not just flushed) so the RUNNING row is visible
    # to the in-flight check above from another session right away, instead
    # of only becoming visible once this entire run finishes. This is a
    # best-effort guard, not a hard lock — two triggers landing in the same
    # instant can still both pass the check before either commits.
    db.commit()
    db.refresh(run)

    cases = list(
        db.execute(
            select(GoldenCase).where(
                GoldenCase.suite_id == suite_id, GoldenCase.status == CaseStatus.APPROVED
            )
        ).scalars()
    )

    for case in cases:
        component_result = None
        end_to_end_result = None

        if case.check_mode in (CheckMode.COMPONENT, CheckMode.BOTH):
            component_result = _run_component_check(db, run, case, sut, grader)
        if case.check_mode in (CheckMode.END_TO_END, CheckMode.BOTH):
            end_to_end_result = _run_end_to_end_check(db, run, case, sut, grader)

        _localize_faults(component_result, end_to_end_result)

    run.status = RunStatus.COMPLETED
    run.finished_at = utcnow()
    db.commit()
    db.refresh(run)

    # A run that finds something is only useful if someone (or something)
    # notices — raise alerts on what this run reveals rather than leaving it
    # sitting in a table nobody's looking at.
    alert_service.check_for_new_failures(db, run)
    alert_service.check_for_pass_rate_drop(db, run)
    alert_service.check_calibration_staleness(db, run)

    return run


def get_run(db: Session, run_id: uuid.UUID) -> EvalRun:
    run = db.get(EvalRun, run_id)
    if run is None:
        raise NotFoundError(f"EvalRun {run_id} not found")
    return run


def list_runs(db: Session, suite_id: uuid.UUID | None = None) -> list[EvalRun]:
    stmt = select(EvalRun).order_by(EvalRun.started_at.desc())
    if suite_id is not None:
        stmt = stmt.where(EvalRun.suite_id == suite_id)
    return list(db.execute(stmt).scalars())


def list_case_results(db: Session, run_id: uuid.UUID) -> list[CaseResult]:
    stmt = select(CaseResult).where(CaseResult.run_id == run_id)
    return list(db.execute(stmt).scalars())
