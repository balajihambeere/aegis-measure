import anthropic
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.services.judge.prompts import build_judge_prompt

TOOL_NAME = "record_rubric_verdict"


def _tool_schema(dimensions: list[dict]) -> dict:
    return {
        "name": TOOL_NAME,
        "description": (
            "Record a pass/fail verdict with a short rationale for each rubric dimension."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                dim["key"]: {
                    "type": "object",
                    "properties": {
                        "passed": {"type": "boolean"},
                        "rationale": {"type": "string"},
                    },
                    "required": ["passed", "rationale"],
                }
                for dim in dimensions
            },
            "required": [dim["key"] for dim in dimensions],
        },
    }


class AnthropicJudgeProvider:
    """The LLM-as-judge grader, backed by the Claude API. Retries transient
    failures (network errors, rate limits) rather than silently treating a
    dropped judge call as a passing or failing verdict — an eval result must
    be either real or an explicit error, never a guess."""

    def __init__(self, api_key: str, model: str, timeout_seconds: float = 30.0):
        self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout_seconds)
        self._model = model

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(
            (anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.APITimeoutError)
        ),
    )
    def grade_dimensions(
        self,
        *,
        question: str,
        context: str | None,
        reference_answer: str,
        candidate_answer: str,
        dimensions: list[dict],
    ) -> dict[str, dict]:
        prompt = build_judge_prompt(
            question=question,
            context=context,
            reference_answer=reference_answer,
            candidate_answer=candidate_answer,
            dimensions=dimensions,
        )
        # The SDK's overloads expect a Literal model name and typed
        # TypedDicts for tools/tool_choice; we intentionally accept any
        # model string (configurable via JUDGE_MODEL) and build the tool
        # schema dynamically from the rubric's dimensions.
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            tools=[_tool_schema(dimensions)],  # type: ignore[arg-type]
            tool_choice={"type": "tool", "name": TOOL_NAME},
            messages=[{"role": "user", "content": prompt}],
        )  # type: ignore[call-overload]
        for block in response.content:
            if block.type == "tool_use":
                result: dict = block.input  # type: ignore[assignment]
                return result
        raise RuntimeError("Judge model did not return a tool_use block")
