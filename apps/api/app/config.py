from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://aegis:aegis@localhost:5432/aegis"

    aegis_api_key: str = "change-me-dev-key"

    llm_provider: str = "anthropic"
    anthropic_api_key: str = ""
    judge_model: str = "claude-haiku-4-5-20251001"
    assistant_model: str = "claude-haiku-4-5-20251001"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_timeout_seconds: float = 20.0
    openai_max_retries: int = 2

    default_schedule_interval_hours: int = 6
    calibration_agreement_threshold: float = 0.9

    # Off by default so importing/testing the app never spins up a
    # background thread unexpectedly; the shipped docker-compose stack
    # turns this on via .env for the real deployment.
    scheduler_enabled: bool = False
    scheduler_tick_interval_seconds: int = 300

    reference_assistant_url: str = "http://localhost:8100"
    enable_retrieval_bug: bool = False

    alert_webhook_url: str = ""

    # Comma-separated list, e.g. "http://localhost:5173,https://dashboard.example.com"
    cors_allowed_origins: str = "http://localhost:3000"

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
