"""Application settings loaded from environment variables and `.env`."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed configuration for AgentCare.

    Field names are matched case-insensitively, so `SECRET_KEY` in the
    environment fills `secret_key`. Unknown keys in `.env` are ignored.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    secret_key: SecretStr

    database_url: str = "postgresql+psycopg://agentcare:agentcare@localhost:5432/agentcare"
    upload_dir: Path = Path("./uploads")
    # Times are stored in UTC and shown in this time zone.
    hospital_tz: str = "Asia/Kolkata"

    # Every LLM call goes through OpenRouter; llm_model is an OpenRouter model id.
    open_router_api_key: SecretStr | None = None
    llm_model: str = "anthropic/claude-haiku-5.5"
    llm_timeout_seconds: float = Field(default=120, gt=0)
    llm_max_retries: int = Field(default=2, ge=0)

    run_workflows_inline: bool = False
    max_upload_mb: int = Field(default=10, gt=0)
    sensitive_cancel_window_hours: int = Field(default=24, ge=0)
    routing_confidence_threshold: float = Field(default=0.6, ge=0, le=1)
    job_interval_seconds: int = Field(default=60, ge=0)

    langsmith_tracing: bool = False
    langsmith_api_key: SecretStr | None = None
    langsmith_endpoint: str | None = None
    # Where traces go: a project, or an agent id and environment. Set one or the other.
    langsmith_project: str | None = None
    langsmith_agent_id: str | None = None
    langsmith_agent_environment: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings, loaded once."""
    return Settings()


def export_langsmith(settings: Settings) -> None:
    """When tracing is on, copy the LangSmith settings into the environment, the only place LangSmith reads them.

    Settings read `.env` but leave the environment alone, so without this `.env` could not turn tracing on.
    """
    if not settings.langsmith_tracing:
        return
    api_key = settings.langsmith_api_key.get_secret_value() if settings.langsmith_api_key else None
    values = {
        "LANGSMITH_TRACING": "true",
        "LANGSMITH_API_KEY": api_key,
        "LANGSMITH_ENDPOINT": settings.langsmith_endpoint,
        "LANGSMITH_PROJECT": settings.langsmith_project,
        "LANGSMITH_AGENT_ID": settings.langsmith_agent_id,
        "LANGSMITH_AGENT_ENVIRONMENT": settings.langsmith_agent_environment,
    }
    os.environ.update({name: value for name, value in values.items() if value})
