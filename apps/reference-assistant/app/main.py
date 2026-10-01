from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.deps import get_answer_generator
from app.llm_provider import AnswerGenerator
from app.retrieval import retrieve
from app.schemas import (
    AnswerRequest,
    AnswerResponse,
    AnswerWithContextRequest,
    AnswerWithContextResponse,
)

app = FastAPI(
    title="Zuxpert-lite Reference Assistant",
    description=(
        "A small seeded fashion-catalog Q&A assistant used as the default system "
        "under test for Aegis Measure. Implements the component-check contract "
        "(/answer_with_context: frozen context, no retrieval) and the end-to-end "
        "contract (/answer: the assistant retrieves its own context)."
    ),
    version="0.1.0",
)


@app.exception_handler(RuntimeError)
def handle_runtime_error(request: Request, exc: RuntimeError) -> JSONResponse:
    # Covers RuntimeError raised either from get_answer_generator() itself
    # (e.g. missing ANTHROPIC_API_KEY, raised during dependency resolution,
    # before a route body ever runs) or from generator.generate(...).
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/answer", response_model=AnswerResponse)
def answer(
    data: AnswerRequest, generator: AnswerGenerator = Depends(get_answer_generator)
) -> AnswerResponse:
    """The end-to-end check hits this endpoint: no context is supplied, so
    the assistant must retrieve its own — exactly what a real customer's
    question goes through, including whatever the retrieval step gets
    wrong."""
    settings = get_settings()
    item = retrieve(data.question, enable_retrieval_bug=settings.enable_retrieval_bug)
    generated = generator.generate(question=data.question, context=item["listing_text"])
    return AnswerResponse(
        answer=generated, retrieved_sku=item["sku"], retrieved_context=item["listing_text"]
    )


@app.post("/answer_with_context", response_model=AnswerWithContextResponse)
def answer_with_context(
    data: AnswerWithContextRequest, generator: AnswerGenerator = Depends(get_answer_generator)
) -> AnswerWithContextResponse:
    """The component check hits this endpoint: the exact context is handed
    over directly, bypassing retrieval entirely — isolating whether the
    assistant reasons correctly given the right facts."""
    generated = generator.generate(question=data.question, context=data.context)
    return AnswerWithContextResponse(answer=generated)
