from app.services.grading.base import DimensionResult, GradingResult
from app.services.judge.base import JudgeProvider


class LLMJudgeGrader:
    """The production grader: a judge model scored against an explicit
    rubric, not a single blended verdict. A case passes only if every
    dimension passes."""

    def __init__(self, provider: JudgeProvider):
        self._provider = provider

    def grade(
        self,
        *,
        question: str,
        context: str | None,
        reference_answer: str,
        candidate_answer: str,
        rubric_dimensions: list[dict],
        **_: object,
    ) -> GradingResult:
        raw = self._provider.grade_dimensions(
            question=question,
            context=context,
            reference_answer=reference_answer,
            candidate_answer=candidate_answer,
            dimensions=rubric_dimensions,
        )
        dimension_results = {
            key: DimensionResult(passed=bool(v["passed"]), rationale=v.get("rationale", ""))
            for key, v in raw.items()
        }
        passed = all(d.passed for d in dimension_results.values())
        return GradingResult(passed=passed, dimension_results=dimension_results)
