def test_coverage_check_create_and_complete_re_review(client):
    suite = client.post("/suites", json={"name": "festive-sale-bundle-policy"}).json()

    created = client.post(
        "/coverage-checks",
        json={
            "feature_name": "festive-sale-bundle-and-gift-wrap",
            "launch_date": "2026-09-20",
            "linked_suite_id": suite["id"],
            "declared_gaps": ["children's sizing not covered yet"],
            "coverage_status": "partial",
            "answered_by": "Vyasa",
            "re_review_due_at": "2026-09-28",
        },
    )
    assert created.status_code == 201
    check = created.json()
    assert check["re_review_completed_at"] is None

    completed = client.post(f"/coverage-checks/{check['id']}/complete-re-review")
    assert completed.status_code == 200
    assert completed.json()["re_review_completed_at"] is not None

    # Can't complete a re-review twice.
    again = client.post(f"/coverage-checks/{check['id']}/complete-re-review")
    assert again.status_code == 409


def test_alerts_list_and_acknowledge(client):
    # No alerts yet for a brand new suite.
    suite = client.post("/suites", json={"name": "alerts-api-test-suite"}).json()
    resp = client.get("/alerts", params={"suite_id": suite["id"]})
    assert resp.status_code == 200
    assert resp.json() == []
