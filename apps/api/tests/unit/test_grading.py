"""Grading evolved from exact-match -> keyword -> LLM-as-judge+rubric because
the first two both break in specific, reproducible ways. These tests
reproduce each grader's known failure mode directly."""

from app.services.grading.exact_match import ExactMatchGrader
from app.services.grading.keyword import KeywordGrader
from app.services.grading.llm_judge import LLMJudgeGrader
from app.services.judge.base import JudgeProvider


def test_exact_match_false_fails_a_correct_paraphrase():
    grader = ExactMatchGrader()
    result = grader.grade(
        reference_answer="Machine-wash cold, tumble dry low.",
        candidate_answer=(
            "You can machine wash this on a cold setting, then tumble dry on low heat."
        ),
    )
    # Same instruction, same correctness — exact-match still fails it. This
    # is the grader's known flaw, not a bug in this test.
    assert result.passed is False


def test_exact_match_passes_identical_text():
    grader = ExactMatchGrader()
    result = grader.grade(
        reference_answer="Pure silk — dry clean only.",
        candidate_answer="Pure silk — dry clean only.",
    )
    assert result.passed is True


def test_keyword_grader_is_fooled_by_an_adversarial_sentence():
    """'This isn't pure silk, so unlike our silk pieces, you don't need to
    dry clean it — a normal machine wash on cold is fine.' contains both
    required keywords while asserting the dangerous opposite of the correct
    care instruction. The keyword grader cannot tell the difference."""
    grader = KeywordGrader()
    result = grader.grade(
        candidate_answer=(
            "This isn't pure silk, so unlike our silk pieces, you don't need to "
            "dry clean it — a normal machine wash on cold is fine."
        ),
        required_keywords=["silk", "dry clean"],
    )
    assert result.passed is True  # the flaw: this should fail, but doesn't


def test_keyword_grader_correctly_fails_when_a_keyword_is_missing():
    grader = KeywordGrader()
    result = grader.grade(
        candidate_answer="Machine wash cold is fine for this piece.",
        required_keywords=["silk", "dry clean"],
    )
    assert result.passed is False
    assert "silk" in result.dimension_results["keyword_presence"].rationale


class _ScriptedJudgeProvider:
    """Test double implementing JudgeProvider with a scripted response,
    standing in for a real Claude call."""

    def __init__(self, response: dict[str, dict]):
        self._response = response

    def grade_dimensions(self, **_: object) -> dict[str, dict]:
        return self._response


def test_llm_judge_fails_the_case_the_single_blended_verdict_used_to_excuse():
    """The stole-detail answer got the core fact right but invented an
    unrelated detail. A single blended verdict passed it; the three-part
    rubric must fail it on no_false_claims alone."""
    provider: JudgeProvider = _ScriptedJudgeProvider(
        {
            "core_fact_correct": {"passed": True, "rationale": "Silk, dry clean stated correctly."},
            "no_false_claims": {
                "passed": False,
                "rationale": "Stole detail isn't in this SKU's listing at all.",
            },
            "no_unsafe_omission": {"passed": True, "rationale": "Nothing unsafe omitted."},
        }
    )
    grader = LLMJudgeGrader(provider)
    result = grader.grade(
        question="Does SKU BPS-2214 need dry cleaning?",
        context="SKU BPS-2214: pure silk, block print.",
        reference_answer="Pure silk — dry clean only.",
        candidate_answer=(
            "Pure silk — dry clean only. This piece also pairs well with a "
            "matching stole, which is machine-washable separately."
        ),
        rubric_dimensions=[
            {"key": "core_fact_correct", "description": "..."},
            {"key": "no_false_claims", "description": "..."},
            {"key": "no_unsafe_omission", "description": "..."},
        ],
    )
    assert result.passed is False
    assert result.dimension_results["core_fact_correct"].passed is True
    assert result.dimension_results["no_false_claims"].passed is False


def test_llm_judge_passes_only_when_every_dimension_passes():
    provider: JudgeProvider = _ScriptedJudgeProvider(
        {
            "core_fact_correct": {"passed": True, "rationale": "Correct."},
            "no_false_claims": {"passed": True, "rationale": "Nothing false."},
            "no_unsafe_omission": {"passed": True, "rationale": "Nothing missing."},
        }
    )
    grader = LLMJudgeGrader(provider)
    result = grader.grade(
        question="q",
        context="c",
        reference_answer="r",
        candidate_answer="a",
        rubric_dimensions=[
            {"key": "core_fact_correct", "description": "..."},
            {"key": "no_false_claims", "description": "..."},
            {"key": "no_unsafe_omission", "description": "..."},
        ],
    )
    assert result.passed is True
