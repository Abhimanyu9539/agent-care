"""Application settings loaded from environment variables and `.env`."""

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

    database_url: str = "sqlite:///./agentcare.db"
    checkpoint_db: Path = Path("./checkpoints.db")
    upload_dir: Path = Path("./uploads")

    anthropic_api_key: SecretStr | None = None
    llm_model: str = "claude-opus-5"
    llm_timeout_seconds: float = Field(default=120, gt=0)
    llm_max_retries: int = Field(default=2, ge=0)

    run_workflows_inline: bool = False
    max_upload_mb: int = Field(default=10, gt=0)
    sensitive_cancel_window_hours: int = Field(default=24, ge=0)
    routing_confidence_threshold: float = Field(default=0.6, ge=0, le=1)
    job_interval_seconds: int = Field(default=60, ge=0)

    langsmith_tracing: bool = False
    langsmith_api_key: SecretStr | None = None
    langsmith_project: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings, loaded once."""
    return Settings()
