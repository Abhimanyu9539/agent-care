"""Sign-in API: register, log in, log out, and who is signed in."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import RowMapping
from sqlalchemy.orm import Session

from app.auth.deps import current_user
from app.auth.security import MAX_PASSWORD_BYTES, verify_password
from app.auth.users import EmailTaken, get_user, get_user_by_email, register_patient
from app.db.session import get_db

router = APIRouter(prefix="/api/auth")

Db = Annotated[Session, Depends(get_db)]

MIN_PASSWORD_LENGTH = 8
# One message for an unknown email, a wrong password and an inactive account,
# so the API never reveals which emails are registered.
LOGIN_FAILED = "Email or password is incorrect."


# Fields default to "" so a missing field gets the friendly message below, not a 422.
class RegisterBody(BaseModel):
    full_name: str = ""
    email: str = ""
    password: str = ""
    date_of_birth: str = ""
    phone: str = ""


class LoginBody(BaseModel):
    email: str = ""
    password: str = ""


def _user_json(user: RowMapping) -> dict:
    """The user as the frontend sees it. Never includes the password hash."""
    return {"id": user["id"], "full_name": user["full_name"], "role": user["role"]}


def _sign_in(request: Request, db: Session, user_id: int) -> dict:
    request.session.clear()
    request.session["user_id"] = user_id
    return _user_json(get_user(db, user_id))


def _registration_error(form: dict[str, str], password: str) -> str | None:
    """The first problem with the registration form, or None."""
    if not all(form.values()) or not password:
        return "Please fill in every field."
    if "@" not in form["email"]:
        return "Please enter a valid email address."
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"The password needs at least {MIN_PASSWORD_LENGTH} characters."
    if len(password.encode()) > MAX_PASSWORD_BYTES:
        return f"The password can be at most {MAX_PASSWORD_BYTES} characters."
    try:
        born = date.fromisoformat(form["date_of_birth"])
    except ValueError:
        return "Please enter a valid date of birth."
    if born > date.today():
        return "The date of birth cannot be in the future."
    return None


@router.post("/register", status_code=201)
def register(request: Request, db: Db, body: RegisterBody) -> dict:
    form = {
        "full_name": body.full_name.strip(),
        "email": body.email.strip(),
        "date_of_birth": body.date_of_birth,
        "phone": body.phone.strip(),
    }
    error = _registration_error(form, body.password)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    try:
        user_id = register_patient(
            db,
            full_name=form["full_name"],
            email=form["email"],
            password=body.password,
            date_of_birth=date.fromisoformat(form["date_of_birth"]),
            phone=form["phone"],
        )
    except EmailTaken:
        raise HTTPException(status_code=400, detail="That email is already registered.") from None
    return _sign_in(request, db, user_id)


@router.post("/login")
def login(request: Request, db: Db, body: LoginBody) -> dict:
    user = get_user_by_email(db, body.email)
    if user is None or not user["is_active"] or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=400, detail=LOGIN_FAILED)
    return _sign_in(request, db, user["id"])


@router.post("/logout", status_code=204)
def logout(request: Request) -> Response:
    request.session.clear()
    return Response(status_code=204)


@router.get("/me")
def me(user: Annotated[RowMapping | None, Depends(current_user)]) -> dict:
    """The signed-in user, or 401."""
    if user is None:
        raise HTTPException(status_code=401, detail="Please log in.")
    return _user_json(user)
