"""A case only belongs in the golden set once two independent reviewers
agree. These tests encode that rule directly against the API."""


def _create_suite(client, name="fabric-and-care"):
    resp = client.post("/suites", json={"name": name, "description": "fabric/care cases"})
    assert resp.status_code == 201
    return resp.json()


def _create_case(client, suite_id, question="Does SKU BPS-2214 need dry cleaning?"):
    resp = client.post(
        "/cases",
        json={
            "suite_id": suite_id,
            "question": question,
            "context": "SKU BPS-2214: pure mulberry silk, block print.",
            "source": "real_complaint",
        },
    )
    assert resp.status_code == 201
    return resp.json()


def test_full_approval_flow_when_reviewers_agree(client):
    suite = _create_suite(client)
    case = _create_case(client, suite["id"])
    case_id = case["id"]
    assert case["status"] == "draft"

    r1 = client.post(
        f"/cases/{case_id}/reviews",
        json={"reviewer_name": "Chitrangada", "proposed_answer": "Pure silk — dry clean only."},
    )
    assert r1.status_code == 201

    # Blind contract: before the second review lands, the status endpoint
    # must not reveal the first reviewer's proposed answer.
    status_after_one = client.get(f"/cases/{case_id}/reviews").json()
    assert status_after_one["submission_count"] == 1
    assert status_after_one["submissions"] is None

    r2 = client.post(
        f"/cases/{case_id}/reviews",
        json={
            "reviewer_name": "merchandising-lead",
            "proposed_answer": "Dry clean only — pure silk fabric.",
        },
    )
    assert r2.status_code == 201

    status_after_two = client.get(f"/cases/{case_id}/reviews").json()
    assert status_after_two["submission_count"] == 2
    assert {s["reviewer_name"] for s in status_after_two["submissions"]} == {
        "Chitrangada",
        "merchandising-lead",
    }

    resolve = client.post(
        f"/cases/{case_id}/resolve",
        json={
            "decision": "approve",
            "resolved_by": "Vyasa",
            "reference_answer": "Pure silk — dry clean only. Do not machine or hand wash.",
        },
    )
    assert resolve.status_code == 200
    approved = resolve.json()
    assert approved["status"] == "approved"
    assert approved["reference_answer"].startswith("Pure silk")
    assert approved["resolved_by"] == "Vyasa"


def test_disagreement_flags_needs_resolution_instead_of_silently_picking_one(client):
    """A listing that hedges produces two reviewers who each give a
    defensible but different answer. That's not a grading bug to paper
    over — the case gets flagged, not auto-approved."""
    suite = _create_suite(client, name="dupatta-care")
    case = _create_case(client, suite["id"], question="Can this kurta go in the washing machine?")
    case_id = case["id"]

    client.post(
        f"/cases/{case_id}/reviews",
        json={"reviewer_name": "Chitrangada", "proposed_answer": "Machine-washable, gentle cycle."},
    )
    client.post(
        f"/cases/{case_id}/reviews",
        json={"reviewer_name": "merchandising-lead", "proposed_answer": "Hand-wash only."},
    )

    resolve = client.post(
        f"/cases/{case_id}/resolve",
        json={
            "decision": "needs_resolution",
            "resolved_by": "Vyasa",
            "notes": "Listing hedges between 'easy-care' and 'gentle wash' — source is ambiguous.",
        },
    )
    assert resolve.status_code == 200
    body = resolve.json()
    assert body["status"] == "needs_resolution"
    assert body["reference_answer"] is None


def test_second_review_must_come_from_a_different_reviewer(client):
    suite = _create_suite(client, name="footwear-sizing")
    case = _create_case(client, suite["id"], question="Does this come in half sizes?")
    case_id = case["id"]

    client.post(
        f"/cases/{case_id}/reviews",
        json={"reviewer_name": "Chitrangada", "proposed_answer": "No, full sizes only."},
    )
    dup = client.post(
        f"/cases/{case_id}/reviews",
        json={"reviewer_name": "Chitrangada", "proposed_answer": "No, full sizes only, really."},
    )
    assert dup.status_code == 409


def test_cannot_resolve_before_two_reviews_submitted(client):
    suite = _create_suite(client, name="sale-bundle-policy")
    case = _create_case(client, suite["id"], question="Can the coupon stack with the bundle?")
    case_id = case["id"]

    client.post(
        f"/cases/{case_id}/reviews",
        json={"reviewer_name": "Draupadi", "proposed_answer": "No stacking allowed."},
    )

    resolve = client.post(
        f"/cases/{case_id}/resolve",
        json={"decision": "approve", "resolved_by": "Vyasa", "reference_answer": "No stacking."},
    )
    assert resolve.status_code == 409


def test_only_an_approved_case_can_be_retired(client):
    suite = _create_suite(client, name="chennai-regional-sizing")
    case = _create_case(client, suite["id"], question="Is regional size 26 the same for kids?")
    case_id = case["id"]

    draft_retire = client.post(f"/cases/{case_id}/retire")
    assert draft_retire.status_code == 409

    client.post(
        f"/cases/{case_id}/reviews",
        json={"reviewer_name": "Chitrangada", "proposed_answer": "No, separate scale."},
    )
    client.post(
        f"/cases/{case_id}/reviews",
        json={"reviewer_name": "vendor-rep", "proposed_answer": "No, kids use a different table."},
    )
    client.post(
        f"/cases/{case_id}/resolve",
        json={
            "decision": "approve",
            "resolved_by": "Vyasa",
            "reference_answer": "No — children's regional sizing uses a separate table.",
        },
    )

    retire = client.post(f"/cases/{case_id}/retire")
    assert retire.status_code == 200
    assert retire.json()["status"] == "retired"


def test_list_cases_filters_by_suite_and_status(client):
    suite_a = _create_suite(client, name="suite-a")
    suite_b = _create_suite(client, name="suite-b")
    _create_case(client, suite_a["id"], question="q-a1")
    _create_case(client, suite_b["id"], question="q-b1")

    only_a = client.get("/cases", params={"suite_id": suite_a["id"]}).json()
    assert len(only_a) == 1
    assert only_a[0]["question"] == "q-a1"

    only_draft = client.get("/cases", params={"status": "draft"}).json()
    assert all(c["status"] == "draft" for c in only_draft)
    assert len(only_draft) == 2


def test_create_case_for_unknown_suite_returns_404(client):
    import uuid

    resp = client.post(
        "/cases",
        json={"suite_id": str(uuid.uuid4()), "question": "q", "source": "manual"},
    )
    assert resp.status_code == 404


def test_creating_a_suite_with_a_duplicate_name_returns_409_not_500(client):
    _create_suite(client, name="duplicate-suite-name")
    resp = client.post("/suites", json={"name": "duplicate-suite-name"})
    assert resp.status_code == 409
