"""Patient requests: submit one, see its status, and keep it private to its patient.

Needs the database running with the tables created (see README).
The `app` fixture and the test-account cleanup are in conftest.py.
"""

import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import text


def _new_patient(app: FastAPI) -> TestClient:
    """A client signed in as a newly registered test patient."""
    client = TestClient(app)
    client.post(
        "/auth/register",
        data={
            "full_name": "Test Patient",
            "email": f"test-{uuid.uuid4().hex[:12]}@example.com",
            "password": "password123",
            "date_of_birth": "1990-05-01",
            "phone": "+91 90000 99999",
        },
    )
    return client


def _submit(client: TestClient, request_text: str) -> Response:
    return client.post("/patient/requests", data={"request_text": request_text}, follow_redirects=False)


def test_patient_home_shows_the_request_form(app: FastAPI) -> None:
    page = _new_patient(app).get("/patient").text

    assert 'name="request_text"' in page


def test_submit_saves_a_running_request_and_an_audit_event(app: FastAPI) -> None:
    client = _new_patient(app)

    response = _submit(client, "  I need a cardiology follow-up next week.  ")

    assert response.status_code == 303
    url = response.headers["location"]
    run_id = int(url.removeprefix("/patient/requests/"))
    with app.state.engine.connect() as connection:
        run = connection.execute(
            text("SELECT status, request_text FROM workflow_runs WHERE id = :id"), {"id": run_id}
        ).mappings().one()
        events = connection.execute(
            text("SELECT action, entity_type, entity_id FROM audit_events WHERE workflow_run_id = :id"),
            {"id": run_id},
        ).all()
    assert run["status"] == "RUNNING"
    assert run["request_text"] == "I need a cardiology follow-up next week."
    assert events == [("request.create", "workflow_run", run_id)]

    page = client.get(url).text
    assert f"WR-{run_id}" in page
    assert "I need a cardiology follow-up next week." in page
    assert "RUNNING" in page


@pytest.mark.parametrize("request_text", ["", "   ", "x" * 2001])
def test_empty_or_too_long_request_is_rejected(app: FastAPI, request_text: str) -> None:
    response = _submit(_new_patient(app), request_text)

    assert response.status_code == 400
    assert 'class="error"' in response.text
    with app.state.engine.connect() as connection:
        runs = connection.execute(
            text(
                "SELECT count(*) FROM workflow_runs r JOIN users u ON u.id = r.created_by "
                "WHERE u.email LIKE 'test-%@example.com'"
            )
        ).scalar_one()
    assert runs == 0


def test_another_patient_gets_404(app: FastAPI) -> None:
    owner = _new_patient(app)
    url = _submit(owner, "Book a dermatology visit.").headers["location"]

    assert owner.get(url).status_code == 200
    assert _new_patient(app).get(url).status_code == 404
    # A missing request looks the same as someone else's.
    assert owner.get("/patient/requests/999999999").status_code == 404
