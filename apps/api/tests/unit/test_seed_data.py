"""The demo/seed data (database/seed/golden_cases.json) is the project's
primary evidence that it implements real-world-style incidents, not
contrived examples. This just guards its structure so a future edit can't
silently break scripts/seed_demo.py."""

import json
from pathlib import Path

SEED_PATH = (
    Path(__file__).resolve().parents[4] / "database" / "seed" / "golden_cases.json"
)


def _load_seed() -> dict:
    return json.loads(SEED_PATH.read_text())


def test_seed_file_exists_and_parses():
    assert SEED_PATH.exists(), f"expected seed data at {SEED_PATH}"
    seed = _load_seed()
    assert "suites" in seed


def test_every_suite_has_approvable_cases():
    seed = _load_seed()
    assert len(seed["suites"]) >= 5  # one per major incident scenario

    for suite in seed["suites"]:
        assert suite["name"]
        assert suite["default_schedule_interval_hours"] > 0
        assert len(suite["cases"]) >= 1
        for case in suite["cases"]:
            assert case["question"]
            assert case["reference_answer"]
            assert len(case["reviewers"]) == 2, "exactly two independent reviewers"
            assert case["reviewers"][0] != case["reviewers"][1]
            assert case["check_mode"] in ("component", "end_to_end", "both")


def test_coverage_checks_reference_a_real_suite():
    seed = _load_seed()
    suite_names = {s["name"] for s in seed["suites"]}
    for check in seed.get("coverage_checks", []):
        assert check["linked_suite"] in suite_names
        assert check["coverage_status"] in ("covered", "partial", "none")
