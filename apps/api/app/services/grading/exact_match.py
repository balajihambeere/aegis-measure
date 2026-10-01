from app.services.grading.base import DimensionResult, GradingResult


class ExactMatchGrader:
    """Character-for-character comparison against the reference answer. Kept
    here as a documented, tested, *known-flawed* baseline — not the
    production grader. It false-fails any answer that states the same fact
    in different words, which is exactly the failure this class's test suite
    reproduces."""

    def grade(self, *, reference_answer: str, candidate_answer: str, **_: object) -> GradingResult:
        passed = reference_answer.strip() == candidate_answer.strip()
        dimension = DimensionResult(
            passed=passed,
            rationale="Exact string match." if passed else "Text differs from reference answer.",
        )
        return GradingResult(passed=passed, dimension_results={"exact_match": dimension})
