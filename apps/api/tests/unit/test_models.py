import pytest
from sqlalchemy.exc import IntegrityError

from app.models import GoldenCase, ReviewSubmission, Rubric, Suite
from app.models.enums import CaseStatus, CheckMode
from app.models.rubric import DEFAULT_RUBRIC_DIMENSIONS


def test_suite_name_must_be_unique(db_session):
    db_session.add(Suite(name="fabric-and-care"))
    db_session.flush()

    db_session.add(Suite(name="fabric-and-care"))
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()  # the failed flush leaves the session's transaction aborted


def test_golden_case_defaults_to_draft_and_both_check_modes(db_session):
    suite = Suite(name="footwear-sizing")
    db_session.add(suite)
    db_session.flush()

    case = GoldenCase(
        suite_id=suite.id,
        question="Does this come in half sizes?",
        context="SKU FTW-1187 listing text...",
        reference_answer="No, this model is only stocked in full sizes.",
        source="real_complaint",
    )
    db_session.add(case)
    db_session.flush()

    assert case.status == CaseStatus.DRAFT
    assert case.check_mode == CheckMode.BOTH


def test_deleting_suite_cascades_to_its_cases(db_session):
    suite = Suite(name="dupatta-care")
    db_session.add(suite)
    db_session.flush()

    case = GoldenCase(suite_id=suite.id, question="q", source="support_queue")
    db_session.add(case)
    db_session.flush()
    case_id = case.id

    db_session.delete(suite)
    db_session.flush()
    db_session.expire_all()  # force a real DB read, not the stale identity map

    assert db_session.get(GoldenCase, case_id) is None


def test_deleting_case_cascades_to_its_review_submissions(db_session):
    suite = Suite(name="sale-bundle-policy")
    db_session.add(suite)
    db_session.flush()

    case = GoldenCase(suite_id=suite.id, question="Can the coupon stack?", source="manual")
    db_session.add(case)
    db_session.flush()

    submission = ReviewSubmission(
        case_id=case.id, reviewer_name="Draupadi", proposed_answer="No stacking allowed."
    )
    db_session.add(submission)
    db_session.flush()
    submission_id = submission.id

    db_session.delete(case)
    db_session.flush()
    db_session.expire_all()  # force a real DB read, not the stale identity map

    assert db_session.get(ReviewSubmission, submission_id) is None


def test_rubric_stores_dimension_list_as_json(db_session):
    rubric = Rubric(name="default-product-answer-rubric", dimensions=DEFAULT_RUBRIC_DIMENSIONS)
    db_session.add(rubric)
    db_session.flush()
    db_session.expire(rubric)

    reloaded = db_session.get(Rubric, rubric.id)
    keys = {dim["key"] for dim in reloaded.dimensions}
    assert keys == {"core_fact_correct", "no_false_claims", "no_unsafe_omission"}


def test_suite_relationship_exposes_its_cases(db_session):
    suite = Suite(name="chennai-regional-sizing")
    db_session.add(suite)
    db_session.flush()

    db_session.add(GoldenCase(suite_id=suite.id, question="q1", source="beta"))
    db_session.add(GoldenCase(suite_id=suite.id, question="q2", source="beta"))
    db_session.flush()
    db_session.expire(suite)

    assert len(suite.cases) == 2
