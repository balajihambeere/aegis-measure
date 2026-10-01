# Concept-to-Code Mapping

Every concept below is implemented as real, tested code — not a doc-only description. The
"Test" column points at the test that actually exercises the scenario described, not a
generic one.

| Concept | Component | Implementation | Test |
|---|---|---|---|
| **Silent quality drift** — correctness degrading with nothing measuring it | Entire platform | — | `tests/integration/test_runs_api.py` (a run genuinely grades the system, doesn't just say "fine") |
| **Golden Set** — real question + exact context + hand-verified reference answer | `GoldenCase` model | `app/models/golden_case.py` | `tests/unit/test_models.py` |
| **Two-independent-reviewer rule** | Blind dual-review workflow | `app/services/review_service.py`, `app/api/routes/cases.py` (`POST /cases/{id}/reviews`, `GET .../reviews`) | `tests/integration/test_golden_set_api.py::test_full_approval_flow_when_reviewers_agree` |
| **Disagreement means the source is ambiguous**, not a grading bug to resolve by picking one answer | `resolve_case` requires an explicit `needs_resolution` decision; never auto-merges | `app/services/review_service.py::resolve_case` | `test_disagreement_flags_needs_resolution_instead_of_silently_picking_one` |
| **Exact-match grading fails on paraphrase** | `ExactMatchGrader` (kept as a documented, tested, known-flawed baseline) | `app/services/grading/exact_match.py` | `tests/unit/test_grading.py::test_exact_match_false_fails_a_correct_paraphrase` |
| **Keyword-presence grading is fooled by a sentence using the right words to say the wrong thing** | `KeywordGrader` (same — documented baseline) | `app/services/grading/keyword.py` | `test_keyword_grader_is_fooled_by_an_adversarial_sentence` |
| **LLM-as-judge + explicit multi-dimension rubric** (`core_fact_correct`, `no_false_claims`, `no_unsafe_omission`; a case passes only if every dimension passes) | `LLMJudgeGrader`, `Rubric` model, `AnthropicJudgeProvider` | `app/services/grading/llm_judge.py`, `app/models/rubric.py`, `app/services/judge/anthropic_provider.py` | `test_llm_judge_fails_the_case_the_single_blended_verdict_used_to_excuse` |
| **Judge calibration** — verdicts checked against human verdicts; re-run when the golden set changes or the judge model changes | `CalibrationRun`, `HumanLabeledSample`, `require_calibrated` gate | `app/services/calibration_service.py` | `tests/unit/test_calibration.py` |
| **Dual-trigger continuous scheduling**: on-change (deploy hook) + fixed interval, neither depending on anyone remembering | `POST /webhooks/on-change`; `run_due_suites` background tick | `app/api/routes/webhooks.py`, `app/services/scheduling/tick.py`, `app/jobs/scheduler.py` | `tests/unit/test_scheduling.py`, `tests/integration/test_webhooks_api.py` |
| **Component check vs. end-to-end check** — a check fed frozen context can't see retrieval failures; run both to localize the fault | `run_eval`'s per-case-mode execution + `_localize_faults` | `app/services/eval_engine.py` | `tests/unit/test_eval_engine.py::test_run_eval_localizes_an_upstream_retrieval_fault` |
| **A near-duplicate-SKU retrieval bug** (two visually/textually similar items get confused) | `ENABLE_RETRIEVAL_BUG` toggle in the reference assistant's retrieval | `apps/reference-assistant/app/retrieval.py` | `apps/reference-assistant/tests/test_retrieval.py::test_retrieval_bug_substitutes_the_near_duplicate_twin` |
| **"If this broke silently, who would notice, and when?"** — a written, explicit pre-launch coverage decision with gaps named on purpose | `LaunchCoverageCheck` register | `app/services/coverage_service.py`, `app/api/routes/coverage.py` | `tests/integration/test_coverage_and_alerts_api.py` |
| **A policy question (discount stacking) needs a different rubric/source than a product-fact question** | Per-case `rubric_id` (not a single hardcoded rubric); seed data's `festive-sale-bundle-policy` suite | `app/models/golden_case.py` (`rubric_id`), `database/seed/golden_cases.json` | `scripts/seed_demo.py` (live-run evidence) |
| **Tightened schedule during a high-risk launch window** (hourly vs. a normal 6h) | `ScheduleOverride` | `app/models/suite.py`, `app/services/scheduling/tick.py::_effective_interval_hours` | `tests/unit/test_scheduling.py::test_an_active_schedule_override_tightens_the_interval` |
| **A disclosed gap gets a scheduled re-review, not quietly forgotten** | `re_review_due_at` / `complete_re_review` / `COVERAGE_GAP_DUE` alert | `app/services/coverage_service.py`, `app/services/alert_service.py::check_coverage_gaps_due` | `tests/unit/test_alerts.py::test_coverage_gap_due_alert_fires_once_past_the_re_review_date` |
| **The whole arc compounding in production** (golden set grows from real incidents; detection goes from weeks to hours) | All of the above, seeded with real-world-style incidents | `database/seed/golden_cases.json`, `scripts/seed_demo.py` | Live-run output (see `docs/operations.md`) |

## What's deliberately out of scope

- **Distributed tracing across systems** — a different product surface from this one.
- **Multi-tenant access control** — this is a single-tenant internal tool by design; see
  `docs/architecture.md`'s reasoning.
- **Cost/FinOps tracking** — not part of this platform's job.
