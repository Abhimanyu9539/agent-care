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

from app.agents.coordinator import agent as coordinator_agent  # noqa: E402
from app.agents.coordinator.schema import CoordinatorPlan  # noqa: E402
from app.agents.routing import agent as routing_agent  # noqa: E402
from app.agents.routing.schema import RoutingVerdict  # noqa: E402
from app.agents.safety import agent as safety_agent  # noqa: E402
from app.agents.safety.schema import SafetyVerdict  # noqa: E402
from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

TEST_USERS = "SELECT id FROM users WHERE email LIKE 'test-%@example.com'"


@pytest.fixture
def app() -> Iterator[FastAPI]:
    # No API key: unless a test uses `fake_llm`, the LLM step fails, as it would with the key removed.
    app = create_app(Settings(_env_file=None, secret_key="test-secret", open_router_api_key=None))
    yield app
    # Children first, so no foreign key blocks a delete.
    with app.state.engine.begin() as connection:
        connection.execute(text(f"DELETE FROM audit_events WHERE actor_user_id IN ({TEST_USERS})"))
        connection.execute(
            text(
                "DELETE FROM escalations WHERE patient_id IN "
                f"(SELECT id FROM patient_profiles WHERE user_id IN ({TEST_USERS}))"
            )
        )
        connection.execute(
            text(
                "DELETE FROM appointments WHERE patient_id IN "
                f"(SELECT id FROM patient_profiles WHERE user_id IN ({TEST_USERS}))"
            )
        )
        test_runs = f"SELECT id FROM workflow_runs WHERE created_by IN ({TEST_USERS})"
        connection.execute(text(f"DELETE FROM workflow_steps WHERE run_id IN ({test_runs})"))
        connection.execute(text(f"DELETE FROM workflow_runs WHERE created_by IN ({TEST_USERS})"))
        connection.execute(text(f"DELETE FROM patient_profiles WHERE user_id IN ({TEST_USERS})"))
        connection.execute(text(f"DELETE FROM users WHERE id IN ({TEST_USERS})"))
    app.state.engine.dispose()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


class FakeLLM:
    """Stands in for the safety, coordinator and routing LLMs, and remembers every text it was sent.

    Safety answers `category`. The coordinator answers `plan`, routing answers `route`;
    either raises its answer instead when it is an exception.
    """

    TOOL_CALLS = [{"tool": "list_departments", "args": {}, "ok": True, "ms": 1, "result_ref": "6 found"}]

    def __init__(self) -> None:
        self.category = "ADMIN"
        self.plan: CoordinatorPlan | Exception = CoordinatorPlan(
            intent="BOOK", plan=["routing"], reason="The fake LLM says so."
        )
        self.route: RoutingVerdict | Exception = RoutingVerdict(
            department="cardiology", visit_type="NEW", confidence=0.9, reason="The fake LLM says so."
        )
        self.sent: list[str] = []

    def safety(self, masked_text: str, settings: Settings) -> tuple[SafetyVerdict, dict]:
        self.sent.append(masked_text)
        return SafetyVerdict(category=self.category, reason="The fake LLM says so."), {"tokens_in": 10, "tokens_out": 5}

    def coordinator(self, masked_text: str, settings: Settings) -> tuple[CoordinatorPlan, dict]:
        self.sent.append(masked_text)
        if isinstance(self.plan, Exception):
            raise self.plan
        return self.plan, {"tokens_in": 15, "tokens_out": 6}

    def routing(self, masked_text: str, tools: list, settings: Settings) -> tuple[RoutingVerdict, list, dict]:
        self.sent.append(masked_text)
        if isinstance(self.route, Exception):
            raise self.route
        return self.route, self.TOOL_CALLS, {"tokens_in": 20, "tokens_out": 8}


@pytest.fixture
def fake_llm(monkeypatch: pytest.MonkeyPatch) -> FakeLLM:
    """Replace the real LLM calls, so tests never reach OpenRouter."""
    fake = FakeLLM()
    monkeypatch.setattr(safety_agent, "ask_llm", fake.safety)
    monkeypatch.setattr(coordinator_agent, "ask_llm", fake.coordinator)
    monkeypatch.setattr(routing_agent, "ask_llm", fake.routing)
    return fake
