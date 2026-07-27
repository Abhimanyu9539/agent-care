"""Smoke tests: the app boots, reaches Postgres, and configuration is validated.

Needs the database running: `docker compose up -d db`.
"""

import os

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings, export_langsmith
from app.main import create_app


def test_health_reports_database_ok() -> None:
    settings = Settings(_env_file=None, secret_key="test-secret")
    client = TestClient(create_app(settings))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_reports_database_down() -> None:
    # Nothing listens on port 1. The engine's connect timeout (5 s) ends the attempt;
    # 127.0.0.1 rather than localhost, so only one address is tried.
    unreachable = "postgresql+psycopg://agentcare:agentcare@127.0.0.1:1/agentcare"
    settings = Settings(_env_file=None, secret_key="test-secret", database_url=unreachable)
    client = TestClient(create_app(settings))

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "error", "database": "down"}


def test_missing_secret_key_fails_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(ValidationError, match="secret_key"):
        Settings(_env_file=None)


def test_langsmith_settings_are_copied_to_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    environment: dict[str, str] = {}
    monkeypatch.setattr(os, "environ", environment)  # leaves the real environment alone
    settings = Settings(
        _env_file=None,
        secret_key="test-secret",
        langsmith_tracing=True,
        langsmith_api_key="test-key",
        langsmith_endpoint="https://eu.api.smith.langchain.com",
        langsmith_agent_id="agentcare",
        langsmith_agent_environment="local",
    )

    export_langsmith(settings)

    # LangSmith reads only the environment, never .env. Settings left empty (the project here) stay out of it.
    assert environment == {
        "LANGSMITH_TRACING": "true",
        "LANGSMITH_API_KEY": "test-key",
        "LANGSMITH_ENDPOINT": "https://eu.api.smith.langchain.com",
        "LANGSMITH_AGENT_ID": "agentcare",
        "LANGSMITH_AGENT_ENVIRONMENT": "local",
    }


def test_langsmith_settings_stay_out_of_the_environment_when_tracing_is_off(monkeypatch: pytest.MonkeyPatch) -> None:
    environment: dict[str, str] = {}
    monkeypatch.setattr(os, "environ", environment)
    settings = Settings(_env_file=None, secret_key="test-secret", langsmith_api_key="test-key")

    export_langsmith(settings)

    assert environment == {}
