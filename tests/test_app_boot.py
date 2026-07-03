"""Smoke tests: the app boots, reaches Postgres, and configuration is validated.

Needs the database running: `docker compose up -d db`.
"""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
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
