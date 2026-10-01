import uuid

from sqlalchemy.orm import Session

from app.models.common import utcnow
from app.models.enums import CaseStatus
from app.models.golden_case import GoldenCase, ReviewSubmission
from app.schemas.golden_case import (
    CaseResolutionRequest,
    ReviewStatusRead,
    ReviewSubmissionCreate,
    ReviewSubmissionRead,
)
from app.services.case_service import get_case
from app.services.errors import ConflictError

MAX_INDEPENDENT_REVIEWS = 2


def submit_review(
    db: Session, case_id: uuid.UUID, data: ReviewSubmissionCreate
) -> ReviewSubmission:
    """A case only belongs in the golden set if two people who know the
    subject, working *independently*, would write down the same answer. This
    enforces: no more than two submissions, and the second must come from a
    genuinely different reviewer — not the same person submitting twice."""
    case = get_case(db, case_id)

    if case.status not in (CaseStatus.DRAFT, CaseStatus.NEEDS_RESOLUTION):
        raise ConflictError(
            f"Case {case_id} is {case.status.value}; only draft or "
            "needs-resolution cases accept new review submissions"
        )

    existing = case.review_submissions
    if len(existing) >= MAX_INDEPENDENT_REVIEWS:
        raise ConflictError(
            f"Case {case_id} already has {MAX_INDEPENDENT_REVIEWS} independent "
            "review submissions"
        )
    if any(s.reviewer_name == data.reviewer_name for s in existing):
        raise ConflictError(
            f"'{data.reviewer_name}' already submitted a review for this case — "
            "the second review must come from a different, independent reviewer"
        )

    submission = ReviewSubmission(
        case_id=case_id,
        reviewer_name=data.reviewer_name,
        proposed_answer=data.proposed_answer,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


def get_review_status(db: Session, case_id: uuid.UUID) -> ReviewStatusRead:
    """Blind-until-both-submitted: while fewer than two independent reviews
    exist, callers can see *that* a submission was recorded and *who* made
    it, but not the proposed answer text — otherwise a second reviewer could
    anchor on the first reviewer's wording instead of judging independently."""
    case = get_case(db, case_id)
    submissions = case.review_submissions

    if len(submissions) < MAX_INDEPENDENT_REVIEWS:
        return ReviewStatusRead(
            case_id=case_id,
            submission_count=len(submissions),
            reviewer_names=[s.reviewer_name for s in submissions],
            submissions=None,
        )

    return ReviewStatusRead(
        case_id=case_id,
        submission_count=len(submissions),
        reviewer_names=[s.reviewer_name for s in submissions],
        submissions=[ReviewSubmissionRead.model_validate(s) for s in submissions],
    )


def resolve_case(db: Session, case_id: uuid.UUID, data: CaseResolutionRequest) -> GoldenCase:
    """Agreement between two independent reviewers is a human judgment call,
    not a string-equality check (that mistake belongs to the exact-match
    grader, applied to the wrong problem). A moderator looks at both
    submissions and either approves the
    case with a reference answer, or flags it needs_resolution because the
    underlying source material itself is ambiguous."""
    case = get_case(db, case_id)

    if case.status not in (CaseStatus.DRAFT, CaseStatus.NEEDS_RESOLUTION):
        raise ConflictError(f"Case {case_id} is {case.status.value}; cannot resolve it again")

    if len(case.review_submissions) < MAX_INDEPENDENT_REVIEWS:
        raise ConflictError(
            f"Case {case_id} cannot be resolved until {MAX_INDEPENDENT_REVIEWS} "
            "independent reviews have been submitted"
        )

    if data.decision == "approve":
        if not data.reference_answer:
            raise ConflictError("reference_answer is required to approve a case")
        case.reference_answer = data.reference_answer
        case.status = CaseStatus.APPROVED
    else:
        case.status = CaseStatus.NEEDS_RESOLUTION

    case.resolved_by = data.resolved_by
    case.resolved_at = utcnow()
    case.resolution_notes = data.notes

    db.commit()
    db.refresh(case)
    return case
