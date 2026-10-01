import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_judge_grader
from app.config import get_settings
from app.db.session import get_db
from app.schemas.calibration import (
    CalibrationRunCreate,
    CalibrationRunRead,
    HumanLabeledSampleCreate,
    HumanLabeledSampleRead,
)
from app.services import calibration_service
from app.services.grading.llm_judge import LLMJudgeGrader

router = APIRouter(tags=["calibration"])


@router.post("/human-labeled-samples", response_model=HumanLabeledSampleRead, status_code=201)
def create_human_labeled_sample(
    data: HumanLabeledSampleCreate, db: Session = Depends(get_db)
) -> HumanLabeledSampleRead:
    sample = calibration_service.create_human_labeled_sample(db, data)
    return HumanLabeledSampleRead.model_validate(sample)


@router.post("/calibration-runs", response_model=CalibrationRunRead, status_code=201)
def create_calibration_run(
    data: CalibrationRunCreate,
    db: Session = Depends(get_db),
    grader: LLMJudgeGrader = Depends(get_judge_grader),
) -> CalibrationRunRead:
    threshold = data.threshold or get_settings().calibration_agreement_threshold
    run = calibration_service.run_calibration(
        db,
        rubric_id=data.rubric_id,
        judge_model_version=data.judge_model_version,
        grader=grader,
        threshold=threshold,
    )
    return CalibrationRunRead.model_validate(run)


@router.get("/calibration-runs", response_model=list[CalibrationRunRead])
def list_calibration_runs(
    rubric_id: uuid.UUID | None = None, db: Session = Depends(get_db)
) -> list[CalibrationRunRead]:
    runs = calibration_service.list_calibration_runs(db, rubric_id=rubric_id)
    return [CalibrationRunRead.model_validate(r) for r in runs]
