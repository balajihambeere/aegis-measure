import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.calibration import CalibrationRun, HumanLabeledSample
from app.models.golden_case import GoldenCase
from app.schemas.calibration import HumanLabeledSampleCreate
from app.services.case_service import get_case
from app.services.errors import ConflictError
from app.services.grading.llm_judge import LLMJudgeGrader
from app.services.rubric_service import get_rubric


def create_human_labeled_sample(
    db: Session, data: HumanLabeledSampleCreate
) -> HumanLabeledSample:
    get_case(db, data.case_id)  # raises NotFoundError if missing
    sample = HumanLabeledSample(
        case_id=data.case_id,
        candidate_answer=data.candidate_answer,
        human_verdict=data.human_verdict,
        labeled_by=data.labeled_by,
    )
    db.add(sample)
    db.commit()
    db.refresh(sample)
    return sample


def run_calibration(
    db: Session,
    *,
    rubric_id: uuid.UUID,
    judge_model_version: str,
    grader: LLMJudgeGrader,
    threshold: float,
) -> CalibrationRun:
    """Checks whether the judge's verdict matches a human's, on cases where
    the real answer is already known — run before trusting a rubric/judge-
    model combination, and again whenever either one changes."""
    rubric = get_rubric(db, rubric_id)

    samples = list(
        db.execute(
            select(HumanLabeledSample)
            .join(GoldenCase, HumanLabeledSample.case_id == GoldenCase.id)
            .where(GoldenCase.rubric_id == rubric_id)
        ).scalars()
    )
    if not samples:
        raise ConflictError(
            f"No human-labeled samples exist for rubric {rubric_id} — "
            "nothing to calibrate against"
        )

    agreement_count = 0
    disagreements: list[dict] = []
    for sample in samples:
        case = sample.case
        result = grader.grade(
            question=case.question,
            context=case.context,
            reference_answer=case.reference_answer or "",
            candidate_answer=sample.candidate_answer,
            rubric_dimensions=rubric.dimensions,
        )
        if result.passed == sample.human_verdict:
            agreement_count += 1
        else:
            disagreements.append(
                {
                    "case_id": str(case.id),
                    "sample_id": str(sample.id),
                    "judge_verdict": result.passed,
                    "human_verdict": sample.human_verdict,
                }
            )

    sample_size = len(samples)
    agreement_rate = agreement_count / sample_size
    run = CalibrationRun(
        rubric_id=rubric_id,
        judge_model_version=judge_model_version,
        sample_size=sample_size,
        agreement_count=agreement_count,
        agreement_rate=agreement_rate,
        threshold=threshold,
        passed_threshold=agreement_rate >= threshold,
        disagreements=disagreements,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def list_calibration_runs(
    db: Session, rubric_id: uuid.UUID | None = None
) -> list[CalibrationRun]:
    stmt = select(CalibrationRun).order_by(CalibrationRun.created_at.desc())
    if rubric_id is not None:
        stmt = stmt.where(CalibrationRun.rubric_id == rubric_id)
    return list(db.execute(stmt).scalars())


def latest_calibration(
    db: Session, rubric_id: uuid.UUID, judge_model_version: str
) -> CalibrationRun | None:
    stmt = (
        select(CalibrationRun)
        .where(
            CalibrationRun.rubric_id == rubric_id,
            CalibrationRun.judge_model_version == judge_model_version,
        )
        .order_by(CalibrationRun.created_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalars().first()


def is_calibrated(db: Session, rubric_id: uuid.UUID, judge_model_version: str) -> bool:
    run = latest_calibration(db, rubric_id, judge_model_version)
    return run is not None and run.passed_threshold


def require_calibrated(db: Session, rubric_id: uuid.UUID, judge_model_version: str) -> None:
    """Gate: a rubric/judge-model combination cannot be trusted for scheduled
    runs until it has been calibrated above threshold. Used by the scheduler
    before firing a run."""
    if not is_calibrated(db, rubric_id, judge_model_version):
        raise ConflictError(
            f"Rubric {rubric_id} is not calibrated for judge model "
            f"'{judge_model_version}' — run calibration before scheduling "
            "eval runs against it."
        )


__all__ = [
    "create_human_labeled_sample",
    "run_calibration",
    "list_calibration_runs",
    "latest_calibration",
    "is_calibrated",
    "require_calibrated",
]
