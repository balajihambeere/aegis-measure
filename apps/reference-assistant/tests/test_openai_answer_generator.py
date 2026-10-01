"""Production reliability: the OpenAI answer generator must actually retry
transient failures, mirroring the Anthropic generator and the api service's
judge providers."""

from unittest.mock import MagicMock

import openai
import pytest

from app.llm_provider import OpenAIAnswerGenerator


def _text_response(text: str) -> MagicMock:
    message = MagicMock()
    message.content = text
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


def test_generate_retries_on_connection_error_then_succeeds(monkeypatch):
    generator = OpenAIAnswerGenerator(api_key="test-key", model="gpt-4o-mini", max_retries=2)

    call_count = {"n": 0}

    def flaky_create(**kwargs):
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise openai.APIConnectionError(request=MagicMock())
        return _text_response("Pure silk — dry clean only.")

    monkeypatch.setattr(generator._client.chat.completions, "create", flaky_create)
    monkeypatch.setattr("tenacity.nap.time.sleep", lambda *_: None)

    result = generator.generate(question="q", context="c")

    assert call_count["n"] == 3
    assert result == "Pure silk — dry clean only."


def test_generate_raises_after_exhausting_configured_retries(monkeypatch):
    generator = OpenAIAnswerGenerator(api_key="test-key", model="gpt-4o-mini", max_retries=1)
    call_count = {"n": 0}

    def always_fails(**kwargs):
        call_count["n"] += 1
        raise openai.APIConnectionError(request=MagicMock())

    monkeypatch.setattr(generator._client.chat.completions, "create", always_fails)
    monkeypatch.setattr("tenacity.nap.time.sleep", lambda *_: None)

    with pytest.raises(openai.APIConnectionError):
        generator.generate(question="q", context="c")

    assert call_count["n"] == 2


def test_missing_api_key_raises_immediately():
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        OpenAIAnswerGenerator(api_key="", model="gpt-4o-mini")
