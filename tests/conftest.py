"""Shared test setup.

Environment defaults are set before any test imports `app.main`,
which builds the app at import time and needs `SECRET_KEY`.

Tests run against the real database. Test accounts use emails like test-<random>@example.com,
and they and everything they created are deleted after each test, so the seed data is never touched.
"""

import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("APP_ENV", "test")

from collections.abc import Iterator  # noqa: E402 (imports after the environment defaults)

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

TEST_USERS = "SELECT id FROM users WHERE email LIKE 'test-%@example.com'"


@pytest.fixture
def app() -> Iterator[FastAPI]:
    app = create_app(Settings(_env_file=None, secret_key="test-secret"))
    yield app
    # Children first, so no foreign key blocks a delete.
    with app.state.engine.begin() as connection:
        connection.execute(text(f"DELETE FROM audit_events WHERE actor_user_id IN ({TEST_USERS})"))
        connection.execute(text(f"DELETE FROM workflow_runs WHERE created_by IN ({TEST_USERS})"))
        connection.execute(text(f"DELETE FROM patient_profiles WHERE user_id IN ({TEST_USERS})"))
        connection.execute(text(f"DELETE FROM users WHERE id IN ({TEST_USERS})"))
    app.state.engine.dispose()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)
