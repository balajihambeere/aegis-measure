from app.config import get_settings
from app.llm_provider import AnswerGenerator, AnthropicAnswerGenerator, OpenAIAnswerGenerator


def get_answer_generator() -> AnswerGenerator:
    """LLM_PROVIDER picks anthropic vs. openai; both are swappable behind
    the same AnswerGenerator protocol."""
    settings = get_settings()
    if settings.llm_provider == "openai":
        return OpenAIAnswerGenerator(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            timeout_seconds=settings.openai_timeout_seconds,
            max_retries=settings.openai_max_retries,
        )
    return AnthropicAnswerGenerator(
        api_key=settings.anthropic_api_key, model=settings.assistant_model
    )
