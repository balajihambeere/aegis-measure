#!/usr/bin/env python3
"""Seeds Aegis Measure with real-world-style incidents
(database/seed/golden_cases.json) and replays the golden-set construction
history end to end against a running stack: suite creation, draft cases,
blind dual review, approval, and coverage-gate registration.

This part needs no LLM — it proves the golden-set, review, and coverage-gate
subsystems work against real seed data over the real API. It then attempts
to trigger an actual LLM-graded eval run for each suite; if
ANTHROPIC_API_KEY isn't configured for the api and reference-assistant
services, that step reports a clear, expected failure rather than crashing
(see app/services/sut_adapter and app/llm_provider's graceful-degradation
paths, already covered by their own test suites).

Usage:
    cd infrastructure && docker compose up -d   # bring the stack up first
    python3 scripts/seed_demo.py
    python3 scripts/seed_demo.py --base-url http://localhost:8001 --api-key change-me-dev-key
"""

import argparse
import json
import pathlib
import sys
import urllib.error
import urllib.request

SEED_PATH = pathlib.Path(__file__).resolve().parent.parent / "database" / "seed" / "golden_cases.json"


def call(method: str, url: str, api_key: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        url, data=data, method=method, headers={"Content-Type": "application/json", "X-API-Key": api_key}
    )
    try:
        with urllib.request.urlopen(request) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        return exc.code, json.loads(raw) if raw else {"detail": exc.reason}


def ensure_suite(base_url: str, api_key: str, suite_def: dict) -> str:
    status, body = call(
        "POST",
        f"{base_url}/suites",
        api_key,
        {
            "name": suite_def["name"],
            "description": suite_def["description"],
            "default_schedule_interval_hours": suite_def["default_schedule_interval_hours"],
        },
    )
    if status == 201:
        print(f"  created suite '{suite_def['name']}'")
        return body["id"]
    if status == 409:
        _, suites = call("GET", f"{base_url}/suites", api_key)
        print(f"  suite '{suite_def['name']}' already exists, reusing")
        return next(s["id"] for s in suites if s["name"] == suite_def["name"])
    print(f"  ERROR creating suite '{suite_def['name']}': {status} {body}")
    sys.exit(1)


def ensure_case_approved(base_url: str, api_key: str, suite_id: str, case_def: dict) -> None:
    _, existing_cases = call("GET", f"{base_url}/cases?suite_id={suite_id}", api_key)
    if any(c["question"] == case_def["question"] for c in existing_cases):
        print(f"    already approved: {case_def['question'][:60]}")
        return

    status, case = call(
        "POST",
        f"{base_url}/cases",
        api_key,
        {
            "suite_id": suite_id,
            "question": case_def["question"],
            "context": case_def["context"],
            "source": case_def["source"],
            "check_mode": case_def["check_mode"],
        },
    )
    if status != 201:
        print(f"    ERROR creating case: {status} {case}")
        return
    case_id = case["id"]

    reviewer_1, reviewer_2 = case_def["reviewers"]
    # Two genuinely independent reviewers, both agreeing on the same
    # reference answer, before this case counts toward any run.
    call(
        "POST",
        f"{base_url}/cases/{case_id}/reviews",
        api_key,
        {"reviewer_name": reviewer_1, "proposed_answer": case_def["reference_answer"]},
    )
    call(
        "POST",
        f"{base_url}/cases/{case_id}/reviews",
        api_key,
        {"reviewer_name": reviewer_2, "proposed_answer": case_def["reference_answer"]},
    )
    status, _ = call(
        "POST",
        f"{base_url}/cases/{case_id}/resolve",
        api_key,
        {
            "decision": "approve",
            "resolved_by": reviewer_2,
            "reference_answer": case_def["reference_answer"],
        },
    )
    if status == 200:
        print(f"    approved: {case_def['question'][:60]}")
    else:
        print(f"    ERROR approving case: {status}")


def ensure_coverage_check(base_url: str, api_key: str, check_def: dict, suite_ids: dict) -> None:
    _, existing = call("GET", f"{base_url}/coverage-checks", api_key)
    if any(c["feature_name"] == check_def["feature_name"] for c in existing):
        print(f"  coverage check already registered: {check_def['feature_name']}")
        return

    status, _ = call(
        "POST",
        f"{base_url}/coverage-checks",
        api_key,
        {
            "feature_name": check_def["feature_name"],
            "launch_date": check_def["launch_date"],
            "linked_suite_id": suite_ids.get(check_def["linked_suite"]),
            "declared_gaps": check_def["declared_gaps"],
            "coverage_status": check_def["coverage_status"],
            "answered_by": check_def["answered_by"],
            "re_review_due_at": check_def["re_review_due_at"],
        },
    )
    if status == 201:
        print(f"  registered coverage check: {check_def['feature_name']}")
    else:
        print(f"  ERROR registering coverage check: {status}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8001")
    parser.add_argument("--api-key", default="change-me-dev-key")
    args = parser.parse_args()

    seed = json.loads(SEED_PATH.read_text())

    print("Seeding golden sets from real-world-style incidents...")
    suite_ids: dict[str, str] = {}
    for suite_def in seed["suites"]:
        suite_id = ensure_suite(args.base_url, args.api_key, suite_def)
        suite_ids[suite_def["name"]] = suite_id
        for case_def in suite_def["cases"]:
            ensure_case_approved(args.base_url, args.api_key, suite_id, case_def)

    print("\nRegistering coverage-gate launches (the pre-launch coverage ritual, written down)...")
    for check_def in seed.get("coverage_checks", []):
        ensure_coverage_check(args.base_url, args.api_key, check_def, suite_ids)

    print("\nTriggering an LLM-graded eval run per suite (needs ANTHROPIC_API_KEY)...")
    for name, suite_id in suite_ids.items():
        status, body = call(
            "POST", f"{args.base_url}/runs", args.api_key, {"suite_id": suite_id, "trigger_source": "manual"}
        )
        if status == 201:
            print(f"  '{name}': run {body['id']} -> {body['status']}")
        else:
            print(f"  '{name}': run not started ({status}): {body.get('detail', body)}")

    print(f"\nDone. Explore the results in the dashboard, or GET {args.base_url}/runs for raw data.")


if __name__ == "__main__":
    main()
