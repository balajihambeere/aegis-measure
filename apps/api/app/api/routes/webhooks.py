from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_judge_grader, get_sut_adapter
from app.config import get_settings
from app.db.session import get_db
from app.models.enums import TriggerSource
from app.schemas.eval_run import EvalRunRead
from app.schemas.webhook import OnChangeTriggerRequest, OnChangeTriggerResponse
from app.services import suite_service
from app.services.errors import ConflictError
from app.services.eval_engine import run_eval
from app.services.grading.llm_judge import LLMJudgeGrader
from app.services.rate_limit import check_rate_limit
from app.services.sut_adapter.base import SUTAdapter

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# A deploy pipeline firing this on every merge is the expected usage; a tight
# loop calling it dozens of times a minute (misconfigured CI, retry storm) is
# not — cap it rather than let a runaway caller flood the judge/SUT with runs.
ON_CHANGE_RATE_LIMIT = 20
ON_CHANGE_RATE_WINDOW_SECONDS = 60.0


@router.post("/on-change", response_model=OnChangeTriggerResponse, status_code=201)
def trigger_on_change(
    data: OnChangeTriggerRequest,
    db: Session = Depends(get_db),
    grader: LLMJudgeGrader = Depends(get_judge_grader),
    sut: SUTAdapter = Depends(get_sut_adapter),
) -> OnChangeTriggerResponse:
    """The on-change trigger: wire this into the system-under-test's own
    deploy pipeline so every prompt/retrieval/model change fires the
    relevant suite(s) within minutes — catching engineering regressions
    before the next scheduled tick would.

    With no suite_id, fires every suite (a full-catalog deploy touches
    everything); suites already mid-run are skipped, not errored."""
    check_rate_limit("webhooks.on-change", ON_CHANGE_RATE_LIMIT, ON_CHANGE_RATE_WINDOW_SECONDS)
    settings = get_settings()
    judge_model_version = settings.judge_model
    suites = (
        [suite_service.get_suite(db, data.suite_id)]
        if data.suite_id is not None
        else suite_service.list_suites(db)
    )

    triggered = []
    skipped = []
    for suite in suites:
        try:
            run = run_eval(
                db,
                suite_id=suite.id,
                trigger_source=TriggerSource.ON_CHANGE,
                grader=grader,
                sut=sut,
                judge_model_version=judge_model_version,
            )
            triggered.append(EvalRunRead.model_validate(run))
        except ConflictError:
            skipped.append(suite.id)

    return OnChangeTriggerResponse(triggered=triggered, skipped_suite_ids=skipped)
