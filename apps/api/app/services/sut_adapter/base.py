from typing import Protocol, TypedDict


class EndToEndAnswer(TypedDict):
    answer: str
    retrieved_context: str


class ComponentAnswer(TypedDict):
    answer: str


class SUTAdapter(Protocol):
    """The two call shapes a system under test must support: answer a
    question using its own retrieval (end-to-end check), or answer a
    question given frozen context (component check)."""

    def answer(self, question: str) -> EndToEndAnswer: ...

    def answer_with_context(self, question: str, context: str) -> ComponentAnswer: ...


class SUTUnavailableError(Exception):
    """The system under test could not be reached or returned an error —
    distinct from a grading failure, so callers can tell 'the SUT is down'
    apart from 'the SUT answered and was wrong'."""
