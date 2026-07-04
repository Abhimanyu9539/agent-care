"""Sign-in pages: register, log in, log out."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from app.auth.security import MAX_PASSWORD_BYTES, verify_password
from app.auth.users import EmailTaken, get_user_by_email, register_patient
from app.db.session import get_db
from app.web import templates

router = APIRouter(prefix="/auth")

Db = Annotated[Session, Depends(get_db)]

MIN_PASSWORD_LENGTH = 8
# One message for an unknown email, a wrong password and an inactive account,
# so the page never reveals which emails are registered.
LOGIN_FAILED = "Email or password is incorrect."


def _sign_in(request: Request, user_id: int) -> RedirectResponse:
    request.session.clear()
    request.session["user_id"] = user_id
    return RedirectResponse("/", status_code=303)


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


@router.get("/register")
def register_page(request: Request) -> Response:
    return templates.TemplateResponse(request, "auth/register.html", {"form": {}})


@router.post("/register")
def register(
    request: Request,
    db: Db,
    full_name: Annotated[str, Form()] = "",
    email: Annotated[str, Form()] = "",
    password: Annotated[str, Form()] = "",
    date_of_birth: Annotated[str, Form()] = "",
    phone: Annotated[str, Form()] = "",
) -> Response:
    # Everything the form shows again on an error; the password is never sent back.
    form = {
        "full_name": full_name.strip(),
        "email": email.strip(),
        "date_of_birth": date_of_birth,
        "phone": phone.strip(),
    }
    error = _registration_error(form, password)
    if error is None:
        try:
            user_id = register_patient(
                db,
                full_name=form["full_name"],
                email=form["email"],
                password=password,
                date_of_birth=date.fromisoformat(form["date_of_birth"]),
                phone=form["phone"],
            )
        except EmailTaken:
            error = "That email is already registered."
        else:
            return _sign_in(request, user_id)
    return templates.TemplateResponse(
        request, "auth/register.html", {"form": form, "error": error}, status_code=400
    )


@router.get("/login")
def login_page(request: Request) -> Response:
    return templates.TemplateResponse(request, "auth/login.html", {"email": ""})


@router.post("/login")
def login(
    request: Request,
    db: Db,
    email: Annotated[str, Form()] = "",
    password: Annotated[str, Form()] = "",
) -> Response:
    user = get_user_by_email(db, email)
    if user is None or not user["is_active"] or not verify_password(password, user["password_hash"]):
        return templates.TemplateResponse(
            request, "auth/login.html", {"email": email, "error": LOGIN_FAILED}, status_code=400
        )
    return _sign_in(request, user["id"])


@router.post("/logout")
def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse("/auth/login", status_code=303)
