"""Patient pages. Every route here needs the PATIENT role."""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import RowMapping
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.db.session import get_db
from app.services.patient import create_request, get_request
from app.web import templates

patient_user = require_role("PATIENT")

router = APIRouter(prefix="/patient", dependencies=[Depends(patient_user)])

User = Annotated[RowMapping, Depends(patient_user)]
Db = Annotated[Session, Depends(get_db)]

MAX_REQUEST_CHARS = 2000


@router.get("")
def home(request: Request, user: User) -> Response:
    """The form where a patient describes what they need."""
    return templates.TemplateResponse(request, "patient/home.html", {"user": user})


@router.post("/requests")
def submit(request: Request, user: User, db: Db, request_text: Annotated[str, Form()] = "") -> Response:
    """Save the request, then show it. Redirecting means a page refresh cannot submit it twice."""
    request_text = request_text.strip()
    if not request_text:
        error = "Please describe what you need."
    elif len(request_text) > MAX_REQUEST_CHARS:
        error = f"Please keep your request to at most {MAX_REQUEST_CHARS} characters."
    else:
        run_id = create_request(db, user["id"], request_text)
        return RedirectResponse(f"/patient/requests/{run_id}", status_code=303)
    return templates.TemplateResponse(
        request,
        "patient/home.html",
        {"user": user, "request_text": request_text, "error": error},
        status_code=400,
    )


@router.get("/requests/{run_id}")
def show(request: Request, run_id: int, user: User, db: Db) -> Response:
    """One request and its status.

    Another patient's request gets the same 404 as a missing one, so the page never reveals which ids exist.
    """
    run = get_request(db, run_id, user["id"])
    if run is None:
        raise HTTPException(status_code=404, detail="Request not found.")
    return templates.TemplateResponse(request, "patient/request.html", {"user": user, "run": run})
