"""Sign-in and role checks: register, log in, log out and who may open which page.

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
    form = {
        "full_name": "Test Patient",
        "email": _new_email(),
        "password": "password123",
        "date_of_birth": "1990-05-01",
        "phone": "+91 90000 99999",
    } | fields
    return client.post("/auth/register", data=form, follow_redirects=False)


def _login(client: TestClient, email: str, password: str) -> Response:
    return client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=False)


def _redirects_to_login(response: Response) -> bool:
    return response.status_code == 303 and response.headers["location"] == "/auth/login"


def test_sign_in_pages_render(client: TestClient) -> None:
    assert client.get("/auth/login").status_code == 200
    assert client.get("/auth/register").status_code == 200


def test_home_redirects_when_signed_out(client: TestClient) -> None:
    assert _redirects_to_login(client.get("/", follow_redirects=False))


def test_register_creates_patient_and_signs_in(app: FastAPI, client: TestClient) -> None:
    email = _new_email()

    response = _register(client, email=email)

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    with app.state.engine.connect() as connection:
        user = connection.execute(
            text("SELECT id, role, password_hash FROM users WHERE email = :email"), {"email": email}
        ).mappings().one()
        profiles = connection.execute(
            text("SELECT count(*) FROM patient_profiles WHERE user_id = :id"), {"id": user["id"]}
        ).scalar_one()
    assert user["role"] == "PATIENT"
    assert user["password_hash"] != "password123"
    assert verify_password("password123", user["password_hash"])
    assert profiles == 1
    assert "Signed in as Test Patient (PATIENT)" in client.get("/").text


def test_register_rejects_duplicate_email_in_any_case(client: TestClient) -> None:
    email = _new_email()
    _register(client, email=email)

    response = _register(client, email=email.upper())

    assert response.status_code == 400
    assert "That email is already registered." in response.text


def test_register_rejects_short_password(app: FastAPI, client: TestClient) -> None:
    email = _new_email()

    response = _register(client, email=email, password="short")

    assert response.status_code == 400
    assert "at least 8 characters" in response.text
    with app.state.engine.connect() as connection:
        count = connection.execute(
            text("SELECT count(*) FROM users WHERE email = :email"), {"email": email}
        ).scalar_one()
    assert count == 0


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
        assert LOGIN_FAILED in response.text

    response = _login(fresh, email.upper(), "password123")

    assert response.status_code == 303
    assert "Signed in as Test Patient (PATIENT)" in fresh.get("/").text


def test_inactive_user_cannot_log_in_and_is_signed_out(app: FastAPI, client: TestClient) -> None:
    email = _new_email()
    _register(client, email=email)  # leaves `client` signed in
    with app.state.engine.begin() as connection:
        connection.execute(text("UPDATE users SET is_active = false WHERE email = :email"), {"email": email})

    response = _login(TestClient(app), email, "password123")

    assert response.status_code == 400
    assert LOGIN_FAILED in response.text
    assert _redirects_to_login(client.get("/", follow_redirects=False))


def test_logout_clears_the_session(client: TestClient) -> None:
    _register(client)
    assert client.get("/patient", follow_redirects=False).status_code == 200

    response = client.post("/auth/logout", follow_redirects=False)

    assert _redirects_to_login(response)
    assert _redirects_to_login(client.get("/", follow_redirects=False))


def test_role_pages_redirect_when_signed_out(client: TestClient) -> None:
    assert _redirects_to_login(client.get("/patient", follow_redirects=False))
    assert _redirects_to_login(client.get("/staff/slots", follow_redirects=False))


def test_patient_cannot_open_staff_pages(client: TestClient) -> None:
    _register(client)

    assert client.get("/staff/slots").status_code == 403
    assert client.get("/", follow_redirects=False).headers["location"] == "/patient"


@pytest.mark.parametrize("role", ["STAFF", "ADMIN"])
def test_staff_and_admin_open_staff_pages_but_not_patient_pages(
    app: FastAPI, client: TestClient, role: str
) -> None:
    # The role is read from the database on every request, so changing it here takes effect at once.
    email = _new_email()
    _register(client, email=email)
    with app.state.engine.begin() as connection:
        connection.execute(
            text("UPDATE users SET role = :role WHERE email = :email"), {"role": role, "email": email}
        )

    response = client.get("/staff/slots")

    assert response.status_code == 200
    assert "Upcoming slots" in response.text
    assert client.get("/patient").status_code == 403
    assert client.get("/", follow_redirects=False).headers["location"] == "/staff/slots"


def test_staff_slots_page_shows_slots_from_the_database(app: FastAPI, client: TestClient) -> None:
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
        page = client.get("/staff/slots").text
    finally:
        with app.state.engine.begin() as connection:
            connection.execute(text("DELETE FROM appointment_slots WHERE id = :id"), {"id": slot_id})
            connection.execute(text("DELETE FROM doctors WHERE id = :id"), {"id": doctor_id})
            connection.execute(text("DELETE FROM departments WHERE id = :id"), {"id": department_id})

    assert f"S-{slot_id}" in page
    assert "Dr. Test Doctor" in page
    assert code in page
    assert "AVAILABLE" in page
