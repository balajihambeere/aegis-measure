from app.config import get_settings
from app.services.grading.llm_judge import LLMJudgeGrader
from app.services.judge.anthropic_provider import AnthropicJudgeProvider
from app.services.judge.base import JudgeProvider
from app.services.judge.openai_provider import OpenAIJudgeProvider
from app.services.sut_adapter.base import SUTAdapter
from app.services.sut_adapter.http_adapter import HTTPSUTAdapter


def get_judge_grader() -> LLMJudgeGrader:
    """Constructs the production judge from configured settings
    (LLM_PROVIDER picks anthropic vs. openai; both are swappable behind the
    same JudgeProvider protocol). Overridden in tests with a scripted grader
    so the test suite never makes a real API call."""
    settings = get_settings()
    provider: JudgeProvider
    if settings.llm_provider == "openai":
        provider = OpenAIJudgeProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            timeout_seconds=settings.openai_timeout_seconds,
            max_retries=settings.openai_max_retries,
        )
    else:
        provider = AnthropicJudgeProvider(
            api_key=settings.anthropic_api_key, model=settings.judge_model
        )
    return LLMJudgeGrader(provider)


def get_sut_adapter() -> SUTAdapter:
    """Points at the reference assistant by default; swap by changing
    REFERENCE_ASSISTANT_URL to any system implementing the same two-endpoint
    contract. Overridden in tests with a scripted adapter."""
    settings = get_settings()
    return HTTPSUTAdapter(base_url=settings.reference_assistant_url)
