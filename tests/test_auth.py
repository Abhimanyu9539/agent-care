"""Sign-in and role checks: register, log in, log out and who may use which route.

Needs the database running with the tables created (see README).
The `app` and `client` fixtures and the test-account cleanup are in conftest.py.
"""

import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import text

from app.auth.security import verify_password

LOGIN_FAILED = "Email or password is incorrect."


def _new_email() -> str:
    return f"test-{uuid.uuid4().hex[:12]}@example.com"


def _register(client: TestClient, **fields: str) -> Response:
    body = {
        "full_name": "Test Patient",
        "email": _new_email(),
        "password": "password123",
        "date_of_birth": "1990-05-01",
        "phone": "+91 90000 99999",
    } | fields
    return client.post("/api/auth/register", json=body)


def _login(client: TestClient, email: str, password: str) -> Response:
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _me(client: TestClient) -> Response:
    return client.get("/api/auth/me")


def test_me_is_401_when_signed_out(client: TestClient) -> None:
    assert _me(client).status_code == 401


def test_register_creates_patient_and_signs_in(app: FastAPI, client: TestClient) -> None:
    email = _new_email()

    response = _register(client, email=email)

    assert response.status_code == 201
    body = response.json()
    assert body["full_name"] == "Test Patient"
    assert body["role"] == "PATIENT"
    assert "password_hash" not in body
    with app.state.engine.connect() as connection:
        user = connection.execute(
            text("SELECT id, role, password_hash FROM users WHERE email = :email"), {"email": email}
        ).mappings().one()
        profiles = connection.execute(
            text("SELECT count(*) FROM patient_profiles WHERE user_id = :id"), {"id": user["id"]}
        ).scalar_one()
    assert body["id"] == user["id"]
    assert user["role"] == "PATIENT"
    assert user["password_hash"] != "password123"
    assert verify_password("password123", user["password_hash"])
    assert profiles == 1
    assert _me(client).json() == body


def test_register_rejects_duplicate_email_in_any_case(client: TestClient) -> None:
    email = _new_email()
    _register(client, email=email)

    response = _register(client, email=email.upper())

    assert response.status_code == 400
    assert response.json()["detail"] == "That email is already registered."


def test_register_rejects_short_password(app: FastAPI, client: TestClient) -> None:
    email = _new_email()

    response = _register(client, email=email, password="short")

    assert response.status_code == 400
    assert "at least 8 characters" in response.json()["detail"]
    with app.state.engine.connect() as connection:
        count = connection.execute(
            text("SELECT count(*) FROM users WHERE email = :email"), {"email": email}
        ).scalar_one()
    assert count == 0


def test_register_rejects_missing_fields(client: TestClient) -> None:
    response = client.post("/api/auth/register", json={})

    assert response.status_code == 400
    assert response.json()["detail"] == "Please fill in every field."


def test_login_with_right_and_wrong_password(app: FastAPI, client: TestClient) -> None:
    email = _new_email()
    _register(client, email=email)
    fresh = TestClient(app)

    # Wrong password, unknown email and an over-long password all get the same answer.
    for response in (
        _login(fresh, email, "wrong-password"),
        _login(fresh, _new_email(), "password123"),
        _login(fresh, email, "x" * 100),
    ):
        assert response.status_code == 400
        assert response.json()["detail"] == LOGIN_FAILED

    response = _login(fresh, email.upper(), "password123")

    assert response.status_code == 200
    assert response.json()["full_name"] == "Test Patient"
    assert "password_hash" not in response.json()
    assert _me(fresh).json()["role"] == "PATIENT"


def test_inactive_user_cannot_log_in_and_is_signed_out(app: FastAPI, client: TestClient) -> None:
    email = _new_email()
    _register(client, email=email)  # leaves `client` signed in
    with app.state.engine.begin() as connection:
        connection.execute(text("UPDATE users SET is_active = false WHERE email = :email"), {"email": email})

    response = _login(TestClient(app), email, "password123")

    assert response.status_code == 400
    assert response.json()["detail"] == LOGIN_FAILED
    assert _me(client).status_code == 401


def test_logout_clears_the_session(client: TestClient) -> None:
    _register(client)
    assert _me(client).status_code == 200

    response = client.post("/api/auth/logout")

    assert response.status_code == 204
    assert _me(client).status_code == 401


def test_role_routes_are_401_when_signed_out(client: TestClient) -> None:
    assert client.post("/api/patient/requests", json={"request_text": "Hello"}).status_code == 401
    assert client.get("/api/staff/slots").status_code == 401


def test_patient_cannot_use_staff_routes(client: TestClient) -> None:
    _register(client)

    assert client.get("/api/staff/slots").status_code == 403


@pytest.mark.parametrize("role", ["STAFF", "ADMIN"])
def test_staff_and_admin_use_staff_routes_but_not_patient_routes(
    app: FastAPI, client: TestClient, role: str
) -> None:
    # The role is read from the database on every request, so changing it here takes effect at once.
    email = _new_email()
    _register(client, email=email)
    with app.state.engine.begin() as connection:
        connection.execute(
            text("UPDATE users SET role = :role WHERE email = :email"), {"role": role, "email": email}
        )

    assert client.get("/api/staff/slots").status_code == 200
    assert client.post("/api/patient/requests", json={"request_text": "Hello"}).status_code == 403
    assert _me(client).json()["role"] == role


def test_staff_slots_come_from_the_database(app: FastAPI, client: TestClient) -> None:
    email = _new_email()
    _register(client, email=email)
    code = f"test-{uuid.uuid4().hex[:12]}"
    with app.state.engine.begin() as connection:
        connection.execute(text("UPDATE users SET role = 'STAFF' WHERE email = :email"), {"email": email})
        department_id = connection.execute(
            text("INSERT INTO departments (code, name, description) VALUES (:code, :code, 'test') RETURNING id"),
            {"code": code},
        ).scalar_one()
        doctor_id = connection.execute(
            text("INSERT INTO doctors (department_id, full_name) VALUES (:id, 'Dr. Test Doctor') RETURNING id"),
            {"id": department_id},
        ).scalar_one()
        slot_id = connection.execute(
            text(
                "INSERT INTO appointment_slots (doctor_id, start_time, end_time) "
                "VALUES (:id, now() + interval '1 hour', now() + interval '90 minutes') RETURNING id"
            ),
            {"id": doctor_id},
        ).scalar_one()

    try:
        slots = client.get("/api/staff/slots").json()
    finally:
        with app.state.engine.begin() as connection:
            connection.execute(text("DELETE FROM appointment_slots WHERE id = :id"), {"id": slot_id})
            connection.execute(text("DELETE FROM doctors WHERE id = :id"), {"id": doctor_id})
            connection.execute(text("DELETE FROM departments WHERE id = :id"), {"id": department_id})

    slot = next(s for s in slots if s["id"] == slot_id)
    assert slot["doctor"] == "Dr. Test Doctor"
    assert slot["department"] == code
    assert slot["status"] == "AVAILABLE"
    assert slot["starts_at"]
