import json

import openai
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.services.judge.prompts import build_judge_prompt

TOOL_NAME = "record_rubric_verdict"


def _tool_schema(dimensions: list[dict]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": TOOL_NAME,
            "description": (
                "Record a pass/fail verdict with a short rationale for each rubric dimension."
            ),
            "parameters": {
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
        },
    }


class OpenAIJudgeProvider:
    """The same LLM-as-judge contract as AnthropicJudgeProvider, backed by
    the OpenAI API — selected when LLM_PROVIDER=openai. max_retries is
    configurable (unlike the Anthropic provider's fixed 3) since it's driven
    by an explicit OPENAI_MAX_RETRIES setting."""

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: float = 20.0,
        max_retries: int = 2,
    ):
        self._client = openai.OpenAI(api_key=api_key, timeout=timeout_seconds)
        self._model = model
        # A Retrying instance built around the *call*, not a decorator, so
        # max_retries can come from settings instead of being baked in at
        # import time. The retried step (_call) must not catch and re-wrap
        # these exceptions itself — see http_adapter.py's regression test
        # for the exact bug that mistake causes (retries silently disabled).
        self._retrying = Retrying(
            reraise=True,
            stop=stop_after_attempt(max_retries + 1),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(
                (openai.APIConnectionError, openai.RateLimitError, openai.APITimeoutError)
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
        return self._retrying(self._call, prompt, dimensions)

    def _call(self, prompt: str, dimensions: list[dict]) -> dict[str, dict]:
        # The SDK's overloads expect typed TypedDicts for messages/tools and
        # a Literal model name; we intentionally accept any model string
        # (configurable via OPENAI_MODEL) and build the tool schema
        # dynamically from the rubric's dimensions.
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],  # type: ignore[list-item]
            tools=[_tool_schema(dimensions)],  # type: ignore[list-item]
            tool_choice={"type": "function", "function": {"name": TOOL_NAME}},  # type: ignore[arg-type]
        )  # type: ignore[call-overload]
        tool_calls = response.choices[0].message.tool_calls
        if not tool_calls:
            raise RuntimeError("Judge model did not return a tool call")
        result: dict = json.loads(tool_calls[0].function.arguments)
        return result
