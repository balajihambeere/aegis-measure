import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.services.sut_adapter.base import ComponentAnswer, EndToEndAnswer, SUTUnavailableError


class HTTPSUTAdapter:
    """Calls a system under test over HTTP using the contract the reference
    assistant (apps/reference-assistant) implements: POST /answer and
    POST /answer_with_context. Any real system can be swapped in by
    pointing REFERENCE_ASSISTANT_URL at it, as long as it implements the
    same two endpoints."""

    def __init__(self, base_url: str, timeout_seconds: float = 30.0):
        self._client = httpx.Client(base_url=base_url, timeout=timeout_seconds)

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
    )
    def _post(self, path: str, json: dict) -> httpx.Response:
        # Deliberately no try/except here: httpx.ConnectError and
        # httpx.TimeoutException must propagate to tenacity unmodified so
        # its retry_if_exception_type check can see them. Catching and
        # re-wrapping them here (as the two public methods below do, once
        # retries are exhausted) would hide them from tenacity and silently
        # disable retrying altogether.
        response = self._client.post(path, json=json)
        response.raise_for_status()
        return response

    def answer(self, question: str) -> EndToEndAnswer:
        """The end-to-end check hits this; a retrieval or network blip here
        is exactly the kind of upstream fault that should be localized, not
        retried away silently for more than a couple of attempts."""
        try:
            response = self._post("/answer", {"question": question})
        except httpx.HTTPError as exc:
            raise SUTUnavailableError(f"SUT /answer call failed: {exc}") from exc
        body = response.json()
        return {"answer": body["answer"], "retrieved_context": body["retrieved_context"]}

    def answer_with_context(self, question: str, context: str) -> ComponentAnswer:
        try:
            response = self._post(
                "/answer_with_context", {"question": question, "context": context}
            )
        except httpx.HTTPError as exc:
            raise SUTUnavailableError(f"SUT /answer_with_context call failed: {exc}") from exc
        body = response.json()
        return {"answer": body["answer"]}
