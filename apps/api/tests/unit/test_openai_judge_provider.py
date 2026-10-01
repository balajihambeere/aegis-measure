"""Production reliability: the OpenAI judge provider must actually retry
transient failures, the same way the Anthropic one and the SUT adapter do.
Built around a Retrying(...) call wrapping _call(...) specifically so
_call never catches and re-wraps the retryable exceptions itself — that
exact mistake in an earlier version of HTTPSUTAdapter silently disabled its
retries (see tests/unit/test_sut_adapter_retry.py)."""

from unittest.mock import MagicMock

import openai
import pytest

from app.services.judge.openai_provider import OpenAIJudgeProvider

DIMENSIONS = [{"key": "core_fact_correct", "description": "states the fact"}]


def _tool_call_response(arguments_json: str) -> MagicMock:
    tool_call = MagicMock()
    tool_call.function.arguments = arguments_json
    message = MagicMock()
    message.tool_calls = [tool_call]
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


def test_grade_dimensions_retries_on_connection_error_then_succeeds(monkeypatch):
    provider = OpenAIJudgeProvider(api_key="test-key", model="gpt-4o-mini", max_retries=2)

    success = _tool_call_response('{"core_fact_correct": {"passed": true, "rationale": "ok"}}')
    call_count = {"n": 0}

    def flaky_create(**kwargs):
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise openai.APIConnectionError(request=MagicMock())
        return success

    monkeypatch.setattr(provider._client.chat.completions, "create", flaky_create)
    monkeypatch.setattr("tenacity.nap.time.sleep", lambda *_: None)

    result = provider.grade_dimensions(
        question="q",
        context="c",
        reference_answer="r",
        candidate_answer="a",
        dimensions=DIMENSIONS,
    )

    assert call_count["n"] == 3
    assert result == {"core_fact_correct": {"passed": True, "rationale": "ok"}}


def test_grade_dimensions_raises_after_exhausting_configured_retries(monkeypatch):
    provider = OpenAIJudgeProvider(api_key="test-key", model="gpt-4o-mini", max_retries=1)
    call_count = {"n": 0}

    def always_fails(**kwargs):
        call_count["n"] += 1
        raise openai.APIConnectionError(request=MagicMock())

    monkeypatch.setattr(provider._client.chat.completions, "create", always_fails)
    monkeypatch.setattr("tenacity.nap.time.sleep", lambda *_: None)

    with pytest.raises(openai.APIConnectionError):
        provider.grade_dimensions(
            question="q",
            context="c",
            reference_answer="r",
            candidate_answer="a",
            dimensions=DIMENSIONS,
        )

    assert call_count["n"] == 2  # max_retries=1 -> 2 total attempts
