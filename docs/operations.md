# Operations

## Local / single-host deployment

```bash
cp .env.example .env
# Fill in ANTHROPIC_API_KEY for real judge/assistant calls, and change
# AEGIS_API_KEY + NEXT_PUBLIC_AEGIS_API_KEY (must match) from the default.
cd infrastructure
docker compose up -d --build
```

This brings up, in order (via `depends_on` + healthchecks): `postgres` → `reference-assistant`
→ `api` (runs `alembic upgrade head` on start, then serves) → `web`. Verified end-to-end as
part of this project's own build — see `docs/architecture.md` for what each service does.

- API: `http://localhost:8001` (`/health`, `/docs`)
- Reference assistant: `http://localhost:8100/health`
- Dashboard: `http://localhost:3300`
- Postgres: `localhost:55433` (host-mapped; `aegis`/`aegis`)

Host ports are intentionally non-default to avoid colliding with other local projects;
container-to-container traffic uses the standard ports regardless (see `docker-compose.yml`).

## Environment variables

All of them are documented inline in `.env.example`, grouped by concern (database, auth, LLM
provider, scheduler, calibration, reference assistant, alerting, CORS). A few worth calling
out specifically:

- `AEGIS_API_KEY` / `NEXT_PUBLIC_AEGIS_API_KEY` **must match** — the first is what the
  API checks, the second is what the dashboard sends (inlined into its client bundle at
  build/runtime, since the dashboard has no server-side layer to keep it out of).
- `SCHEDULER_ENABLED` defaults to `false` in code (so importing/testing the app never spins up
  a background thread by surprise) but is set `true` in the shipped `.env.example` for the
  real deployment.
- `ENABLE_RETRIEVAL_BUG` (reference assistant only) — set `true` to reproduce a near-duplicate-SKU
  retrieval failure on demand; see `apps/reference-assistant/app/retrieval.py`.

## Database & migrations

Alembic manages the schema (`apps/api/alembic/`). The API container runs `alembic upgrade
head` automatically before starting; to run it by hand (e.g. before a deploy):

```bash
cd apps/api
export DATABASE_URL=postgresql+psycopg://aegis:aegis@localhost:55433/aegis
alembic upgrade head
```

**Rollback**: `alembic downgrade -1` reverts the most recent migration. Every migration in
this project has been verified to round-trip (`upgrade → downgrade → upgrade`) cleanly,
including the Postgres ENUM types that `op.drop_table()` alone does not clean up (see the
explicit `sa.Enum(...).drop(...)` calls in `413424a04d46_initial_schema.py`'s `downgrade()` —
a real gap autogenerate left behind, caught and fixed during this build).

**Backup**: standard `pg_dump`/`pg_restore` against the `aegis` database; nothing
project-specific. Given the data (eval history, golden sets, alerts) is operationally
important but fully reconstructible from `database/seed/golden_cases.json` plus whatever
cases a team has since approved, a daily `pg_dump` is sufficient — there's no streaming or
point-in-time-recovery requirement this project introduces.

## Scaling boundaries

Identified, not engineered around (none of these have been hit at this project's scale):

- **The in-process rate limiter and the scheduler's in-flight-run guard are single-instance.**
  Running more than one `api` replica would need a shared store (Redis or similar) for both —
  documented in `app/services/rate_limit.py` and `app/services/eval_engine.py`'s docstrings.
- **`run_eval` is synchronous.** A suite with very many approved cases makes `POST /runs`
  (or a scheduled tick) take proportionally longer, since each case's judge/SUT calls happen
  in sequence within one request/tick. At the scale this project's own suites run at (single
  digits to low tens of cases), this has not been a problem; a queue-backed worker would be
  the fix if it ever is (see `docs/architecture.md`'s "why not a message queue" note for why
  that's not built preemptively).

## Observability

- **Logs**: structured JSON to stdout (`app/logging_config.py`) — `docker compose logs -f api`
  or your platform's log aggregator of choice.
- **Metrics**: `GET /metrics` (Prometheus text format, requires `X-API-Key`) — run counts by
  status, each suite's latest pass rate.
- **Alerts**: `GET /alerts` surfaces what the platform itself found (new failures, pass-rate
  drops, stale calibration, overdue coverage re-reviews); optionally mirrored to
  `ALERT_WEBHOOK_URL` (a plain `{"text": "..."}` POST, Slack-compatible).

## Troubleshooting

| Symptom | Likely cause | Where to look |
|---|---|---|
| Every `CaseResult` shows `dimension_results: {"error": {...}}` | `ANTHROPIC_API_KEY` not set for `api` and/or `reference-assistant` | The `rationale` text names which service's call (503) failed. |
| `POST /runs` returns `409` | Another run for that suite is already in progress, or just finished and raced the check | `GET /runs?suite_id=` to see current status; safe to retry. |
| Dashboard shows CORS errors in the browser console | `CORS_ALLOWED_ORIGINS` on `api` doesn't include the dashboard's actual origin | Check what port the dashboard is actually served from vs. the API's configured origin. |
| A scheduled run never fires | `SCHEDULER_ENABLED=false`, or the suite's interval (plus any active `ScheduleOverride`) hasn't elapsed since its last run | `GET /runs?suite_id=` for `started_at` of the last run; check `SCHEDULER_TICK_INTERVAL_SECONDS`. |
| A suite's dashboard shows a clean pass rate you don't trust | Check `/alerts` for `calibration_stale` — the rubric/judge-model combination in use hasn't been calibrated against human-verified samples | `POST /calibration-runs` after adding `human-labeled-samples`. |

## Seeding demo data

```bash
./scripts/demo.sh
```

Brings the stack up and replays a realistic set of incidents (saree, dupatta/retrieval-bug,
footwear, festive-sale policy, regional sizing) through the real API — golden-set
creation, blind dual review, approval, coverage-gate registration, and an attempted
LLM-graded run per suite. See `scripts/seed_demo.py` and `database/seed/golden_cases.json`.
