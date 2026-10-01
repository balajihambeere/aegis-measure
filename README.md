# Aegis Measure

A continuous AI-quality evaluation platform — the **Measure** stage of a larger
observability approach for AI systems. Every feature below is real, tested code, not a
doc-only description (see
[`docs/concept-to-code-mapping.md`](docs/concept-to-code-mapping.md)).

## What it does

AI assistants can quietly get worse without any safety or uptime dashboard noticing —
nothing crashes, nothing looks unsafe, the answers just slowly stop being as good as they
used to be. This platform exists to make that impossible to miss:

- **Golden sets** — real questions, exact context, reference answers two independent
  reviewers agree on, with a *blind* review workflow (a second reviewer can't see the first's
  answer until both are in).
- **LLM-as-judge grading against an explicit rubric** — not a single blended verdict; every
  dimension (`core_fact_correct`, `no_false_claims`, `no_unsafe_omission`) must pass.
  Exact-match and keyword-presence graders are kept as documented, tested, *known-flawed*
  baselines, reproducing their real, specific failure modes.
- **Judge calibration** — a rubric/judge-model combination's verdicts are checked against
  human-labeled samples before anything depends on them.
- **Dual-trigger continuous scheduling** — an on-change webhook (wire into your deploy
  pipeline) plus a fixed-interval background tick, with a tightened interval for high-risk
  launch windows.
- **Component vs. end-to-end checks** — run both, and the platform tells you whether a
  failure is an upstream/retrieval fault or a reasoning fault, not just that something broke.
- **The coverage-gate ritual** — "if this broke silently, who would notice, and when?" is a
  tracked, written record per launch, with declared gaps and a scheduled re-review.
- **Alerts** — new failures, pass-rate drops, stale calibration, and overdue re-reviews are
  surfaced automatically, not left sitting in a table nobody's watching.

## Architecture

![Aegis Measure system architecture: an external CI/CD pipeline and the web dashboard both call the api service, which stores data in Postgres, calls an LLM provider for judging and answer generation, and calls the reference-assistant (which also calls the LLM provider); api optionally fires an outbound alert webhook.](docs/diagrams/architecture.svg)

Four services — `api` (FastAPI), `reference-assistant` (the default system under test, a
seeded fashion-catalog Q&A assistant standing in for a real production assistant), `web`
(Next.js dashboard), and `postgres`. Full detail, request flow, and the "why not X" reasoning
behind what's *absent* (no vector DB, no message queue, no distributed tracing) is in
[`docs/architecture.md`](docs/architecture.md).

## Dashboard

**Suites** — pass-rate summary and trigger controls

![Suites list with summary stat cards and per-suite pass rate](docs/screenshots/suites.jpg)

**Suite detail** — golden cases and run history

![Suite detail page showing golden cases and runs](docs/screenshots/suite-detail.jpg)

**Run detail** — per-case rubric breakdown and fault diagnosis

![Run detail page showing candidate answer, reference answer, and rubric dimension results](docs/screenshots/run-detail.jpg)

**Review queue** — the blind two-reviewer workflow

![Review queue page](docs/screenshots/review-queue.jpg)

**Judge calibration** — agreement rate vs. human-labeled samples

![Judge calibration page](docs/screenshots/calibration.jpg)

**Coverage gate** — the "who would notice, and when?" register

![Coverage gate page listing launches and declared gaps](docs/screenshots/coverage-gate.jpg)

**Alerts** — pass-rate drops, new failures, stale calibration, overdue re-reviews

![Alerts page listing raised alerts with acknowledge action](docs/screenshots/alerts.jpg)

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Backend | Python 3.12, FastAPI | Async-friendly, strong typing, the richest LLM-eval tooling ecosystem. |
| Database | Postgres 16, SQLAlchemy 2.0, Alembic | Real relational integrity for a system whose whole point is trustworthy records. |
| Scheduler | APScheduler (in-process) | A queue/broker would add operational surface this scale doesn't need — see `docs/architecture.md`. |
| LLM provider | Anthropic Claude, via a small provider-abstraction layer | Swappable without touching call sites (`app/services/judge/base.py`, `app/llm_provider.py`). |
| Frontend | Next.js (App Router), Tailwind CSS | Client-rendered dashboard; no server-side data layer needed for this scope. |
| Deployment | Docker Compose | Four services, single host — matches the project's actual scale. |

## Quick start

```bash
cp .env.example .env
# Add your ANTHROPIC_API_KEY for real judge/assistant calls (optional — the platform
# degrades gracefully without one, recording a clear error per case instead of crashing).
cd infrastructure
docker compose up -d --build
```

- API: http://localhost:8001 (interactive docs at `/docs`)
- Reference assistant: http://localhost:8100/health
- Dashboard: http://localhost:3300

Then seed it with a realistic demo scenario:

```bash
./scripts/demo.sh
```

See [`docs/operations.md`](docs/operations.md) for environment variables, migrations,
backup/rollback, scaling boundaries, observability, and troubleshooting.

## Local development (without Docker)

**API**:
```bash
cd apps/api
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL=postgresql+psycopg://aegis:aegis@localhost:55433/aegis
alembic upgrade head
pytest -q            # 67 tests, no live DB-writes leak into the dev database —
                      # tests run against an isolated <db>_test database (tests/conftest.py)
ruff check . && mypy app
uvicorn app.main:app --reload
```

**Reference assistant**: same pattern, in `apps/reference-assistant/`.

**Dashboard**:
```bash
cd apps/web
npm install
npm run typecheck && npm run lint
npm run dev
```

## API reference

[`docs/api.md`](docs/api.md) — every endpoint, auth, and error shape.

## Testing

- **Unit** (`apps/api/tests/unit/`, `apps/reference-assistant/tests/`): grading logic,
  calibration math, scheduling due-ness, retry behavior, auth, rate limiting — pure logic,
  no external services.
- **Integration** (`apps/api/tests/integration/`): full HTTP request/response cycles against
  a real (isolated) Postgres database, with the judge/SUT dependencies swapped for scripted
  test doubles.
- **Live/manual verification**: every phase of this build was additionally verified against
  the real Docker Compose stack (not just mocks) — see `docs/concept-to-code-mapping.md` and
  `scripts/seed_demo.py` for what was actually run and observed, including a real bug (a
  retry-defeating exception-wrapping order, and a duplicate-name 500-instead-of-409) caught
  and fixed by that live testing, not just unit tests.
- Running a real Claude-graded eval end-to-end requires `ANTHROPIC_API_KEY`; without one,
  `scripts/demo.sh` still proves the golden-set/review/coverage-gate subsystems live, and
  reports the LLM-graded step's expected, graceful failure rather than crashing.

## Concept-to-code mapping

[`docs/concept-to-code-mapping.md`](docs/concept-to-code-mapping.md) — every concept, where
it's implemented, and the test that actually exercises the scenario it's meant to catch.
