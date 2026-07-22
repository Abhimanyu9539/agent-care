"""Staff escalation inbox: open cases, most urgent first, and resolving one.

Needs the database running with the tables created (see README).
The `app` fixture and the test-account cleanup are in conftest.py.
The tests only resolve cases they created, so the seeded cases stay open.
"""

import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text


def _sign_up(app: FastAPI, role: str = "PATIENT") -> tuple[TestClient, int]:
    """A client signed in as a new test user with this role, and the user's id."""
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
    # The role is read from the database on every request, so this takes effect at once.
    with app.state.engine.begin() as connection:
        connection.execute(text("UPDATE users SET role = :role WHERE id = :id"), {"role": role, "id": user["id"]})
    return client, user["id"]


def _add_case(app: FastAPI, patient_user_id: int, priority: str, minutes_ago: int, status: str = "OPEN") -> int:
    """An escalation for this test patient, created `minutes_ago` minutes ago."""
    with app.state.engine.begin() as connection:
        return connection.execute(
            text(
                "INSERT INTO escalations (patient_id, type, priority, reason, status, created_at) "
                "SELECT id, 'LOW_CONFIDENCE', :priority, 'Test case', :status, "
                "       now() - :minutes_ago * interval '1 minute' "
                "FROM patient_profiles WHERE user_id = :user_id "
                "RETURNING id"
            ),
            {"user_id": patient_user_id, "priority": priority, "status": status, "minutes_ago": minutes_ago},
        ).scalar_one()


def test_inbox_lists_open_cases_most_urgent_first(app: FastAPI) -> None:
    _, patient_id = _sign_up(app)
    staff, _ = _sign_up(app, "STAFF")
    normal = _add_case(app, patient_id, "NORMAL", minutes_ago=30)
    high_newer = _add_case(app, patient_id, "HIGH", minutes_ago=5)
    high_older = _add_case(app, patient_id, "HIGH", minutes_ago=20)
    urgent = _add_case(app, patient_id, "URGENT", minutes_ago=1)
    resolved = _add_case(app, patient_id, "URGENT", minutes_ago=1, status="RESOLVED")

    cases = staff.get("/api/staff/escalations").json()

    # The seeded cases are in the list too; only the order of ours is checked.
    mine = [case for case in cases if case["id"] in {normal, high_newer, high_older, urgent, resolved}]
    assert [case["id"] for case in mine] == [urgent, high_older, high_newer, normal]
    assert mine[-1] == {
        "id": normal,
        "type": "LOW_CONFIDENCE",
        "priority": "NORMAL",
        "reason": "Test case",
        "workflow_run_id": None,
        "patient": "Test Patient",
        "waiting_minutes": 30,
    }


def test_resolve_closes_the_case_and_records_who_did_it(app: FastAPI) -> None:
    _, patient_id = _sign_up(app)
    staff, staff_id = _sign_up(app, "STAFF")
    case_id = _add_case(app, patient_id, "URGENT", minutes_ago=1)

    response = staff.post(f"/api/staff/escalations/{case_id}/resolve")

    assert response.status_code == 204
    with app.state.engine.connect() as connection:
        case = connection.execute(
            text("SELECT status, reviewed_by, reviewed_at FROM escalations WHERE id = :id"), {"id": case_id}
        ).mappings().one()
        events = connection.execute(
            text("SELECT actor_user_id, action FROM audit_events WHERE entity_type = 'escalation' AND entity_id = :id"),
            {"id": case_id},
        ).all()
    assert case["status"] == "RESOLVED"
    assert case["reviewed_by"] == staff_id
    assert case["reviewed_at"] is not None
    assert events == [(staff_id, "escalation.resolve")]
    assert case_id not in [case["id"] for case in staff.get("/api/staff/escalations").json()]
    # A case can only be resolved once.
    assert staff.post(f"/api/staff/escalations/{case_id}/resolve").status_code == 404


def test_only_staff_can_use_the_inbox(app: FastAPI) -> None:
    patient, patient_id = _sign_up(app)
    case_id = _add_case(app, patient_id, "URGENT", minutes_ago=1)

    assert patient.get("/api/staff/escalations").status_code == 403
    assert patient.post(f"/api/staff/escalations/{case_id}/resolve").status_code == 403
    assert TestClient(app).get("/api/staff/escalations").status_code == 401
