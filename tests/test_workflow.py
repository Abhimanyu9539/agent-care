"""The first workflow: the safety step runs after a request is saved and decides what happens next.

Needs the database running with the tables created (see README). No LLM is called.
The `app` fixture and the test-account cleanup are in conftest.py.
The test client waits for background tasks, so each workflow has finished when `submit` returns.
"""

import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient
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


def test_safety_step_sorts_requests() -> None:
    def category(request_text: str) -> str:
        return safety_intake({"run_id": 1, "request_text": request_text})["safety"]["category"]

    assert category("I have crushing chest pain right now") == "EMERGENCY"
    assert category("What dose should I take?") == "CLINICAL_ADVICE"
    assert category("Book a cardiology follow-up") == "ADMIN"


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
    assert blocked == [({"rule_id": "clinical_advice.dose"},)]


def test_ordinary_request_passes_the_safety_step(app: FastAPI) -> None:
    run = _submit(_sign_up(app), "Book a cardiology follow-up next week")

    assert run["status"] == "COMPLETED"
    assert run["safety"] == "ADMIN"
    assert _rows(app, "SELECT id FROM escalations WHERE workflow_run_id = :id", run["id"]) == []


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
    # The timeline stores counts, never the patient's words.
    assert _rows(app, "SELECT input_summary FROM workflow_steps WHERE run_id = :id", run_id) == [({"text_chars": 15},)]
    assert staff.get("/api/staff/runs/999999999").status_code == 404
    assert patient.get(f"/api/staff/runs/{run_id}").status_code == 403
