from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.eval_run import CaseResult, EvalRun
from app.models.suite import Suite

router = APIRouter(tags=["metrics"])


@router.get("/metrics", response_class=PlainTextResponse)
def metrics(db: Session = Depends(get_db)) -> str:
    """Minimal Prometheus-text-format exposition — run counts by status, and
    each suite's latest pass rate. Deliberately small: this is an internal
    single-tenant tool, not a general observability platform."""
    lines = [
        "# HELP aegis_eval_runs_total Total eval runs by status.",
        "# TYPE aegis_eval_runs_total counter",
    ]
    status_counts = db.execute(
        select(EvalRun.status, func.count()).group_by(EvalRun.status)
    ).all()
    for status, count in status_counts:
        lines.append(f'aegis_eval_runs_total{{status="{status.value}"}} {count}')

    lines += [
        "# HELP aegis_suite_latest_pass_rate Pass rate of each suite's most recent run.",
        "# TYPE aegis_suite_latest_pass_rate gauge",
    ]
    for suite in db.execute(select(Suite)).scalars():
        latest_run = db.execute(
            select(EvalRun)
            .where(EvalRun.suite_id == suite.id)
            .order_by(EvalRun.started_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        if latest_run is None:
            continue
        results = list(
            db.execute(select(CaseResult).where(CaseResult.run_id == latest_run.id)).scalars()
        )
        if not results:
            continue
        pass_rate = sum(1 for r in results if r.passed) / len(results)
        lines.append(f'aegis_suite_latest_pass_rate{{suite="{suite.name}"}} {pass_rate:.4f}')

    return "\n".join(lines) + "\n"
