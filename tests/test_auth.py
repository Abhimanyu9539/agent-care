"""Sign-in: register, log in and log out, against the real database.

Needs the database running with the tables created (see README).
Test accounts use emails like test-<random>@example.com and are deleted after each test,
so the seed data is never touched.
"""

import uuid
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import text

from app.auth.security import verify_password
from app.config import Settings
from app.main import create_app

LOGIN_FAILED = "Email or password is incorrect."


@pytest.fixture
def app() -> Iterator[FastAPI]:
    app = create_app(Settings(_env_file=None, secret_key="test-secret"))
    yield app
    with app.state.engine.begin() as connection:
        test_users = "SELECT id FROM users WHERE email LIKE 'test-%@example.com'"
        connection.execute(text(f"DELETE FROM patient_profiles WHERE user_id IN ({test_users})"))
        connection.execute(text("DELETE FROM users WHERE email LIKE 'test-%@example.com'"))
    app.state.engine.dispose()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


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
    assert client.get("/", follow_redirects=False).status_code == 200

    response = client.post("/auth/logout", follow_redirects=False)

    assert _redirects_to_login(response)
    assert _redirects_to_login(client.get("/", follow_redirects=False))
