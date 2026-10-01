from typing import Protocol


class JudgeProvider(Protocol):
    """A second AI system, a separate model call, given the question, the
    reference answer, and the actual answer, asked to judge whether the
    actual answer was correct — scored per rubric dimension, not as one
    blended verdict. Swappable so the judge model/vendor isn't locked in."""

    def grade_dimensions(
        self,
        *,
        question: str,
        context: str | None,
        reference_answer: str,
        candidate_answer: str,
        dimensions: list[dict],
    ) -> dict[str, dict]:
        """Returns {dimension_key: {"passed": bool, "rationale": str}, ...}
        with exactly one entry per item in `dimensions`."""
        ...
