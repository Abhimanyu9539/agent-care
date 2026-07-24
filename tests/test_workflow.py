"""The first workflow: the safety step runs after a request is saved and decides what happens next.

Needs the database running with the tables created (see README). The real LLM is never called:
`fake_llm` stands in for it, and without it the test settings have no API key, so the LLM step fails.
The fixtures and the test-account cleanup are in conftest.py.
The test client waits for background tasks, so each workflow has finished when `submit` returns.
"""

import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langgraph.runtime import Runtime
from sqlalchemy import text

from app.agents.safety.agent import safety_intake


def _sign_up(app: FastAPI, role: str = "PATIENT") -> TestClient:
    """A client signed in as a new test user with this role."""
    client = TestClient(app)
    user = client.post(
        "/api/auth/register",
        json={
            "full_name": "Test Patient",
            "email": f"test-{uuid.uuid4().hex[:12]}@example.com",
            "password": "password123",
            "date_of_birth": "1990-05-01",
            "phone": "+91 90000 99999",
        },
    ).json()
    with app.state.engine.begin() as connection:
        connection.execute(text("UPDATE users SET role = :role WHERE id = :id"), {"role": role, "id": user["id"]})
    return client


def _submit(patient: TestClient, request_text: str) -> dict:
    """Submit a request and return how the patient sees it once the workflow has run."""
    run_id = patient.post("/api/patient/requests", json={"request_text": request_text}).json()["id"]
    return patient.get(f"/api/patient/requests/{run_id}").json()


def _rows(app: FastAPI, sql: str, run_id: int) -> list:
    with app.state.engine.connect() as connection:
        return connection.execute(text(sql), {"id": run_id}).all()


def test_rules_decide_obvious_cases_without_the_llm(app: FastAPI, fake_llm) -> None:
    def safety(request_text: str) -> dict:
        state = {"run_id": 1, "request_text": request_text, "patient_name": "Test Patient"}
        return safety_intake(state, Runtime(context=app.state.settings))["safety"]

    assert safety("I have crushing chest pain right now")["category"] == "EMERGENCY"
    assert safety("What dose should I take?")["category"] == "CLINICAL_ADVICE"
    assert fake_llm.sent == []

    assert safety("Book a cardiology follow-up") == {
        "category": "ADMIN", "rule_id": None, "reason": "The fake LLM says so.", "source": "llm"
    }
    assert fake_llm.sent == ["Book a cardiology follow-up"]


def test_emergency_opens_an_urgent_case_for_staff(app: FastAPI) -> None:
    run = _submit(_sign_up(app), "I have crushing chest pain right now")

    assert run["status"] == "ESCALATED"
    assert run["safety"] == "EMERGENCY"
    cases = _rows(app, "SELECT type, priority, status FROM escalations WHERE workflow_run_id = :id", run["id"])
    assert cases == [("EMERGENCY", "URGENT", "OPEN")]
    steps = _rows(app, "SELECT seq, agent, node, outcome FROM workflow_steps WHERE run_id = :id", run["id"])
    assert steps == [(1, "safety", "safety_intake", "OK")]
    events = _rows(app, "SELECT action, actor_agent FROM audit_events WHERE workflow_run_id = :id ORDER BY id", run["id"])
    assert events == [("request.create", None), ("escalation.open", "safety"), ("workflow.status_change", "safety")]

    inbox = _sign_up(app, "STAFF").get("/api/staff/escalations").json()
    assert any(case["workflow_run_id"] == run["id"] and case["priority"] == "URGENT" for case in inbox)


def test_clinical_question_is_declined_without_a_case(app: FastAPI) -> None:
    run = _submit(_sign_up(app), "What dose of my BP tablets should I take?")

    assert run["status"] == "COMPLETED"
    assert run["safety"] == "CLINICAL_ADVICE"
    assert _rows(app, "SELECT id FROM escalations WHERE workflow_run_id = :id", run["id"]) == []
    blocked = _rows(
        app, "SELECT metadata FROM audit_events WHERE workflow_run_id = :id AND action = 'safety.blocked_input'", run["id"]
    )
    assert blocked == [({"source": "rules", "rule_id": "clinical_advice.dose"},)]


@pytest.mark.parametrize(
    ("category", "status", "cases"),
    [
        ("EMERGENCY", "ESCALATED", [("EMERGENCY", "URGENT")]),
        ("CLINICAL_ADVICE", "COMPLETED", []),
        ("ADMIN", "COMPLETED", []),
    ],
)
def test_the_llm_decides_when_no_rule_matches(app: FastAPI, fake_llm, category, status, cases) -> None:
    fake_llm.category = category

    run = _submit(_sign_up(app), "Please help me with my dad")

    assert (run["status"], run["safety"]) == (status, category)
    assert _rows(app, "SELECT type, priority FROM escalations WHERE workflow_run_id = :id", run["id"]) == cases
    [(outcome, llm_meta)] = _rows(app, "SELECT outcome, llm_meta FROM workflow_steps WHERE run_id = :id", run["id"])
    assert outcome == "OK"
    assert llm_meta == {
        "model": app.state.settings.llm_model, "prompt_version": "safety-v1", "tokens_in": 10, "tokens_out": 5
    }


def test_the_llm_never_sees_personal_details(app: FastAPI, fake_llm) -> None:
    _submit(_sign_up(app), "I am Test Patient, call me on +91 98765 43210 or write to me at tp@mail.com")

    assert fake_llm.sent == ["I am [NAME] [NAME], call me on [NUMBER] or write to me at [EMAIL]"]


def test_without_an_api_key_the_request_goes_to_staff(app: FastAPI) -> None:
    # No fake_llm and no API key, so the LLM call fails: the same path as a timeout or OpenRouter being down.
    run = _submit(_sign_up(app), "Please help me with my dad")

    assert (run["status"], run["safety"]) == ("ESCALATED", "UNCHECKED")
    cases = _rows(app, "SELECT type, priority, status FROM escalations WHERE workflow_run_id = :id", run["id"])
    assert cases == [("SYSTEM_FAILURE", "HIGH", "OPEN")]
    [(outcome, llm_meta)] = _rows(app, "SELECT outcome, llm_meta FROM workflow_steps WHERE run_id = :id", run["id"])
    assert outcome == "FAILED"
    assert llm_meta["error"] == "LLMNotConfigured"


def test_staff_see_the_timeline_and_patients_do_not(app: FastAPI) -> None:
    patient = _sign_up(app)
    run_id = _submit(patient, "I can't breathe")["id"]
    staff = _sign_up(app, "STAFF")

    shown = staff.get(f"/api/staff/runs/{run_id}").json()

    assert shown["run"]["status"] == "ESCALATED"
    assert shown["run"]["patient"] == "Test Patient"
    [step] = shown["steps"]
    assert (step["agent"], step["node"], step["outcome"]) == ("safety", "safety_intake", "OK")
    assert step["output"]["safety"]["rule_id"] == "emergency.breathing"
    assert step["llm_meta"] is None  # a rule decided, so the LLM was not asked
    # The timeline stores counts, never the patient's words.
    assert _rows(app, "SELECT input_summary FROM workflow_steps WHERE run_id = :id", run_id) == [({"text_chars": 15},)]
    assert staff.get("/api/staff/runs/999999999").status_code == 404
    assert patient.get(f"/api/staff/runs/{run_id}").status_code == 403
