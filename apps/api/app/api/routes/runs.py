import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_judge_grader, get_sut_adapter
from app.config import get_settings
from app.db.session import get_db
from app.models.enums import TriggerSource
from app.schemas.eval_run import CaseResultRead, EvalRunCreate, EvalRunRead
from app.services import eval_engine
from app.services.grading.llm_judge import LLMJudgeGrader
from app.services.sut_adapter.base import SUTAdapter

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=EvalRunRead, status_code=201)
def create_run(
    data: EvalRunCreate,
    db: Session = Depends(get_db),
    grader: LLMJudgeGrader = Depends(get_judge_grader),
    sut: SUTAdapter = Depends(get_sut_adapter),
) -> EvalRunRead:
    judge_model_version = data.judge_model_version or get_settings().judge_model
    run = eval_engine.run_eval(
        db,
        suite_id=data.suite_id,
        trigger_source=TriggerSource(data.trigger_source),
        grader=grader,
        sut=sut,
        judge_model_version=judge_model_version,
    )
    return EvalRunRead.model_validate(run)


@router.get("", response_model=list[EvalRunRead])
def list_runs(
    suite_id: uuid.UUID | None = None, db: Session = Depends(get_db)
) -> list[EvalRunRead]:
    return [EvalRunRead.model_validate(r) for r in eval_engine.list_runs(db, suite_id=suite_id)]


@router.get("/{run_id}", response_model=EvalRunRead)
def get_run(run_id: uuid.UUID, db: Session = Depends(get_db)) -> EvalRunRead:
    return EvalRunRead.model_validate(eval_engine.get_run(db, run_id))


@router.get("/{run_id}/results", response_model=list[CaseResultRead])
def list_case_results(run_id: uuid.UUID, db: Session = Depends(get_db)) -> list[CaseResultRead]:
    eval_engine.get_run(db, run_id)  # 404 if the run doesn't exist
    results = eval_engine.list_case_results(db, run_id)
    return [CaseResultRead.model_validate(r) for r in results]
