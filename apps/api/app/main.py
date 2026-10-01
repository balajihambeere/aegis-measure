from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import require_api_key
from app.api.routes import (
    alerts,
    calibration,
    cases,
    coverage,
    health,
    metrics,
    rubrics,
    runs,
    suites,
    webhooks,
)
from app.config import get_settings
from app.jobs.scheduler import start_scheduler, stop_scheduler
from app.logging_config import configure_logging
from app.services.errors import ConflictError, NotFoundError

logger = configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.scheduler_enabled:
        start_scheduler(settings.scheduler_tick_interval_seconds)
    yield
    if settings.scheduler_enabled:
        stop_scheduler()


app = FastAPI(
    title="Aegis Measure",
    description="EvalOps platform for continuous AI-quality evaluation — the Measure stage.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_allowed_origins_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(NotFoundError)
def handle_not_found(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
def handle_conflict(request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


# /health and /ready are unauthenticated (container healthchecks hit them
# with no headers); every other endpoint requires X-API-Key.
app.include_router(health.router)

_auth = [Depends(require_api_key)]
app.include_router(suites.router, dependencies=_auth)
app.include_router(cases.router, dependencies=_auth)
app.include_router(rubrics.router, dependencies=_auth)
app.include_router(calibration.router, dependencies=_auth)
app.include_router(runs.router, dependencies=_auth)
app.include_router(webhooks.router, dependencies=_auth)
app.include_router(coverage.router, dependencies=_auth)
app.include_router(alerts.router, dependencies=_auth)
app.include_router(metrics.router, dependencies=_auth)
