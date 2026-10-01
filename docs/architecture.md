# Architecture

## System overview

![Aegis Measure system architecture: an external CI/CD pipeline and the web dashboard both call the api service, which stores data in Postgres, calls an LLM provider for judging and answer generation, and calls the reference-assistant (which also calls the LLM provider); api optionally fires an outbound alert webhook.](diagrams/architecture.svg)

Four services, each with one job:

- **`api`** — the Aegis Measure product itself: golden-set management, grading,
  calibration, the eval-run engine, the dual-trigger scheduler, coverage gate, and alerts.
- **`reference-assistant`** — a small seeded fashion-catalog Q&A assistant standing in for a
  real production assistant. It's the *default* system under test, swappable via
  `REFERENCE_ASSISTANT_URL` — any service implementing the same two-endpoint contract
  (`POST /answer`, `POST /answer_with_context`) can be evaluated instead.
- **`web`** — the dashboard. A plain client-rendered Next.js app (no server-side data layer)
  that talks to `api` over HTTP/CORS.
- **`postgres`** — the only datastore. No cache layer, no message queue (see "Why not X" below).

## Why these pieces exist (no unnecessary components)

- **No vector database.** The reference assistant's catalog is ~15 items; word-overlap
  retrieval (`apps/reference-assistant/app/retrieval.py`) is enough to honestly demonstrate
  the component-vs-end-to-end distinction without a search index whose own behavior would
  need separate testing.
- **No message queue / background job framework.** `run_eval` executes synchronously within
  one HTTP request or one scheduler tick. At this scale (a handful of suites, each with tens
  of cases, graded a few times an hour) a queue would add operational surface (a broker to
  run, monitor, and reason about failure modes for) without a problem it solves — a check
  every few hours, not every few seconds, is the right interval for this kind of drift.
- **No distributed tracing stack.** That's a different product surface. Structured JSON logs
  (`app/logging_config.py`) and `/metrics` are enough for a single-process app.
- **No multi-tenant auth / RBAC.** A single shared API key (`app/api/auth.py`) is correct for
  a single-tenant internal tool with no user accounts (see `concept-to-code-mapping.md`).

## Request flow: triggering and running an eval

1. A trigger fires `run_eval` (`app/services/eval_engine.py`) one of three ways:
   - **Manual**: `POST /runs`.
   - **On-change**: `POST /webhooks/on-change`, meant to be called from the SUT's own deploy
     pipeline.
   - **Scheduled**: a background tick (`app/jobs/scheduler.py`) calls `run_due_suites`
     (`app/services/scheduling/tick.py`) on a fixed interval; it checks each suite's
     `default_schedule_interval_hours` (or an active `ScheduleOverride` for a tightened
     high-risk window) against its last run.
2. `run_eval` creates an `EvalRun` row (committed immediately so a concurrent trigger can see
   it and refuse to double-run the same suite — a best-effort in-process guard, not a
   distributed lock; see the module's docstring).
3. For every `APPROVED` case in the suite, depending on its `check_mode`:
   - **Component**: call the SUT's `/answer_with_context` with the case's frozen, stored
     context (tests reasoning in isolation, blind to retrieval failures by design).
   - **End-to-end**: call `/answer` with only the question; the SUT retrieves its own context
     (tests the whole real pipeline).
4. Each answer is graded by `LLMJudgeGrader` against the case's rubric (per-dimension
   pass/fail); a `CaseResult` row is written.
5. When a case ran both modes, `_localize_faults` compares the pair: component passes +
   end-to-end fails → `upstream_retrieval_fault`; both fail → `reasoning_fault`. Neither side
   being a real graded answer (e.g. the SUT was unreachable) suppresses the diagnosis rather
   than guessing (a real bug caught by `tests/unit/test_eval_engine.py` mid-build).
6. After the run completes, `alert_service` checks for a new failure, a pass-rate drop versus
   the previous run, and a stale (uncalibrated) judge/rubric combination for the suite —
   raising `Alert` rows and, if `ALERT_WEBHOOK_URL` is set, a best-effort outbound notification.

## Data model

See `apps/api/app/models/` for the SQLAlchemy source of truth. Key entities:

- `Suite` → `GoldenCase` (1:N) → `ReviewSubmission` (1:N, capped at 2) and `CaseResult` (1:N,
  via `EvalRun`).
- `Rubric` ← `GoldenCase.rubric_id` (nullable — falls back to `DEFAULT_RUBRIC_DIMENSIONS`).
- `CalibrationRun` and `HumanLabeledSample` ← `Rubric`/`GoldenCase`, independent of eval runs.
- `LaunchCoverageCheck` — optionally linked to a `Suite`, otherwise standalone.
- `Alert` — optionally linked to a `Suite` and/or `EvalRun`.

Migrations are Alembic, under `apps/api/alembic/versions/`; `alembic upgrade head` runs
automatically on container start (see the API's `Dockerfile`).

## Security & reliability posture

- **Auth**: a single `X-API-Key` header, checked by `app/api/auth.py`, required on every
  router except `/health` and `/ready` (container healthchecks carry no headers).
- **CORS**: explicit allow-list (`CORS_ALLOWED_ORIGINS`), not a wildcard.
- **Rate limiting**: the on-change webhook caps at 20 requests/minute
  (`app/services/rate_limit.py`) — an in-memory, single-process limiter; a multi-replica
  deployment would need a shared store instead.
- **Retries**: every outbound call to Claude or to the SUT (`app/services/judge/`,
  `app/services/sut_adapter/`, `apps/reference-assistant/app/llm_provider.py`) retries
  transient network/timeout/rate-limit errors up to 3 times with exponential backoff, via
  `tenacity`. A genuine design trap here — wrapping the raw error into a different exception
  type *before* tenacity's retry predicate can see it, silently disabling retries — is
  documented and regression-tested in `tests/unit/test_sut_adapter_retry.py`.
- **Graceful degradation**: an unreachable SUT or a missing `ANTHROPIC_API_KEY` fails the
  specific `CaseResult` (recorded with a clear error rationale) without erroring the whole
  `EvalRun` or crashing the scheduler tick.
