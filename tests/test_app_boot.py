"""Step 1 smoke tests: the app boots and configuration is validated."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from agentcare.config import Settings
from agentcare.main import create_app


def test_health_returns_ok() -> None:
    settings = Settings(_env_file=None, secret_key="test-secret")
    client = TestClient(create_app(settings))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_missing_secret_key_fails_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(ValidationError, match="secret_key"):
        Settings(_env_file=None)
