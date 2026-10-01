from app.services.grading.base import DimensionResult, GradingResult


class KeywordGrader:
    """Pass if every required keyword/phrase appears somewhere in the
    candidate answer. Also kept as a documented, tested, *known-flawed*
    baseline: it checks whether the words show up, not what they mean, so a
    sentence that uses every required keyword while asserting the exact
    opposite fact still passes — a break-test reproducing exactly that is in
    this module's tests."""

    def grade(
        self,
        *,
        candidate_answer: str,
        required_keywords: list[str],
        **_: object,
    ) -> GradingResult:
        answer_lower = candidate_answer.lower()
        missing = [kw for kw in required_keywords if kw.lower() not in answer_lower]
        passed = not missing
        rationale = (
            "All required keywords present."
            if passed
            else f"Missing required keyword(s): {', '.join(missing)}"
        )
        dimension = DimensionResult(passed=passed, rationale=rationale)
        return GradingResult(passed=passed, dimension_results={"keyword_presence": dimension})
