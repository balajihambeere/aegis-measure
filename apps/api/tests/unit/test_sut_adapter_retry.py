"""Production reliability: a transient network blip talking to the system
under test should be retried, not immediately surfaced as a failure.

This module exists because of a real bug caught here: the first version of
HTTPSUTAdapter wrapped httpx.ConnectError into SUTUnavailableError *inside*
the retried method, before tenacity's retry_if_exception_type ever saw the
original exception — since SUTUnavailableError doesn't match the retry
predicate, no retry ever happened. Splitting the raw httpx call into its own
retried helper, with the SUTUnavailableError wrapping only in the outer
method, is what actually fixes it."""

from unittest.mock import MagicMock

import httpx
import pytest

from app.services.sut_adapter.base import SUTUnavailableError
from app.services.sut_adapter.http_adapter import HTTPSUTAdapter


def test_answer_retries_on_connect_error_then_succeeds(monkeypatch):
    adapter = HTTPSUTAdapter(base_url="http://sut.invalid")

    success_response = MagicMock()
    success_response.raise_for_status.return_value = None
    success_response.json.return_value = {"answer": "a", "retrieved_context": "c"}

    call_count = {"n": 0}

    def flaky_post(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise httpx.ConnectError("connection refused")
        return success_response

    monkeypatch.setattr(adapter._client, "post", flaky_post)
    # tenacity's exponential-backoff wait strategy is baked in at decoration
    # time, so there's no wait_exponential object left to patch here; patch
    # its actual sleep call instead so the test doesn't spend real seconds.
    monkeypatch.setattr("tenacity.nap.time.sleep", lambda *_: None)

    result = adapter.answer("does this need dry cleaning?")

    assert call_count["n"] == 3  # failed twice, succeeded on the third attempt
    assert result == {"answer": "a", "retrieved_context": "c"}


def test_answer_wraps_exhausted_retries_as_sut_unavailable(monkeypatch):
    adapter = HTTPSUTAdapter(base_url="http://sut.invalid")
    call_count = {"n": 0}

    def always_fails(*args, **kwargs):
        call_count["n"] += 1
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(adapter._client, "post", always_fails)
    monkeypatch.setattr("tenacity.nap.time.sleep", lambda *_: None)

    with pytest.raises(SUTUnavailableError):
        adapter.answer("does this need dry cleaning?")

    assert call_count["n"] == 3  # stop_after_attempt(3) — all three used
